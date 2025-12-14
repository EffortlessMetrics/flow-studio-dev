# Config Phase 1: Step Engine Profiles

> **Status**: Design Draft (v2.4.0 Target)
> **Created**: December 2025
> **Author**: System
> **Related**: [STEPWISE_BACKENDS.md](./STEPWISE_BACKENDS.md), [flow_registry.py](../swarm/config/flow_registry.py), [orchestrator.py](../swarm/runtime/orchestrator.py)

---

## Problem Statement

The `StepDefinition` dataclass in `flow_registry.py` currently lacks:

1. **Engine profile configuration**: No way to specify which LLM/mode to use per step
2. **CLI support for resuming**: No tool for resuming failed runs from a checkpoint

This limits flexibility for:

- Running expensive steps with opus, cheap steps with haiku
- Resuming failed runs from the last successful checkpoint
- A/B testing different engines on the same flow
- Cost optimization (use stub mode for some steps, real LLM for others)

### Current State

Today, engine selection happens at the backend level, not the step level:

```python
# Current: Engine is backend-scoped, not step-scoped
backend = get_backend("claude-step-orchestrator")
run_id = backend.start(spec)
```

The `StepDefinition` dataclass has no awareness of engines:

```python
@dataclass
class StepDefinition:
    id: str
    index: int
    agents: Tuple[str, ...]
    role: str
    teaching_notes: Optional[TeachingNotes] = None
    routing: Optional[StepRouting] = None
    # No engine_profile field
```

---

## Goals

1. **Add `engine_profile` field to `StepDefinition`**: Enable per-step engine configuration
2. **Create CLI tool for step-level resume**: `stepwise_resume.py` for checkpoint recovery
3. **Document profiles in YAML config**: Extend flow YAML schema with engine profiles

---

## Non-Goals

- **Runtime profile switching**: Profiles are static per run; no dynamic switching mid-step
- **Multi-tenant profile management**: No user-scoped or team-scoped profile storage
- **Profile inheritance chains**: No hierarchical profile composition (step < flow < global)
- **Cost tracking per profile**: No integrated billing or token counting by profile

---

## Data Model

### EngineProfile Dataclass

A new dataclass to represent per-step engine configuration:

```python
# swarm/config/flow_registry.py

from dataclasses import dataclass
from typing import Optional

@dataclass
class EngineProfile:
    """Engine configuration for a step.

    Controls which LLM backend and mode to use when executing a step.
    Steps without an explicit profile inherit from the run-level backend.

    Attributes:
        engine: Engine identifier - "claude-step" | "gemini-step" | "stub"
        mode: Execution mode - "stub" | "sdk" | "cli"
        model: Optional model override (e.g., "claude-sonnet-4-20250514", "claude-opus-4-20250514")
        timeout_ms: Step timeout in milliseconds (default 300000 = 5 minutes)
    """
    engine: str = "claude-step"  # "claude-step" | "gemini-step" | "stub"
    mode: str = "stub"           # "stub" | "sdk" | "cli"
    model: Optional[str] = None  # Model override, None means use engine default
    timeout_ms: int = 300000     # 5 minutes default
```

### Extended StepDefinition

Update `StepDefinition` to include the optional engine profile:

```python
@dataclass
class StepDefinition:
    """A single step within a flow.

    Attributes:
        id: Unique identifier for this step within the flow
        index: 1-based position in the flow
        agents: Tuple of agent keys assigned to execute this step
        role: Description of what this step accomplishes
        teaching_notes: Optional teaching metadata for stepwise execution
        routing: Optional routing configuration for non-linear flow execution
        engine_profile: Optional engine configuration for this step
    """
    id: str
    index: int  # 1-based within flow
    agents: Tuple[str, ...]
    role: str
    teaching_notes: Optional[TeachingNotes] = None
    routing: Optional[StepRouting] = None
    engine_profile: Optional[EngineProfile] = None  # NEW
```

---

## YAML Config Schema

### Step-Level Engine Profile

Extend the flow YAML schema to support `engine_profile` on individual steps:

```yaml
# swarm/config/flows/build.yaml

steps:
  - id: load_context
    agents:
      - context-loader
    role: "Load relevant context for subtask."
    engine_profile:
      engine: claude-step
      mode: sdk
      model: claude-haiku-4-20250514  # Use haiku for cheap context loading
      timeout_ms: 60000  # 1 minute is enough for context loading
    routing:
      kind: linear
      next: author_tests

  - id: critique_code
    agents:
      - code-critic
    role: "Harsh review of code vs ADR/contracts."
    engine_profile:
      engine: claude-step
      mode: sdk
      model: claude-opus-4-20250514  # Use opus for critical review
      timeout_ms: 600000  # 10 minutes for thorough review
    routing:
      kind: microloop
      loop_target: implement
      loop_condition_field: status
      loop_success_values: ["VERIFIED", "verified"]
      next: mutate
      max_iterations: 3
```

### Flow-Level Default Profile

Optionally define a flow-level default that steps inherit:

```yaml
# swarm/config/flows/build.yaml

key: build
title: "Flow 3 - Plan -> Code (Build)"

# Flow-level default engine profile (optional)
default_engine_profile:
  engine: claude-step
  mode: stub
  timeout_ms: 300000

steps:
  - id: load_context
    # No engine_profile: inherits flow default (stub mode)
    agents:
      - context-loader
    role: "Load relevant context."

  - id: critique_code
    # Override flow default with opus for this critical step
    engine_profile:
      engine: claude-step
      mode: sdk
      model: claude-opus-4-20250514
    agents:
      - code-critic
    role: "Harsh review."
```

### Parsing Engine Profile

Update `_load_flow_steps` in `FlowRegistry` to parse engine profiles:

```python
def _load_flow_steps(
    self, flows_dir: Path, flow_key: str
) -> Tuple[Tuple[StepDefinition, ...], Tuple[str, ...]]:
    """Load steps from a per-flow YAML file."""
    flow_file = flows_dir / f"{flow_key}.yaml"

    if not flow_file.exists():
        return (), ()

    with open(flow_file) as f:
        flow_data = yaml.safe_load(f)

    # Parse flow-level default engine profile
    default_profile = None
    if "default_engine_profile" in flow_data:
        dp_data = flow_data["default_engine_profile"]
        default_profile = EngineProfile(
            engine=dp_data.get("engine", "claude-step"),
            mode=dp_data.get("mode", "stub"),
            model=dp_data.get("model"),
            timeout_ms=dp_data.get("timeout_ms", 300000),
        )

    steps: List[StepDefinition] = []
    for idx, step_data in enumerate(flow_data.get("steps", []), start=1):
        # Parse teaching_notes if present
        teaching_notes = None
        if "teaching_notes" in step_data:
            tn_data = step_data["teaching_notes"]
            teaching_notes = TeachingNotes(
                inputs=tuple(tn_data.get("inputs", [])),
                outputs=tuple(tn_data.get("outputs", [])),
                emphasizes=tuple(tn_data.get("emphasizes", [])),
                constraints=tuple(tn_data.get("constraints", [])),
            )

        # Parse routing if present
        routing = None
        if "routing" in step_data:
            r_data = step_data["routing"]
            routing = StepRouting(
                kind=r_data.get("kind", "linear"),
                next=r_data.get("next"),
                loop_target=r_data.get("loop_target"),
                loop_condition_field=r_data.get("loop_condition_field"),
                loop_success_values=tuple(r_data.get("loop_success_values", [])),
                max_iterations=r_data.get("max_iterations", 5),
                branches=r_data.get("branches", {}),
            )

        # Parse engine_profile if present (NEW)
        engine_profile = default_profile  # Inherit flow default
        if "engine_profile" in step_data:
            ep_data = step_data["engine_profile"]
            engine_profile = EngineProfile(
                engine=ep_data.get("engine", "claude-step"),
                mode=ep_data.get("mode", "stub"),
                model=ep_data.get("model"),
                timeout_ms=ep_data.get("timeout_ms", 300000),
            )

        step = StepDefinition(
            id=step_data["id"],
            index=idx,
            agents=tuple(step_data.get("agents", [])),
            role=step_data.get("role", ""),
            teaching_notes=teaching_notes,
            routing=routing,
            engine_profile=engine_profile,  # NEW
        )
        steps.append(step)

    cross_cutting = tuple(flow_data.get("cross_cutting", []))

    return tuple(steps), cross_cutting
```

