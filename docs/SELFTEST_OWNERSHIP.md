# Selftest System Ownership and Maintainer Guide

This document is your handover guide for maintaining the selftest system. It covers the implementation map, common maintenance tasks, decision logs, and escalation paths.

**Target audience**: New maintainers, tech leads, and future contributors who need to understand how to evolve the selftest system.

---

## The Map: What Exists and What's Next

### Phase 1: Foundational Infrastructure (COMPLETE)

**Status**: Shipped and production-ready

**Components**:
- Documentation suite (SYSTEM.md, GOVERNANCE.md, API_CONTRACT.md, AC_MATRIX.md, OPERATOR_CHECKLIST.md, OWNERSHIP.md)
- 11 selftest steps across 3 tiers (KERNEL, GOVERNANCE, OPTIONAL)
- API endpoints (`/api/selftest/plan`, `/platform/status`)
- Degradation logging system (JSONL format, schema v1.0)
- CLI tools (`selftest.py`, `kernel_smoke.py`, `selftest_doctor.py`, `selftest_degradations.py`)
- BDD test coverage (6 acceptance criteria, 20+ scenarios)
- Comprehensive test suite (3 test files, 40+ tests)
- Flow Studio integration (Selftest tab, status modal)

**Artifacts**:
```
swarm/
  tools/
    selftest.py               # Main orchestrator
    selftest_config.py        # Step registry
    selftest_doctor.py        # Diagnostic tool
    kernel_smoke.py           # Fast kernel check
    selftest_degradations.py  # Log reader/pretty-printer
docs/
  SELFTEST_SYSTEM.md          # Architecture reference
  SELFTEST_GOVERNANCE.md      # Quick reference for operators
  SELFTEST_API_CONTRACT.md    # Stable API contract (versioned)
  SELFTEST_AC_MATRIX.md       # AC → step → test traceability
  SELFTEST_OPERATOR_CHECKLIST.md # Day-to-day operator guide
  SELFTEST_OWNERSHIP.md       # This document
features/
  selftest.feature            # BDD scenarios
tests/
  test_selftest_acceptance.py # AC validation tests
  test_selftest_degradation_log.py # Degradation log tests
  test_selftest_api_contract.py # API contract tests
  test_selftest_bdd.py        # BDD executable spine
.github/
  workflows/
    swarm-validate.yml        # CI gate (kernel + governance)
selftest_degradations.log     # Persistent degradation log (JSONL)
```

**Key Decisions Made**:
- Layered tiers (KERNEL → GOVERNANCE → OPTIONAL) prevent "everything is broken" syndrome
- JSONL log format (not JSON) for append-only, streaming-friendly storage
- Schema version 1.0 frozen for stability (no breaking changes without approval)
- API contract versioned with semver (breaking changes require major bump)
- Degraded mode allows graceful workflow around governance failures

---

### Phase 2: Operational Hardening (NEXT)

**Status**: Design complete, implementation deferred to next milestone

**Goals**:
- Enforce selftest in CI as a mandatory merge gate
- Add pre-commit hooks for local validation
- Integrate selftest metrics into observability platforms
- Add remediation automation (auto-fix for mechanical issues)

**Components to Build**:

1. **CI Gate Enforcement**:
   - Extend `.github/workflows/swarm-validate.yml` to block merges on KERNEL failures
   - Add status check requirements in branch protection rules
   - Document escalation paths for urgent hotfixes

2. **Pre-commit Integration**:
   - Create `.pre-commit-config.yaml` with kernel-smoke as a fast pre-commit hook
   - Document opt-in setup process (do not auto-install; require explicit `pre-commit install`)
   - Ensure < 0.5s baseline for tight iteration loops

3. **Metrics and Dashboards**:
   - Export selftest results to Prometheus/Grafana
   - Track MTTR (mean time to repair) for selftest failures
   - Alert on persistent degradations (> 24 hours)

4. **Auto-Remediation**:
   - Extend `heal-selftest` skill to apply mechanical fixes automatically
   - Scope: auto-format code, regenerate configs, fix simple Gherkin errors
   - Humans review and approve all auto-fixes (no silent commits)

