# ADR: Native Observability Platform Plugins (P4.6)

## Status

Proposed

## Context

The selftest system currently has basic metrics emission capabilities via `selftest_metrics.py`, supporting local JSONL and Prometheus backends. However, the integration with observability platforms requires significant manual setup:

1. **Prometheus Integration**: Basic counter/histogram support exists, but no Kubernetes-native ServiceMonitor CRDs, recording rules, or pre-built Grafana dashboards are deployed automatically
2. **Datadog Integration**: Requires manual DogStatsD configuration and dashboard creation
3. **No Vendor-Native Assets**: Teams must manually create dashboards, alerts, and monitors in each platform
4. **Missing OpenTelemetry Support**: No path to modern OTLP-based observability stacks

The goal is to provide first-class, out-of-the-box integrations for Prometheus, Datadog, and OpenTelemetry that work with minimal configuration.

## Decision

We choose **Plugin-Based Backend Architecture with Pre-Built Assets**: A backend manager that routes metrics to multiple configurable backends, each with vendor-native dashboard, alert, and SLO definitions.

```
                        +-----------------+
                        | Selftest Runner |
                        +--------+--------+
                                 |
                                 | emit_metric()
                                 v
                        +-----------------+
                        | Backend Manager |
                        +--------+--------+
                                 |
         +-----------+-----------+-----------+-----------+
         |           |           |           |           |
         v           v           v           v           v
    +--------+  +--------+  +--------+  +--------+  +--------+
    | JSONL  |  | Prom   |  | Datadog|  | OTEL   |  | Custom |
    |Backend |  |Backend |  |Backend |  |Backend |  |Backend |
    +--------+  +--------+  +--------+  +--------+  +--------+
```

## Alternatives Considered

### Option A: Unified Metrics Library Only

**Summary**: Enhance `selftest_metrics.py` with more backends but no pre-built assets.

**Rejected because**: Teams would still need to create dashboards, alerts, and SLOs manually in each platform. This solves only half the problem (emission) while ignoring the operational burden (visualization/alerting).

### Option B: OpenTelemetry-Only

**Summary**: Standardize exclusively on OTLP and use OTEL collector for routing.

**Rejected because**: While OTEL is the future, many organizations are deeply invested in Prometheus or Datadog. Requiring OTEL collector deployment adds operational complexity for simple use cases. However, OTEL support is included in Phase 3.

### Option C: Vendor-Specific Scripts

**Summary**: Separate scripts for each platform (e.g., `setup_datadog.sh`, `setup_prometheus.sh`).

**Rejected because**: Creates maintenance burden across multiple scripts. Plugin architecture centralizes logic while allowing vendor-specific behavior.

## Design Details

### 1. Plugin Architecture

#### 1.1 Backend Interface

```python
# swarm/tools/metrics/backends/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class MetricDefinition:
    name: str
    type: str  # "counter", "histogram", "gauge"
    value: float
    labels: Dict[str, str]
    timestamp: Optional[float] = None

class MetricsBackend(ABC):
    """Base class for all metrics backends."""

    @abstractmethod
    def emit(self, metric: MetricDefinition) -> None:
        """Emit a single metric to the backend."""
        pass

    @abstractmethod
    def flush(self) -> None:
        """Flush any buffered metrics."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Clean up resources."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend identifier."""
        pass
```

#### 1.2 Backend Manager

```python
# swarm/tools/metrics/manager.py
class BackendManager:
    """Manages multiple metrics backends."""

    def __init__(self, config: dict):
        self.backends: List[MetricsBackend] = []
        self._load_backends(config)

    def _load_backends(self, config: dict):
        if config.get("jsonl", {}).get("enabled", True):
            self.backends.append(JSONLBackend(config["jsonl"]))
        if config.get("prometheus", {}).get("enabled", False):
            self.backends.append(PrometheusBackend(config["prometheus"]))
        if config.get("datadog", {}).get("enabled", False):
            self.backends.append(DatadogBackend(config["datadog"]))
        if config.get("opentelemetry", {}).get("enabled", False):
            self.backends.append(OTELBackend(config["opentelemetry"]))

    def emit(self, metric: MetricDefinition):
        for backend in self.backends:
            try:
                backend.emit(metric)
            except Exception as e:
                # Log but don't fail - observability should not break the system
                logger.warning(f"Backend {backend.name} failed: {e}")

    def flush(self):
        for backend in self.backends:
            backend.flush()
```

