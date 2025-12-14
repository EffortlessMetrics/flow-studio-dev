# Flow Studio - Swarm Visualization & Interactive Editor

Flow Studio is a local web UI for visualizing and editing the swarm's flow architecture and agent configuration. It provides a graphical interface to understand flows, steps, agents, and their relationships—and allows safe, guided editing of configuration files.

> **Note**: As of v2.2, Flow Studio uses FastAPI exclusively. The legacy Flask backend has been archived. If you're using `templates/flowstudio-only`, this does not affect you—that template continues to use Flask independently.

## Quick Start

### 1. Start the Server

```bash
make flow-studio
# or
uv run swarm/tools/flow_studio_fastapi.py
```

Then open **http://localhost:5000** in your browser.

### 2. Explore the UI

- **Left sidebar**: Lists all flows (Signal, Plan, Build, Gate, Deploy, Wisdom)
- **Center graph**: Shows flows → steps → agents as a visual DAG
- **Right panel**: Details about selected flow, step, or agent

Click any node in the graph to see its details and available edits.

### 3. Edit Agent Models

When you click an agent, the right panel shows:

- Agent metadata (category, color, short role)
- **Model selector** dropdown (inherit / haiku / sonnet / opus)
- Which flows/steps use this agent
- File path to edit manually

To change an agent's model:

1. Click the agent in the graph
2. Select a new model from the dropdown
3. Click **Save**
4. Flow Studio updates `swarm/config/agents/<key>.yaml`
5. A prompt tells you to run: `make gen-adapters && make validate-swarm`

### 4. Reorder Flow Steps (Future: v2)

Drag-and-drop reordering is built into the API but not yet exposed in the UI. For now, edit `swarm/config/flows/<key>.yaml` directly and reorder the `steps:` array.

## Architecture

### Files

- **Source of truth**: `swarm/config/flows/*.yaml` and `swarm/config/agents/*.yaml`
- **UI**: Single-page app served from FastAPI (no build step needed)
- **API**: FastAPI backend with REST endpoints

### Key Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Main UI HTML |
| GET | `/api/health` | Health check |
| GET | `/api/flows` | List all flows |
| GET | `/api/flows/<key>` | Get flow detail (steps, agents) |
| GET | `/api/agents` | List all agents |
| GET | `/api/graph` | Full graph data for visualization |
| POST | `/api/agents/<key>/model` | Change agent model |
| POST | `/api/flows/<key>/steps/reorder` | Reorder steps in a flow |

### Response Examples

**GET /api/agents**
```json
[
  {
    "key": "clarifier",
    "category": "shaping",
    "color": "yellow",
    "model": "inherit",
    "flows": ["signal", "plan", "build", "gate", "deploy", "wisdom"],
    "shortRole": "Detect ambiguities, draft clarification questions"
  },
  ...
]
```

**POST /api/agents/clarifier/model**
```json
{
  "success": true,
  "agent": "clarifier",
  "new_model": "sonnet"
}
```

## Workflow Examples

### Change an Agent's Model

```bash
# Start Flow Studio
make flow-studio

# In the browser:
# 1. Click an agent (e.g., "clarifier") in the graph
# 2. Select "sonnet" from the Model dropdown
# 3. Click "Save"
# 4. See confirmation: "✓ Model updated to sonnet"
# 5. Copy the command shown and run it:
#    make gen-adapters && make validate-swarm
```

### View Which Flows Use an Agent

```bash
# In Flow Studio:
# 1. Click an agent
# 2. See "Used In" section showing all flows and steps
# Example: clarifier is used in:
#   - signal.normalize
#   - plan.kickoff
#   - build.kickoff
#   - gate.assess
#   - deploy.monitor
#   - wisdom.analyze
```

### Understand Flow Structure

```bash
# In Flow Studio:
# 1. Click a flow (e.g., "Build") in the sidebar
# 2. See the full flow graph: Build → 12 steps → agents per step
# 3. Click a step (e.g., "author_tests") to see:
#    - Which agents run in that step
#    - Step description (role)
#    - File to edit: swarm/config/flows/build.yaml
```

### Find All Agents in a Category

```bash
# Example: Find all "verification" agents
# Method 1 (UI): Look for blue badges (color = blue for verification)
# Method 2 (CLI):
make agents-models | grep verification
```

## Configuration Guide

### Adding a New Agent

1. Create `swarm/config/agents/<key>.yaml`:
   ```yaml
   key: my-new-agent
   flows:
     - signal
   category: shaping
   color: yellow
   source: project/user
   short_role: "One-line description of what this agent does"
   model: inherit
   ```

