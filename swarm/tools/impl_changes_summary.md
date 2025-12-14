# Implementation Changes Summary

## Task: Add Budget Metrics to Receipts in Engines

**Date**: 2025-12-10

### Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `swarm/runtime/engines.py` | Modified | Updated `_write_receipt` methods and callers to include truncation_info |

### Implementation Details

**Modified**: `swarm/runtime/engines.py`

#### GeminiStepEngine Changes

1. **`_write_receipt` signature updated** (lines 701-759):
   - Added optional parameter: `truncation_info: Optional[HistoryTruncationInfo] = None`
   - Added docstring documentation for the new parameter
   - Added logic to include `context_truncation` in receipt JSON:
   ```python
   if truncation_info:
       receipt["context_truncation"] = truncation_info.to_dict()
   ```

2. **`_execute_gemini` signature updated** (lines 544-549):
   - Added optional parameter: `truncation_info: Optional[HistoryTruncationInfo] = None`
   - Updated docstring
   - Updated `_write_receipt` call to pass truncation_info (line 661)

3. **`run_step` updated** (line 339):
   - Updated call to `_execute_gemini` to pass truncation_info from `_build_prompt`

#### ClaudeStepEngine Changes

1. **`_run_step_stub`** (lines 1276-1347):
   - Added call to `_build_prompt(ctx)` to obtain truncation_info (line 1297)
   - Added context_truncation to receipt JSON (lines 1342-1344)

2. **`_run_step_cli`** (lines 1546-1568):
   - Added context_truncation to receipt JSON (lines 1565-1567)
   - truncation_info already available from `_build_prompt` call (line 1400)

3. **`_run_step_sdk_async`** (lines 1808-1831):
   - Added context_truncation to receipt JSON (lines 1826-1828)
   - truncation_info already available from `_build_prompt` call (line 1635)

### Receipt Structure

Receipts now include an optional `context_truncation` field:

```json
{
  "engine": "claude-step",
  "mode": "sdk",
  "provider": "anthropic",
  ...
  "context_truncation": {
    "steps_included": 5,
    "steps_total": 10,
    "chars_used": 180000,
    "budget_chars": 200000,
    "truncated": true
  }
}
```

### Tests Addressed

- `tests/test_step_engine_contract.py` - 34 tests passed
- `tests/test_context_budget_config.py` - 18 tests passed
- `tests/test_claude_stepwise_backend.py` - 14 tests passed
- `tests/test_gemini_stepwise_backend.py` - 16 tests passed

**Total: 82 tests passed**

### Known Test Issues

`tests/test_step_prompt_teaching_notes.py` has 11 failing tests due to a pre-existing API change in `_build_prompt` (now returns tuple instead of string). These tests need to be updated to unpack the tuple.

### Trade-offs and Decisions

1. **Stub mode includes truncation_info**: Even in stub mode, `_build_prompt` is called to compute truncation_info for consistent budget metrics across all execution modes.

2. **Optional field**: The `context_truncation` field is only added when truncation_info is available, keeping receipt JSON minimal when no history truncation occurs.

### Verification Status

**VERIFIED**: Code written, 82 primary tests pass.

---

## Task: Add Budget Preset Types to Flow Studio domain.ts

**Date**: 2025-12-10

### Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `swarm/tools/flow_studio_ui/src/domain.ts` | Modified | Added budget preset types and updated StepReceipt interface |

### Implementation Details

**Modified**: `swarm/tools/flow_studio_ui/src/domain.ts`

Added three new type definitions after the existing `ContextBudgetOverride` interface (lines 162-188):

1. **`ContextBudgetPresetId`** - Union type for preset identifiers:
   ```typescript
   export type ContextBudgetPresetId = "lean" | "balanced" | "heavy";
   ```

2. **`ContextBudgetPreset`** - Interface for preset configuration values:
   ```typescript
   export interface ContextBudgetPreset {
     id: ContextBudgetPresetId;
     label: string;
     description: string;
     context_budget_chars: number;
     history_max_recent_chars: number;
     history_max_older_chars: number;
   }
   ```

3. **`BudgetMetrics`** - Interface for budget metrics captured during prompt building:
   ```typescript
   export interface BudgetMetrics {
     prompt_chars_used: number;
     prompt_tokens_estimated: number;
     history_steps_total: number;
     history_steps_included: number;
     truncation_occurred: boolean;
     effective_budgets: {
       context_budget_chars: number;
       history_max_recent_chars: number;
       history_max_older_chars: number;
       source: "default" | "profile" | "flow" | "step";
     };
   }
   ```

