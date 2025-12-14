# Selftest Alert System

This directory contains alert policies and routing configuration for the swarm selftest system.

## First Response Steps

When a selftest alert fires, follow these steps:

### 1. Gather Diagnostics (30 seconds)
```bash
make selftest-incident-pack
```
This creates `selftest_incident_<timestamp>.tar.gz` containing:
- Full selftest output
- Platform status
- Degradation logs
- Recent git commits
- Environment info

### 2. Get Fix Suggestions (10 seconds)
```bash
make selftest-suggest-remediation
```
This analyzes failures and suggests specific fix commands.

### 3. Triage by Severity

| Alert Severity | Action |
|----------------|--------|
| PAGE (kernel failure) | Immediate investigation required |
| TICKET (governance) | Create issue, fix in next sprint |
| INFO (trending) | Monitor, no immediate action |

### 4. Common Quick Fixes

| Symptom | Command |
|---------|---------|
| Agent not found | `make gen-adapters` |
| AC matrix stale | `make check-ac-freshness` |
| Lint errors | `ruff check --fix swarm/` |
| Color mismatch | Update `swarm/AGENTS.md` per role_family |

---

## Overview

The alert system provides **three-tier monitoring** for selftest health:

- **PAGE**: Critical failures requiring immediate on-call response
- **TICKET**: Issues needing investigation but not immediate action
- **INFO**: Trends and monitoring data (no action required)

## Files

- `selftest_alerts.yaml` — Alert rule definitions with thresholds, windows, and remediation hints
- `channels.yaml` — Routing configuration for PagerDuty, Slack, GitHub Issues, and email
- `README.md` — This file

## Alert Policies

### PAGE Severity (3 alerts)

**When**: Critical failures blocking development or CI

**Response Time**: Immediate (< 15 minutes)

**Routing**: PagerDuty on-call + Slack #selftest-issues

| Alert | Threshold | Window | What It Means |
|-------|-----------|--------|---------------|
| `kernel_failure_rate_critical` | >5% failures | 5 min | Core infrastructure broken (Python lint/compile) |
| `blocked_test_detected` | Any BLOCKED | 3 runs | Configuration or environment issue preventing execution |
| `p95_duration_degraded` | P95 > 180s | 5 min | Performance regression; system degraded but recoverable |

### TICKET Severity (4 alerts)

**When**: Issues requiring investigation but not immediate response

**Response Time**: < 4 hours during business hours

**Routing**: Slack #selftest-issues + GitHub Issues

| Alert | Threshold | Window | What It Means |
|-------|-----------|--------|---------------|
| `governance_failure_rate_elevated` | >10% failures | 1 hour | Systemic issues with agent/flow/skill definitions |
| `flaky_test_pattern` | 3+ failures + 1+ pass | 24 hours | Test needs stabilization (race conditions, timing issues) |
| `degradation_log_growth` | >10 entries/hour | 1 hour | Multiple subsystems degrading; investigate common cause |
| `optional_step_repeated_failure` | >80% failures | 6 hours | Optional step consistently failing (technical debt signal) |

### INFO Severity (1 alert)

**When**: Trends and long-term health indicators

**Response Time**: Review during sprint planning

**Routing**: Email digest (daily or weekly)

| Alert | Threshold | Window | What It Means |
|-------|-----------|--------|---------------|
| `selftest_success_rate_trending_down` | Avg < 95% | 7 days | Growing technical debt or test fragility |

## Setup

### Prerequisites

1. **Environment Variables** (see `channels.yaml` for full list):
   ```bash
   export PAGERDUTY_SERVICE_KEY="your-service-key"
   export PAGERDUTY_ROUTING_KEY="your-routing-key"
   export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
   export GITHUB_REPO="EffortlessMetrics/flow-studio"
   export GITHUB_TOKEN="ghp_..."
   ```

2. **PagerDuty Service** (for PAGE alerts):
   - Create a service in PagerDuty dashboard
   - Set up escalation policy (on-call rotation)
   - Copy service key and routing key

3. **Slack Webhook** (for TICKET/PAGE alerts):
   - Create a webhook in Slack workspace settings
   - Configure #selftest-issues channel
   - Copy webhook URL

4. **GitHub Token** (for TICKET alerts as issues):
   - Generate a personal access token with `repo` scope
   - Grant write access to issues

### Configuration

All alert policies are defined in YAML and can be version-controlled. No external dashboards required for initial setup.

**For production use**, integrate with your observability platform:

1. **Prometheus + Alertmanager**:
   ```bash
   # Load alert rules
   promtool check rules selftest_alerts.yaml

   # Configure Alertmanager with channels.yaml routing
   ```