---

## CLI Resume Tool

### Usage Examples

```bash
# Resume from a specific step
uv run swarm/tools/stepwise_resume.py run-20251209-143022-abc123 --from-step critique_code

# Resume from the last successful step
uv run swarm/tools/stepwise_resume.py run-20251209-143022-abc123 --from-last-success

# Dry-run: show what would be executed without running
uv run swarm/tools/stepwise_resume.py run-20251209-143022-abc123 --from-step critique_code --dry-run

# Resume with different backend (override original)
uv run swarm/tools/stepwise_resume.py run-20251209-143022-abc123 --from-step critique_code \
    --backend claude-step-orchestrator --mode sdk

# Resume and stop at a specific step
uv run swarm/tools/stepwise_resume.py run-20251209-143022-abc123 --from-step implement \
    --to-step critique_code
```

### Implementation Sketch

```python
#!/usr/bin/env python3
"""stepwise_resume.py - Resume a stepwise run from a checkpoint.

Usage:
    uv run swarm/tools/stepwise_resume.py <run_id> --from-step <step_id>
    uv run swarm/tools/stepwise_resume.py <run_id> --from-last-success
    uv run swarm/tools/stepwise_resume.py <run_id> --from-step <step_id> --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from swarm.runtime import storage
from swarm.runtime.backends import get_backend
from swarm.runtime.types import RunSpec, RunStatus


def find_last_successful_step(run_id: str) -> Optional[str]:
    """Find the last step that completed successfully.

    Args:
        run_id: The run identifier.

    Returns:
        The step_id of the last successful step, or None if no steps succeeded.
    """
    events = storage.read_events(run_id)

    last_success_step = None
    for event in events:
        if event.kind == "step_end" and event.step_id:
            # step_end means success (step_error means failure)
            last_success_step = event.step_id

    return last_success_step


def get_next_step_after(run_id: str, step_id: str) -> Optional[str]:
    """Get the step that should execute after the given step.

    Args:
        run_id: The run identifier.
        step_id: The step that completed.

    Returns:
        The next step_id to execute, or None if flow is complete.
    """
    events = storage.read_events(run_id)

    # Look for route_decision event after this step
    for event in events:
        if event.kind == "route_decision" and event.step_id == step_id:
            payload = event.payload or {}
            return payload.get("to_step")

    return None


def load_run_state(run_id: str) -> dict:
    """Load the current state of a run.

    Args:
        run_id: The run identifier.

    Returns:
        Dictionary with run metadata and status.
    """
    summary = storage.read_summary(run_id)
    spec = storage.read_spec(run_id)
    events = storage.read_events(run_id)

    return {
        "run_id": run_id,
        "status": summary.status.value if summary else "unknown",
        "flow_keys": spec.flow_keys if spec else [],
        "backend": spec.backend if spec else None,
        "event_count": len(list(events)),
        "spec": spec,
        "summary": summary,
    }


def resume_run(
    run_id: str,
    from_step: str,
    to_step: Optional[str] = None,
    backend_override: Optional[str] = None,
    mode_override: Optional[str] = None,
    dry_run: bool = False,
) -> Optional[str]:
    """Resume a run from a specific step.

    Args:
        run_id: The run to resume.
        from_step: The step ID to start from.
        to_step: Optional step ID to stop at.
        backend_override: Optional backend to use instead of original.
        mode_override: Optional mode override.
        dry_run: If True, show plan without executing.

    Returns:
        The new run_id if executed, None if dry_run.
    """
    state = load_run_state(run_id)

    if state["status"] not in ["failed", "succeeded"]:
        print(f"Warning: Run {run_id} has status '{state['status']}', not failed/succeeded")

    original_spec = state["spec"]
    if not original_spec:
        print(f"Error: Could not load spec for run {run_id}")
        return None

    # Determine backend
    backend_id = backend_override or original_spec.backend
    if not backend_id:
        backend_id = "claude-step-orchestrator"

    # Build params for resume
    resume_params = dict(original_spec.params)
    resume_params["resumed_from"] = run_id
    resume_params["resume_step"] = from_step
    if mode_override:
        resume_params["mode"] = mode_override

    print(f"\nResume Plan:")
    print(f"  Original run: {run_id}")
    print(f"  From step:    {from_step}")
    print(f"  To step:      {to_step or '(end of flow)'}")
    print(f"  Backend:      {backend_id}")
    print(f"  Flow keys:    {original_spec.flow_keys}")

    if dry_run:
        print("\n[DRY RUN] Would execute the above plan.")
        return None

    # Create new spec for resumed run
    new_spec = RunSpec(
        flow_keys=original_spec.flow_keys,
        profile_id=original_spec.profile_id,
        backend=backend_id,
        initiator="cli-resume",
        params=resume_params,
    )

    # Get backend and start run
    backend = get_backend(backend_id)

    # Use orchestrator directly for step-level control
    orchestrator = backend._get_orchestrator()

    # Execute flow(s) with start/end step
    for flow_key in original_spec.flow_keys:
        new_run_id = orchestrator.run_stepwise_flow(
            flow_key=flow_key,
            spec=new_spec,
            start_step=from_step,
            end_step=to_step,
        )
        print(f"\nStarted resumed run: {new_run_id}")
        return new_run_id

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Resume a stepwise run from a checkpoint",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Resume from specific step
    %(prog)s run-123 --from-step critique_code

    # Resume from last success
    %(prog)s run-123 --from-last-success

    # Dry run
    %(prog)s run-123 --from-step implement --dry-run
        """,
    )
    parser.add_argument("run_id", help="The run ID to resume")
    parser.add_argument(
        "--from-step",
        dest="from_step",
        help="Step ID to resume from",
    )
    parser.add_argument(
        "--from-last-success",
        dest="from_last_success",
        action="store_true",
        help="Resume from the step after the last successful step",
    )
    parser.add_argument(
        "--to-step",
        dest="to_step",
        help="Step ID to stop at (inclusive)",
    )
    parser.add_argument(
        "--backend",
        help="Override backend (e.g., claude-step-orchestrator)",
    )
    parser.add_argument(
        "--mode",
        help="Override mode (stub, sdk, cli)",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Show plan without executing",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.from_step and not args.from_last_success:
        parser.error("Must specify --from-step or --from-last-success")

    if args.from_step and args.from_last_success:
        parser.error("Cannot specify both --from-step and --from-last-success")

    # Determine start step
    from_step = args.from_step
    if args.from_last_success:
        last_success = find_last_successful_step(args.run_id)
        if not last_success:
            print(f"Error: No successful steps found in run {args.run_id}")
            sys.exit(1)
        from_step = get_next_step_after(args.run_id, last_success)
        if not from_step:
            print(f"Run {args.run_id} completed successfully, no resume needed")
            sys.exit(0)
        print(f"Last successful step: {last_success}")
        print(f"Will resume from: {from_step}")

    # Resume the run
    new_run_id = resume_run(
        run_id=args.run_id,
        from_step=from_step,
        to_step=args.to_step,
        backend_override=args.backend,
        mode_override=args.mode,
        dry_run=args.dry_run,
    )

    if new_run_id:
        print(f"\nResume started. Monitor with:")
        print(f"  tail -f swarm/runs/{new_run_id}/events.jsonl")


if __name__ == "__main__":
    main()
```