2. Register in `swarm/AGENTS.md`:
   ```markdown
   | my-new-agent | signal | shaping | yellow | project/user | One-line description |
   ```

3. Update `swarm/config/flows/signal.yaml` to add the agent to a step:
   ```yaml
   steps:
     - id: normalize
       agents:
         - signal-normalizer
         - my-new-agent  # Add here
   ```

4. Regenerate and validate:
   ```bash
   make gen-adapters
   make validate-swarm
   ```

5. Refresh Flow Studio (browser reload)

### Reordering Flow Steps

Currently, reorder steps by editing `swarm/config/flows/<key>.yaml` directly:

```yaml
steps:
  - id: step-1
    agents: [agent-a]
    role: "First step description"
  - id: step-2  # Swap these two...
    agents: [agent-b]
    role: "Second step description"
```

Then regenerate and validate:
```bash
make gen-flows
make validate-swarm
```

(Drag-and-drop reordering in the UI is planned for v2.)

## Troubleshooting

### Port 5000 Already in Use

```bash
# Use a custom port
PORT=8000 make flow-studio
# or
PORT=8000 uv run swarm/tools/flow_studio.py

# Then open http://localhost:8000
```

### Changes Don't Appear in UI

Flow Studio reads from `swarm/config/flows/` and `swarm/config/agents/` each time you request an endpoint. If you edit files directly (outside the UI):

1. Refresh the browser (Ctrl+R or Cmd+R)
2. The UI will reload fresh data from disk

### Agent or Flow Not Found

- Ensure the YAML file exists in `swarm/config/agents/` or `swarm/config/flows/`
- Ensure the `key:` field in the YAML matches the filename (without `.yaml`)
- Run `make validate-swarm` to check for misalignment

### Graph Not Rendering

Flow Studio uses **Cytoscape.js** (loaded from CDN). If you're offline:

1. Edit `swarm/tools/flow_studio_fastapi.py`
2. Find the line: `<script src="https://cdn.jsdelivr.net/npm/cytoscape@3.25.0/dist/cytoscape.min.js"></script>`
3. Download and serve locally, or provide offline bundle

## Design Philosophy

Flow Studio is intentionally **read-mostly with light editing**:

- **View**: See flows, steps, agents, relationships instantly
- **Edit**: Change agent models safely with validation feedback
- **Educate**: Inspect the graph to understand swarm architecture
- **Minimal**: No drag-drop complexity (yet). Edit YAML for major changes.

The config files remain the authoritative source. Flow Studio is a **guided window** into those files, not a competing configuration interface.

## Advanced Usage

### Scripting / API

Flow Studio provides a REST API. You can script edits:

```bash
# Change clarifier model to sonnet
curl -X POST http://localhost:5000/api/agents/clarifier/model \
  -H "Content-Type: application/json" \
  -d '{"model": "sonnet"}'

# Reorder build flow steps
curl -X POST http://localhost:5000/api/flows/build/steps/reorder \
  -H "Content-Type: application/json" \
  -d '{"step_ids": ["kickoff", "auth_tests", "auth_code", ...]}'
```

### Integration with CI/CD

Flow Studio can be used in CI to validate changes:

```bash
# In a pre-commit hook or CI workflow
python3 swarm/tools/flow_studio.py &
SERVER_PID=$!
sleep 2

# Validate endpoints
curl -f http://localhost:5000/api/health || exit 1

kill $SERVER_PID
```

### Extending the UI

To add features to the UI:

1. Edit the HTML template in `swarm/tools/flow_studio_fastapi.py`
2. Add new JavaScript functions (see `showAgentDetails()` for examples)
3. Add new API endpoints: Add route decorators like `@app.get()` in `flow_studio_fastapi.py`
4. Restart Flow Studio and test

## Roadmap

- **v0.2** (current): Model editing, basic validation
- **v1.0**: Drag-reorder steps in UI, live validation feedback
- **v2.0**: Add new agents in UI, export flow diagrams
- **v3.0**: Import flows from other repos, sync with git

## Contributing

To improve Flow Studio:

1. File an issue describing the improvement
2. Fork, create a branch
3. Edit `swarm/tools/flow_studio_fastapi.py` (backend and HTML template)
4. Test with `make flow-studio`
5. Submit a PR with before/after screenshots

See `CONTRIBUTING.md` for full contribution guidelines.

---

**Questions?** Check `CLAUDE.md` § Agent Ops for more on managing the swarm.
