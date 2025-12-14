# Selftest Acceptance Criteria Matrix

This document maps every `@AC-SELFTEST-*` acceptance criterion tag to:
- The selftest step(s) that implement it
- The tests that verify it
- Where it surfaces in the API and UI
- Implementation status and notes

Use this as the **source of truth** for understanding which acceptance criteria are implemented, how they're enforced, and where they're observable.

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅     | Fully implemented and tested |
| ⚠️     | Partially implemented or in progress |
| ❌     | Not yet implemented (aspirational) |

---

## Acceptance Criteria Matrix

### AC-SELFTEST-KERNEL-FAST

**Status**: ✅ Fully Implemented

| Field | Value |
|-------|-------|
| **Description** | Kernel smoke check exists and is fast (sub-second baseline) |
| **Implemented In Steps** | `core-checks` |
| **Tier** | KERNEL |
| **Test Files** | `tests/test_selftest_acceptance.py::test_kernel_smoke_check_*` |
| **Gherkin Scenarios** | `features/selftest.feature:26-33, 35-40` |
| **Surfaces In** | `/api/selftest/plan`, `/platform/status.kernel.status`, Flow Studio **Selftest** tab |
| **Notes** | Kernel smoke check must pass in < 0.5s; blocks all merges if failed |

---

### AC-SELFTEST-INTROSPECTABLE

**Status**: ✅ Fully Implemented

| Field | Value |
|-------|-------|
| **Description** | Selftest is introspectable: `--plan` lists all steps with tiers and dependencies |
| **Implemented In Steps** | `skills-governance`, `agents-governance`, `bdd`, `ac-status`, `policy-tests`, `devex-contract`, `graph-invariants`, `flowstudio-smoke` |
| **Tier** | GOVERNANCE |
| **Test Files** | `tests/test_selftest_acceptance.py::test_selftest_plan_*` <br> `tests/test_selftest_bdd.py::test_selftest_plan_output` |
| **Gherkin Scenarios** | `features/selftest.feature:42-67` |
| **Surfaces In** | `/api/selftest/plan` (JSON with `steps`, `summary`, `by_tier`), Flow Studio **Selftest** modal |
| **Notes** | `--plan` must complete in < 0.2s; JSON schema is versioned and contract-tested |

---

### AC-SELFTEST-INDIVIDUAL-STEPS

**Status**: ✅ Fully Implemented

| Field | Value |
|-------|-------|
| **Description** | Can run individual selftest steps (`--step <id>`, `--until <id>`) |
| **Implemented In Steps** | `ac-coverage`, `extras` |
| **Tier** | OPTIONAL |
| **Test Files** | `tests/test_selftest_acceptance.py::test_run_individual_step_*` <br> `tests/test_selftest_bdd.py::test_individual_step_isolation` |
| **Gherkin Scenarios** | `features/selftest.feature:69-99` |
| **Surfaces In** | CLI `--step`, `--until`, Flow Studio **Selftest** modal (individual step drill-down) |
| **Notes** | Step execution is isolated; output shows timing, step_id, status, and error details |

---

### AC-SELFTEST-DEGRADED

**Status**: ✅ Fully Implemented

| Field | Value |
|-------|-------|
| **Description** | Degraded mode allows workflow around governance failures while blocking kernel failures |
| **Implemented In Steps** | `core-checks` (always blocks), `skills-governance` through `flowstudio-smoke` (blocked in degraded mode only if KERNEL fails) |
| **Tier** | GOVERNANCE |
| **Test Files** | `tests/test_selftest_acceptance.py::test_degraded_mode_*` <br> `tests/test_selftest_degradation_log.py` |
| **Gherkin Scenarios** | `features/selftest.feature:101-123` |
| **Surfaces In** | `/api/selftest/plan`, `/platform/status.state`, `selftest_degradations.log`, Flow Studio **Status** tab |
| **Notes** | KERNEL failures always block; GOVERNANCE failures create warnings in degraded mode; exit code reflects true status |

---

### AC-SELFTEST-FAILURE-HINTS

**Status**: ✅ Fully Implemented