---

## Makefile Targets

Add convenience targets for resuming runs:

```makefile
# Resume stepwise run from checkpoint
stepwise-resume:
	@if [ -z "$(RUN_ID)" ]; then echo "Usage: make stepwise-resume RUN_ID=<id> STEP=<step_id>"; exit 1; fi
	@if [ -z "$(STEP)" ]; then echo "Usage: make stepwise-resume RUN_ID=<id> STEP=<step_id>"; exit 1; fi
	uv run swarm/tools/stepwise_resume.py $(RUN_ID) --from-step $(STEP)

# Resume stepwise run (dry-run mode)
stepwise-resume-dry:
	@if [ -z "$(RUN_ID)" ]; then echo "Usage: make stepwise-resume-dry RUN_ID=<id> STEP=<step_id>"; exit 1; fi
	@if [ -z "$(STEP)" ]; then echo "Usage: make stepwise-resume-dry RUN_ID=<id> STEP=<step_id>"; exit 1; fi
	uv run swarm/tools/stepwise_resume.py $(RUN_ID) --from-step $(STEP) --dry-run

# Resume from last successful step
stepwise-resume-last:
	@if [ -z "$(RUN_ID)" ]; then echo "Usage: make stepwise-resume-last RUN_ID=<id>"; exit 1; fi
	uv run swarm/tools/stepwise_resume.py $(RUN_ID) --from-last-success
```