2. **Datadog**:
   ```bash
   # Convert YAML to Datadog monitors
   python scripts/convert_to_datadog.py selftest_alerts.yaml
   ```

3. **Grafana**:
   ```bash
   # Import as alert rules via provisioning
   cp selftest_alerts.yaml /etc/grafana/provisioning/alerting/
   ```

### Local Testing

Test alert routing without triggering real alerts:

```bash
# Validate YAML syntax
yamllint selftest_alerts.yaml channels.yaml

# Test Slack webhook
curl -X POST "${SLACK_WEBHOOK_URL}" \
  -H 'Content-Type: application/json' \
  -d '{"text": "Test alert from selftest system"}'

# Test GitHub issue creation (dry-run)
gh issue create \
  --repo "${GITHUB_REPO}" \
  --title "[Test] Selftest Alert" \
  --body "This is a test issue. Safe to close." \
  --label "selftest,test"
```

## Alert Response Workflow

### When You Get Paged

1. **Acknowledge** the PagerDuty alert (you have 15 minutes SLA)

2. **Gather context**:
   ```bash
   # Generate full diagnostic bundle
   make selftest-incident-pack

   # This creates: selftest_incident_<timestamp>.tar.gz
   ```

3. **Review the incident pack** (see "Incident Pack Contents" below)

4. **Follow the runbook** linked in the alert:
   - `docs/runbooks/kernel_failure.md`
   - `docs/runbooks/blocked_test.md`
   - `docs/runbooks/performance_degradation.md`

5. **Mitigate** the issue:
   - For kernel failures: fix Python syntax/import errors
   - For blocked tests: check config/dependencies
   - For performance: identify and optimize slow tests

6. **Resolve** the PagerDuty incident (auto-resolves after 30m if metrics recover)

7. **Document** learnings in the runbook

### When You Get a TICKET Alert

1. **Review** the Slack message and GitHub issue

2. **Triage** severity:
   - Is this affecting CI? Escalate to PAGE
   - Can it wait until next sprint? Keep as TICKET
   - Is it a known issue? Link to existing issue and close

3. **Investigate**:
   ```bash
   # Check degradation log
   make selftest-degradation-log

   # Run validation
   make validate-swarm --strict

   # Generate incident pack if needed
   make selftest-incident-pack
   ```

4. **Fix** or **defer**:
   - Apply immediate fix if trivial
   - Schedule for next sprint if complex
   - Add to backlog if low priority

5. **Close** the GitHub issue when resolved

## Incident Pack

The incident pack is a diagnostic bundle for troubleshooting selftest failures.

### Generate

```bash
make selftest-incident-pack
```

This creates: `selftest_incident_<timestamp>.tar.gz`

### Contents

```
selftest_incident_20251201_123456/
├── manifest.json           # Index of all artifacts
├── README.txt              # Explains contents and context
├── selftest_output.json    # Full selftest run (JSON v2 format)
├── selftest_plan.json      # /api/selftest/plan response
├── platform_status.json    # /platform/status response
├── degradation_log.json    # Current degradation log
├── recent_commits.txt      # Last 10 commits
├── ci_logs/                # Recent CI workflow logs
│   ├── latest_run.log
│   └── previous_runs.log
└── environment.txt         # Python version, dependencies, git status
```

### Use Cases

1. **Attach to PagerDuty incident** — Provides on-call engineer full context
2. **Attach to GitHub issue** — Documents the failure state for async investigation
3. **Share with team** — Send via Slack when multiple people are investigating
4. **Archive for postmortems** — Include in incident reports

### Manual Collection

If `make selftest-incident-pack` fails, collect manually:

```bash
mkdir -p /tmp/selftest_incident

# Run selftest
uv run swarm/tools/selftest.py --json-v2 > /tmp/selftest_incident/selftest_output.json

# Get API responses
curl http://localhost:5000/api/selftest/plan > /tmp/selftest_incident/selftest_plan.json
curl http://localhost:5000/platform/status > /tmp/selftest_incident/platform_status.json
curl http://localhost:5000/platform/degradation-log > /tmp/selftest_incident/degradation_log.json

# Get git context
git log -10 --oneline > /tmp/selftest_incident/recent_commits.txt
git status > /tmp/selftest_incident/git_status.txt

# Package
tar -czf selftest_incident_manual.tar.gz -C /tmp selftest_incident
```

## Alert Maintenance

### Adding a New Alert

