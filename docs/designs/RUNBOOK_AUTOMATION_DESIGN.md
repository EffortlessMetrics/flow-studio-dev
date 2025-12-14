# P4.4: Runbook Automation Design

**Status**: Proposed
**Author**: ADR Author Agent
**Date**: 2025-12-01
**Version**: 1.0

---

## 1. Problem Statement

### Current State

When selftest alerts fire (via PagerDuty, Slack, or other channels), operators must:

1. Wake up or context-switch to the alert
2. SSH/access the affected environment
3. Manually run `make selftest-incident-pack`
4. Manually run `make selftest-suggest-remediation`
5. Capture git status and recent commits
6. Upload diagnostics to incident channel
7. Create or update GitHub issue if not exists

### Pain Points

| Pain | Impact | Frequency |
|------|--------|-----------|
| **Delayed diagnostics** | MTTR increased by 5-15 minutes for initial context | Every incident |
| **Inconsistent response** | Some operators forget steps; diagnostics vary in quality | ~30% of incidents |
| **Cognitive load at 3 AM** | Sleep-deprived humans make mistakes | After-hours pages |
| **Manual toil** | Repetitive commands that could be automated | Every incident |
| **Context fragmentation** | Diagnostics scattered across terminal, Slack, GitHub | Every incident |

### Goal

**Auto-gather diagnostics when alerts fire**, reducing MTTR by 5-10 minutes and ensuring consistent first-response artifacts regardless of who is on-call.

### Non-Goals

- **Auto-remediation**: This design is read-only; humans decide what to execute
- **Replacing on-call**: Automation assists humans, does not replace judgment
- **Complex orchestration**: We avoid multi-step workflows that could fail silently

---

## 2. Architecture Overview

```
                           ALERT SOURCES
                    +-----------------------+
                    |   PagerDuty          |
                    |   Alertmanager       |
                    |   GitHub Actions     |
                    |   Slack Command      |
                    +-----------+-----------+
                                |
                                v
                    +-----------------------+
                    |   WEBHOOK GATEWAY    |
                    |   (Lambda/Cloud Fn)  |
                    |                       |
                    |   - Verify signature  |
                    |   - Parse payload     |
                    |   - Rate limit        |
                    +-----------+-----------+
                                |
                                v
                    +-----------------------+
                    |   DIAGNOSTIC RUNNER  |
                    |                       |
                    |   - incident-pack     |
                    |   - suggest-remed     |
                    |   - git status        |
                    |   - recent commits    |
                    +-----------+-----------+
                                |
                    +-----------+-----------+
                    |                       |
                    v                       v
        +-----------------+     +-----------------+
        |   INCIDENT      |     |   ARTIFACT      |
        |   CHANNEL       |     |   STORAGE       |
        |   (Slack/PD)    |     |   (S3/GCS)      |
        +-----------------+     +-----------------+
                    |
                    v
        +-----------------+
        |   GITHUB ISSUE  |
        |   (if needed)   |
        +-----------------+
```

### Data Flow

1. **Alert fires** from any configured source
2. **Webhook gateway** receives, verifies, and normalizes the event
3. **Diagnostic runner** executes `selftest-incident-pack` and `suggest-remediation`
4. **Artifacts** uploaded to storage bucket with unique incident ID
5. **Summary posted** to incident channel with download link
6. **GitHub issue created** if configured and not duplicate

---

## 3. Trigger Events

| Event | Source | Alert Type | Auto-Action |
|-------|--------|------------|-------------|
| Kernel failure | Selftest alert | PAGE | Full incident pack + page attachment |
| Governance failure | Selftest alert | TICKET | Incident pack + GitHub issue |
| CI workflow failure | GitHub Actions | TICKET | Selftest run + suggest remediation |
| Manual trigger | Slack command | N/A | Run specified diagnostics on-demand |
| Blocked test detected | Selftest alert | PAGE | Full incident pack + immediate notify |
| Duration SLO breach | Selftest alert | PAGE | Performance diagnostics |

### Event Priority Mapping

```yaml
event_priorities:
  kernel_failure:
    priority: P1
    timeout: 60s        # Max time to gather diagnostics
    artifacts: full     # incident-pack + suggest + git + CI

  governance_failure:
    priority: P2
    timeout: 120s
    artifacts: standard # incident-pack + suggest

  ci_failure:
    priority: P3
    timeout: 180s
    artifacts: minimal  # selftest output + git status

  manual_trigger:
    priority: P4
    timeout: 300s
    artifacts: custom   # User-specified
```

