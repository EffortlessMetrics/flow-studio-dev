# Health Check - No Gate Decision Scenario

> Teaching scenario: Gate flow incomplete - individual checks passed but decision artifact missing

## Purpose

This scenario demonstrates what happens when the Gate flow (Flow 4) performs individual verification steps but fails to produce the final decision artifact (`merge_recommendation.md`). This creates an incomplete gate state.

## Failure Pattern

**Root Cause**: The `merge-decider` agent was not invoked or failed to write `merge_recommendation.md`.

**Detection Point**: RunInspector and Flow Studio detect missing decision artifact for Gate flow.

**Result**: Gate flow shows partial completion - individual checks present but no final decision.

## Directory Structure

```
health-check-no-gate-decision/
├── run.json                    # Scenario metadata
├── README.md                   # This file
├── signal/                     # Flow 1 - Complete
│   ├── problem_statement.md
│   └── requirements_functional.md
├── plan/                       # Flow 2 - Complete
│   ├── adr_current.md
│   └── work_plan.md
├── build/                      # Flow 3 - Complete
│   ├── subtask_context_manifest.json
│   ├── test_changes_summary.md
│   ├── impl_changes_summary.md
│   ├── code_critique.md
│   └── build_receipt.json
└── gate/                       # Flow 4 - INCOMPLETE (no decision)
    ├── receipt_audit.md        # Individual check: PRESENT
    └── security_status.md      # Individual check: PRESENT
    # MISSING: merge_recommendation.md
```

## SDLC Bar Status in Flow Studio

When viewed in Flow Studio, this run shows:

- **Signal (Flow 1)**: GREEN - All required artifacts present
- **Plan (Flow 2)**: GREEN - All required artifacts present
- **Build (Flow 3)**: GREEN - All required artifacts present
- **Gate (Flow 4)**: YELLOW/INCOMPLETE - Checks present but no `merge_recommendation.md`
- **Deploy (Flow 5)**: GRAY - Cannot start without gate decision
- **Wisdom (Flow 6)**: GRAY - Not started

## Teaching Points

1. **Decision artifacts are critical**: Individual checks aren't enough - a final decision is required
2. **Flow completion requires all steps**: Partial execution leaves workflow in limbo
3. **Deploy cannot proceed**: Flow 5 depends on Gate's `merge_recommendation.md` as input
4. **Orchestrator failure pattern**: This typically indicates orchestrator didn't complete Gate flow properly

## Expected User Action

After viewing this scenario in Flow Studio:

1. Notice Gate flow shows INCOMPLETE status (yellow bar)
2. Inspect `gate/` directory and notice missing `merge_recommendation.md`
3. Re-run Gate flow to completion
4. Verify `merge_recommendation.md` is produced before proceeding to Deploy

## Contrast with Baseline

**health-check (baseline)**: Gate completes with `merge_recommendation.md` showing MERGE decision

**health-check-no-gate-decision (this scenario)**: Gate has partial results but no final decision - workflow is blocked

## Contrast with health-check-missing-tests

**health-check-missing-tests**: Gate completes and produces decision (BOUNCE) - workflow is clear

**health-check-no-gate-decision (this scenario)**: Gate incomplete, no decision made - workflow is ambiguous