### 2. Prometheus Plugin Enhancements

#### 2.1 Current State

- Basic counter/histogram support via `prometheus_client`
- Manual scrape config required in `prometheus.yml`
- No Kubernetes integration
- No pre-built dashboards or alerts

#### 2.2 Enhancements

**ServiceMonitor CRD for Kubernetes:**

```yaml
# observability/kubernetes/selftest-servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: selftest
  namespace: selftest
  labels:
    app: selftest
    release: prometheus
spec:
  selector:
    matchLabels:
      app: selftest
  endpoints:
    - port: metrics
      interval: 15s
      path: /metrics
      scheme: http
  namespaceSelector:
    matchNames:
      - selftest
```

**Recording Rules for Common Queries:**

```yaml
# observability/prometheus/recording_rules.yaml
groups:
  - name: selftest_recording_rules
    interval: 30s
    rules:
      # Pre-computed availability SLI
      - record: selftest:availability:success_rate:5m
        expr: |
          (
            sum(rate(selftest_step_total{tier!="optional"}[5m]))
            - sum(rate(selftest_step_failures_total{tier!="optional"}[5m]))
          ) / sum(rate(selftest_step_total{tier!="optional"}[5m])) * 100

      # Pre-computed P95 duration
      - record: selftest:performance:p95_duration:5m
        expr: |
          histogram_quantile(0.95,
            sum(rate(selftest_run_duration_seconds_bucket[5m])) by (le)
          )

      # Governance pass rate by step
      - record: selftest:governance:pass_rate_by_step:5m
        expr: |
          1 - (
            sum(rate(selftest_step_failures_total{tier="governance"}[5m])) by (step_id)
            / sum(rate(selftest_step_total{tier="governance"}[5m])) by (step_id)
          )
```

**Alert Rules Matching SLOs:**

```yaml
# observability/prometheus/alert_rules.yaml
groups:
  - name: selftest_slo_alerts
    rules:
      - alert: SelftestAvailabilitySLOBreach
        expr: selftest:availability:success_rate:5m < 99
        for: 5m
        labels:
          severity: critical
          slo: availability
        annotations:
          summary: "Selftest availability SLO breached"
          description: "Success rate {{ $value | printf \"%.2f\" }}% is below 99% target"
          runbook_url: "https://github.com/org/repo/docs/runbooks/selftest-availability-slo.md"
          dashboard_url: "http://grafana:3000/d/selftest"

      - alert: SelftestPerformanceSLOBreach
        expr: selftest:performance:p95_duration:5m > 120
        for: 5m
        labels:
          severity: high
          slo: performance
        annotations:
          summary: "Selftest performance SLO breached"
          description: "P95 duration {{ $value | printf \"%.1f\" }}s exceeds 120s target"

      - alert: SelftestKernelFailure
        expr: increase(selftest_kernel_failures_total[5m]) > 0
        for: 0s
        labels:
          severity: critical
        annotations:
          summary: "Selftest kernel failure detected"
          description: "Kernel failure blocks CI/CD pipeline"
```

### 3. Datadog Plugin

#### 3.1 Native DogStatsD Integration

