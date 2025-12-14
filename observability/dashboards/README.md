# Selftest Observability Dashboards

This directory contains dashboard-as-code definitions for monitoring the selftest governance system across all environments (dev, staging, prod).

## Dashboard Files

- **`selftest_dashboard.jsonnet`** — Grafana dashboard in Jsonnet format (grafonnet library)
- **`selftest_dashboard.json`** — Grafana dashboard in JSON format (importable)
- **`selftest_dashboard_compact.yaml`** — Compact YAML format for Datadog, New Relic, or other platforms

## Dashboard Overview

The dashboard includes **4 core panels** as specified in `docs/SELFTEST_OBSERVABILITY_SPEC.md`:

1. **Run Success Rate (%)** — Time-series line chart showing pass rate over time by environment
2. **Step Failure Distribution** — Top 5 failing steps by `step_id` with failure rate
3. **Run Duration Distribution** — P50, P95, P99 histograms for performance tracking
4. **Active Degradations** — Count of active degradations by severity (critical/warning/info)

Plus additional panels:
- **Overall Status Gauge** — Red/Yellow/Green indicator (BROKEN/DEGRADED/HEALTHY)
- **Failures Heatmap** — Step failures over time by severity
- **Acceptance Criteria Pass Rates** — Table view of AC coverage
- **SLO Compliance Indicators** — Three gauges showing SLO status

## Installation

### Grafana (Prometheus Backend)

#### Prerequisites

- Grafana 7.0+ installed
- Prometheus 2.0+ with selftest metrics scraped
- Selftest running with `SELFTEST_METRICS_BACKEND=prometheus`

#### Step 1: Enable Prometheus Metrics

```bash
# Enable Prometheus metrics in selftest
export SELFTEST_METRICS_BACKEND=prometheus
export SELFTEST_METRICS_PORT=9091

# Run selftest to start emitting metrics
make selftest
```

#### Step 2: Configure Prometheus Scrape Config

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'selftest'
    static_configs:
      - targets: ['localhost:9091']
    scrape_interval: 15s
```

Reload Prometheus:
```bash
curl -X POST http://localhost:9090/-/reload
```

#### Step 3: Verify Metrics

```bash
# Check Prometheus endpoint
curl http://localhost:9091/metrics | grep selftest

# Query via Prometheus
curl 'http://localhost:9090/api/v1/query?query=selftest_governance_pass_rate' | jq .
```

#### Step 4: Import Dashboard

**Option A: Via Grafana UI**

1. Open Grafana: `http://localhost:3000`
2. Navigate to **Dashboards → Import**
3. Upload `selftest_dashboard.json`
4. Select Prometheus datasource
5. Click **Import**

**Option B: Via API**

```bash
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @observability/dashboards/selftest_dashboard.json
```

**Option C: Jsonnet (Advanced)**

If using grafonnet with jsonnet tooling:

```bash
# Install jsonnet and grafonnet
brew install jsonnet
git clone https://github.com/grafana/grafonnet-lib.git

# Compile jsonnet to JSON
jsonnet -J grafonnet-lib selftest_dashboard.jsonnet > selftest_dashboard_compiled.json

# Import compiled dashboard
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @selftest_dashboard_compiled.json
```

#### Step 5: Configure Variables

After import, verify template variables:

- **datasource**: Should auto-select Prometheus datasource
- **environment**: Should populate with `dev`, `staging`, `prod` from metric labels

### Datadog

#### Prerequisites

- Datadog account with API/APP keys
- Selftest running with `SELFTEST_METRICS_BACKEND=datadog`

#### Step 1: Enable Datadog Metrics

```bash
# Install Datadog client
uv pip install datadog

# Configure API keys
export SELFTEST_METRICS_BACKEND=datadog
export DD_API_KEY=<your-api-key>
export DD_APP_KEY=<your-app-key>

# Run selftest to start emitting metrics
make selftest
```

#### Step 2: Import Dashboard

**Option A: Via Datadog UI**

1. Open Datadog dashboards: `https://app.datadoghq.com/dashboard/lists`
2. Click **New Dashboard**
3. Click **Import Dashboard JSON**
4. Paste contents of `selftest_dashboard_compact.yaml` (convert to JSON if needed)

**Option B: Via API**

```bash
# Convert YAML to JSON (using yq or Python)
cat selftest_dashboard_compact.yaml | yq eval -o=json > selftest_dashboard_datadog.json

# Upload via API
curl -X POST "https://api.datadoghq.com/api/v1/dashboard" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
  -H "Content-Type: application/json" \
  -d @selftest_dashboard_datadog.json
```

