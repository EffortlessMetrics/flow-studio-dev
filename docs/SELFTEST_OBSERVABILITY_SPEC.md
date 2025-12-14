# Selftest Observability Specification

> **Status**: Complete observability design for selftest system
>
> **Version**: 1.0
>
> **Last Updated**: 2025-12-01

---

## Table of Contents

1. [Overview](#overview)
2. [Metrics Definitions](#1-metrics-definitions)
3. [Data Collection & Emission](#2-data-collection--emission)
4. [Dashboard Specifications](#3-dashboard-specifications)
5. [SLOs & Service Level Indicators](#4-slos--service-level-indicators)
6. [Alert Rules](#5-alert-rules)
7. [Integration with External Platforms](#6-integration-with-external-platforms)
8. [Data Retention & Cleanup](#7-data-retention--cleanup)
9. [Dashboard Examples](#8-dashboard-examples-yamljson-snippets)
10. [Testing the Observability System](#9-testing-the-observability-system)

---

## Overview

The selftest system is a **layered, degradable governance framework**. This observability specification defines how to monitor selftest health across environments (dev, staging, prod) with appropriate alerting and dashboards.

### Design Principles

1. **Tier-aware monitoring**: Different tiers (KERNEL/GOVERNANCE/OPTIONAL) have different severity thresholds
2. **Environment-specific SLOs**: Dev is best-effort, staging allows degradation, prod requires perfection
3. **Actionable metrics**: Every metric has a clear remediation path
4. **Minimal overhead**: Metric emission adds < 10ms per step

### Architecture Overview

```
┌──────────────────┐
│  Selftest Step   │
│   Execution      │
└────────┬─────────┘
         │
         ├─── Start: emit counter + timestamp
         │
         ├─── Execute: run command, capture output
         │
         ├─── End: emit duration + status + exit_code
         │
         └─── On Failure: emit degradation entry (if degraded mode)
                │
                v
    ┌───────────────────────┐
    │  Metrics Collection   │
    │  - Local: JSONL       │
    │  - Prometheus         │
    │  - CloudWatch         │
    │  - Datadog            │
    └───────────┬───────────┘
                │
                v
    ┌───────────────────────┐
    │   Dashboard Query     │
    │   - Grafana           │
    │   - Flow Studio       │
    │   - Datadog           │
    └───────────┬───────────┘
                │
                v
    ┌───────────────────────┐
    │   Alert Evaluation    │
    │   - Prometheus rules  │
    │   - Datadog monitors  │
    │   - PagerDuty         │
    └───────────────────────┘
```

---

## 1. Metrics Definitions

### 1.1 Core Metrics

#### `selftest_step_total`

**Type**: Counter

**Description**: Total number of selftest step executions

**Unit**: steps (count)

**Labels**:
- `step_id` (string): Step identifier (e.g., `core-checks`, `agents-governance`)
- `environment` (string): Execution environment (`dev`, `staging`, `prod`)
- `tier` (string): Step tier (`kernel`, `governance`, `optional`)

**Collection Point**: `SelfTestRunner.run_step()`, emitted at step start

**Target Environment**: All (dev, staging, prod)

**Example**:
```
selftest_step_total{step_id="core-checks", environment="dev", tier="kernel"} 142
selftest_step_total{step_id="agents-governance", environment="staging", tier="governance"} 89
```

**Queries**:
- Total runs per step: `rate(selftest_step_total[5m])`
- Most-run steps: `topk(5, sum by (step_id) (selftest_step_total))`

---

#### `selftest_step_failures_total`

**Type**: Counter

**Description**: Total number of selftest step failures

**Unit**: failures (count)

**Labels**:
- `step_id` (string): Step identifier
- `severity` (string): Failure severity (`critical`, `warning`, `info`)
- `environment` (string): Execution environment
- `tier` (string): Step tier
- `exit_code` (int): Command exit code

**Collection Point**: `SelfTestRunner.run_step()`, emitted when `result.passed == False`

**Target Environment**: All (dev, staging, prod)

**Example**:
```
selftest_step_failures_total{step_id="core-checks", severity="critical", environment="prod", tier="kernel", exit_code="1"} 3
selftest_step_failures_total{step_id="bdd", severity="warning", environment="dev", tier="governance", exit_code="1"} 12
```

**Queries**:
- Failure rate per step: `rate(selftest_step_failures_total[5m]) / rate(selftest_step_total[5m])`
- Top failing steps: `topk(5, sum by (step_id) (selftest_step_failures_total))`

---

#### `selftest_step_duration_seconds`

**Type**: Histogram

**Description**: Execution time for each selftest step

**Unit**: seconds

**Buckets**: `[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]`

**Labels**:
- `step_id` (string): Step identifier
- `environment` (string): Execution environment
- `tier` (string): Step tier

**Collection Point**: `SelfTestRunner.run_step()`, emitted at step completion

**Target Environment**: All (dev, staging, prod)

**Example**:
```
# Histogram buckets
selftest_step_duration_seconds_bucket{step_id="core-checks", environment="dev", tier="kernel", le="5.0"} 98
selftest_step_duration_seconds_bucket{step_id="core-checks", environment="dev", tier="kernel", le="10.0"} 142
selftest_step_duration_seconds_sum{step_id="core-checks", environment="dev", tier="kernel"} 1024.5
selftest_step_duration_seconds_count{step_id="core-checks", environment="dev", tier="kernel"} 142
```

**Queries**:
- P50 latency: `histogram_quantile(0.5, rate(selftest_step_duration_seconds_bucket[5m]))`
- P99 latency: `histogram_quantile(0.99, rate(selftest_step_duration_seconds_bucket[5m]))`
- Slowest steps: `topk(5, avg by (step_id) (rate(selftest_step_duration_seconds_sum[5m]) / rate(selftest_step_duration_seconds_count[5m])))`

---

#### `selftest_governance_pass_rate`

**Type**: Gauge

**Description**: Percentage of governance steps passing (0-100)

**Unit**: percentage

**Labels**:
- `environment` (string): Execution environment

**Collection Point**: `SelfTestRunner.run()`, computed from results summary

**Target Environment**: All (dev, staging, prod)

**Example**:
```
selftest_governance_pass_rate{environment="prod"} 100.0
selftest_governance_pass_rate{environment="staging"} 95.0
selftest_governance_pass_rate{environment="dev"} 85.0
```

**Queries**:
- Pass rate over time: `selftest_governance_pass_rate`
- Drop detection: `delta(selftest_governance_pass_rate[5m]) < -10`

---

### 1.2 Degradation Metrics

#### `selftest_degradations_active`

**Type**: Gauge

**Description**: Number of currently active degradations (failures in degraded mode)

**Unit**: degradations (count)

**Labels**:
- `step_id` (string): Step identifier
- `severity` (string): Degradation severity
- `environment` (string): Execution environment
- `tier` (string): Step tier (only `governance` or `optional` steps log degradations)

**Collection Point**: `SelfTestRunner.log_degradation()`, incremented on failure, decremented on subsequent pass

**Target Environment**: All (dev, staging, prod)

**Example**:
```
selftest_degradations_active{step_id="agents-governance", severity="warning", environment="dev", tier="governance"} 1
selftest_degradations_active{step_id="bdd", severity="warning", environment="staging", tier="governance"} 0
```

**Queries**:
- Total active degradations: `sum(selftest_degradations_active)`
- Per-step degradations: `selftest_degradations_active`

---

#### `selftest_degradations_total`

**Type**: Counter

**Description**: Total number of degradations logged across all runs

**Unit**: events (count)

**Labels**:
- `step_id` (string): Step identifier
- `severity` (string): Degradation severity
- `environment` (string): Execution environment
- `tier` (string): Step tier

**Collection Point**: `SelfTestRunner.log_degradation()`, emitted on each degradation

**Target Environment**: All (dev, staging, prod)

**Example**:
```
selftest_degradations_total{step_id="agents-governance", severity="warning", environment="dev", tier="governance"} 15
selftest_degradations_total{step_id="policy-tests", severity="warning", environment="staging", tier="governance"} 3
```

**Queries**:
- Degradation rate: `rate(selftest_degradations_total[5m])`
- Most-degraded steps: `topk(5, sum by (step_id) (selftest_degradations_total))`

---

### 1.3 System Health Metrics

#### `selftest_kernel_failures_total`

**Type**: Counter

**Description**: Total number of KERNEL-tier step failures (always fatal)

**Unit**: failures (count)

**Labels**:
- `environment` (string): Execution environment

**Collection Point**: `SelfTestRunner.run()`, incremented when any KERNEL step fails

**Target Environment**: All (dev, staging, prod)

**Example**:
```
selftest_kernel_failures_total{environment="prod"} 0
selftest_kernel_failures_total{environment="dev"} 2
```

**Queries**:
- Kernel failure rate: `rate(selftest_kernel_failures_total[5m])`
- Prod kernel failures (should be zero): `selftest_kernel_failures_total{environment="prod"}`

---

#### `selftest_run_overall_status`

**Type**: Gauge

**Description**: Current overall selftest health status

**Unit**: status code (0 = BROKEN, 0.5 = DEGRADED, 1 = HEALTHY)

**Labels**:
- `status` (string): Status label (`HEALTHY`, `DEGRADED`, `BROKEN`)
- `environment` (string): Execution environment

**Collection Point**: `SelfTestRunner.run()`, computed from final exit code and degradation count

**Target Environment**: All (dev, staging, prod)

**Computation**:
- `HEALTHY` (1.0): All steps pass or only non-blocking failures
- `DEGRADED` (0.5): KERNEL passes, GOVERNANCE/OPTIONAL failed
- `BROKEN` (0.0): KERNEL failed

**Example**:
```
selftest_run_overall_status{status="HEALTHY", environment="prod"} 1
selftest_run_overall_status{status="DEGRADED", environment="staging"} 0.5
selftest_run_overall_status{status="BROKEN", environment="dev"} 0
```

**Queries**:
- Current status: `selftest_run_overall_status`
- Alert on broken: `selftest_run_overall_status{status="BROKEN"} == 0`

---

### 1.4 Acceptance Criteria Metrics

#### `selftest_ac_pass_rate`

**Type**: Gauge

**Description**: Pass rate for a specific acceptance criteria ID (0-100)

**Unit**: percentage

**Labels**:
- `ac_id` (string): Acceptance criteria ID (e.g., `AC-SELFTEST-KERNEL-FAST`)
- `environment` (string): Execution environment

**Collection Point**: `SelfTestRunner.run()`, computed by mapping step results to AC IDs

**Target Environment**: All (dev, staging, prod)

**Example**:
```
selftest_ac_pass_rate{ac_id="AC-SELFTEST-KERNEL-FAST", environment="prod"} 100.0
selftest_ac_pass_rate{ac_id="AC-SELFTEST-DEGRADATION-TRACKED", environment="dev"} 90.0
```

**Queries**:
- Per-AC pass rate: `selftest_ac_pass_rate`
- Failing ACs: `selftest_ac_pass_rate < 100`

---

#### `selftest_ac_failures_total`

**Type**: Counter

**Description**: Total failures for a specific acceptance criteria ID

**Unit**: failures (count)

**Labels**:
- `ac_id` (string): Acceptance criteria ID
- `environment` (string): Execution environment

**Collection Point**: `SelfTestRunner.run()`, incremented when any step covering this AC fails

**Target Environment**: All (dev, staging, prod)

**Example**:
```
selftest_ac_failures_total{ac_id="AC-SELFTEST-KERNEL-FAST", environment="prod"} 0
selftest_ac_failures_total{ac_id="AC-SELFTEST-DEGRADATION-TRACKED", environment="dev"} 8
```

**Queries**:
- AC failure rate: `rate(selftest_ac_failures_total[5m])`
- Most-failing ACs: `topk(5, sum by (ac_id) (selftest_ac_failures_total))`

---

### 1.5 Performance Metrics

#### `selftest_run_duration_seconds`

**Type**: Histogram

**Description**: Total execution time for an entire selftest run

**Unit**: seconds

**Buckets**: `[5.0, 10.0, 15.0, 30.0, 60.0, 120.0, 300.0, 600.0]`

**Labels**:
- `mode` (string): Selftest mode (`strict`, `degraded`, `kernel-only`)
- `environment` (string): Execution environment

**Collection Point**: `SelfTestRunner.run()`, emitted at run completion

**Target Environment**: All (dev, staging, prod)

**Example**:
```
selftest_run_duration_seconds_bucket{mode="strict", environment="dev", le="30.0"} 142
selftest_run_duration_seconds_sum{mode="strict", environment="dev"} 3500.5
selftest_run_duration_seconds_count{mode="strict", environment="dev"} 142
```

**Queries**:
- P99 run time: `histogram_quantile(0.99, rate(selftest_run_duration_seconds_bucket[5m]))`
- Slow runs: `rate(selftest_run_duration_seconds_sum[5m]) / rate(selftest_run_duration_seconds_count[5m]) > 60`

---

## 2. Data Collection & Emission

### 2.1 Instrumentation Architecture

Metrics are emitted at three key points in the selftest lifecycle:

```python
class SelfTestRunner:
    def run_step(self, step: SelfTestStep) -> SelfTestResult:
        # 1. Step start: emit counter
        emit_metric(
            name="selftest_step_total",
            value=1,
            labels={
                "step_id": step.id,
                "environment": self.environment,
                "tier": step.tier.value,
            },
        )

        # 2. Execute step
        start_time = time.time()
        result = subprocess.run(step.full_command(), ...)
        duration = time.time() - start_time

        # 3. Step end: emit duration + status
        emit_metric(
            name="selftest_step_duration_seconds",
            value=duration,
            labels={
                "step_id": step.id,
                "environment": self.environment,
                "tier": step.tier.value,
            },
            type="histogram",
        )

        if not result.passed:
            # 4. On failure: emit failure counter
            emit_metric(
                name="selftest_step_failures_total",
                value=1,
                labels={
                    "step_id": step.id,
                    "severity": step.severity.value,
                    "environment": self.environment,
                    "tier": step.tier.value,
                    "exit_code": result.exit_code,
                },
            )

            # 5. If degraded mode: log degradation
            if self.degraded and step.tier != SelfTestTier.KERNEL:
                self.log_degradation(result)
                emit_metric(
                    name="selftest_degradations_total",
                    value=1,
                    labels={
                        "step_id": step.id,
                        "severity": step.severity.value,
                        "environment": self.environment,
                        "tier": step.tier.value,
                    },
                )

        return result
```

---

### 2.2 Transport Mechanisms

#### 2.2.1 Local JSONL (Default)

**File Path**: `swarm/runs/<run-id>/build/selftest_metrics.jsonl`

**Format**: One JSON object per line (JSONL)

**Schema**:
```json
{
  "timestamp": "2025-12-01T10:15:22.123456+00:00",
  "metric_name": "selftest_step_duration_seconds",
  "metric_type": "histogram",
  "value": 3.456,
  "labels": {
    "step_id": "core-checks",
    "environment": "dev",
    "tier": "kernel"
  }
}
```

**Implementation**:
```python
def emit_metric_local(name: str, value: float, labels: dict, metric_type: str = "counter"):
    """Write metric to local JSONL file."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metric_name": name,
        "metric_type": metric_type,
        "value": value,
        "labels": labels,
    }

    with open(METRICS_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
```

**Advantages**:
- Zero external dependencies
- Works immediately on clone
- Git-ignored, doesn't pollute repo
- Human-readable for debugging

**Limitations**:
- No aggregation or querying
- Manual parsing required

---

#### 2.2.2 Prometheus OpenMetrics

**Endpoint**: `http://localhost:9091/metrics` (configurable via `SELFTEST_METRICS_PORT`)

**Format**: OpenMetrics text format

**Example**:
```
# HELP selftest_step_total Total number of selftest step executions
# TYPE selftest_step_total counter
selftest_step_total{step_id="core-checks",environment="dev",tier="kernel"} 142

# HELP selftest_step_duration_seconds Execution time for each selftest step
# TYPE selftest_step_duration_seconds histogram
selftest_step_duration_seconds_bucket{step_id="core-checks",environment="dev",tier="kernel",le="5.0"} 98
selftest_step_duration_seconds_bucket{step_id="core-checks",environment="dev",tier="kernel",le="+Inf"} 142
selftest_step_duration_seconds_sum{step_id="core-checks",environment="dev",tier="kernel"} 1024.5
selftest_step_duration_seconds_count{step_id="core-checks",environment="dev",tier="kernel"} 142
```

**Implementation**:
```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Define metrics
step_total = Counter(
    "selftest_step_total",
    "Total number of selftest step executions",
    ["step_id", "environment", "tier"],
)

step_duration = Histogram(
    "selftest_step_duration_seconds",
    "Execution time for each selftest step",
    ["step_id", "environment", "tier"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

# Start metrics server (non-blocking)
if os.getenv("SELFTEST_METRICS_ENABLED", "false") == "true":
    port = int(os.getenv("SELFTEST_METRICS_PORT", "9091"))
    start_http_server(port)

# Emit metrics
step_total.labels(step_id=step.id, environment=env, tier=step.tier.value).inc()
step_duration.labels(step_id=step.id, environment=env, tier=step.tier.value).observe(duration)
```

**Configuration**:
```bash
# Enable Prometheus metrics
export SELFTEST_METRICS_ENABLED=true
export SELFTEST_METRICS_PORT=9091

# Run selftest
make selftest
```

**Scrape Config** (Prometheus):
```yaml
scrape_configs:
  - job_name: 'selftest'
    static_configs:
      - targets: ['localhost:9091']
    scrape_interval: 15s
```

---

#### 2.2.3 AWS CloudWatch

**Implementation**:
```python
import boto3
from datetime import datetime, timezone

cloudwatch = boto3.client('cloudwatch')

def emit_metric_cloudwatch(name: str, value: float, labels: dict):
    """Emit metric to CloudWatch."""
    dimensions = [
        {"Name": k, "Value": v} for k, v in labels.items()
    ]

    cloudwatch.put_metric_data(
        Namespace='Selftest',
        MetricData=[
            {
                'MetricName': name,
                'Dimensions': dimensions,
                'Value': value,
                'Timestamp': datetime.now(timezone.utc),
                'Unit': 'Count',  # or 'Seconds' for duration
            }
        ]
    )
```

**Configuration**:
```bash
# Enable CloudWatch
export SELFTEST_METRICS_BACKEND=cloudwatch
export AWS_REGION=us-east-1

# Run selftest
make selftest
```

---

#### 2.2.4 Datadog

**Implementation**:
```python
from datadog import initialize, statsd

# Initialize Datadog
options = {
    'api_key': os.getenv('DD_API_KEY'),
    'app_key': os.getenv('DD_APP_KEY'),
}
initialize(**options)

def emit_metric_datadog(name: str, value: float, labels: dict, metric_type: str):
    """Emit metric to Datadog."""
    tags = [f"{k}:{v}" for k, v in labels.items()]

    if metric_type == "counter":
        statsd.increment(name, value=value, tags=tags)
    elif metric_type == "gauge":
        statsd.gauge(name, value, tags=tags)
    elif metric_type == "histogram":
        statsd.histogram(name, value, tags=tags)
```

**Configuration**:
```bash
# Enable Datadog
export SELFTEST_METRICS_BACKEND=datadog
export DD_API_KEY=<your-api-key>
export DD_APP_KEY=<your-app-key>

# Run selftest
make selftest
```

---

### 2.3 Environment Detection

The selftest system auto-detects the environment and chooses the appropriate metric backend:

```python
def detect_metric_backend() -> str:
    """
    Detect which metrics backend to use based on environment variables.

    Priority:
    1. SELFTEST_METRICS_BACKEND (explicit override)
    2. Auto-detection:
       - PROMETHEUS_MULTIPROC_DIR → prometheus
       - DD_API_KEY → datadog
       - AWS_REGION → cloudwatch
    3. Default: local JSONL
    """
    backend = os.getenv("SELFTEST_METRICS_BACKEND")
    if backend:
        return backend

    if os.getenv("PROMETHEUS_MULTIPROC_DIR"):
        return "prometheus"
    if os.getenv("DD_API_KEY"):
        return "datadog"
    if os.getenv("AWS_REGION"):
        return "cloudwatch"

    return "local"
```

---

## 3. Dashboard Specifications

### 3.1 Developer Dashboard (Flow Studio Integration)

**Title**: Selftest Status at a Glance

**Location**: Flow Studio UI → Selftest tab

**Refresh Rate**: 10 seconds

**Audience**: Developers working locally

**Purpose**: Quick visual feedback on selftest health

#### Panels

**Panel 1: Status Banner**

- **Type**: Single stat with color indicator
- **Query**: `selftest_run_overall_status`
- **Display**:
  - `HEALTHY` → Green banner, "✓ All systems go"
  - `DEGRADED` → Yellow banner, "⚠ Governance issues detected"
  - `BROKEN` → Red banner, "✗ Kernel failure (blocking)"
- **Thresholds**:
  - Green: `value == 1`
  - Yellow: `value == 0.5`
  - Red: `value == 0`

**Panel 2: Step Pass/Fail Bar Chart**

- **Type**: Horizontal bar chart
- **Query**: `count(selftest_step_total) by (tier, step_id)`
- **X-axis**: Step count
- **Y-axis**: Step ID
- **Color**: Green (pass), Red (fail)
- **Groups**: Separate bars for KERNEL / GOVERNANCE / OPTIONAL

**Panel 3: Active Degradations List**

- **Type**: Table
- **Query**: `selftest_degradations_active > 0`
- **Columns**:
  - Step ID
  - Severity
  - Timestamp (last failure)
  - Remediation command
- **Limit**: Top 5 recent
- **Sort**: By timestamp DESC

**Panel 4: Execution Time Sparkline**

- **Type**: Sparkline (small line chart)
- **Query**: `sum(rate(selftest_run_duration_seconds_sum[5m])) / sum(rate(selftest_run_duration_seconds_count[5m]))`
- **Time Range**: Last 7 runs
- **Y-axis**: Duration (seconds)
- **Threshold Line**: 30s (expected baseline)

---

### 3.2 Platform Dashboard (Grafana)

**Title**: Selftest Governance Health

**Location**: Grafana dashboard (import JSON)

**Refresh Rate**: 1 minute

**Time Range**: Last 7 days (default)

**Audience**: Platform engineers, SREs

**Purpose**: Multi-environment monitoring and trend analysis

#### Panels

**Panel 1: Governance Pass Rate (Line Chart)**

- **Type**: Time series line chart
- **Query**: `selftest_governance_pass_rate`
- **Y-axis**: Pass rate (0-100%)
- **X-axis**: Time
- **Series**: One line per environment (dev, staging, prod)
- **Thresholds**:
  - Green zone: 95-100%
  - Yellow zone: 90-95%
  - Red zone: <90%

**Panel 2: Failures Heatmap**

- **Type**: Heatmap
- **Query**: `sum by (step_id, severity) (rate(selftest_step_failures_total[1h]))`
- **X-axis**: Time (buckets: 1 hour)
- **Y-axis**: Step ID
- **Color**: Failure rate (red = high, green = low)
- **Time Range**: Last 7 days

**Panel 3: AC Pass Rates Table**

- **Type**: Table
- **Query**: `selftest_ac_pass_rate`
- **Columns**:
  - AC ID
  - Pass Rate (last 24h)
  - Status (✓ if 100%, ⚠ if <100%)
- **Filter**: All 6 ACs
- **Sort**: By pass rate ASC (failures first)

**Panel 4: Current Degradations Single Stat**

- **Type**: Single stat
- **Query**: `sum(selftest_degradations_active)`
- **Display**: Large number with color
- **Thresholds**:
  - Green: `value == 0`
  - Red: `value > 0`
- **Link**: Click to open degradations table

**Panel 5: Step Execution Time Histogram**

- **Type**: Histogram
- **Query**: `histogram_quantile(0.99, rate(selftest_step_duration_seconds_bucket[5m]))`
- **X-axis**: Duration (seconds)
- **Y-axis**: Frequency
- **Buckets**: Auto (Grafana default)

---

### 3.3 Incident Response Dashboard

**Title**: Selftest Incident Overview

**Location**: Grafana dashboard (import JSON) or PagerDuty UI

**Refresh Rate**: Real-time (10 seconds)

**Audience**: On-call SRE responding to selftest alert

**Purpose**: Rapid diagnosis and remediation guidance

#### Panels

**Panel 1: Failed Step Details**

- **Type**: Table
- **Query**: `selftest_step_failures_total{environment="prod"} > 0`
- **Columns**:
  - Step ID
  - Tier
  - Exit Code
  - Last Failure Time
  - Link to Fix Guide (e.g., `/docs/SELFTEST_SYSTEM.md#troubleshooting`)
- **Limit**: All failures (no limit)

**Panel 2: AC IDs Affected**

- **Type**: List
- **Query**: `selftest_ac_failures_total{environment="prod"} > 0`
- **Display**: List of AC IDs with failure count
- **Link**: Click AC ID to open AC documentation

**Panel 3: Degradation Message & Remediation**

- **Type**: Text panel
- **Query**: Read from `selftest_degradations.log` (last entry)
- **Display**:
  - Degradation message
  - Suggested remediation command
  - Timestamp

**Panel 4: Time Since Last Success**

- **Type**: Single stat
- **Query**: `time() - max(selftest_run_overall_status{status="HEALTHY"} @ timestamp)`
- **Display**: Duration (e.g., "2h 15m")
- **Thresholds**:
  - Green: < 1 hour
  - Yellow: 1-4 hours
  - Red: > 4 hours

**Panel 5: Kernel vs Governance Failure Indicator**

- **Type**: Status list
- **Query**:
  - `selftest_kernel_failures_total{environment="prod"}`
  - `selftest_governance_pass_rate{environment="prod"} < 100`
- **Display**:
  - `KERNEL FAILURE` (red) if kernel failed
  - `GOVERNANCE FAILURE` (yellow) if governance failed
  - `HEALTHY` (green) if all pass

---

## 4. SLOs & Service Level Indicators

### 4.1 Dev Environment

**Purpose**: Fast iteration, best-effort quality

#### SLI: Selftest Availability

**Definition**: Percentage of time selftest can run without environment errors

**Measurement**: `(successful_runs + failed_runs) / total_run_attempts`

**Target**: 99% (allow 7.2 min/week downtime)

**Rationale**: Dev environment can tolerate harness issues (outdated deps, etc.)

**Alert**: None (dev is best-effort)

---

#### SLI: Kernel Pass Rate

**Definition**: Percentage of kernel steps passing

**Measurement**: `(kernel_passes) / (kernel_passes + kernel_failures)`

**Target**: 95% (allow occasional transient failures)

**Alert**: Warning if <95% for 1+ hour (Slack notification)

---

### 4.2 Staging Environment

**Purpose**: Pre-production validation, governance testing

#### SLI: Governance Steps Passing

**Definition**: Percentage of governance steps passing

**Measurement**: `selftest_governance_pass_rate{environment="staging"}`

**Target**: 95% (allow 36 min/week degradation)

**Alert**: Page on-call if <95% for 10+ minutes

**Error Budget**: 5% (approximately 2 failures per 40 runs)

---

#### SLI: Kernel Availability

**Definition**: Kernel must always pass in staging

**Measurement**: `selftest_kernel_failures_total{environment="staging"} == 0`

**Target**: 99.9% (allow 0.72 min/week failures)

**Alert**: Page immediately on kernel failure

---

### 4.3 Production Environment

**Purpose**: Gate all merges, enforce quality

#### SLI: All Steps Passing

**Definition**: Kernel + Governance steps must pass

**Measurement**: `selftest_governance_pass_rate{environment="prod"} == 100`

**Target**: 99.9% (allow 0.72 min/week failures)

**Alert**: Page immediately on any failure (kernel or governance)

---

#### SLI: Selftest Latency

**Definition**: P99 execution time for full selftest suite

**Measurement**: `histogram_quantile(0.99, rate(selftest_run_duration_seconds_bucket{environment="prod"}[5m]))`

**Target**: < 60s (P99)

**Alert**: Warning if P99 > 90s for 5+ minutes

**Rationale**: Selftest should not become a bottleneck in CI/CD pipeline

---

### 4.4 SLO Summary Table

| Environment | SLI | Target | Error Budget | Alert Threshold | Alert Destination |
|-------------|-----|--------|--------------|-----------------|-------------------|
| Dev | Selftest Availability | 99% | 1% (7.2 min/week) | N/A | None |
| Dev | Kernel Pass Rate | 95% | 5% (36 min/week) | <95% for 1h | Slack (warning) |
| Staging | Governance Passing | 95% | 5% (36 min/week) | <95% for 10m | PagerDuty (page) |
| Staging | Kernel Availability | 99.9% | 0.1% (0.72 min/week) | Any failure | PagerDuty (page) |
| Prod | All Steps Passing | 99.9% | 0.1% (0.72 min/week) | Any failure | PagerDuty (page) |
| Prod | Selftest Latency (P99) | <60s | N/A | >90s for 5m | Slack (warning) |

---

## 5. Alert Rules

### 5.1 Immediate Alerts (Page On-Call)

#### Alert 1: Kernel Failure in Prod

**Severity**: Critical

**Condition**:
```promql
selftest_kernel_failures_total{environment="prod"} > 0
```

**Duration**: Immediate (0s)

**Action**: Page on-call via PagerDuty

**Runbook**: `docs/runbooks/selftest-kernel-failure.md`

**Message**:
```
🚨 CRITICAL: Selftest kernel failure in PROD
Environment: prod
Failed steps: [list from selftest_step_failures_total]
Runbook: https://github.com/org/repo/docs/runbooks/selftest-kernel-failure.md
```

---

#### Alert 2: Multiple Governance Failures in Staging

**Severity**: High

**Condition**:
```promql
sum(rate(selftest_step_failures_total{environment="staging", tier="governance"}[5m])) > 2
```

**Duration**: 5 minutes

**Action**: Page on-call via PagerDuty

**Runbook**: `docs/runbooks/selftest-governance-failures.md`

**Message**:
```
⚠️ HIGH: Multiple selftest governance failures in STAGING
Environment: staging
Failure rate: [rate]
Runbook: https://github.com/org/repo/docs/runbooks/selftest-governance-failures.md
```

---

#### Alert 3: Selftest Unavailable in Prod

**Severity**: Critical

**Condition**:
```promql
absent(selftest_run_overall_status{environment="prod"})
```

**Duration**: 10 minutes

**Action**: Page on-call via PagerDuty

**Runbook**: `docs/runbooks/selftest-unavailable.md`

**Message**:
```
🚨 CRITICAL: Selftest metrics missing in PROD
Environment: prod
Duration: 10+ minutes
Possible cause: Harness issue, metrics collection failure
Runbook: https://github.com/org/repo/docs/runbooks/selftest-unavailable.md
```

---

### 5.2 Warning Alerts (Slack Notification)

#### Alert 4: Dev Kernel Failure (Long Duration)

**Severity**: Warning

**Condition**:
```promql
selftest_kernel_failures_total{environment="dev"} > 0
```

**Duration**: 1 hour

**Action**: Post to Slack `#dev-notifications`

**Message**:
```
💡 WARNING: Selftest kernel failing in DEV for 1+ hour
Environment: dev
Failed step: [step_id]
Recommendation: Run `make selftest-doctor` to diagnose
```

---

#### Alert 5: Staging Governance Failure

**Severity**: Warning

**Condition**:
```promql
selftest_governance_pass_rate{environment="staging"} < 100
```

**Duration**: 5 minutes

**Action**: Create GitHub issue, post to Slack

**Message**:
```
⚠️ WARNING: Selftest governance failure in STAGING
Environment: staging
Pass rate: [percentage]%
Failed steps: [list]
Action: Track in GitHub issue #[issue_number]
```

---

#### Alert 6: Slow Selftest Execution

**Severity**: Warning

**Condition**:
```promql
histogram_quantile(0.99, rate(selftest_run_duration_seconds_bucket[5m])) > 90
```

**Duration**: 5 minutes

**Action**: Post to Slack `#platform-notifications`

**Message**:
```
🐢 WARNING: Selftest execution slow (P99 > 90s)
Environment: [env]
P99 duration: [duration]s
Recommendation: Investigate slow steps with `make selftest --verbose`
```

---

### 5.3 Info Alerts (Logging Only)

#### Alert 7: Dev/Staging Slow Step

**Severity**: Info

**Condition**:
```promql
histogram_quantile(0.99, rate(selftest_step_duration_seconds_bucket[5m])) > 30
```

**Duration**: 10 minutes

**Action**: Log to CloudWatch/Datadog (no notification)

**Message**:
```
ℹ️ INFO: Slow selftest step detected
Environment: [env]
Step: [step_id]
P99 duration: [duration]s
```

---

#### Alert 8: Increasing Step Duration Trend

**Severity**: Info

**Condition**:
```promql
deriv(avg_over_time(selftest_step_duration_seconds_sum[1h])[7d:1h]) > 0.1
```

**Duration**: 7 days

**Action**: Weekly report to `#platform-weekly`

**Message**:
```
📈 INFO: Selftest step duration increasing over 7 days
Step: [step_id]
Trend: +[percentage]% per day
```

---

### 5.4 Alert Configuration Examples

#### Prometheus Alerting Rules

**File**: `prometheus/alerts/selftest.yml`

```yaml
groups:
  - name: selftest_critical
    interval: 15s
    rules:
      - alert: SelftestKernelFailureProd
        expr: selftest_kernel_failures_total{environment="prod"} > 0
        for: 0s
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Selftest kernel failure in PROD"
          description: "Kernel step failed in prod. This blocks all merges."
          runbook_url: "https://github.com/org/repo/docs/runbooks/selftest-kernel-failure.md"
          dashboard_url: "https://grafana.example.com/d/selftest-incident"

      - alert: SelftestUnavailableProd
        expr: absent(selftest_run_overall_status{environment="prod"})
        for: 10m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Selftest metrics missing in PROD"
          description: "No selftest metrics received for 10+ minutes."
          runbook_url: "https://github.com/org/repo/docs/runbooks/selftest-unavailable.md"

  - name: selftest_warnings
    interval: 1m
    rules:
      - alert: SelftestGovernanceFailureStaging
        expr: selftest_governance_pass_rate{environment="staging"} < 100
        for: 5m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "Selftest governance failure in STAGING"
          description: "Pass rate: {{ $value }}%"
          dashboard_url: "https://grafana.example.com/d/selftest-platform"
```

---

#### Datadog Monitor Configuration

**File**: `datadog/monitors/selftest.json`

```json
{
  "name": "Selftest Kernel Failure in Prod",
  "type": "metric alert",
  "query": "sum(last_5m):sum:selftest.kernel_failures.total{environment:prod} > 0",
  "message": "🚨 CRITICAL: Selftest kernel failure in PROD\n\n@pagerduty-platform\n\n[Runbook](https://github.com/org/repo/docs/runbooks/selftest-kernel-failure.md)",
  "tags": ["team:platform", "service:selftest", "env:prod"],
  "options": {
    "thresholds": {
      "critical": 0
    },
    "notify_no_data": true,
    "no_data_timeframe": 10,
    "notify_audit": false,
    "require_full_window": false,
    "new_group_delay": 60,
    "include_tags": true,
    "escalation_message": "Selftest kernel failure persisting. Escalate to senior SRE."
  },
  "priority": 1
}
```

---

## 6. Integration with External Platforms

### 6.1 Prometheus Integration

**Setup**:

1. Install `prometheus_client`:
   ```bash
   uv pip install prometheus-client
   ```

2. Enable Prometheus metrics:
   ```bash
   export SELFTEST_METRICS_BACKEND=prometheus
   export SELFTEST_METRICS_PORT=9091
   ```

3. Configure Prometheus scrape config:
   ```yaml
   # prometheus.yml
   scrape_configs:
     - job_name: 'selftest'
       static_configs:
         - targets: ['localhost:9091']
       scrape_interval: 15s
   ```

4. Import Grafana dashboard:
   ```bash
   curl -o grafana/dashboards/selftest.json \
     https://raw.githubusercontent.com/org/repo/main/observability/dashboards/selftest-grafana.json
   ```

**Validation**:
```bash
# Run selftest with Prometheus metrics
make selftest

# Check metrics endpoint
curl http://localhost:9091/metrics | grep selftest
```

---

### 6.2 Datadog Integration

**Setup**:

1. Install Datadog client:
   ```bash
   uv pip install datadog
   ```

2. Configure API keys:
   ```bash
   export SELFTEST_METRICS_BACKEND=datadog
   export DD_API_KEY=<your-api-key>
   export DD_APP_KEY=<your-app-key>
   ```

3. Import Datadog dashboard:
   ```bash
   # Upload dashboard JSON via API
   curl -X POST "https://api.datadoghq.com/api/v1/dashboard" \
     -H "DD-API-KEY: ${DD_API_KEY}" \
     -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
     -d @observability/dashboards/selftest-datadog.json
   ```

**Metric Naming Convention**:

Datadog uses dot notation instead of underscores:
- `selftest_step_total` → `selftest.step.total`
- `selftest_step_duration_seconds` → `selftest.step.duration_seconds`

**Validation**:
```bash
# Run selftest with Datadog metrics
make selftest

# Query metrics via Datadog API
curl -X GET "https://api.datadoghq.com/api/v1/metrics/selftest.step.total" \
  -H "DD-API-KEY: ${DD_API_KEY}"
```

---

### 6.3 AWS CloudWatch Integration

**Setup**:

1. Install boto3:
   ```bash
   uv pip install boto3
   ```

2. Configure AWS credentials:
   ```bash
   export SELFTEST_METRICS_BACKEND=cloudwatch
   export AWS_REGION=us-east-1
   export AWS_ACCESS_KEY_ID=<your-key>
   export AWS_SECRET_ACCESS_KEY=<your-secret>
   ```

3. Create CloudWatch dashboard:
   ```bash
   aws cloudwatch put-dashboard \
     --dashboard-name Selftest \
     --dashboard-body file://observability/dashboards/selftest-cloudwatch.json
   ```

**Metric Namespace**: `Selftest`

**Validation**:
```bash
# Run selftest with CloudWatch metrics
make selftest

# Query metrics via AWS CLI
aws cloudwatch get-metric-statistics \
  --namespace Selftest \
  --metric-name selftest_step_total \
  --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum
```

---

### 6.4 GitHub Integration

**Purpose**: Post selftest metrics as PR comments for visibility

**Setup**:

1. Add GitHub token:
   ```bash
   export GITHUB_TOKEN=<your-token>
   ```

2. Enable GitHub integration:
   ```bash
   export SELFTEST_GITHUB_INTEGRATION=true
   ```

3. Run selftest in CI:
   ```yaml
   # .github/workflows/selftest.yml
   - name: Run selftest
     run: |
       make selftest --json-v2 > selftest_report.json
       uv run swarm/tools/post_selftest_to_github.py \
         --report selftest_report.json \
         --pr ${{ github.event.pull_request.number }}
   ```

**PR Comment Format**:

```markdown
## Selftest Results

**Status**: ✅ HEALTHY / ⚠️ DEGRADED / ❌ BROKEN

**Summary**:
- Passed: 8/10
- Failed: 2/10
- Duration: 15.3s

**Failed Steps**:
- `agents-governance` (GOVERNANCE): Agent validation failed
- `bdd` (GOVERNANCE): Feature file missing

**Remediation**:
- Run `make selftest --step agents-governance` for details
- See [Troubleshooting Guide](https://github.com/org/repo/docs/SELFTEST_SYSTEM.md#troubleshooting)

**SLO Compliance**:
- Kernel: ✅ 100% (target: 99.9%)
- Governance: ⚠️ 80% (target: 95%)
```

---

### 6.5 Slack Integration

**Purpose**: Daily digest and failure notifications

**Setup**:

1. Create Slack webhook:
   ```bash
   export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
   ```

2. Configure notifications:
   ```bash
   # Post to Slack on failure
   make selftest || curl -X POST $SLACK_WEBHOOK_URL \
     -H 'Content-Type: application/json' \
     -d '{"text": "Selftest failed in dev. See logs for details."}'
   ```

**Daily Digest Script**:

```bash
#!/bin/bash
# scripts/selftest_daily_digest.sh

# Query metrics for last 24h
pass_rate=$(curl -s "http://prometheus:9090/api/v1/query?query=selftest_governance_pass_rate" | jq '.data.result[0].value[1]')

# Format message
message=$(cat <<EOF
📊 Selftest Daily Digest ($(date +%Y-%m-%d))

**Governance Pass Rate**: ${pass_rate}%
**Kernel Failures**: 0 (all healthy)
**Top Failing Steps**:
  1. agents-governance (3 failures)
  2. bdd (1 failure)

**Recommendation**: Address governance failures before next release.

[View Dashboard](https://grafana.example.com/d/selftest-platform)
EOF
)

# Post to Slack
curl -X POST $SLACK_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d "{\"text\": \"$message\"}"
```

**Cron Schedule**:
```cron
0 9 * * * /path/to/scripts/selftest_daily_digest.sh
```

---

## 7. Data Retention & Cleanup

### 7.1 Local Logs

**Path**: `swarm/runs/<run-id>/build/selftest_metrics.jsonl`

**Retention Policy**:
- Keep last 30 days
- Archive older logs to `swarm/runs/archive/<year>/<month>/`
- Compress archives with gzip

**Cleanup Script**:

```bash
#!/bin/bash
# scripts/cleanup_selftest_metrics.sh

RETENTION_DAYS=30
ARCHIVE_DIR="swarm/runs/archive/$(date +%Y/%m)"
METRICS_DIR="swarm/runs"

# Find metrics files older than retention period
find "$METRICS_DIR" -name "selftest_metrics.jsonl" -mtime +$RETENTION_DAYS | while read file; do
    # Create archive directory
    mkdir -p "$ARCHIVE_DIR"

    # Move and compress file
    gzip -c "$file" > "$ARCHIVE_DIR/$(basename $(dirname $file))-metrics.jsonl.gz"

    # Delete original
    rm "$file"

    echo "Archived: $file → $ARCHIVE_DIR"
done
```

**Cron Schedule**:
```cron
0 2 * * * /path/to/scripts/cleanup_selftest_metrics.sh
```

---

### 7.2 Prometheus Data

**Storage**: Prometheus TSDB blocks

**Retention Policy**:
- 15 days (configurable via `--storage.tsdb.retention.time`)
- Compress older blocks automatically

**Configuration**:
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

storage:
  tsdb:
    retention.time: 15d
    retention.size: 10GB
```

**Backup Strategy**:
```bash
# Backup Prometheus data directory
tar -czf prometheus-backup-$(date +%Y%m%d).tar.gz /var/lib/prometheus/data/
```

---

### 7.3 Grafana Dashboards

**Retention Policy**:
- Keep dashboards indefinitely (version controlled)
- Archive old dashboard versions after 90 days

**Version Control**:
```bash
# Export Grafana dashboard to JSON
curl -H "Authorization: Bearer $GRAFANA_API_KEY" \
  "https://grafana.example.com/api/dashboards/uid/selftest" \
  > observability/dashboards/selftest-grafana-$(date +%Y%m%d).json

# Commit to git
git add observability/dashboards/
git commit -m "chore: backup Grafana dashboard $(date +%Y-%m-%d)"
```

---

### 7.4 GitHub PR Comments

**Retention Policy**:
- Post metrics to PR for 7 days (visible during review)
- Archive in GitHub run artifacts indefinitely

**Artifact Upload** (GitHub Actions):
```yaml
- name: Upload selftest report
  uses: actions/upload-artifact@v3
  with:
    name: selftest-report
    path: selftest_report.json
    retention-days: 90
```

---

## 8. Dashboard Examples (YAML/JSON Snippets)

### 8.1 Grafana Dashboard JSON

**File**: `observability/dashboards/selftest-grafana.json`

```json
{
  "dashboard": {
    "title": "Selftest Governance Health",
    "tags": ["selftest", "platform"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Governance Pass Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "selftest_governance_pass_rate",
            "legendFormat": "{{environment}}"
          }
        ],
        "yaxes": [
          {
            "label": "Pass Rate (%)",
            "min": 0,
            "max": 100
          }
        ],
        "thresholds": [
          {
            "value": 95,
            "colorMode": "critical",
            "op": "lt",
            "fill": true,
            "line": true,
            "yaxis": "left"
          }
        ]
      },
      {
        "id": 2,
        "title": "Failures Heatmap",
        "type": "heatmap",
        "targets": [
          {
            "expr": "sum by (step_id, severity) (rate(selftest_step_failures_total[1h]))"
          }
        ],
        "dataFormat": "tsbuckets",
        "color": {
          "mode": "spectrum",
          "colorScheme": "interpolateRdYlGn",
          "exponent": 0.5
        }
      },
      {
        "id": 3,
        "title": "AC Pass Rates",
        "type": "table",
        "targets": [
          {
            "expr": "selftest_ac_pass_rate",
            "format": "table",
            "instant": true
          }
        ],
        "columns": [
          { "text": "AC ID", "value": "ac_id" },
          { "text": "Pass Rate (%)", "value": "Value" },
          { "text": "Status", "value": "status" }
        ]
      }
    ]
  }
}
```

---

### 8.2 Prometheus Alert Rules

**File**: `prometheus/alerts/selftest.yml`

```yaml
groups:
  - name: selftest_critical
    interval: 15s
    rules:
      - alert: SelftestKernelFailureProd
        expr: selftest_kernel_failures_total{environment="prod"} > 0
        for: 0s
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Selftest kernel failure in PROD"
          description: "Kernel step failed in prod. This blocks all merges."
          runbook_url: "https://github.com/org/repo/docs/runbooks/selftest-kernel-failure.md"

      - alert: SelftestGovernanceFailureStaging
        expr: selftest_governance_pass_rate{environment="staging"} < 95
        for: 10m
        labels:
          severity: high
          team: platform
        annotations:
          summary: "Selftest governance failures in STAGING"
          description: "Pass rate: {{ $value }}%. Target: 95%"
```

---

### 8.3 Datadog Dashboard Definition

**File**: `observability/dashboards/selftest-datadog.json`

```json
{
  "title": "Selftest Governance Health",
  "layout_type": "ordered",
  "widgets": [
    {
      "definition": {
        "type": "timeseries",
        "requests": [
          {
            "q": "avg:selftest.governance.pass_rate{*} by {environment}",
            "display_type": "line"
          }
        ],
        "title": "Governance Pass Rate",
        "yaxis": {
          "min": "0",
          "max": "100"
        }
      }
    },
    {
      "definition": {
        "type": "heatmap",
        "requests": [
          {
            "q": "sum:selftest.step.failures.total{*} by {step_id,severity}.as_rate()"
          }
        ],
        "title": "Failures Heatmap"
      }
    },
    {
      "definition": {
        "type": "query_table",
        "requests": [
          {
            "q": "avg:selftest.ac.pass_rate{*} by {ac_id}",
            "aggregator": "last",
            "conditional_formats": [
              {
                "comparator": "<",
                "value": 100,
                "palette": "white_on_red"
              },
              {
                "comparator": ">=",
                "value": 100,
                "palette": "white_on_green"
              }
            ]
          }
        ],
        "title": "AC Pass Rates"
      }
    }
  ]
}
```

---

### 8.4 Slack Workflow Template

**File**: `slack/workflows/selftest-alert.json`

```json
{
  "name": "Selftest Alert Workflow",
  "trigger": {
    "type": "webhook",
    "url": "https://hooks.slack.com/workflows/..."
  },
  "steps": [
    {
      "id": "parse_alert",
      "type": "function",
      "function": "parse_prometheus_alert",
      "inputs": {
        "alert_payload": "{{webhook.body}}"
      }
    },
    {
      "id": "post_message",
      "type": "send_message",
      "channel": "#platform-alerts",
      "message": {
        "text": "🚨 Selftest Alert: {{parse_alert.alert_name}}",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Severity*: {{parse_alert.severity}}\n*Environment*: {{parse_alert.environment}}\n*Description*: {{parse_alert.description}}"
            }
          },
          {
            "type": "actions",
            "elements": [
              {
                "type": "button",
                "text": "View Runbook",
                "url": "{{parse_alert.runbook_url}}"
              },
              {
                "type": "button",
                "text": "View Dashboard",
                "url": "{{parse_alert.dashboard_url}}"
              }
            ]
          }
        ]
      }
    }
  ]
}
```

---

## 9. Testing the Observability System

### 9.1 Metrics Emission Validation

**Test**: Verify metrics are emitted correctly

**Steps**:

1. Enable local metrics:
   ```bash
   export SELFTEST_METRICS_BACKEND=local
   ```

2. Run selftest:
   ```bash
   make selftest
   ```

3. Verify metrics file exists:
   ```bash
   ls -l swarm/runs/*/build/selftest_metrics.jsonl
   ```

4. Validate JSON structure:
   ```bash
   cat swarm/runs/*/build/selftest_metrics.jsonl | jq .
   ```

5. Check for expected metrics:
   ```bash
   grep "selftest_step_total" swarm/runs/*/build/selftest_metrics.jsonl
   grep "selftest_step_duration_seconds" swarm/runs/*/build/selftest_metrics.jsonl
   grep "selftest_governance_pass_rate" swarm/runs/*/build/selftest_metrics.jsonl
   ```

**Expected Output**:
```json
{"timestamp": "2025-12-01T10:15:22.123456+00:00", "metric_name": "selftest_step_total", "metric_type": "counter", "value": 1, "labels": {"step_id": "core-checks", "environment": "dev", "tier": "kernel"}}
{"timestamp": "2025-12-01T10:15:25.678901+00:00", "metric_name": "selftest_step_duration_seconds", "metric_type": "histogram", "value": 3.456, "labels": {"step_id": "core-checks", "environment": "dev", "tier": "kernel"}}
```

---

### 9.2 Dashboard Rendering Validation

**Test**: Verify dashboards query metrics correctly

**Steps** (Prometheus + Grafana):

1. Start Prometheus:
   ```bash
   export SELFTEST_METRICS_BACKEND=prometheus
   export SELFTEST_METRICS_PORT=9091
   make selftest &

   # Start Prometheus
   prometheus --config.file=prometheus.yml
   ```

2. Verify metrics endpoint:
   ```bash
   curl http://localhost:9091/metrics | grep selftest
   ```

3. Query Prometheus:
   ```bash
   curl 'http://localhost:9090/api/v1/query?query=selftest_governance_pass_rate' | jq .
   ```

4. Import Grafana dashboard:
   ```bash
   curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
     -H "Content-Type: application/json" \
     -d @observability/dashboards/selftest-grafana.json
   ```

5. Open dashboard:
   ```bash
   open http://localhost:3000/d/selftest
   ```

6. Verify panels render:
   - Governance pass rate line chart should show data
   - Failures heatmap should be populated
   - AC pass rates table should display rows

---

### 9.3 Alert Firing Validation

**Test**: Trigger synthetic failures and verify alerts fire

**Steps**:

1. Create a failing step:
   ```bash
   # Temporarily break a governance step
   mv .claude/agents/clarifier.md .claude/agents/clarifier.md.bak
   ```

2. Run selftest in degraded mode:
   ```bash
   make selftest-degraded
   ```

3. Verify degradation logged:
   ```bash
   cat selftest_degradations.log | tail -n 1
   ```

4. Check Prometheus alert state:
   ```bash
   curl http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | select(.labels.alertname == "SelftestGovernanceFailureStaging")'
   ```

5. Verify alert fires:
   - Prometheus: Alert should transition from `pending` to `firing`
   - Datadog: Monitor should show `ALERT` state
   - PagerDuty: Incident should be created

6. Restore step:
   ```bash
   mv .claude/agents/clarifier.md.bak .claude/agents/clarifier.md
   ```

7. Verify alert resolves:
   ```bash
   make selftest
   # Alert should transition to `resolved`
   ```

---

### 9.4 Data Retention Validation

**Test**: Verify metrics are cleaned up on schedule

**Steps**:

1. Create old metrics files:
   ```bash
   # Create a metrics file from 35 days ago
   touch -d "35 days ago" swarm/runs/old-run/build/selftest_metrics.jsonl
   ```

2. Run cleanup script:
   ```bash
   bash scripts/cleanup_selftest_metrics.sh
   ```

3. Verify file archived:
   ```bash
   ls swarm/runs/archive/$(date +%Y/%m)/ | grep old-run-metrics.jsonl.gz
   ```

4. Verify original deleted:
   ```bash
   [ ! -f swarm/runs/old-run/build/selftest_metrics.jsonl ] && echo "File deleted"
   ```

---

### 9.5 Integration Test Suite

**Test**: End-to-end validation of observability system

**Script**: `tests/observability/test_selftest_observability.py`

```python
#!/usr/bin/env python3
"""Integration tests for selftest observability system."""

import json
import os
import subprocess
import time
from pathlib import Path

def test_metrics_emission():
    """Test that selftest emits metrics to local JSONL."""
    # Run selftest
    result = subprocess.run(
        ["make", "selftest"],
        env={**os.environ, "SELFTEST_METRICS_BACKEND": "local"},
        capture_output=True,
    )

    # Find metrics file
    metrics_file = list(Path("swarm/runs").rglob("selftest_metrics.jsonl"))[0]
    assert metrics_file.exists(), "Metrics file not found"

    # Parse metrics
    with open(metrics_file) as f:
        metrics = [json.loads(line) for line in f]

    # Validate schema
    assert all("timestamp" in m for m in metrics), "Missing timestamp"
    assert all("metric_name" in m for m in metrics), "Missing metric_name"
    assert all("value" in m for m in metrics), "Missing value"
    assert all("labels" in m for m in metrics), "Missing labels"

    # Validate expected metrics
    metric_names = {m["metric_name"] for m in metrics}
    assert "selftest_step_total" in metric_names
    assert "selftest_step_duration_seconds" in metric_names
    assert "selftest_governance_pass_rate" in metric_names


def test_prometheus_metrics():
    """Test that selftest exposes Prometheus metrics."""
    # Start selftest with Prometheus backend
    env = {
        **os.environ,
        "SELFTEST_METRICS_BACKEND": "prometheus",
        "SELFTEST_METRICS_PORT": "9091",
    }
    proc = subprocess.Popen(["make", "selftest"], env=env)

    # Wait for metrics server to start
    time.sleep(2)

    # Query metrics endpoint
    result = subprocess.run(
        ["curl", "http://localhost:9091/metrics"],
        capture_output=True,
        text=True,
    )

    # Validate OpenMetrics format
    assert "selftest_step_total" in result.stdout
    assert "selftest_step_duration_seconds" in result.stdout
    assert "# HELP" in result.stdout
    assert "# TYPE" in result.stdout

    proc.wait()


def test_degradation_logging():
    """Test that degraded mode logs degradations."""
    # Run selftest in degraded mode (force a governance failure)
    result = subprocess.run(
        ["make", "selftest-degraded"],
        env={**os.environ, "SELFTEST_FORCE_FAILURE": "agents-governance"},
        capture_output=True,
    )

    # Check degradation log
    log_file = Path("selftest_degradations.log")
    assert log_file.exists(), "Degradation log not found"

    with open(log_file) as f:
        entries = [json.loads(line) for line in f]

    # Validate schema
    assert len(entries) > 0, "No degradations logged"
    entry = entries[-1]
    assert entry["step_id"] == "agents-governance"
    assert entry["tier"] == "governance"
    assert entry["severity"] == "warning"
    assert "remediation" in entry


if __name__ == "__main__":
    test_metrics_emission()
    test_prometheus_metrics()
    test_degradation_logging()
    print("All observability tests passed!")
```

**Run Tests**:
```bash
uv run pytest tests/observability/test_selftest_observability.py -v
```

---

## Summary

This observability specification provides a complete monitoring and alerting framework for the selftest system:

1. **10 core metrics** covering execution, failures, degradation, and performance
2. **3 transport mechanisms** (local JSONL, Prometheus, Datadog, CloudWatch)
3. **3 dashboards** for developers, platform engineers, and incident responders
4. **Environment-specific SLOs** with appropriate error budgets
5. **8 alert rules** ranging from critical (immediate page) to info (logging only)
6. **Integration guides** for Prometheus, Datadog, CloudWatch, GitHub, Slack
7. **Data retention policies** to prevent unbounded growth
8. **Example configurations** (copy-paste ready)
9. **Testing framework** to validate observability system health

The system is **composable** (start with local JSONL, graduate to Prometheus), **layered** (different SLOs for dev/staging/prod), and **actionable** (every alert has a runbook).

**Next Steps**:
1. Implement metric emission in `swarm/tools/selftest.py` (see § 2.1)
2. Add Prometheus client library and expose `/metrics` endpoint (see § 2.2.2)
3. Import Grafana dashboards (see § 8.1)
4. Configure Prometheus alert rules (see § 8.2)
5. Run integration tests (see § 9.5)

**Maintenance**:
- Review SLO compliance monthly
- Update alert thresholds based on observed failure rates
- Archive old metrics per retention policy (see § 7)
- Validate dashboards after metrics schema changes

**Philosophy**: Observability is not monitoring—it's the ability to ask arbitrary questions of your system. This spec enables you to ask "Why did selftest fail?" and get a definitive answer, not a guess.
