# Long-Running Harnesses for Agent SDLC

> For: External audiences (talks, blog posts, handoffs) wanting to understand how Anthropic's long-running agent patterns map to a real implementation.
>
> **Prerequisites:** [FLOW_STUDIO.md](./FLOW_STUDIO.md), [RUNTIME_BACKENDS.md](./RUNTIME_BACKENDS.md)

---

## Introduction

Long-running LLM agents face three core challenges:

1. **State persistence**: How does an agent maintain context across extended execution?
2. **Observability**: How do operators see what the agent is doing and has done?
3. **Control**: How can execution be paused, resumed, or corrected mid-flight?

Traditional single-call LLM interactions solve none of these. A 30-second API call either succeeds or fails; there is no intermediate visibility. For extended workflows (builds, deployments, multi-step verifications), this opacity is unacceptable.

The demo-swarm addresses this by implementing **stepwise execution**: breaking flows into discrete steps, making one LLM call per step, and persisting state between calls. This document maps Anthropic's recommended patterns for effective long-running agent harnesses to our implementation.

---

## Anthropic Pattern Mapping

### Initializer Agents: Signal and Plan Flows

Anthropic recommends **initializer agents** that set up context, frame the problem, and establish constraints before coding begins. These agents should load heavy context upfront (20-50k tokens) because "compute is cheap; reducing downstream re-search saves attention."

**Signal Flow (Flow 1)** maps to this pattern:

```
signal-normalizer -> problem-framer -> requirements-author <-> requirements-critic -> bdd-author -> scope-assessor
```

The Signal flow transforms raw input (ticket, PR description, user request) into structured specs:

| Agent | Role | Output |
|-------|------|--------|
| `signal-normalizer` | Parse raw input, find related context | `issue_normalized.md`, `context_brief.md` |
| `problem-framer` | Synthesize into clear problem statement | `problem_statement.md` |
| `requirements-author` | Write testable requirements | `requirements.md` |
| `requirements-critic` | Verify completeness and feasibility | `requirements_critique.md` |
| `bdd-author` | Turn requirements into scenarios | `features/*.feature` |
| `scope-assessor` | Estimate effort, identify risks | `scope_estimate.md`, `early_risks.md` |

**Plan Flow (Flow 2)** continues initialization:

```
impact-analyzer -> design-optioneer -> adr-author -> interface-designer -> ... -> work-planner
```

This produces ADRs, API contracts, test strategies, and work breakdown. By the time coding starts, the agent has:

- Loaded 20-50k tokens of relevant context
- Framed the problem with clear success criteria
- Established architectural constraints
- Identified risks and stakeholders
- Created a work plan with subtasks

This heavy upfront investment reduces downstream iteration and prevents the classic "agent goes off in the wrong direction for 20 minutes" failure mode.

### Coding Agents: Build Flow with Microloops

Anthropic recommends **coding agents** that iterate via adversarial loops: a writer produces artifacts, a critic reviews them, and the loop continues until verification passes or the critic explicitly judges that further iteration cannot help.

**Build Flow (Flow 3)** implements this pattern with two primary microloops:

**Test Microloop:**
```
test-author <-> test-critic
```

The orchestrator:
1. Calls `test-author` to write/update tests
2. Calls `test-critic` to review
3. If `test-critic.status == UNVERIFIED` with `can_further_iteration_help: yes`, routes back to `test-author`
4. If `test-critic.status == VERIFIED` or `can_further_iteration_help: no`, proceeds

**Code Microloop:**
```
code-implementer <-> code-critic
```

Same pattern: implement, critique, iterate until VERIFIED or no viable fix path.

**Key insight**: Agents do not know they are looping. They simply:
- Read inputs
- Write outputs
- Set status (VERIFIED / UNVERIFIED / BLOCKED)
- Optionally suggest `recommended_next`

The **orchestrator** interprets these signals and decides routing. This separation of concerns keeps agents simple and composable.

### QA/Verification Agents: Gate Flow

Anthropic recommends **verification agents** that audit artifacts, enforce policies, and make go/no-go decisions. These agents should not fix substantive issues; they verify and report.

**Gate Flow (Flow 4)** implements this pattern:

```
receipt-checker -> contract-enforcer -> security-scanner -> coverage-enforcer -> gate-fixer -> merge-decider
```

| Agent | Role | Scope |
|-------|------|-------|
| `receipt-checker` | Verify build receipt exists and is complete | Read-only audit |
| `contract-enforcer` | Check API changes vs contracts | Read-only verification |
| `security-scanner` | Run SAST, secret scans | Read-only security audit |
| `coverage-enforcer` | Verify coverage thresholds | Read-only coverage audit |
| `gate-fixer` | **Mechanical fixes only** | Lint, format, docstrings, typos |
| `merge-decider` | Synthesize checks into decision | MERGE / BOUNCE / ESCALATE |

**gate-fixer scope is intentionally narrow**: it can fix lint errors and missing docstrings but cannot change logic, tests, or APIs. Substantive issues trigger a BOUNCE back to Build or Plan.

This enforces the principle that verification agents should not become "Build 2.0"--they audit the gravity well's shape, not fill it in.