---

## Orchestrator Integration

### Engine Selection Per Step

Update `GeminiStepOrchestrator._execute_single_step` to use step-level engine profiles:

```python
def _execute_single_step(
    self,
    run_id: RunId,
    flow_key: str,
    flow_def: FlowDefinition,
    step: StepDefinition,
    spec: RunSpec,
    history: List[Dict[str, Any]],
    routing_ctx: Optional["RoutingContext"] = None,
) -> Dict[str, Any]:
    """Execute a single step via the configured StepEngine.

    If the step has an engine_profile, use a step-specific engine.
    Otherwise, use the orchestrator's default engine.
    """
    step_start = datetime.now(timezone.utc)

    # Determine which engine to use (NEW)
    engine = self._get_engine_for_step(step)

    # Log step start with engine info
    storage_module.append_event(
        run_id,
        RunEvent(
            run_id=run_id,
            ts=step_start,
            kind="step_start",
            flow_key=flow_key,
            step_id=step.id,
            agent_key=step.agents[0] if step.agents else None,
            payload={
                "role": step.role,
                "agents": list(step.agents),
                "step_index": step.index,
                "engine": engine.engine_id,
                "engine_profile": self._serialize_profile(step.engine_profile),
            },
        ),
    )

    # ... rest of implementation uses `engine` instead of `self._engine`


def _get_engine_for_step(self, step: StepDefinition) -> StepEngine:
    """Get the appropriate engine for a step.

    Args:
        step: The step definition (may have engine_profile).

    Returns:
        StepEngine instance configured for this step.
    """
    if step.engine_profile is None:
        return self._engine  # Use orchestrator default

    profile = step.engine_profile

    # Create step-specific engine based on profile
    if profile.engine == "claude-step":
        from .engines import ClaudeStepEngine
        engine = ClaudeStepEngine(
            repo_root=self._repo_root,
            mode=profile.mode,
            model=profile.model,
        )
    elif profile.engine == "gemini-step":
        from .engines import GeminiStepEngine
        engine = GeminiStepEngine(
            repo_root=self._repo_root,
            stub_mode=(profile.mode == "stub"),
        )
    elif profile.engine == "stub":
        from .engines import StubStepEngine
        engine = StubStepEngine(repo_root=self._repo_root)
    else:
        # Unknown engine, fall back to default
        return self._engine

    return engine


def _serialize_profile(self, profile: Optional[EngineProfile]) -> Optional[dict]:
    """Serialize engine profile for event payload."""
    if profile is None:
        return None
    return {
        "engine": profile.engine,
        "mode": profile.mode,
        "model": profile.model,
        "timeout_ms": profile.timeout_ms,
    }
```

---

## Implementation Phases

### Phase A: Add EngineProfile Dataclass

**Files**: `swarm/config/flow_registry.py`

1. Add `EngineProfile` dataclass
2. Add `engine_profile` field to `StepDefinition`
3. Update type hints and docstrings
4. No behavior change yet

**Estimated effort**: 0.5 days

### Phase B: Parse engine_profile from YAML

**Files**: `swarm/config/flow_registry.py`

1. Update `_load_flow_steps` to parse `engine_profile`
2. Support flow-level `default_engine_profile`
3. Add validation for known engine names
4. Add tests for YAML parsing

**Estimated effort**: 1 day

### Phase C: Wire Orchestrator to Use Profiles

**Files**: `swarm/runtime/orchestrator.py`, `swarm/runtime/engines.py`

