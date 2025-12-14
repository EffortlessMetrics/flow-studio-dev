# Selftest API Contract

This document defines the stable, versioned contract for the selftest API endpoints. Breaking changes require semver version bump and are subject to code review.

## Overview

The selftest API provides two core endpoints:

1. **`GET /api/selftest/plan`** — Retrieve the complete selftest execution plan with all steps, tiers, and dependencies
2. **`GET /platform/status`** — Retrieve current governance status (includes selftest results and status)

Both endpoints are consumed by:
- Flow Studio UI (real-time step tracking)
- CI/CD pipelines (merge gates, status checks)
- Dashboards (governance health monitoring)

**Stability Level**: Stable. The contract below is enforced by comprehensive automated tests.

---

## Endpoint 1: GET /api/selftest/plan

### Request

```
GET /api/selftest/plan
```

No parameters. Returns the complete plan regardless of current execution state.

### Response (200 OK)

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
      "depends_on": [],
      "ac_ids": ["AC-SELFTEST-KERNEL-FAST"]
    },
    {
      "id": "skills-governance",
      "tier": "governance",
      "severity": "warning",
      "category": "governance",
      "description": "Skills linting and formatting",
      "depends_on": [],
      "ac_ids": ["AC-SELFTEST-INTROSPECTABLE"]
    },
    {
      "id": "agents-governance",
      "tier": "governance",
      "severity": "warning",
      "category": "governance",
      "description": "Agent definitions linting and formatting",
      "depends_on": [],
      "ac_ids": ["AC-SELFTEST-INTROSPECTABLE"]
    },
    {
      "id": "bdd",
      "tier": "governance",
      "severity": "warning",
      "category": "correctness",
      "description": "BDD scenarios (cucumber features)",
      "depends_on": [],
      "ac_ids": ["AC-SELFTEST-INTROSPECTABLE"]
    },
    {
      "id": "ac-status",
      "tier": "governance",
      "severity": "warning",
      "category": "governance",
      "description": "Validate acceptance criteria coverage",
      "depends_on": [],
      "ac_ids": ["AC-SELFTEST-INTROSPECTABLE"]
    },
    {
      "id": "policy-tests",
      "tier": "governance",
      "severity": "warning",
      "category": "governance",
      "description": "OPA/Conftest policy validation",
      "depends_on": [],
      "ac_ids": ["AC-SELFTEST-INTROSPECTABLE"]
    },
    {
      "id": "devex-contract",
      "tier": "governance",
      "severity": "warning",
      "category": "governance",
      "description": "Developer experience contract (flows, commands, skills)",
      "depends_on": ["core-checks"],
      "ac_ids": ["AC-SELFTEST-INTROSPECTABLE"]
    },
    {
      "id": "graph-invariants",
      "tier": "governance",
      "severity": "warning",
      "category": "governance",
      "description": "Governance graph connectivity and invariants",
      "depends_on": ["devex-contract"],
      "ac_ids": ["AC-SELFTEST-INTROSPECTABLE"]
    },
    {
      "id": "flowstudio-smoke",
      "tier": "governance",
      "severity": "warning",
      "category": "governance",
      "description": "Flow Studio core APIs respond (health, flows, graph, runs)",
      "depends_on": [],
      "ac_ids": ["AC-SELFTEST-INTROSPECTABLE"]
    },
    {
      "id": "ac-coverage",
      "tier": "optional",
      "severity": "info",
      "category": "governance",
      "description": "Acceptance criteria coverage thresholds",
      "depends_on": [],
      "ac_ids": ["AC-SELFTEST-INDIVIDUAL-STEPS"]
    },
    {
      "id": "extras",
      "tier": "optional",
      "severity": "info",
      "category": "governance",
      "description": "Experimental and additional checks",
      "depends_on": [],
      "ac_ids": ["AC-SELFTEST-DEGRADED"]
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

### Response (503 Service Unavailable)

```json
{
  "error": "Selftest module not available"
}
```

The endpoint may return 503 if the selftest module cannot be imported (e.g., missing dependencies).

---

## Response Schema

### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | Yes | Semver string (e.g., "1.0", "1.0.0"). Used for change detection. |
| `steps` | array | Yes | List of selftest step definitions (never empty in normal operation) |
| `summary` | object | Yes | Summary statistics about the plan |

### Step Object Schema

Each step in the `steps` array has the following structure:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier (kebab-case, e.g., "core-checks"). Used as key in URLs and logs. |
| `tier` | string | Yes | Execution tier: `kernel`, `governance`, or `optional`. Determines failure severity. |
| `severity` | string | Yes | Severity level: `critical`, `warning`, or `info`. Guides human interpretation of failures. |
| `category` | string | Yes | Functional category: `security`, `performance`, `correctness`, or `governance`. Groups steps by concern. |
| `description` | string | Yes | Human-readable one-line description (non-empty). Used in UI and logs. |
| `depends_on` | array | Yes | List of step IDs this step depends on (may be empty). Controls execution order. |
| `ac_ids` | array | Yes | List of acceptance criteria IDs (e.g., `["AC-SELFTEST-KERNEL-FAST"]`). Links steps to BDD scenarios. |

### Summary Object Schema

| Field | Type | Description |
|-------|------|-------------|
| `total` | integer | Total count of steps (must equal `len(steps)`) |
| `by_tier` | object | Counts grouped by tier |
| `by_tier.kernel` | integer | Count of steps with `tier: "kernel"` |
| `by_tier.governance` | integer | Count of steps with `tier: "governance"` |
| `by_tier.optional` | integer | Count of steps with `tier: "optional"` |

---

## Invariants (Enforced by Tests)

The following invariants are **guaranteed** and tested automatically:

### 1. Consistency Invariants

- **Total Count**: `summary.total == len(steps)`
- **Tier Counts**:
  - `summary.by_tier.kernel + summary.by_tier.governance + summary.by_tier.optional == summary.total`
  - `summary.by_tier.<tier> == count(step for step in steps if step.tier == <tier>)`

### 2. Uniqueness Invariants

- **Step IDs**: All `step.id` values are unique across the `steps` array (no duplicates)
- **Self-Dependencies**: No step depends on itself (no `step_id in step.depends_on`)

### 3. Validity Invariants

- **Enum Values**: All `tier` values are in `{kernel, governance, optional}`
- **Enum Values**: All `severity` values are in `{critical, warning, info}`
- **Enum Values**: All `category` values are in `{security, performance, correctness, governance}`
- **Dependencies Valid**: All IDs in `depends_on` refer to existing steps (no dangling references)

### 4. Graph Invariants

- **Acyclic**: The dependency graph forms a DAG (directed acyclic graph). No cycles (direct or transitive).
- **Topological Order**: Steps with dependencies appear after their dependencies in the `steps` array (no forward references)

### 5. Determinism Invariants

- **Idempotent**: Calling `/api/selftest/plan` twice returns identical JSON (same step order, same properties)
- **Version Stability**: If `version` remains unchanged, the plan is guaranteed unchanged

### 6. Performance Invariants

- **Response Time**: Response time < 1 second (suitable for real-time UI updates)
- **No Side Effects**: Endpoint is read-only; no state changes occur

---

## Version History and Stability

### Current Version: 1.0

The current stable version is `1.0`. This document describes the contract for this version.

### Breaking Change Policy

**What triggers a major version bump?**
- Adding or removing a field from step objects
- Changing the type of a field (e.g., `string` → `array`)
- Changing valid enum values (e.g., tier: `[kernel, governance, optional]` → `[kernel, governance]`)
- Changing the structure of `summary` object

**What does NOT trigger a version bump?**
- Adding new steps to the `steps` array
- Changing a step's `description` text
- Changing a step's dependencies
- Changing AC IDs

**Release Process:**
1. Propose change with rationale (issue/PR comment)
2. Update `swarm/tools/selftest.py` `get_selftest_plan_json()` and version field
3. Update this document and response schema examples
4. Run contract tests (`pytest tests/test_selftest_api_contract.py`)
5. Merge with explicit version bump in commit message: `semver: major bump 1.0 → 2.0`

---

## Endpoint 2: GET /platform/status

The `/platform/status` endpoint provides broader governance context, including selftest results. See `docs/SELFTEST_GOVERNANCE.md` for details on the status schema.

### Coherence Requirements with /api/selftest/plan

The following coherence invariants are enforced between the two endpoints:

1. **Step ID Alignment**: Any step ID mentioned in `/platform/status` governance.selftest.steps must exist in `/api/selftest/plan`
2. **Count Alignment**: Status should not report more steps than the plan defines
3. **Tier Alignment**: If status reports a step's tier, it must match the tier in the plan
4. **Metadata Availability**: Every step in status must have corresponding description, tier, and dependencies in the plan (for UI rendering)

---

## Integration with Flow Studio

### Plan Display

Flow Studio displays the selftest plan in the "Governance" tab:

```
Self-Test Steps:
  [KERNEL] core-checks (critical)      - Python tooling checks
  [KERNEL] ...

  [GOVERNANCE] skills-governance (warning) - Skills linting
  [GOVERNANCE] agents-governance (warning) - Agent definitions
  ...
```

**UI Expectations:**
- Steps displayed in order (same order as returned by API)
- Tier badges (KERNEL/GOVERNANCE/OPTIONAL) color-coded
- Severity icons (CRITICAL/WARNING/INFO)
- Dependencies shown as arrows between steps
- AC IDs shown in detailed view (click to link to BDD scenarios)

### Status Integration

Flow Studio's status modal shows current selftest execution state, keyed by step IDs from `/api/selftest/plan`.

---

## Error Handling

### Graceful Degradation

If the selftest module is unavailable:
- `/api/selftest/plan` returns `503 Service Unavailable` with `{"error": "Selftest module not available"}`
- Flow Studio displays a graceful fallback message
- Status endpoint continues to work independently

### Validation Errors

If the plan fails internal validation (e.g., invalid dependencies), the endpoint logs the error and may return `500 Internal Server Error`. This is a deployment issue, not a runtime contract violation.

---

## Testing and Validation

### Automated Tests

All contract invariants are validated by automated pytest tests:

```bash
# Run contract tests
uv run pytest tests/test_selftest_api_contract.py -v

# Run plan-status coherence tests
uv run pytest tests/test_selftest_plan_status_e2e.py -v
```

**Test Coverage** (19 tests total):
- `test_selftest_api_contract.py`: 14 tests covering plan schema and invariants
- `test_selftest_plan_status_e2e.py`: 5 tests covering coherence between endpoints

### Continuous Integration

Every PR runs these tests to prevent contract regressions:

```yaml
# .github/workflows/validate.yml
- run: uv run pytest tests/test_selftest_api_contract.py -v
- run: uv run pytest tests/test_selftest_plan_status_e2e.py -v
```

---

## Usage Examples

### Example 1: UI Rendering (JavaScript/React)

```javascript
// Fetch the plan
const response = await fetch('/api/selftest/plan');
const plan = await response.json();

// Render step list
plan.steps.forEach((step) => {
  const tier = step.tier.toUpperCase();
  const color = {
    'KERNEL': 'red',
    'GOVERNANCE': 'yellow',
    'OPTIONAL': 'blue'
  }[tier];

  console.log(`[${tier}] ${step.id} - ${step.description}`);
  if (step.depends_on.length > 0) {
    console.log(`  Depends on: ${step.depends_on.join(', ')}`);
  }
});

// Display summary
console.log(`Total: ${plan.summary.total} steps`);
console.log(`Kernel: ${plan.summary.by_tier.kernel}, Governance: ${plan.summary.by_tier.governance}, Optional: ${plan.summary.by_tier.optional}`);
```

### Example 2: CI Integration (Bash)

```bash
#!/bin/bash

# Fetch the plan
PLAN=$(curl -s http://localhost:5000/api/selftest/plan)

# Extract KERNEL step count
KERNEL_COUNT=$(echo "$PLAN" | jq '.summary.by_tier.kernel')
echo "KERNEL steps: $KERNEL_COUNT"

# Iterate over steps
echo "$PLAN" | jq -r '.steps[] | "\(.id) (\(.tier))"' | while read id tier; do
  echo "  - $id ($tier)"
done
```

### Example 3: Status Monitoring (Python)

```python
import requests

response = requests.get('http://localhost:5000/api/selftest/plan')
plan = response.json()

# Verify plan is healthy
assert plan['summary']['total'] > 0, "Plan has no steps"
assert plan['summary']['by_tier']['kernel'] >= 1, "Missing KERNEL tier"

# Extract all step IDs for status polling
step_ids = [step['id'] for step in plan['steps']]
print(f"Monitoring {len(step_ids)} selftest steps")
```

---

## FAQ

**Q: Can I add a new step without breaking the contract?**
A: Yes. Adding steps does not change the contract (only adds items to the array). Clients should handle gracefully.

**Q: What if a step's description changes?**
A: This is a non-breaking change. Clients that cache descriptions may need invalidation logic.

**Q: Can I change a step's tier from GOVERNANCE to OPTIONAL?**
A: No, this is a breaking change (changes execution semantics). Requires major version bump.

**Q: What does "depends_on" mean for step ordering?**
A: A step with `depends_on: ["other-step"]` must not execute until `other-step` passes. The flow runner respects this order.

**Q: Can there be empty steps list?**
A: Theoretically, if selftest is disabled. But in normal operation, list is non-empty. Contract handles both cases.

---

## Changelog

### v1.0 (Current)
- Initial stable contract
- 11 selftest steps defined (1 KERNEL, 8 GOVERNANCE, 2 OPTIONAL)
- Full dependency graph support
- AC ID traceability
- Tier-based execution semantics

---

## Related Documents

- **`docs/SELFTEST_SYSTEM.md`** — Architecture and design of the selftest system
- **`docs/SELFTEST_GOVERNANCE.md`** — Governance status endpoint and remediation
- **`features/selftest.feature`** — BDD scenarios (acceptance criteria)
- **`swarm/tools/selftest.py`** — Implementation of `get_selftest_plan_json()`

