# Selftest Service Level Objectives (SLOs)

This directory contains SLO definitions for the selftest governance system. SLOs define the target reliability, performance, and quality levels for the selftest system across environments.

## SLO Files

- **`selftest_slos.yaml`** — Complete SLO definitions with Prometheus and Datadog configurations

## SLO Overview

The selftest system has **3 core SLOs** as specified in `docs/SELFTEST_OBSERVABILITY_SPEC.md` § 4:

### SLO 1: Availability SLO

**Objective**: 99% of selftest runs complete successfully over 30 days

**Rationale**: The selftest system is a governance gate. If it fails frequently, it either blocks legitimate merges (false negative) or becomes ignored (false sense of security). 99% availability ensures selftest is reliable enough to trust.

**Target**: `>= 99%`

**Window**: 30 days (rolling)

**Error Budget**: 1% (approximately 7.2 minutes per week of downtime)

**Severity if breached**: Critical (page on-call)

**Measurement**:
```promql
# Prometheus
(sum(rate(selftest_step_total{environment="prod"}[30d])) - sum(rate(selftest_step_failures_total{environment="prod"}[30d]))) / sum(rate(selftest_step_total{environment="prod"}[30d])) * 100

# Datadog
(sum:selftest.step.total{environment:prod}.as_count() - sum:selftest.step.failures.total{environment:prod}.as_count()) / sum:selftest.step.total{environment:prod}.as_count() * 100
```

**What counts as success**:
- All KERNEL steps pass (core-checks)
- All GOVERNANCE steps pass (agents, skills, BDD, AC, policy)
- OPTIONAL steps may fail without impacting SLO

**What counts as failure**:
- Any KERNEL step fails (exit code 1)
- Any GOVERNANCE step fails in strict mode
- Selftest cannot run (harness issue)

### SLO 2: Performance SLO

**Objective**: P95 run duration <= 120 seconds over 30 days

**Rationale**: Selftest is part of CI/CD pipeline. If it's slow, it bottlenecks development velocity. P95 ensures most runs complete quickly, with tolerance for occasional slow runs (e.g., first run after cache clear).

**Target**: `<= 120s` (P95)

**Window**: 30 days (rolling)

**Error Budget**: 30 seconds (150s - 120s)

**Severity if breached**: High (create ticket, notify team)

**Measurement**:
```promql
# Prometheus
histogram_quantile(0.95, rate(selftest_run_duration_seconds_bucket{environment="prod"}[30d]))

# Datadog
p95:selftest.run.duration_seconds{environment:prod}
```

**What counts**:
- Full selftest run (all 16 steps in strict mode)
- Excludes kernel-only smoke checks (< 1s)
- Includes harness overhead (Python startup, validation parsing)

**Typical baselines**:
- P50: ~15-30s (fast path, warm cache)
- P95: ~60-90s (typical)
- P99: ~100-120s (cold cache, I/O contention)

### SLO 3: Degradation SLO

**Objective**: No more than 3 repeated degradations for the same step within 24 hours

**Rationale**: Degraded mode allows governance failures to be non-blocking, but repeated degradations indicate a persistent issue that needs attention. This SLO prevents accumulation of "known broken" state.

**Target**: `<= 3 degradations per step per 24h`

**Window**: 24 hours (rolling)

**Error Budget**: 2 additional degradations (5 total before escalation)

**Severity if breached**: High (create GitHub issue, notify team)

**Measurement**:
```promql
# Prometheus
max by (step_id) (sum_over_time(selftest_degradations_total{environment="prod"}[24h]))

# Datadog
max:selftest.degradations.total{environment:prod}.as_count().rollup(sum, 86400) by {step_id}
```

**What counts**:
- Only GOVERNANCE and OPTIONAL tier failures (KERNEL failures exit immediately)
- Repeated failures of the same step (by `step_id`)
- Within a 24-hour sliding window