---

## 4. Webhook Endpoints

### Endpoint Specification

```
POST /webhooks/pagerduty
POST /webhooks/alertmanager
POST /webhooks/github-actions
POST /webhooks/slack-command
GET  /webhooks/health
```

### PagerDuty Webhook

```yaml
path: /webhooks/pagerduty
method: POST
authentication:
  type: signature
  header: X-PagerDuty-Signature
  algorithm: HMAC-SHA256
  secret: ${PAGERDUTY_WEBHOOK_SECRET}

payload_schema:
  event:
    event_type: incident.triggered | incident.acknowledged | incident.resolved
    incident:
      id: string
      title: string
      urgency: high | low
      service:
        id: string
        name: string
      assignments:
        - assignee:
            id: string
            email: string

action_mapping:
  incident.triggered: run_incident_pack
  incident.acknowledged: attach_diagnostics
  incident.resolved: archive_artifacts
```

### Alertmanager Webhook

```yaml
path: /webhooks/alertmanager
method: POST
authentication:
  type: bearer
  header: Authorization
  token: ${ALERTMANAGER_BEARER_TOKEN}

payload_schema:
  version: "4"
  status: firing | resolved
  alerts:
    - labels:
        alertname: string
        severity: PAGE | TICKET | INFO
        tier: KERNEL | GOVERNANCE | OPTIONAL
      annotations:
        summary: string
        description: string
        runbook_url: string
      startsAt: ISO8601
      endsAt: ISO8601

action_mapping:
  firing:
    PAGE: run_full_incident_pack
    TICKET: run_standard_incident_pack
    INFO: log_only
  resolved: archive_artifacts
```

### GitHub Actions Webhook

```yaml
path: /webhooks/github-actions
method: POST
authentication:
  type: signature
  header: X-Hub-Signature-256
  algorithm: HMAC-SHA256
  secret: ${GITHUB_WEBHOOK_SECRET}

payload_schema:
  action: completed | requested
  workflow_run:
    id: number
    name: string
    conclusion: success | failure | cancelled
    head_branch: string
    head_sha: string
    html_url: string

action_mapping:
  completed:
    failure: run_ci_diagnostics
    cancelled: log_only
    success: no_action
```

### Slack Command Webhook

```yaml
path: /webhooks/slack-command
method: POST
authentication:
  type: signature
  header: X-Slack-Signature
  algorithm: HMAC-SHA256
  secret: ${SLACK_SIGNING_SECRET}

commands:
  /selftest status:
    action: get_current_status
    response_type: ephemeral

  /selftest diagnose:
    action: run_incident_pack
    response_type: in_channel

  /selftest suggest:
    action: run_suggest_remediation
    response_type: ephemeral

  /selftest history:
    action: get_recent_failures
    response_type: ephemeral

  /selftest help:
    action: show_help
    response_type: ephemeral
```

---

## 5. Auto-Diagnostic Actions

### Action Sequence

```
                    START
                      |
                      v
              +-------+-------+
              |  Clone repo   |
              |  (if needed)  |
              +-------+-------+
                      |
                      v
              +-------+-------+
              | Run incident  |
              | pack          |
              +-------+-------+
                      |
                      v
              +-------+-------+
              | Run suggest   |
              | remediation   |
              +-------+-------+
                      |
                      v
              +-------+-------+
              | Capture git   |
              | context       |
              +-------+-------+
                      |
                      v
              +-------+-------+
              | Fetch CI logs |
              | (if GitHub)   |
              +-------+-------+
                      |
                      v
              +-------+-------+
              | Package       |
              | artifacts     |
              +-------+-------+
                      |
                      v
              +-------+-------+
              | Upload to     |
              | storage       |
              +-------+-------+
                      |
                      v
              +-------+-------+
              | Post to       |
              | incident      |
              | channel       |
              +-------+-------+
                      |
                      v
              +-------+-------+
              | Create GitHub |
              | issue if new  |
              +-------+-------+
                      |
                      v
                     END
```

### Diagnostic Commands

