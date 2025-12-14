# API Coherence Contract

This document defines the runtime API coherence contract between:
- `/api/selftest/plan` (GET) - Returns selftest execution plan with AC IDs
- `/platform/status` (GET) - Returns governance status with per-AC status

## Contract Definition

### 1. AC ID Bijection

**Invariant:** All AC IDs declared in `/api/selftest/plan` must appear in `/platform/status` governance.ac

```
plan_ac_ids ⊆ status_ac_ids
```

**Rationale:** UI and CLI tools must be able to look up status for every AC mentioned in the plan.

**Test:** `test_plan_acs_match_status_acs`

### 2. AC ID Format

**Invariant:** All AC IDs follow format `AC-SELFTEST-*` (uppercase, hyphen-delimited)

**Examples:**
- `AC-SELFTEST-KERNEL-FAST`
- `AC-SELFTEST-INTROSPECTABLE`
- `AC-SELFTEST-DEGRADATION-TRACKED`

**Test:** `test_plan_endpoint_returns_all_acs`

### 3. AC Status Values

**Invariant:** All AC status values in `/platform/status` governance.ac must be one of:

```
{PASS, FAIL, CRITICAL, WARNING, INFO}
```

**Precedence:** `CRITICAL > FAILURE > WARNING > INFO > PASS`

**Semantics:**
- `CRITICAL`: AC failed at KERNEL tier (blocks all merges)
- `WARNING`: AC failed at GOVERNANCE tier (can be degraded)
- `INFO`: AC failed at OPTIONAL tier (informational)
- `FAIL`: Generic failure (legacy)
- `PASS`: All steps implementing this AC passed

**Test:** `test_status_ac_values_are_valid_statuses`

### 4. Step Tier Semantics

**Invariant:** Step tiers in `/api/selftest/plan` must match these semantics:

| Tier | Enum Value | Blocks Merge | In Degraded Mode |
|------|-----------|--------------|------------------|
| KERNEL | `"kernel"` | Always | Always fails |
| GOVERNANCE | `"governance"` | In strict mode | Warns only |
| OPTIONAL | `"optional"` | Never | Informational |

**Test:** `test_plan_steps_have_correct_tiers`

### 5. Dependency Graph Validity

**Invariant:** All step dependencies in `steps[*].depends_on` must:
- Reference valid step IDs in the same plan
- Not create self-dependencies (step → step)
- Form a valid DAG (no cycles)

**Test:** `test_plan_depends_on_relationships_valid`

### 6. Response Stability

**Invariant:** Both endpoints must return deterministic, stable responses:
- Calling `/api/selftest/plan` twice returns identical JSON (same order)
- AC IDs are in consistent order
- Summary counts are consistent

**Test:** `test_api_response_is_stable_across_runs`

## Data Structures

### /api/selftest/plan Response

```json
{
  "version": "1.0",
  "steps": [
    {
      "id": "core-checks",
      "tier": "kernel",
      "severity": "critical",
      "category": "correctness",
      "description": "Python tooling checks (ruff linting + compile validation)",
      "ac_ids": ["AC-SELFTEST-KERNEL-FAST", "AC-SELFTEST-FAILURE-HINTS"],
      "depends_on": []
    }
  ],
  "summary": {
    "total": 11,
    "by_tier": {
      "kernel": 1,
      "governance": 8,
      "optional": 2
    }
  }
}
```

### /platform/status Response (governance section)

```json
{
  "timestamp": "2025-12-01T11:37:20+00:00",
  "service": "demo-swarm",
  "governance": {
    "kernel": { "ok": true, "status": "HEALTHY" },
    "selftest": { "mode": "strict", "status": "GREEN" },
    "validation": { "status": "PASS" },
    "state": "HEALTHY",
    "degradations": [],
    "ac": {
      "AC-SELFTEST-KERNEL-FAST": "PASS",
      "AC-SELFTEST-INTROSPECTABLE": "PASS",
      "AC-SELFTEST-DEGRADED": "PASS",
      "AC-SELFTEST-FAILURE-HINTS": "PASS",
      "AC-SELFTEST-DEGRADATION-TRACKED": "PASS",
      "AC-SELFTEST-INDIVIDUAL-STEPS": "PASS"
    }
  },
  "flows": {},
  "agents": {},
  "hints": {}
}
```

## Cross-Cutting ACs

Some ACs apply to multiple steps (cross-cutting concerns):