| Field | Value |
|-------|-------|
| **Description** | Selftest provides actionable hints on failure (commands, docs, context) |
| **Implemented In Steps** | All steps (via `--help`, failure output, `/platform/status`) |
| **Tier** | GOVERNANCE |
| **Test Files** | `tests/test_selftest_acceptance.py::test_failure_hints_*` |
| **Gherkin Scenarios** | `features/selftest.feature:125-142` |
| **Surfaces In** | Selftest stderr/stdout, `/platform/status.governance.hints`, Flow Studio **Selftest** modal (remediation commands) |
| **Notes** | Each failure includes `Try: uv run swarm/tools/selftest.py --step <id>` and links to relevant docs |

---

### AC-SELFTEST-DEGRADATION-TRACKED

**Status**: ✅ Fully Implemented

| Field | Value |
|-------|-------|
| **Description** | Governance and optional failures are logged to persistent JSONL file in degraded mode |
| **Implemented In Steps** | All GOVERNANCE and OPTIONAL steps (when `--degraded` flag is used) |
| **Tier** | GOVERNANCE |
| **Test Files** | `tests/test_selftest_degradation_log.py::test_log_*` <br> `tests/test_selftest_api_contract.py` (status endpoint coherence) |
| **Gherkin Scenarios** | `features/selftest.feature:144-183` |
| **Surfaces In** | `selftest_degradations.log` (JSONL), `/platform/status.governance.degradations`, CLI `swarm/tools/selftest_degradations.py` |
| **Notes** | JSONL schema v1.0 frozen: `timestamp`, `step_id`, `step_name`, `tier`, `message`, `severity`, `remediation` |

---

### AC-SELFTEST-STEPWISE-GEMINI

**Status**: ✅ Fully Implemented

| Field | Value |
|-------|-------|
| **Description** | Gemini stepwise backend orchestration is tested and functional |
| **Implemented In Steps** | `gemini-stepwise-tests` |
| **Tier** | GOVERNANCE |
| **Test Files** | `tests/test_gemini_stepwise_backend.py` |
| **Gherkin Scenarios** | N/A (unit tests only) |
| **Surfaces In** | `/api/selftest/plan`, Flow Studio **Selftest** tab |
| **Notes** | Verifies GeminiStepwiseBackend registration, capabilities, run creation, and transcript/receipt generation |

---

### AC-SELFTEST-STEPWISE-CLAUDE

**Status**: ✅ Fully Implemented

| Field | Value |
|-------|-------|
| **Description** | Claude stepwise backend orchestration is tested and functional |
| **Implemented In Steps** | `claude-stepwise-tests` |
| **Tier** | GOVERNANCE |
| **Test Files** | `tests/test_claude_stepwise_backend.py` |
| **Gherkin Scenarios** | N/A (unit tests only) |
| **Surfaces In** | `/api/selftest/plan`, Flow Studio **Selftest** tab |
| **Notes** | Verifies ClaudeStepwiseBackend registration, capabilities, run creation, and transcript/receipt generation |

---

### AC-SELFTEST-PROVIDER-ENV

**Status**: ✅ Fully Implemented

| Field | Value |
|-------|-------|
| **Description** | Provider environment validation reports engine configuration status |
| **Implemented In Steps** | `provider-env-check` |
| **Tier** | GOVERNANCE |
| **Test Files** | N/A (informational step, always passes) |
| **Gherkin Scenarios** | N/A |
| **Surfaces In** | `/api/selftest/plan`, Flow Studio **Selftest** tab |
| **Notes** | Reports table of engine/provider/mode/env-vars status. Always passes (INFO severity). Helps users understand their stepwise backend configuration. |

---

### AC-SELFTEST-RUNS-GC-HEALTH

**Status**: ✅ Fully Implemented

| Field | Value |
|-------|-------|
| **Description** | Runs garbage collection and retention policy tooling is functional |
| **Implemented In Steps** | `runs-gc-health` |
| **Tier** | GOVERNANCE |
| **Test Files** | `tests/test_runs_gc.py` |
| **Gherkin Scenarios** | N/A |
| **Surfaces In** | `/api/selftest/plan`, Flow Studio **Selftest** tab |
| **Notes** | Validates `runs_gc.py` can list runs and `runs_retention_config.py` loads correctly. Allows fail in degraded mode. |