1. Add `_get_engine_for_step()` method
2. Update `_execute_single_step()` to use step-specific engines
3. Add engine profile to step events
4. Add tests for per-step engine selection

**Estimated effort**: 1.5 days

### Phase D: Create stepwise_resume.py

**Files**: `swarm/tools/stepwise_resume.py`, `Makefile`

1. Implement CLI tool with argparse
2. Add `find_last_successful_step()` function
3. Add `resume_run()` function
4. Add Makefile targets
5. Add tests for resume functionality

**Estimated effort**: 1 day

### Phase E: Tests and Documentation

**Files**: `tests/`, `docs/`

1. Add unit tests for `EngineProfile` parsing
2. Add integration tests for per-step engines
3. Add tests for stepwise_resume.py
4. Update STEPWISE_BACKENDS.md with profile documentation
5. Update CLAUDE.md extension points section

**Estimated effort**: 1 day

**Total estimated effort**: 5 days

---

## Open Questions

### 1. Should profiles be inheritable?

**Question**: Should step inherit from flow, flow from global default?

**Current proposal**: Single level inheritance (step inherits from flow default).

**Alternative**: Three-level inheritance chain:
```
global default -> flow default -> step override
```

**Recommendation**: Start with single-level (flow default). Add global defaults in a future phase if needed.

### 2. How to handle profile validation?

**Question**: What happens with unknown engine names in YAML?

**Options**:
- Fail validation at load time (strict)
- Warn and use default engine (permissive)
- Fail at step execution time (late validation)

**Recommendation**: Fail at load time with clear error message. Unknown engines are likely typos.

### 3. Should resume create new run_id or append?

**Question**: When resuming, should we create a fresh run or continue the existing one?

**Options**:
- **New run_id**: Clean separation, easy to compare original vs resumed
- **Append to existing**: Single run_id, but events.jsonl may have gaps

**Recommendation**: Create new run_id with `resumed_from` in params. This keeps run history clean and auditable.

### 4. How to handle timeout_ms in profiles?

**Question**: Should timeout be enforced at the orchestrator level or engine level?

**Options**:
- Orchestrator enforces timeout (kills step after timeout_ms)
- Engine respects timeout (passes to underlying LLM API)
- Both (orchestrator as safety limit, engine as soft limit)

**Recommendation**: Engine respects timeout, orchestrator has a higher safety limit (2x engine timeout).

---

## Validation Contract

Add profile validation to `validate_swarm.py`:

```python
def validate_engine_profile(profile: dict, step_id: str, flow_key: str) -> List[str]:
    """Validate an engine profile definition.

    Args:
        profile: The engine_profile dict from YAML.
        step_id: The step ID for error messages.
        flow_key: The flow key for error messages.

    Returns:
        List of validation errors (empty if valid).
    """
    errors = []

    valid_engines = {"claude-step", "gemini-step", "stub"}
    valid_modes = {"stub", "sdk", "cli"}

    engine = profile.get("engine", "claude-step")
    if engine not in valid_engines:
        errors.append(
            f"FR-006: {flow_key}/{step_id} has unknown engine '{engine}' "
            f"(valid: {valid_engines})"
        )

    mode = profile.get("mode", "stub")
    if mode not in valid_modes:
        errors.append(
            f"FR-006: {flow_key}/{step_id} has unknown mode '{mode}' "
            f"(valid: {valid_modes})"
        )

    timeout_ms = profile.get("timeout_ms", 300000)
    if not isinstance(timeout_ms, int) or timeout_ms <= 0:
        errors.append(
            f"FR-006: {flow_key}/{step_id} has invalid timeout_ms '{timeout_ms}' "
            f"(must be positive integer)"
        )

    return errors
```

---

## See Also

- [flow_registry.py](../swarm/config/flow_registry.py) - StepDefinition and flow loading
- [orchestrator.py](../swarm/runtime/orchestrator.py) - Stepwise execution logic
- [engines.py](../swarm/runtime/engines.py) - StepEngine implementations
- [STEPWISE_BACKENDS.md](./STEPWISE_BACKENDS.md) - Stepwise execution documentation
- [VALIDATION_RULES.md](./VALIDATION_RULES.md) - Validation rules reference

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2025-12 | Draft | Initial design document |
