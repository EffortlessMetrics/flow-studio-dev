# Selftest Developer Workflow

This guide explains how developers should use the selftest system in their daily work: local testing, CI integration, and debugging when things fail.

**Target audience**: Developers contributing to the swarm (agents, flows, skills) or the codebase.

---

## Quick Reference Card

**Before every PR:**
```bash
make selftest-fast    # ~400ms, catches KERNEL issues
```

**Before pushing governance/config changes:**
```bash
make selftest-govern  # ~30s, validates swarm config
```

**When stuck on a failure:**
```bash
make selftest-suggest-remediation  # Get fix hints
```

**Full validation:**
```bash
make selftest         # ~2min, all 16 steps
```

---

## TL;DR: Three Commands You Need

```bash
# Before committing (fast, inner-loop iteration)
make selftest-fast      # ~400ms, KERNEL only

# Before pushing (full validation)
make selftest           # ~120s, all 16 steps

# When CI fails (diagnostic)
make selftest-doctor    # Diagnose HARNESS_ISSUE vs SERVICE_ISSUE
```

**Golden rule**: Run `make selftest-fast` before every commit. Run `make selftest` before every push.

---

## The Developer Loop

### Inner-Loop Iteration (Tight Feedback)

When you're actively coding and want fast feedback:

```bash
# Make some changes to code or swarm config
vim swarm/config/agents/my-agent.yaml

# Fast check (KERNEL tier only, ~400ms)
make selftest-fast

# If it passes, commit
git add swarm/config/agents/my-agent.yaml
git commit -m "feat: update my-agent config"

# If it fails, fix and repeat
```

**What `selftest-fast` checks**:
- Python syntax errors (compileall)
- Linting (ruff)
- No unit tests, no governance checks

**When to use**: During active development (tight iteration loop).

---

### Pre-Push Validation (Full Check)

Before pushing to GitHub:

```bash
# Run the full selftest suite (all 16 steps)
make selftest

# If it passes, push
git push origin my-feature-branch

# If it fails, diagnose and fix (see Debugging section)
make selftest-doctor
```

**What `make selftest` checks**:
- KERNEL (Python checks)
- GOVERNANCE (agent configs, flows, BDD, AC matrix, policy, contracts, graph invariants)
- OPTIONAL (coverage, experimental checks)

**Exit codes**:
- **0**: All passed → safe to push
- **1**: KERNEL or GOVERNANCE failed → fix before pushing
- **2**: Config error (selftest harness broken) → escalate

**When to use**: Before every `git push` (catch issues before CI does).

---

### Governance-Only Check (No Code Tests)

If you only changed swarm config (agents, flows, skills) and want to skip code checks:

```bash
# Run governance checks only (no core-checks, no code tests)
make selftest-govern

# Equivalent to:
uv run swarm/tools/selftest.py --until governance
```

**What `selftest-govern` checks**:
- Agent config validation
- Flow reference integrity
- BDD scenario structure
- AC matrix consistency
- Policy-as-code (OPA/Conftest)
- Flow graph invariants

**When to use**: When you changed `swarm/` or `.claude/` but not `src/` or `tests/`.

---

## CI Integration

### How CI Uses Selftest

GitHub Actions runs `.github/workflows/swarm-validate.yml` on every PR:

```yaml
name: Swarm Validation
on: [pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run swarm validation
        run: make dev-check
```

**What `make dev-check` does**:

```bash
make gen-adapters      # Regenerate adapters from config
make gen-flows         # Regenerate flows from config
make check-adapters    # Verify adapters match config
make check-flows       # Verify flows match config
make validate-swarm    # Run FR-001 through FR-005 checks
make selftest          # Run all 16 selftest steps
```

**Result**: CI blocks merge if any step fails.

---

### What Developers See

When you open a PR, you'll see a status check called **"Swarm Validation"**:

- ✅ **Green check**: All passed → ready for review
- ❌ **Red X**: Something failed → click "Details" to see logs
- 🟡 **Yellow dot**: Still running → wait

**If CI fails**, click "Details" to see which step failed, then:

1. Run `make selftest-doctor` locally to diagnose
2. Run `make selftest --step <failing-step> --verbose` to see details
3. Fix the issue and push a new commit
4. CI will re-run automatically

---

## Pytest Test Taxonomy

In addition to the selftest system, you can run pytest tests directly using marks to filter by test type:

### Test Categories

| Mark | Speed | Description | When to Use |
|------|-------|-------------|-------------|
| `unit` | <100ms | Isolated logic tests, no I/O, no subprocesses | TDD inner loop |
| `integration` | 100ms-1s | CLI, file I/O, subprocess tests | Pre-push |
| `slow` | >1s | Full subprocess, extensive I/O, network | Nightly CI |
| `quick` | <100ms | Alias for unit + mocked tests | Fast iteration |

