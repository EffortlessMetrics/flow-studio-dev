# Selftest Observability

This directory contains observability-as-code artifacts for the selftest governance system, implementing the design specified in `docs/SELFTEST_OBSERVABILITY_SPEC.md`.

## Directory Structure

```
observability/
├── README.md                              # This file
├── dashboards/                            # Dashboard definitions
│   ├── selftest_dashboard.jsonnet         # Grafana (Jsonnet)
│   ├── selftest_dashboard.json            # Grafana (JSON)
│   ├── selftest_dashboard_compact.yaml    # Datadog/other platforms
│   └── README.md                          # Installation guide
├── prometheus/                            # Prometheus-specific assets
│   ├── recording_rules.yaml               # Pre-computed SLI metrics
│   ├── alert_rules.yaml                   # SLO-based alerts
│   ├── install.sh                         # Installation script
│   └── README.md                          # Prometheus setup guide
├── kubernetes/                            # Kubernetes-native assets
│   └── service_monitor.yaml               # ServiceMonitor + PrometheusRule CRDs
├── slos/                                  # SLO definitions
│   ├── selftest_slos.yaml                 # SLO objectives and thresholds
│   └── README.md                          # SLO documentation
└── alerts/                                # Alert rules (existing)
    ├── selftest_alerts.yaml               # Alert definitions
    ├── channels.yaml                      # Notification channels
    └── README.md                          # Alert setup guide
```

## Quick Start

### 1. Enable Metrics Collection

```bash
# For Prometheus (local/dev)
export SELFTEST_METRICS_BACKEND=prometheus
export SELFTEST_METRICS_PORT=9091
make selftest

# For Datadog (staging/prod)
export SELFTEST_METRICS_BACKEND=datadog
export DD_API_KEY=<your-key>
make selftest
```

### 2. Import Dashboards

**Grafana**:
```bash
# Import JSON dashboard
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @observability/dashboards/selftest_dashboard.json
```

**Datadog**:
```bash
# Convert YAML to JSON and upload via API
cat observability/dashboards/selftest_dashboard_compact.yaml | yq eval -o=json | \
  curl -X POST "https://api.datadoghq.com/api/v1/dashboard" \
    -H "DD-API-KEY: ${DD_API_KEY}" \
    -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
    -H "Content-Type: application/json" \
    -d @-
```

### 3. Install Prometheus Rules

**Standalone Prometheus**:
```bash
# Install recording and alert rules
cd observability/prometheus
./install.sh

# Or manually
cp recording_rules.yaml /etc/prometheus/rules/selftest_recording.yaml
cp alert_rules.yaml /etc/prometheus/rules/selftest_alerts.yaml
curl -X POST http://localhost:9090/-/reload
```

**Kubernetes (Prometheus Operator)**:
```bash
# Apply ServiceMonitor and PrometheusRule CRDs
./install.sh --kubernetes

# Or manually
kubectl apply -f kubernetes/service_monitor.yaml -n selftest
```

### 4. Configure SLOs

**Prometheus**:
```bash
# Recording rules for SLOs are included in prometheus/recording_rules.yaml
# The rules pre-compute:
#   - selftest:availability:success_rate:30d (target: 99%)
#   - selftest:performance:p95_duration:30d (target: 120s)
#   - selftest:degradation:max_count:24h (target: <= 3)
```

**Datadog**:
- Navigate to **Monitors → Service Level Objectives → New SLO**
- Use definitions from `slos/selftest_slos.yaml`

## What's Included

### Dashboards (4 Core Panels)

1. **Run Success Rate (%)** — Time-series of pass rate by environment
2. **Step Failure Distribution** — Top 5 failing steps
3. **Run Duration Distribution** — P50, P95, P99 percentiles
4. **Active Degradations** — Count by severity

Plus 3 SLO compliance gauges (Availability, Performance, Degradation).

### SLOs (3 Core Objectives)

1. **Availability SLO**: 99% of runs succeed over 30 days
   - Target: >= 99%
   - Error budget: 1% (432 min/month)
   - Severity: Critical (page on-call)

2. **Performance SLO**: P95 run duration <= 120s over 30 days
   - Target: <= 120s
   - Error budget: 30s (150s - 120s)
   - Severity: High (create ticket)

3. **Degradation SLO**: No more than 3 repeated degradations per step in 24h
   - Target: <= 3 per step per 24h
   - Error budget: 2 additional (5 total)
   - Severity: High (create ticket)

### Metrics (11 Total)

- **Counters**: `selftest_step_total`, `selftest_step_failures_total`, `selftest_degradations_total`, `selftest_kernel_failures_total`, `selftest_ac_failures_total`
- **Gauges**: `selftest_governance_pass_rate`, `selftest_degradations_active`, `selftest_run_overall_status`, `selftest_ac_pass_rate`
- **Histograms**: `selftest_step_duration_seconds`, `selftest_run_duration_seconds`

See `docs/SELFTEST_OBSERVABILITY_SPEC.md` § 1 for complete metric definitions.

## Implementation Status

### ✅ Complete