---

### AC-SELFTEST-WISDOM-SMOKE

**Status**: ✅ Fully Implemented

| Field | Value |
|-------|-------|
| **Description** | Wisdom summarization and aggregation tooling is functional |
| **Implemented In Steps** | `wisdom-smoke` |
| **Tier** | GOVERNANCE |
| **Test Files** | `tests/test_wisdom_tools.py` |
| **Gherkin Scenarios** | N/A |
| **Surfaces In** | `/api/selftest/plan`, Flow Studio **Selftest** tab |
| **Notes** | Validates `wisdom_summarizer.py` and `wisdom_aggregate_runs.py` run without errors in dry-run mode. Uses `stepwise-sdlc-claude` golden example. Allows fail in degraded mode. |

---

## Acceptance Criteria by Tier

### KERNEL Tier (Blocking)

Must pass before any merge:

| AC ID | Step | Test | Status |
|-------|------|------|--------|
| AC-SELFTEST-KERNEL-FAST | `core-checks` | `test_selftest_acceptance.py` | ✅ |

### GOVERNANCE Tier (Controlled Failure)

Enforced in strict mode; can warn in degraded mode:

| AC ID | Primary Steps | Test Files | Status |
|-------|---------------|-----------|--------|
| AC-SELFTEST-INTROSPECTABLE | `skills-governance`, `agents-governance`, `bdd`, `ac-status`, `policy-tests`, `devex-contract`, `graph-invariants`, `flowstudio-smoke` | `test_selftest_acceptance.py`, `test_selftest_api_contract.py` | ✅ |
| AC-SELFTEST-DEGRADED | All GOVERNANCE/OPTIONAL steps + `--degraded` flag | `test_selftest_acceptance.py`, `test_selftest_degradation_log.py` | ✅ |
| AC-SELFTEST-FAILURE-HINTS | All steps (hints in stderr/stdout) | `test_selftest_acceptance.py` | ✅ |
| AC-SELFTEST-DEGRADATION-TRACKED | All steps (degradation logging) | `test_selftest_degradation_log.py`, `test_selftest_api_contract.py` | ✅ |
| AC-SELFTEST-STEPWISE-GEMINI | `gemini-stepwise-tests` | `test_gemini_stepwise_backend.py` | ✅ |
| AC-SELFTEST-STEPWISE-CLAUDE | `claude-stepwise-tests` | `test_claude_stepwise_backend.py` | ✅ |
| AC-SELFTEST-PROVIDER-ENV | `provider-env-check` | N/A (informational) | ✅ |
| AC-SELFTEST-RUNS-GC-HEALTH | `runs-gc-health` | `test_runs_gc.py` | ✅ |
| AC-SELFTEST-WISDOM-SMOKE | `wisdom-smoke` | `test_wisdom_tools.py` | ✅ |

### OPTIONAL Tier (Informational)

Nice-to-have; failures do not block work:

| AC ID | Primary Steps | Test Files | Status |
|-------|---------------|-----------|--------|
| AC-SELFTEST-INDIVIDUAL-STEPS | `ac-coverage`, `extras` | `test_selftest_acceptance.py` | ✅ |

---

## Test Coverage Map

### Unit Tests

**Location**: `tests/test_selftest_acceptance.py`

| Test Function | AC ID(s) | Verifies |
|---------------|----------|----------|
| `test_kernel_smoke_check_is_fast` | AC-SELFTEST-KERNEL-FAST | Kernel smoke < 0.5s |
| `test_kernel_smoke_check_reports_status` | AC-SELFTEST-KERNEL-FAST | Exit codes: 0 (HEALTHY), 1 (BROKEN) |
| `test_selftest_plan_returns_valid_json` | AC-SELFTEST-INTROSPECTABLE | `/api/selftest/plan` schema |
| `test_selftest_plan_step_counts` | AC-SELFTEST-INTROSPECTABLE | Summary matches step count |
| `test_run_individual_step_core_checks` | AC-SELFTEST-INDIVIDUAL-STEPS | `--step core-checks` isolation |
| `test_run_until_step` | AC-SELFTEST-INDIVIDUAL-STEPS | `--until skills-governance` execution |
| `test_degraded_mode_allows_governance_failures` | AC-SELFTEST-DEGRADED | Exit code 0 when KERNEL OK, GOVERNANCE fail |
| `test_degraded_mode_blocks_kernel_failures` | AC-SELFTEST-DEGRADED | Exit code 1 when KERNEL fail |
| `test_failure_hints_in_output` | AC-SELFTEST-FAILURE-HINTS | Hints present in stderr/stdout |