```python
# swarm/tools/metrics/backends/datadog.py
from datadog import initialize, statsd
from .base import MetricsBackend, MetricDefinition

class DatadogBackend(MetricsBackend):
    """Datadog metrics backend using DogStatsD."""

    def __init__(self, config: dict):
        self.config = config
        initialize(
            statsd_host=config.get("statsd_host", "localhost"),
            statsd_port=config.get("statsd_port", 8125),
        )
        self.default_tags = self._build_default_tags(config)

    def _build_default_tags(self, config: dict) -> list:
        tags = config.get("tags", {})
        return [f"{k}:{v}" for k, v in tags.items()]

    def _metric_name(self, name: str) -> str:
        """Convert Prometheus-style to Datadog-style."""
        # selftest_step_total -> selftest.step.total
        return name.replace("_", ".")

    def emit(self, metric: MetricDefinition) -> None:
        dd_name = self._metric_name(metric.name)
        tags = self.default_tags + [f"{k}:{v}" for k, v in metric.labels.items()]

        if metric.type == "counter":
            statsd.increment(dd_name, value=int(metric.value), tags=tags)
        elif metric.type == "gauge":
            statsd.gauge(dd_name, metric.value, tags=tags)
        elif metric.type == "histogram":
            statsd.histogram(dd_name, metric.value, tags=tags)

    def flush(self) -> None:
        statsd.flush()

    def close(self) -> None:
        pass  # DogStatsD handles cleanup

    @property
    def name(self) -> str:
        return "datadog"
```

#### 3.2 Pre-Built Datadog Dashboard

```json
// observability/datadog/dashboard.json
{
  "title": "Selftest Governance Health",
  "description": "Monitoring dashboard for selftest system SLOs and health",
  "layout_type": "ordered",
  "template_variables": [
    {
      "name": "environment",
      "default": "*",
      "prefix": "env"
    }
  ],
  "widgets": [
    {
      "definition": {
        "type": "query_value",
        "requests": [
          {
            "q": "avg:selftest.governance.pass_rate{$environment}",
            "aggregator": "last"
          }
        ],
        "title": "Governance Pass Rate",
        "precision": 1,
        "custom_unit": "%",
        "conditional_formats": [
          { "comparator": ">=", "value": 99, "palette": "white_on_green" },
          { "comparator": ">=", "value": 95, "palette": "white_on_yellow" },
          { "comparator": "<", "value": 95, "palette": "white_on_red" }
        ]
      }
    },
    {
      "definition": {
        "type": "timeseries",
        "requests": [
          {
            "q": "avg:selftest.governance.pass_rate{$environment}",
            "display_type": "line"
          }
        ],
        "title": "Pass Rate Over Time",
        "yaxis": { "min": "80", "max": "100" },
        "markers": [
          { "value": "y = 99", "display_type": "error dashed", "label": "SLO Target" }
        ]
      }
    },
    {
      "definition": {
        "type": "toplist",
        "requests": [
          {
            "q": "sum:selftest.step.failures.total{$environment} by {step_id}.as_count()"
          }
        ],
        "title": "Top Failing Steps"
      }
    },
    {
      "definition": {
        "type": "distribution",
        "requests": [
          {
            "q": "avg:selftest.run.duration_seconds{$environment}"
          }
        ],
        "title": "Run Duration Distribution"
      }
    }
  ]
}
```

#### 3.3 Datadog Monitors (Alerts as Code)

```json
// observability/datadog/monitors.json
{
  "monitors": [
    {
      "name": "Selftest Availability SLO Breach",
      "type": "metric alert",
      "query": "avg(last_5m):avg:selftest.governance.pass_rate{env:prod} < 99",
      "message": "Selftest availability SLO breached.\n\nSuccess rate {{value}}% is below 99% target.\n\n@pagerduty-platform\n\n[Runbook](https://github.com/org/repo/docs/runbooks/selftest-availability-slo.md)",
      "tags": ["team:platform", "service:selftest", "slo:availability"],
      "options": {
        "thresholds": { "critical": 99 },
        "notify_no_data": true,
        "no_data_timeframe": 10,
        "notify_audit": false,
        "require_full_window": false
      },
      "priority": 1
    },
    {
      "name": "Selftest Kernel Failure",
      "type": "metric alert",
      "query": "sum(last_5m):sum:selftest.kernel.failures.total{env:prod}.as_count() > 0",
      "message": "Selftest kernel failure detected.\n\nKernel failures block CI/CD pipeline.\n\n@pagerduty-platform-urgent",
      "tags": ["team:platform", "service:selftest", "severity:critical"],
      "options": {
        "thresholds": { "critical": 0 },
        "notify_no_data": false
      },
      "priority": 1
    },
    {
      "name": "Selftest Performance Degradation",
      "type": "metric alert",
      "query": "avg(last_5m):p95:selftest.run.duration_seconds{env:prod} > 120",
      "message": "Selftest P95 duration exceeds 120s target.\n\nCurrent P95: {{value}}s\n\n@slack-platform-alerts",
      "tags": ["team:platform", "service:selftest", "slo:performance"],
      "options": {
        "thresholds": { "critical": 120, "warning": 90 }
      },
      "priority": 2
    }
  ]
}
```