```bash
# Step 1: Run incident pack
make selftest-incident-pack
# Output: selftest_incident_<timestamp>.tar.gz

# Step 2: Run suggest remediation
uv run swarm/tools/selftest_suggest_remediation.py --json > remediation_suggestions.json

# Step 3: Capture git context
git log -10 --oneline > recent_commits.txt
git status > git_status.txt
git diff --stat HEAD~5..HEAD > recent_changes.txt

# Step 4: CI logs (if applicable)
gh run view $RUN_ID --log > ci_log.txt 2>/dev/null || echo "CI logs unavailable" > ci_log.txt

# Step 5: Package
tar -czf diagnostics_$INCIDENT_ID.tar.gz \
  selftest_incident_*.tar.gz \
  remediation_suggestions.json \
  recent_commits.txt \
  git_status.txt \
  recent_changes.txt \
  ci_log.txt
```

### Artifact Schema

```json
{
  "incident_id": "inc-20251201-143022-abc123",
  "generated_at": "2025-12-01T14:30:22Z",
  "trigger": {
    "source": "pagerduty",
    "event_type": "incident.triggered",
    "alert_name": "kernel_failure_rate_critical"
  },
  "artifacts": {
    "incident_pack": {
      "file": "selftest_incident_20251201_143022.tar.gz",
      "size_bytes": 524288,
      "contents": ["selftest_output.json", "environment.txt", "..."]
    },
    "remediation": {
      "file": "remediation_suggestions.json",
      "actionable_count": 3,
      "unmatched_count": 1
    },
    "git_context": {
      "branch": "feat/selftest-resilience",
      "commit": "abc123def456",
      "recent_commits_count": 10
    }
  },
  "upload": {
    "bucket": "selftest-diagnostics",
    "key": "incidents/inc-20251201-143022-abc123/diagnostics.tar.gz",
    "url": "https://storage.example.com/..."
  },
  "notifications_sent": {
    "slack": true,
    "github_issue": "https://github.com/org/repo/issues/123"
  }
}
```

---

## 6. Slack Bot Commands

### Command Reference

| Command | Description | Response Type | Permissions |
|---------|-------------|---------------|-------------|
| `/selftest status` | Show current selftest status | Ephemeral | All |
| `/selftest diagnose` | Run incident pack now | In-channel | Operators |
| `/selftest suggest` | Get remediation suggestions | Ephemeral | All |
| `/selftest history [n]` | Show recent n failures (default: 5) | Ephemeral | All |
| `/selftest help` | Show command help | Ephemeral | All |

### Example Interactions

**Status Check:**
```
User: /selftest status

Bot: *Selftest Status* (as of 2025-12-01 14:30:22 UTC)

  KERNEL: PASS (3/3 steps)
  GOVERNANCE: WARN (5/6 steps - 1 degraded)
  OPTIONAL: PASS (2/2 steps)

Degraded steps:
  - `bdd` - Override active until 2025-12-02 09:00 UTC (by @alice)

Last full run: 2 minutes ago
Next scheduled: in 13 minutes
```

**Diagnose Request:**
```
User: /selftest diagnose

Bot: Running incident pack... (this may take 60-90 seconds)

Bot: *Incident Pack Complete*

Diagnostics bundle: `inc-20251201-143522-xyz789`
Download: https://storage.example.com/...

Summary:
  - Selftest status: 8/10 passed, 1 failed, 1 skipped
  - Failed step: `policy-tests` (GOVERNANCE tier)
  - 2 actionable remediation suggestions

Suggested commands:
  1. `make policy-lint` - Re-run policy validation
  2. `uv run swarm/tools/validate_swarm.py --strict` - Check agent definitions

Full details attached to current incident.
```

**Remediation Suggestions:**
```
User: /selftest suggest

Bot: *Remediation Suggestions* (based on latest degradation log)

[1/2] `POLICY_VIOLATION`
  Step: policy-tests (GOVERNANCE)
  Error: "OPA policy 'require_adr' failed: Missing ADR reference"

  Suggested fix:
    1. Check ADR exists: `ls docs/adr/`
    2. Re-run policy: `make policy-lint`

[2/2] `AGENT_COLOR_MISMATCH`
  Step: agents-governance (GOVERNANCE)
  Error: "Agent 'foo' has color 'blue' but role_family 'implementation' requires 'green'"

  Suggested fix:
    1. Edit config: `$EDITOR swarm/config/agents/foo.yaml`
    2. Change `color: blue` to `color: green`
    3. Regenerate: `make gen-adapters && make check-adapters`

Run `/selftest diagnose` for full incident pack.
```

---

## 7. Implementation Options

### Option A: Serverless (Recommended)

