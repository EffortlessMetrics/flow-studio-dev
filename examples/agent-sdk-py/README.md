# Python Agent SDK Example

A minimal, working example that proves: **If Claude Code works, Agent SDK works - no separate API key needed.**

## What This Proves

The Claude Agent SDK is "headless Claude Code". It reuses your existing Claude subscription (Max/Team/Enterprise) when you're logged into Claude Code. This means:

- No separate API billing account needed
- No API keys to manage
- If `claude 'hello'` works in your terminal, this demo works

## Prerequisites

1. **Claude Code installed and authenticated**:
   ```bash
   # Install Claude Code
   npm install -g @anthropic-ai/claude-code

   # Log in (opens browser for OAuth)
   claude login

   # Verify it works
   claude 'say hello'
   ```

2. **Python 3.10+**

## Running the Demo

### Option 1: Direct execution

```bash
cd examples/agent-sdk-py
pip install claude-code-sdk
python agent_sdk_demo.py
```

### Option 2: Install as package

```bash
cd examples/agent-sdk-py
pip install -e .
demo  # Uses the entry point defined in pyproject.toml
```

### Option 3: Using uv (recommended)

```bash
cd examples/agent-sdk-py
uv run python agent_sdk_demo.py
```

## Expected Output

```
============================================================
Claude Agent SDK Demo
============================================================

This demo proves: If Claude Code works, Agent SDK works.
No separate API key or billing account needed.

[1/3] SDK imported successfully
[2/3] Working directory: /path/to/flow-studio

Sending query to Claude Agent SDK...
(This uses your Claude Code login - no API key needed)

[3/3] Query completed successfully!

------------------------------------------------------------
RESPONSE:
------------------------------------------------------------
1. Signal (Flow 1): Raw input -> problem statement, requirements, BDD
2. Plan (Flow 2): Requirements -> ADR, contracts, observability spec
3. Build (Flow 3): Implement via adversarial microloops
4. Gate (Flow 4): Pre-merge audit and merge/bounce decision
5. Deploy (Flow 5): Move artifact to production, verify health
6. Wisdom (Flow 6): Analyze artifacts, extract learnings
------------------------------------------------------------

SUCCESS: Agent SDK is working with your Claude Code login.
```

## How It Works

1. The script imports `claude_code_sdk` (ClaudeCodeOptions, query)
2. It sends a simple prompt asking about the swarm flows
3. The SDK routes this through your Claude Code installation
4. Claude responds using your existing subscription

No API key appears anywhere in the code because none is needed.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ImportError: claude_code_sdk` | SDK not installed | `pip install claude-code-sdk` |
| Auth/permission errors | Not logged in | `claude login` |
| "claude not found" | Claude Code not installed | `npm install -g @anthropic-ai/claude-code` |

## Learn More

- [Agent SDK Integration Guide](../../docs/AGENT_SDK_INTEGRATION.md) - Full integration patterns
- [Stepwise Backends](../../docs/STEPWISE_BACKENDS.md) - How the swarm uses the SDK
- [CLAUDE.md](../../CLAUDE.md) - Repository overview and Claude surfaces