**Deferred Decisions**:
- Should GOVERNANCE failures block merge in CI? (Defer to org policy)
- What's the SLA for fixing persistent degradations? (Defer to team agreement)
- Which metrics should trigger alerts? (Defer to observability team)

---

### Phase 3: Advanced Features (FUTURE)

**Status**: Aspirational; not yet scheduled

**Ideas**:
- Distributed selftest execution (parallelize steps for speed)
- Historical trend analysis (detect regressions across releases)
- AC-driven test generation (auto-create BDD scenarios from spec_ledger.yaml)
- Integration with external policy engines (OPA, Conftest, Kyverno)
- Custom step plugins (allow teams to define their own governance checks)

**When to Revisit**:
- When baseline selftest exceeds 5 seconds (speed bottleneck)
- When governance checks become team-specific (need plugin system)
- When historical analysis is needed for postmortems

---

## First Week as Maintainer

### Day 1: Understand the System

**Read these documents in order**:
1. `docs/SELFTEST_SYSTEM.md` — Architecture and philosophy
2. `docs/SELFTEST_GOVERNANCE.md` — Operator quick reference
3. `docs/SELFTEST_AC_MATRIX.md` — AC traceability matrix
4. `docs/SELFTEST_OPERATOR_CHECKLIST.md` — Day-to-day troubleshooting

**Run these commands**:
```bash
# See the full plan
make selftest --plan

# Run kernel smoke check (< 0.5s)
make kernel-smoke

# Run full selftest (strict mode)
make selftest

# Diagnose system health
make selftest-doctor

# View degradation log
cat selftest_degradations.log | python -m json.tool
```

**Explore the code**:
- `swarm/tools/selftest_config.py` — Step definitions (16 steps, tiers, dependencies)
- `swarm/tools/selftest.py` — Main orchestrator (CLI, JSON output, --degraded mode)
- `tests/test_selftest_acceptance.py` — AC validation tests (comprehensive)

### Day 2-3: Understand the Tests

**Run the test suite**:
```bash
# AC validation tests
uv run pytest tests/test_selftest_acceptance.py -v

# Degradation log tests
uv run pytest tests/test_selftest_degradation_log.py -v

# API contract tests
uv run pytest tests/test_selftest_api_contract.py -v

# BDD executable spine
uv run pytest tests/test_selftest_bdd.py -v -m executable
```

**Study the BDD scenarios**:
- `features/selftest.feature` — 6 ACs, 20+ scenarios
- Note which scenarios are `@executable` vs design-only
- Understand how ACs map to steps (via `ac_ids` field in config)

### Day 4-5: Review CI Integration

**Check the CI workflow**:
- `.github/workflows/swarm-validate.yml` — Runs `make dev-check` (kernel + governance)
- Understand exit codes: 0 (pass), 1 (KERNEL or GOVERNANCE fail), 2 (config error)

**Test CI behavior locally**:
```bash
# Simulate CI run
make dev-check

# If failure, diagnose
make selftest-doctor

# View CI logs (if GitHub Actions)
gh run list --workflow=swarm-validate.yml
gh run view <run-id>
```

### Day 6-7: Understand Extension Points

**Review config-driven architecture**:
- All 16 steps are defined in `swarm/tools/selftest_config.py` as `SelfTestStep` objects
- To add a new step: add to `SELFTEST_STEPS` list, update `SELFTEST_AC_MATRIX.md`, write tests

**Explore degradation logging**:
- Schema: `timestamp`, `step_id`, `step_name`, `tier`, `message`, `severity`, `remediation`
- Format: JSONL (one JSON object per line, append-only)
- Read with: `uv run swarm/tools/selftest_degradations.py --format pretty`

**Check API endpoints**:
```bash
# Start Flow Studio (if running)
make flow-studio

# Test endpoints
curl http://localhost:5000/api/selftest/plan | jq .
curl http://localhost:5000/platform/status | jq .governance
```

---

## Common Maintenance Tasks

### Task: Add a New Selftest Step

**When**: A new governance check needs to be enforced (e.g., "validate flow graph cycles")

**Steps**:

1. **Design the step** (decide tier, severity, category):
   - KERNEL = must always pass
   - GOVERNANCE = should pass, can warn in degraded mode
   - OPTIONAL = nice-to-have, never blocks

2. **Add to `swarm/tools/selftest_config.py`**:
   ```python
   SelfTestStep(
       id="my-new-check",
       name="My New Check",
       description="Validates something important",
       tier=SelfTestTier.GOVERNANCE,
       severity=SelfTestSeverity.WARNING,
       category=SelfTestCategory.GOVERNANCE,
       command=["uv run swarm/tools/my_check.py"],
       ac_ids=["AC-SELFTEST-MY-CHECK"],
       dependencies=[],  # or ["core-checks"] if dependent
   )
   ```

3. **Write the check implementation**:
   - Create `swarm/tools/my_check.py`
   - Exit code 0 = pass, 1 = fail
   - Print actionable error messages to stderr

4. **Add to AC matrix** (`docs/SELFTEST_AC_MATRIX.md`):
   ```markdown
   ### AC-SELFTEST-MY-CHECK
   **Status**: ✅ Fully Implemented
   | Field | Value |
   |-------|-------|
   | **Implemented In Steps** | `my-new-check` |
   | **Tier** | GOVERNANCE |
   | **Test Files** | `tests/test_my_check.py` |
   ```

5. **Write tests**:
   - Add `tests/test_my_check.py` with comprehensive tests
   - Add BDD scenario to `features/selftest.feature` with `@AC-SELFTEST-MY-CHECK` tag
   - Run: `uv run pytest tests/test_my_check.py -v`

6. **Update API contract** (if breaking change):
   - If changing step schema, bump `version` in `/api/selftest/plan`
   - Update `docs/SELFTEST_API_CONTRACT.md` with changelog entry
   - Run contract tests: `uv run pytest tests/test_selftest_api_contract.py -v`

7. **Validate everything**:
   ```bash
   make selftest --plan           # See new step in plan
   make selftest --step my-new-check --verbose  # Test in isolation
   make selftest                  # Full suite
   ```

8. **Document**:
   - Add remediation hints to `docs/SELFTEST_GOVERNANCE.md`
   - Update `docs/SELFTEST_OPERATOR_CHECKLIST.md` with troubleshooting tips

---

### Task: Add a New Acceptance Criterion (AC)

**When**: A new requirement needs traceability (e.g., "selftest must support parallel execution")

**Steps**:

1. **Register the AC** in `swarm/AGENTS.md` (or wherever ACs are tracked):
   ```markdown
   - AC-SELFTEST-PARALLEL: Selftest supports parallel step execution
   ```

2. **Add to spec ledger** (if using `specs/spec_ledger.yaml`):
   ```yaml
   acceptance_criteria:
     - id: AC-SELFTEST-PARALLEL
       description: "Selftest supports parallel step execution"
       tests:
         - type: integration
           command: "uv run pytest tests/test_parallel_execution.py"
       status: pending
   ```

3. **Write BDD scenario** in `features/selftest.feature`:
   ```gherkin
   @AC-SELFTEST-PARALLEL @executable
   Scenario: Selftest runs steps in parallel when no dependencies
     When I run `uv run swarm/tools/selftest.py --parallel`
     Then independent steps should execute concurrently
     And total time should be < 50% of serial execution
   ```

4. **Implement the feature**:
   - Update `swarm/tools/selftest.py` to support `--parallel` flag
   - Add logic to detect independent steps (no shared dependencies)
   - Use `concurrent.futures` or `asyncio` for parallel execution

5. **Write tests**:
   - Add `tests/test_parallel_execution.py`
   - Verify steps run in parallel, correct order, and isolation

6. **Update AC matrix** (`docs/SELFTEST_AC_MATRIX.md`):
   ```markdown
   ### AC-SELFTEST-PARALLEL
   **Status**: ✅ Fully Implemented
   | Field | Value |
   |-------|-------|
   | **Implemented In Steps** | All steps (via --parallel flag) |
   | **Test Files** | `tests/test_parallel_execution.py` |
   | **Surfaces In** | CLI `--parallel`, `/api/selftest/plan` (parallel_safe field) |
   ```

