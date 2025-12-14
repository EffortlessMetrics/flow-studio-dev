# Flow Studio Deep Link Integration - Implementation Plan

## Summary

Create a small link generator tool (`swarm/tools/mk_flow_link.py`) that makes "open this run in Flow Studio" a first-class action for CI/PR workflows.

## Context

Flow Studio already supports deep linking via URL parameters:
- `mode` - `author` (default) or `operator`
- `run` - run ID (e.g., `health-check`, `swarm-selftest-baseline`)
- `flow` - flow key (e.g., `signal`, `build`, `gate`)
- `step` - step ID within flow (e.g., `self_review`, `merge_decision`)
- `view` - `agents` (default) or `artifacts`
- `tab` - tab name in step details (e.g., `run`, `spec`, `artifacts`)

Example URL:
```
http://localhost:5000/?mode=operator&run=swarm-selftest-baseline&flow=gate&step=merge_decision&tab=run
```

## Goals

1. **CLI tool** - Generate Flow Studio URLs programmatically
2. **Validation integration** - Emit URLs when validation detects issues
3. **PR comments** - Template for `gh-reporter` to link runs to Flow Studio

## Detailed Plan

### 1. Create `swarm/tools/mk_flow_link.py`

**File**: `swarm/tools/mk_flow_link.py`

**Purpose**: Standalone CLI tool + importable module for generating Flow Studio URLs

**Features**:
- Generate URLs with all supported parameters
- Support both local (`localhost:5000`) and custom base URLs
- Validation of parameters (flow/step combinations)
- JSON output mode for machine consumption
- Human-friendly CLI for manual use

**CLI interface**:
```bash
# Basic usage - link to a run
uv run swarm/tools/mk_flow_link.py --run health-check

# Link to specific flow in operator mode
uv run swarm/tools/mk_flow_link.py --run pr-123 --flow build --mode operator

# Link to specific step with artifacts view
uv run swarm/tools/mk_flow_link.py --run pr-123 --flow gate --step merge_decision --view artifacts

# Link to specific tab in step details
uv run swarm/tools/mk_flow_link.py --run pr-123 --flow gate --step merge_decision --tab run

# JSON output for piping to other tools
uv run swarm/tools/mk_flow_link.py --run pr-123 --flow build --json

# Custom base URL (for deployment)
uv run swarm/tools/mk_flow_link.py --run pr-123 --base-url https://flow-studio.example.com
```

**API interface** (importable):
```python
from swarm.tools.mk_flow_link import FlowStudioLinkGenerator

gen = FlowStudioLinkGenerator(base_url="http://localhost:5000")

# Generate link to run
url = gen.link(run="health-check")

# Generate link to flow
url = gen.link(run="pr-123", flow="build", mode="operator")

# Generate link to step
url = gen.link(run="pr-123", flow="gate", step="merge_decision", view="artifacts")

# Generate link with tab selection
url = gen.link(run="pr-123", flow="gate", step="merge_decision", tab="run")
```

**Implementation details**:

**Class: `FlowStudioLinkGenerator`**
- Constructor: `__init__(base_url="http://localhost:5000", repo_root=None)`
- Method: `link(run, flow=None, step=None, mode=None, view=None, tab=None) -> str`
- Method: `validate_params(flow, step) -> bool` - Check flow/step exist in catalog
- Method: `get_available_flows() -> list[str]` - List valid flow keys
- Method: `get_flow_steps(flow_key) -> list[str]` - List steps for a flow

**Validation logic**:
- If `step` provided, `flow` must be provided
- If `tab` provided, `step` must be provided
- `flow` must be valid (signal/plan/build/gate/deploy/wisdom)
- `step` must exist in the specified flow (read from `swarm/config/flows/*.yaml`)
- `mode` must be `author` or `operator` if specified
- `view` must be `agents` or `artifacts` if specified

**Error handling**:
- Invalid parameters → print error + exit 1
- Missing flow config files → warning + proceed (graceful degradation)

**Output formats**:
- Default: plain URL to stdout
- `--json`: `{"url": "...", "params": {...}}`
- `--verbose`: URL + parameter breakdown

---

### 2. Integrate with `validate_swarm.py`

**File**: `swarm/tools/validate_swarm.py`

**Change**: Add Flow Studio URLs to JSON output for flow/step/agent issues

**Current JSON structure** (from `build_detailed_json_output`):
```json
{
  "version": "1.0.0",
  "summary": {...},
  "agents": {
    "agent-key": {
      "checks": {...},
      "has_issues": true,
      "issues": [...]
    }
  },
  "flows": {
    "flow-key": {
      "checks": {...},
      "has_issues": true,
      "issues": [...]
    }
  },
  "steps": {
    "flow:step": {
      "checks": {...},
      "has_issues": true,
      "issues": [...]
    }
  }
}
```

**Proposed enhancement**:
Add `flow_studio_url` field to each flow/step with issues:

```json
{
  "flows": {
    "build": {
      "checks": {...},
      "has_issues": true,
      "flow_studio_url": "http://localhost:5000/?mode=operator&flow=build&view=artifacts",
      "issues": [...]
    }
  },
  "steps": {
    "gate:merge_decision": {
      "checks": {...},
      "has_issues": true,
      "flow_studio_url": "http://localhost:5000/?mode=operator&flow=gate&step=merge_decision&tab=run",
      "issues": [...]
    }
  }
}
```

**Implementation**:
1. Import `FlowStudioLinkGenerator` in `validate_swarm.py`
2. In `build_detailed_json_output()`, after building `flows_data` and `steps_data`:
   - For each flow with issues, add `flow_studio_url` field
   - For each step with issues, add `flow_studio_url` field
3. Use `mode=operator` and `view=artifacts` by default for operator-focused links

**CLI flag** (optional):
```bash
# Generate validation report with Flow Studio links
uv run swarm/tools/validate_swarm.py --json --flow-studio-base http://localhost:5000
```

---

### 3. PR Comment Template for `gh-reporter`

**File**: `.claude/agents/gh-reporter.md`

**Enhancement**: Add Flow Studio link generation to PR/issue comments

**Example PR comment** (template):

````markdown
## Swarm SDLC Summary for `pr-123-abc123`

