# Selftest System Documentation

> **Context:** This selftest system is wired into the **Flow Studio demo harness** in
> this repo.
>
> It validates both the swarm configuration (agents, flows, skills) and the Flow Studio
> runtime (APIs, health, governance). Other repos can reuse this pattern or depend on
> it as a library.

## Overview

The selftest system is a **layered, degradable governance framework** that validates the swarm's health without treating every failure as "everything is broken."

### Core Design

**Three tiers of severity:**
- **KERNEL** (critical): Must always pass. Examples: ruff linting, compile checks, unit tests.
- **GOVERNANCE** (warning): Should pass. Examples: agent validation, policy checks.
- **OPTIONAL** (info): Nice-to-have. Examples: coverage thresholds, experimental checks.

**Three operational modes:**
- **Strict** (default): KERNEL + GOVERNANCE failures block (exit 1)
- **Degraded** (flag: `--degraded`): Only KERNEL failures block (exit 1)
- **Kernel-only** (flag: `--kernel-only`): Only the 1 KERNEL step runs

**Key insight**: When selftest fails, the response depends on *what* failed, not just "did it fail."

---

## Selftest Contract

The set of **16 selftest steps** is a governed contract. If you add or remove steps, you must update:

1. `swarm/tools/selftest_config.py` — The authoritative step definitions
2. `swarm/SELFTEST_SYSTEM.md` — This document's step table
3. `docs/SELFTEST_GOVERNANCE.md` — Quick reference
4. `docs/SELFTEST_DEVELOPER_WORKFLOW.md` — Developer guide
5. `docs/INDEX.md` — Documentation spine references
6. `Makefile` — Help text and summary outputs
7. `tests/selftest_plan_test.py` — Test expectations (EXPECTED_TOTAL_STEPS, etc.)

**Current tier distribution:**

<!-- META:SELFTEST_COUNTS -->
**16 selftest steps** (1 KERNEL + 13 GOVERNANCE + 2 OPTIONAL)
<!-- /META:SELFTEST_COUNTS -->

- KERNEL: 1 step (fast kernel health)
- GOVERNANCE: 13 steps (config, flows, agents, BDD, policies, UI)
- OPTIONAL: 2 steps (coverage, extras)

This contract ensures documentation, tests, and configuration stay synchronized.

---

## Commands

### Run Full Selftest

```bash
make selftest
# Runs all 16 steps in strict mode
# Exit code: 0 if all pass, 1 if KERNEL or GOVERNANCE fails
```

Equivalent to:
```bash
uv run swarm/tools/selftest.py
```

### Run Fast Kernel Check

```bash
make kernel-smoke
# Runs the KERNEL step (core-checks: ruff + compile)
# ~300-400ms total, must always be green
```

Equivalent to:
```bash
uv run swarm/tools/selftest.py --kernel-only
```

### Run Degraded Mode

```bash
make selftest-degraded
# KERNEL failures block, GOVERNANCE/OPTIONAL warnings OK
# Use when some governance checks are in flux
```

Equivalent to:
```bash
uv run swarm/tools/selftest.py --degraded
```

### Run Selftest Doctor

```bash
make selftest-doctor
# Diagnoses whether failures are due to:
# - HARNESS_ISSUE: environment/toolchain broken
# - SERVICE_ISSUE: code/config is actually broken
# - HEALTHY: everything working
```

Equivalent to:
```bash
uv run swarm/tools/selftest_doctor.py
```

### View Selftest Plan

```bash
uv run swarm/tools/selftest.py --plan
# Shows all 16 steps, dependencies, tiers, without running
```

### List All Steps

```bash
uv run swarm/tools/selftest.py --list
# Display all available steps with metadata
```

### Run Single Step

```bash
uv run swarm/tools/selftest.py --step core-checks
# Run only the specified step (and dependencies)
```

### Run Steps Up To

```bash
uv run swarm/tools/selftest.py --until devex-contract
# Run steps in order up to and including the specified step
```