#### Step 3: Verify Metrics

```bash
# Query metrics via Datadog API
curl -X GET "https://api.datadoghq.com/api/v1/metrics/selftest.governance.pass_rate" \
  -H "DD-API-KEY: ${DD_API_KEY}"
```

### AWS CloudWatch

#### Prerequisites

- AWS account with CloudWatch access
- Selftest running with `SELFTEST_METRICS_BACKEND=cloudwatch`

#### Step 1: Enable CloudWatch Metrics

```bash
# Install boto3
uv pip install boto3

# Configure AWS credentials
export SELFTEST_METRICS_BACKEND=cloudwatch
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=<your-key>
export AWS_SECRET_ACCESS_KEY=<your-secret>

# Run selftest to start emitting metrics
make selftest
```

#### Step 2: Create CloudWatch Dashboard

```bash
# Create dashboard from JSON definition
aws cloudwatch put-dashboard \
  --dashboard-name Selftest \
  --dashboard-body file://selftest_dashboard_compact.yaml
```

#### Step 3: Verify Metrics

```bash
# List available metrics
aws cloudwatch list-metrics \
  --namespace Selftest \
  --region us-east-1

# Query specific metric
aws cloudwatch get-metric-statistics \
  --namespace Selftest \
  --metric-name selftest_governance_pass_rate \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

## Dashboard Usage

### Filtering by Environment

Use the **environment** template variable to filter metrics:

- **All** — Show metrics from all environments (default)
- **prod** — Production only (use for SLO monitoring)
- **staging** — Staging environment
- **dev** — Development environment

### Understanding Panel Colors

- **Green** — Healthy, within SLO targets
- **Yellow** — Warning, approaching SLO breach
- **Red** — Critical, SLO breached or step failing

### Panel Descriptions

#### 1. Overall Status Gauge

**What it shows**: Current selftest health status

**Values**:
- `1.0` (Green) — HEALTHY: All steps pass
- `0.5` (Yellow) — DEGRADED: Kernel passes, governance/optional failed
- `0.0` (Red) — BROKEN: Kernel failed (blocks CI/CD)

**Action**: If red, run `make selftest-doctor` immediately

#### 2. Governance Pass Rate (%)

**What it shows**: Percentage of governance steps passing over time

**Target**: 95-100% (yellow zone: 90-95%, red zone: <90%)

**Action**: If trending downward, investigate top failing steps in Panel 4

#### 3. Step Failure Distribution (Top 5)

**What it shows**: Bar chart of most-failing steps by `step_id`

**Interpretation**:
- High failure rate → Harness issue or persistent service problem
- Sporadic failures → Transient issues (network, deps, etc.)

**Action**: Click step name to filter other panels, then review logs

#### 4. Run Duration Distribution (P50, P95, P99)

**What it shows**: Performance percentiles for full selftest runs

**Targets**:
- P50 < 30s (typical)
- P95 < 90s (warning)
- P99 < 120s (SLO target)

**Action**: If P99 > 120s, run `make selftest --verbose` to identify slow steps

#### 5. Active Degradations

**What it shows**: Count of currently active degradations (failures in degraded mode)

**Target**: 0 (green)

**Action**: Review `selftest_degradations.log` for remediation commands

#### 6. Failures Heatmap

**What it shows**: Step failures over time, color-coded by severity

**Interpretation**:
- Red cells → High failure rate for that step in that time window
- Green cells → Low/no failures

**Action**: Identify patterns (time-of-day, deploy correlation, etc.)

#### 7. Acceptance Criteria Pass Rates

**What it shows**: Table of all 6 ACs with current pass rates

**Target**: 100% for all ACs

**Action**: If AC < 100%, click AC ID to view related steps and failures

#### 8. SLO Compliance Indicators

**What they show**:
- **Availability SLO**: Success rate over 30 days (target: 99%)
- **Performance SLO**: P95 run duration over 30 days (target: <= 120s)
- **Degradation SLO**: Max degradations per step in 24h (target: <= 3)

**Action**: If any SLO breached, follow remediation in `../slos/selftest_slos.yaml`

## Troubleshooting

### Dashboard Shows No Data

**Symptoms**: All panels show "No data"

**Causes**:
1. Prometheus not scraping selftest metrics endpoint
2. Selftest not running with metrics enabled
3. Incorrect datasource configuration

**Solutions**:

```bash
# 1. Verify selftest metrics are enabled
echo $SELFTEST_METRICS_BACKEND  # Should be "prometheus" or "datadog"

