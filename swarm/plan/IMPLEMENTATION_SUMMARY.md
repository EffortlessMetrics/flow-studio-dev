# CI/PR Deep Link Integration - Implementation Summary

## Overview

This plan creates a **Flow Studio deep link generator** (`mk_flow_link.py`) that enables CI/PR workflows to generate shareable URLs linking directly to runs, flows, steps, and artifacts in Flow Studio.

## Goals

1. **Programmatic URL generation** - CLI tool + Python API for generating Flow Studio deep links
2. **Validation integration** - Emit Flow Studio URLs when `validate_swarm.py` detects issues
3. **PR reporting** - Template for `gh-reporter` agent to create actionable PR comments with links

## Deliverables

### 1. Core Tool: `swarm/tools/mk_flow_link.py`

**Purpose**: Generate Flow Studio deep links for runs, flows, steps, and artifacts.

**CLI Usage**:
```bash
# Basic run link
uv run swarm/tools/mk_flow_link.py --run health-check

# Flow link in operator mode
uv run swarm/tools/mk_flow_link.py --run pr-123 --flow build --mode operator

# Step link with artifacts view
uv run swarm/tools/mk_flow_link.py --run pr-123 --flow gate --step merge_decision --view artifacts

# JSON output for scripting
uv run swarm/tools/mk_flow_link.py --run pr-123 --flow build --json
```

**Python API**:
```python
from swarm.tools.mk_flow_link import FlowStudioLinkGenerator

gen = FlowStudioLinkGenerator()
url = gen.link(run="pr-123", flow="gate", step="merge_decision", mode="operator")
```

**Features**:
- ✅ Supports all Flow Studio URL parameters (mode, run, flow, step, view, tab)
- ✅ Validates parameters against flow configs
- ✅ JSON output mode for machine consumption
- ✅ Custom base URL support for deployments
- ✅ No external dependencies (stdlib only)

### 2. Validation Integration

**File**: `swarm/tools/validate_swarm.py`

**Enhancement**: Add `flow_studio_url` fields to JSON output for flows/steps with issues.

**Example output**:
```json
{
  "flows": {
    "build": {
      "has_issues": true,
      "flow_studio_url": "http://localhost:5000/?mode=operator&flow=build&view=artifacts",
      "issues": [...]
    }
  },
  "steps": {
    "gate:merge_decision": {
      "has_issues": true,
      "flow_studio_url": "http://localhost:5000/?mode=operator&flow=gate&step=merge_decision&tab=run",
      "issues": [...]
    }
  }
}
```

**Usage**:
```bash
# Get validation issues with Flow Studio URLs
uv run swarm/tools/validate_swarm.py --json | jq -r '.flows.build.flow_studio_url'
```

### 3. PR Comment Template

**File**: `.claude/agents/gh-reporter.md`

**Enhancement**: Add Flow Studio link generation to PR/issue reporting.

**Example PR comment**:
```markdown
## Swarm SDLC Summary for `pr-123-abc123`

[📊 View in Flow Studio](http://localhost:5000/?mode=operator&run=pr-123-abc123)

### Flow Progress

| Flow | Status | Decision | Link |
|------|--------|----------|------|
| Signal | ✅ Done | ✅ requirements_decision.md | [View](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=signal&view=artifacts) |
| Build | ⚠️ Partial | ⏳ Missing | [View](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=build&view=artifacts) |
| Gate | ❌ Not Started | — | [View](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=gate) |

### Issues Detected

**Build Flow** - 2 required artifacts missing
- [🔍 Inspect in Flow Studio](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=build&view=artifacts)
- Missing: `test_summary.md`, `build_receipt.json`
```

## Implementation Phases

### Phase 1: Core Tool (Priority: High)

**Subtasks**:
1. Create `swarm/tools/mk_flow_link.py` with `FlowStudioLinkGenerator` class
2. Implement CLI with all parameters (run, flow, step, mode, view, tab)
3. Add parameter validation (flow exists, step exists in flow, etc.)
4. Support JSON output mode
5. Add `--list-flows` and `--list-steps` commands

**Estimate**: Small (2-3 hours)

**Dependencies**: None

**Verification**:
- CLI can generate URLs with all parameter combinations
- Validation rejects invalid flow/step combinations
- JSON output is well-formed

### Phase 2: Testing (Priority: High)

**Subtasks**:
1. Create `tests/test_mk_flow_link.py`
2. Test URL generation (basic, full parameters)
3. Test validation (invalid flow, step without flow, etc.)
4. Test CLI JSON output
5. Test flow/step listing commands

**Estimate**: Small (1-2 hours)

**Dependencies**: Phase 1

**Verification**:
- All tests pass
- Coverage > 90% for `mk_flow_link.py`

### Phase 3: Validation Integration (Priority: Medium)

**Subtasks**:
1. Import `FlowStudioLinkGenerator` in `validate_swarm.py`
2. Add `flow_studio_url` field to `build_detailed_json_output()`
3. Add CLI flag `--flow-studio-base-url` for custom base URL
4. Test JSON output includes URLs

**Estimate**: Small (1-2 hours)

**Dependencies**: Phase 1

**Verification**:
- `validate_swarm.py --json` output includes `flow_studio_url` fields
- URLs are valid and link to correct flows/steps

### Phase 4: gh-reporter Integration (Priority: Medium)

