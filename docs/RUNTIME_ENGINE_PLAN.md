# Runtime Engine Architecture Plan

**Status**: Draft
**Goal**: Make Claude less opaque to the runtime; put Claude and Gemini on the same conceptual rails.

---

## Current State

### What We Have

1. **Backends Architecture** (`swarm/runtime/backends.py`):
   - `RunBackend` ABC with: `start()`, `get_summary()`, `list_summaries()`, `get_events()`, `cancel()`
   - `ClaudeHarnessBackend` — wraps Make/CLI, runs in background thread
   - `GeminiCliBackend` — calls Gemini CLI with JSONL, maps to `RunEvent`
   - `GeminiStepwiseBackend` — delegates to `GeminiStepOrchestrator` for step-by-step

2. **Gemini Step Orchestrator** (`swarm/runtime/orchestrator.py`):
   - Iterates through flow steps from `FlowRegistry`
   - Separate Gemini CLI call per step with context handoff
   - Emits `step_start`, `step_end` events per step

3. **Storage** (`swarm/runtime/storage.py`):
   - `meta.json`, `spec.json`, `events.jsonl` per run
   - Thread-safe locking

4. **Claude Slash Commands** (`.claude/commands/flow-*.md`):
   - Pure prompt-based orchestration inside Claude Code
   - Agents write artifacts to `RUN_BASE/<flow>/`
   - **No structured transcript or events** — runtime only sees "footprints"

### The Problem

Claude flows produce artifacts, but the runtime cannot see:
- What prompts were sent to Claude
- What Claude actually said (LLM messages)
- Tool calls and their results
- Step boundaries and timing
- Structured step receipts

This makes Claude a "black box" compared to Gemini stepwise, which emits rich events.

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Flow Studio / RunService                  │
│                 (Unified view of all runs)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     StepOrchestrator                         │
│          (Generic: walks flows/steps, calls engine)          │
└─────────────────────────────────────────────────────────────┘
              │                              │
              ▼                              ▼
┌─────────────────────┐        ┌─────────────────────────────┐
│   GeminiStepEngine  │        │     ClaudeStepEngine        │
│   (Gemini CLI)      │        │  (Claude Agent SDK)         │
│                     │        │  + Level 2 subagents        │
└─────────────────────┘        └─────────────────────────────┘
              │                              │
              ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Shared Run Ledger                         │
│   RUN_BASE: meta.json, spec.json, events.jsonl, artifacts   │
└─────────────────────────────────────────────────────────────┘
```

**Key insight**: The orchestrator owns "which step to run"; the engine owns "how to run it".

---

## Phase 1: Claude Recording (No Behavior Change)

Make Claude flows visible to the runtime without changing how they're orchestrated.

### 1A. LLM Transcript Format

Define a standard format for "what the LLM actually said" per step.

**File location**:
```
RUN_BASE/<flow_key>/llm/<step_id>-<agent_key>-<engine>.jsonl
```

**Example**:
```
swarm/runs/abc123/build/llm/3.4-code-implementer-claude.jsonl
```

**Schema** (JSONL, one line per message):
```jsonc
{"ts": "2025-12-08T20:01:00Z", "type": "system", "content": "..."}
{"ts": "2025-12-08T20:01:01Z", "type": "user", "content": "..."}
{"ts": "2025-12-08T20:01:03Z", "type": "assistant", "content": "...", "tool_calls": [...]}
{"ts": "2025-12-08T20:01:05Z", "type": "tool", "name": "bash", "input": "...", "output": "..."}
```

**Step Receipt** (JSON summary):
```
RUN_BASE/<flow_key>/receipts/<step_id>-<agent_key>.json
```

```json
{
  "engine": "claude",
  "agent_key": "code-implementer",
  "flow_key": "build",
  "step_id": "3.4",
  "status": "VERIFIED",
  "summary": "Implemented feature X with 3 new functions",
  "concerns": [],
  "next_actions": []
}
```

### 1B. Event Recorder CLI Tool

Create a Python CLI tool Claude flows can call to emit structured `RunEvent`s.

**File**: `swarm/tools/record_event.py`

```python
#!/usr/bin/env python3
"""Record a RunEvent from Claude flows into the runtime event stream."""

import argparse
import json
from datetime import datetime, timezone

from swarm.runtime.types import RunEvent
from swarm.runtime import storage

