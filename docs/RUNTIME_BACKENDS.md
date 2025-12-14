# Runtime Backends

> For: Developers integrating with Flow Studio's runtime system or adding new execution backends.

> **You are here:** Technical reference for the runtime layer. Coming from:
> [Flow Studio](./FLOW_STUDIO.md) | Jump to:
> [Flow Studio API](./FLOW_STUDIO_API.md)

**See also:**
- [FLOW_STUDIO.md](./FLOW_STUDIO.md) - UI documentation
- [CLAUDE.md](../CLAUDE.md) - Repository overview

The runtime system provides a unified interface for executing swarm flows across
different backends. Flow Studio, CLI, and other consumers use the `RunService`
to start runs, track progress, and query results without knowing which backend
is handling execution.

---

## Overview

The runtime architecture consists of four core components:

### RunService

The central singleton that coordinates run execution. All consumers should use
`RunService` rather than calling backends directly.

```python
from swarm.runtime import RunService

service = RunService.get_instance()
run_id = service.start_run(spec)
summary = service.get_run(run_id)
```

### RunSpec

Specification for starting a new run. Captures the intent of what should be
executed.

```python
from swarm.runtime import RunSpec

spec = RunSpec(
    flow_keys=["signal", "plan"],  # Flows to execute
    profile_id="baseline",          # Optional profile from profile_registry
    backend="claude-harness",       # Which backend to use
    initiator="flow-studio",        # Source: "cli", "flow-studio", "api", "ci"
    params={"title": "My Run"},     # Backend-specific parameters
)
```

### RunSummary

Comprehensive view of a run's current state, including status, timing, errors,
and artifacts.

```python
@dataclass
class RunSummary:
    id: RunId                        # Unique run identifier
    spec: RunSpec                    # Original specification
    status: RunStatus                # pending, running, succeeded, failed, canceled
    sdlc_status: SDLCStatus          # ok, warning, error, unknown
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]   # When execution began
    completed_at: Optional[datetime] # When execution finished
    error: Optional[str]             # Error message if failed
    artifacts: Dict[str, Any]        # Produced artifacts by flow/step
    is_exemplar: bool                # Teaching example flag
    tags: List[str]                  # Categorization tags
```

### RunEvent

A single event in a run's timeline, enabling streaming updates and audit trails.

```python
@dataclass
class RunEvent:
    run_id: RunId
    ts: datetime
    kind: str        # Event type (see Event Lifecycle below)
    flow_key: str
    step_id: Optional[str]
    agent_key: Optional[str]
    payload: Dict[str, Any]
```

---

## Available Backends

| ID | Label | Description |
|----|-------|-------------|
| `claude-harness` | Claude Code CLI | Default backend; wraps existing Make targets and Claude CLI commands |
| `gemini-cli` | Gemini CLI (flow) | Executes entire flows via single Gemini CLI invocations with streaming JSONL output |
| `gemini-step-orchestrator` | Gemini CLI (stepwise) | Uses `GeminiStepOrchestrator` for step-by-step execution with context handoff |
| `claude-agent-sdk` | Claude Agent SDK | Future implementation - not yet available |

### Backend Capabilities

Each backend reports its capabilities via `BackendCapabilities`:

```python
@dataclass
class BackendCapabilities:
    id: BackendId
    label: str
    supports_streaming: bool   # Can stream events in real-time
    supports_events: bool      # Emits structured events
    supports_cancel: bool      # Runs can be cancelled mid-execution
    supports_replay: bool      # Past runs can be replayed
```

**Capability Matrix:**

| Backend | Streaming | Events | Cancel | Replay |
|---------|-----------|--------|--------|--------|
| `claude-harness` | No | Yes | Yes | No |
| `gemini-cli` | Yes | Yes | Yes | No |
| `gemini-step-orchestrator` | Yes | Yes | Yes | No |
| `claude-agent-sdk` | Yes | Yes | Yes | Yes |

---

## Environment Variables

### Gemini CLI Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SWARM_GEMINI_STUB` | `1` | Enable stub mode (simulated JSONL output). Set to `0` for real CLI |
| `SWARM_GEMINI_CLI` | `gemini` | Path to the Gemini CLI binary |

**Example: Using real Gemini CLI**

```bash
export SWARM_GEMINI_STUB=0
export SWARM_GEMINI_CLI=/usr/local/bin/gemini
make flow-studio
```

**Stub Mode Behavior:**