- [x] Dashboard definitions (Grafana JSON, Jsonnet, compact YAML)
- [x] SLO definitions (Prometheus recording rules, Datadog SLO format)
- [x] Installation guides (README.md in each directory)
- [x] All 4 required dashboard panels present
- [x] All 3 SLOs defined with objectives, thresholds, remediation
- [x] Valid YAML/JSON (syntax verified)
- [x] Metric references match spec (8/11 core metrics used)
- [x] Prometheus recording rules (`prometheus/recording_rules.yaml`)
- [x] Prometheus alert rules (`prometheus/alert_rules.yaml`)
- [x] Kubernetes ServiceMonitor and PrometheusRule CRDs (`kubernetes/service_monitor.yaml`)
- [x] Installation script for Prometheus (`prometheus/install.sh`)

### 🚧 To Be Implemented

- [ ] Metric emission in `swarm/tools/selftest.py` (P2.1-2.3)
- [ ] Prometheus client library integration
- [ ] Datadog statsd integration
- [ ] Datadog dashboard and monitors (Phase 2)
- [ ] CloudWatch boto3 integration
- [ ] OpenTelemetry support (Phase 3)
- [ ] Integration tests (`tests/observability/test_selftest_observability.py`)

## Usage Examples

### Query Current SLO Status

```bash
# Availability SLO
curl -s 'http://localhost:9090/api/v1/query?query=selftest:availability:success_rate:30d' | jq -r '.data.result[0].value[1]'

# Performance SLO (P95 duration)
curl -s 'http://localhost:9090/api/v1/query?query=selftest:performance:p95_duration:30d' | jq -r '.data.result[0].value[1]'

# Degradation SLO (max per step)
curl -s 'http://localhost:9090/api/v1/query?query=max(selftest:degradation:max_count:24h)' | jq -r '.data.result[0].value[1]'
```

### Generate Weekly SLO Report

```bash
# Run weekly report script
bash scripts/slo_weekly_report.sh > slo_report_$(date +%Y-%m-%d).md

# Send to team
cat slo_report_*.md | mail -s "Selftest SLO Report" platform-team@example.com
```

### Check Dashboard Panel Rendering

```bash
# Open Grafana dashboard
open http://localhost:3000/d/selftest

# Verify panels load (check for "No data" errors)
# If errors: review logs, check Prometheus scrape targets
```

## Validation

All dashboards and SLOs have been validated:

```bash
# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('observability/dashboards/selftest_dashboard_compact.yaml'))"
python3 -c "import yaml; yaml.safe_load(open('observability/slos/selftest_slos.yaml'))"

# Validate JSON syntax
python3 -c "import json; json.load(open('observability/dashboards/selftest_dashboard.json'))"

# Verify required panels present
python3 -c "
import yaml
dashboard = yaml.safe_load(open('observability/dashboards/selftest_dashboard_compact.yaml'))
required = ['Run Success Rate', 'Step Failure Distribution', 'Run Duration', 'Active Degradations']
found = [any(r.lower() in w['title'].lower() for w in dashboard['widgets']) for r in required]
assert all(found), 'Missing required panels'
print('✓ All required panels present')
"

# Verify SLOs defined
python3 -c "
import yaml
slos = yaml.safe_load(open('observability/slos/selftest_slos.yaml'))
assert len(slos['slos']) == 3, 'Expected 3 SLOs'
names = [s['name'] for s in slos['slos']]
assert any('availability' in n.lower() for n in names), 'Missing availability SLO'
assert any('performance' in n.lower() for n in names), 'Missing performance SLO'
assert any('degradation' in n.lower() for n in names), 'Missing degradation SLO'
print('✓ All 3 SLOs defined')
"
```

## Documentation

- **Observability Spec**: `docs/SELFTEST_OBSERVABILITY_SPEC.md` — Complete design specification
- **Plugins Design**: `docs/designs/OBSERVABILITY_PLUGINS_DESIGN.md` — Plugin architecture ADR
- **Dashboard Guide**: `dashboards/README.md` — Installation and usage instructions
- **Prometheus Guide**: `prometheus/README.md` — Prometheus rules and Kubernetes setup
- **SLO Guide**: `slos/README.md` — SLO definitions and remediation playbooks
- **Alert Guide**: `alerts/README.md` — Alert rules and notification channels

## Related Systems

- **Selftest System**: `swarm/SELFTEST_SYSTEM.md` — Core selftest documentation
- **Flow Studio**: Port 5000 (visual graph) — Will integrate SLO status indicators
- **CI Integration**: `.github/workflows/swarm-validate.yml` — Runs selftest on every PR

## Philosophy

Observability is not monitoring — it's the ability to ask arbitrary questions of your system. These dashboards and SLOs enable you to:

1. **Diagnose failures** — Identify which step failed, when, and why
2. **Track reliability** — Measure SLO compliance over time
3. **Predict issues** — Detect trends before they become outages
4. **Guide decisions** — Use error budgets to balance velocity and stability

Every metric has a clear remediation path. Every alert has a runbook. Every SLO breach has a playbook.

## Support

For observability issues:

1. Verify metrics are being emitted: `curl http://localhost:9091/metrics | grep selftest`
2. Check dashboard installation: See `dashboards/README.md` § Troubleshooting
3. Review SLO compliance: `make selftest --json-v2 | jq .summary`
4. Create GitHub issue with dashboard screenshot and metric queries

## Next Steps

1. Implement metric emission (P2.1-2.3)
2. Deploy dashboards to staging/prod
3. Configure alert rules with PagerDuty integration
4. Schedule weekly SLO review meetings
5. Integrate SLO status into Flow Studio UI
