# Health Check - Missing Tests Scenario

> Teaching scenario: Build flow completed with missing test artifacts, gate bounces back

## Purpose

This scenario demonstrates what happens when the Build flow (Flow 3) completes but critical test artifacts are missing. The Gate flow (Flow 4) detects the incomplete build and bounces the work back to Build.

## Failure Pattern

**Root Cause**: The `test-author` step in Build flow did not produce required test artifacts.

**Detection Point**: Gate flow's `receipt-checker` detects missing `test_changes_summary.md` during receipt audit.

**Result**: Gate flow produces `merge_recommendation.md` with status `BOUNCE` and reason `missing test coverage`.

## Directory Structure

```
health-check-missing-tests/
├── run.json                    # Scenario metadata
├── README.md                   # This file
├── signal/                     # Flow 1 - Complete
│   ├── problem_statement.md
│   └── requirements_functional.md
├── plan/                       # Flow 2 - Complete
│   ├── adr_current.md
│   └── work_plan.md
├── build/                      # Flow 3 - DEGRADED (missing test artifacts)
│   ├── subtask_context_manifest.json
│   ├── impl_changes_summary.md
│   ├── code_critique.md
│   └── build_receipt.json     # Status shows test step incomplete
└── gate/                       # Flow 4 - BOUNCE
    ├── receipt_audit.md       # Identifies missing test artifacts
    └── merge_recommendation.md # Status: BOUNCE
```

## SDLC Bar Status in Flow Studio

When viewed in Flow Studio, this run shows:

- **Signal (Flow 1)**: GREEN - All required artifacts present
- **Plan (Flow 2)**: GREEN - All required artifacts present
- **Build (Flow 3)**: YELLOW/DEGRADED - Missing `test_changes_summary.md`
- **Gate (Flow 4)**: RED/BOUNCE - Bounced back to Build
- **Deploy (Flow 5)**: GRAY - Not started
- **Wisdom (Flow 6)**: GRAY - Not started

## Teaching Points

1. **Incomplete flows are detectable**: Missing artifacts create degraded status bars
2. **Gate enforces receipts**: Receipt audit catches missing evidence
3. **Bounce-back pattern**: Gate doesn't try to fix test gaps, bounces to Build
4. **Human decision point**: Engineer reviews `merge_recommendation.md` to understand why bounce occurred

## Expected User Action

After viewing this scenario in Flow Studio:

1. Read `gate/merge_recommendation.md` to understand the bounce reason
2. Read `gate/receipt_audit.md` to see which artifacts are missing
3. Re-run Build flow with focus on test authoring
4. Re-run Gate flow after Build is complete

## Contrast with Baseline

**health-check (baseline)**: All flows complete, all artifacts present, Gate recommends MERGE

**health-check-missing-tests (this scenario)**: Build incomplete, Gate bounces back, human must intervene