### Verbose Output with Timing

```bash
uv run swarm/tools/selftest.py --verbose
# Show detailed output, timing, and stderr for each step
```

### JSON Output

```bash
# Legacy format (backward compatible)
uv run swarm/tools/selftest.py --json

# V2 format with severity/category breakdown
uv run swarm/tools/selftest.py --json-v2
```

### Manage Overrides

```bash
# Create 24-hour override
make override-create STEP=bdd REASON="Under construction" APPROVER=alice

# List active overrides
make override-list

# Revoke override
make override-revoke STEP=bdd
```

---

## The 16 Selftest Steps

| # | Step ID | Tier | Severity | Category | Description | Dependencies |
|---|---------|------|----------|----------|-------------|---------------|
| 1 | core-checks | KERNEL | CRITICAL | CORRECTNESS | Python ruff + compile checks | (none) |
| 2 | skills-governance | GOVERNANCE | WARNING | GOVERNANCE | Skills linting & YAML validation | (none) |
| 3 | agents-governance | GOVERNANCE | WARNING | GOVERNANCE | Agent definitions validation | (none) |
| 4 | bdd | GOVERNANCE | WARNING | CORRECTNESS | BDD feature file structure | (none) |
| 5 | ac-status | GOVERNANCE | WARNING | GOVERNANCE | Acceptance criteria tracking | (none) |
| 6 | policy-tests | GOVERNANCE | WARNING | GOVERNANCE | OPA policy validation | (none) |
| 7 | devex-contract | GOVERNANCE | WARNING | GOVERNANCE | Flow/agent/skill contracts | core-checks |
| 8 | graph-invariants | GOVERNANCE | WARNING | GOVERNANCE | Flow graph connectivity | devex-contract |
| 9 | flowstudio-smoke | GOVERNANCE | WARNING | GOVERNANCE | Flow Studio in-process smoke | (none) |
| 10 | gemini-stepwise-tests | GOVERNANCE | WARNING | CORRECTNESS | Gemini stepwise backend tests | (none) |
| 11 | claude-stepwise-tests | GOVERNANCE | WARNING | CORRECTNESS | Claude stepwise backend tests | (none) |
| 12 | runs-gc-dry-check | GOVERNANCE | WARNING | GOVERNANCE | Runs GC health check | core-checks |
| 13 | ac-coverage | OPTIONAL | INFO | GOVERNANCE | Coverage thresholds | (none) |
| 14 | provider-env-check | GOVERNANCE | INFO | GOVERNANCE | Provider env validation | (none) |
| 15 | wisdom-smoke | GOVERNANCE | WARNING | GOVERNANCE | Wisdom tooling smoke test | (none) |
| 16 | extras | OPTIONAL | INFO | GOVERNANCE | Experimental checks | (none) |

### Step Descriptions

**1. core-checks** (KERNEL / CRITICAL / CORRECTNESS)
- Runs: `uv run ruff check`, `uv run python -m compileall`
- Purpose: Ensure Python code passes linting and compiles correctly
- Failure means: Code quality is compromised
- Time: ~1-5s

**2. skills-governance** (GOVERNANCE / WARNING / GOVERNANCE)
- Runs: `uv run swarm/tools/skills_lint.py`
- Purpose: Validate skill YAML syntax, required fields, and format
- Failure means: Skill definitions have structural issues
- Time: <100ms

**3. agents-governance** (GOVERNANCE / WARNING / GOVERNANCE)
- Runs: `uv run swarm/tools/validate_swarm.py --check-modified`
- Purpose: Validate agent definitions, flow references, skill references
- Failure means: Agent/skill/flow definitions are misaligned
- Time: <1s (incremental mode only checks modified files)

**4. bdd** (GOVERNANCE / WARNING / CORRECTNESS)
- Runs: `uv run swarm/tools/bdd_validator.py`
- Purpose: Validate BDD feature file structure and scenarios
- Failure means: Feature files have malformed syntax or missing scenarios
- Time: <500ms