def main() -> None:
    parser = argparse.ArgumentParser(description="Record a RunEvent")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--flow-key", required=True)
    parser.add_argument("--step-id", required=False)
    parser.add_argument("--agent-key", required=False)
    parser.add_argument("--kind", required=True, help="Event kind (step_start, step_end, critic_result, etc.)")
    parser.add_argument("--payload-file", required=False, help="JSON file with event payload")
    parser.add_argument("--payload", required=False, help="Inline JSON payload")
    args = parser.parse_args()

    payload = {}
    if args.payload_file:
        with open(args.payload_file, "r", encoding="utf-8") as f:
            payload = json.load(f)
    elif args.payload:
        payload = json.loads(args.payload)

    event = RunEvent(
        run_id=args.run_id,
        ts=datetime.now(timezone.utc),
        kind=args.kind,
        flow_key=args.flow_key,
        step_id=args.step_id,
        agent_key=args.agent_key,
        payload=payload,
    )

    storage.append_event(args.run_id, event)
    print(f"Recorded event: {args.kind} for {args.run_id}")


if __name__ == "__main__":
    main()
```

**Usage from Claude flows**:

```bash
# Step start
uv run swarm/tools/record_event.py \
  --run-id "$RUN_ID" \
  --flow-key "build" \
  --step-id "author_tests" \
  --kind "step_start"

# Critic result
printf '{"status": "UNVERIFIED", "can_further_iteration_help": true}' > /tmp/critic.json
uv run swarm/tools/record_event.py \
  --run-id "$RUN_ID" \
  --flow-key "build" \
  --step-id "author_tests" \
  --agent-key "test-critic" \
  --kind "critic_result" \
  --payload-file /tmp/critic.json

# Step complete
uv run swarm/tools/record_event.py \
  --run-id "$RUN_ID" \
  --flow-key "build" \
  --step-id "author_tests" \
  --kind "step_complete"
```

### 1C. Flow Studio Transcript API

Add endpoint to serve transcripts.

**Endpoint**: `GET /api/runs/{run_id}/flows/{flow_key}/steps/{step_id}/transcript`

```python
@app.get("/api/runs/{run_id}/flows/{flow_key}/steps/{step_id}/transcript")
def get_step_transcript(run_id: str, flow_key: str, step_id: str) -> dict:
    path = storage.find_run_path(run_id)
    if not path:
        raise HTTPException(status_code=404, detail="Run not found")

    # Look for transcript files matching step_id
    llm_dir = path / flow_key / "llm"
    if not llm_dir.exists():
        raise HTTPException(status_code=404, detail="No transcripts")

    # Find matching file (pattern: <step_id>-*-*.jsonl)
    transcripts = list(llm_dir.glob(f"{step_id}-*.jsonl"))
    if not transcripts:
        raise HTTPException(status_code=404, detail="Transcript not found")

    messages = []
    with transcripts[0].open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                messages.append(json.loads(line))

    return {
        "run_id": run_id,
        "flow_key": flow_key,
        "step_id": step_id,
        "messages": messages
    }
```

---

## Phase 2: StepEngine Abstraction

Extract a generic engine interface from `GeminiStepOrchestrator`.

### 2A. StepEngine Interface

**File**: `swarm/runtime/engines.py`

```python
"""Step engine abstraction for pluggable LLM backends."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable

from .types import RunEvent, RunSpec


@dataclass
class StepContext:
    """Context provided to an engine for executing a step."""
    repo_root: Path
    run_id: str
    flow_key: str
    step_id: str
    step_index: int
    spec: RunSpec
    # Flow/step metadata
    flow_title: str
    step_role: str
    step_agents: tuple[str, ...]
    # Previous step outputs for context building
    history: list[dict[str, Any]]


@dataclass
class StepResult:
    """Result of executing a single step."""
    step_id: str
    status: str  # "succeeded" | "failed" | "skipped"
    output: str  # Summary text
    error: str | None = None
    duration_ms: int = 0
    artifacts: dict[str, Any] | None = None


class StepEngine(ABC):
    """Abstract engine that executes a single step."""

    @property
    @abstractmethod
    def engine_id(self) -> str:
        """Unique identifier for this engine (e.g., 'gemini-step', 'claude-step')."""
        ...

    @abstractmethod
    def run_step(self, ctx: StepContext) -> tuple[StepResult, Iterable[RunEvent]]:
        """Execute a step and return result + events.

        Args:
            ctx: Step execution context including flow/step metadata and history.

        Returns:
            Tuple of (StepResult, iterable of RunEvents produced during execution).
        """
        ...
```

### 2B. GeminiStepEngine

Refactor existing Gemini step execution logic into the engine interface.

```python
class GeminiStepEngine(StepEngine):
    """Step engine using Gemini CLI."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.gemini_cmd = os.environ.get("SWARM_GEMINI_CLI", "gemini")
        self.stub_mode = os.environ.get("SWARM_GEMINI_STUB", "1") == "1"
        self.cli_available = shutil.which(self.gemini_cmd) is not None

    @property
    def engine_id(self) -> str:
        return "gemini-step"

    def run_step(self, ctx: StepContext) -> tuple[StepResult, Iterable[RunEvent]]:
        events: list[RunEvent] = []

        # Build prompt from context
        prompt = self._build_prompt(ctx)

        # Execute (stub or real)
        if self.stub_mode or not self.cli_available:
            output = f"[STUB] Step {ctx.step_id} completed"
            result = StepResult(
                step_id=ctx.step_id,
                status="succeeded",
                output=output,
            )
            return result, events

        # Real execution via Gemini CLI
        # ... (existing _run_gemini_step logic, yielding events)
        ...
