# Flow 6 Production Extensions

This document shows how to extend Flow 6 (Wisdom) from the out-of-the-box artifact-based implementation to real observability platforms.

## Out-of-the-Box (What Works on Clone)

Flow 6 uses **only flow artifacts and git/GitHub**:

- ✅ Verify all flow artifacts exist
- ✅ Analyze test results from Flow 3 (Build)
- ✅ Compare coverage trends (if coverage tools ran)
- ✅ Correlate with GitHub issues (`gh issue list`)
- ✅ Detect regressions via git blame + test failures
- ✅ Compile flow timeline from all artifacts
- ✅ Extract learnings from critiques and receipts
- ✅ Suggest playbook updates based on patterns
- ✅ Create GitHub issues for test gaps
- ✅ Post learnings + action items to PR/issue

**No external infrastructure required**. Every agent completes successfully using flow receipts, git history, and GitHub APIs.

---

## Production Extensions

Most orgs will want to extend Flow 6 to integrate with real observability and incident systems. Here are common patterns:

### Extension 1: Real Metrics (Prometheus, Datadog)

**What to add:**

1. **Metrics Backend**
   - Prometheus server OR Datadog account
   - Query API access
   - Time range configuration (e.g., "last 24h")

2. **New Agent: `metrics-verifier`** (insert before `learning-synthesizer`)

   ```markdown
   ## Inputs
   - `RUN_BASE/plan/observability_spec.md` (expected metrics)
   - `RUN_BASE/deploy/deployment_decision.md` (deployment timestamp)
   - Environment: `METRICS_ENDPOINT` (Prometheus/Datadog URL)

   ## Behavior

   1. Parse observability_spec.md for expected metrics:
      - `http_requests_total`
      - `http_request_duration_seconds`
      - `error_rate`
      - Custom business metrics

   2. Query metrics backend since deployment:
      - Prometheus: `http_requests_total{app="myapp"}[24h]`
      - Datadog: API query for metrics by deployment tag

   3. Verify metrics match spec:
      - Are all expected metrics present?
      - Are values within expected ranges?
      - Any unexpected spikes or drops?

   4. Write `RUN_BASE/wisdom/metrics_verification.md`:
      - Metrics found vs expected
      - Anomalies detected
      - Compliance status (PASS/FAIL per metric)
   ```

3. **Environment Variables**
   ```bash
   export METRICS_ENDPOINT=http://prometheus.prod:9090
   export METRICS_LOOKBACK=24h
   ```

**Benefits**: Verify observability instrumentation is working, detect metrics anomalies, validate SLIs.

---

### Extension 2: Real Logs (ELK, Splunk, CloudWatch)

**What to add:**

1. **Log Aggregation**
   - Elasticsearch/Kibana OR Splunk OR CloudWatch Logs
   - Query API access
   - Log correlation IDs (request IDs, trace IDs)

2. **New Agent: `log-verifier`** (insert before `learning-synthesizer`)

   ```markdown
   ## Inputs
   - `RUN_BASE/plan/observability_spec.md` (expected log patterns)
   - `RUN_BASE/deploy/deployment_decision.md` (deployment timestamp)
   - Environment: `LOGS_ENDPOINT` (ELK/Splunk URL)

   ## Behavior

   1. Parse observability_spec.md for expected log events:
      - Startup logs (e.g., "Server started on port 8080")
      - Error patterns (e.g., "ERROR: Database connection failed")
      - Business events (e.g., "Order created: order_id=...")

   2. Query log backend since deployment:
      - ELK: Search for log level ERROR, WARNING in deployment window
      - Splunk: Query for app=myapp, timestamp > deployment_time
      - CloudWatch: Filter logs by log group + time range

   3. Analyze error patterns:
      - New error types introduced?
      - Error rate increased vs baseline?
      - Expected logs missing?

   4. Write `RUN_BASE/wisdom/log_verification.md`:
      - Error patterns found
      - Baseline vs current error rates
      - Missing expected logs
      - Compliance status
   ```

3. **Environment Variables**
   ```bash
   export LOGS_ENDPOINT=http://elasticsearch.prod:9200
   export LOGS_INDEX=app-logs-*
   ```

**Benefits**: Detect new error patterns, verify log instrumentation, early warning for production issues.

---

### Extension 3: Real Incidents (PagerDuty, Opsgenie)

**What to add:**

1. **Incident Management**
   - PagerDuty OR Opsgenie OR incident.io account
   - API key with read access
   - Incident correlation rules