**5. ac-status** (GOVERNANCE / WARNING / GOVERNANCE)
- Runs: Acceptance criteria coverage status check
- Purpose: Track coverage of acceptance criteria in current build
- Failure means: AC gaps detected in implementation
- Time: <100ms

**6. policy-tests** (GOVERNANCE / WARNING / GOVERNANCE)
- Runs: OPA/Conftest policy validation
- Purpose: Validate code against organization policies (security, compliance, etc.)
- Failure means: Code violates policy constraints
- Time: <500ms

**7. devex-contract** (GOVERNANCE / WARNING / GOVERNANCE)
- Runs: `uv run swarm/tools/validate_swarm.py`, `uv run swarm/tools/gen_flows.py --check`, `uv run swarm/tools/gen_adapters.py --platform claude --mode check-all`
- Purpose: Validate developer experience contracts (flows, commands, adapters)
- Failure means: Flow specs, adapter configs, or skill contracts are misaligned
- Depends on: core-checks (ensures code compiles before checking contracts)
- Time: <2s

**8. graph-invariants** (GOVERNANCE / WARNING / GOVERNANCE)
- Runs: `uv run swarm/tools/flow_graph.py --validate`
- Purpose: Check flow graph connectivity and governance invariants
- Failure means: Flow steps don't connect properly or violate structural invariants
- Depends on: devex-contract (assumes valid contracts)
- Time: <500ms

**9. flowstudio-smoke** (GOVERNANCE / WARNING / GOVERNANCE)
- Runs: `uv run python -m swarm.tools.flow_studio_smoke`
- Purpose: Verify Flow Studio selftest summary loads without HTTP (in-process)
- Failure means: Flow Studio app has import or data loading issues
- Time: ~5-10s

**10. gemini-stepwise-tests** (GOVERNANCE / WARNING / CORRECTNESS)
- Runs: `uv run pytest tests/test_gemini_stepwise_backend.py`
- Purpose: Unit tests for Gemini stepwise backend orchestration
- Failure means: Stepwise execution with Gemini is broken
- Time: ~30-60s

**11. claude-stepwise-tests** (GOVERNANCE / WARNING / CORRECTNESS)
- Runs: `uv run pytest tests/test_claude_stepwise_backend.py`
- Purpose: Unit tests for Claude stepwise backend orchestration
- Failure means: Stepwise execution with Claude is broken
- Time: ~30-60s

**12. runs-gc-dry-check** (GOVERNANCE / WARNING / GOVERNANCE)
- Runs: `uv run swarm/tools/runs_gc.py list`
- Purpose: Validate runs garbage collection tool is operational
- Failure means: Run lifecycle management is broken
- Depends on: core-checks
- Time: <60s
- **Why this matters**: Flow Studio performance degrades with too many runs; this step validates
  the GC tooling works so operators can maintain healthy run counts. See [runs-retention.md](runbooks/runs-retention.md).

**13. ac-coverage** (OPTIONAL / INFO / GOVERNANCE)
- Runs: Coverage threshold check
- Purpose: Verify acceptance criteria coverage meets target percentage
- Failure means: Coverage below threshold (non-blocking, informational)
- Time: <100ms

**14. provider-env-check** (GOVERNANCE / INFO / GOVERNANCE)
- Runs: `uv run swarm/tools/provider_env_check.py`
- Purpose: Validate provider environment variables for stepwise backends
- Failure means: Provider configuration may be incomplete
- Time: <30s

