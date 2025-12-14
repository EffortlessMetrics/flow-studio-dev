# Gemini CLI Swarm Commands

This directory contains TOML command definitions for **interactive CLI use** with the Gemini CLI tool.

## Purpose

These commands let human operators execute Swarm flows directly from the terminal:

```bash
# Execute Flow 1 (Signal) for a run called "my-feature"
gemini /swarm/signal my-feature

# Execute Flow 3 (Build)
gemini /swarm/build my-feature
```

## Available Commands

| Command | Flow | Description |
|---------|------|-------------|
| `/swarm/signal` | Flow 1 | Normalize input, frame problem, author requirements |
| `/swarm/plan` | Flow 2 | Create ADR, contracts, test/work plans |
| `/swarm/build` | Flow 3 | Implement code and tests via microloops |
| `/swarm/gate` | Flow 4 | Pre-merge audit and merge decision |
| `/swarm/deploy` | Flow 5 | Merge, verify health, create audit trail |
| `/swarm/wisdom` | Flow 6 | Analyze artifacts, extract learnings |

## Command Structure

Each TOML file defines:
- `description`: Help text shown in command listings
- `prompt`: The prompt template with `@{}` file references and `{{args}}` placeholders

Example from `signal.toml`:
```toml
description = "Execute Swarm Flow 1 (Signal): normalize input..."

prompt = """
You are executing Swarm Flow 1...
- Flow spec: @{swarm/flows/flow-signal.md}
- Run artifacts: swarm/runs/{{args}}/signal/
...
"""
```

## Relationship to Flow Studio Backend

**These commands are separate from the GeminiCliBackend in `swarm/runtime/backends.py`.**

| Aspect | TOML Commands (this directory) | GeminiCliBackend |
|--------|--------------------------------|------------------|
| **Use case** | Interactive human CLI use | Programmatic Flow Studio execution |
| **Invocation** | `gemini /swarm/<flow> <run-id>` | `gemini --output-format stream-json --prompt "..."` |
| **Output format** | Human-readable terminal | JSONL event stream |
| **File references** | Uses `@{}` syntax | Inlined in prompt |
| **Prompt source** | TOML files | `_build_prompt()` method |

The separation is intentional:
- **TOML commands** are optimized for human ergonomics (readable prompts, file references, help text)
- **Backend prompts** are optimized for programmatic control (structured output, run_id injection, event streaming)

## Future Possibilities

A command-driven backend variant could invoke these TOML commands directly instead of using `--prompt`. This would:
- Reuse the same prompt definitions for both interactive and programmatic use
- Require different output parsing (not stream-json format)
- Be useful if prompt maintenance becomes duplicated

For now, the separation keeps each path optimized for its use case.

## See Also

- Flow specs: `swarm/flows/flow-*.md`
- Backend implementation: `swarm/runtime/backends.py` (GeminiCliBackend class)
- RUN_BASE conventions: Root `CLAUDE.md` "RUN_BASE: Artifact Placement" section