When `SWARM_GEMINI_STUB=1` (default) or the Gemini CLI is not on PATH, the
backend generates simulated JSONL events for testing:

```json
{"type": "init", "backend": "gemini-cli", "flow": "signal"}
{"type": "text", "message": "Starting flow signal"}
{"type": "tool_use", "tool": "read", "input": {"path": "swarm/flows/flow-signal.md"}}
{"type": "tool_result", "tool": "read", "success": true}
{"type": "result", "flow": "signal", "status": "complete"}
```

This allows CI and development environments to test the runtime without
requiring Gemini CLI installation.

---

## Event Lifecycle

Runs progress through a defined event sequence. The `kind` field of `RunEvent`
indicates the event type.

### Standard Run Lifecycle

```text
run_created -> run_started -> [flow_start -> flow_end]* -> run_completed
```

| Event Kind | Description |
|------------|-------------|
| `run_created` | Run initialized, metadata persisted |
| `run_started` | Execution began |
| `flow_start` | A flow began execution |
| `flow_end` | A flow completed successfully |
| `flow_error` | A flow failed |
| `run_completed` | Run finished (success or failure) |
| `run_canceled` | Run was canceled |

### Stepwise Orchestrator Lifecycle

When using `GeminiStepOrchestrator`, additional step-level events are emitted:

```text
run_created -> run_started -> flow_start ->
  [step_start -> step_end]* ->
flow_end -> run_completed
```

| Event Kind | Description |
|------------|-------------|
| `step_start` | A step began execution |
| `step_end` | A step completed successfully |
| `step_error` | A step failed |

### Gemini CLI Event Mapping

The Gemini CLI emits JSONL events that are mapped to `RunEvent` kinds:

| Gemini Event | RunEvent Kind | Description |
|--------------|---------------|-------------|
| `init` | `backend_init` | Session initialization |
| `message` | `assistant_message` / `user_message` | Text output (role-based) |
| `tool_use` | `tool_start` | Tool invocation started |
| `tool_result` | `tool_end` | Tool invocation completed |
| `error` | `error` | Error occurred |
| `result` | `step_complete` | Final completion result |
| `text` | `log` | Legacy text output (stub mode) |

---

## TOML Commands vs Backend Prompts

There are two ways to invoke Gemini for Swarm flows, serving different use cases:

### 1. Interactive CLI (Human Use)

**Location:** `.gemini/commands/swarm/*.toml`

TOML command files are optimized for human operators using the Gemini CLI
interactively from the terminal.

```bash
gemini /swarm/signal my-run-id
gemini /swarm/build feature-123
```

**Example TOML command** (`.gemini/commands/swarm/signal.toml`):

```toml
description = "Execute Swarm Flow 1 (Signal): normalize input, frame problem, author requirements"

prompt = """
You are executing Swarm Flow 1 (Signal -> Specs) for the demo-swarm system.

## Context
- Flow spec: @{swarm/flows/flow-signal.md}
- Run artifacts will be written to: swarm/runs/{{args}}/signal/

## Your Tasks
1. Read the flow spec to understand the steps
2. For each step in the flow...
"""
```

**Characteristics:**
- Uses `@{}` file references for context injection
- Uses `{{args}}` for runtime parameter substitution
- Human-readable prompts with help text
- Designed for interactive terminal sessions

### 2. Programmatic Backend (Flow Studio Use)

**Location:** `swarm/runtime/backends.py`

Backend prompts are generated programmatically for machine-driven execution
via Flow Studio's runtime.

```python
def _build_prompt(self, flow_key: str, run_id: RunId, spec: RunSpec) -> str:
    return f'''You are the Gemini CLI backend executing a Swarm flow step.

Flow: {flow_key}
Run ID: {run_id}
...
'''
```

**Characteristics:**
- Direct CLI invocation with `--output-format stream-json`
- Explicit `run_id` injection
- Structured event streaming for UI consumption
- No file references (context passed inline or via instructions)

### Why the Separation?

| Aspect | TOML Commands | Backend Prompts |
|--------|---------------|-----------------|
| **Audience** | Human operators | Flow Studio / API |
| **Ergonomics** | Readable prompts, help text | Structured output, event streaming |
| **Context** | `@{}` file references | Inline instructions |
| **Output** | Interactive terminal | JSONL for parsing |
| **Invocation** | `gemini /swarm/<flow>` | Subprocess with `--prompt` |

---

## Adding a New Backend

To add a new backend, implement the `RunBackend` abstract base class:

### Step 1: Define the Backend Class

```python
# swarm/runtime/backends.py

class MyCustomBackend(RunBackend):
    """Custom backend implementation."""

    @property
    def id(self) -> BackendId:
        return "my-custom"  # Add to BackendId type

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            id="my-custom",
            label="My Custom Backend",
            supports_streaming=True,
            supports_events=True,
            supports_cancel=True,
            supports_replay=False,
        )

    def start(self, spec: RunSpec) -> RunId:
        """Start a run. Returns immediately with run ID."""
        run_id = generate_run_id()
        # ... initialize run state ...
        # ... spawn background execution ...
        return run_id

    def get_summary(self, run_id: RunId) -> Optional[RunSummary]:
        """Get current summary for a run."""
        return storage.read_summary(run_id)

    def list_summaries(self) -> List[RunSummary]:
        """List all known runs."""
        # ... implementation ...

    def get_events(self, run_id: RunId) -> List[RunEvent]:
        """Get all events for a run."""
        return storage.read_events(run_id)

    def cancel(self, run_id: RunId) -> bool:
        """Cancel a running run. Returns True if cancelled."""
        # ... implementation ...
```

### Step 2: Update the Backend Registry

```python
# swarm/runtime/backends.py

_BACKEND_REGISTRY: dict[BackendId, type[RunBackend]] = {
    "claude-harness": ClaudeHarnessBackend,
    "claude-agent-sdk": AgentSDKBackend,
    "gemini-cli": GeminiCliBackend,
    "my-custom": MyCustomBackend,  # Add your backend
}
```

### Step 3: Update the BackendId Type

```python
# swarm/runtime/types.py

BackendId = Literal[
    "claude-harness",
    "claude-agent-sdk",
    "gemini-cli",
    "gemini-step-orchestrator",
    "my-custom",  # Add your backend ID
    "custom-cli",
]
```

### Step 4: Register with RunService

```python
# swarm/runtime/service.py

class RunService:
    def __init__(self, repo_root: Optional[Path] = None):
        self._backends: dict[BackendId, RunBackend] = {
            "claude-harness": ClaudeHarnessBackend(self._repo_root),
            "gemini-cli": GeminiCliBackend(self._repo_root),
            "my-custom": MyCustomBackend(self._repo_root),  # Add your backend
        }
```

### Step 5: Write Tests

```python
# tests/test_my_custom_backend.py

class TestMyCustomBackend:
    def test_capabilities(self):
        backend = MyCustomBackend()
        caps = backend.capabilities()
        assert caps.id == "my-custom"
        assert caps.supports_streaming is True

    def test_start_returns_run_id(self, monkeypatch):
        backend = MyCustomBackend()
        spec = RunSpec(flow_keys=["build"], backend="my-custom", initiator="test")
        run_id = backend.start(spec)
        assert run_id.startswith("run-")
```

---

## Storage Layout

Runs are persisted to disk under `swarm/runs/<run-id>/`:

```text
swarm/runs/run-20251208-143022-abc123/
  meta.json        # RunSummary serialized as JSON
  spec.json        # RunSpec serialized as JSON
  events.jsonl     # Append-only event log (one JSON object per line)
  signal/          # Flow 1 artifacts
  plan/            # Flow 2 artifacts
  build/           # Flow 3 artifacts
  gate/            # Flow 4 artifacts
  deploy/          # Flow 5 artifacts
  wisdom/          # Flow 6 artifacts
```

The storage module (`swarm/runtime/storage.py`) provides utilities for reading
and writing run state.

---

## API Integration

Flow Studio exposes runtime functionality via REST API:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/backends` | GET | List available backends and capabilities |
| `POST /api/run` | POST | Start a new run |
| `GET /api/runs` | GET | List runs |
| `GET /api/runs/<id>` | GET | Get run summary |
| `GET /api/runs/<id>/events` | GET | Get run events |
| `POST /api/runs/<id>/cancel` | POST | Cancel a running run |

See [FLOW_STUDIO_API.md](./FLOW_STUDIO_API.md) for complete API reference.

---

## See Also

- **[FLOW_STUDIO.md](./FLOW_STUDIO.md)**: UI documentation
- **[FLOW_STUDIO_API.md](./FLOW_STUDIO_API.md)**: REST API reference
- **[CLAUDE.md](../CLAUDE.md)**: Repository overview
- **[swarm/runtime/](../swarm/runtime/)**: Source code