**15. wisdom-smoke** (GOVERNANCE / INFO / GOVERNANCE)
- Runs: `uv run swarm/tools/wisdom_summarizer.py stepwise-sdlc-claude --dry-run --output quiet`, `uv run swarm/tools/wisdom_aggregate_runs.py --dry-run --output quiet`
- Purpose: Validate wisdom summarizer and aggregator tools are operational
- Failure means: Wisdom tooling is broken (summarization/aggregation won't work)
- Time: <60s

**16. extras** (OPTIONAL / INFO / GOVERNANCE)
- Runs: Experimental and additional checks
- Purpose: Future placeholder for new governance checks
- Failure means: Experimental check failed (non-blocking)
- Time: <100ms

---

## Exit Codes

| Condition | Exit Code |
|-----------|-----------|
| All pass | 0 |
| KERNEL failure (any mode) | 1 |
| GOVERNANCE failure (strict mode) | 1 |
| GOVERNANCE failure (degraded mode) | 0 |
| OPTIONAL failure (any mode) | 0 |
| Config error / invalid arguments | 2 |

### Interpretation

- **Exit 0**: All executed steps passed (or failed non-blocking steps only)
- **Exit 1**: One or more blocking steps failed (KERNEL in any mode, or GOVERNANCE in strict mode)
- **Exit 2**: Invalid configuration or arguments (e.g., unknown step id, circular dependency)

---

## The Doctor Diagnostic

When selftest fails, run:

```bash
make selftest-doctor
# or
uv run swarm/tools/selftest_doctor.py
```

This checks:

**Harness** (environment):
- Python version (>= 3.8)
- Virtual environment active
- Rust toolchain available (`rustc --version`)
- Git repository status

**Service** (code):
- Python syntax in selftest.py
- Cargo compilation (`cargo check`)

**Output**:
```
Summary: HEALTHY | HARNESS_ISSUE | SERVICE_ISSUE

Harness status:
  Python env:     OK | ERROR | WARNING
  Rust toolchain: OK | ERROR | WARNING
  Git state:      OK | ERROR | WARNING

Service status:
  Python syntax:  OK | ERROR
  Cargo check:    OK | ERROR

Recommendations:
  1. Upgrade to Python 3.8+
  2. Install Rust: rustup install stable
  3. Fix compilation error in src/main.rs
```

**Next steps**:
- If HARNESS_ISSUE: Fix environment (`uv sync`, `rustup update`, etc.)
- If SERVICE_ISSUE: Run `uv run swarm/tools/selftest.py --plan` to see which steps fail, then investigate code
- If HEALTHY: Continue working; selftest is non-blocking

---

## Degraded Mode & Overrides

### When to Use Degraded Mode

```bash
make selftest-degraded
```

Use degraded mode when:
- A governance check is in flux (e.g., BDD scenarios being written)
- You want to keep working while addressing governance debt
- A particular step is explicitly overridden
- You need feedback loop speed during development

**Important**: KERNEL must still pass in degraded mode. If a KERNEL step fails, exit code is still 1 (blocking).

**Example usage**:
```bash
# During active development, allow governance issues to warn but not block
make selftest-degraded

# If output is:
# PASS core-checks
# WARN agents-governance (failed, but non-blocking in degraded mode)
# PASS bdd
# Exit code: 0 (can proceed with working on issues)

# When ready to merge, switch back to strict mode
make selftest
# Must all pass before merge
```

### Override Escape Hatch

For temporary, human-approved exceptions:

```bash
# Create a 24-hour override for the BDD step
make override-create STEP=bdd REASON="BDD under active development" APPROVER=alice HOURS=24

# Run selftest; BDD step is automatically skipped
make selftest
# Output: SKIP bdd (override active)

# List active overrides
make override-list
# Output:
# bdd       | active until 2025-12-01 15:30:00 | Alice | BDD under active development

# Revoke when done
make override-revoke STEP=bdd
```

**Important notes**:
- Overrides are audit-logged with who/when/why/expiration
- Overrides prevent a step from running (exit code 0 if skipped)
- Default expiration: 24 hours
- Use responsibly; overrides should be temporary workarounds, not permanent bypasses
- Document the reason for auditing and future reference

---

## Degradation Logging

When running in degraded mode, non-blocking failures (GOVERNANCE and OPTIONAL tiers) are logged to `selftest_degradations.log` for audit and analysis.

### Schema Version

**Current version: 1.1**

| Version | Changes |
|---------|---------|
| 1.0 | Initial schema (7 fields): timestamp, step_id, step_name, tier, message, severity, remediation |
| 1.1 | Added `status` (StepStatus enum) and `reason` (why step ended in that status) for unified vocabulary |

### Schema Fields (v1.1)

| Field | Type | Description |
|-------|------|-------------|
| timestamp | string | ISO 8601 UTC timestamp (e.g., `2025-12-01T10:15:22+00:00`) |
| step_id | string | Unique step identifier (e.g., `agents-governance`) |
| step_name | string | Human-readable step description |
| tier | string | `governance` or `optional` (NEVER `kernel`) |
| status | string | StepStatus: `PASS`, `FAIL`, `SKIP`, or `TIMEOUT` |
| reason | string | Why step ended in this status (e.g., `nonzero_exit`, `timeout`, `skipped_by_env`) |
| message | string | Failure output from step (stderr or stdout excerpt) |
| severity | string | `critical`, `warning`, or `info` |
| remediation | string | Suggested fix command (e.g., `uv run swarm/tools/selftest.py --step <step>`) |

### Design Invariants

1. **KERNEL tier is never logged**: KERNEL failures block immediately and are handled differently
2. **Only degraded mode writes logs**: Strict mode doesn't write degradation entries
3. **Only FAIL and TIMEOUT statuses are logged**: PASS and SKIP don't create degradation entries

### Example Entry

```json
{
  "timestamp": "2025-12-01T10:15:22+00:00",
  "step_id": "agents-governance",
  "step_name": "Agent definitions linting and formatting",
  "tier": "governance",
  "status": "FAIL",
  "reason": "nonzero_exit",
  "message": "Agent 'foo-bar' not found in registry",
  "severity": "warning",
  "remediation": "Run: uv run swarm/tools/selftest.py --step agents-governance for details"
}
```

### Reading Degradation Logs

```bash
# View all entries
cat selftest_degradations.log

# Parse as JSON Lines
jq -s '.' selftest_degradations.log

# Filter by step
jq -s '.[] | select(.step_id == "agents-governance")' selftest_degradations.log

# Count failures by tier
jq -s 'group_by(.tier) | map({tier: .[0].tier, count: length})' selftest_degradations.log
```

### Migration from v1.0 to v1.1

Existing v1.0 log files are valid but lack `status` and `reason` fields. To migrate:

```python
# Simple migration: add status="FAIL" and reason="nonzero_exit" to v1.0 entries
# (v1.0 only logged failures, so these are safe defaults)
import json

with open("selftest_degradations.log") as f:
    for line in f:
        entry = json.loads(line)
        if "status" not in entry:
            entry["status"] = "FAIL"
            entry["reason"] = "nonzero_exit"
        print(json.dumps(entry))
```

---

## JSON Report Structure

Selftest automatically writes a JSON report to:
```
swarm/runs/<run-id>/build/selftest_report.json
```

### Report Structure (V2 Format)

```json
{
  "version": "2.0",
  "metadata": {
    "run_id": "flow-3-abc123",
    "timestamp": "2025-11-30T15:30:00Z",
    "hostname": "macbook",
    "platform": "darwin",
    "git_branch": "main",
    "git_commit": "abc123def456",
    "user": "alice",
    "mode": "strict" | "degraded" | "kernel-only"
  },
  "summary": {
    "passed": 8,
    "failed": 1,
    "skipped": 1,
    "total": 10,
    "by_severity": {
      "critical": { "passed": 1, "failed": 0, "total": 1 },
      "warning": { "passed": 5, "failed": 1, "total": 6 },
      "info": { "passed": 2, "failed": 0, "total": 2 }
    },
    "by_category": {
      "security": { "passed": 0, "failed": 0, "total": 0 },
      "performance": { "passed": 0, "failed": 0, "total": 0 },
      "correctness": { "passed": 2, "failed": 0, "total": 2 },
      "governance": { "passed": 6, "failed": 1, "total": 7 }
    },
    "total_duration_ms": 15000
  },
  "results": [
    {
      "step_id": "core-checks",
      "description": "Rust cargo fmt, clippy, and unit tests",
      "tier": "kernel",
      "severity": "critical",
      "category": "correctness",
      "status": "PASS" | "FAIL" | "SKIP",
      "exit_code": 0,
      "duration_ms": 3500,
      "command": "cargo fmt --check && cargo clippy ... && cargo test ...",
      "timestamp_start": 1734000600.123,
      "timestamp_end": 1734000603.623,
      "stdout": "... (first 500 chars if failed) ...",
      "stderr": "... (first 500 chars if failed) ..."
    }
  ]
}
```

### Legacy Format (V1, Backward Compatible)

```json
{
  "mode": "strict" | "degraded" | "kernel-only",
  "passed": 8,
  "failed": 1,
  "skipped": 1,
  "total": 10,
  "total_time_ms": 15000,
  "results": [
    {
      "step_id": "core-checks",
      "description": "Rust cargo fmt, clippy, and unit tests",
      "tier": "kernel",
      "severity": "critical",
      "category": "correctness",
      "status": "PASS" | "FAIL" | "SKIP",
      "exit_code": 0,
      "duration_ms": 3500,
      "command": "cargo fmt --check && ..."
    }
  ]
}
```

### Reading Reports

```bash
# See summary
jq .summary swarm/runs/<run-id>/build/selftest_report.json

# See failed steps only
jq '.results[] | select(.status == "FAIL")' swarm/runs/<run-id>/build/selftest_report.json

# See severity breakdown
jq '.summary.by_severity' swarm/runs/<run-id>/build/selftest_report.json

# Count passed by category
jq '.summary.by_category[] | {category: .category, passed}' swarm/runs/<run-id>/build/selftest_report.json

# Get total time
jq '.summary.total_duration_ms / 1000 | "\(.)s"' swarm/runs/<run-id>/build/selftest_report.json
```

---

## Integration with Flows

### Flow 3 (Build)

Selftest is part of the build flow's verification:

1. **Step 0**: Repository setup
   - `repo-operator` ensures clean tree, creates feature branch
2. **Step 1-N**: Implementation microloops
   - Code ⇄ critic loops
   - Tests ⇄ critic loops
   - Mutator → fixer iteration
3. **Final Step**: **Run selftest**
   - Generates `selftest_report.json`
   - Exit code 0 = ready for Gate
   - Exit code 1 = debug and rerun
   - Timing: ~15-30s for full suite

**Example Flow 3 selftest integration**:
```bash
# Within the build flow orchestrator
echo "Running selftest..."
uv run swarm/tools/selftest.py --json-v2

# If exit 0: continue to Gate
if [ $? -eq 0 ]; then
  echo "Selftest passed; ready for Gate"
else
  echo "Selftest failed; see report for details"
  jq '.summary' swarm/runs/<run-id>/build/selftest_report.json
  exit 1
fi
```

### Flow 4 (Gate)

Gate reviews selftest report:
- **KERNEL failures**: Escalate, don't merge (code is broken)
- **GOVERNANCE failures**: Decide (merge with known issues, or bounce to Build)
- **OPTIONAL failures**: Informational only; doesn't affect merge decision

**Example Gate logic**:
```bash
# Read selftest report
critical_failed=$(jq '.summary.by_severity.critical.failed' selftest_report.json)
warning_failed=$(jq '.summary.by_severity.warning.failed' selftest_report.json)

if [ "$critical_failed" -gt 0 ]; then
  echo "FAIL: Critical selftest failures detected"
  exit 1  # Bounce to Build
fi

if [ "$warning_failed" -gt 0 ]; then
  echo "WARN: Governance selftest issues; approver decision required"
  # Create decision artifact documenting the governance waiver
fi
```

### Flow 5 (Deploy)

Deploy reads Gate's decision, respects selftest status:
- If Gate approved merge: deployment proceeds
- Selftest results are archived in deployment log for audit trail

### Flow 6 (Wisdom)

Wisdom analyzes selftest reports across runs:
- Detects patterns of repeated failures
- Suggests improvements to governance checks
- Feeds learnings back to Flow 2 for process refinement

---

## Troubleshooting

### Symptom: "Everything is broken" (selftest red across all steps)

**Step 1**: Run doctor
```bash
make selftest-doctor
```

**Step 2**: Interpret output
- If HARNESS_ISSUE: Your environment is broken
- If SERVICE_ISSUE: Your code is broken
- If HEALTHY: Something subtle is wrong; narrow it down

**Step 3**: If HARNESS_ISSUE, fix environment
```bash
# Python env issues
uv sync

# Rust toolchain issues
rustup update stable

# Git state issues
git status  # Check for uncommitted files, detached HEAD, etc.
```

**Step 4**: If SERVICE_ISSUE, narrow down
```bash
# See which steps are failing
uv run swarm/tools/selftest.py --plan

# Run steps individually
uv run swarm/tools/selftest.py --step core-checks

# If core-checks fails, check Rust code
cargo fmt --check
cargo clippy --workspace --all-targets --all-features
cargo test --workspace --tests
```

### Symptom: Governance checks failing in strict mode (but you're actively working)

**Option 1**: Fix the issue (recommended for production branches)
```bash
# Example: agents-governance failing
uv run swarm/tools/validate_swarm.py

# Fix issues, re-run
make selftest
```

**Option 2**: Use degraded mode (temporary, during development)
```bash
make selftest-degraded

# When ready to merge, switch back to strict
make selftest
```

**Option 3**: Override (human-approved, time-limited)
```bash
# Example: BDD scenarios under active development
make override-create STEP=bdd REASON="BDD under construction" APPROVER=alice

# When done
make override-revoke STEP=bdd
```

### Symptom: Selftest is slow

The full suite takes ~15-30s depending on code size. To speed up:

```bash
# Use kernel-smoke for fast feedback (300-400ms)
make kernel-smoke

# Use incremental agent validation
uv run swarm/tools/validate_swarm.py --check-modified

# Run single step
uv run swarm/tools/selftest.py --step core-checks
```

**Slow step breakdown** (approximate times):
- core-checks: 10-30s (cargo test dominates)
- skills-governance: <100ms
- agents-governance: <1s
- bdd: <500ms
- ac-status: <100ms
- policy-tests: <500ms
- devex-contract: <2s
- graph-invariants: <500ms
- ac-coverage: <100ms
- extras: <100ms

### Symptom: False positives / flaky checks

If a step is legitimately flaky or under development:

```bash
# Create temporary override (24 hours)
make override-create STEP=<step> REASON="Flaky check under investigation" APPROVER=<name>

# File a GitHub issue to track root cause fix
gh issue create --title "Fix flaky selftest: <step>" --body "..."

# When fixed, revoke override
make override-revoke STEP=<step>
```

### Symptom: A governance check is wrong / shouldn't fail

Example: The BDD validator is requiring scenarios that don't apply to this feature.

```bash
# Document the issue
gh issue create --title "BDD validator false positive" --body "..."

# Temporarily override while fix is developed
make override-create STEP=bdd REASON="BDD validator false positive; see issue #123" APPROVER=<name> HOURS=72

# Fix the validator code or requirements
# When fixed, revoke override
make override-revoke STEP=bdd
```

---

## Philosophy

The selftest system embodies:

1. **Layered governance**: Not all failures are equal. KERNEL > GOVERNANCE > OPTIONAL.
   - KERNEL is the safety net: code must compile, format, and pass unit tests
   - GOVERNANCE keeps the ship in order: agent definitions, flow contracts, policy compliance
   - OPTIONAL is forward-looking: coverage targets, experimental checks

2. **Degradable operation**: You can work while fixing non-critical issues.
   - Strict mode enforces everything (for merge-readiness)
   - Degraded mode allows governance issues to warn (for active development)
   - Kernel-smoke provides fast feedback (for tight iteration loops)

3. **Diagnosable failures**: Doctor tool separates environment from code issues.
   - HARNESS_ISSUE: Fix your local toolchain
   - SERVICE_ISSUE: Fix your code
   - HEALTHY: Something subtle; investigate further

4. **Auditable exemptions**: Overrides logged with who/when/why/expiration.
   - Transparent temporary exceptions
   - Built-in expiration prevents "permanent" workarounds
   - Audit trail for compliance and debugging

5. **Fast iteration**: Kernel-smoke for quick feedback, full selftest for gating.
   - ~300-400ms for fast loop (kernel-smoke)
   - ~15-30s for confident gate decision (full selftest)
   - Developer chooses based on context

The goal: **Catch real problems without false alarms. Enable flow while maintaining integrity.**

---

## Flow Studio Governance Gate

The `flowstudio-smoke` selftest step provides an **in-process governance gate** for Flow Studio. Unlike traditional HTTP-based smoke tests, this step evaluates selftest health directly without starting a server.

### How It Works

1. **In-process evaluation**: Uses `get_selftest_summary()` to build the selftest summary object
2. **Self-skip logic**: The step skips itself during summary generation to avoid recursion
3. **Fast path**: Completes in ~0.5–2s (vs. 5–10s for HTTP-based approaches)
4. **Unified model**: Reads the same summary that `/platform/status` serves

### When Flow Studio Smoke Fails

If `flowstudio-smoke` fails, it means Flow Studio would report an unhealthy governance state:

```bash
# View the specific failure
uv run swarm/tools/selftest.py --step flowstudio-smoke --verbose

# Check what selftest sees
uv run swarm/tools/selftest.py --json-v2 | jq '.summary'

# Compare with /platform/status (if Flow Studio is running)
curl -s http://localhost:5000/platform/status | jq '.governance.selftest'
```

### Relationship to `/platform/status`

The Flow Studio smoke step and `/platform/status` endpoint share the same underlying model:

- **Both** call `SelfTestRunner.build_summary()` to get kernel/governance health
- **Both** read the same step registry from `selftest_config.py`
- **Both** produce the same GREEN/YELLOW/RED status semantics

This ensures Flow Studio's governance view is always coherent with what selftest reports. See `swarm/tools/STATUS_ENDPOINT.md` for the full endpoint specification.

### Skipping in Fast Mode

For inner-loop development, you can skip the Flow Studio smoke step:

```bash
# Via environment variable
SELFTEST_SKIP_STEPS=flowstudio-smoke uv run swarm/tools/selftest.py

# Via dev-check-fast target
make dev-check-fast
```

Use full `make dev-check` before merging to ensure governance coherence.

---

## See Also

- `/CLAUDE.md` — Overall system philosophy and agent taxonomy
- `/swarm/positioning.md` — Design philosophy and axioms
- `/swarm/flows/` — Flow specifications (signal, plan, build, gate, deploy, wisdom)
- `/swarm/tools/selftest.py` — Main selftest orchestrator (implementation)
- `/swarm/tools/selftest_config.py` — Step definitions and configuration
- `/swarm/tools/selftest_doctor.py` — Diagnostic tool
- `/swarm/tools/override_manager.py` — Override management (audit logging, expiration)
- `/swarm/tools/STATUS_ENDPOINT.md` — Platform status endpoint specification
- `/swarm/tools/flow_studio_smoke.py` — In-process Flow Studio smoke check
