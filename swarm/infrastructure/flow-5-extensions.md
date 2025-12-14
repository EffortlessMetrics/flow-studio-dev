# Flow 5 Production Extensions

This document shows how to extend Flow 5 (Deploy) from the out-of-the-box GitHub-native implementation to real deployment platforms.

## Out-of-the-Box (What Works on Clone)

Flow 5 uses **only git and GitHub** (via `gh` CLI):

- ✅ Merge PR to main branch (`gh pr merge`)
- ✅ Create git tag and GitHub release (`git tag`, `gh release create`)
- ✅ Monitor GitHub Actions/CI status (`gh run list`, `gh run view`)
- ✅ Create GitHub deployment event (`gh api /repos/.../deployments`)
- ✅ Verify via CI checks + health endpoints (if URL available)
- ✅ Post deployment summary to PR/issue (`gh pr comment`)

**No external infrastructure required**. Every agent completes successfully using standard git/GitHub APIs.

---

## Production Extensions

Most orgs will want to extend Flow 5 to integrate with real deployment platforms. Here are common patterns:

### Extension 1: Kubernetes Deployment

**What to add:**

1. **Cluster Access**
   - Kubeconfig for target cluster(s)
   - Namespace configuration
   - RBAC permissions for deployments

2. **Agent Updates**

   **`deployer` agent**:
   ```markdown
   ## Production Mode (Kubernetes)

   1. Check if `KUBE_CONTEXT` environment variable is set
   2. If set:
      - Apply manifests: `kubectl apply -f k8s/ --context=$KUBE_CONTEXT`
      - Wait for rollout: `kubectl rollout status deployment/app --context=$KUBE_CONTEXT`
      - Write actual kubectl output to deployment_log.md
   3. If not set:
      - Fall back to GitHub-native deployment (current behavior)
   ```

   **`smoke-verifier` agent**:
   ```markdown
   ## Production Mode (Kubernetes)

   1. If `KUBE_CONTEXT` set:
      - Get service endpoint: `kubectl get service app -o jsonpath='{.status.loadBalancer.ingress[0].ip}'`
      - Run health checks against cluster endpoint
      - Verify pod status: `kubectl get pods -l app=myapp`
   2. Else:
      - Use GitHub deployment URL (current behavior)
   ```

3. **Environment Variables**
   ```bash
   export KUBE_CONTEXT=production-cluster
   export KUBE_NAMESPACE=myapp-prod
   export DEPLOY_TIMEOUT=600  # seconds to wait for rollout
   ```

**Benefits**: Real deployment verification, rollout status tracking, pod-level health checks.

---

### Extension 2: Canary Deployment with Metrics

**What to add:**

1. **Metrics Backend**
   - Prometheus or Datadog access
   - Metrics query endpoint
   - Alert manager (optional)

2. **New Agent: `canary-analyzer`** (insert between `smoke-verifier` and `deploy-decider`)

   ```markdown
   ## Inputs
   - `RUN_BASE/deploy/smoke_test_results.md`
   - `RUN_BASE/plan/observability_spec.md` (SLO thresholds)
   - Environment: `METRICS_ENDPOINT` (Prometheus/Datadog URL)

   ## Behavior

   1. Parse observability_spec.md for canary thresholds:
      - error_rate_threshold (e.g., < 1%)
      - p95_latency_threshold (e.g., < 200ms)
      - canary_duration (e.g., 5 minutes)

   2. Query metrics backend:
      - Prometheus: `rate(http_requests_total{status="500",version="canary"}[5m])`
      - Datadog: API query for error rate by version tag

   3. Compare canary vs baseline:
      - If canary_error_rate > baseline_error_rate * 1.5 → FAIL
      - If canary_p95_latency > threshold → FAIL
      - Else → PASS

   4. Write `RUN_BASE/deploy/canary_analysis.md`:
      - Metrics observed
      - Thresholds from spec
      - PASS/FAIL decision with evidence
   ```

3. **Update `deploy-decider` agent**:
   ```markdown
   ## Inputs (Production Mode)
   - `ci_status.md`
   - `smoke_test_results.md`
   - `canary_analysis.md` (if present)

   ## Decision Logic
   - If canary_analysis.md exists and shows FAIL → ROLLBACK
   - Else if CI failed → INVESTIGATE
   - Else if smoke tests failed → INVESTIGATE
   - Else → STABLE
   ```