---

## Architecture

```
                        +----------------+
                        |  Flow Studio   |  (UI)
                        +-------+--------+
                                |
                                v
                        +----------------+
                        |  RunService    |  (singleton coordinator)
                        +-------+--------+
                                |
            +-------------------+-------------------+
            |                   |                   |
            v                   v                   v
    +--------------+    +--------------+    +--------------+
    | Claude       |    | Gemini       |    | Gemini       |
    | Harness      |    | CLI          |    | Stepwise     |
    | Backend      |    | Backend      |    | Backend      |
    +--------------+    +--------------+    +------+-------+
                                                   |
                                                   v
                                           +----------------+
                                           | Orchestrator   |  (GeminiStepOrchestrator)
                                           +-------+--------+
                                                   |
                                                   v
                                           +----------------+
                                           | StepEngine     |  (GeminiStepEngine / ClaudeStepEngine)
                                           +-------+--------+
                                                   |
                                                   v
                                           +----------------+
                                           |   CLI / SDK    |  (actual LLM invocation)
                                           +----------------+
                                                   |
                                                   v
    +-------------------------------------------------------------------------------------+
    |                              RUN_BASE                                               |
    |  swarm/runs/<run-id>/                                                               |
    |    meta.json, spec.json, events.jsonl                                               |
    |    signal/ plan/ build/ gate/ deploy/ wisdom/                                       |
    |      llm/         <- transcripts (JSONL per step)                                   |
    |      receipts/    <- receipts (JSON per step)                                       |
    +-------------------------------------------------------------------------------------+
```

**Component roles:**

| Component | Location | Responsibility |
|-----------|----------|----------------|
| Flow Studio | `swarm/tools/flow_studio_ui/` | Web UI for visualization and control |
| RunService | `swarm/runtime/service.py` | Singleton that coordinates all run execution |
| Backend | `swarm/runtime/backends.py` | Implements `RunBackend` interface for specific execution method |
| Orchestrator | `swarm/runtime/orchestrator.py` | Coordinates stepwise execution, step traversal, context handoff |
| StepEngine | `swarm/runtime/engines.py` | Executes individual steps via CLI/SDK |

---

## Step Execution Lifecycle

### 1. Run Creation

When a run starts:

```python
# RunService.start_run()
run_id = generate_run_id()  # e.g., "run-20251209-143022-abc123"
storage.create_run_dir(run_id)
storage.write_spec(run_id, spec)
storage.write_summary(run_id, initial_summary)
storage.append_event(run_id, RunEvent(kind="run_created", ...))
```

### 2. Flow Iteration

The orchestrator loads the flow definition and iterates through steps:

```python
# GeminiStepOrchestrator.run_stepwise_flow()
flow_def = flow_registry.get_flow(flow_key)
for step in flow_def.steps:
    ctx = StepContext(
        repo_root=self._repo_root,
        run_id=run_id,
        flow_key=flow_key,
        step_id=step.id,
        step_index=step.index,
        total_steps=len(flow_def.steps),
        spec=spec,
        flow_title=flow_def.title,
        step_role=step.role,
        step_agents=tuple(step.agents),
        history=step_history,  # Previous step outputs
    )
    result, events = engine.run_step(ctx)
    step_history.append(result)
```

### 3. Step Execution

Each step produces:

**Events** (appended to `events.jsonl`):
```json
{"kind": "step_start", "step_id": "impl-loop", "agent_key": "code-implementer", "payload": {...}}
{"kind": "tool_start", "step_id": "impl-loop", "payload": {"tool": "Read", "input": {...}}}
{"kind": "tool_end", "step_id": "impl-loop", "payload": {"tool": "Read", "success": true}}
{"kind": "step_end", "step_id": "impl-loop", "payload": {"status": "succeeded", "duration_ms": 5000}}
```

**Transcript** (at `RUN_BASE/<flow>/llm/<step_id>-<agent>-<engine>.jsonl`):
```jsonl
{"timestamp": "...", "role": "system", "content": "Executing step impl-loop with agent code-implementer"}
{"timestamp": "...", "role": "user", "content": "Step role: Implement code changes..."}
{"timestamp": "...", "role": "assistant", "content": "I'll implement the health endpoint..."}
{"timestamp": "...", "role": "tool", "tool_name": "Write", "tool_input": {...}, "tool_output": "..."}
```

**Receipt** (at `RUN_BASE/<flow>/receipts/<step_id>-<agent>.json`):
```json
{
  "engine": "claude-step",
  "model": "claude-sonnet-4-20250514",
  "step_id": "impl-loop",
  "flow_key": "build",
  "run_id": "run-20251209-143022-abc123",
  "agent_key": "code-implementer",
  "started_at": "2025-12-09T14:30:22.000000Z",
  "completed_at": "2025-12-09T14:30:26.800000Z",
  "duration_ms": 4800,
  "status": "succeeded",
  "tokens": {"prompt": 12500, "completion": 3200, "total": 15700}
}
```

### 4. Context Handoff

Each step receives the history of previous steps:

```python
@dataclass
class StepContext:
    history: List[Dict[str, Any]]  # Previous step results
    # ...

# In prompt building:
for prev in ctx.history:
    prompt += f"### Step: {prev['step_id']} [{prev['status']}]\n"
    prompt += f"Output: {prev['output'][:1000]}...\n"
```

The engine budgets context to prevent unbounded growth (values from `runtime.yaml`):
- Total history budget: 400k chars (~100k tokens, ~50% of 200k context window)
- Most recent step: up to 120k chars (~30k tokens for rich detail)
- Older steps: up to 20k chars each (~5k tokens for meaningful summaries)

See [CONTEXT_BUDGETS.md](./CONTEXT_BUDGETS.md) for the full philosophy and tuning guidance.

---

## Why Stepwise?

### Per-Step Observability

Batch execution (one LLM call per flow) is a black box. Stepwise execution emits `step_start` and `step_end` events for each step, allowing operators to:

- See which step is currently executing
- Identify where failures occur
- Measure per-step duration and token usage
- Debug by examining individual step transcripts

### Context Management

Stepwise execution explicitly manages context handoff:

- Previous step outputs are summarized and included in subsequent prompts
- Context budgeting prevents prompts from growing unboundedly
- Each step starts with a clear "what came before" summary

### Error Isolation

When a step fails, you know exactly which step and why. Batch execution might fail somewhere in step 7 of 12, but you only see "flow failed."

### Resumption Potential

While not yet implemented, stepwise execution enables future resumption:

- If step 5 fails, re-run from step 5 with existing history
- Partial runs can be completed without starting over
- Human intervention can occur at step boundaries

### Backend Swappability

The `StepEngine` abstraction allows different backends:

```python
class GeminiStepEngine(StepEngine):
    def run_step(self, ctx: StepContext) -> Tuple[StepResult, Iterable[RunEvent]]:
        # Invoke Gemini CLI

class ClaudeStepEngine(StepEngine):
    def run_step(self, ctx: StepContext) -> Tuple[StepResult, Iterable[RunEvent]]:
        # Invoke Claude Agent SDK
```

Same orchestrator, same event format, different underlying LLM.

---

## Extension Points

### Adding a New StepEngine

To add a new LLM provider (e.g., OpenAI):

**1. Implement the engine** (`swarm/runtime/engines.py`):

```python
class OpenAIStepEngine(StepEngine):
    @property
    def engine_id(self) -> str:
        return "openai-step"

    def run_step(self, ctx: StepContext) -> Tuple[StepResult, Iterable[RunEvent]]:
        prompt = self._build_prompt(ctx)
        # Call OpenAI API
        # Write transcript and receipt
        # Return StepResult and events
```

**2. Create a backend** (`swarm/runtime/backends.py`):

```python
class OpenAIStepwiseBackend(RunBackend):
    def _get_orchestrator(self) -> GeminiStepOrchestrator:
        return get_orchestrator(
            engine=OpenAIStepEngine(self._repo_root),
            repo_root=self._repo_root,
        )
```

**3. Register the backend**:

```python
_BACKEND_REGISTRY["openai-step-orchestrator"] = OpenAIStepwiseBackend
```

**4. Add tests** following patterns in `tests/test_gemini_stepwise_backend.py`.

### Adding Custom Flow Steps

Flow steps are defined in YAML (`swarm/config/flows/<flow>.yaml`):

```yaml
steps:
  - id: my-custom-step
    role: "Execute custom validation logic"
    agents: [my-custom-agent]
```

The orchestrator automatically includes new steps in stepwise execution.

---

## Trade-Offs

| Approach | Throughput | Observability | Control | Complexity |
|----------|------------|---------------|---------|------------|
| Batch (one call per flow) | High | Low | Low | Low |
| Stepwise (one call per step) | Lower | High | High | Medium |

Stepwise execution trades throughput for observability and control. For debugging, teaching, and production reliability, this trade-off is usually worth it.

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [STEPWISE_BACKENDS.md](./STEPWISE_BACKENDS.md) | Detailed stepwise backend reference |
| [TRANSCRIPT_SCHEMA.md](./TRANSCRIPT_SCHEMA.md) | Transcript and receipt format specification |
| [RUNTIME_BACKENDS.md](./RUNTIME_BACKENDS.md) | General backend architecture |
| [FLOW_STUDIO.md](./FLOW_STUDIO.md) | Flow Studio UI documentation |
| [CLAUDE.md](../CLAUDE.md) | Repository overview and technology stack |

---

## Summary

The demo-swarm implements Anthropic's long-running agent patterns through:

1. **Initializer agents** (Signal/Plan flows) that load heavy context upfront
2. **Coding agents** (Build flow) with adversarial microloops for quality
3. **Verification agents** (Gate flow) that audit without fixing substantive issues
4. **Stepwise execution** that provides per-step observability, context handoff, and error isolation

The key architectural insight: separate "what to do" (flow specs) from "how to do it" (backends/engines). This allows the same flow to run via different LLM providers while maintaining consistent event streams and artifact formats.

For production use, start with stub mode to test orchestration, then enable real backends once the flow logic is verified.