### 4. OpenTelemetry Plugin (Phase 3)

#### 4.1 OTLP Exporter

```python
# swarm/tools/metrics/backends/opentelemetry.py
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

class OTELBackend(MetricsBackend):
    """OpenTelemetry metrics backend using OTLP."""

    def __init__(self, config: dict):
        resource = Resource.create({
            "service.name": "selftest",
            "service.version": "1.0.0",
            "deployment.environment": config.get("environment", "dev"),
        })

        exporter = OTLPMetricExporter(
            endpoint=config.get("endpoint", "localhost:4317"),
            headers=config.get("headers", {}),
        )

        reader = PeriodicExportingMetricReader(
            exporter,
            export_interval_millis=config.get("export_interval_ms", 60000),
        )

        provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(provider)

        self.meter = metrics.get_meter("selftest")
        self._instruments = {}

    def _get_or_create_instrument(self, metric: MetricDefinition):
        key = (metric.name, metric.type)
        if key not in self._instruments:
            if metric.type == "counter":
                self._instruments[key] = self.meter.create_counter(
                    metric.name,
                    description=f"Selftest {metric.name}"
                )
            elif metric.type == "gauge":
                self._instruments[key] = self.meter.create_observable_gauge(
                    metric.name,
                    callbacks=[lambda: metric.value]
                )
            elif metric.type == "histogram":
                self._instruments[key] = self.meter.create_histogram(
                    metric.name,
                    description=f"Selftest {metric.name}"
                )
        return self._instruments[key]

    def emit(self, metric: MetricDefinition) -> None:
        instrument = self._get_or_create_instrument(metric)
        if metric.type == "counter":
            instrument.add(int(metric.value), metric.labels)
        elif metric.type == "histogram":
            instrument.record(metric.value, metric.labels)

    def flush(self) -> None:
        pass  # OTLP handles export timing

    def close(self) -> None:
        metrics.get_meter_provider().shutdown()

    @property
    def name(self) -> str:
        return "opentelemetry"
```

### 5. Configuration

#### 5.1 Backend Configuration File

```yaml
# swarm/config/observability_backends.yaml
# Observability backend configuration for selftest metrics
# All backends support multi-emit: a single metric can go to multiple backends

version: "1.0"

backends:
  # Local JSONL (always available, zero dependencies)
  jsonl:
    enabled: true
    path: "selftest_metrics.jsonl"
    rotate_size_mb: 10
    max_files: 5

  # Prometheus (pull-based)
  prometheus:
    enabled: false
    port: 9091
    path: /metrics

    # Kubernetes integration (optional)
    kubernetes:
      service_monitor: true
      namespace: selftest
      labels:
        release: prometheus

    # Recording rules (auto-deployed if kubernetes.enabled)
    recording_rules:
      - selftest:availability:success_rate:5m
      - selftest:performance:p95_duration:5m
      - selftest:governance:pass_rate_by_step:5m

    # Alert rules (auto-deployed if kubernetes.enabled)
    alert_rules:
      - SelftestAvailabilitySLOBreach
      - SelftestPerformanceSLOBreach
      - SelftestKernelFailure

  # Datadog (push-based via DogStatsD)
  datadog:
    enabled: false
    statsd_host: ${DD_AGENT_HOST:-localhost}
    statsd_port: ${DD_DOGSTATSD_PORT:-8125}
    api_key: ${DD_API_KEY}  # Only needed for dashboard/monitor sync

    # Default tags applied to all metrics
    tags:
      env: ${ENVIRONMENT:-dev}
      service: selftest
      team: platform

    # Auto-sync dashboards and monitors on startup
    sync_assets: false
    asset_path: observability/datadog/

  # OpenTelemetry (future - Phase 3)
  opentelemetry:
    enabled: false
    endpoint: ${OTEL_EXPORTER_OTLP_ENDPOINT:-localhost:4317}
    protocol: grpc  # or http
    headers:
      authorization: Bearer ${OTEL_TOKEN}

    # Resource attributes
    resource:
      service.name: selftest
      service.version: "1.0.0"
      deployment.environment: ${ENVIRONMENT:-dev}

    export_interval_ms: 60000

# Environment-specific overrides
environments:
  dev:
    prometheus.enabled: false
    datadog.enabled: false
    jsonl.enabled: true

  staging:
    prometheus.enabled: true
    datadog.enabled: false
    jsonl.enabled: true

  prod:
    prometheus.enabled: true
    datadog.enabled: true
    jsonl.enabled: false
```

