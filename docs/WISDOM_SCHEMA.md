# Wisdom Summary Schema

> For: Developers working with Flow 6 (Wisdom) outputs and cross-run analytics.

This document defines the JSON schema for `wisdom_summary.json`, the structured output of the wisdom summarizer that enables dashboards, trend analysis, and cross-run comparisons.

---

## Overview

The wisdom summary consolidates Flow 6 artifacts into a machine-readable format:

```
RUN_BASE/wisdom/
├── artifact_audit.md        # Input: Flow artifact matrix
├── regression_report.md     # Input: Regression findings
├── flow_history.json        # Input: Execution timeline
├── learnings.md             # Input: Extracted patterns
├── feedback_actions.md      # Input: Action items
└── wisdom_summary.json      # Output: Structured summary
```

---

## Schema Definition

### Top-Level Structure

```json
{
  "run_id": "string",
  "created_at": "ISO8601 timestamp",
  "flows": { /* FlowSummary per flow */ },
  "summary": { /* Aggregate metrics */ },
  "labels": [ /* Extracted tags */ ],
  "key_artifacts": { /* Artifact paths */ }
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | string | Run identifier (e.g., `health-check-risky-deploy`) |
| `created_at` | string | ISO8601 timestamp when summary was generated |
| `flows` | object | Per-flow execution status and loop counts |
| `summary` | object | Aggregate metrics (artifacts, regressions, learnings) |
| `labels` | array | Extracted labels/tags for categorization |
| `key_artifacts` | object | Paths to key wisdom artifacts |

---

## FlowSummary Object

Each flow key (`signal`, `plan`, `build`, `gate`, `deploy`, `wisdom`) maps to a FlowSummary:

```json
{
  "status": "succeeded | failed | skipped",
  "microloops": 0,      // Optional, only if > 0
  "test_loops": 0,      // Optional, only if > 0
  "code_loops": 0       // Optional, only if > 0
}
```

### Status Values

| Status | Meaning |
|--------|---------|
| `succeeded` | Flow completed with decision artifact present |
| `failed` | Flow directory exists but decision artifact missing |
| `skipped` | No directory or no artifacts present |

### Loop Counts

Loop counts are only included when greater than zero:

| Field | Source | Description |
|-------|--------|-------------|
| `microloops` | Signal flow | `requirements_loop` iterations |
| `test_loops` | Build flow | `test_loop` iterations |
| `code_loops` | Build flow | `code_loop` iterations |

---

## Summary Object

Aggregate metrics across the run:

```json
{
  "artifacts_present": 5,
  "regressions_found": 0,
  "learnings_count": 3,
  "feedback_actions_count": 2,
  "issues_created": 1
}
```

| Field | Type | Description |
|-------|------|-------------|
| `artifacts_present` | int | Count of wisdom artifacts (0-5) |
| `regressions_found` | int | Regressions detected in regression_report.md |
| `learnings_count` | int | Section headings (##/###) in learnings.md |
| `feedback_actions_count` | int | Checkboxes in feedback_actions.md |
| `issues_created` | int | "Issue to Create" sections in feedback_actions.md |

---

## Labels Array

Labels are extracted from flow outcomes and artifact content:

```json
["outcome-name", "risk-managed", "conditional-approval", "complete-artifacts", "no-gaps"]
```

### Standard Labels

| Label | Source | Meaning |
|-------|--------|---------|
| `outcome-*` | flow_history.json `outcome` | Lowercased, hyphenated outcome |
| `risk-managed` | learnings.md contains "risk" | Risk patterns identified |
| `conditional-approval` | learnings.md contains "conditional approv" | Conditional approval noted |
| `complete-artifacts` | artifact_audit.md contains "COMPLETE" | All expected artifacts present |
| `no-gaps` | artifact_audit.md contains "Gaps Identified: None" | No artifact gaps |

---

## Key Artifacts Object

Maps artifact types to relative paths:

```json
{
  "artifact_audit": "wisdom/artifact_audit.md",
  "regression_report": "wisdom/regression_report.md",
  "learnings": "wisdom/learnings.md",
  "flow_history": "wisdom/flow_history.json",
  "feedback_actions": "wisdom/feedback_actions.md"
}
```

Only present artifacts are included in the map.

---

## Complete Example

```json
{
  "run_id": "health-check",
  "created_at": "2025-01-15T10:30:00.000000+00:00",
  "flows": {
    "signal": {
      "status": "succeeded",
      "microloops": 2
    },
    "plan": {
      "status": "succeeded"
    },
    "build": {
      "status": "succeeded",
      "test_loops": 1,
      "code_loops": 2
    },
    "gate": {
      "status": "succeeded"
    },
    "deploy": {
      "status": "succeeded"
    },
    "wisdom": {
      "status": "succeeded"
    }
  },
  "summary": {
    "artifacts_present": 5,
    "regressions_found": 0,
    "learnings_count": 4,
    "feedback_actions_count": 3,
    "issues_created": 1
  },
  "labels": [
    "complete-artifacts",
    "no-gaps",
    "outcome-success"
  ],
  "key_artifacts": {
    "artifact_audit": "wisdom/artifact_audit.md",
    "regression_report": "wisdom/regression_report.md",
    "learnings": "wisdom/learnings.md",
    "flow_history": "wisdom/flow_history.json",
    "feedback_actions": "wisdom/feedback_actions.md"
  }
}
```

---

## Aggregation Schema

When aggregating across runs with `wisdom_aggregate_runs.py`, the output structure is:

```json
{
  "generated_at": "ISO8601 timestamp",
  "runs_analyzed": 10,
  "flow_success_rates": {
    "signal": 0.9,
    "plan": 0.85,
    "build": 0.8,
    "gate": 0.95,
    "deploy": 0.9,
    "wisdom": 1.0
  },
  "flow_counts": {
    "signal": { "succeeded": 9, "failed": 1, "skipped": 0 },
    ...
  },
  "totals": {
    "regressions_found": 5,
    "learnings_extracted": 40,
    "feedback_actions": 25,
    "issues_created": 8,
    "artifacts_produced": 48
  },
  "averages": {
    "regressions_per_run": 0.5,
    "learnings_per_run": 4.0,
    "artifacts_per_run": 4.8
  },
  "top_labels": [
    ["complete-artifacts", 8],
    ["no-gaps", 7],
    ["outcome-success", 6]
  ],
  "runs": [
    { "_source": "example", "_path": "swarm/examples/health-check", ... }
  ]
}
```

---

## Usage

### Generate Summary for a Run

```bash
# Generate and write to disk
make wisdom-summary RUN_ID=health-check