| AC ID | Steps | Rationale |
|-------|-------|-----------|
| `AC-SELFTEST-FAILURE-HINTS` | All steps | Every step provides hints on failure |
| `AC-SELFTEST-DEGRADATION-TRACKED` | All GOVERNANCE/OPTIONAL steps | All non-kernel failures tracked in degradations.log |
| `AC-SELFTEST-INTROSPECTABLE` | 8 GOVERNANCE steps | All governance steps contribute to introspection |

**Test:** `test_cross_cutting_acs_appear_on_multiple_steps`

## AC Count Validation

The test suite validates that the number of unique AC IDs in the plan matches
the number documented in `docs/SELFTEST_AC_MATRIX.md`.

**Current Count:** 6 AC IDs

**Source of Truth:** `docs/SELFTEST_AC_MATRIX.md` (grep for `### AC-SELFTEST-*`)

**Test:** `test_plan_endpoint_returns_all_acs`

## Error Handling

Both endpoints support graceful degradation:

### 503 Service Unavailable

**Plan Endpoint:** Returns 503 if selftest module cannot be imported

```json
{
  "error": "Selftest module not available"
}
```

**Status Endpoint:** Returns 503 if status provider unavailable

```json
{
  "error": "Status provider not available",
  "timestamp": null,
  "service": "demo-swarm"
}
```

**Test Behavior:** Tests skip with `pytest.skip()` on 503 (not a failure)

## Implementation References

- **Plan Endpoint:** `swarm/tools/flow_studio_fastapi.py::api_selftest_plan()`
- **Status Endpoint:** `swarm/tools/flow_studio_fastapi.py::platform_status()`
- **Plan Logic:** `swarm/tools/selftest.py::get_selftest_plan_json()`
- **Status Logic:** `swarm/tools/status_provider.py::StatusProvider._aggregate_ac_status()`
- **Config:** `swarm/tools/selftest_config.py::SELFTEST_STEPS`

## Test Suite

**File:** `tests/test_selftest_api_contract_coherence.py`

**Test Classes:**
1. `TestSelfTestAPIContractCoherence` - Main coherence tests (7 tests)
2. `TestCoherenceEdgeCases` - Edge cases and error handling (3 tests)

**Run Tests:**

```bash
# Run full suite
uv run pytest tests/test_selftest_api_contract_coherence.py -v

# Run specific test
uv run pytest tests/test_selftest_api_contract_coherence.py::TestSelfTestAPIContractCoherence::test_plan_acs_match_status_acs -v

# Run with output
uv run pytest tests/test_selftest_api_contract_coherence.py -v -s
```

## Example Usage

### Python

```python
from fastapi.testclient import TestClient
from swarm.tools.flow_studio_fastapi import app

client = TestClient(app)

# Fetch plan
plan_resp = client.get("/api/selftest/plan")
plan = plan_resp.json()

# Collect all AC IDs
ac_ids = set()
for step in plan["steps"]:
    ac_ids.update(step["ac_ids"])

# Fetch status
status_resp = client.get("/platform/status")
status = status_resp.json()

# Check AC statuses
for ac_id in ac_ids:
    ac_status = status["governance"]["ac"][ac_id]
    print(f"{ac_id}: {ac_status}")
```

### JavaScript (Flow Studio UI)

```javascript
// Fetch plan
const planResp = await fetch("/api/selftest/plan");
const plan = await planResp.json();

// Fetch status
const statusResp = await fetch("/platform/status");
const status = await statusResp.json();

// Build AC status map
const acStatus = status.governance.ac;

// Render UI with color coding
plan.steps.forEach(step => {
  step.ac_ids.forEach(acId => {
    const status = acStatus[acId];
    const color = statusColors[status]; // PASS → green, CRITICAL → red, etc.
    renderAcBadge(acId, status, color);
  });
});
```

## Maintenance

When adding new acceptance criteria:

1. Add to `docs/SELFTEST_AC_MATRIX.md`
2. Add to `swarm/tools/selftest_config.py` (SelfTestStep.ac_ids)
3. Run `uv run pytest tests/test_selftest_api_contract_coherence.py -v`
4. Verify coherence tests pass
5. Update this document if new AC patterns emerge

## Breaking Changes

Changes to the contract that require coordination:

- **Adding AC status values:** Update `valid_statuses` in `test_status_ac_values_are_valid_statuses`
- **Changing tier enum values:** Update `valid_tiers` in `test_plan_steps_have_correct_tiers`
- **Changing AC ID format:** Update regex in `test_plan_endpoint_returns_all_acs`

Always run the full test suite before merging changes to:
- `swarm/tools/flow_studio_fastapi.py`
- `swarm/tools/selftest.py`
- `swarm/tools/status_provider.py`
- `swarm/tools/selftest_config.py`