**Architecture:**
- AWS Lambda or Google Cloud Functions
- API Gateway for webhook endpoints
- S3/GCS for artifact storage
- EventBridge/Cloud Scheduler for health checks

**Pros:**
- Zero infrastructure management
- Auto-scaling to handle burst alerts
- Pay-per-invocation (~$0 for low volume)
- Built-in retry and dead-letter queues

**Cons:**
- Cold start latency (1-3 seconds)
- Execution time limit (15 min Lambda, 9 min Cloud Functions)
- Vendor lock-in (minor, easily portable)

**Cost Estimate:**
- 100 alerts/month: ~$0.01 (effectively free)
- 1,000 alerts/month: ~$0.10
- Storage: $0.02/GB/month

**Implementation Effort:**
- Initial setup: 2-3 days
- Maintenance: Low (serverless handles ops)

### Option B: Always-on Service

**Architecture:**
- Kubernetes deployment (2 replicas)
- Persistent WebSocket connections for real-time
- Redis for state/caching
- PostgreSQL for audit log

**Pros:**
- No cold starts
- Real-time streaming of diagnostic output
- Full control over execution environment
- WebSocket support for live updates

**Cons:**
- Higher operational cost (~$50-100/month minimum)
- Infrastructure to manage
- Overkill for low-volume alerting

**Cost Estimate:**
- Kubernetes cluster: $50-100/month
- Monitoring: $20/month
- Storage: $10/month

**Implementation Effort:**
- Initial setup: 1-2 weeks
- Maintenance: Medium (patches, scaling, monitoring)

### Option C: GitHub Actions Only

**Architecture:**
- `repository_dispatch` events trigger workflows
- Workflow runs diagnostics in Actions environment
- Artifacts uploaded to GitHub Releases or Actions artifacts
- Notifications via gh CLI or API

**Pros:**
- No additional infrastructure
- Already integrated with repo
- Free for public repos, generous limits for private
- Familiar to developers

**Cons:**
- Limited to GitHub-triggered events (no PagerDuty direct integration)
- Workflow queue delays possible
- Actions minutes quotas
- Cannot receive webhooks from external alerting systems

**Cost Estimate:**
- Free tier: 2,000 minutes/month (private repos)
- Additional minutes: $0.008/minute

**Implementation Effort:**
- Initial setup: 1 day
- Maintenance: Very low

### Recommendation: Hybrid Approach

**Phase 1: GitHub Actions (Week 1)**
- Implement `repository_dispatch` workflow for CI failures
- Add manual workflow trigger for `/selftest diagnose` equivalent
- Store artifacts in Actions artifacts

**Phase 2: Slack Integration (Week 2)**
- Add Slack bot with slash commands
- Use GitHub Actions as backend (trigger via API)
- Real-time status without infrastructure

**Phase 3: Full Webhook Service (Optional, Week 3-4)**
- Deploy serverless functions for PagerDuty/Alertmanager
- Add artifact storage in cloud bucket
- Enable direct alert-to-diagnostic pipeline

This phased approach delivers value quickly while avoiding premature infrastructure investment.

---

## 8. Security Considerations

### Authentication & Authorization

| Endpoint | Auth Method | Verification |
|----------|-------------|--------------|
| PagerDuty | HMAC-SHA256 signature | `X-PagerDuty-Signature` header |
| Alertmanager | Bearer token | `Authorization: Bearer <token>` |
| GitHub | HMAC-SHA256 signature | `X-Hub-Signature-256` header |
| Slack | HMAC-SHA256 signature | `X-Slack-Signature` header |

### Secret Management

```yaml
# All secrets stored in environment, never in code
required_secrets:
  - PAGERDUTY_WEBHOOK_SECRET     # For webhook signature verification
  - PAGERDUTY_SERVICE_KEY        # For incident updates
  - ALERTMANAGER_BEARER_TOKEN    # For webhook auth
  - GITHUB_WEBHOOK_SECRET        # For webhook signature
  - GITHUB_TOKEN                 # For issue creation (PAT or App)
  - SLACK_SIGNING_SECRET         # For Slack command verification
  - SLACK_BOT_TOKEN              # For posting messages
  - ARTIFACT_STORAGE_KEY         # For S3/GCS access
```

### Rate Limiting

```yaml
rate_limits:
  global:
    requests_per_minute: 60
    burst: 10

  per_source:
    pagerduty: 30/min
    alertmanager: 30/min
    github: 30/min
    slack: 60/min

  per_action:
    incident_pack: 10/hour    # Expensive operation
    suggest_remediation: 30/min
    status_check: 120/min
```

