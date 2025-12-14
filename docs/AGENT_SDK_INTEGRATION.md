# Agent SDK Integration Guide

> For: Developers building agents using the Claude Agent SDK or Anthropic APIs.

This guide explains how Claude's programmable surfaces map to this demo swarm, and how to integrate Agent SDK-based agents with the swarm's flows.

---

## Understanding Claude Surfaces

This repo uses three Anthropic surfaces. Understanding which to use saves confusion:

| Surface | Auth/Plan | Use Case | API Key? |
|---------|-----------|----------|----------|
| **Agent SDK** (TS/Python) | Claude login (Max/Team/Enterprise) | Local dev, building agents | No |
| **CLI** (`claude --output-format`) | Claude login | Shell integration, debugging | No |
| **HTTP API** (`api.anthropic.com`) | API account | Server-side, CI, multi-tenant | Yes |

> **Key insight**: The Agent SDK is "headless Claude Code"—it reuses your existing Claude
> subscription when you're logged into Claude Code. No separate API billing account needed.
> Use HTTP APIs when you need explicit keys for server deployments.

---

## Quick Start: Which Surface Should I Use?

| Persona | Use Case | Recommended Surface |
|---------|----------|---------------------|
| Developer building agents locally | Claude Max/Team subscription | **Agent SDK** |
| Running in CI/automation | Need explicit API keys | **HTTP API** |
| Debugging stepwise flows | Quick shell tests | **CLI** |
| Backend service / multi-tenant | Production deployment | **HTTP API** |

---

## Hello World Examples

Try the Agent SDK with these minimal examples:

### TypeScript

```bash
cd examples/agent-sdk-ts
npm install
npm run demo
```

See `examples/agent-sdk-ts/README.md` for details.

### Python

```bash
cd examples/agent-sdk-py
uv run python agent_sdk_demo.py
```

See `examples/agent-sdk-py/README.md` for details.

### Makefile Shortcuts

```bash
make agent-sdk-ts-demo    # Run TypeScript example
make agent-sdk-py-demo    # Run Python example
make agent-sdk-help       # Show Agent SDK help
```

---

## Agent SDK Integration

The Agent SDK is the primary programmable surface for local development. It provides a TypeScript and Python interface to Claude that reuses your Claude Code login.

### TypeScript Agent SDK

Install the official Claude Agent SDK:

```bash
npm install @anthropic-ai/claude-code
```

Basic usage pattern:

```typescript
import { Claude } from "@anthropic-ai/claude-code";

// Initialize the agent
const claude = new Claude();

// Run a stepwise flow by calling local make targets
const result = await claude.run({
  prompt: `Run the signal flow for this issue: ${issueDescription}`,
  workingDirectory: "/path/to/flow-studio",
  allowedTools: ["Bash", "Read", "Write", "Glob", "Grep"],
});

// Or drive the swarm directly
const flowResult = await claude.run({
  prompt: "Execute /flow-1-signal with the issue context above",
  workingDirectory: "/path/to/flow-studio",
});
```

### Python Agent SDK

Install the Claude Code SDK:

```bash
pip install claude-code-sdk
```

Basic usage pattern:

```python
from claude_code_sdk import ClaudeCodeOptions, query
import asyncio

async def run_flow():
    options = ClaudeCodeOptions(
        allowed_tools=["Bash", "Read", "Write", "Glob", "Grep"]
    )

    async for event in query(
        prompt="Run the signal flow for issue: Add health check endpoint",
        cwd="/path/to/flow-studio",
        options=options,
    ):
        if event.type == "text":
            print(event.text)
        elif event.type == "result":
            print(f"Completed: {event.result}")

asyncio.run(run_flow())
```

---

## Stepwise Execution with Agent SDK

This repo's stepwise backends use the Agent SDK for per-step LLM calls. The `ClaudeStepEngine` in `swarm/runtime/engines.py` wraps the SDK.

### How It Works

1. **Orchestrator** loads flow definition from `flow_registry`
2. **Per step**: Orchestrator calls `ClaudeStepEngine._run_step_sdk_async()`
3. **Engine** uses `claude_code_sdk.query()` with step-specific prompt
4. **Artifacts** written to `RUN_BASE/<flow>/llm/` and `receipts/`

### Configuration

Set the engine mode via environment variable:

```bash
# Use stub mode (default for CI/dev - no LLM calls)
export SWARM_CLAUDE_STEP_ENGINE_MODE=stub

# Use real SDK execution
export SWARM_CLAUDE_STEP_ENGINE_MODE=sdk

# Use CLI fallback
export SWARM_CLAUDE_STEP_ENGINE_MODE=cli
```

Or configure in `swarm/config/runtime.yaml`:

```yaml
engines:
  claude:
    mode: "sdk"  # Options: stub, sdk, cli
    provider: "anthropic"
```

### Running Stepwise Flows

```bash
# Stub mode (zero-cost demo)
make stepwise-sdlc-stub

# Real Agent SDK execution
SWARM_CLAUDE_STEP_ENGINE_MODE=sdk make stepwise-sdlc-claude-sdk
```

---

## CLI Integration

For debugging and quick tests, use the Claude CLI directly:

```bash
# Run a single flow with structured output
claude --output-format stream-json -p "Execute /flow-1-signal for issue: Add health check"

# Debugging stepwise execution
claude --output-format json -p "Run step 1 of the signal flow"
```

---

## HTTP API Integration

For server-side deployments, CI/CD, and multi-tenant scenarios, use the Anthropic HTTP API:

```bash
export ANTHROPIC_API_KEY=sk-ant-...

curl https://api.anthropic.com/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 4096,
    "messages": [{"role": "user", "content": "..."}]
  }'
```

For production harnesses, see [LONG_RUNNING_HARNESSES.md](./LONG_RUNNING_HARNESSES.md).

---

## Integration Patterns

### Pattern 1: Agent SDK Drives Swarm Flows

Your Agent SDK application calls into this repo's flows:

```
┌─────────────────────┐     ┌──────────────────────────────┐
│  Your Agent App     │────▶│  flow-studio repo            │
│  (Agent SDK)        │     │  make stepwise-sdlc-claude   │
└─────────────────────┘     └──────────────────────────────┘
```

### Pattern 2: Swarm Uses Agent SDK Internally

The swarm's stepwise orchestrator uses Agent SDK for execution:

```
┌───────────────────────┐
│  make stepwise-sdlc-* │
│  (orchestrator.py)    │
│        ▼              │
│  ClaudeStepEngine     │
│  (engines.py)         │
│        ▼              │
│  claude_code_sdk      │
└───────────────────────┘
```

### Pattern 3: Hybrid (Agent SDK + HTTP API)

Development uses Agent SDK; production uses HTTP APIs:

```
Development                   Production
┌─────────────────┐          ┌─────────────────┐
│ Agent SDK       │          │ HTTP API        │
│ (Claude login)  │          │ (API keys)      │
└─────────────────┘          └─────────────────┘
         │                           │
         ▼                           ▼
┌─────────────────────────────────────────────┐
│          Same flow definitions              │
│          (swarm/flows/*.md)                 │
└─────────────────────────────────────────────┘
```

---

## Dependency Status

**Current state**: The SDK dependencies are not yet in `pyproject.toml`. This is intentional—the swarm works in stub mode without SDK installation.

To use real SDK execution:

```bash
# Python
pip install claude-code-sdk

# Then enable SDK mode
SWARM_CLAUDE_STEP_ENGINE_MODE=sdk make stepwise-sdlc-claude-sdk
```

The engine gracefully degrades to stub mode if the SDK is not installed.

---

## Troubleshooting

### "SDK not available, using stub mode"

Install the SDK:
```bash
pip install claude-code-sdk
```

### "Authentication required"

Ensure you're logged into Claude Code:
```bash
claude auth login
```

### "Mode 'sdk' requested but SDK unavailable"

The SDK must be installed for sdk mode. Either:
1. Install: `pip install claude-code-sdk`
2. Use stub mode: `SWARM_CLAUDE_STEP_ENGINE_MODE=stub`
3. Use CLI mode: `SWARM_CLAUDE_STEP_ENGINE_MODE=cli`

---

## See Also

- [STEPWISE_BACKENDS.md](./STEPWISE_BACKENDS.md) — Detailed stepwise execution documentation
- [LONG_RUNNING_HARNESSES.md](./LONG_RUNNING_HARNESSES.md) — Production harness patterns
- [RUNTIME_BACKENDS.md](./RUNTIME_BACKENDS.md) — Backend architecture overview
- [RUN_LIFECYCLE.md](./RUN_LIFECYCLE.md) — Run management and retention