# Preview without writing
uv run swarm/tools/wisdom_summarizer.py health-check --dry-run

# Output path only
uv run swarm/tools/wisdom_summarizer.py health-check --output path
```

### Aggregate Across Runs

```bash
# JSON output
make wisdom-aggregate

# Markdown report
make wisdom-report

# Custom output file
uv run swarm/tools/wisdom_aggregate_runs.py --output /tmp/wisdom.json
```

### Python API

```python
from swarm.tools.wisdom_summarizer import WisdomSummarizer

summarizer = WisdomSummarizer()

# Generate summary
summary = summarizer.generate_summary("health-check")
print(summary.to_dict())

# Write to disk
path = summarizer.write_summary("health-check")
print(f"Written to: {path}")
```

---

## Validation

The schema is informally validated by the dataclasses in `wisdom_summarizer.py`:

- `FlowSummary`: status, loop counts
- `WisdomSummary`: run_id, created_at, flows, summary, labels, key_artifacts

For formal JSON Schema validation, see the example test in `tests/test_wisdom_summarizer.py`.

---

## See Also

- [RUN_LIFECYCLE.md](./RUN_LIFECYCLE.md) — Run management and retention
- [swarm/flows/flow-wisdom.md](../swarm/flows/flow-wisdom.md) — Flow 6 specification
- [swarm/infrastructure/flow-6-extensions.md](../swarm/infrastructure/flow-6-extensions.md) — Production extensions