**Examples**:
- `agents-governance` fails 4 times in 12 hours → SLO breach
- `bdd` fails once, passes, fails again 25 hours later → SLO OK (outside window)
- `core-checks` (KERNEL) fails once → Not counted (exits immediately, doesn't degrade)

## SLO Implementation

### Prometheus

#### Step 1: Configure Recording Rules

Add to `prometheus.yml` or separate rule file:

```yaml
# /etc/prometheus/rules/selftest_slo.yml
groups:
  - name: selftest_slo_rules
    interval: 1m
    rules:
      # Availability SLO
      - record: selftest:availability:success_rate:30d
        expr: |
          (
            sum(rate(selftest_step_total{environment="prod"}[30d]))
            - sum(rate(selftest_step_failures_total{environment="prod"}[30d]))
          ) / sum(rate(selftest_step_total{environment="prod"}[30d])) * 100
        labels:
          slo: availability
          environment: prod

      # Performance SLO
      - record: selftest:performance:p95_duration:30d
        expr: |
          histogram_quantile(0.95,
            rate(selftest_run_duration_seconds_bucket{environment="prod"}[30d])
          )
        labels:
          slo: performance
          environment: prod

      # Degradation SLO
      - record: selftest:degradation:max_count:24h
        expr: |
          max by (step_id) (
            sum_over_time(selftest_degradations_total{environment="prod"}[24h])
          )
        labels:
          slo: degradation
          environment: prod
```

#### Step 2: Configure Alert Rules

Add to alert rules file:

```yaml
# /etc/prometheus/alerts/selftest_slo.yml
groups:
  - name: selftest_slo_alerts
    interval: 1m
    rules:
      - alert: SelftestAvailabilitySLOBreach
        expr: selftest:availability:success_rate:30d < 99
        for: 5m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Selftest availability SLO breached"
          description: "Success rate {{ $value }}% is below 99% target"
          runbook: "https://github.com/org/repo/docs/runbooks/selftest-availability-slo.md"

      - alert: SelftestPerformanceSLOBreach
        expr: selftest:performance:p95_duration:30d > 120
        for: 5m
        labels:
          severity: high
          team: platform
        annotations:
          summary: "Selftest performance SLO breached"
          description: "P95 duration {{ $value }}s exceeds 120s target"
          runbook: "https://github.com/org/repo/docs/runbooks/selftest-performance-slo.md"

      - alert: SelftestDegradationSLOBreach
        expr: selftest:degradation:max_count:24h > 3
        for: 0s
        labels:
          severity: high
          team: platform
        annotations:
          summary: "Selftest degradation SLO breached for {{$labels.step_id}}"
          description: "Step {{$labels.step_id}} degraded {{ $value }} times in 24h"
          runbook: "https://github.com/org/repo/docs/runbooks/selftest-degradation-slo.md"
```

#### Step 3: Reload Prometheus

```bash
# Reload configuration
curl -X POST http://localhost:9090/-/reload

# Verify recording rules
curl http://localhost:9090/api/v1/rules | jq '.data.groups[] | select(.name == "selftest_slo_rules")'

# Verify alert rules
curl http://localhost:9090/api/v1/rules | jq '.data.groups[] | select(.name == "selftest_slo_alerts")'
```

### Datadog

#### Step 1: Create SLOs via UI

1. Navigate to **Monitors → Service Level Objectives → New SLO**

2. **Availability SLO**:
   - Name: "Selftest Availability SLO"
   - Type: Metric-based
   - Numerator (good events): `sum:selftest.step.total{environment:prod}.as_count() - sum:selftest.step.failures.total{environment:prod}.as_count()`
   - Denominator (total events): `sum:selftest.step.total{environment:prod}.as_count()`
   - Target: 99%
   - Time window: 30 days

3. **Performance SLO**:
   - Name: "Selftest Performance SLO"
   - Type: Monitor-based
   - Create monitor: `p95:selftest.run.duration_seconds{environment:prod} > 120`
   - Target: 0% of time in alert state
   - Time window: 30 days

4. **Degradation SLO**:
   - Name: "Selftest Degradation SLO"
   - Type: Metric-based
   - Query: `max:selftest.degradations.total{environment:prod}.as_count().rollup(sum, 86400) by {step_id}`
   - Target: < 3 degradations
   - Time window: 24 hours

#### Step 2: Create SLOs via API

```bash
# Availability SLO
curl -X POST "https://api.datadoghq.com/api/v1/slo" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Selftest Availability SLO",
    "type": "metric",
    "description": "99% of selftest runs complete successfully",
    "thresholds": [
      {
        "timeframe": "30d",
        "target": 99.0,
        "warning": 95.0
      }
    ],
    "query": {
      "numerator": "sum:selftest.step.total{environment:prod}.as_count() - sum:selftest.step.failures.total{environment:prod}.as_count()",
      "denominator": "sum:selftest.step.total{environment:prod}.as_count()"
    },
    "tags": ["team:platform", "service:selftest", "env:prod"]
  }'

# Performance SLO
curl -X POST "https://api.datadoghq.com/api/v1/slo" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Selftest Performance SLO",
    "type": "metric",
    "description": "P95 run duration <= 120s",
    "thresholds": [
      {
        "timeframe": "30d",
        "target": 120,
        "warning": 90
      }
    ],
    "query": {
      "numerator": "p95:selftest.run.duration_seconds{environment:prod}"
    },
    "tags": ["team:platform", "service:selftest", "env:prod"]
  }'
```

## Error Budget Management

### Understanding Error Budgets

Each SLO has an **error budget** — the amount of failure allowed before the SLO is breached.

**Availability SLO**:
- Target: 99%
- Error budget: 1%
- In 30 days (43,200 minutes): 432 minutes of downtime allowed
- Per week: ~100 minutes / 7.2 minutes

**Performance SLO**:
- Target: 120s (P95)
- Error budget: 30s (150s - 120s)
- Remaining budget: How much slower P95 can get before breach

**Degradation SLO**:
- Target: 3 degradations per step per 24h
- Error budget: 2 additional degradations (5 total before escalation)

### Burn Rate Alerts

**Fast burn** (2x rate over 1 hour):
```promql
# Availability: Burning error budget 2x faster than expected
rate(selftest_step_failures_total{environment="prod"}[1h]) / rate(selftest_step_total{environment="prod"}[1h]) > 0.02
```

**Slow burn** (1.5x rate over 6 hours):
```promql
# Availability: Sustained elevated failure rate
rate(selftest_step_failures_total{environment="prod"}[6h]) / rate(selftest_step_total{environment="prod"}[6h]) > 0.015
```

### Error Budget Policy

When error budget is exhausted (<5% remaining):

1. **Freeze non-critical changes**: No new features, only bug fixes
2. **Focus on reliability**: Prioritize fixing failing steps
3. **Post-mortem required**: Document root cause and prevention
4. **Weekly review**: Track burn rate and budget recovery

When error budget is healthy (>50% remaining):

1. **Proceed normally**: New features, refactoring allowed
2. **Proactive fixes**: Address flaky tests, improve performance
3. **Monthly review**: Track trends, adjust SLO targets if needed

## Monitoring SLO Compliance

### Daily Check

```bash
# Query recording rules for current SLO values
curl -s 'http://localhost:9090/api/v1/query?query=selftest:availability:success_rate:30d' | jq -r '.data.result[0].value[1]'
curl -s 'http://localhost:9090/api/v1/query?query=selftest:performance:p95_duration:30d' | jq -r '.data.result[0].value[1]'
curl -s 'http://localhost:9090/api/v1/query?query=selftest:degradation:max_count:24h' | jq -r '.data.result[0].value[1]'
```

### Weekly Report

Generate SLO compliance report:

```bash
#!/bin/bash
# scripts/slo_weekly_report.sh

echo "# Selftest SLO Compliance Report"
echo "**Week of**: $(date +%Y-%m-%d)"
echo ""
echo "## SLO Status"
echo ""

# Availability
availability=$(curl -s 'http://localhost:9090/api/v1/query?query=selftest:availability:success_rate:30d' | jq -r '.data.result[0].value[1]')
availability_status=$( (( $(echo "$availability >= 99" | bc -l) )) && echo "✅ PASS" || echo "❌ FAIL")

# Performance
performance=$(curl -s 'http://localhost:9090/api/v1/query?query=selftest:performance:p95_duration:30d' | jq -r '.data.result[0].value[1]')
performance_status=$( (( $(echo "$performance <= 120" | bc -l) )) && echo "✅ PASS" || echo "❌ FAIL")

# Degradation
degradation=$(curl -s 'http://localhost:9090/api/v1/query?query=max(selftest:degradation:max_count:24h)' | jq -r '.data.result[0].value[1]')
degradation_status=$( (( $(echo "$degradation <= 3" | bc -l) )) && echo "✅ PASS" || echo "❌ FAIL")

echo "| SLO | Target | Actual | Status |"
echo "|-----|--------|--------|--------|"
echo "| Availability | 99% | ${availability}% | ${availability_status} |"
echo "| Performance | 120s | ${performance}s | ${performance_status} |"
echo "| Degradation | <= 3 | ${degradation} | ${degradation_status} |"
```

## Remediation Playbooks

### Availability SLO Breach

**Severity**: Critical

**Steps**:

1. **Identify failing steps**:
   ```bash
   make selftest-doctor
   ```

2. **Check for infrastructure issues**:
   ```bash
   # CI/CD health
   gh run list --limit 10 --json conclusion

   # Environment issues
   uv --version
   python --version
   ```

3. **Review degradation log**:
   ```bash
   cat selftest_degradations.log | tail -n 20
   ```

4. **Run focused diagnostic**:
   ```bash
   make selftest --step <failing-step-id> --verbose
   ```

5. **If harness issue**: Update dependencies, fix test infrastructure
6. **If service issue**: Revert recent changes, fix bugs in code/tests
7. **Document in post-mortem**: Root cause, prevention plan

### Performance SLO Breach

**Severity**: High

**Steps**:

1. **Identify slow steps**:
   ```bash
   make selftest --verbose | grep "duration:"
   ```

2. **Profile specific step**:
   ```bash
   time make selftest --step <slow-step-id>
   ```

3. **Check for I/O contention**:
   ```bash
   iostat -x 1 10  # Run during selftest
   ```

4. **Optimize slow steps**:
   - Cache validation results (avoid re-parsing)
   - Parallelize independent checks
   - Reduce redundant Glob/Grep operations
   - Use incremental validation (`--check-modified`)

5. **If persistent**: Increase SLO target to realistic baseline (120s → 150s)

### Degradation SLO Breach

**Severity**: High

**Steps**:

1. **List recent degradations**:
   ```bash
   cat selftest_degradations.log | grep <step-id> | tail -n 5
   ```

2. **Run selftest-doctor**:
   ```bash
   make selftest-doctor
   ```

3. **Check for flaky tests**:
   - If test-related: Re-run 10 times, check pass rate
   - If environment-related: Check for transient network/disk issues

4. **Create GitHub issue**:
   ```bash
   gh issue create \
     --title "Repeated degradation: <step-id>" \
     --body "Step degraded {{ count }} times in 24h. See selftest_degradations.log for details." \
     --label "selftest,degradation"
   ```

5. **Fix underlying issue**: Don't just silence the degradation

## SLO Tuning

### When to Adjust SLO Targets

**Increase target** (make SLO stricter):
- Consistently exceeding current target by >10%
- Error budget never used (>80% remaining)
- Stakeholders require higher reliability

**Decrease target** (make SLO looser):
- Consistently breaching current target despite fixes
- Underlying system constraints (e.g., third-party API latency)
- Cost of maintaining target outweighs value

### Example Tuning

**Scenario**: Performance SLO (P95 <= 120s) consistently breached at ~135s despite optimizations.

**Analysis**:
- P50 is fast (~30s), no inefficiency
- P95 spike due to cold cache after CI machine restart
- Optimization costs >40 eng-hours, benefit marginal

**Decision**: Adjust SLO to P95 <= 150s

**Process**:
1. Document in `selftest_slos.yaml` (change target, add comment)
2. Update alert thresholds in Prometheus/Datadog
3. Update dashboard annotations
4. Announce in team channel with rationale

## Reporting and Dashboards

### SLO Dashboard

View SLO compliance in Grafana:

- Navigate to **Selftest Governance Health** dashboard
- Scroll to **SLO Compliance Indicators** row (bottom)
- Three gauges show current status (green/yellow/red)

### SLO History

Query historical SLO compliance:

```promql
# Availability over last 90 days
selftest:availability:success_rate:30d offset 0d
selftest:availability:success_rate:30d offset 30d
selftest:availability:success_rate:30d offset 60d

# Performance over last 90 days
selftest:performance:p95_duration:30d offset 0d
selftest:performance:p95_duration:30d offset 30d
selftest:performance:p95_duration:30d offset 60d
```

### Monthly Review

Template for monthly SLO review meeting:

```markdown
# Selftest SLO Review — [Month Year]

## SLO Compliance

| SLO | Target | Achieved | Status |
|-----|--------|----------|--------|
| Availability | 99% | [value]% | ✅/❌ |
| Performance | 120s | [value]s | ✅/❌ |
| Degradation | <= 3 | [value] | ✅/❌ |

## Error Budget

| SLO | Total Budget | Used | Remaining |
|-----|--------------|------|-----------|
| Availability | 1% | [value]% | [value]% |
| Performance | 30s | [value]s | [value]s |
| Degradation | 2 | [value] | [value] |

## Incidents

- [Date]: Availability SLO breach due to [cause]
- [Date]: Performance degradation from [cause]

## Trends

- Availability: [improving/stable/declining]
- Performance: [faster/stable/slower]
- Degradations: [increasing/stable/decreasing]

## Actions

1. [Action item 1]
2. [Action item 2]

## SLO Adjustments

- [Any proposed SLO target changes]
```

## Related Documentation

- **Metrics Spec**: `docs/SELFTEST_OBSERVABILITY_SPEC.md` § 1 (Metrics Definitions)
- **Dashboards**: `../dashboards/README.md` (Dashboard installation)
- **Alert Rules**: `docs/SELFTEST_OBSERVABILITY_SPEC.md` § 5 (Alert Rules)
- **Troubleshooting**: `swarm/SELFTEST_SYSTEM.md` § Troubleshooting

## Support

For SLO-related issues:

1. Review [Remediation Playbooks](#remediation-playbooks) above
2. Check current SLO values: `curl http://localhost:9090/api/v1/query?query=selftest:availability:success_rate:30d`
3. Review error budget status in Grafana dashboard
4. Create GitHub issue with SLO details and trend analysis