```

### 2C. Generic StepOrchestrator

```python
class StepOrchestrator:
    """Generic orchestrator that walks flows/steps using a StepEngine."""

    def __init__(
        self,
        engine: StepEngine,
        flow_registry: FlowRegistry,
        repo_root: Path,
    ):
        self.engine = engine
        self.flow_registry = flow_registry
        self.repo_root = repo_root

    def execute_flow(
        self,
        run_id: str,
        flow_key: str,
        spec: RunSpec,
        start_step: str | None = None,
        end_step: str | None = None,
    ) -> None:
        """Execute a flow step-by-step using the configured engine."""
        flow_def = self.flow_registry.get_flow(flow_key)
        if not flow_def:
            raise ValueError(f"Unknown flow: {flow_key}")

        steps = self._filter_steps(flow_def.steps, start_step, end_step)
        history: list[dict[str, Any]] = []

        for step in steps:
            ctx = StepContext(
                repo_root=self.repo_root,
                run_id=run_id,
                flow_key=flow_key,
                step_id=step.id,
                step_index=step.index,
                spec=spec,
                flow_title=flow_def.title,
                step_role=step.role,
                step_agents=step.agents,
                history=history,
            )

            result, events = self.engine.run_step(ctx)

            # Record events
            for event in events:
                storage.append_event(run_id, event)

            # Update history for next step
            history.append({
                "step_id": result.step_id,
                "status": result.status,
                "output": result.output,
                "error": result.error,
            })

            if result.status == "failed":
                break
```

---

## Phase 3: Claude Stepwise Engine

Enable "level 2 subagents" — each step gets its own Claude orchestrator thread.

### 3A. ClaudeStepEngine

```python
class ClaudeStepEngine(StepEngine):
    """Step engine using Claude Agent SDK.

    Each step execution creates a new Claude "thread" that can:
    - Use tools (bash, read, write, etc.)
    - Call subagents (level 2 subagents) as needed
    - Write artifacts directly to RUN_BASE
    """

    def __init__(self, repo_root: Path, config: dict[str, Any] | None = None):
        self.repo_root = repo_root
        self.config = config or {}

    @property
    def engine_id(self) -> str:
        return "claude-step"

    def run_step(self, ctx: StepContext) -> tuple[StepResult, Iterable[RunEvent]]:
        events: list[RunEvent] = []

        # Build system + user prompts
        system_prompt = self._build_system_prompt(ctx)
        user_prompt = self._build_user_prompt(ctx)

        # Initialize Claude thread for this step
        # (Using Claude Agent SDK or similar)
        try:
            thread = self._create_thread(system_prompt, ctx)

            # Stream messages and map to events
            for msg in thread.stream(user_prompt):
                event = self._map_message_to_event(ctx, msg)
                if event:
                    events.append(event)

            result = StepResult(
                step_id=ctx.step_id,
                status="succeeded",
                output=f"Step {ctx.step_id} completed",
            )

        except Exception as e:
            result = StepResult(
                step_id=ctx.step_id,
                status="failed",
                output="",
                error=str(e),
            )

        return result, events

    def _create_thread(self, system_prompt: str, ctx: StepContext):
        """Create a Claude thread with appropriate tools.

        Tools may include a 'call_agent' tool for level 2 subagents.
        """
        # Implementation depends on Claude Agent SDK
        ...