7. **Update step config** (link AC to relevant steps):
   ```python
   ac_ids=["AC-SELFTEST-KERNEL-FAST", "AC-SELFTEST-PARALLEL"]
   ```

---

### Task: Bump Degradation Log Schema Version

**When**: You need to add a new field to the degradation log (e.g., `"fix_command": "make gen-adapters"`)

**Approval Required**: This is a **breaking change**. Requires tech lead approval.

**Steps**:

1. **Document the change**:
   - Create a GitHub issue: "Bump DEGRADATION_LOG_SCHEMA to v1.1: add fix_command field"
   - Explain why the new field is needed (e.g., "operators need actionable commands")

2. **Get approval**:
   - Tag tech lead or team lead in the issue
   - Wait for explicit approval comment (e.g., "Approved. Proceed with v1.1 bump.")

3. **Update schema version** in `swarm/tools/selftest.py`:
   ```python
   DEGRADATION_LOG_SCHEMA = "1.1"  # was 1.0
   ```

4. **Add the new field** to log entries:
   ```python
   entry = {
       "timestamp": now_iso,
       "step_id": step_id,
       "step_name": step_name,
       "tier": tier,
       "message": message,
       "severity": severity,
       "remediation": remediation,
       "fix_command": fix_command,  # NEW in v1.1
   }
   ```

5. **Update tests** (`tests/test_selftest_degradation_log.py`):
   - Add test for new field presence
   - Ensure backward compatibility (v1.0 logs still parse)

6. **Update documentation**:
   - `docs/SELFTEST_SYSTEM.md` — Document schema version change
   - `docs/SELFTEST_GOVERNANCE.md` — Show example with `fix_command`
   - `docs/SELFTEST_API_CONTRACT.md` — Add changelog entry

7. **Migrate existing logs** (if needed):
   ```bash
   # Backup
   cp selftest_degradations.log selftest_degradations.log.bak

   # Add missing field (example: add "fix_command": "N/A" to all v1.0 entries)
   # Use jq or Python script to rewrite log
   ```

8. **Announce in changelog**:
   ```markdown
   ## v1.1.0 (2025-12-15)
   - **BREAKING**: Degradation log schema bumped to v1.1
   - Added `fix_command` field for actionable remediation commands
   - Backward compatible: v1.0 logs still readable
   ```

---

### Task: Change an AC from GOVERNANCE to KERNEL Tier

**When**: A check becomes critical (e.g., "agents-governance should always pass, not just warn")

**Approval Required**: This changes execution semantics. Requires team consensus.

**Steps**:

1. **Document the rationale**:
   - Create issue: "Promote agents-governance to KERNEL tier"
   - Explain why (e.g., "agent misconfigurations cause production incidents")

2. **Get approval** (team vote or tech lead decision):
   - Discuss in team meeting or async in issue
   - Require explicit +1 from at least 2 senior engineers

3. **Update tier** in `swarm/tools/selftest_config.py`:
   ```python
   SelfTestStep(
       id="agents-governance",
       tier=SelfTestTier.KERNEL,  # was GOVERNANCE
       severity=SelfTestSeverity.CRITICAL,  # was WARNING
       # ... rest unchanged
   )
   ```

4. **Update AC matrix** (`docs/SELFTEST_AC_MATRIX.md`):
   - Move AC from GOVERNANCE section to KERNEL section
   - Update status table to reflect new tier

5. **Update tests**:
   - Verify that failures now block in all modes (including `--degraded`)
   - Run: `uv run pytest tests/test_selftest_acceptance.py -k agents_governance`

6. **Update documentation**:
   - `docs/SELFTEST_GOVERNANCE.md` — Move step to KERNEL section
   - `docs/SELFTEST_SYSTEM.md` — Update tier table
   - `docs/SELFTEST_OPERATOR_CHECKLIST.md` — Update escalation path

7. **Communicate the change**:
   - Announce in team chat: "agents-governance is now KERNEL tier; failures block all merges"
   - Update CI docs to clarify new blocking behavior

