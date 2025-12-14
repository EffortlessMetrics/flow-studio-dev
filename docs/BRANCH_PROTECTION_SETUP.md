# Branch Protection Setup Guide

This guide helps repository administrators configure branch protection rules to enforce selftest validation as a mandatory merge gate.

> **Status: Phase 2 Complete (v2.0.0)**
>
> The Selftest Governance Gate is now available and ready to be enabled as a required check on `main`. All infrastructure is in place; this guide walks you through enabling it.

---

## Admin Quick Setup (2 Minutes)

For admins who just want to enable the governance gate now that Phase 2 is complete:

1. Go to **Settings** > **Branches** > **Edit** (on the `main` rule)
2. Under "Require status checks to pass before merging", add:
   - **Selftest Governance Gate** (from `.github/workflows/selftest-governance-gate.yml`)
   - **Swarm Validation** (from `.github/workflows/swarm-validate.yml`) - if not already added
3. Click **Save changes**

**That's it.** The gate is now enforcing AC matrix alignment, test bijection, and degradation system coherence on every PR that touches selftest infrastructure.

---

## Prerequisites

- Repository admin access (required to configure branch protection)
- GitHub workflows present and working:
  - `.github/workflows/swarm-validate.yml` (general swarm validation)
  - `.github/workflows/selftest-governance-gate.yml` (selftest-specific governance)
- Selftest system is operational (verify with `make selftest`)

---

## Quick Start: 5-Minute Setup (Full Configuration)

If you want to enable complete branch protection with both swarm and selftest governance enforcement:

1. Go to **Settings** > **Branches** in your GitHub repository
2. Click **Add rule** under "Branch protection rules"
3. Enter `main` as the branch name pattern
4. Check these boxes:
   - **Require status checks to pass before merging**
   - **Require branches to be up to date before merging**
   - Search for and select both:
     - **Swarm Validation** (from `.github/workflows/swarm-validate.yml`)
     - **Selftest Governance Gate** (from `.github/workflows/selftest-governance-gate.yml`)
   - **Require approvals** > Set to **1** approval
   - **Dismiss stale pull request approvals when new commits are pushed**
5. Click **Create** (or **Save changes** if editing)

**Result**: All PRs to `main` must pass both validation workflows and get 1 approval before merging. PRs touching selftest infrastructure will additionally be validated for AC matrix alignment and test coherence.

---

## Step-by-Step Setup

### Step 1: Verify Workflow Exists

Before configuring branch protection, ensure the CI workflow is present and functional:

```bash
# Check that the workflow file exists
ls -l .github/workflows/swarm-validate.yml

# Run the workflow locally to verify it works
make dev-check
```

**Expected output**: `dev-check` should exit with code 0 (success) or 1 (validation failure). If you see code 2, there's a configuration error—fix that first before proceeding.

---

### Step 2: Enable Branch Protection on `main`

1. Navigate to your repository on GitHub
2. Click **Settings** (top right, requires admin access)
3. In the left sidebar, click **Branches**
4. Under "Branch protection rules", click **Add rule**

**Branch name pattern**: `main`

---

### Step 3: Configure Required Status Checks

In the "Protect matching branches" section:

#### 3a. Require Status Checks

✅ **Require status checks to pass before merging**

This ensures the CI workflow must pass before any PR can be merged.

#### 3b. Select the Required Workflows

After checking the box above, a search field appears. Add both checks:

**1. Swarm Validation** (general swarm governance):

Type `Swarm Validation` and select the check. This corresponds to `.github/workflows/swarm-validate.yml`:

```yaml
name: Swarm Validation
jobs:
  validate-swarm:
    name: validate-swarm
```

**2. Selftest Governance Gate** (selftest-specific validation):

Type `Selftest Governance Gate` and select the check. This corresponds to `.github/workflows/selftest-governance-gate.yml`:

```yaml
name: Selftest Governance Gate
jobs:
  selftest-governance-gate:
    name: Selftest Governance Gate
```

**Important**: The check names must match exactly. If a check doesn't appear, the workflow hasn't run yet on any branch. Push a commit to trigger it, then return to this setup.