### 6. Pre-Built Assets

#### 6.1 Directory Structure

```
observability/
  prometheus/
    recording_rules.yaml        # Pre-computed SLIs
    alert_rules.yaml            # SLO-based alerts
  grafana/
    selftest_dashboard.json     # (existing)
    selftest_dashboard.jsonnet  # (existing)
  kubernetes/
    servicemonitor.yaml         # Prometheus Operator CRD
    prometheusrule.yaml         # Alert/Recording rules CRD
  datadog/
    dashboard.json              # Dashboard as code
    monitors.json               # Monitors as code
    synthetics.json             # API tests (optional)
  otel/
    collector-config.yaml       # OTEL Collector configuration
```

#### 6.2 Installation Scripts

```bash
# scripts/install_prometheus_assets.sh
#!/bin/bash
# Deploy Prometheus observability assets to Kubernetes

NAMESPACE=${NAMESPACE:-selftest}

# Apply ServiceMonitor
kubectl apply -f observability/kubernetes/servicemonitor.yaml -n $NAMESPACE

# Apply PrometheusRule (recording + alert rules)
kubectl apply -f observability/kubernetes/prometheusrule.yaml -n $NAMESPACE

# Import Grafana dashboard
if [ -n "$GRAFANA_URL" ]; then
  curl -X POST "$GRAFANA_URL/api/dashboards/db" \
    -H "Authorization: Bearer $GRAFANA_API_KEY" \
    -H "Content-Type: application/json" \
    -d @observability/grafana/selftest_dashboard.json
fi

echo "Prometheus assets deployed to namespace: $NAMESPACE"
```

```bash
# scripts/install_datadog_assets.sh
#!/bin/bash
# Deploy Datadog observability assets

# Sync dashboard
curl -X POST "https://api.datadoghq.com/api/v1/dashboard" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
  -H "Content-Type: application/json" \
  -d @observability/datadog/dashboard.json

# Sync monitors
jq -c '.monitors[]' observability/datadog/monitors.json | while read monitor; do
  curl -X POST "https://api.datadoghq.com/api/v1/monitor" \
    -H "DD-API-KEY: ${DD_API_KEY}" \
    -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
    -H "Content-Type: application/json" \
    -d "$monitor"
done

echo "Datadog assets deployed"
```

### 7. Metric Naming Conventions

| Prometheus Style | Datadog Style | Description |
|------------------|---------------|-------------|
| `selftest_step_total` | `selftest.step.total` | Total step executions |
| `selftest_step_failures_total` | `selftest.step.failures.total` | Total step failures |
| `selftest_step_duration_seconds` | `selftest.step.duration_seconds` | Step execution time |
| `selftest_run_duration_seconds` | `selftest.run.duration_seconds` | Total run time |
| `selftest_governance_pass_rate` | `selftest.governance.pass_rate` | Governance pass % |
| `selftest_kernel_failures_total` | `selftest.kernel.failures.total` | Kernel failures |
| `selftest_degradations_total` | `selftest.degradations.total` | Degradation events |
| `selftest_degradations_active` | `selftest.degradations.active` | Active degradations |

### 8. Implementation Plan

#### Phase 1: Prometheus Enhancements (P4.6.1)

