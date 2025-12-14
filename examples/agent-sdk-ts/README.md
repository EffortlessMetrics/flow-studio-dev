# Agent SDK TypeScript Example

This is a minimal, working example that proves:

> **If Claude Code works, Agent SDK works - no separate API key needed.**

## What This Demonstrates

The Claude Agent SDK is "headless Claude Code" - it reuses your existing Claude
subscription (Max/Team/Enterprise). You do not need a separate API billing
account or API key.

| Surface | Auth | API Key Required? |
|---------|------|-------------------|
| Claude Code (IDE) | Claude login | No |
| Agent SDK | Claude login | No |
| HTTP API | API account | Yes |

This example uses the Agent SDK to query Claude about the swarm flows defined
in this repository, proving the SDK connection works without any API key
configuration.

## Prerequisites

1. **Claude Code installed and logged in**

   ```bash
   # Verify Claude Code is working
   claude --version
   claude "Hello, are you there?"
   ```

   If this works, the Agent SDK will work too.

2. **Node.js 18+**

   ```bash
   node --version  # Should be 18.x or higher
   ```

## Running the Demo

```bash
# Navigate to this example
cd examples/agent-sdk-ts

# Install dependencies
npm install

# Run the demo
npm run demo
```

## Expected Output

```
============================================================
Claude Agent SDK Demo
============================================================

This example proves: If Claude Code works, Agent SDK works.
No separate API key needed - uses your Claude Code login.

Querying Claude to list flows in this repository...
------------------------------------------------------------

Response from Claude:

1. Signal -> Specs (Flow 1): Transforms raw input into problem statement, requirements, BDD scenarios, and early risk assessment
2. Specs -> Plan (Flow 2): Converts requirements into ADR, API contracts, observability spec, and test/work plans
...

------------------------------------------------------------
Success! The Agent SDK connected without an API key.

What this proves:
  1. Agent SDK reuses your Claude Code subscription
  2. No separate API billing account needed
  3. Works if you're logged into Claude Code
```

## Troubleshooting

### "Authentication failed"

Make sure you are logged into Claude Code:

```bash
claude "Hello"
```

If this fails, run `claude` and follow the login prompts.

### "Module not found"

Run `npm install` to install dependencies.

### Type errors

Run `npm run typecheck` to verify TypeScript configuration.

## Further Reading

- [CLAUDE.md](../../CLAUDE.md) - Repository overview and Claude surfaces explanation
- [docs/STEPWISE_BACKENDS.md](../../docs/STEPWISE_BACKENDS.md) - How stepwise execution uses Agent SDK

## Key Insight

The Agent SDK is the primary programmable surface for local development with
Claude. Use it when you want to build agents, automate workflows, or integrate
Claude into your tools - all without managing API keys or separate billing.
