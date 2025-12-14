# Runbook: UI Layout Review

**Branch**: `docs/flowstudio-ux-handover`

## Goal

Run a per-screen UX layout review for Flow Studio and produce structured artifacts for human/agent critique. This runbook coordinates the UX Critic -> UX Implementer workflow to systematically review and improve Flow Studio screens.

## Constraints

- Flow Studio should be running for best results (automatic fallback to manifest if not)
- MCP servers must be configured in `~/.config/claude/mcp.json` for agent workflows
- Reviews produce JSON critiques conforming to `swarm/schemas/ux_critique.schema.json`
- Implementer changes are limited to governed file paths (see `ux_repo` allowlist)

## Invariants (Don't Break These)

1. `layout_spec.ts` is the source of truth for screen definitions
2. `ux_manifest.json` binds layout spec + docs + tests together
3. SDK contract (`window.__flowStudio`) remains stable during review
4. UIID selectors (`data-uiid`) must not be renamed without updating tests

## Prerequisites

Install dependencies:

```bash
uv sync --extra dev
# For screenshots and SDK state capture:
uv add playwright && playwright install chromium
```

Configure MCP servers in `~/.config/claude/mcp.json` (for agent workflows):

```jsonc
{
  "mcpServers": {
    "ux_spec": {
      "command": "uv",
      "args": ["run", "python", "-m", "swarm.tools.mcp_ux_spec"],
      "cwd": "/path/to/flow-studio"
    },
    "ux_review": {
      "command": "uv",
      "args": ["run", "python", "-m", "swarm.tools.mcp_ux_review"],
      "cwd": "/path/to/flow-studio"
    },
    "ux_repo": {
      "command": "uv",
      "args": ["run", "python", "-m", "swarm.tools.mcp_ux_repo"],
      "cwd": "/path/to/flow-studio"
    }
  }
}
```

## Quick Start: Running a Full UX Pass

### Option A: With Flow Studio Running (Recommended)

```bash
# 1. Start Flow Studio
make flow-studio

# 2. Run layout review (captures all screens)
uv run swarm/tools/run_layout_review.py

# 3. Check output
ls -la swarm/runs/ui-review/
```

### Option B: Using Manifest Fallback (No Server Required)

```bash
# Uses ux_manifest.json fallback screens
uv run swarm/tools/run_layout_review.py --use-manifest
```

### Option C: HTTP-Only Mode (No Playwright)

```bash
# Skips screenshots and SDK state extraction
uv run swarm/tools/run_layout_review.py --no-playwright
```

## What Gets Captured

For each screen defined in `layout_spec.ts`:

| Artifact | Description | Capture Method |
|----------|-------------|----------------|
| `dom.html` | Rendered HTML after `data-ui-ready="ready"` | Playwright (fallback: HTTP) |
| `state.json` | SDK state from `window.__flowStudio` | Playwright JS execution |
| `screenshot.png` | Visual capture of the screen | Playwright |
| `screen_spec.json` | Screen metadata (id, route, title, description) | API or manifest |

### SDK State Contents

When Playwright is available, `state.json` includes:

```json
{
  "state": { /* getState() result */ },
  "graphState": { /* getGraphState() result */ },
  "layoutScreens": [ /* getLayoutScreens() result */ ],
  "allUIIDs": [ /* getAllKnownUIIDs() result */ ],
  "sdkVersion": "captured-via-playwright"
}
```

## Technical Steps (Full Workflow)

### Step 1: Validate environment

```bash
uv sync --extra dev
make dev-check
make demo-run
```

All checks should pass before proceeding.

### Step 2: Start Flow Studio

```bash
make flow-studio
```

Verify it's running: `http://localhost:5000/?run=demo-health-check&mode=operator`

### Step 3: Run layout review to capture DOM state

```bash
uv run swarm/tools/run_layout_review.py
```

This visits all screens from `layout_spec.ts` and captures:
- DOM structure (waits for `data-ui-ready="ready"`)
- SDK state snapshots (via `window.__flowStudio`)
- Screenshots (if Playwright available)

Outputs go to: `swarm/runs/ui-review/<timestamp>/`

### Step 4: Generate agent prompts

List available screens:

```bash
uv run python -m swarm.tools.ux_orchestrator --list-screens
```

Generate prompts for a specific screen:

```bash
uv run python -m swarm.tools.ux_orchestrator --screen flows.default
```

Or generate prompts for all screens:

```bash
uv run python -m swarm.tools.ux_orchestrator --all
```

### Step 5: Run UX Critic agent