**Note**: The Selftest Governance Gate only runs on PRs that touch selftest infrastructure files (see the workflow's `paths` filter). For PRs that don't touch those files, only Swarm Validation will run.

#### 3c. Require Up-to-Date Branches

✅ **Require branches to be up to date before merging**

This prevents merge races where a PR passes on an outdated base but would fail on the latest `main`.

---

### Step 4: Configure Pull Request Approvals

✅ **Require a pull request before merging**

This is enabled by default when you create a branch protection rule.

Within this section:

✅ **Require approvals**: Set to **1** (or higher, depending on your team's policy)

This ensures at least one human reviews the receipts (flow artifacts, test results, etc.) before merge.

✅ **Dismiss stale pull request approvals when new commits are pushed**

This forces a fresh review if the PR changes after approval. Critical for ensuring approvers saw the final state.

---

### Step 5: (Optional) Additional Safeguards

Consider enabling these for stricter governance:

- **Require signed commits**: Ensures all commits are cryptographically signed (GPG/SSH)
- **Require linear history**: Prevents merge commits (enforce rebase or squash merges)
- **Restrict push access**: Only allow specific teams/users to push to `main`
- **Do not allow bypassing the above settings**: Prevents admins from force-merging

---

### Step 6: Apply Rule to Release Branches

Repeat Steps 2–5 for release branches:

**Branch name pattern**: `release/*`

This protects all branches like `release/v1.0`, `release/v2.0`, etc.

**Same settings as `main`**:
- Require status checks (Swarm Validation)
- Require 1 approval
- Dismiss stale approvals

---

## Understanding the Workflows

### Swarm Validation Workflow

The `.github/workflows/swarm-validate.yml` workflow runs `make dev-check`, which includes:

```bash
make gen-adapters
make gen-flows
make check-adapters
make check-flows
make validate-swarm
make selftest
```

### Selftest Governance Gate Workflow

The `.github/workflows/selftest-governance-gate.yml` workflow runs selftest-specific governance checks:

1. **AC Matrix Freshness** - Validates that `docs/SELFTEST_AC_MATRIX.md` is aligned with implementation
2. **AC Test Suite** - Runs bijection, API contract, and traceability tests
3. **Degradation Tests** - Validates schema compliance, CLI contracts, and status coherence
4. **Diagnostics** (informational) - Runs `selftest-doctor` for troubleshooting info

This workflow only triggers on PRs that modify selftest infrastructure files (see `paths` in the workflow YAML).

### Exit Codes

**Exit codes** (both workflows):

- **0 (success)**: All checks passed. PR can proceed.
- **1 (failure)**: KERNEL or GOVERNANCE tier failed (in strict mode). PR is blocked.
- **2 (config error)**: Selftest harness is broken (missing files, invalid config). PR is blocked.

**What developers see**:

- ✅ Green check: Workflow passed (exit 0)
- ❌ Red X: Workflow failed (exit 1 or 2)
- 🟡 Yellow dot: Workflow is still running

**Troubleshooting**: If a PR fails, developers should:

1. Run `make selftest-doctor` locally to diagnose
2. Run `make selftest --step <failing-step> --verbose` to see details
3. Fix the issue and push a new commit
4. The workflow will re-run automatically

See `docs/SELFTEST_DEVELOPER_WORKFLOW.md` for the full developer experience.

---

## Enforcement Behavior

### KERNEL Failures

**Severity**: CRITICAL (P0)

**Behavior**: Always blocks merge, no exceptions.

**Examples**:
- Python code has syntax errors (doesn't compile)
- Core checks fail (ruff linting errors)

**Resolution**: Fix immediately. No workaround available.

**Timeline**: < 15 minutes to green CI

---

### GOVERNANCE Failures

**Severity**: WARNING (P1 or P2)

**Behavior**: Blocks merge in strict mode. Can be worked around with `--degraded` mode (see below).

**Examples**:
- Agent frontmatter out of sync with config
- Flow references unknown agents
- BDD scenarios have formatting errors

**Resolution**:
- **If fix is < 10 minutes**: Fix it and push
- **If fix is > 10 minutes**: Document in PR description, merge with `--degraded`, fix in follow-up PR

**Degraded Mode Workflow**:

Developers can temporarily bypass GOVERNANCE failures by documenting the degradation:

1. Run `make selftest-degraded` locally to confirm only GOVERNANCE is failing (KERNEL passes)
2. Add a comment to the PR description:
   ```markdown
   ## Selftest Status: DEGRADED

   - **Tier**: GOVERNANCE (agents-governance step failed)
   - **Reason**: Agent config out of sync due to upstream merge
   - **Fix planned**: Follow-up PR #<issue-number>
   - **Approved by**: @tech-lead
   ```
3. Request an admin bypass (or merge locally with admin rights)

**Important**: Degraded mode is a **temporary workaround**, not a permanent state. All degradations must be tracked and resolved.

---

### OPTIONAL Failures

**Severity**: INFORMATIONAL (P3 or P4)

**Behavior**: Never blocks merge. Logged for informational purposes only.

**Examples**:
- Coverage below threshold (80%)
- Experimental checks failing

**Resolution**: Address in follow-up PRs at team's discretion.

---

## Troubleshooting

### Problem: Workflow Doesn't Appear in Status Check List

**Symptom**: When setting up branch protection, the "Swarm Validation" check doesn't appear in the search results.

**Cause**: The workflow hasn't run yet on any branch in the repository.

**Fix**:
1. Push any commit to any branch (e.g., a README edit on a feature branch)
2. Wait for the workflow to complete (check the **Actions** tab)
3. Return to branch protection settings; the check should now appear

---

### Problem: CI Passes Locally but Fails in GitHub

**Symptom**: `make dev-check` passes on developer's machine but fails in CI.

**Cause**: Environment differences (Python version, missing dependencies, etc.)

**Fix**:
1. Check the workflow logs in the **Actions** tab
2. Compare CI Python version with local: `python --version`
3. Ensure `uv sync --extra dev` was run in CI (check workflow YAML)
4. Run `make selftest-doctor` locally to rule out harness issues

---

### Problem: PR Approved but Can't Merge (Status Check Pending)

**Symptom**: PR has 1 approval but the "Merge pull request" button is disabled. Status check shows 🟡 (yellow dot).

**Cause**: Workflow is still running or hasn't started.

**Fix**:
1. Check the **Actions** tab to see workflow status
2. If stuck (> 10 minutes), cancel and re-run the workflow
3. If branch is out of date, merge `main` into the PR branch and workflow will re-run

---

### Problem: Admin Needs to Force-Merge During Incident

**Symptom**: Production incident requires hotfix, but CI is red due to unrelated failure.

**Process**:
1. **Document the override**:
   - Create an incident ticket (e.g., Jira, GitHub issue)
   - Note why CI is failing and why it's safe to bypass
   - Get explicit approval from tech lead or on-call
2. **Use admin bypass**:
   - As a repo admin, click "Merge without waiting for status checks"
   - Reference the incident ticket in the merge commit message
3. **Fix forward**:
   - After incident is resolved, create a follow-up PR to fix the CI failure
   - Document in incident postmortem

See `docs/SELFTEST_OWNERSHIP.md` for escalation paths.

---

## Verifying the Setup

After configuring branch protection, verify it works with these test scenarios:

### Test 1: Submit a Passing PR (Basic)

```bash
# Create a test branch
git checkout -b test-branch-protection
echo "# Test" >> README.md
git add README.md
git commit -m "test: verify branch protection"
git push origin test-branch-protection

# Open PR on GitHub
gh pr create --title "Test branch protection" --body "Verifying selftest enforcement"
```

**Expected outcome**: CI runs, passes, you can merge after 1 approval.

---

### Test 2: Submit a Failing PR (Swarm Validation)

```bash
# Introduce a linting error
echo "import os,sys" > bad_style.py  # ruff will reject this
git add bad_style.py
git commit -m "test: introduce linting error"
git push origin test-branch-protection

# Wait for CI
```

**Expected outcome**: Swarm Validation fails with exit code 1, PR is blocked from merge.

**Cleanup**: `git rm bad_style.py && git commit --amend && git push --force`

---

### Test 3: Verify Selftest Governance Gate (AC/Governance Failure)

This test verifies the Selftest Governance Gate specifically blocks PRs with governance issues:

```bash
# Create a test branch that touches selftest infrastructure
git checkout -b test-governance-gate

# Break an AC (e.g., add a fake AC that doesn't exist in implementation)
# Or break AC matrix alignment by editing docs/SELFTEST_AC_MATRIX.md
echo "| AC-999 | FAKE | fake-step | Fake AC for testing |" >> docs/SELFTEST_AC_MATRIX.md
git add docs/SELFTEST_AC_MATRIX.md
git commit -m "test: break AC matrix alignment"
git push origin test-governance-gate

# Open PR
gh pr create --title "Test governance gate" --body "Verifying AC matrix enforcement"
```

**Expected outcome**:
1. Selftest Governance Gate workflow triggers (because `docs/SELFTEST_*.md` is in the paths filter)
2. The "[GOVERNANCE] Check AC Matrix Freshness" step fails
3. PR is blocked from merge
4. PR receives a comment with the governance gate results table

**Cleanup**: Close the PR and delete the branch:
```bash
gh pr close --delete-branch
git checkout main
git branch -D test-governance-gate
```

---

### Test 4: Verify Gate Passes After Fix

After running Test 3, verify fixing the issue allows merge:

```bash
# Fix the AC matrix
git checkout -b test-governance-fix
# Make a valid change to selftest docs
echo "" >> docs/SELFTEST_SYSTEM.md  # Add blank line (harmless)
git add docs/SELFTEST_SYSTEM.md
git commit -m "test: valid selftest doc change"
git push origin test-governance-fix

# Open PR
gh pr create --title "Test governance gate (pass)" --body "Verifying gate passes on valid changes"
```

**Expected outcome**:
1. Selftest Governance Gate workflow triggers
2. All governance checks pass (AC Freshness, AC Tests, Degradation Tests)
3. PR shows green checkmark for Selftest Governance Gate
4. PR can be merged after 1 approval

**Cleanup**: Merge or close the PR, delete the branch

---

## FAQ

### Q: Can I configure different rules for `main` vs `release/*`?

**A**: Yes. Create separate branch protection rules for each pattern. For example:
- `main` — require 1 approval
- `release/*` — require 2 approvals + additional checks

### Q: What if I need to merge a PR that fails GOVERNANCE but passes KERNEL?

**A**: Use the degraded mode workflow (see "GOVERNANCE Failures" above). Document why in the PR description, get approval, and track a follow-up fix.

### Q: Can developers run the exact same checks locally that CI runs?

**A**: Yes. For the Swarm Validation workflow, run `make dev-check` locally. For the Selftest Governance Gate checks specifically, run:

```bash
# AC Matrix Freshness
uv run swarm/tools/check_selftest_ac_freshness.py

# AC Tests
uv run pytest tests/test_selftest_ac_bijection.py tests/test_selftest_ac_traceability.py tests/test_selftest_api_contract.py tests/test_selftest_api_contract_coherence.py -v

# Degradation Tests
uv run pytest tests/test_selftest_degradation_schema_compliance.py tests/test_selftest_degradations_cli_contract.py tests/test_selftest_status_degradation_coherence.py tests/test_selftest_degradation_log.py -v
```

### Q: What's the difference between "Swarm Validation" and "Selftest Governance Gate"?

**A**:
- **Swarm Validation** — Runs on all PRs touching `swarm/` or `.claude/`. Validates agent/flow definitions, runs the full dev-check suite.
- **Selftest Governance Gate** — Runs only on PRs touching selftest infrastructure files. Validates AC matrix alignment, test bijection, and degradation system coherence.

Both should be required checks on `main` for complete governance coverage.

### Q: What's the difference between `make selftest` and `make selftest-fast`?

**A**:
- `make selftest` — Full 16-step suite (~2 minutes)
- `make selftest-fast` — KERNEL only (~400ms)
- `make selftest-govern` — GOVERNANCE only (no code checks)

Use `selftest-fast` for tight inner-loop iteration. Use full `selftest` before pushing.

### Q: How do I see detailed failure logs when CI is red?

**A**: Click on the failing workflow in the **Actions** tab, expand the failing step, and read the logs. Or run `make selftest-doctor` locally to diagnose.

---

## Related Documentation

- **Developer workflow**: `docs/SELFTEST_DEVELOPER_WORKFLOW.md` — How to use selftest locally
- **Ownership & escalation**: `docs/SELFTEST_OWNERSHIP.md` — Who to contact when things break
- **Governance reference**: `docs/SELFTEST_GOVERNANCE.md` — Quick fixes for common issues
- **System architecture**: `docs/SELFTEST_SYSTEM.md` — Deep dive into the 16 steps

---

## Changelog

### v2.0.0 (2025-12-01)
- **Phase 2 Complete**: Added Admin Quick Setup section for enabling the gate now
- Added Selftest Governance Gate as a required check alongside Swarm Validation
- Expanded workflow documentation to cover both workflows
- Added Test 3 and Test 4 for verifying the governance gate works
- Added FAQ entry explaining the difference between the two workflows
- Updated prerequisites to list both workflow files

### v1.0.0 (2025-12-01)
- Initial branch protection setup guide
- Documented KERNEL/GOVERNANCE/OPTIONAL enforcement behavior
- Added troubleshooting section and FAQ