- [ ] Create `observability/prometheus/recording_rules.yaml`
- [ ] Create `observability/prometheus/alert_rules.yaml`
- [ ] Create `observability/kubernetes/servicemonitor.yaml`
- [ ] Create `observability/kubernetes/prometheusrule.yaml`
- [ ] Add installation script `scripts/install_prometheus_assets.sh`
- [ ] Document Kubernetes deployment in `observability/README.md`

#### Phase 2: Datadog Native Integration (P4.6.2)

- [ ] Implement `DatadogBackend` in `swarm/tools/metrics/backends/datadog.py`
- [ ] Create `observability/datadog/dashboard.json`
- [ ] Create `observability/datadog/monitors.json`
- [ ] Add installation script `scripts/install_datadog_assets.sh`
- [ ] Test with DogStatsD agent

#### Phase 3: OpenTelemetry Support (P4.6.3)

- [ ] Implement `OTELBackend` in `swarm/tools/metrics/backends/opentelemetry.py`
- [ ] Create `observability/otel/collector-config.yaml`
- [ ] Test with OTEL Collector → Prometheus/Datadog/Jaeger
- [ ] Document OTEL deployment patterns

### 9. Testing Strategy

#### 9.1 Unit Tests (Mock Backends)

```python
# tests/observability/test_backends.py
def test_prometheus_backend_counter():
    backend = PrometheusBackend({"port": 9999})
    metric = MetricDefinition(
        name="selftest_step_total",
        type="counter",
        value=1,
        labels={"step_id": "core-checks", "tier": "kernel"}
    )
    backend.emit(metric)
    # Verify metric was registered
    assert "selftest_step_total" in REGISTRY._names_to_collectors

def test_datadog_backend_metric_name_conversion():
    backend = DatadogBackend({"statsd_host": "localhost"})
    assert backend._metric_name("selftest_step_total") == "selftest.step.total"

def test_backend_manager_multi_emit():
    config = {
        "jsonl": {"enabled": True},
        "prometheus": {"enabled": True},
    }
    manager = BackendManager(config)
    assert len(manager.backends) == 2
```

#### 9.2 Integration Tests (Docker Compose)

```yaml
# tests/observability/docker-compose.yml
version: "3.8"
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

  selftest:
    build: ../..
    environment:
      - SELFTEST_METRICS_BACKEND=prometheus
      - SELFTEST_METRICS_PORT=9091
    depends_on:
      - prometheus
```

#### 9.3 E2E Tests (Sandbox Accounts)

For Datadog integration:
- Use Datadog sandbox account with test API key
- Verify dashboard creation via API
- Verify monitor creation and alert triggering
- Clean up test assets after each run

## Consequences

### Positive

1. **Zero-Config Experience**: New users can enable Prometheus or Datadog with a single environment variable
2. **Vendor-Native Assets**: Teams get dashboards and alerts that follow vendor best practices
3. **SLO Alignment**: Pre-built alerts match the SLOs defined in `observability/slos/selftest_slos.yaml`
4. **Multi-Backend Support**: Organizations can emit to multiple backends simultaneously
5. **Future-Proof**: OpenTelemetry support provides path to modern observability stacks

### Negative

1. **Increased Complexity**: More code to maintain across multiple backends
2. **Dependency Growth**: Optional dependencies on `datadog`, `opentelemetry-*` packages
3. **Asset Drift**: Pre-built dashboards/alerts may become stale if not updated with metric changes

### Risks

| Risk | Mitigation |
|------|------------|
| Datadog API changes break asset sync | Version-pin API, validate assets in CI |
| OTEL spec changes | Use stable OTEL SDK versions only |
| Prometheus recording rules performance | Benchmark rules, use appropriate intervals |
| Metric cardinality explosion | Limit label values, document best practices |

## References

- `docs/SELFTEST_OBSERVABILITY_SPEC.md` - Complete observability specification
- `observability/README.md` - Quick start guide
- `observability/slos/selftest_slos.yaml` - SLO definitions
- `swarm/tools/selftest_metrics.py` - Current metrics implementation