**Subtasks**:
1. Update `.claude/agents/gh-reporter.md` prompt
2. Add Flow Studio link generation to PR comment template
3. Create example PR comments with links
4. Test with `RunInspector` to generate real status

**Estimate**: Small (1-2 hours)

**Dependencies**: Phase 1

**Verification**:
- `gh-reporter` can generate PR comments with Flow Studio links
- Links work when Flow Studio is running

### Phase 5: Documentation (Priority: Low)

**Subtasks**:
1. Add section to `DEMO_RUN.md` on deep link usage
2. Create `swarm/tools/README.md` with tool catalog
3. Update `CLAUDE.md` with link generator command
4. Add examples to flow documentation

**Estimate**: Small (1-2 hours)

**Dependencies**: Phases 1-4

**Verification**:
- Documentation is clear and includes examples
- Links in docs work when Flow Studio is running

## Success Criteria

1. ✅ `mk_flow_link.py` can generate valid Flow Studio URLs
2. ✅ All URL parameters supported (mode, run, flow, step, view, tab)
3. ✅ Validation detects invalid flow/step combinations
4. ✅ JSON output mode works for machine consumption
5. ✅ Tests achieve > 90% coverage
6. ✅ `validate_swarm.py` JSON includes `flow_studio_url` fields
7. ✅ `gh-reporter` can generate PR comments with links
8. ✅ Documentation updated with usage examples

## Example Workflows

### Developer debugging a failed build

```bash
# Run validation, get Flow Studio URL for build flow
URL=$(uv run swarm/tools/validate_swarm.py --json | jq -r '.flows.build.flow_studio_url')

# Open in browser
echo "Inspect build artifacts: $URL"
```

### CI/PR integration

```bash
# Generate link for PR comment
RUN_ID="pr-${PR_NUMBER}-${COMMIT_SHA:0:7}"
LINK=$(uv run swarm/tools/mk_flow_link.py --run "$RUN_ID" --mode operator)

# Post to PR
gh pr comment "$PR_NUMBER" --body "View run in Flow Studio: $LINK"
```

### Manual inspection

```bash
# Generate link to specific step with artifacts
uv run swarm/tools/mk_flow_link.py \
  --run swarm-selftest-baseline \
  --flow gate \
  --step merge_decision \
  --view artifacts \
  --tab run
```

## Files Created/Modified

### New Files

1. `swarm/tools/mk_flow_link.py` (core tool)
2. `tests/test_mk_flow_link.py` (tests)
3. `swarm/tools/README.md` (tool docs)

### Modified Files

1. `swarm/tools/validate_swarm.py` (add URLs to JSON)
2. `.claude/agents/gh-reporter.md` (add template)
3. `DEMO_RUN.md` (add usage section)
4. `CLAUDE.md` (add command reference)

## Technical Details

### URL Format

Flow Studio deep links use standard query parameters:

```
http://localhost:5000/?mode=operator&run=pr-123&flow=build&step=self_review&view=artifacts&tab=run
```

**Parameters**:
- `mode` - UI mode (`author` | `operator`, default: `author`)
- `run` - Run ID (e.g., `health-check`, `pr-123-abc123`)
- `flow` - Flow key (`signal` | `plan` | `build` | `gate` | `deploy` | `wisdom`)
- `step` - Step ID within flow (requires `flow`)
- `view` - Graph view (`agents` | `artifacts`, default: `agents`)
- `tab` - Step detail tab (`spec` | `run` | `artifacts`, requires `step`)

### Validation Logic

**Rules enforced by `FlowStudioLinkGenerator`**:
1. `run` is required
2. `step` requires `flow`
3. `tab` requires `step`
4. `flow` must be in `[signal, plan, build, gate, deploy, wisdom]`
5. `step` must exist in the specified flow's config YAML
6. `mode` must be in `[author, operator]` if specified
7. `view` must be in `[agents, artifacts]` if specified

### Dependencies

**Runtime**:
- Python 3.10+
- No external dependencies (stdlib only)

**Development**:
- pytest (testing)
- Coverage report tools

## Design Decisions

### Why a separate CLI tool?

- **Composability** - Can be used standalone, imported as library, or piped to other tools
- **Single responsibility** - URL generation is orthogonal to validation/reporting
- **Testability** - Isolated logic, easy to test
- **Reusability** - Any tool can import `FlowStudioLinkGenerator`

### Why integrate with validate_swarm?

- Validation results are already consumed by CI/reporting tools
- Adding URLs makes validation output actionable
- Backward compatible (only adds fields to JSON output)

### Why default to localhost?

- Flow Studio is a local development tool (not deployed by default)
- Users running Flow Studio locally can click links immediately
- CI/PR comments include instructions to start Flow Studio
- Custom base URL supported via `--base-url` flag

## Next Steps

Ready to implement! Start with **Phase 1** (core tool) and proceed sequentially through phases.

## Plan Documents

All planning artifacts are in `swarm/plan/`:

1. **flow_studio_deeplink_plan.md** - Detailed implementation plan
2. **mk_flow_link_example.py** - Example implementation with full CLI/API
3. **gh_reporter_template_example.md** - PR comment templates and examples
4. **IMPLEMENTATION_SUMMARY.md** - This document (executive summary)

---

**Status**: ✅ Planning complete, ready for implementation

**Total Effort Estimate**: Small-Medium (8-12 hours across all phases)

**Risk**: Low (no breaking changes, backward compatible, well-defined scope)