### Make Targets

```bash
# Run by category
make test-unit           # Isolated logic tests only
make test-integration    # CLI, file I/O, subprocess tests
make test-slow           # Tests that take >1 second

# Run all pytest tests
make test-all            # Full pytest suite

# Combine with selftest
make selftest            # Swarm governance (16 steps)
make test-all            # Pytest coverage
```

### Marking Your Tests

When writing new tests, add appropriate marks:

```python
import pytest

@pytest.mark.unit
def test_parse_config():
    """Pure logic, no I/O."""
    assert parse_config("key=value") == {"key": "value"}

@pytest.mark.integration
def test_cli_output(tmp_path):
    """Involves file I/O."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("key: value")
    assert load_config(config_file) == {"key": "value"}

@pytest.mark.slow
@pytest.mark.integration
def test_full_workflow(tmp_path):
    """Full end-to-end workflow, takes several seconds."""
    # ... extensive setup and teardown
```

### CI Behavior

- **CI runs**: `make test-unit` (fast feedback) + selected integration tests
- **CI does NOT run**: `@pytest.mark.slow` tests by default (run in nightly builds)
- **Local development**: Run `make test-all` before major PRs

---

## Debugging Failures

### Step 1: Run the Doctor

When selftest fails (locally or in CI), start here:

```bash
make selftest-doctor
```

**Output**:

```
Diagnosing selftest health...

Status: HARNESS_ISSUE
Diagnosis: Python not found in PATH
Recommendation: Install Python 3.11+ and add to PATH
```

or

```
Status: SERVICE_ISSUE
Diagnosis: Code has linting errors (step: core-checks)
Recommendation: Run `make selftest --step core-checks --verbose` for details
```

**Interpretation**:

| Status | Meaning | Who Fixes |
|--------|---------|-----------|
| `HEALTHY` | All systems operational | No action needed |
| `HARNESS_ISSUE` | Environment broken (Python, Rust, etc.) | DevOps / local setup |
| `SERVICE_ISSUE` | Code/config is broken | Developer (you) |

---

### Step 2: Run the Failing Step in Verbose Mode

If the doctor says `SERVICE_ISSUE` and identifies a step:

```bash
# Run the failing step with verbose output
make selftest --step core-checks --verbose
```

or use the direct command:

```bash
uv run swarm/tools/selftest.py --step core-checks --verbose
```

**Output will show**:
- Full command being run
- stdout and stderr from the command
- Exit code
- Actionable error messages

**Example failure output**:

```
Step: core-checks
Command: uv run swarm/tools/validate_swarm.py
Exit code: 1

Error: swarm/config/agents/test.yaml: missing required field 'color'
Fix: Add `color: green` to frontmatter

Recommendation: Fix the issue and re-run.
```

---

### Step 3: Fix and Re-Run

After fixing the issue:

```bash
# Re-run the failing step to verify the fix
make selftest --step core-checks --verbose

# Or re-run the full suite
make selftest
```

**If still failing**, repeat Step 2 (check verbose output) or escalate to the maintainer (see `docs/SELFTEST_OWNERSHIP.md`).

---

## Common Scenarios

### Scenario 1: "I Changed an Agent Config and CI Failed"

**Symptom**: Edited `swarm/config/agents/my-agent.yaml` and CI is now red.

**Diagnosis**:

```bash
# Check what's wrong
make selftest --step agents-governance --verbose
```

**Common issues**:

1. **Color mismatch**: Frontmatter color doesn't match role family
   - **Fix**: Update color in YAML to match role family (see `CLAUDE.md` color table)

2. **Missing frontmatter field**: YAML is missing `name`, `description`, or `color`
   - **Fix**: Add the missing field to the YAML file

3. **Agent not in registry**: `.claude/agents/my-agent.md` exists but not in `swarm/AGENTS.md`
   - **Fix**: Add entry to `swarm/AGENTS.md` or remove the file

**After fixing**:

```bash
# Regenerate adapters
make gen-adapters

# Verify fix
make check-adapters
make validate-swarm

# Push
git add swarm/config/agents/my-agent.yaml .claude/agents/my-agent.md
git commit -m "fix: update my-agent config"
git push
```

---

### Scenario 2: "I Added a BDD Scenario and Selftest Failed"

**Symptom**: Added a new scenario to `features/selftest.feature` and the `bdd` step is failing.

**Diagnosis**:

```bash
make selftest --step bdd --verbose
```

**Common issues**:

1. **Syntax error in Gherkin**: Missing `@` tag, malformed step, etc.
   - **Fix**: Lint the feature file with your editor's Gherkin plugin or manually check syntax

2. **Missing AC tag**: Scenario doesn't have an `@AC-*` tag
   - **Fix**: Add `@AC-SELFTEST-MY-FEATURE` tag to the scenario