8. **Run full selftest**:
   ```bash
   make selftest
   # Verify agents-governance failures now exit 1 in all modes
   ```

---

### Task: Selftest is Failing in CI (Emergency Response)

**When**: CI is red, blocking merges. You need to triage and fix quickly.

**Steps**:

1. **Run selftest doctor locally**:
   ```bash
   make selftest-doctor
   ```
   - Output: HEALTHY, HARNESS_ISSUE, or SERVICE_ISSUE

2. **If HARNESS_ISSUE**:
   - Environment broken (Python missing, Rust toolchain broken, etc.)
   - Fix: Update CI runner, restore dependencies
   - Escalate to DevOps if CI infra issue

3. **If SERVICE_ISSUE**:
   - Code/config is actually broken
   - Run: `make selftest --step <failing-step> --verbose`
   - Fix the issue in code (e.g., fix linting errors, regenerate configs)
   - Commit the fix: `git commit -m "fix: resolve selftest <step> failure"`

4. **If KERNEL failure**:
   - P0 CRITICAL: stop all work, fix immediately
   - No workaround available (KERNEL can't be degraded)
   - Examples: code doesn't compile, unit tests fail

5. **If GOVERNANCE failure**:
   - P1 SHOULD FIX if fix is < 10 minutes
   - P2 DEFER if fix is large (use `--degraded` mode temporarily)
   - Document degraded state in PR description

6. **If urgent hotfix needed**:
   - Create hotfix branch
   - Apply minimal fix to restore green CI
   - Merge with expedited review
   - Create follow-up issue for root cause fix

7. **Post-incident**:
   - Document what broke, why, and how it was fixed
   - Update `docs/SELFTEST_OPERATOR_CHECKLIST.md` with new troubleshooting hints
   - Consider adding a new test to prevent recurrence

---

## Quick Diagnostics

When selftest fails, use these tools to diagnose the issue quickly:

### Tool 1: Selftest Doctor

**Command**: `make selftest-doctor`

**What it does**: Separates HARNESS_ISSUE (environment broken) from SERVICE_ISSUE (code/config broken).

**Example output**:

```
Status: SERVICE_ISSUE
Diagnosis: Step 'agents-governance' failed (exit code 1)
Recommendation: Run `make selftest --step agents-governance --verbose` for details
```

**When to use**: First step when selftest fails locally or in CI.

---

### Tool 2: Selftest Incident Pack

**Command**: `make selftest-incident-pack`

**What it does**: Gathers all diagnostic info into a tarball for escalation to maintainers.

**Output**: Creates `selftest_incident_<timestamp>.tar.gz` with:
- Full selftest output (verbose mode)
- Degradation log (`selftest_degradations.log`)
- Doctor output
- Environment info (Python/uv versions, git status, recent commits)

**When to use**: When escalating a persistent failure to maintainer (attach to GitHub issue).

---

### Tool 3: Selftest Suggest Remediation

**Command**: `make selftest-suggest-remediation`

**What it does**: Analyzes degradation log and suggests fixes based on historical patterns.

**Example output**:

```
Analyzing degradation log...

Found 2 degradations:

1. Step: agents-governance
   Issue: Color mismatch in deploy-decider.yaml
   Suggested fix: Update `color: blue` to `color: purple` (role_family=design)
   Documentation: See CLAUDE.md § Agent Taxonomy

2. Step: bdd
   Issue: Missing @AC tag in scenario
   Suggested fix: Add `@AC-SELFTEST-MY-FEATURE` tag to scenario line 42
   Documentation: See features/selftest.feature for examples
```

**When to use**: When stuck on a failure and need quick remediation hints.

**Important**: This tool is **read-only** (no code changes). You must apply fixes manually.

---

## Decision Log

### Decision 1: Use JSONL (not JSON) for Degradation Log

**Date**: 2025-11-28

**Context**: Degradation log needs append-only writes, streaming-friendly reads, and human readability.

**Options Considered**:
1. Single JSON file (array of objects)
2. JSONL (one JSON object per line)
3. SQLite database
4. CSV format

**Decision**: Use JSONL (option 2)

**Rationale**:
- Append-only: No need to read entire file to add entry (just append line)
- Streaming-friendly: Can `tail -f` for live monitoring
- Simple parsing: `for line in file: json.loads(line)`
- Human-readable: Each line is valid JSON (easy to inspect)
- No external dependencies: Works with stdlib only

**Trade-offs**:
- Not sortable without reading entire file (acceptable: log is chronological by design)
- No relational queries (acceptable: log is simple enough)

**Status**: Implemented and stable. Schema version 1.0 frozen.

---

### Decision 2: KERNEL vs GOVERNANCE Tier Semantics

**Date**: 2025-11-20

**Context**: Need to distinguish "repo is broken" from "governance is out of compliance"

**Decision**: Three-tier system:
- KERNEL: Must always pass (code compiles, tests pass)
- GOVERNANCE: Should pass, can warn in degraded mode (agent configs, flow specs)
- OPTIONAL: Nice-to-have, never blocks (coverage thresholds, experimental checks)

**Rationale**:
- KERNEL failures = immediate escalation (no one can merge)
- GOVERNANCE failures = controlled degradation (team can decide)
- OPTIONAL failures = informational only (no noise)

**Status**: Implemented. ~10 GOVERNANCE steps, 1 KERNEL step, 2 OPTIONAL steps.

---

### Decision 3: API Contract Versioning with Semver

**Date**: 2025-11-25

**Context**: Flow Studio and CI pipelines depend on `/api/selftest/plan`. Need stability guarantees.

**Decision**: Use semver versioning (`version` field in JSON). Breaking changes require major bump.

**Breaking Changes**:
- Adding/removing fields
- Changing field types
- Changing enum values
- Changing response structure

**Non-Breaking Changes**:
- Adding steps to the array
- Changing step descriptions
- Changing dependencies

**Process**:
1. Propose change in GitHub issue
2. Update `version` field in `swarm/tools/selftest.py`
3. Update `docs/SELFTEST_API_CONTRACT.md`
4. Run contract tests (`pytest tests/test_selftest_api_contract.py`)
5. Merge with explicit version bump commit message

**Status**: Current version is 1.0. No breaking changes allowed without approval.

---

### Decision 4: No Auto-Install for Pre-commit Hooks

**Date**: 2025-11-29

**Context**: Should pre-commit hooks be installed automatically on clone?

**Decision**: No. Require explicit opt-in via `pre-commit install`.

**Rationale**:
- Respects developer autonomy (some devs prefer manual validation)
- Avoids surprise behavior (hooks can slow down commits)
- Aligns with swarm philosophy: scaffolding provided, enforcement is conscious choice

**Trade-off**:
- Developers may forget to install hooks (mitigated by CI enforcement)

**Status**: Documented in CONTRIBUTING.md. Hooks available in `.pre-commit-config.yaml` but not auto-installed.

---

### Decision 5: Degraded Mode Exit Code is 0

**Date**: 2025-11-22

**Context**: Should `--degraded` mode exit 0 or 1 when GOVERNANCE fails?

**Decision**: Exit 0 (success) when GOVERNANCE fails in degraded mode, exit 1 only for KERNEL failures.

**Rationale**:
- Degraded mode is a conscious workaround; exit 0 signals "this is expected"
- Exit 1 reserved for true failures (KERNEL broken)
- Humans can inspect degradation log to see what's degraded

**Trade-off**:
- CI may not flag degraded state as red (mitigated by degradation log parsing in CI)

**Status**: Implemented. Degradation log provides audit trail.

---

### Decision 6: AC-6 Closure Implemented

**Date**: 2025-12-01

**Context**: AC-6 (selftest degradation tracking) required persistent logging, CLI tool, and API endpoint.

**Implementation**:
- Added `selftest_degradations.log` (JSONL format, schema v1.0)
- Created `swarm/tools/show_selftest_degradations.py` CLI tool
- Added `/api/selftest/degradations` endpoint in Flow Studio
- Comprehensive test coverage (12+ tests in `test_selftest_degradation_log.py`)
- BDD scenarios validated (`@AC-SELFTEST-DEGRADATION-TRACKED`)

**Committed in**: feat/selftest-resilience-slice-1 branch (commits 9038263, 2bf5fdb, 9893a8b)

**Status**: Shipped and production-ready.

---

### Decision 7: Phase 1.5 Operational Hardening

**Date**: 2025-12-01

**Context**: After Phase 1 (foundational infrastructure) completion, Phase 1.5 focuses on developer UX and org-level policy.

**Scope**:
- Branch protection setup guide (`docs/BRANCH_PROTECTION_SETUP.md`)
- Developer workflow documentation (`docs/SELFTEST_DEVELOPER_WORKFLOW.md`)
- PR template with selftest checklist (`.github/pull_request_template.md`)
- Five new Make targets for common workflows:
  - `make selftest-fast` — KERNEL only (~400ms)
  - `make selftest-govern` — GOVERNANCE only (~30s)
  - `make selftest-incident-pack` — Gather diagnostics
  - `make selftest-suggest-remediation` — AI-assisted remediation hints
- Incident tooling (`selftest_incident_pack.py`, `selftest_suggest_remediation.py`)

**Goal**: Make selftest accessible to all developers, reduce escalations, improve MTTR.

**Status**: Implemented in Phase 1.5 (this commit).

---

## Contact and Escalation

### Maintainer Roles

**Primary Maintainer**: Swarm Team (update this section when assigned)
- Responsibilities: Review PRs, approve schema bumps, manage releases
- Contact: @swarm-team (GitHub), swarm-team@example.com
- On-call rotation: See [PagerDuty schedule](https://example.pagerduty.com/schedules/swarm)

**Backup Maintainer**: Platform Team (update when assigned)
- Responsibilities: Cover primary during vacations, handle escalations
- Contact: @platform-team (GitHub), platform@example.com

**Tech Lead / Approval Authority**: Engineering Lead (update when assigned)
- Responsibilities: Approve breaking changes, tier promotions, schema bumps
- Contact: @tech-lead (GitHub), techlead@example.com

**On-Call & Incident Escalation**:
- **Primary channel**: `#swarm-selftest` (Slack)
- **Incident channel**: `#swarm-incidents` (Slack)
- **Page escalation**: PagerDuty service "Swarm Selftest" (P0 only)
- **Email**: swarm-selftest-oncall@example.com

**Escalation Timeline**:
- **P0 (KERNEL broken)**: Page immediately, respond within 15 minutes
- **P1 (GOVERNANCE blocked)**: Post in #swarm-selftest, respond within 2 hours
- **P2 (degraded state)**: Create issue, triage within 1 business day
- **P3 (OPTIONAL failures)**: Create issue, triage at next sprint planning

---

### Escalation Paths

**Level 1: Routine Maintenance** (no escalation needed)
- Adding a new OPTIONAL step
- Fixing a bug in an existing step
- Updating documentation
- Adding tests

**Level 2: Moderate Change** (maintainer approval required)
- Adding a new GOVERNANCE step
- Changing a step's tier (e.g., OPTIONAL → GOVERNANCE)
- Adding a new AC with traceability
- Changing API contract (non-breaking)

**Level 3: Breaking Change** (tech lead approval required)
- Promoting a step to KERNEL tier
- Bumping degradation log schema version
- Changing API contract (breaking change)
- Removing a step entirely

**Level 4: Critical Incident** (immediate escalation)
- KERNEL failures blocking all merges
- Selftest system completely broken (can't run)
- Production incident related to selftest

---

### Where to File Issues

**GitHub Issues**: `https://github.com/<org>/<repo>/issues`
- Use label: `selftest` for all selftest-related issues
- Use label: `P0` for critical failures (KERNEL broken)
- Use label: `P1` for urgent governance issues
- Use label: `P2` for deferred improvements

**Slack Channel**: `#swarm-selftest` (if exists)
- For quick questions, troubleshooting help
- For announcing maintenance windows

**Email**: selftest-maintainers@example.com (if exists)
- For urgent escalations outside business hours

---

## Quick Reference: Key Files and Their Purpose

| File | Purpose | When to Edit |
|------|---------|--------------|
| `swarm/tools/selftest.py` | Main orchestrator | Adding CLI flags, changing execution logic |
| `swarm/tools/selftest_config.py` | Step registry | Adding/removing/modifying steps |
| `swarm/tools/selftest_doctor.py` | Diagnostic tool | Improving diagnostics |
| `swarm/tools/kernel_smoke.py` | Fast kernel check | Changing KERNEL checks |
| `docs/SELFTEST_SYSTEM.md` | Architecture reference | Documenting design changes |
| `docs/SELFTEST_GOVERNANCE.md` | Operator quick reference | Adding remediation hints |
| `docs/SELFTEST_API_CONTRACT.md` | API contract | Changing API response schema |
| `docs/SELFTEST_AC_MATRIX.md` | AC traceability | Adding/removing ACs |
| `docs/SELFTEST_OPERATOR_CHECKLIST.md` | Day-to-day troubleshooting | Adding common errors/fixes |
| `features/selftest.feature` | BDD scenarios | Adding new ACs or scenarios |
| `tests/test_selftest_acceptance.py` | AC validation tests | Validating new ACs |
| `tests/test_selftest_degradation_log.py` | Degradation log tests | Changing log format |
| `tests/test_selftest_api_contract.py` | API contract tests | Enforcing API guarantees |
| `.github/workflows/swarm-validate.yml` | CI gate | Changing CI behavior |

---

## Onboarding Checklist for New Maintainers

Use this checklist to verify your understanding:

- [ ] I have read all 6 selftest docs (SYSTEM, GOVERNANCE, API_CONTRACT, AC_MATRIX, OPERATOR_CHECKLIST, OWNERSHIP)
- [ ] I can run `make selftest` and interpret the output
- [ ] I can run `make selftest-doctor` and understand the diagnosis
- [ ] I can read the degradation log: `cat selftest_degradations.log | python -m json.tool`
- [ ] I know which tier each step belongs to (KERNEL, GOVERNANCE, OPTIONAL)
- [ ] I understand exit codes: 0 (pass), 1 (KERNEL or GOVERNANCE fail in strict), 2 (config error)
- [ ] I can add a new selftest step and write tests for it
- [ ] I can bump the degradation log schema version (with approval)
- [ ] I know how to escalate a KERNEL failure (P0 critical)
- [ ] I have access to the GitHub repo, CI logs, and team communication channels

---

## Maintenance Philosophy

The selftest system embodies these principles:

1. **Diagnosability over Speed**: A slow test that tells you exactly what's wrong is better than a fast test that fails mysteriously.

2. **Graceful Degradation over Hard Blocks**: GOVERNANCE failures allow `--degraded` workarounds. KERNEL failures block immediately.

3. **Audit Trail over Silent Fixes**: Degradation log records every non-blocking failure. No silent ignoring.

4. **Stability over Features**: API contract is versioned and stable. Breaking changes require explicit approval.

5. **Documentation over Tribal Knowledge**: All decisions, processes, and troubleshooting steps are documented.

When in doubt, ask: "Does this change make selftest more diagnosable, more transparent, and more stable?" If yes, proceed. If no, reconsider.

---

## Related Documents

- **`docs/SELFTEST_SYSTEM.md`** — Architecture and design philosophy
- **`docs/SELFTEST_GOVERNANCE.md`** — Quick reference for operators
- **`docs/SELFTEST_API_CONTRACT.md`** — Stable API contract (versioned)
- **`docs/SELFTEST_AC_MATRIX.md`** — AC → step → test traceability
- **`docs/SELFTEST_OPERATOR_CHECKLIST.md`** — Day-to-day troubleshooting guide
- **`observability/alerts/README.md`** — Alert runbooks and incident response
- **`swarm/CLAUDE.md`** — Overall swarm guidance for agents
- **`CONTRIBUTING.md`** — Contribution guidelines (pre-commit, validation)

---

## Changelog

### v1.0.0 (2025-12-01)
- Initial ownership documentation
- Phase 1 (Foundational Infrastructure) complete
- Phase 2 (Operational Hardening) designed, deferred to next milestone
- Phase 3 (Advanced Features) aspirational