1. **Define the alert** in `selftest_alerts.yaml`:
   ```yaml
   - name: new_alert_name
     severity: TICKET  # or PAGE, INFO
     description: What this alert means
     query: Metric query or threshold logic
     threshold: 0.10
     window: 1h
     slo_reference: related_slo_name
     remediation_hint: How to fix this
     dashboard_link: "http://..."
     runbook: "docs/runbooks/new_alert.md"
   ```

2. **Add routing** in `channels.yaml`:
   ```yaml
   slack:
     alerts:
       - new_alert_name
   ```

3. **Create runbook** at `docs/runbooks/new_alert.md`

4. **Test**:
   ```bash
   # Validate syntax
   yamllint selftest_alerts.yaml

   # Verify metrics exist
   curl http://localhost:5000/metrics | grep new_alert_metric
   ```

5. **Document** in this README

### Tuning Thresholds

If alerts are **too noisy**:

1. Check alert history: How often does it fire?
2. Review false positive rate: Were they real issues?
3. Adjust threshold or window:
   - Increase threshold (e.g., 5% → 10%)
   - Lengthen window (e.g., 5m → 15m)
4. Consider downgrading severity (PAGE → TICKET)

If alerts are **missing real issues**:

1. Check SLO violations: Are we meeting SLOs despite issues?
2. Review incident history: Were there undetected failures?
3. Adjust threshold or window:
   - Decrease threshold (e.g., 10% → 5%)
   - Shorten window (e.g., 1h → 15m)
4. Consider adding a new alert for the gap

### Disabling an Alert

To temporarily disable an alert:

```yaml
- name: flaky_test_pattern
  enabled: false  # Add this field
  severity: TICKET
  # ... rest of config
```

To permanently remove:

1. Delete from `selftest_alerts.yaml`
2. Remove from channel routing in `channels.yaml`
3. Update this README
4. Archive the runbook (move to `docs/runbooks/archived/`)

## Metrics Reference

All alerts are based on metrics exposed by the selftest system. See `observability/metrics/README.md` for full metric catalog.

**Key metrics used by alerts**:

- `selftest_step_failures` (counter, labeled by tier/step)
- `selftest_step_status` (gauge, labeled by status: PASS/FAIL/BLOCKED)
- `selftest_duration_seconds` (histogram)
- `selftest_success_rate` (gauge, 0.0-1.0)
- `degradation_log_entries_total` (counter)

## Escalation Policy

**If alert is not resolved within SLA**:

1. **PAGE alerts** (15m SLA):
   - PagerDuty escalates to secondary on-call
   - Slack mentions @oncall-secondary
   - Email sent to swarm-leads@

2. **TICKET alerts** (4h SLA during business hours):
   - GitHub issue auto-assigned to swarm-leads
   - Slack reminder posted to #selftest-issues
   - No PagerDuty escalation (async response acceptable)

**If multiple PAGE alerts fire simultaneously**:

- Indicates systemic failure (e.g., infrastructure outage)
- Escalate to swarm-leads immediately
- Consider declaring a P0 incident
- Generate incident pack and share with incident commander

## FAQ

**Q: Why are some alerts marked INFO but still monitored?**

A: INFO alerts track trends for sprint planning. They don't require immediate action but help identify growing technical debt.

**Q: Can I test alerts without triggering real pages?**

A: Yes. Set environment variables to point to test channels:
```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/.../test-channel"
export PAGERDUTY_SERVICE_KEY="test-service-key"
```

**Q: How do I silence alerts during maintenance?**

A: Use your alerting platform's maintenance window feature:
- PagerDuty: Maintenance Windows
- Alertmanager: Silences
- Datadog: Downtimes

**Q: What if the incident pack command fails?**

A: Fall back to manual collection (see "Manual Collection" section above) or use `/api/selftest/plan` for minimal diagnostics.

**Q: How often should I review alert policies?**

A: Quarterly, or after any major system change. Review:
- Alert firing frequency (aim for <5 false positives/week)
- SLO violations vs alert coverage
- Runbook accuracy and completeness

## References

- SLO Definitions: `observability/slos/selftest_slos.yaml`
- Metrics Catalog: `observability/metrics/README.md`
- Selftest Documentation: `swarm/SELFTEST_SYSTEM.md`
- Runbooks: `docs/runbooks/`
- Incident Pack Script: `swarm/tools/selftest_incident_pack.py`

## Support

For questions or issues with the alert system:

1. Check runbooks in `docs/runbooks/`
2. Review degradation log: `make selftest-degradation-log`
3. Generate incident pack: `make selftest-incident-pack`
4. Post in #selftest-issues on Slack
5. File a GitHub issue with `alert-system` label

---

**Last Updated**: 2025-12-01
**Maintainer**: swarm-team
**Version**: 1.0