3. **Undefined step**: Scenario uses a step that doesn't have a pytest implementation
   - **Fix**: Add the corresponding test to `tests/test_selftest_acceptance.py`

**After fixing**:

```bash
# Verify fix
make selftest --step bdd --verbose

# Run full selftest to ensure no other issues
make selftest

# Push
git add features/selftest.feature
git commit -m "feat: add BDD scenario for AC-SELFTEST-MY-FEATURE"
git push
```

---

### Scenario 3: "CI Passed Locally but Failed in GitHub"

**Symptom**: `make selftest` passes on your machine but fails in CI.

**Possible causes**:

1. **Environment difference**: CI uses a different Python version, missing dependencies, etc.
2. **Branch out of date**: PR branch is behind `main`, and a recent merge broke something
3. **Flaky test**: A test is non-deterministic (rare in selftest, but possible)

**Diagnosis**:

```bash
# Check CI logs (GitHub Actions tab)
gh run view <run-id>

# Compare local environment with CI
python --version  # CI uses Python 3.11+
uv --version      # CI uses uv for dependency management

# Ensure dependencies are up to date
uv sync --extra dev

# Re-run selftest locally
make selftest
```

**If still failing in CI only**:

1. Merge `main` into your PR branch to get the latest changes
2. Push and let CI re-run
3. If still failing, escalate to maintainer (see `docs/SELFTEST_OWNERSHIP.md`)

---

### Scenario 4: "I Need to Merge a PR but GOVERNANCE is Failing"

**Symptom**: CI failed on a GOVERNANCE step (e.g., `agents-governance`), but the fix will take > 10 minutes and you need to unblock the team.

**Degraded Mode Workflow**:

1. **Verify KERNEL passes**:
   ```bash
   uv run swarm/tools/kernel_smoke.py
   # Exit code should be 0
   ```

2. **Run in degraded mode locally**:
   ```bash
   make selftest-degraded
   # Exit code should be 0 (GOVERNANCE warnings are non-blocking)
   ```

3. **Document in PR description**:
   ```markdown
   ## Selftest Status: DEGRADED

   - **Tier**: GOVERNANCE (agents-governance step failed)
   - **Reason**: Agent config out of sync due to upstream merge conflict
   - **Fix planned**: Follow-up PR #<issue-number>
   - **Approved by**: @tech-lead
   ```

4. **Get approval and merge**:
   - Request admin bypass (if branch protection is strict)
   - Or merge locally with `git push origin HEAD:main` (if you have admin rights)

5. **Create follow-up PR to fix degradation**:
   ```bash
   git checkout -b fix/governance-degradation
   # Fix the issue
   git commit -m "fix: resolve agents-governance degradation"
   git push origin fix/governance-degradation
   gh pr create --title "Fix governance degradation from PR #<number>"
   ```

**Important**: Degraded mode is a **temporary workaround**. All degradations must be tracked and resolved.

---

## Quick Reference: Make Targets

| Command | What It Does | When to Use | Typical Time |
|---------|--------------|-------------|--------------|
| `make selftest-fast` | KERNEL only (Python checks) | Inner-loop iteration (tight feedback) | ~400ms |
| `make selftest` | Full 16-step suite | Before pushing (comprehensive check) | ~120s |
| `make selftest-govern` | GOVERNANCE only (no code checks) | Changed swarm config only | ~30s |
| `make selftest-doctor` | Diagnose failures | When selftest fails | ~2s |
| `make selftest-degraded` | Run in degraded mode (GOVERNANCE warns) | Temporary workaround for GOVERNANCE failures | ~120s |
| `make selftest --plan` | Show all steps (introspection) | Understand what selftest does | ~0.2s |
| `make selftest --step <id>` | Run a single step | Debug specific failure | Varies |
| `make selftest-incident-pack` | Gather diagnostics for incidents | When escalating to maintainer | ~5s |
| `make selftest-suggest-remediation` | Get remediation suggestions | When stuck on a failure | ~2s |

---

## Quick Reference: Exit Codes

| Exit Code | Meaning | What to Do |
|-----------|---------|------------|
| 0 | All passed | Proceed (commit/push/merge) |
| 1 | KERNEL or GOVERNANCE failed | Fix the issue (see Debugging section) |
| 2 | Config error (harness broken) | Escalate to maintainer (see SELFTEST_OWNERSHIP.md) |

---

## Advanced Usage

### Run a Specific Step

To debug a single failing step:

```bash
# Run agents-governance step only
make selftest --step agents-governance --verbose
```

or directly:

```bash
uv run swarm/tools/selftest.py --step agents-governance --verbose
```

---

### See the Full Plan

To understand what selftest does (all 16 steps, tiers, dependencies):

```bash
make selftest --plan
```

or use the API:

```bash
curl http://localhost:5000/api/selftest/plan | jq .
```

(requires Flow Studio to be running: `make flow-studio`)

---

### JSON Output for Tooling

If you're building automation around selftest:

```bash
uv run swarm/tools/selftest.py --json-v2 > selftest_report.json
```

**Output contract**:

```json
{
  "status": "PASS" | "FAIL",
  "summary": {
    "total_steps": 10,
    "passed": 9,
    "failed": 1,
    "warnings": 0
  },
  "steps": [
    {
      "id": "core-checks",
      "name": "Core Checks",
      "tier": "KERNEL",
      "status": "PASS",
      "message": "All checks passed"
    }
  ]
}
```

---

### Incident Pack (For Escalation)

If you need to escalate a failure to the maintainer:

```bash
# Gather all diagnostic info
make selftest-incident-pack
```

**Output**: Creates `selftest_incident_<timestamp>.tar.gz` with:
- Full selftest output (verbose)
- `selftest_degradations.log`
- `selftest_doctor` output
- Environment info (Python version, uv version, git status)
- Recent git commits

**Send this to maintainer** (see `docs/SELFTEST_OWNERSHIP.md` for contact info).

---

### Remediation Suggestions (AI-Assisted)

If you're stuck on a failure and want suggestions:

```bash
# Get AI-suggested fixes
make selftest-suggest-remediation
```

**Output**: Reads `selftest_degradations.log` and suggests fixes based on:
- Historical patterns (common fixes for this step)
- Error message analysis
- Related documentation links

**Note**: This is **read-only** (no code changes). You still need to apply the fix manually.

---

## FAQ

### Q: How do I skip selftest for a quick experiment?

**A**: You can't skip selftest in CI (it's mandatory). Locally, just don't run it. But you'll be blocked when you push. Better to run `make selftest-fast` (fast enough for tight iteration).

---

### Q: Can I run selftest in parallel (speed up CI)?

**A**: Not yet. Parallel execution is a Phase 3 feature (see `docs/SELFTEST_OWNERSHIP.md` roadmap). Current baseline is ~120s for full suite, which is acceptable for CI.

---

### Q: What if I need to merge urgently and CI is red?

**A**: Use the degraded mode workflow (see "Scenario 4" above). Document the degradation, get approval, merge with admin bypass, and fix forward in a follow-up PR.

---

### Q: How do I add a new selftest step?

**A**: See `docs/SELFTEST_OWNERSHIP.md` § "Task: Add a New Selftest Step". Short version:
1. Add step to `swarm/tools/selftest_config.py`
2. Implement the check (exit 0 = pass, 1 = fail)
3. Add to AC matrix (`docs/SELFTEST_AC_MATRIX.md`)
4. Write tests (`tests/test_*.py`)
5. Run `make selftest` to verify

---

### Q: Where do I report selftest bugs?

**A**: Create a GitHub issue with label `selftest`. Include:
- Full selftest output (run with `--verbose`)
- Output of `make selftest-doctor`
- Environment info (OS, Python version, uv version)

See `docs/SELFTEST_OWNERSHIP.md` for maintainer contact info.

---

## Pre-Commit Hooks

The repo includes pre-commit hooks that run validation on commit. To enable them:

```bash
# Install pre-commit (one time)
pip install pre-commit

# Enable hooks for this repo
pre-commit install
```

**What the hooks check:**
- `swarm-validate`: Validates swarm spec/impl alignment (strict mode)
- `selftest-ac-freshness`: Checks AC matrix is up to date
- `selftest-ac-tests`: Runs AC traceability tests
- `selftest-degradation-tests`: Runs degradation system tests

**When hooks trigger:**
- Hooks run automatically on `git commit`
- Only relevant hooks run based on which files changed
- If a hook fails, the commit is blocked until you fix the issue

**To skip hooks temporarily** (not recommended):
```bash
git commit --no-verify -m "message"
```

**To run hooks manually:**
```bash
pre-commit run --all-files
```

---

## Related Documentation

- **Branch protection setup**: `docs/BRANCH_PROTECTION_SETUP.md` — How to enforce selftest in CI
- **Ownership & escalation**: `docs/SELFTEST_OWNERSHIP.md` — Who to contact when things break
- **Governance reference**: `docs/SELFTEST_GOVERNANCE.md` — Quick fixes for common issues
- **System architecture**: `docs/SELFTEST_SYSTEM.md` — Deep dive into the 16 steps
- **AC matrix**: `docs/SELFTEST_AC_MATRIX.md` — Traceability of acceptance criteria

---

## Changelog

### v1.0.0 (2025-12-01)
- Initial developer workflow documentation
- Added three-command TL;DR section
- Documented inner-loop, pre-push, and governance-only workflows
- Added common scenarios and troubleshooting guide
- Added quick reference tables for Make targets and exit codes
