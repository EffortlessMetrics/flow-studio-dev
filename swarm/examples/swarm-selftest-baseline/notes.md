# Swarm Selftest Baseline: Notes

## Overview

This example shows a **healthy swarm** passing all 10 selftest steps across all three tiers:

- ✅ **Kernel Tier** (1 step): Service is operational
  - `core-checks` — Rust compilation, format, linting, unit tests

- ✅ **Governance Tier** (7 steps): Configuration and contracts are valid
  - `skills-governance` — Skills YAML parses and references valid
  - `agents-governance` — Agent bijection, colors, frontmatter syntax
  - `bdd` — Feature files exist and are well-formed
  - `ac-status` — Acceptance criteria tracked in code and docs
  - `policy-tests` — OPA policies (if defined) validate successfully
  - `devex-contract` — Flow/agent/skill contracts are satisfied
  - `graph-invariants` — Flow DAG is acyclic, dependencies valid

- ✅ **Optional Tier** (2 steps): Extended checks pass (informational)
  - `ac-coverage` — Code coverage meets thresholds
  - `extras` — Experimental/future checks (benign)

## Key Metrics

- **Total time:** 12.45s (per-step breakdown shown in report)
- **Critical failures:** 0 (if any, flow halts; Kernel failure = RED status)
- **Warning failures:** 0 (if any in Governance, status = YELLOW, but flow continues)
- **Info failures:** 0 (Optional tier failures don't affect overall status)

## Severity Distribution

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 1     | PASS   |
| WARNING  | 6     | PASS   |
| INFO     | 3     | PASS   |

## Category Distribution

| Category    | Count | Status |
|-------------|-------|--------|
| security    | 1     | PASS   |
| performance | 0     | N/A    |
| correctness | 5     | PASS   |
| governance  | 4     | PASS   |

## Interpreting the Report

### Overall Status
- `GREEN` = All tiers pass (Kernel OK, Governance OK, Optional OK)
- `YELLOW` = Kernel OK, but Governance has warnings; flow may proceed with caution
- `RED` = Kernel failure; flow halts

### Using This for Agents
Flow 6 (Wisdom) and other agents can:

1. **Read** `selftest_report.json` from `RUN_BASE/build/`
2. **Extract** the `summary` section for quick status
3. **Correlate** failures across steps with known issues (e.g., "agent color mismatch" → `agents-governance` failure)
4. **Recommend** fixes in `learnings.md` (e.g., "Agents need color audit; see ADR 00001")

### Step Structure

Each step object includes:

```json
{
  "step_id": "example-step",
  "description": "Human-readable description",
  "tier": "kernel|governance|optional",
  "severity": "critical|warning|info",
  "category": "security|performance|correctness|governance",
  "status": "PASS|FAIL|SKIP",
  "exit_code": 0,
  "duration_ms": 1000,
  "command": "shell command that ran",
  "timestamp_start": 1701345135.0,
  "timestamp_end": 1701345138.2
}
```

Agents can:
- Check `tier` to understand **scope** (is this Kernel or optional?)
- Check `severity` to understand **urgency** (critical = must fix, info = informational)
- Check `category` to understand **domain** (is this security, correctness, governance, performance?)
- Use `timestamp_start`/`timestamp_end` for **profiling** or detecting slow checks
- Extract the `command` to re-run the check if needed for debugging

## Extending This Example

If the swarm gains new steps (e.g., "performance-benchmarks", "schema-validation"), add them to this report and update the tier breakdowns. The structure is forward-compatible.

## Related

- `swarm/SELFTEST_SYSTEM.md` — Full selftest system spec
- `docs/adr/00001-swarm-selftest-scope.md` — Clarifies this is "swarm" selftest, not service selftest