**Run Status**: [View in Flow Studio](http://localhost:5000/?mode=operator&run=pr-123-abc123)

### Flow Progress

| Flow | Status | Decision | Link |
|------|--------|----------|------|
| Signal | ✅ Done | ✅ requirements_decision.md | [View](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=signal) |
| Plan | ✅ Done | ✅ work_plan.md | [View](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=plan) |
| Build | ⚠️ Partial | ⏳ Missing | [View](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=build&view=artifacts) |
| Gate | ❌ Not Started | — | [View](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=gate) |
| Deploy | ❌ Not Started | — | [View](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=deploy) |
| Wisdom | ❌ Not Started | — | [View](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=wisdom) |

### Issues Detected

**Build Flow** - 2 required artifacts missing
- [View details in Flow Studio](http://localhost:5000/?mode=operator&run=pr-123-abc123&flow=build&view=artifacts)
- Missing: `test_summary.md`, `build_receipt.json`

**Next Steps**:
1. Complete Build flow artifacts
2. Run Gate flow for pre-merge validation
3. Review receipts in Flow Studio

---
*Inspect locally*: Start Flow Studio with `make flow-studio`, then visit the links above.
````

**Implementation approach**:
1. `gh-reporter` agent uses `RunInspector` to get run status
2. Uses `mk_flow_link.py` to generate URLs
3. Generates markdown table with per-flow links
4. Adds artifact-level links for flows with issues

**Agent prompt update**:
Add to `gh-reporter.md`:

```markdown
## Flow Studio Integration

When reporting run status, include Flow Studio deep links:

1. **Run-level link**: `http://localhost:5000/?mode=operator&run={run_id}`
2. **Flow-level links**: `...&flow={flow_key}&view=artifacts` for each flow
3. **Step-level links**: `...&flow={flow}&step={step_id}&tab=run` for steps with issues

Use `swarm.tools.mk_flow_link.FlowStudioLinkGenerator` to generate URLs.

Template:
- Table with flow status + "View" links
- Issue section with deep links to affected flows/steps
- Footer with instruction to start Flow Studio locally
```

---

### 4. Testing

**File**: `tests/test_mk_flow_link.py`

**Test cases**:

1. **URL generation** - Basic parameters
   ```python
   def test_generate_basic_run_link():
       gen = FlowStudioLinkGenerator()
       url = gen.link(run="health-check")
       assert url == "http://localhost:5000/?run=health-check"
   ```

2. **URL generation** - Full parameters
   ```python
   def test_generate_full_link():
       gen = FlowStudioLinkGenerator()
       url = gen.link(
           run="pr-123",
           flow="gate",
           step="merge_decision",
           mode="operator",
           view="artifacts",
           tab="run"
       )
       assert "mode=operator" in url
       assert "flow=gate" in url
       assert "step=merge_decision" in url
   ```

3. **Validation** - Invalid step without flow
   ```python
   def test_validation_step_without_flow():
       gen = FlowStudioLinkGenerator()
       with pytest.raises(ValueError):
           gen.link(run="pr-123", step="foo")
   ```

4. **Validation** - Invalid flow
   ```python
   def test_validation_invalid_flow():
       gen = FlowStudioLinkGenerator()
       with pytest.raises(ValueError):
           gen.link(run="pr-123", flow="invalid")
   ```

5. **CLI** - JSON output
   ```python
   def test_cli_json_output():
       result = subprocess.run(
           ["uv", "run", "swarm/tools/mk_flow_link.py", "--run", "test", "--json"],
           capture_output=True,
           text=True
       )
       data = json.loads(result.stdout)
       assert "url" in data
       assert data["params"]["run"] == "test"
   ```

---

### 5. Documentation

**Files to update**:

1. **DEMO_RUN.md** - Add section on Flow Studio deep links
   ```markdown
   ## Flow Studio Deep Links

   Generate shareable URLs for runs:

   ```bash
   # Link to a run
   uv run swarm/tools/mk_flow_link.py --run health-check

   # Link to specific flow with artifacts view
   uv run swarm/tools/mk_flow_link.py --run health-check --flow build --view artifacts
   ```

   Use in CI/PR workflows to provide direct links to artifacts.
   ```

2. **swarm/tools/README.md** (new file) - Tool catalog
   ```markdown
   # Swarm Tools

   ## mk_flow_link.py

   Generate Flow Studio deep links for CI/PR integration.

   **Usage**:
   ```bash
   uv run swarm/tools/mk_flow_link.py --run <run-id> [options]
   ```

   **Options**:
   - `--run` - Run ID (required)
   - `--flow` - Flow key (signal/plan/build/gate/deploy/wisdom)
   - `--step` - Step ID within flow
   - `--mode` - Mode (author/operator)
   - `--view` - View mode (agents/artifacts)
   - `--tab` - Tab in step details (spec/run/artifacts)
   - `--base-url` - Base URL (default: http://localhost:5000)
   - `--json` - Output as JSON
   ```

3. **CLAUDE.md** - Add to "Essential Commands" section
   ```markdown
   ### Flow Studio Deep Links

   Generate URLs for sharing run/flow/step state:

   ```bash
   uv run swarm/tools/mk_flow_link.py --run <run-id> --flow <flow> --step <step>
   ```
   ```

---

## Implementation Order

1. ✅ **Phase 1**: Create `mk_flow_link.py` CLI tool
   - Core `FlowStudioLinkGenerator` class
   - CLI interface with all parameters
   - Validation logic
   - JSON output mode

2. ✅ **Phase 2**: Add tests
   - URL generation tests
   - Validation tests
   - CLI integration tests

3. ✅ **Phase 3**: Integrate with `validate_swarm.py`
   - Add `flow_studio_url` to JSON output
   - CLI flag for custom base URL

4. ✅ **Phase 4**: Update `gh-reporter` agent
   - Add Flow Studio link generation to prompt
   - PR comment template with table + links

5. ✅ **Phase 5**: Documentation
   - Update DEMO_RUN.md
   - Create swarm/tools/README.md
   - Update CLAUDE.md

---

## Design Decisions

### Why a separate CLI tool?

- **Composability**: Can be used standalone, imported, or piped
- **Single responsibility**: URL generation is orthogonal to validation/reporting
- **Testability**: Isolated logic, easy to test
- **Reusability**: Any tool can import `FlowStudioLinkGenerator`

### Why not extend validate_swarm directly?

- `validate_swarm.py` already has a focused purpose (validation)
- Link generation is a presentation concern, not validation
- Separation of concerns: validation logic stays pure

### Why integrate with validate_swarm JSON output?

- Validation results are often consumed by CI/reporting tools
- Adding URLs to JSON output makes it actionable
- No CLI changes needed (backward compatible)

### Base URL handling

Default to `http://localhost:5000` because:
- Flow Studio is a local dev tool (not deployed by default)
- Users running Flow Studio locally can click links immediately
- CI/PR comments include instruction to start Flow Studio

For deployments:
- Support `--base-url` flag
- Environment variable: `FLOW_STUDIO_BASE_URL`

---

## Success Criteria

1. ✅ CLI tool can generate valid Flow Studio URLs
2. ✅ All URL parameters supported (mode, run, flow, step, view, tab)
3. ✅ Validation detects invalid flow/step combinations
4. ✅ JSON output mode for machine consumption
5. ✅ Tests cover URL generation and validation logic
6. ✅ `validate_swarm.py` JSON output includes `flow_studio_url` fields
7. ✅ `gh-reporter` can generate PR comments with Flow Studio links
8. ✅ Documentation updated with usage examples

---

## Example Workflows

### Developer debugging a failed build

```bash
# Run validation, get JSON with Flow Studio URLs
uv run swarm/tools/validate_swarm.py --json | jq -r '.flows.build.flow_studio_url'

# Open URL in browser to inspect artifacts
```

### CI/PR integration

```bash
# Generate link for PR comment
RUN_ID="pr-${PR_NUMBER}-${COMMIT_SHA:0:7}"
LINK=$(uv run swarm/tools/mk_flow_link.py --run "$RUN_ID" --mode operator)

# Post to PR comment
gh pr comment $PR_NUMBER --body "View run in Flow Studio: $LINK"
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

# Open in browser and inspect
```

---

## Files to Create

1. `swarm/tools/mk_flow_link.py` (new)
2. `tests/test_mk_flow_link.py` (new)
3. `swarm/tools/README.md` (new)

## Files to Modify

1. `swarm/tools/validate_swarm.py` (integrate URLs)
2. `.claude/agents/gh-reporter.md` (add template)
3. `DEMO_RUN.md` (add section)
4. `CLAUDE.md` (add command)

---

## Notes

- **Performance**: URL generation is fast (< 10ms), no network calls
- **Dependencies**: None (stdlib only, uses `urllib.parse`)
- **Backward compatibility**: No breaking changes to existing tools
- **Deployment**: Works locally (default) and can be configured for remote Flow Studio
- **Validation**: Uses existing flow config YAML as source of truth
