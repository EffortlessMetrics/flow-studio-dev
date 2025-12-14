# swarm/meta/

Machine-readable metadata for Flow Studio and tooling.

## Files

### artifact_catalog.json

Defines expected artifacts per flow/step. Used by:
- Flow Studio for run status overlay
- run_inspector.py for artifact status checks
- Validation tooling for artifact completeness

Structure:
```json
{
  "flows": {
    "<flow_key>": {
      "title": "Flow N - Name",
      "decision_artifact": "filename.md",
      "steps": {
        "<step_id>": {
          "required": ["file1.md"],
          "optional": ["file2.md"],
          "note": "Optional explanation"
        }
      }
    }
  }
}
```

## Usage

```python
from swarm.tools.run_inspector import RunInspector

inspector = RunInspector()

# List available runs
runs = inspector.list_runs()

# Get SDLC bar for a run
bar = inspector.get_sdlc_bar("health-check")

# Get step status
status = inspector.get_step_status("health-check", "build", "self_review")

# Get full run summary
summary = inspector.get_run_summary("health-check")
```

## CLI

```bash
# List runs
uv run python swarm/tools/run_inspector.py --list

# Show SDLC bar
uv run python swarm/tools/run_inspector.py --run health-check --sdlc-bar

# Inspect a flow
uv run python swarm/tools/run_inspector.py --run health-check --flow build --json

# Inspect a step
uv run python swarm/tools/run_inspector.py --run health-check --flow build --step self_review
```