1. Open Claude Code with `ux-critic` agent selected
2. Paste the Critic prompt from `ux_orchestrator` output
3. Let it call `ux_spec` + `ux_review` MCP tools
4. Agent produces a JSON critique conforming to `ux_critique.schema.json`
5. Save the critique to `swarm/runs/ux-critique/<timestamp>/<screen_id>.json`

### Step 6: Run UX Implementer agent

1. Open Claude Code with `ux-implementer` agent selected
2. Paste the Implementer prompt stub + the Critic JSON
3. Let it:
   - Call `get_write_allowlist` from `ux_repo`
   - Read/write files via `ux_repo` tools
   - Run `run_ux_tests` to validate changes
4. Collect `pr_title`, `pr_body`, and touched files from agent output
5. Create a PR with the suggested changes

### Step 7: Validate and merge

```bash
make dev-check
uv run pytest tests/test_flow_studio_*.py -v
```

If all tests pass, the PR is ready for human review.

## Success Criteria

1. `run_layout_review.py` completes without errors for all screens
2. `ux_orchestrator` generates valid prompts for at least `flows.default` screen
3. UX Critic produces a JSON critique that validates against `ux_critique.schema.json`
4. UX Implementer successfully applies at least one fix
5. All Flow Studio tests pass after changes
6. PR created and merged for at least one screen review

## Output Structure

### Layout review artifacts

```text
swarm/runs/ui-review/<timestamp>/
  summary.json           # Run summary with all screens and status
  flows.default/
    dom.html             # Rendered DOM (after data-ui-ready)
    state.json           # SDK state (getState, getGraphState, etc.)
    screenshot.png       # Visual capture
    screen_spec.json     # Screen metadata
    screenshot.skip      # (if screenshot not captured)
  flows.selftest/
    ...
  flows.shortcuts/
    ...
  flows.validation/
    ...
  flows.tour/
    ...
```

### Summary.json format

```json
{
  "run_id": "20241207-143025",
  "timestamp": "2024-12-07T14:30:25Z",
  "base_url": "http://localhost:5000",
  "screens": [
    {
      "id": "flows.default",
      "route": "/",
      "has_dom": true,
      "has_state": true,
      "has_screenshot": true,
      "errors": []
    }
  ]
}
```

### Interpreting Results

| Indicator | Meaning |
|-----------|---------|
| `has_dom: true` | DOM captured successfully |
| `has_state: true` | SDK state extracted via Playwright |
| `has_screenshot: true` | Visual capture available |
| `errors: []` | No issues during capture |
| `errors: [...]` | Warnings/errors (check for Playwright issues) |

### Critique artifacts

```text
swarm/runs/ux-critique/<timestamp>/
  <screen_id>.json     # Structured critique (JSON)
```

### Implementation artifacts

```text
swarm/runs/ux-patches/<timestamp>/
  <screen_id>/
    summary.json       # What was changed
    pr_body.md         # PR description
```

## Troubleshooting

### "Flow Studio not reachable"

```bash
# Start the server
make flow-studio

# Or use manifest fallback
uv run swarm/tools/run_layout_review.py --use-manifest
```

### "Playwright not installed"

```bash
uv add playwright
playwright install chromium
```

### "Timeout waiting for data-ui-ready"

The UI is taking too long to initialize. Check:
1. Flow Studio server is healthy: `curl http://localhost:5000/api/health`
2. No JavaScript errors in browser console
3. Network connectivity to the server

### "SDK state extraction failed"

The `window.__flowStudio` SDK is not exposed. Check:
1. TypeScript is compiled: `make ts-build`
2. SDK is properly initialized in the page

## Dependencies

- `v0.5.0-flowstudio` or later (layout spec, SDK methods)
- httpx (required for HTTP capture)
- playwright (optional, for screenshots and SDK state)
- Python 3.11+
- Node.js for TypeScript compilation (if modifying `layout_spec.ts`)

## Files to Modify

- `swarm/tools/flow_studio_ui/src/layout_spec.ts` — screen definitions
- `swarm/tools/flow_studio_ui/src/*.ts` — UI implementation
- `swarm/tools/flow_studio_ui/css/*.css` — styling

## Files to Create

- `swarm/runs/ui-review/<timestamp>/` — review artifacts
- `swarm/runs/ux-critique/<timestamp>/` — critique JSON files
- `swarm/runs/ux-patches/<timestamp>/` — implementation summaries

## Related Resources

- `docs/FLOW_STUDIO.md` — Flow Studio overview and governed surfaces
- `docs/FLOW_STUDIO_UX_HANDOVER.md` — UX system context and handover
- `swarm/schemas/ux_critique.schema.json` — critique JSON schema
- `ux_manifest.json` (repo root) — UX manifest binding specs, docs, tests, and tools
- `swarm/tools/flow_studio_ui/src/layout_spec.ts` — Authoritative screen definitions