### Audit Logging

All webhook invocations and actions are logged:

```json
{
  "timestamp": "2025-12-01T14:30:22Z",
  "event_id": "evt-abc123",
  "source": "pagerduty",
  "action": "run_incident_pack",
  "trigger": {
    "incident_id": "P123ABC",
    "alert_name": "kernel_failure_rate_critical",
    "urgency": "high"
  },
  "result": {
    "status": "success",
    "duration_ms": 45000,
    "artifacts_uploaded": true,
    "notifications_sent": ["slack", "github_issue"]
  },
  "actor": {
    "type": "webhook",
    "source_ip": "203.0.113.50",
    "verified": true
  }
}
```

### Access Control

| Role | Slack Commands | Webhook Access | Artifact Access |
|------|----------------|----------------|-----------------|
| All users | status, help | N/A | Read own team |
| Operators | diagnose, suggest, history | N/A | Read/write |
| Admins | All + config | Configure | Full access |
| Automation | N/A | Full | Write |

---

## 9. Configuration Schema

```yaml
# swarm/config/runbook_automation.yaml
version: "1.0"

enabled: true

# Trigger sources
triggers:
  pagerduty:
    enabled: true
    signing_secret: ${PAGERDUTY_WEBHOOK_SECRET}
    events:
      - incident.triggered
      - incident.acknowledged

  alertmanager:
    enabled: true
    bearer_token: ${ALERTMANAGER_BEARER_TOKEN}
    severity_filter: [PAGE, TICKET]

  github:
    enabled: true
    webhook_secret: ${GITHUB_WEBHOOK_SECRET}
    events:
      - workflow_run.completed
    workflow_filter:
      - "CI"
      - "Selftest"

  slack:
    enabled: true
    signing_secret: ${SLACK_SIGNING_SECRET}
    bot_token: ${SLACK_BOT_TOKEN}
    allowed_channels:
      - "#selftest-alerts"
      - "#oncall"

# Actions per event type
actions:
  on_kernel_failure:
    - name: incident_pack
      timeout: 120s
    - name: suggest_remediation
      timeout: 30s
    - name: create_issue
      dedupe_window: 24h
    - name: post_to_slack
      channel: "#selftest-alerts"
      mention: "@oncall"

  on_governance_failure:
    - name: incident_pack
      timeout: 180s
    - name: suggest_remediation
      timeout: 30s
    - name: create_issue
      dedupe_window: 24h

  on_ci_failure:
    - name: selftest_run
      timeout: 300s
    - name: suggest_remediation
      timeout: 30s
    - name: comment_on_pr

  on_manual_trigger:
    - name: incident_pack
      timeout: 300s
    - name: suggest_remediation
      timeout: 60s

# Artifact storage
artifacts:
  storage:
    type: s3  # s3 | gcs | local
    bucket: selftest-diagnostics
    region: us-east-1
    prefix: incidents/
    retention_days: 90

  upload:
    compress: true
    max_size_mb: 100

# Notifications
notifications:
  slack:
    channel: "#selftest-alerts"
    thread_replies: true

  github:
    create_issue: true
    issue_labels: [selftest, automated, incident]
    dedupe_window: 24h

  pagerduty:
    attach_to_incident: true
    add_note: true

# Runtime limits
limits:
  max_concurrent_runs: 5
  max_queue_depth: 20
  diagnostic_timeout: 300s
  upload_timeout: 60s

# Health check
health:
  enabled: true
  interval: 60s
  endpoints:
    - name: storage
      type: s3_bucket
      bucket: selftest-diagnostics
    - name: slack
      type: webhook
      url: ${SLACK_WEBHOOK_URL}
```

---

## 10. Implementation Plan

### Phase 1: GitHub Actions Foundation (Week 1)

**Goal**: Automate diagnostics for CI failures with zero new infrastructure.

**Tasks**:

1. **Create diagnostic workflow** (Day 1-2)
   ```yaml
   # .github/workflows/selftest-diagnostics.yml
   name: Selftest Diagnostics
   on:
     workflow_run:
       workflows: [CI]
       types: [completed]
       conclusions: [failure]
     workflow_dispatch:
       inputs:
         incident_id:
           description: 'Incident ID for tracking'
           required: false
   ```