```

### 3B. ClaudeStepwiseBackend

```python
class ClaudeStepwiseBackend(RunBackend):
    """Backend using StepOrchestrator with ClaudeStepEngine."""

    @property
    def id(self) -> BackendId:
        return "claude-step-orchestrator"

    def __init__(self, repo_root: Path | None = None):
        self._repo_root = repo_root or Path(__file__).resolve().parents[2]
        self._flow_registry = FlowRegistry.get_instance()
        self._engine = ClaudeStepEngine(self._repo_root)
        self._orchestrator = StepOrchestrator(
            self._engine,
            self._flow_registry,
            self._repo_root,
        )

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            id="claude-step-orchestrator",
            label="Claude (stepwise)",
            supports_streaming=True,
            supports_events=True,
            supports_cancel=True,
            supports_replay=False,
        )

    def start(self, spec: RunSpec) -> RunId:
        # Same pattern as GeminiStepwiseBackend
        run_id = generate_run_id()
        # ... create run, spawn thread calling self._orchestrator.execute_flow
        ...
```

---

## Phase 4: Mixed Backends (Optional)

Enable per-flow or per-step engine selection.

### Config Extension

```yaml
# swarm/config/backends.yaml
default_engine: gemini-step

per_flow:
  signal: claude-step
  plan: claude-step
  build: claude-step
  gate: gemini-step
  deploy: gemini-step
  wisdom: gemini-step
```

### RunSpec Extension

```python
@dataclass
class RunSpec:
    flow_keys: list[str]
    profile_id: str | None = None
    backend: BackendId = "claude-harness"
    initiator: str = "cli"
    params: dict[str, Any] = field(default_factory=dict)
    # NEW: Per-flow engine overrides
    flow_engines: dict[str, str] | None = None  # e.g., {"build": "claude-step"}
```

### Orchestrator Engine Selection

```python
def execute_flow(self, run_id: str, flow_key: str, spec: RunSpec, ...):
    # Select engine based on per-flow config or default
    engine = self._default_engine
    if spec.flow_engines and flow_key in spec.flow_engines:
        engine_id = spec.flow_engines[flow_key]
        engine = self._engines[engine_id]

    # ... proceed with selected engine
```

---

## Implementation Sequence

### Week 1: Phase 1 (Claude Recording)

1. **Day 1-2**: Define transcript/receipt format, add `record_event.py`
2. **Day 3**: Add transcript endpoint to Flow Studio API
3. **Day 4-5**: Wire event recording into 1-2 Claude flow commands (e.g., flow-3-build)

### Week 2: Phase 2 (StepEngine Abstraction)

1. **Day 1-2**: Create `engines.py` with `StepEngine`, `StepContext`, `StepResult`
2. **Day 3-4**: Extract `GeminiStepEngine` from existing orchestrator
3. **Day 5**: Create generic `StepOrchestrator`, update `GeminiStepwiseBackend`

### Week 3+: Phase 3 (Claude Stepwise)

1. Implement minimal `ClaudeStepEngine` for one flow
2. Add `ClaudeStepwiseBackend` to registry
3. Test with signal or plan flow

### Later: Phase 4 (Mixed Backends)

Only if needed — may be sufficient to select backend at run level.

---

## Documentation Updates

### CLAUDE.md Additions

```markdown
## Execution Engines & Orchestrators

Two ways flows execute:

1. **Claude-native (slash commands)** — orchestrated inside Claude Code
   - `/flow-*` commands drive flows and microloops
   - Agents write to `swarm/runs/<run-id>/<flow>/...`
   - Runtime records events via `record_event.py`

2. **Runtime backends (Gemini & Claude stepwise)**
   - Orchestrated by Python (`RunService` + backends)
   - Engines execute one step at a time
   - All runs share ledger: `meta.json`, `events.jsonl`, artifacts

Flow Studio shows the same shape regardless of backend.
```

### New: LLM_TRANSCRIPTS.md

Document the transcript format contract for all engines.

---

## Success Criteria

1. **Phase 1 Complete When**:
   - Claude flows emit `step_start`/`step_end` events visible in Flow Studio
   - At least one flow writes LLM transcripts viewable in UI

2. **Phase 2 Complete When**:
   - `GeminiStepwiseBackend` uses `StepOrchestrator` + `GeminiStepEngine`
   - Existing tests pass, behavior unchanged

3. **Phase 3 Complete When**:
   - `claude-step-orchestrator` appears in `/api/backends`
   - Can execute one flow (e.g., signal) with Claude stepwise
   - Events appear in Flow Studio timeline

---

## Open Questions

1. **Claude Agent SDK availability**: Which SDK/API will we use for Claude step execution?
2. **Level 2 subagent tool**: Should `call_agent` be a tool, or just rely on Claude's native agent calling?
3. **Transcript verbosity**: Should we record all messages or summarize?
4. **Cross-process safety**: Do we need file locking for concurrent Claude processes?