2. **Update `issue-correlator` agent** (extend from GitHub issues to include incidents)

   ```markdown
   ## Production Mode (Incident Tracking)

   1. Query incident API since deployment:
      - PagerDuty: GET /incidents?since={deploy_time}&service_ids[]={service_id}
      - Opsgenie: GET /v2/alerts?query=createdAt>{deploy_time}

   2. Correlate incidents with this deployment:
      - Filter by service/app name
      - Check incident description for keywords from this change
      - Link via deployment tag or release version

   3. Classify incidents:
      - Directly caused by this deploy (timing + correlation)
      - Possibly related (same service, timing overlap)
      - Unrelated (different service or pre-deployment)

   4. Write `RUN_BASE/wisdom/incident_correlation.md`:
      - Incidents found in deployment window
      - Correlation confidence (HIGH/MEDIUM/LOW)
      - Incident links and summaries
      - Recommended actions (rollback, investigate, monitor)
   ```

3. **Environment Variables**
   ```bash
   export PAGERDUTY_API_KEY=u+abc123...
   export PAGERDUTY_SERVICE_ID=PXYZ789
   # or
   export OPSGENIE_API_KEY=xyz-abc-123
   export OPSGENIE_TEAM=platform
   ```

**Benefits**: Automatic correlation of production incidents with deployments, faster root cause analysis, data-driven rollback decisions.

---

### Extension 4: SLO Tracking

**What to add:**

1. **SLO Definition**
   - SLI metrics (latency, error rate, availability)
   - SLO targets (e.g., "99.9% uptime")
   - Error budget calculation

2. **New Agent: `slo-calculator`** (insert before `learning-synthesizer`)

   ```markdown
   ## Inputs
   - `RUN_BASE/plan/observability_spec.md` (SLO definitions)
   - `RUN_BASE/wisdom/metrics_verification.md`
   - Environment: `METRICS_ENDPOINT`

   ## Behavior

   1. Parse observability_spec.md for SLOs:
      - Availability SLO: 99.9% uptime
      - Latency SLO: p95 < 200ms
      - Error rate SLO: < 1% of requests

   2. Calculate SLI from metrics:
      - Availability: (total_requests - error_requests) / total_requests
      - Latency: histogram_quantile(0.95, http_request_duration_seconds)
      - Error rate: rate(http_requests_total{status=~"5.."}[24h])

   3. Calculate error budget:
      - Budget allowed: (1 - SLO) * total_requests
      - Budget consumed: error_requests
      - Budget remaining: budget_allowed - budget_consumed
      - Burn rate: budget_consumed / time_window

   4. Write `RUN_BASE/wisdom/slo_status.md`:
      - SLI values vs SLO targets
      - Error budget status (% remaining)
      - Burn rate analysis
      - Recommendations (slow down deploys, speed up, etc.)
   ```

3. **Environment Variables**
   ```bash
   export SLO_WINDOW=30d  # rolling window for SLO calculation
   ```

**Benefits**: Data-driven deployment velocity decisions, error budget visibility, proactive alerts before SLO breach.

---

### Extension 5: Cost Analysis

**What to add:**

1. **Cloud Billing API**
   - AWS Cost Explorer OR GCP Billing OR Azure Cost Management
   - API credentials with cost read access
   - Cost allocation tags

2. **Update `test-gap-finder` → `cost-analyzer`** agent

   ```markdown
   ## Inputs
   - `RUN_BASE/plan/work_plan.md` (estimated effort/cost)
   - `RUN_BASE/deploy/deployment_decision.md` (deployment timestamp)
   - Environment: Cloud billing API credentials

   ## Behavior

   1. Query cloud billing API for cost since deployment:
      - AWS: GetCostAndUsage API with service filter
      - GCP: Billing API with project + labels
      - Azure: Cost Management API with resource group

   2. Compare actual vs estimated:
      - Compute costs (EC2, GCE, VMs)
      - Storage costs (S3, GCS, Blob)
      - Network egress
      - Third-party services (RDS, CloudSQL, etc.)

   3. Identify cost anomalies:
      - Costs > 2x estimate → FLAG
      - New unexpected services → FLAG
      - Usage patterns changed → INVESTIGATE

   4. Write `RUN_BASE/wisdom/cost_analysis.md`:
      - Estimated vs actual costs
      - Cost breakdown by service
      - Anomalies and recommendations
      - ROI analysis (if business metrics available)
   ```