2. **Add incident pack action** (Day 2-3)
   - Wrapper action for `make selftest-incident-pack`
   - Upload artifacts to workflow run
   - Post summary to PR if applicable

3. **Add manual trigger support** (Day 3-4)
   - `repository_dispatch` for external triggers
   - Workflow inputs for customization

4. **Document and test** (Day 4-5)
   - Update runbooks with new automation
   - Test with simulated failures
   - Measure MTTR improvement

**Deliverables**:
- [ ] Diagnostic workflow file
- [ ] Updated Makefile targets
- [ ] Documentation in `docs/runbooks/automated_diagnostics.md`

### Phase 2: Slack Integration (Week 2)

**Goal**: Enable on-demand diagnostics from Slack.

**Tasks**:

1. **Create Slack app** (Day 1)
   - Register app in Slack workspace
   - Configure slash commands
   - Set up OAuth scopes

2. **Implement command handlers** (Day 2-3)
   - `/selftest status` - Read-only, immediate response
   - `/selftest diagnose` - Trigger GitHub Action, post result
   - `/selftest suggest` - Quick remediation lookup
   - `/selftest history` - Recent failures from API

3. **Connect to GitHub Actions** (Day 3-4)
   - Slack command triggers `repository_dispatch`
   - GitHub Action posts result back to Slack
   - Thread replies for context

4. **Test and deploy** (Day 4-5)
   - Test in staging workspace
   - Roll out to production
   - Train operators

**Deliverables**:
- [ ] Slack app configuration
- [ ] Command handler code (Lambda or GitHub Action)
- [ ] Updated operator runbook

### Phase 3: Full Webhook Service (Week 3-4, Optional)

**Goal**: Direct integration with PagerDuty and Alertmanager.

**Tasks**:

1. **Deploy serverless functions** (Day 1-3)
   - API Gateway + Lambda (or Cloud Functions)
   - Webhook signature verification
   - Event normalization

2. **Implement artifact storage** (Day 3-5)
   - S3/GCS bucket setup
   - Upload/download handlers
   - Retention policy

3. **Connect alert sources** (Day 5-7)
   - PagerDuty webhook configuration
   - Alertmanager webhook configuration
   - Auto-attach diagnostics to incidents

4. **Add observability** (Day 7-10)
   - Metrics for webhook processing
   - Alerts for automation failures
   - Dashboard for diagnostic runs

**Deliverables**:
- [ ] Serverless function code
- [ ] Infrastructure-as-code (Terraform/CDK)
- [ ] Monitoring dashboards
- [ ] Runbook updates

---

## 11. Testing Strategy

### Unit Tests

```python
# tests/test_webhook_handlers.py

def test_pagerduty_signature_verification():
    """Verify PagerDuty webhook signatures are validated."""

def test_alertmanager_payload_parsing():
    """Verify Alertmanager payloads are correctly parsed."""

def test_action_mapping():
    """Verify correct actions are triggered for each event type."""

def test_rate_limiting():
    """Verify rate limits are enforced."""
```

### Integration Tests

```python
# tests/integration/test_diagnostics_pipeline.py

def test_incident_pack_generation():
    """End-to-end test of incident pack generation."""

def test_artifact_upload():
    """Verify artifacts are uploaded to storage."""

def test_slack_notification():
    """Verify Slack messages are posted correctly."""

def test_github_issue_creation():
    """Verify GitHub issues are created with correct content."""
```

### Mock Webhook Payloads

```json
// tests/fixtures/pagerduty_incident_triggered.json
{
  "event": {
    "event_type": "incident.triggered",
    "occurred_at": "2025-12-01T14:30:22Z",
    "incident": {
      "id": "P123ABC",
      "title": "[PAGE] Selftest Alert: kernel_failure_rate_critical",
      "urgency": "high",
      "service": {
        "id": "PSERVICE1",
        "name": "Selftest Monitor"
      }
    }
  }
}
```

### E2E Test Plan

| Test Case | Trigger | Expected Outcome | Frequency |
|-----------|---------|------------------|-----------|
| PagerDuty page | Test incident | Diagnostics attached | Weekly |
| Alertmanager firing | Test alert | Slack notification | Weekly |
| GitHub CI failure | Intentional fail | PR comment | Daily |
| Slack /selftest diagnose | Manual command | Diagnostics posted | Daily |
| Rate limit exceeded | Burst requests | 429 response | On change |

### Test Slack Workspace

