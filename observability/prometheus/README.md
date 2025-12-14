# Prometheus Integration for Selftest

This directory contains Prometheus-specific observability assets for the selftest system.

## Contents

```
prometheus/
    recording_rules.yaml   # Pre-computed SLI metrics
    alert_rules.yaml       # SLO-based alerts
    install.sh             # Installation script
    README.md              # This file
```

## Quick Start

### Standalone Prometheus

```bash
# Install rules to default location (/etc/prometheus/rules)
./install.sh

# Install to custom location
PROMETHEUS_CONFIG_DIR=/path/to/rules ./install.sh

# Preview changes without installing
./install.sh --dry-run
```

### Kubernetes (Prometheus Operator)

```bash
# Apply ServiceMonitor and PrometheusRule CRDs
./install.sh --kubernetes

# Apply to custom namespace
NAMESPACE=monitoring ./install.sh --kubernetes
```

## Recording Rules

Recording rules pre-compute common queries for dashboard performance:

| Rule Name | Description | SLI |
|-----------|-------------|-----|
| `selftest:pass_rate:5m` | Overall pass rate over 5 minutes | Availability |
| `selftest:kernel_failure_rate:5m` | Kernel failure rate | Kernel Health |
| `selftest:governance_pass_rate:5m` | Governance pass rate | Governance Health |
| `selftest:step_duration_p95:5m` | P95 duration by step | Performance |
| `selftest:run_duration_p95:5m` | Overall P95 run duration | Performance |
| `selftest:availability:success_rate:30d` | 30-day success rate (SLO) | Availability |
| `selftest:performance:p95_duration:30d` | 30-day P95 duration (SLO) | Performance |
| `selftest:degradation:max_count:24h` | Max degradations per step | Degradation |

## Alert Rules

Alerts are organized by severity:

### Critical (Page On-Call)

| Alert | Condition | Description |
|-------|-----------|-------------|
| `SelftestKernelFailure` | Kernel failure rate > 1% for 5m | Core infrastructure failure |
| `SelftestKernelBlocked` | Any kernel step BLOCKED | Configuration/environment issue |
| `SelftestAvailabilitySLOBreach` | Success rate < 99% over 30d | SLO violation |

### High (Urgent Ticket)

| Alert | Condition | Description |
|-------|-----------|-------------|
| `SelftestPerformanceSLOBreach` | P95 duration > 120s for 5m | Performance SLO violation |
| `SelftestDegradationSLOBreach` | > 3 degradations per step in 24h | Repeated failures |

### Warning (Standard Ticket)

| Alert | Condition | Description |
|-------|-----------|-------------|
| `SelftestAvailabilitySLOWarning` | Success rate < 99.5% | Approaching SLO breach |
| `SelftestPerformanceSLOWarning` | P95 duration > 90s for 15m | Approaching SLO breach |
| `SelftestGovernanceDegraded` | Governance pass rate < 95% | Governance issues |
| `SelftestGovernanceStepFailing` | Step pass rate < 80% for 30m | Specific step failing |

### Info (Monitoring Only)

| Alert | Condition | Description |
|-------|-----------|-------------|
| `SelftestActiveDegradations` | Any active degradations | System in degraded mode |
| `SelftestSlowStep` | Step P95 > 30s for 30m | Performance optimization candidate |

## Verification

### Check Rule Syntax

```bash
# Using promtool (bundled with Prometheus)
promtool check rules recording_rules.yaml
promtool check rules alert_rules.yaml
```

### Query Recording Rules

```bash
# Check if rules are loaded
curl -s 'http://localhost:9090/api/v1/rules' | jq '.data.groups[] | select(.name | contains("selftest"))'

# Query a recording rule
curl -s 'http://localhost:9090/api/v1/query?query=selftest:pass_rate:5m'
```

### Check Alert Status

```bash
# List all selftest alerts
curl -s 'http://localhost:9090/api/v1/alerts' | jq '.data.alerts[] | select(.labels.alertname | startswith("Selftest"))'
```

## Integration with Grafana

The recording rules are designed to work with the Grafana dashboard at `observability/dashboards/selftest_dashboard.json`.

Example queries for Grafana panels:

```promql
# Pass Rate Panel
selftest:pass_rate:5m

# Performance Panel
selftest:run_duration_p95:5m

# SLO Compliance Panel
selftest:availability:success_rate:30d
```

## Troubleshooting

### Rules Not Loading

1. Check Prometheus config includes rules directory:
   ```yaml
   # prometheus.yml
   rule_files:
     - /etc/prometheus/rules/*.yaml
   ```

2. Check file permissions:
   ```bash
   ls -la /etc/prometheus/rules/selftest_*.yaml
   ```

3. Check Prometheus logs:
   ```bash
   journalctl -u prometheus | grep -i "rule"
   ```

### Alerts Not Firing

1. Verify metrics are being scraped:
   ```bash
   curl -s 'http://localhost:9090/api/v1/targets' | jq '.data.activeTargets[] | select(.labels.job == "selftest")'
   ```

2. Check alert conditions manually:
   ```bash
   curl -s 'http://localhost:9090/api/v1/query?query=selftest:kernel_failure_rate:5m'
   ```

3. Check alert manager configuration for notification routing.

### Kubernetes Issues

1. Verify Prometheus Operator is installed:
   ```bash
   kubectl get crd servicemonitors.monitoring.coreos.com
   ```

2. Check ServiceMonitor is discovered:
   ```bash
   kubectl get servicemonitor -n selftest
   kubectl describe servicemonitor selftest -n selftest
   ```

3. Check PrometheusRule is loaded:
   ```bash
   kubectl get prometheusrule -n selftest
   kubectl describe prometheusrule selftest-rules -n selftest
   ```

## Reference

- **Design Document**: `docs/designs/OBSERVABILITY_PLUGINS_DESIGN.md`
- **SLO Definitions**: `observability/slos/selftest_slos.yaml`
- **Alert Policies**: `observability/alerts/selftest_alerts.yaml`
- **Grafana Dashboard**: `observability/dashboards/selftest_dashboard.json`