**Location**: `tests/test_selftest_degradation_log.py`

| Test Function | AC ID(s) | Verifies |
|---------------|----------|----------|
| `test_log_created_on_governance_failure_in_degraded_mode` | AC-SELFTEST-DEGRADATION-TRACKED | `selftest_degradations.log` created with valid entries |
| `test_degradation_log_entries_are_jsonl_valid` | AC-SELFTEST-DEGRADATION-TRACKED | Each line is valid JSON |
| `test_degradation_log_schema_has_required_fields` | AC-SELFTEST-DEGRADATION-TRACKED | Required fields: `timestamp`, `step_id`, `tier`, `message`, `severity`, `remediation` |
| `test_log_persists_across_runs` | AC-SELFTEST-DEGRADATION-TRACKED | Entries append, chronologically sorted |
| `test_pretty_printer_formats_degradations` | AC-SELFTEST-DEGRADATION-TRACKED | CLI tool renders human-readable output |

**Location**: `tests/test_selftest_api_contract.py`

| Test Function | AC ID(s) | Verifies |
|---------------|----------|----------|
| `test_selftest_plan_api_contract_structure` | AC-SELFTEST-INTROSPECTABLE | Response schema (version, steps, summary) |
| `test_selftest_plan_api_contract_step_fields` | AC-SELFTEST-INTROSPECTABLE | Each step has: `id`, `tier`, `ac_ids`, `depends_on` |
| `test_selftest_plan_api_contract_tier_values` | AC-SELFTEST-INTROSPECTABLE | Tiers are valid enums |
| `test_selftest_plan_api_contract_summary_counts` | AC-SELFTEST-INTROSPECTABLE | Summary totals match step counts |
| `test_selftest_plan_api_contract_no_duplicates` | AC-SELFTEST-INTROSPECTABLE | No duplicate step IDs |
| `test_selftest_plan_api_contract_dependencies_valid` | AC-SELFTEST-INTROSPECTABLE | All dependencies reference valid step IDs |

### BDD Scenarios

**Location**: `features/selftest.feature`

| Scenario Tag | AC ID(s) | Gherkin Lines |
|--------------|----------|---------------|
| @AC-SELFTEST-KERNEL-FAST @executable | AC-SELFTEST-KERNEL-FAST | 26-33, 35-40 |
| @AC-SELFTEST-INTROSPECTABLE @executable | AC-SELFTEST-INTROSPECTABLE | 42-60 |
| @AC-SELFTEST-INDIVIDUAL-STEPS @executable | AC-SELFTEST-INDIVIDUAL-STEPS | 69-99 |
| @AC-SELFTEST-DEGRADED @executable | AC-SELFTEST-DEGRADED | 101-123 |
| @AC-SELFTEST-FAILURE-HINTS | AC-SELFTEST-FAILURE-HINTS | 125-142 |
| @AC-SELFTEST-DEGRADATION-TRACKED | AC-SELFTEST-DEGRADATION-TRACKED | 144-183 |

---

## API Surface Mapping

### GET /api/selftest/plan

**Response fields traced to AC IDs**:

```json
{
  "version": "1.0",            // AC-SELFTEST-INTROSPECTABLE
  "steps": [                   // AC-SELFTEST-INTROSPECTABLE, AC-SELFTEST-INDIVIDUAL-STEPS
    {
      "id": "core-checks",     // AC-SELFTEST-INTROSPECTABLE
      "tier": "kernel",        // AC-SELFTEST-INTROSPECTABLE
      "ac_ids": ["AC-SELFTEST-KERNEL-FAST"],  // This document's source of truth
      "depends_on": [],        // AC-SELFTEST-INTROSPECTABLE
      "description": "...",    // AC-SELFTEST-FAILURE-HINTS
      "severity": "critical"   // AC-SELFTEST-DEGRADATION-TRACKED
    }
  ],
  "summary": {                 // AC-SELFTEST-INTROSPECTABLE
    "total": 11,
    "by_tier": { "kernel": 1, "governance": 8, "optional": 2 }
  }
}
```

### GET /platform/status

**Response fields traced to AC IDs**:

```json
{
  "state": "HEALTHY" | "DEGRADED" | "BROKEN",        // AC-SELFTEST-KERNEL-FAST, AC-SELFTEST-DEGRADED
  "kernel": {
    "status": "PASS" | "FAIL",                        // AC-SELFTEST-KERNEL-FAST
    "last_run": "2025-12-01T10:15:22Z"
  },
  "governance": {
    "status": "PASS" | "FAIL" | "WARN",              // AC-SELFTEST-INTROSPECTABLE, AC-SELFTEST-DEGRADED
    "ac": { "AC-SELFTEST-INTROSPECTABLE": "PASS", ... },  // AC IDs from this matrix
    "hints": ["Try: uv run swarm/tools/selftest.py --step agents-governance"],  // AC-SELFTEST-FAILURE-HINTS
    "degradations": [                                 // AC-SELFTEST-DEGRADATION-TRACKED
      {
        "timestamp": "2025-12-01T10:15:22Z",
        "step_id": "agents-governance",
        "message": "...",
        "remediation": "..."
      }
    ]
  },
  "selftest": {
    "plan": { /* /api/selftest/plan response */ }    // AC-SELFTEST-INTROSPECTABLE
  }
}
```

---

## Flow Studio UI Surfaces

### Selftest Tab (in Flow Studio operator view)

| UI Element | AC ID(s) | Notes |
|-----------|----------|-------|
| **Status banner** (HEALTHY / BROKEN / DEGRADED) | AC-SELFTEST-KERNEL-FAST, AC-SELFTEST-DEGRADED | Color-coded; reflects kernel + governance status |
| **Step list with tier colors** | AC-SELFTEST-INTROSPECTABLE | KERNEL (red), GOVERNANCE (yellow), OPTIONAL (blue) |
| **"View Full Plan" button** | AC-SELFTEST-INTROSPECTABLE | Opens modal with all steps |
| **Step drill-down (modal)** | AC-SELFTEST-INDIVIDUAL-STEPS | Click a step; see status, timing, AC IDs, remediation |
| **Failure hints** | AC-SELFTEST-FAILURE-HINTS | "Try: uv run swarm/tools/selftest.py --step X" |
| **Degradations section** | AC-SELFTEST-DEGRADATION-TRACKED | List of logged governance failures from log file |

---

## Verification Checklist

Use this to verify all ACs are implemented before release:

- [ ] All 11 AC IDs appear in matrix above
- [ ] Each AC maps to at least 1 selftest step
- [ ] Each AC has at least 1 test file (unit or BDD)
- [ ] Each AC has at least 1 UI/API surface
- [ ] Contract tests pass: `pytest tests/test_selftest_api_contract.py -v`
- [ ] Degradation log tests pass: `pytest tests/test_selftest_degradation_log.py -v`
- [ ] BDD scenarios pass: `pytest tests/test_selftest_bdd.py -v`
- [ ] Flow Studio Selftest tab renders without errors
- [ ] `/api/selftest/plan` returns 200 with valid schema
- [ ] `/platform/status` includes all AC statuses

---

## References

- **Gherkin Scenarios**: `features/selftest.feature`
- **Selftest Config**: `swarm/tools/selftest_config.py` (SelfTestStep.ac_ids)
- **API Contract**: `docs/SELFTEST_API_CONTRACT.md`
- **System Design**: `docs/SELFTEST_SYSTEM.md`
- **Degradation Log Schema**: `tests/test_selftest_degradation_log.py`