- Create dedicated `#selftest-testing` channel
- Use test PagerDuty service for dry runs
- Maintain test GitHub repo for CI integration tests

---

## 12. Success Metrics

### Key Performance Indicators

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| **Time to first diagnostic** | 5-15 min | < 2 min | P95 latency |
| **Diagnostic completeness** | 70% | 95% | % incidents with full pack |
| **Operator toil reduction** | 0% | 80% | Manual commands eliminated |
| **False positive rate** | N/A | < 5% | Spurious automation runs |

### Observability

```yaml
# Metrics to track
metrics:
  - selftest_automation_runs_total
    labels: [source, event_type, status]

  - selftest_automation_duration_seconds
    labels: [source, action]
    type: histogram

  - selftest_automation_errors_total
    labels: [source, error_type]

  - selftest_artifacts_uploaded_total
    labels: [destination]

  - selftest_notifications_sent_total
    labels: [channel, status]
```

### Rollback Criteria

Automation will be disabled if:
- Error rate > 20% for 1 hour
- P95 latency > 5 minutes
- Storage costs exceed budget by 2x
- Operators report degraded experience

---

## 13. Appendix

### A. Reference Implementation: GitHub Actions Workflow

```yaml
# .github/workflows/selftest-diagnostics.yml
name: Selftest Diagnostics

on:
  workflow_run:
    workflows: [CI]
    types: [completed]
  workflow_dispatch:
    inputs:
      incident_id:
        description: 'Incident ID'
        required: false
        default: 'manual'

jobs:
  diagnose:
    if: ${{ github.event.workflow_run.conclusion == 'failure' || github.event_name == 'workflow_dispatch' }}
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          pip install uv
          uv sync --frozen

      - name: Run incident pack
        run: make selftest-incident-pack

      - name: Run suggest remediation
        run: |
          uv run swarm/tools/selftest_suggest_remediation.py --json \
            > remediation_suggestions.json || true

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: diagnostics-${{ github.run_id }}
          path: |
            selftest_incident_*.tar.gz
            remediation_suggestions.json
          retention-days: 30

      - name: Post summary
        if: github.event.workflow_run.pull_request
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const suggestions = JSON.parse(fs.readFileSync('remediation_suggestions.json'));

            const body = `## Selftest Diagnostics

            **Run ID:** ${{ github.run_id }}
            **Triggered by:** ${{ github.event_name }}

            ### Summary
            - Actionable suggestions: ${suggestions.actionable_suggestions}
            - Unmatched issues: ${suggestions.unmatched}

            [Download diagnostics](https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }})
            `;

            github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: body
            });
```

### B. Related Documents

- `swarm/SELFTEST_SYSTEM.md` - Selftest documentation
- `observability/alerts/selftest_alerts.yaml` - Alert definitions
- `observability/alerts/channels.yaml` - Alert routing
- `swarm/tools/selftest_incident_pack.py` - Incident pack implementation
- `swarm/tools/selftest_suggest_remediation.py` - Remediation engine
- `docs/runbooks/` - Operator runbooks

### C. Glossary

| Term | Definition |
|------|------------|
| **Incident Pack** | Tarball containing diagnostic artifacts for troubleshooting |
| **MTTR** | Mean Time To Recovery |
| **PAGE** | Alert severity requiring immediate human response |
| **TICKET** | Alert severity for async investigation |
| **Webhook** | HTTP callback from external service |

---

## 14. Decision

**We choose Option A (Serverless) with a phased rollout starting with GitHub Actions.**

### Rationale

1. **GitHub Actions first** delivers immediate value without infrastructure
2. **Serverless functions** scale naturally and cost nearly nothing at expected volume
3. **Phased approach** allows validation before investment
4. **Slack integration** addresses the most common operator need (on-demand diagnostics)

### Trade-offs Accepted

- Cold start latency is acceptable for alerting use case (not real-time)
- Vendor lock-in is minimal and easily portable
- GitHub Actions limitations accepted for Phase 1 (no external webhook support)

### Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Webhook secret compromise | Low | High | Rotate secrets regularly; audit logs |
| Runaway costs | Low | Medium | Budget alerts; rate limiting |
| Automation failure during incident | Medium | High | Graceful degradation; manual fallback documented |
| Slack app approval delays | Medium | Low | Start with test workspace; parallel approval |

---

**Approval History**

| Date | Approver | Status |
|------|----------|--------|
| 2025-12-01 | ADR Author | Proposed |