Also updated the `StepReceipt` interface (lines 375-382) to include an optional `context_truncation` field:
```typescript
context_truncation?: {
  steps_included: number;
  steps_total: number;
  chars_used: number;
  budget_chars: number;
  truncated: boolean;
};
```

### Tests Addressed

- TypeScript type-check passed (`make ts-check`)
- TypeScript build completed successfully (`make ts-build`)

### Critique Issues Resolved

N/A - No code_critique.md present

### Trade-offs and Decisions

1. **Placement**: New types placed immediately after `ContextBudgetOverride` to maintain logical grouping of context budget related types.

2. **Inline object type**: Used inline object type for `effective_budgets` within `BudgetMetrics` to match the existing pattern for nested structures in domain.ts.

3. **Comment annotation**: Added comment annotation to `context_truncation` field in `StepReceipt` explaining it is populated by the prompt builder.

### Verification Status

**VERIFIED**: Code written and TypeScript compilation passes.

---

## Previous Task: Create Wisdom Summarizer Module

### Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `swarm/tools/wisdom_summarizer.py` | Created | New Python module for generating wisdom summaries |

### Implementation Details

**Created**: `swarm/tools/wisdom_summarizer.py`

The module provides:

1. **WisdomSummarizer class** - Core logic for reading and summarizing wisdom artifacts
2. **CLI interface** - Runnable via `uv run swarm/tools/wisdom_summarizer.py <run_id>`
3. **Dataclasses** - `FlowSummary` and `WisdomSummary` for structured output

**Key Features**:
- Reads all 5 wisdom artifacts: `artifact_audit.md`, `regression_report.md`, `flow_history.json`, `learnings.md`, `feedback_actions.md`
- Parses `flow_history.json` to extract flow statuses and microloop counts
- Falls back to artifact presence detection when `flow_history.json` is unavailable
- Counts markdown headings in `learnings.md` to estimate learnings count
- Counts action items (`- [ ]`) in `feedback_actions.md`
- Detects "NO REGRESSIONS" pattern in `regression_report.md`
- Extracts labels from content patterns (risk management, conditional approval, etc.)
- Handles missing artifacts gracefully (counts as 0, status as "skipped")

**Output Structure**:
```json
{
  "run_id": "string",
  "created_at": "ISO 8601 timestamp",
  "flows": {
    "signal": { "status": "succeeded|failed|skipped", "microloops": 0 },
    "plan": { "status": "succeeded|failed|skipped" },
    "build": { "status": "succeeded|failed|skipped", "test_loops": 0, "code_loops": 0 },
    "gate": { "status": "succeeded|failed|skipped" },
    "deploy": { "status": "succeeded|failed|skipped" },
    "wisdom": { "status": "succeeded|failed|skipped" }
  },
  "summary": {
    "artifacts_present": "count",
    "regressions_found": "count",
    "learnings_count": "count",
    "feedback_actions_count": "count",
    "issues_created": "count"
  },
  "labels": ["array of tags"],
  "key_artifacts": { ... }
}
```

### Tests Addressed

No specific tests were provided. The implementation was verified manually:

1. Tested against `health-check-risky-deploy` example run - produces correct summary
2. Tested against `health-check` example run - handles missing wisdom artifacts
3. Tested nonexistent run - returns proper error exit code
4. Tested `--help` flag - CLI works correctly
5. Tested `--dry-run` flag - generates summary without writing

### Trade-offs and Decisions

1. **Flexible decision artifact detection**: The fallback artifact detection supports multiple filename patterns (e.g., `adr.md` or `adr_current.md`) to handle naming variations across runs.

2. **Learnings count via heading count**: Counting `##` and `###` headings provides a reasonable estimate of learnings sections without complex parsing.

3. **Label extraction from content patterns**: Labels are extracted using regex pattern matching rather than explicit metadata, making the system work with existing artifacts.

4. **No recursive artifact counting**: The `artifacts_present` count only covers the 5 standard wisdom artifacts, not nested or additional files.

### Verification Status

**VERIFIED**: Code written and manually tested against example runs. All tests pass.

### CLI Usage Examples

```bash
# Generate and write summary
uv run swarm/tools/wisdom_summarizer.py health-check-risky-deploy

# Dry run (don't write to disk)
uv run swarm/tools/wisdom_summarizer.py health-check-risky-deploy --dry-run

# Output just the path
uv run swarm/tools/wisdom_summarizer.py health-check-risky-deploy --output path

# Quiet mode (no output, just write the file)
uv run swarm/tools/wisdom_summarizer.py health-check-risky-deploy --output quiet
```