4. **Environment Variables**
   ```bash
   export METRICS_ENDPOINT=http://prometheus.prod:9090
   export CANARY_ENABLED=true
   export CANARY_DURATION=300  # 5 minutes
   ```

**Benefits**: Automated canary analysis, data-driven rollout decisions, early detection of regressions.

---

### Extension 3: Automated Rollback

**What to add:**

1. **Rollback Mechanism**
   - Git tag for previous version
   - Deployment rollback script
   - Alert notification (Slack, PagerDuty)

2. **New Agent: `rollback-executor`** (triggered by `deploy-decider` if ROLLBACK decision)

   ```markdown
   ## Inputs
   - `RUN_BASE/deploy/deployment_decision.md` (ROLLBACK status)
   - `RUN_BASE/deploy/canary_analysis.md` (reason for rollback)
   - Environment: `ROLLBACK_SCRIPT` or `KUBE_CONTEXT`

   ## Behavior

   1. Determine rollback method:
      - Kubernetes: `kubectl rollout undo deployment/app --context=$KUBE_CONTEXT`
      - Terraform: `terraform destroy -target=module.app && terraform apply`
      - Custom: Execute `$ROLLBACK_SCRIPT`

   2. Execute rollback

   3. Verify rollback success:
      - Check previous version is running
      - Run smoke tests against previous version

   4. Notify team:
      - Post to Slack: "Automated rollback executed for run-id due to: [reason]"
      - Create incident if configured

   5. Write `RUN_BASE/deploy/rollback_log.md`
   ```

3. **Environment Variables**
   ```bash
   export ROLLBACK_SCRIPT=./scripts/rollback.sh
   export ROLLBACK_NOTIFY_SLACK=https://hooks.slack.com/services/...
   ```

**Benefits**: Automated recovery from bad deployments, reduced MTTR, audit trail of rollback decisions.

---

### Extension 4: Blue/Green or Progressive Delivery

**What to add:**

1. **Traffic Management**
   - Service mesh (Istio, Linkerd)
   - Ingress controller with traffic splitting
   - Feature flags (LaunchDarkly, Split.io)

2. **Update `deployment-notifier` agent**:
   ```markdown
   ## Progressive Delivery Mode

   1. Deploy green/canary environment (10% traffic)
   2. Create GitHub deployment with environment=canary
   3. Monitor for `CANARY_DURATION` seconds
   4. If metrics good:
      - Increase traffic: 10% → 50% → 100%
      - Update deployment environment=production
   5. If metrics bad:
      - Route all traffic back to blue
      - Trigger rollback-executor
   ```

3. **Environment Variables**
   ```bash
   export TRAFFIC_SPLIT_ENABLED=true
   export TRAFFIC_INCREMENT=10,50,100  # percentage steps
   export SOAK_DURATION=300  # seconds per step
   ```

**Benefits**: Gradual rollout, minimal blast radius, ability to pause and inspect at each stage.

---

## Implementation Checklist

To extend Flow 5 for your organization:

- [ ] Choose deployment platform (k8s, ECS, Cloud Run, VMs)
- [ ] Set up cluster access / cloud credentials
- [ ] Configure metrics backend (Prometheus, Datadog)
- [ ] Define SLO thresholds in `observability_spec.md`
- [ ] Update agent prompts to detect environment variables
- [ ] Write fallback behavior (if env vars not set, use GitHub-native)
- [ ] Test rollback mechanism in staging
- [ ] Document environment variables in team runbook
- [ ] (Optional) Add canary-analyzer agent
- [ ] (Optional) Add rollback-executor agent
- [ ] (Optional) Add traffic-splitter agent for progressive delivery

---

## Architecture Pattern

The key pattern is **graceful extension**:

1. **Base layer** (ships in repo): GitHub-native deployment
2. **Detection layer** (in agent prompts): Check for environment variables
3. **Extension layer** (org-specific): If env vars present, use real platform
4. **Fallback**: If env vars absent, base layer still works

This way:
- ✅ Repo works out of the box (demo/learning)
- ✅ Production teams extend by setting env vars + updating prompts
- ✅ No breaking changes to base swarm
- ✅ Clear audit trail in artifacts regardless of deployment platform
