# Selftest Environment-Specific Operations Guide

This document provides environment-specific operator guidance for the selftest system across **dev**, **staging**, and **production** environments.

**Target Audience**: Operators, SREs, platform engineers, and on-call engineers who need to understand how selftest behaves differently in each environment and what actions to take when failures occur.

**Key Insight**: Not all selftest failures mean "everything is broken." The response depends on **what failed** and **where it failed**. This guide helps you make that judgment quickly and confidently.

---

## Table of Contents

- [Quick Reference](#quick-reference)
- [Environment Profiles](#environment-profiles)
  - [Development Environment](#development-environment)
  - [Staging Environment](#staging-environment)
  - [Production Environment](#production-environment)
- [Degradation Patterns by Environment](#degradation-patterns-by-environment)
- [Escalation Decision Tree](#escalation-decision-tree)
- [Common Failure Scenarios & Remediation](#common-failure-scenarios--remediation)
- [Operator Runbooks](#operator-runbooks)
  - [Dev Operator Workflow](#dev-operator-workflow)
  - [Staging Operator Workflow](#staging-operator-workflow)
  - [Production Operator Workflow](#production-operator-workflow)
- [Monitoring & Alerting](#monitoring--alerting)
- [Environment-Specific CI/CD Integration](#environment-specific-cicd-integration)
- [FAQ](#faq)
- [Quick Reference Table](#quick-reference-table)
- [Appendix: Selftest Step Reference](#appendix-selftest-step-reference)

---

## Quick Reference

**When selftest fails, ask these three questions:**

1. **Where did it fail?** (Dev / Staging / Prod)
2. **What tier failed?** (KERNEL / GOVERNANCE / OPTIONAL)
3. **What's the policy?** (See table below)

| Environment | KERNEL Failure | GOVERNANCE Failure | OPTIONAL Failure | Action |
|-------------|----------------|--------------------|--------------------|--------|
| **Dev** | FATAL (stop) | Acceptable (≤3) | Informational | Fix when convenient |
| **Staging** | FATAL (block merge) | Acceptable (≤1) | Informational | Fix before prod |
| **Prod** | FATAL (page, rollback) | FATAL (incident) | Informational | Immediate response |

**Quick Commands:**

```bash
# Fast health check (300-400ms)
make kernel-smoke

# Full selftest (strict mode)
make selftest

# Degraded mode (KERNEL only blocks)
make selftest-degraded

# Diagnose failures
make selftest-doctor

# View selftest plan
uv run swarm/tools/selftest.py --plan
```

---

## Environment Profiles

### Development Environment

**Purpose**: Local developer machines and feature branches.

**Selftest runs**:
- On every commit (pre-commit hook, if installed)
- On push (CI on feature branch)
- Manually via `make dev-check`

**Acceptable degradation level**: **UP TO 3 governance failures (loose)**

**Philosophy**: Developers are actively working. Some governance checks may lag behind implementation. Allow warnings to accumulate during active development; enforce at merge time.

**Kernel failures**: **Always fatal** (block immediately)

**Example acceptable state**:
```
✅ core-checks (KERNEL)
⚠️  agents-governance (GOVERNANCE) — New agent not registered yet
⚠️  bdd (GOVERNANCE) — BDD scenarios being written
⚠️  ac-coverage (OPTIONAL) — Coverage at 85% (target 95%)
```

**Exit code**: 0 (can continue working)

**Operator response**:
- Fix kernel failures immediately (code quality compromised)
- Fix governance failures when convenient (docs/examples can lag)
- Optional failures are informational (track in issues)

**Commands**:

```bash
# Fast feedback loop during implementation
make kernel-smoke                    # 300-400ms, must be green
uv run swarm/tools/selftest.py --step core-checks  # Single step

# Degraded mode (governance warnings OK)
make selftest-degraded

# Verbose diagnostics
uv run swarm/tools/selftest.py --verbose

# Check what's failing
make selftest-doctor

# See degradation history
uv run swarm/tools/show_selftest_degradations.py
```

**Dev environment policy**:

1. **KERNEL must always pass** — If core-checks fails, work is blocked
2. **GOVERNANCE warnings are acceptable** — Up to 3 failures allowed
3. **Track governance debt** — File issues for known failures
4. **Fix before merge** — Staging enforces stricter rules

**Typical dev workflow**:

```bash
# Morning: Check health
make kernel-smoke
# Expected: HEALTHY (exit 0)

# During development: Allow governance warnings
make selftest-degraded
# Expected: KERNEL passes, governance may warn (exit 0)

# Before PR: Ensure everything passes
make selftest
# Expected: All green (exit 0) or bounce back to dev
```

**CI configuration (dev branches)**:

```yaml
# .github/workflows/dev-validate.yml
name: Dev Validation
on:
  push:
    branches-ignore: [main, staging, production]

jobs:
  selftest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: make kernel-smoke  # Fast check (required)
      - run: make selftest-degraded  # Governance warnings OK
      - run: |
          if [ $? -ne 0 ]; then
            echo "❌ KERNEL failure detected"
            exit 1
          else
            echo "✅ Dev selftest OK (degraded mode)"
          fi
```

---

### Staging Environment

**Purpose**: Integration testing branch before production deploy.

**Selftest runs**:
- On merge to `staging` branch (CI gate)
- Before production deploy (pre-deploy check)
- Manually via `make selftest` (strict mode)

**Acceptable degradation level**: **UP TO 1 governance failure (tight)**

**Philosophy**: Staging is the last line of defense before production. Most issues should be fixed, but one known issue is acceptable if documented and time-critical.

**Kernel failures**: **Always fatal** (block merge)

**Example acceptable state**:
```
✅ core-checks (KERNEL)
✅ agents-governance (GOVERNANCE)
⚠️  ac-coverage (OPTIONAL) — Coverage at 92% (target 95%)
```

**Exit code**: Depends on mode
- Strict mode: 1 if any governance fails (blocks merge)
- Degraded mode: 0 if kernel passes (allows merge with waiver)

**Operator response**:
- Fix kernel failures before merge (blocking)
- Fix governance failures before production deploy (required)
- Document exception if merging with 1 governance failure (PR comment required)

**Commands**:

```bash
# Pre-merge validation (strict mode)
make selftest --strict

# Review failures
make selftest-doctor

# Check if failure is acceptable
uv run swarm/tools/selftest.py --step <failed-step>

# Generate report for approval
uv run swarm/tools/selftest.py --json-v2 | jq .summary > staging-report.json
```

**Staging environment policy**:

1. **KERNEL must pass** — No exceptions
2. **GOVERNANCE failures ≤ 1** — Requires documented waiver
3. **OPTIONAL failures are informational** — Track but don't block
4. **Approval required** — Team lead must approve merge if governance fails

**Typical staging workflow**:

```bash
# Before merge to staging: Validate in strict mode
make selftest
# Expected: All green (exit 0)

# If 1 governance failure:
# 1. Document in PR comment
# 2. Create follow-up issue
# 3. Get team lead approval
# 4. Merge with waiver

# Example PR comment:
# "Merging with 1 governance failure (ac-coverage at 92%).
#  See issue #456 for follow-up. Approved by @tech-lead."
```

**CI configuration (staging branch)**:

```yaml
# .github/workflows/staging-gate.yml
name: Staging Gate
on:
  push:
    branches: [staging]

jobs:
  selftest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: make selftest  # Strict mode (required)
      - run: |
          EXIT_CODE=$?
          if [ $EXIT_CODE -eq 0 ]; then
            echo "✅ Staging selftest passed"
          elif [ $EXIT_CODE -eq 1 ]; then
            echo "❌ KERNEL or GOVERNANCE failure detected"
            echo "Review report and decide: merge with waiver or fix"
            # Generate report
            uv run swarm/tools/selftest.py --json-v2 > staging-report.json
            exit 1
          else
            echo "❌ Config error"
            exit 2
          fi
```

**Merge approval checklist (staging)**:

- [ ] KERNEL passes (core-checks)
- [ ] GOVERNANCE failures ≤ 1 (or 0 for ideal)
- [ ] If 1 governance failure: documented in PR comment
- [ ] Follow-up issue created for governance failure
- [ ] Team lead approval obtained
- [ ] Degradation logged in `selftest_degradations.log`

---

### Production Environment

**Purpose**: Live deployed system serving real traffic.

**Selftest runs**:
- Pre-deploy check (via Flow 5, before merge to `main`)
- Periodic audit (Flow 6, weekly or on-demand)
- Smoke test after deploy (immediate post-deploy verification)

**Acceptable degradation level**: **ZERO (strict)**

**Philosophy**: Production has no tolerance for degradation. Any failure is a production incident requiring immediate attention and post-mortem.

**Kernel failures**: **Fatal** (auto-rollback or block deploy)

**Example acceptable state**:
```
✅ core-checks (KERNEL)
✅ agents-governance (GOVERNANCE)
✅ bdd (GOVERNANCE)
✅ ac-status (GOVERNANCE)
✅ policy-tests (GOVERNANCE)
✅ devex-contract (GOVERNANCE)
✅ graph-invariants (GOVERNANCE)
✅ ac-coverage (OPTIONAL)
✅ extras (OPTIONAL)
```

**Exit code**: 0 (all pass) or 1 (incident)

**Operator response**:
- Page on-call if any failure
- Immediate rollback if kernel fails
- Post-mortem required for any failure
- Update this document with learnings

**Commands**:

```bash
# Pre-deploy validation (strict mode)
make selftest --strict

# Emergency diagnostics
make selftest-doctor --verbose

# Generate incident report
uv run swarm/tools/selftest.py --json-v2 | jq . > incident-report.json

# Check specific step
uv run swarm/tools/selftest.py --step <failed-step> --verbose

# Rollback procedure (if deploy proceeded and failed)
# See § Production Operator Runbook below
```

**Production environment policy**:

1. **KERNEL must pass** — Auto-rollback on failure
2. **GOVERNANCE must pass** — No waivers in production
3. **OPTIONAL should pass** — Informational; investigate if fails
4. **Incident required** — Any failure triggers post-mortem

**Typical production workflow**:

```bash
# Pre-deploy (Flow 5 integration)
echo "Running pre-deploy selftest..."
make selftest --strict
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  echo "❌ Pre-deploy selftest failed"
  echo "Blocking deployment"
  uv run swarm/tools/selftest.py --json-v2 > deploy-blocked.json
  exit 1
fi

echo "✅ Pre-deploy selftest passed"
echo "Proceeding with deployment..."

# Deploy happens here...

# Post-deploy smoke test
sleep 10  # Wait for services to stabilize
make kernel-smoke
if [ $? -ne 0 ]; then
  echo "❌ Post-deploy smoke test failed"
  echo "INITIATING ROLLBACK"
  ./scripts/rollback.sh
  exit 1
fi

echo "✅ Production deployment verified"
```

**CI configuration (production branch)**:

```yaml
# .github/workflows/production-deploy.yml
name: Production Deploy
on:
  push:
    branches: [main, production]

jobs:
  pre-deploy-selftest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Pre-deploy selftest (strict mode)
        run: |
          make selftest --strict
          EXIT_CODE=$?
          if [ $EXIT_CODE -ne 0 ]; then
            echo "❌ Production selftest failed (BLOCKING)"
            uv run swarm/tools/selftest.py --json-v2 | \
              jq '.summary' > selftest-failure-summary.json
            exit 1
          fi

  deploy:
    needs: pre-deploy-selftest
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: ./scripts/deploy-prod.sh

  post-deploy-smoke:
    needs: deploy
    runs-on: ubuntu-latest
    steps:
      - name: Post-deploy smoke test
        run: |
          sleep 10
          make kernel-smoke
          if [ $? -ne 0 ]; then
            echo "❌ Post-deploy smoke failed (ROLLBACK)"
            ./scripts/rollback.sh
            exit 1
          fi
```

**Incident response checklist (production)**:

- [ ] Page on-call engineer immediately
- [ ] Run `make selftest-doctor` for diagnostics
- [ ] Determine failure tier (KERNEL vs GOVERNANCE)
- [ ] If KERNEL: initiate rollback
- [ ] If GOVERNANCE: assess impact, decide on rollback
- [ ] Document in incident ticket
- [ ] Generate incident report: `uv run swarm/tools/selftest.py --json-v2`
- [ ] Post-mortem within 48 hours
- [ ] Update this document with learnings

---

## Degradation Patterns by Environment

This section documents "normal" degradation patterns for each environment and helps you distinguish between acceptable and concerning failures.

### Dev: Normal Patterns

**Pattern 1: AC-COVERAGE fails during active development**

```
⚠️  ac-coverage (OPTIONAL) — Coverage at 75% (target 95%)
```

**Why it happens**: Developers are writing code before tests, or tests are incomplete.

**Is it OK?**: Yes, in dev. Track in issues and fix before merge.

**Action**: None immediately. Fix when convenient or before PR.

**Pattern 2: agents-governance warns (new agent not registered)**

```
⚠️  agents-governance (GOVERNANCE) — Agent 'foo-bar' referenced in flow but not in registry
```

**Why it happens**: Developer added an agent reference but hasn't registered it yet.

**Is it OK?**: Yes, temporarily. Must fix before merge to staging.

**Action**: Run `make gen-adapters && make check-adapters` to register.

**Pattern 3: bdd fails (scenarios incomplete)**

```
⚠️  bdd (GOVERNANCE) — Missing scenario: "User uploads invalid file"
```

**Why it happens**: BDD scenarios lag behind implementation during active development.

**Is it OK?**: Yes, for 1-2 days. Should catch up before PR review.

**Action**: Add missing scenarios to `features/*.feature` files.

**Pattern 4: policy-tests warns (policy not enforced locally)**

```
⚠️  policy-tests (GOVERNANCE) — OPA policy requires security review; no evidence found
```

**Why it happens**: Local dev doesn't enforce org-wide policies (expected).

**Is it OK?**: Yes, in dev. Staging/prod will enforce.

**Action**: None locally. Staging gate will catch this.

**Summary (Dev)**:

| Pattern | Tier | Acceptable? | Fix Timing |
|---------|------|-------------|------------|
| AC-COVERAGE low | OPTIONAL | Yes | Before merge |
| New agent not registered | GOVERNANCE | Yes (temp) | Before PR |
| BDD scenarios incomplete | GOVERNANCE | Yes (temp) | Before PR review |
| Policy not enforced | GOVERNANCE | Yes | Staging enforces |

**Concerning patterns (Dev)**:

- **KERNEL failures**: Never OK, even in dev
- **Repeated governance failures**: Same step failing for > 3 days
- **3+ governance failures**: Indicates drift; prioritize cleanup

---

### Staging: Normal Patterns

**Pattern 1: AC-COVERAGE slightly below target**

```
⚠️  ac-coverage (OPTIONAL) — Coverage at 93% (target 95%)
```

**Why it happens**: Some edge cases not yet covered by tests.

**Is it OK?**: Yes, if documented and improving.

**Action**: Create follow-up issue. Track coverage trend.

**Pattern 2: policy-tests warns (known exemption)**

```
⚠️  policy-tests (GOVERNANCE) — Security review pending for feature X
```

**Why it happens**: Feature approved for staging but security review not yet complete.

**Is it OK?**: Yes, with documented waiver and follow-up ticket.

**Action**: Document in PR comment. Block production deploy until resolved.

**Concerning patterns (Staging)**:

- **KERNEL failures**: Never OK (blocks merge)
- **2+ GOVERNANCE failures**: Too much debt; fix before merge
- **Repeated failures**: Same step failing across multiple PRs (indicates systemic issue)

**Summary (Staging)**:

| Pattern | Tier | Acceptable? | Fix Timing |
|---------|------|-------------|------------|
| AC-COVERAGE slightly low | OPTIONAL | Yes | Track in issues |
| Policy exemption | GOVERNANCE | Yes (1 only) | Before prod |
| KERNEL failure | KERNEL | No | Fix immediately |
| 2+ GOVERNANCE failures | GOVERNANCE | No | Fix before merge |

**Escalation threshold (Staging)**:

- **0 KERNEL failures**: Proceed
- **1 GOVERNANCE failure**: Documented waiver + team lead approval
- **2+ GOVERNANCE failures**: Bounce to dev for fixes

---

### Production: Normal Patterns

**Pattern 1: All checks pass**

```
✅ All 16 steps passed
✅ Total duration: 18.5s
✅ Exit code: 0
```

**Why it happens**: This is the **only normal state** for production.

**Is it OK?**: Yes, this is expected.

**Action**: Proceed with deploy or periodic audit.

**Pattern 2: Any failure**

```
❌ <any-step> (any tier) — <any reason>
```

**Why it happens**: Something is broken.

**Is it OK?**: **NO**. This is a production incident.

**Action**: Page on-call, investigate immediately, consider rollback.

**Summary (Production)**:

| Pattern | Tier | Acceptable? | Action |
|---------|------|-------------|--------|
| All checks pass | All | Yes | Proceed |
| Any KERNEL failure | KERNEL | No | Incident + rollback |
| Any GOVERNANCE failure | GOVERNANCE | No | Incident + investigate |
| Any OPTIONAL failure | OPTIONAL | No (investigate) | Incident + post-mortem |

**Escalation threshold (Production)**:

- **Any failure**: Incident, page on-call
- **KERNEL failure**: Immediate rollback
- **GOVERNANCE failure**: Assess impact, likely rollback
- **OPTIONAL failure**: Investigate, may not require rollback but still incident

---

## Escalation Decision Tree

Use this decision tree to determine the correct response when selftest fails in any environment.

### Decision Tree: Selftest Fails in DEV

```
┌─────────────────────────────────────┐
│ Selftest failed in DEV environment  │
└─────────────┬───────────────────────┘
              │
              ▼
         Is KERNEL failing?
              │
       ┌──────┴──────┐
       │             │
      YES           NO
       │             │
       ▼             ▼
  BLOCKING      Is GOVERNANCE failing?
       │             │
       │       ┌─────┴─────┐
       │       │           │
       │      YES         NO
       │       │           │
       │       ▼           ▼
       │  How many?   OPTIONAL only
       │       │           │
       │  ┌────┴────┐      │
       │  │         │      │
       │ 1-2       3+      │
       │  │         │      │
       ▼  ▼         ▼      ▼
    Fix   OK,    Investigate  Informational
    NOW   track  (drift?)     (track in issues)
          in
          issues
```

**Example outcomes**:

**KERNEL fails**:
- Fix immediately (linting error, syntax error, test failure)
- Block all work until fixed
- Run `make selftest-doctor` to diagnose

**1-2 GOVERNANCE failures**:
- Acceptable during active development
- Track in issues, fix when convenient
- Run `make selftest-degraded` to continue working

**3+ GOVERNANCE failures**:
- Indicates drift or systemic issue
- Investigate root cause
- Prioritize cleanup before adding more debt

**OPTIONAL fails**:
- Informational only
- Track in issues for next sprint
- No action needed immediately

---

### Decision Tree: Selftest Fails in STAGING

```
┌──────────────────────────────────────┐
│ Selftest failed in STAGING           │
└─────────────┬────────────────────────┘
              │
              ▼
         Is KERNEL failing?
              │
       ┌──────┴──────┐
       │             │
      YES           NO
       │             │
       ▼             ▼
  BLOCK MERGE   Is GOVERNANCE failing?
       │             │
       │       ┌─────┴─────┐
       │       │           │
       │      YES         NO
       │       │           │
       │       ▼           ▼
       │  How many?   OPTIONAL only
       │       │           │
       │  ┌────┴────┐      │
       │  │         │      │
       │  1        2+      │
       │  │         │      │
       ▼  ▼         ▼      ▼
    Fix  Waiver  BLOCK  Informational
    in   OK,    MERGE  (track)
    feature document  Fix before
    branch  + approve merge
            + issue
```

**Example outcomes**:

**KERNEL fails**:
- Block merge to staging
- Bounce PR back to feature branch
- Fix in feature branch, re-validate

**1 GOVERNANCE failure**:
- Document in PR comment
- Create follow-up issue
- Get team lead approval
- Merge with waiver (degradation logged)

**2+ GOVERNANCE failures**:
- Block merge to staging
- Too much technical debt
- Fix in feature branch before re-attempting

**OPTIONAL fails**:
- Informational only
- Track in issues
- Does not block merge

---

### Decision Tree: Selftest Fails in PROD

```
┌──────────────────────────────────────┐
│ Selftest failed in PRODUCTION        │
└─────────────┬────────────────────────┘
              │
              ▼
         PAGE ON-CALL
              │
              ▼
         Is KERNEL failing?
              │
       ┌──────┴──────┐
       │             │
      YES           NO
       │             │
       ▼             ▼
  IMMEDIATE     Is GOVERNANCE failing?
  ROLLBACK           │
       │       ┌─────┴─────┐
       │       │           │
       │      YES         NO
       │       │           │
       │       ▼           ▼
       │  ASSESS      OPTIONAL only
       │  IMPACT           │
       │       │           │
       │  ┌────┴────┐      │
       │  │         │      │
       │ HIGH     LOW      │
       │  │         │      │
       ▼  ▼         ▼      ▼
    ROLLBACK  MONITOR  INVESTIGATE
    + POST-   + POST-  + POST-
    MORTEM    MORTEM   MORTEM
```

**Example outcomes**:

**KERNEL fails**:
- Page on-call immediately
- Initiate rollback (auto-rollback if configured)
- Post-mortem within 48 hours
- Block future deploys until fixed

**GOVERNANCE fails (high impact)**:
- Page on-call immediately
- Assess impact (security, compliance, data integrity)
- Likely rollback
- Post-mortem within 48 hours

**GOVERNANCE fails (low impact)**:
- Page on-call immediately
- Monitor for regressions
- May not rollback, but requires incident ticket
- Post-mortem within 48 hours

**OPTIONAL fails**:
- Page on-call (any failure in prod is incident)
- Investigate root cause
- Likely no rollback needed
- Post-mortem recommended (understand why)

---

## Common Failure Scenarios & Remediation

This section documents specific failures, their causes, and environment-specific remediation steps.

### Scenario 1: "AC-COVERAGE is failing"

**Symptom**:
```
❌ ac-coverage (OPTIONAL) — Coverage at 85% (target 95%)
Exit code: 0 (non-blocking, but warning)
```

**Cause**: Test coverage below configured threshold.

**Dev remediation**:
```bash
# Acceptable during development
# Track in issues, fix when convenient
echo "TODO: Increase coverage" >> .todo
make selftest-degraded  # Continue working
```

**Staging remediation**:
```bash
# Create follow-up issue
gh issue create --title "Increase test coverage to 95%" \
  --body "Current: 85%, Target: 95%. See ac-coverage step."

# Document in PR comment
echo "Coverage at 85%, tracking in issue #456" >> pr-comment.txt

# Proceed with merge (OPTIONAL failure doesn't block)
```

**Production remediation**:
```bash
# Should not happen (staging should have caught this)
# If it does, investigate why staging didn't catch it

# Immediate action: Assess impact
# - Is coverage trending down? (indicates test debt)
# - Did a recent deploy reduce coverage?

# Create incident ticket
gh issue create --title "INCIDENT: Production coverage at 85%" \
  --label incident \
  --body "Investigate why staging didn't catch this."

# Post-mortem: Why did staging allow this through?
```

**Summary**:

| Environment | Action | Urgency |
|-------------|--------|---------|
| Dev | Track, fix later | Low |
| Staging | Create issue, document | Medium |
| Prod | Incident, investigate | High |

---

### Scenario 2: "AC-POLICY-TESTS warns but code seems fine"

**Symptom**:
```
⚠️  policy-tests (GOVERNANCE) — OPA policy requires security review; no evidence found
Exit code: Depends on mode (0 in degraded, 1 in strict)
```

**Cause**: Code violates org-wide policy (security review missing, compliance check missing, etc.).

**Dev remediation**:
```bash
# Policy not enforced locally (expected)
# Continue working, staging will enforce

make selftest-degraded  # GOVERNANCE warning OK in dev
```

**Staging remediation**:
```bash
# Policy enforcement required before prod
# Option 1: Update policy config if policy is too strict
$EDITOR swarm/policies/security.rego

# Option 2: Add exception if justified
echo "exemption: feature-x" >> swarm/policies/exemptions.yaml

# Option 3: Obtain required approval (e.g., security review)
# Document approval in PR comment:
echo "Security review completed by @security-team" >> pr-comment.txt

# Re-run selftest
make selftest
```

**Production remediation**:
```bash
# Should not happen (staging enforces policy)
# If it does, this is a CRITICAL incident

# Immediate action: Page on-call
# Assess impact: Does code violate security policy?
# - If yes: ROLLBACK immediately
# - If no: Policy is misconfigured, fix policy

# Create incident ticket
gh issue create --title "INCIDENT: Policy violation in production" \
  --label incident,critical \
  --body "Code in production violates policy: <details>"

# Post-mortem: Why did staging allow this through?
```

**Summary**:

| Environment | Action | Urgency |
|-------------|--------|---------|
| Dev | Ignore (not enforced) | None |
| Staging | Fix or document exemption | High |
| Prod | Incident, assess rollback | Critical |

---

### Scenario 3: "Agent is not in registry"

**Symptom**:
```
❌ agents-governance (GOVERNANCE) — Agent 'foo-bar' referenced in flow but not in swarm/AGENTS.md
Exit code: 1 (blocking in strict mode)
```

**Cause**: Flow references an agent that doesn't exist in the registry.

**Dev remediation**:
```bash
# Developer added agent but forgot to register

# Option 1: Register the agent
echo "| foo-bar | 3 | implementation | green | project/user | Does foo bar things |" >> swarm/AGENTS.md

# Option 2: Regenerate adapters (if config-backed)
make gen-adapters

# Option 3: Fix typo in flow reference
$EDITOR swarm/flows/flow-build.md

# Validate
make validate-swarm
make selftest
```

**Staging remediation**:
```bash
# Should not happen (dev should catch this)
# If it does, block merge

# Fix in feature branch
git checkout feature-branch
# (apply fix from dev remediation above)
git commit -m "fix: register agent foo-bar"
git push

# Re-validate
make selftest
```

**Production remediation**:
```bash
# Should NEVER happen (staging blocks this)
# If it does, this is a CRITICAL incident

# Immediate action: Page on-call
# This indicates registry is out of sync with deployed code

# Assess impact:
# - Can agents still run? (likely yes, registry is metadata)
# - Is this blocking new deployments? (likely yes)

# Fix immediately:
# (apply fix from dev remediation above)
git commit -m "hotfix: register agent foo-bar"
git push origin main

# Redeploy (fast-forward)
./scripts/deploy-prod.sh

# Post-mortem: How did this reach production?
```

**Summary**:

| Environment | Action | Urgency |
|-------------|--------|---------|
| Dev | Fix locally, validate | Medium |
| Staging | Block merge, fix in branch | High |
| Prod | Hotfix, redeploy | Critical |

---

### Scenario 4: "Core-checks fails (KERNEL)"

**Symptom**:
```
❌ core-checks (KERNEL) — cargo clippy returned exit code 1
Lint warning: unused variable 'x' in src/main.rs:42
Exit code: 1 (blocking in all modes)
```

**Cause**: Code quality issue (lint warning, test failure, formatting error).

**Dev remediation**:
```bash
# KERNEL failure blocks all work

# Step 1: Diagnose
make selftest-doctor
# Output: SERVICE_ISSUE (code is broken)

# Step 2: Identify specific issue
uv run swarm/tools/selftest.py --step core-checks --verbose

# Step 3: Fix
cargo clippy --workspace --all-targets --all-features --fix

# Step 4: Validate
make kernel-smoke
make selftest
```

**Staging remediation**:
```bash
# Should not happen (dev CI should catch this)
# If it does, block merge immediately

# DO NOT MERGE

# Bounce to feature branch:
gh pr review --request-changes \
  --body "KERNEL failure detected (core-checks). Fix in feature branch."

# Developer fixes in feature branch (same as dev remediation)
```

**Production remediation**:
```bash
# Should NEVER happen (staging blocks this)
# If it does, this is a CRITICAL incident

# Immediate action: Page on-call
# KERNEL failure means code is fundamentally broken

# Assess impact:
# - Did a bad deploy just go out? → ROLLBACK immediately
# - Is this a false positive? → Investigate urgently

# Rollback procedure:
./scripts/rollback.sh

# Post-deploy smoke test (after rollback):
make kernel-smoke
# Expected: HEALTHY (exit 0)

# Post-mortem:
# - How did broken code reach production?
# - Did staging CI pass incorrectly?
# - Was there a race condition in CI?
```

**Summary**:

| Environment | Action | Urgency |
|-------------|--------|---------|
| Dev | Fix locally (blocking) | Immediate |
| Staging | Block merge (critical) | Critical |
| Prod | Rollback, incident | Emergency |

---

### Scenario 5: "Devex-contract fails (flow specs invalid)"

**Symptom**:
```
❌ devex-contract (GOVERNANCE) — Flow spec 'flow-build.md' contains hardcoded path 'swarm/runs/my-ticket/'
Expected: RUN_BASE/<flow>/ placeholder
Exit code: 1 (blocking in strict mode)
```

**Cause**: Flow spec uses hardcoded path instead of `RUN_BASE` placeholder.

**Dev remediation**:
```bash
# Fix flow spec
$EDITOR swarm/flows/flow-build.md

# Replace hardcoded paths with RUN_BASE placeholders
# Before: swarm/runs/my-ticket/build/
# After:  RUN_BASE/build/

# Validate
make validate-swarm
make selftest
```

**Staging remediation**:
```bash
# Should not happen (dev should catch this)
# If it does, block merge

# Fix in feature branch (same as dev remediation)
# Re-validate before merge
```

**Production remediation**:
```bash
# Should NEVER happen (staging blocks this)
# If it does, assess impact

# Impact: Flow specs are documentation/metadata
# Likely low runtime impact, but indicates drift

# Fix with hotfix:
# (apply fix from dev remediation above)
git commit -m "hotfix: fix hardcoded path in flow-build.md"
git push origin main

# Redeploy (metadata update only, low risk)
./scripts/deploy-prod.sh

# Post-mortem: Why did staging allow this through?
```

**Summary**:

| Environment | Action | Urgency |
|-------------|--------|---------|
| Dev | Fix spec, validate | Medium |
| Staging | Block merge, fix | High |
| Prod | Hotfix (low impact) | Medium |

---

### Scenario 6: "Graph-invariants fails (flow graph invalid)"

**Symptom**:
```
❌ graph-invariants (GOVERNANCE) — Flow 3 has disconnected step (step-5 has no predecessors or successors)
Exit code: 1 (blocking in strict mode)
```

**Cause**: Flow graph structure is invalid (disconnected step, circular dependency, etc.).

**Dev remediation**:
```bash
# Fix flow graph structure
$EDITOR swarm/config/flows/flow-3.yaml

# Ensure all steps are connected:
# - Every step (except first) has predecessor
# - Every step (except last) has successor

# Regenerate flow docs
make gen-flows

# Validate
uv run swarm/tools/flow_graph.py --validate
make selftest
```

**Staging remediation**:
```bash
# Block merge (graph structure is critical)
# Fix in feature branch (same as dev remediation)
```

**Production remediation**:
```bash
# Should NEVER happen (staging blocks this)
# If it does, this is a HIGH priority incident

# Impact: Flow orchestration may be broken
# - Can flows still execute? (depends on which step)
# - Are we blocking deployments? (likely yes)

# Fix with hotfix:
# (apply fix from dev remediation above)
git commit -m "hotfix: fix disconnected step in flow-3"
git push origin main

# Redeploy
./scripts/deploy-prod.sh

# Validate post-deploy:
make selftest

# Post-mortem: Why did staging allow this through?
```

**Summary**:

| Environment | Action | Urgency |
|-------------|--------|---------|
| Dev | Fix graph, validate | High |
| Staging | Block merge (critical) | Critical |
| Prod | Hotfix, redeploy | High |

---

## Operator Runbooks

### Dev Operator Workflow

**Role**: Software engineer working on a feature branch.

**Daily workflow**:

```bash
# 1. Morning: Check health
make kernel-smoke
# Expected: HEALTHY (exit 0)
# If not: Run `make selftest-doctor` and fix

# 2. During development: Fast feedback
make kernel-smoke  # After each significant change (300-400ms)

# 3. Before commit: Validate
make selftest-degraded  # Governance warnings OK
# If KERNEL fails: Fix immediately
# If GOVERNANCE fails: Track in .todo, fix later

# 4. Before PR: Strict validation
make selftest
# Expected: All green (exit 0)
# If fails: Fix in branch before PR
```

**Handling failures (Dev)**:

```bash
# KERNEL failure (e.g., core-checks)
make selftest-doctor
# Output: SERVICE_ISSUE → code is broken

# Diagnose specific step
uv run swarm/tools/selftest.py --step core-checks --verbose

# Fix (example: lint issue)
cargo clippy --workspace --all-targets --all-features --fix
cargo fmt

# Re-validate
make kernel-smoke
make selftest
```

**GOVERNANCE failure (e.g., agents-governance)**:

```bash
# Diagnose
uv run swarm/tools/selftest.py --step agents-governance

# Fix (example: register agent)
echo "| new-agent | 3 | implementation | green | project/user | Does things |" >> swarm/AGENTS.md
make gen-adapters
make validate-swarm

# Re-validate
make selftest
```

**OPTIONAL failure (e.g., ac-coverage)**:

```bash
# Informational only, doesn't block work
# Track in issues
echo "TODO: Increase coverage to 95%" >> .todo

# Continue working
make selftest-degraded
```

**Emergency: Everything is broken**:

```bash
# Diagnose harness vs service
make selftest-doctor

# Output: HARNESS_ISSUE
# → Fix environment
uv sync
rustup update stable

# Output: SERVICE_ISSUE
# → Fix code (see above)

# Output: HEALTHY
# → Something subtle; investigate further
uv run swarm/tools/selftest.py --plan
# Run each step individually to narrow down
```

**Before submitting PR**:

```bash
# Checklist:
# [ ] make kernel-smoke → HEALTHY
# [ ] make selftest → All green
# [ ] make validate-swarm → No errors
# [ ] git status → Clean tree (or only intended changes)

# If all pass:
git push origin feature-branch
gh pr create --title "feat: add new feature" --body "..."
```

---

### Staging Operator Workflow

**Role**: CI/CD pipeline or platform engineer reviewing PR for merge to staging.

**Pre-merge workflow**:

```bash
# 1. Validate PR branch
git checkout feature-branch
make selftest --strict

# 2. Review results
if [ $? -eq 0 ]; then
  echo "✅ All checks passed (ready to merge)"
elif [ $? -eq 1 ]; then
  echo "❌ KERNEL or GOVERNANCE failure (review needed)"
  # Generate report
  uv run swarm/tools/selftest.py --json-v2 > pr-report.json
  # Review report, decide: merge with waiver or bounce
else
  echo "❌ Config error (fix immediately)"
fi
```

**Handling failures (Staging)**:

**KERNEL failure**:

```bash
# Block merge immediately
gh pr review --request-changes \
  --body "❌ KERNEL failure detected. Fix in feature branch."

# Developer fixes in branch, re-validate before re-attempting merge
```

**1 GOVERNANCE failure** (acceptable with waiver):

```bash
# Document in PR comment
gh pr review --comment \
  --body "⚠️  1 GOVERNANCE failure detected: <step-id>

  Reason: <brief explanation>
  Follow-up: <issue link>
  Approval: Required from @tech-lead

  Proceeding with merge waiver per staging policy."

# Create follow-up issue
gh issue create --title "Fix <step-id> failure" \
  --body "See PR #<num> for context."

# Merge with waiver (after approval)
gh pr merge --squash
```

**2+ GOVERNANCE failures**:

```bash
# Block merge
gh pr review --request-changes \
  --body "❌ 2+ GOVERNANCE failures detected. Too much debt.

  Fix all but one before re-attempting merge."

# Developer fixes in branch
```

**Post-merge workflow**:

```bash
# After merge to staging:
git checkout staging
git pull

# Validate staging branch
make selftest --strict

# If all pass:
echo "✅ Staging validated (ready for production deploy)"

# If any fail:
echo "❌ Staging broken (investigate immediately)"
# Assess: Was this PR the cause? Revert if necessary.
```

**Staging CI integration** (example GitHub Actions workflow):

```yaml
name: Staging Gate
on:
  pull_request:
    branches: [staging]

jobs:
  selftest-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          ref: ${{ github.event.pull_request.head.sha }}

      - name: Setup environment
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          uv sync

      - name: Run selftest (strict mode)
        id: selftest
        run: |
          make selftest --strict
          echo "exit_code=$?" >> $GITHUB_OUTPUT

      - name: Generate report
        if: steps.selftest.outputs.exit_code != '0'
        run: |
          uv run swarm/tools/selftest.py --json-v2 > selftest-report.json
          echo "## Selftest Report" >> $GITHUB_STEP_SUMMARY
          echo '```json' >> $GITHUB_STEP_SUMMARY
          jq '.summary' selftest-report.json >> $GITHUB_STEP_SUMMARY
          echo '```' >> $GITHUB_STEP_SUMMARY

      - name: Evaluate policy
        run: |
          EXIT_CODE=${{ steps.selftest.outputs.exit_code }}

          if [ "$EXIT_CODE" -eq 0 ]; then
            echo "✅ All checks passed"
            exit 0
          elif [ "$EXIT_CODE" -eq 1 ]; then
            # Check if KERNEL or GOVERNANCE failed
            KERNEL_FAILED=$(jq '.summary.by_severity.critical.failed' selftest-report.json)
            GOVERNANCE_FAILED=$(jq '.summary.by_severity.warning.failed' selftest-report.json)

            if [ "$KERNEL_FAILED" -gt 0 ]; then
              echo "❌ KERNEL failure (blocking)"
              exit 1
            elif [ "$GOVERNANCE_FAILED" -gt 1 ]; then
              echo "❌ 2+ GOVERNANCE failures (blocking)"
              exit 1
            elif [ "$GOVERNANCE_FAILED" -eq 1 ]; then
              echo "⚠️  1 GOVERNANCE failure (requires waiver)"
              echo "Review report and obtain approval before merging"
              # Don't exit 1; allow manual approval
              exit 0
            fi
          else
            echo "❌ Config error"
            exit 2
          fi
```

---

### Production Operator Workflow

**Role**: SRE or on-call engineer responsible for production deployments and incident response.

**Pre-deploy workflow**:

```bash
# 1. Pre-deploy validation (strict mode)
git checkout main
git pull

echo "Running pre-deploy selftest (strict mode)..."
make selftest --strict
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  echo "❌ Pre-deploy selftest failed (BLOCKING DEPLOY)"
  echo "Generating failure report..."
  uv run swarm/tools/selftest.py --json-v2 | jq . > predeploy-failure.json

  echo "DEPLOY BLOCKED"
  echo "Review failure report: predeploy-failure.json"
  echo "Do NOT proceed with deployment"
  exit 1
fi

echo "✅ Pre-deploy selftest passed"
echo "Proceeding with deployment..."

# 2. Deploy
./scripts/deploy-prod.sh

# 3. Post-deploy smoke test
echo "Waiting for services to stabilize..."
sleep 10

echo "Running post-deploy smoke test..."
make kernel-smoke
if [ $? -ne 0 ]; then
  echo "❌ Post-deploy smoke test failed"
  echo "INITIATING ROLLBACK"
  ./scripts/rollback.sh

  # Verify rollback
  sleep 10
  make kernel-smoke
  if [ $? -ne 0 ]; then
    echo "❌ ROLLBACK FAILED (CRITICAL)"
    echo "PAGING ON-CALL"
    ./scripts/page-oncall.sh "Production rollback failed"
  else
    echo "✅ Rollback successful"
  fi

  exit 1
fi

echo "✅ Post-deploy smoke test passed"
echo "Production deployment verified"
```

**Handling failures (Production)**:

**Incident: KERNEL failure**:

```bash
# Paged by monitoring: "Production selftest KERNEL failure"

# Step 1: Acknowledge
echo "Acknowledged. Investigating..."

# Step 2: Run diagnostics
make selftest-doctor --verbose

# Step 3: Assess impact
# - Is production serving traffic normally? (check monitoring)
# - Is this blocking new deployments? (likely yes)
# - Is this causing user-facing errors? (depends on failure)

# Step 4: Decide on rollback
if [ "<critical impact>" = true ]; then
  echo "Initiating rollback due to KERNEL failure"
  ./scripts/rollback.sh

  # Verify rollback
  sleep 10
  make kernel-smoke

  # Update incident ticket
  gh issue comment <incident-number> \
    --body "Rolled back to previous version. Selftest now passing."
fi

# Step 5: Generate incident report
uv run swarm/tools/selftest.py --json-v2 > incident-kernel-failure.json
gh issue create --title "INCIDENT: Production KERNEL failure" \
  --label incident,critical \
  --body "$(cat incident-kernel-failure.json)"

# Step 6: Post-mortem (within 48 hours)
# Schedule post-mortem meeting
# Update this document with learnings
```

**Incident: GOVERNANCE failure**:

```bash
# Paged by monitoring: "Production selftest GOVERNANCE failure"

# Step 1: Acknowledge
echo "Acknowledged. Investigating..."

# Step 2: Assess impact
uv run swarm/tools/selftest.py --step <failed-step> --verbose

# Step 3: Determine severity
# - Security/compliance? → HIGH impact (likely rollback)
# - Documentation drift? → LOW impact (monitor, fix soon)
# - Agent config? → MEDIUM impact (assess case-by-case)

# Step 4: Decide on rollback
# High impact example: policy-tests fails (security policy violated)
if [ "<impact>" = "HIGH" ]; then
  echo "Initiating rollback due to HIGH impact GOVERNANCE failure"
  ./scripts/rollback.sh
fi

# Medium/low impact: Monitor, fix soon
if [ "<impact>" = "LOW" ]; then
  echo "Monitoring. No immediate rollback needed."
  echo "Creating hotfix plan..."
fi

# Step 5: Generate incident report
uv run swarm/tools/selftest.py --json-v2 > incident-governance-failure.json
gh issue create --title "INCIDENT: Production GOVERNANCE failure" \
  --label incident \
  --body "$(cat incident-governance-failure.json)"

# Step 6: Post-mortem (within 48 hours)
```

**Incident: OPTIONAL failure** (unusual but investigate):

```bash
# Paged by monitoring: "Production selftest OPTIONAL failure"

# Step 1: Acknowledge
echo "Acknowledged. Investigating..."

# Step 2: Understand why OPTIONAL failed
# OPTIONAL failures don't usually trigger pages
# If they did, something unusual happened

# Step 3: Assess impact
# - Is this a new failure? (indicates regression)
# - Is this a flaky check? (indicates test issue)

# Step 4: Likely no rollback needed
echo "Monitoring. Creating investigation ticket..."

# Step 5: Generate report
gh issue create --title "INCIDENT: Production OPTIONAL failure (unusual)" \
  --label incident,investigate \
  --body "Investigate why OPTIONAL step failed in production."

# Step 6: Post-mortem (recommended, understand why)
```

**Emergency rollback procedure**:

```bash
# Rollback script (example)
#!/bin/bash
set -e

echo "Starting emergency rollback..."

# Identify previous version
PREVIOUS_SHA=$(git log --skip 1 --format=%H -1)
echo "Rolling back to commit: $PREVIOUS_SHA"

# Rollback deployment
# (deployment tool specific; examples below)

# Option 1: Kubernetes rollout undo
# kubectl rollout undo deployment/swarm-service

# Option 2: Git-based deploy
git checkout $PREVIOUS_SHA
./scripts/deploy-prod.sh

# Option 3: Container registry rollback
# docker pull registry.example.com/swarm:previous
# docker tag registry.example.com/swarm:previous registry.example.com/swarm:latest
# ./scripts/deploy-prod.sh

echo "Rollback complete"

# Verify
sleep 10
make kernel-smoke
if [ $? -eq 0 ]; then
  echo "✅ Rollback verified (selftest passing)"
else
  echo "❌ Rollback failed (selftest still failing)"
  echo "ESCALATE TO ON-CALL LEAD"
  exit 1
fi
```

**Post-incident workflow**:

```bash
# After incident resolved:

# 1. Document in incident ticket
gh issue comment <incident-number> \
  --body "## Incident Summary

**Failure**: <step-id> (<tier>)
**Impact**: <description>
**Root cause**: <brief explanation>
**Resolution**: <what we did>
**Rollback**: Yes/No
**Duration**: <time to resolve>

## Post-mortem
Scheduled for <date> with @team
"

# 2. Schedule post-mortem (within 48 hours)
# Invite: on-call engineer, platform team, affected stakeholders

# 3. Update this document
# Add learnings to § Degradation Patterns or § Common Failures

# 4. Update monitoring/alerting if needed
# Example: Add more specific alert for this failure type
```

---

## Monitoring & Alerting

This section describes how to monitor selftest health in each environment and when to alert.

### Dev Environment Monitoring

**Metrics to track**: None (local development, no centralized monitoring).

**Alerting**: None (developers responsible for their own branches).

**Developer self-monitoring**:

```bash
# Run before each commit
make kernel-smoke

# Run before PR
make selftest
```

**CI monitoring (feature branches)**:

```bash
# CI runs on every push to feature branch
# Alert: None (CI status visible in PR, no pages)

# Example GitHub Actions check:
- name: Dev selftest
  run: make selftest-degraded
  continue-on-error: true  # Don't fail build, just warn
```

---

### Staging Environment Monitoring

**Metrics to track**:
- Selftest pass/fail rate (per PR)
- KERNEL failure count (should be 0)
- GOVERNANCE failure count (should be ≤ 1)
- Selftest duration (track performance regression)

**Alerting**:
- Alert if KERNEL fails (page platform team)
- Alert if 2+ GOVERNANCE failures (notify PR author)
- Alert if selftest duration > 60s (performance regression)

**Monitoring setup (example: Datadog/Prometheus)**:

```yaml
# metrics.yaml
selftest_staging_pass_total:
  type: counter
  labels: [pr_number, branch]

selftest_staging_fail_total:
  type: counter
  labels: [pr_number, branch, tier, step_id]

selftest_staging_duration_seconds:
  type: histogram
  labels: [pr_number, branch]
  buckets: [5, 10, 20, 30, 60]
```

**Alert rules (example: Prometheus AlertManager)**:

```yaml
# alerts.yaml
groups:
  - name: selftest_staging
    interval: 5m
    rules:
      - alert: SelftestStagingKernelFailure
        expr: selftest_staging_fail_total{tier="kernel"} > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Staging selftest KERNEL failure"
          description: "PR {{ $labels.pr_number }} has KERNEL failure (blocking)"

      - alert: SelftestStagingGovernanceDebt
        expr: selftest_staging_fail_total{tier="governance"} >= 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Staging selftest has 2+ GOVERNANCE failures"
          description: "PR {{ $labels.pr_number }} has {{ $value }} GOVERNANCE failures (requires cleanup)"

      - alert: SelftestStagingSlow
        expr: histogram_quantile(0.95, selftest_staging_duration_seconds) > 60
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Staging selftest is slow (p95 > 60s)"
          description: "Investigate performance regression"
```

**Dashboard (example: Grafana)**:

```
Panel 1: Selftest Pass Rate (Staging)
- Gauge: (pass / total) * 100
- Target: > 95%

Panel 2: Failure Breakdown by Tier
- Stacked bar chart: KERNEL, GOVERNANCE, OPTIONAL
- Group by: tier

Panel 3: Failure Breakdown by Step
- Table: step_id, count, last_failure_time
- Sort by: count DESC

Panel 4: Selftest Duration (p50, p95, p99)
- Line graph over time
- Target: p95 < 30s

Panel 5: Recent Failures (Last 24h)
- Table: pr_number, branch, step_id, timestamp
- Link to PR for triage
```

---

### Production Environment Monitoring

**Metrics to track**:
- Selftest pass/fail status (binary: PASS or INCIDENT)
- KERNEL failure count (should be 0, page if > 0)
- GOVERNANCE failure count (should be 0, page if > 0)
- OPTIONAL failure count (should be 0, investigate if > 0)
- Selftest duration (track for performance)

**Alerting**:
- **Page on-call** if any failure (KERNEL, GOVERNANCE, or OPTIONAL)
- **Auto-rollback** if KERNEL fails post-deploy (if configured)
- **Escalate to on-call lead** if rollback fails

**Monitoring setup (example: PagerDuty + Datadog)**:

```yaml
# metrics.yaml
selftest_production_status:
  type: gauge
  labels: [environment=production]
  values:
    0: FAIL (incident)
    1: PASS (healthy)

selftest_production_fail_total:
  type: counter
  labels: [tier, step_id]

selftest_production_duration_seconds:
  type: histogram
  labels: []
  buckets: [5, 10, 20, 30, 60]
```

**Alert rules (example: PagerDuty)**:

```yaml
# alerts.yaml
groups:
  - name: selftest_production
    interval: 1m  # Fast polling in prod
    rules:
      - alert: SelftestProductionKernelFailure
        expr: selftest_production_fail_total{tier="kernel"} > 0
        for: 0m  # Immediate page (no delay)
        labels:
          severity: critical
          page: oncall
        annotations:
          summary: "INCIDENT: Production selftest KERNEL failure"
          description: "KERNEL step failed. Immediate rollback recommended."
          runbook: "docs/SELFTEST_ENVIRONMENT_OPERATIONS.md#incident-kernel-failure"

      - alert: SelftestProductionGovernanceFailure
        expr: selftest_production_fail_total{tier="governance"} > 0
        for: 0m  # Immediate page
        labels:
          severity: critical
          page: oncall
        annotations:
          summary: "INCIDENT: Production selftest GOVERNANCE failure"
          description: "GOVERNANCE step failed. Assess impact and decide on rollback."
          runbook: "docs/SELFTEST_ENVIRONMENT_OPERATIONS.md#incident-governance-failure"

      - alert: SelftestProductionOptionalFailure
        expr: selftest_production_fail_total{tier="optional"} > 0
        for: 5m  # Short delay (unusual but not immediate rollback)
        labels:
          severity: warning
          page: oncall
        annotations:
          summary: "INCIDENT: Production selftest OPTIONAL failure (unusual)"
          description: "OPTIONAL step failed. Investigate why."
          runbook: "docs/SELFTEST_ENVIRONMENT_OPERATIONS.md#incident-optional-failure"

      - alert: SelftestProductionDown
        expr: absent(selftest_production_status)
        for: 5m
        labels:
          severity: critical
          page: oncall
        annotations:
          summary: "INCIDENT: Production selftest not reporting"
          description: "Selftest metrics missing. Check if selftest system is down."
```

**Dashboard (example: Grafana for Production)**:

```
Panel 1: Production Selftest Status
- Single stat: PASS / FAIL
- Color: Green (PASS) / Red (FAIL)
- Last updated: <timestamp>

Panel 2: Failure Count by Tier (Last 7 days)
- Bar chart: KERNEL, GOVERNANCE, OPTIONAL
- Target: All zeros

Panel 3: Time Since Last Failure
- Single stat: <hours> since last failure
- Target: > 168h (1 week)

Panel 4: Selftest Duration (Production)
- Line graph over time: p50, p95, p99
- Target: p95 < 30s

Panel 5: Recent Incidents (Last 30 days)
- Table: timestamp, step_id, tier, duration, resolved_by
- Link to incident ticket

Panel 6: Rollback Count (Last 30 days)
- Single stat: <count> rollbacks
- Target: 0
```

**PagerDuty integration (example)**:

```yaml
# pagerduty.yaml
service: swarm-production
escalation_policy:
  - on_call_engineer (immediate)
  - on_call_lead (after 15 min)
  - engineering_manager (after 30 min)

incident_automation:
  - trigger: selftest_production_kernel_failure
    action: create_incident
    severity: critical
    auto_acknowledge: false
    runbook_url: https://docs.example.com/selftest-runbook
    slack_channel: "#incidents"

  - trigger: selftest_production_governance_failure
    action: create_incident
    severity: high
    auto_acknowledge: false
    runbook_url: https://docs.example.com/selftest-runbook
    slack_channel: "#incidents"
```

**Example: Periodic audit (Flow 6 integration)**:

```bash
# Cron job: Run weekly production audit
# crontab -e
0 2 * * 1 /usr/local/bin/run-production-selftest-audit.sh

# run-production-selftest-audit.sh
#!/bin/bash
set -e

echo "Running weekly production selftest audit..."
cd /opt/swarm
make selftest --strict > /var/log/selftest-audit-$(date +%Y%m%d).log 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  echo "❌ Production audit failed"
  # Send alert (non-urgent, as this is periodic audit, not live deploy)
  curl -X POST https://hooks.slack.com/... \
    -d '{"text": "Weekly production selftest audit failed. Review logs."}'
else
  echo "✅ Production audit passed"
fi
```

---

## Environment-Specific CI/CD Integration

This section provides example CI/CD pipeline configurations for each environment.

### Dev CI/CD (Feature Branches)

**Goal**: Fast feedback, allow governance warnings, block only on KERNEL failures.

**GitHub Actions example** (`.github/workflows/dev-ci.yml`):

```yaml
name: Dev CI
on:
  push:
    branches-ignore: [main, staging, production]

jobs:
  fast-check:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v3

      - name: Setup UV
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Kernel smoke test (fast)
        run: |
          make kernel-smoke
          if [ $? -ne 0 ]; then
            echo "❌ KERNEL failure (blocking)"
            exit 1
          fi

      - name: Full selftest (degraded mode)
        run: |
          make selftest-degraded
          # Exit 0 even if GOVERNANCE warns (acceptable in dev)

  full-validation:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v3

      - name: Setup UV
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Full selftest (strict mode)
        id: selftest
        run: make selftest
        continue-on-error: true  # Don't fail build, just report

      - name: Comment PR with results
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const exitCode = ${{ steps.selftest.outcome === 'success' ? 0 : 1 }};
            const body = exitCode === 0
              ? '✅ Selftest passed (all checks green)'
              : '⚠️  Selftest has failures. Review before merging to staging.';

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body
            });
```

---

### Staging CI/CD (Pre-Merge Gate)

**Goal**: Strict validation, block merge on KERNEL or 2+ GOVERNANCE failures, allow 1 GOVERNANCE failure with waiver.

**GitHub Actions example** (`.github/workflows/staging-gate.yml`):

```yaml
name: Staging Gate
on:
  pull_request:
    branches: [staging]

jobs:
  selftest-gate:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v3
        with:
          ref: ${{ github.event.pull_request.head.sha }}

      - name: Setup UV
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Run selftest (strict mode)
        id: selftest
        run: |
          make selftest --strict
          echo "exit_code=$?" >> $GITHUB_OUTPUT
        continue-on-error: true

      - name: Generate report
        if: steps.selftest.outputs.exit_code != '0'
        run: |
          uv run swarm/tools/selftest.py --json-v2 > selftest-report.json

          echo "## Selftest Report" >> $GITHUB_STEP_SUMMARY
          echo '```json' >> $GITHUB_STEP_SUMMARY
          jq '.summary' selftest-report.json >> $GITHUB_STEP_SUMMARY
          echo '```' >> $GITHUB_STEP_SUMMARY

      - name: Upload report artifact
        if: steps.selftest.outputs.exit_code != '0'
        uses: actions/upload-artifact@v3
        with:
          name: selftest-report
          path: selftest-report.json

      - name: Evaluate merge policy
        run: |
          EXIT_CODE=${{ steps.selftest.outputs.exit_code }}

          if [ "$EXIT_CODE" -eq 0 ]; then
            echo "✅ All checks passed (approved for merge)"
            exit 0
          elif [ "$EXIT_CODE" -eq 1 ]; then
            # Parse report
            KERNEL_FAILED=$(jq '.summary.by_severity.critical.failed' selftest-report.json)
            GOVERNANCE_FAILED=$(jq '.summary.by_severity.warning.failed' selftest-report.json)

            echo "KERNEL failures: $KERNEL_FAILED"
            echo "GOVERNANCE failures: $GOVERNANCE_FAILED"

            if [ "$KERNEL_FAILED" -gt 0 ]; then
              echo "❌ KERNEL failure detected (BLOCKING MERGE)"
              exit 1
            elif [ "$GOVERNANCE_FAILED" -gt 1 ]; then
              echo "❌ 2+ GOVERNANCE failures detected (BLOCKING MERGE)"
              exit 1
            elif [ "$GOVERNANCE_FAILED" -eq 1 ]; then
              echo "⚠️  1 GOVERNANCE failure detected (REQUIRES WAIVER)"
              echo "Manual approval required from tech lead"
              echo "Failing check to require approval..."
              exit 1  # Require manual override
            fi
          else
            echo "❌ Config error"
            exit 2
          fi

      - name: Comment PR with waiver instructions
        if: steps.selftest.outputs.exit_code == '1'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = JSON.parse(fs.readFileSync('selftest-report.json', 'utf8'));
            const kernelFailed = report.summary.by_severity.critical.failed;
            const governanceFailed = report.summary.by_severity.warning.failed;

            let body = '## Selftest Results\n\n';

            if (kernelFailed > 0) {
              body += '❌ **KERNEL failure detected (BLOCKING)**\n\n';
              body += 'Fix KERNEL issues in feature branch before merging.\n';
            } else if (governanceFailed > 1) {
              body += '❌ **2+ GOVERNANCE failures detected (BLOCKING)**\n\n';
              body += 'Fix GOVERNANCE issues in feature branch before merging.\n';
            } else if (governanceFailed === 1) {
              body += '⚠️  **1 GOVERNANCE failure detected (REQUIRES WAIVER)**\n\n';
              body += 'To proceed with merge:\n';
              body += '1. Document failure reason in PR comment\n';
              body += '2. Create follow-up issue\n';
              body += '3. Obtain approval from @tech-lead\n';
              body += '4. Override this check manually\n';
            }

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body
            });
```

---

### Production CI/CD (Pre-Deploy Gate)

**Goal**: Zero tolerance, block deploy on any failure, auto-rollback on post-deploy failure.

**GitHub Actions example** (`.github/workflows/production-deploy.yml`):

```yaml
name: Production Deploy
on:
  push:
    branches: [main, production]

jobs:
  pre-deploy-selftest:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v3

      - name: Setup UV
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Pre-deploy selftest (strict mode)
        run: |
          make selftest --strict
          EXIT_CODE=$?

          if [ $EXIT_CODE -ne 0 ]; then
            echo "❌ Pre-deploy selftest FAILED (BLOCKING DEPLOY)"
            uv run swarm/tools/selftest.py --json-v2 | jq '.summary' > failure-summary.json
            cat failure-summary.json
            exit 1
          fi

          echo "✅ Pre-deploy selftest passed"

      - name: Upload pre-deploy report
        uses: actions/upload-artifact@v3
        with:
          name: predeploy-report
          path: failure-summary.json
        if: failure()

  deploy:
    needs: pre-deploy-selftest
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v3

      - name: Deploy to production
        run: |
          echo "Deploying to production..."
          # (deployment tool specific)
          # kubectl apply -f k8s/
          # or
          # ./scripts/deploy-prod.sh

      - name: Wait for services
        run: sleep 30

  post-deploy-smoke:
    needs: deploy
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v3

      - name: Setup UV
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Post-deploy smoke test
        id: smoke
        run: |
          make kernel-smoke
          EXIT_CODE=$?

          if [ $EXIT_CODE -ne 0 ]; then
            echo "❌ Post-deploy smoke test FAILED"
            echo "rollback=true" >> $GITHUB_OUTPUT
            exit 1
          fi

          echo "✅ Post-deploy smoke test passed"
          echo "rollback=false" >> $GITHUB_OUTPUT

      - name: Rollback on failure
        if: steps.smoke.outputs.rollback == 'true'
        run: |
          echo "INITIATING ROLLBACK"
          # (rollback tool specific)
          # kubectl rollout undo deployment/swarm-service
          # or
          # ./scripts/rollback.sh

          # Wait for rollback
          sleep 30

          # Verify rollback
          make kernel-smoke
          if [ $? -ne 0 ]; then
            echo "❌ ROLLBACK FAILED (CRITICAL)"
            echo "PAGING ON-CALL"
            # Send PagerDuty alert
            curl -X POST https://events.pagerduty.com/v2/enqueue \
              -H 'Content-Type: application/json' \
              -d '{
                "routing_key": "${{ secrets.PAGERDUTY_KEY }}",
                "event_action": "trigger",
                "payload": {
                  "summary": "CRITICAL: Production rollback failed",
                  "severity": "critical",
                  "source": "GitHub Actions",
                  "custom_details": {
                    "run_url": "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
                  }
                }
              }'
            exit 1
          fi

          echo "✅ Rollback successful"

      - name: Create incident on failure
        if: failure()
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: 'INCIDENT: Production deploy failed (selftest)',
              labels: ['incident', 'critical'],
              body: `## Incident Summary

              **Type**: Production deploy failure (selftest)
              **Time**: ${{ github.event.head_commit.timestamp }}
              **Commit**: ${{ github.sha }}
              **Workflow**: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}

              ## Actions Taken
              - Pre-deploy selftest: ${{ needs.pre-deploy-selftest.result }}
              - Deploy: ${{ needs.deploy.result }}
              - Post-deploy smoke: ${{ steps.smoke.outputs.rollback == 'true' ? 'FAILED (rollback initiated)' : 'PASSED' }}

              ## Next Steps
              1. Review workflow logs
              2. Assess rollback success
              3. Schedule post-mortem within 48 hours
              4. Update SELFTEST_ENVIRONMENT_OPERATIONS.md with learnings
              `
            });
```

---

## FAQ

### Q: Can I merge to staging with a failing AC-COVERAGE?

**A**: Yes, AC-COVERAGE is OPTIONAL tier. It doesn't block merge, but you should track it in issues and fix before production.

**Details**:
- **Dev**: Yes, fix when convenient
- **Staging**: Yes, but document in PR comment
- **Prod**: Shouldn't happen (staging should have caught it), but if it does, investigate

---

### Q: What's the difference between failing in dev vs staging?

**A**: Dev is local, mistakes are cheap. Staging blocks deploy. Prod blocks release and may trigger rollback.

**Breakdown**:

| Aspect | Dev | Staging | Prod |
|--------|-----|---------|------|
| **Cost of failure** | Low (local) | Medium (blocks merge) | High (incident) |
| **Acceptable degradation** | ≤ 3 GOVERNANCE | ≤ 1 GOVERNANCE | 0 (strict) |
| **Escalation** | Fix when convenient | Fix before merge | Page on-call |
| **Rollback** | N/A (local) | Revert PR | Auto-rollback |

---

### Q: My environment has custom infrastructure - do I adjust selftest?

**A**: Yes, see "Extension Points" section in `swarm/SELFTEST_SYSTEM.md`.

**Examples**:
- Custom CI/CD pipeline → Adjust CI workflow files
- Custom monitoring → Adjust metrics/alerting configuration
- Custom deploy tool → Adjust rollback scripts

---

### Q: How do I temporarily disable a failing check?

**A**: Use the override system (with audit trail).

```bash
# Create temporary override (24 hours)
make override-create STEP=<step-id> REASON="<reason>" APPROVER=<name>

# Run selftest (step is skipped)
make selftest

# Revoke when fixed
make override-revoke STEP=<step-id>
```

**Important**: Overrides are logged with who/when/why/expiration. Use responsibly.

---

### Q: What if selftest is slow (> 60s)?

**A**: Investigate step-by-step timing, optimize slow steps, or use kernel-smoke for fast feedback.

```bash
# Identify slow step
uv run swarm/tools/selftest.py --verbose

# Profile single step
time uv run swarm/tools/selftest.py --step <slow-step>

# Use fast feedback loop
make kernel-smoke  # 300-400ms (only KERNEL checks)
```

---

### Q: Can I run selftest in CI without blocking merge?

**A**: Yes, use `continue-on-error: true` in CI and treat results as informational.

**Example**:

```yaml
- name: Selftest (informational)
  run: make selftest
  continue-on-error: true
```

**Use case**: Rolling out selftest to existing projects; don't want to block existing workflows yet.

---

### Q: How do I know if a failure is a "false positive"?

**A**: Run `make selftest-doctor` to diagnose HARNESS_ISSUE vs SERVICE_ISSUE.

```bash
make selftest-doctor

# Output: HARNESS_ISSUE
# → Environment is broken (fix toolchain)

# Output: SERVICE_ISSUE
# → Code is broken (fix code)

# Output: HEALTHY
# → Something subtle; investigate further
```

---

### Q: What if multiple steps fail at once?

**A**: Indicates systemic issue. Start with KERNEL failures first, then GOVERNANCE.

**Triage order**:
1. Fix KERNEL failures (blocking)
2. Fix GOVERNANCE failures (high priority)
3. Fix OPTIONAL failures (low priority)

**Example**:

```bash
# See which steps failed
uv run swarm/tools/selftest.py --plan

# Run each failed step individually
uv run swarm/tools/selftest.py --step core-checks
uv run swarm/tools/selftest.py --step agents-governance

# Fix in priority order: KERNEL → GOVERNANCE → OPTIONAL
```

---

### Q: How do I test my rollback procedure?

**A**: Run a dry-run in staging environment.

```bash
# Deploy to staging
./scripts/deploy-staging.sh

# Intentionally break selftest (simulate failure)
# (e.g., introduce lint error, break test)

# Trigger rollback
./scripts/rollback-staging.sh

# Verify rollback
make kernel-smoke
# Expected: HEALTHY (exit 0)
```

**Best practice**: Test rollback procedure quarterly in staging.

---

### Q: Can I adjust the acceptable degradation thresholds per environment?

**A**: Yes, but document your thresholds in this file.

**Default thresholds**:
- Dev: ≤ 3 GOVERNANCE failures
- Staging: ≤ 1 GOVERNANCE failure
- Prod: 0 failures

**Custom threshold example** (adjust to your org's risk tolerance):

```bash
# Your org's policy: Staging allows 2 GOVERNANCE failures
# Update § Staging Environment Profile in this doc
# Update CI workflow to check: GOVERNANCE_FAILED <= 2
```

---

### Q: What's the expected selftest duration?

**A**:
- **Kernel smoke**: 300-400ms
- **Full selftest**: 15-30s (depends on codebase size)
- **Degraded mode**: Similar to full (checks same steps, just doesn't exit 1 on GOVERNANCE failures)

---

### Q: How do I page on-call from selftest?

**A**: Integrate with PagerDuty, Opsgenie, or similar.

**Example** (PagerDuty):

```bash
# In post-deploy smoke test
make kernel-smoke
if [ $? -ne 0 ]; then
  # Send PagerDuty event
  curl -X POST https://events.pagerduty.com/v2/enqueue \
    -H 'Content-Type: application/json' \
    -d '{
      "routing_key": "YOUR_INTEGRATION_KEY",
      "event_action": "trigger",
      "payload": {
        "summary": "Production selftest KERNEL failure",
        "severity": "critical",
        "source": "selftest",
        "custom_details": {
          "environment": "production",
          "step": "core-checks"
        }
      }
    }'
fi
```

---

## Quick Reference Table

| Environment | Kernel Failure | Governance Failures OK? | Acceptable Count | Escalation | Rollback Policy |
|-------------|----------------|-------------------------|------------------|------------|-----------------|
| **Dev** | NO (fatal) | YES | ≤ 3 | Fix when convenient | N/A (local) |
| **Staging** | NO (fatal) | MAYBE | ≤ 1 | Fix before merge | Revert PR |
| **Prod** | NO (fatal) | NO | 0 | Incident, page on-call | Auto-rollback |

---

## Appendix: Selftest Step Reference

This appendix provides a quick reference for all 10 selftest steps.

| # | Step ID | Tier | Severity | Category | Typical Duration | Failure Impact |
|---|---------|------|----------|----------|------------------|----------------|
| 1 | core-checks | KERNEL | CRITICAL | CORRECTNESS | 10-30s | Code quality compromised |
| 2 | skills-governance | GOVERNANCE | WARNING | GOVERNANCE | <100ms | Skill definitions invalid |
| 3 | agents-governance | GOVERNANCE | WARNING | GOVERNANCE | <1s | Agent definitions misaligned |
| 4 | bdd | GOVERNANCE | WARNING | CORRECTNESS | <500ms | BDD scenarios malformed |
| 5 | ac-status | GOVERNANCE | WARNING | GOVERNANCE | <100ms | AC gaps detected |
| 6 | policy-tests | GOVERNANCE | WARNING | GOVERNANCE | <500ms | Policy violations detected |
| 7 | devex-contract | GOVERNANCE | WARNING | GOVERNANCE | <2s | Flow/agent/skill contracts misaligned |
| 8 | graph-invariants | GOVERNANCE | WARNING | GOVERNANCE | <500ms | Flow graph structure invalid |
| 9 | ac-coverage | OPTIONAL | INFO | GOVERNANCE | <100ms | Coverage below threshold |
| 10 | extras | OPTIONAL | INFO | GOVERNANCE | <100ms | Experimental checks failed |

**Quick diagnostics**:

```bash
# Run single step
uv run swarm/tools/selftest.py --step <step-id>

# See step details
uv run swarm/tools/selftest.py --plan | grep <step-id>

# Run all steps up to a specific one
uv run swarm/tools/selftest.py --until <step-id>
```

---

## Document Maintenance

**Last Updated**: 2025-12-01

**Owners**: Platform team, SRE team

**Review Frequency**: Quarterly (or after major incident)

**Contribution**: Update this document after post-mortems with learnings.

**Template for learnings**:

```markdown
### Scenario X: "<Brief description>"

**Incident**: <date>, <environment>
**Root cause**: <explanation>
**Resolution**: <what we did>
**Learning**: <what we changed>

**Dev remediation**:
<commands>

**Staging remediation**:
<commands>

**Production remediation**:
<commands>
```

**Feedback**: Submit issues or PRs to improve this doc.

---

## See Also

- **System Design**: `swarm/SELFTEST_SYSTEM.md` — Architecture, tiers, design goals
- **Operator Checklist**: `docs/OPERATOR_CHECKLIST.md` — Pre-release and monitoring checklists
- **API Contract**: `docs/SELFTEST_API_CONTRACT.md` — Endpoint specs
- **AC Matrix**: `docs/SELFTEST_AC_MATRIX.md` — AC-to-step traceability
- **Governance**: `docs/SELFTEST_GOVERNANCE.md` — Common issues & fixes

---

**End of Document**