# 2. Check metrics endpoint is accessible
curl http://localhost:9091/metrics | grep selftest_step_total

# 3. Verify Prometheus is scraping
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.job == "selftest")'

# 4. Check Grafana datasource config
curl -u admin:admin http://localhost:3000/api/datasources | jq .
```

### Wrong Environment Labels

**Symptoms**: Environment filter shows unexpected values or no values

**Cause**: `environment` label not set in metrics emission

**Solution**:

```bash
# Explicitly set environment when running selftest
export SELFTEST_ENVIRONMENT=dev  # or staging, prod
make selftest
```

### Panels Show Errors

**Symptoms**: "Query returned error" or "Invalid query"

**Causes**:
1. Metric names changed (version mismatch)
2. Prometheus recording rules not configured
3. Histogram buckets misconfigured

**Solutions**:

```bash
# 1. Check metric schema version
curl http://localhost:9091/metrics | head -n 20

# 2. Verify recording rules in Prometheus
curl http://localhost:9090/api/v1/rules | jq '.data.groups[] | select(.name == "selftest_slo_rules")'

# 3. Check histogram bucket configuration
curl http://localhost:9091/metrics | grep selftest_run_duration_seconds_bucket
```

### SLO Panels Show Incorrect Values

**Symptoms**: SLO gauges show 0 or NaN

**Cause**: 30-day window has insufficient data (new installation)

**Solution**: Wait for metrics to accumulate or reduce window:

```promql
# Change 30d to 1h for testing
histogram_quantile(0.95, rate(selftest_run_duration_seconds_bucket{environment="prod"}[1h]))
```

## Customization

### Adding Custom Panels

To add a custom panel to the JSON dashboard:

1. Edit `selftest_dashboard.json`
2. Add panel definition to `panels` array
3. Set unique `id` (increment from last panel)
4. Set `gridPos` for layout (x, y, w, h)
5. Re-import dashboard

Example custom panel:

```json
{
  "id": 11,
  "title": "Custom Metric",
  "type": "graph",
  "datasource": "Prometheus",
  "targets": [
    {
      "expr": "your_custom_query",
      "legendFormat": "{{label}}"
    }
  ],
  "gridPos": {
    "x": 0,
    "y": 50,
    "w": 12,
    "h": 8
  }
}
```

### Modifying Thresholds

To change warning/critical thresholds:

1. Edit the `thresholds` field in panel definitions
2. Update corresponding values in `../slos/selftest_slos.yaml`
3. Re-import dashboard

Example:

```json
"thresholds": [
  {
    "value": 90,    // Changed from 95
    "colorMode": "critical",
    "op": "lt"
  }
]
```

## Maintenance

### Dashboard Versioning

When making changes to dashboards:

1. Export updated dashboard from Grafana UI
2. Save to `selftest_dashboard_v<version>.json`
3. Update `selftest_dashboard.json` (latest)
4. Commit both files to git

### Schema Migration

If metric names or labels change:

1. Update dashboard queries to match new schema
2. Add recording rules for backward compatibility
3. Document breaking changes in CHANGELOG.md

### Performance Optimization

For large-scale deployments:

1. Use Prometheus recording rules to pre-aggregate metrics
2. Increase dashboard refresh interval from 1m to 5m
3. Reduce time range from 7d to 24h for faster queries
4. Add dashboard-level caching (Grafana Enterprise)

## Related Documentation

- **Metrics Spec**: `docs/SELFTEST_OBSERVABILITY_SPEC.md` § 1 (Metrics Definitions)
- **SLOs**: `../slos/selftest_slos.yaml` (Service Level Objectives)
- **Alert Rules**: `docs/SELFTEST_OBSERVABILITY_SPEC.md` § 5 (Alert Rules)
- **Troubleshooting**: `swarm/SELFTEST_SYSTEM.md` § Troubleshooting

## Support

For issues with dashboards:

1. Check [Troubleshooting](#troubleshooting) section above
2. Review logs: `cat selftest_metrics.jsonl | jq .`
3. Verify metrics schema: `curl http://localhost:9091/metrics`
4. Create GitHub issue with dashboard screenshot and error message

## License

These dashboards are part of the Flow Studio project and are provided as-is for reference implementations.