3. **Environment Variables**
   ```bash
   export AWS_COST_ALLOCATION_TAG=app:myapp
   # or
   export GCP_BILLING_PROJECT=my-project
   export GCP_BILLING_DATASET=billing_export
   ```

**Benefits**: Early detection of cost overruns, validate cost estimates, optimize resource usage.

---

### Extension 6: Distributed Tracing (Jaeger, Honeycomb)

**What to add:**

1. **Tracing Backend**
   - Jaeger OR Honeycomb OR Datadog APM
   - Trace query API
   - Service map generation

2. **New Agent: `trace-verifier`** (insert before `learning-synthesizer`)

   ```markdown
   ## Inputs
   - `RUN_BASE/plan/observability_spec.md` (expected trace spans)
   - `RUN_BASE/deploy/deployment_decision.md` (deployment timestamp)
   - Environment: `TRACE_ENDPOINT`

   ## Behavior

   1. Parse observability_spec.md for expected traces:
      - Service-to-service calls (e.g., "api → database")
      - Critical paths (e.g., "checkout flow")
      - Latency expectations per span

   2. Query trace backend since deployment:
      - Jaeger: Query for service + time range
      - Honeycomb: BubbleUp analysis for deployment marker

   3. Analyze trace patterns:
      - Are all expected spans present?
      - New unexpected downstream calls?
      - Latency distribution per span
      - Error traces (status code, exceptions)

   4. Write `RUN_BASE/wisdom/trace_verification.md`:
      - Trace coverage (expected vs actual spans)
      - Latency analysis
      - Error traces summary
      - Service dependency changes
   ```

3. **Environment Variables**
   ```bash
   export TRACE_ENDPOINT=http://jaeger.prod:16686
   export TRACE_SERVICE_NAME=myapp
   # or
   export HONEYCOMB_API_KEY=abc123
   export HONEYCOMB_DATASET=production
   ```

**Benefits**: Verify distributed tracing instrumentation, detect new service dependencies, latency regression analysis.

---

## Implementation Checklist

To extend Flow 6 for your organization:

- [ ] Choose observability stack (metrics, logs, traces)
- [ ] Set up API access and credentials
- [ ] Define SLOs in `observability_spec.md` (Flow 2 output)
- [ ] Update relevant agent prompts to detect environment variables
- [ ] Write fallback behavior (if env vars not set, use artifact-based analysis)
- [ ] Test queries against staging environment first
- [ ] Document environment variables in team runbook
- [ ] (Optional) Add metrics-verifier agent
- [ ] (Optional) Add log-verifier agent
- [ ] (Optional) Add slo-calculator agent
- [ ] (Optional) Add cost-analyzer agent
- [ ] (Optional) Add trace-verifier agent

---

## Architecture Pattern

The key pattern is **graceful extension**:

1. **Base layer** (ships in repo): Artifact-based analysis (test output, git blame, GitHub issues)
2. **Detection layer** (in agent prompts): Check for environment variables
3. **Extension layer** (org-specific): If env vars present, query real observability systems
4. **Synthesis**: Combine artifact analysis + live data into unified learnings

This way:
- ✅ Repo works out of the box (demo/learning)
- ✅ Production teams extend by setting env vars + updating prompts
- ✅ No breaking changes to base swarm
- ✅ Clear audit trail in artifacts regardless of observability platform
- ✅ Learnings always extracted, even without live data

---

## Example: Multi-Platform Setup

A production team might use:

```bash
# Metrics
export METRICS_ENDPOINT=http://prometheus.prod:9090

# Logs
export LOGS_ENDPOINT=http://elasticsearch.prod:9200
export LOGS_INDEX=app-logs-*

# Incidents
export PAGERDUTY_API_KEY=u+abc123...
export PAGERDUTY_SERVICE_ID=PXYZ789

# Traces
export TRACE_ENDPOINT=http://jaeger.prod:16686
export TRACE_SERVICE_NAME=myapp

# Costs
export AWS_COST_ALLOCATION_TAG=app:myapp

# SLO
export SLO_WINDOW=30d
```

With these variables set, Flow 6 agents automatically:
- Query Prometheus for metrics verification
- Search Elasticsearch for error patterns
- Correlate PagerDuty incidents with deployment
- Analyze Jaeger traces for service dependencies
- Pull AWS cost data for ROI analysis
- Calculate SLO compliance and error budget

**Without these variables**, Flow 6 still runs successfully using artifacts + git/GitHub.
