# Control Plane Contract for Agent Model Configuration

**Status**: Implemented and Verified
**Date**: 2025-11-30

## Overview

The control plane manages agent model configuration through a simple, auditable flow:

```text
swarm/config/agents/<key>.yaml  ──► control_plane.resolve_model()  ──► .claude/agents/<key>.md
    (source of truth)               (validation + audit)               (projection)
```

The control plane is **not a magical tier system**—it's a validator and router that ensures:
1. Only valid model values are used
2. Precedence is clear (override > config > default)
3. Decisions are auditable
4. The runtime model selector stays in Claude Code where it belongs

## The Contract (Immutable Rules)

### 1. Valid Model Values

Only these values are allowed:

```
{ "inherit", "haiku", "sonnet", "opus" }
```

- **`inherit`** is a **first-class valid value**, not a placeholder
  - Semantics: defer to Claude Code's model selector + automatic Haiku downgrade
  - Default: if `model` is missing from config, control plane sets it to `inherit`
  - Explicitly written to frontmatter as `model: inherit`

- **`haiku`, `sonnet`, `opus`** are explicit pins
  - Semantics: hard override the model selector
  - Pin an agent by setting `model: haiku` (or sonnet/opus) in config
  - No tier mapping, no magic—just string values

### 2. Decision Precedence

Control plane resolves model in this order:

1. **Per-platform override** (if explicitly set)
   - From `swarm/config/agents/<key>.yaml`:
     ```yaml
     platforms:
       claude:
         model: haiku  # Platform-specific override
     ```

2. **Config value** (if set)
   - From `swarm/config/agents/<key>.yaml`:
     ```yaml
     model: inherit  # or haiku/sonnet/opus
     ```

3. **Default**: `inherit`
   - If config has no `model` key, control plane defaults to `inherit`

### 3. Audit Trail

Every decision is logged to `swarm/runs/control_plane_audit.log`:

```
2025-11-30T04:11:34.259227Z adr-author: config -> inherit [from agent config]
2025-11-30T04:11:34.259295Z artifact-auditor: config -> haiku [from agent config]
...
```

Fields:
- **Timestamp**: ISO 8601 with Z suffix
- **Agent**: Key (e.g., `adr-author`)
- **Source**: `config`, `override`, or `default`
- **Model**: Final resolved value
- **Reason**: Explanation of the decision
- **Change tracking** (if applicable): `(changed from X)` when override differs from config

### 4. Projection

The control plane does **not** edit files directly. The **generator** (`gen_adapters.py`) is responsible for:
1. Calling `control_plane.resolve_model(...)`
2. Writing resolved model to `.claude/agents/<key>.md` frontmatter
3. Leaving the body untouched

Frontmatter is **generated, not hand-edited**:
```yaml
---
name: adr-author
description: Write ADR for chosen design → adr.md.
model: inherit  # ← Control plane decision, written by generator
color: purple
---

You are the **ADR Author**.
...
```

## Operational Workflow

### To leave behavior to the model selector (default)

In config, set explicitly or omit:

```yaml
# Option 1: Explicit inherit
model: inherit

# Option 2: Omit (control plane defaults to inherit)
# (no model key at all)
```

Run:
```bash
make gen-adapters
make check-adapters
make validate-swarm
```

Result: `.claude/agents/<key>.md` has `model: inherit`

### To pin an agent to a specific model

```yaml
model: haiku  # (or sonnet / opus)
```

Run:
```bash
make gen-adapters
make check-adapters
make validate-swarm
```

Result: `.claude/agents/<key>.md` has `model: haiku`

### To pin only for Claude, leave others dynamic

```yaml
model: inherit
platform_claude_model: haiku
```

Result: Claude gets `model: haiku`, other platforms can use their own logic

### To audit what changed

```bash
cat swarm/runs/control_plane_audit.log
```

Also check the control plane summary printed at end of `gen_adapters.py` run:

```
[SUMMARY] Processed 45 decisions:
  By source: {'config': 45}
  By model: {'inherit': 41, 'haiku': 4}
```

## Design Rationale

### Why not tier → model mapping?

- **Simplicity**: Direct string values are easier to reason about than abstract tiers
- **Explicitness**: A misconfigured tier won't silently map to the wrong model
- **Separation of concerns**: Tier mapping can happen at the platform adapter level (OpenAI, Gemini) if needed, not at the control plane

### Why is `inherit` first-class?

- **Defers to runtime**: Claude Code's model selector + Haiku downgrade are battle-tested; we shouldn't override them
- **Default safety**: If someone forgets to set `model`, the default is still safe and well-understood
- **Audit clarity**: `inherit` in the log means "no override," making intent explicit

### Why is the generator separate from the control plane?

- **Single Responsibility**: Control plane validates + routes; generator handles templating + writing
- **Testability**: Can test control plane logic independently of file I/O
- **Reusability**: Control plane can be used by other tools (CI checks, dashboards) without knowing about templates

## Testing

All contract rules are validated by:

```bash
uv run swarm/tools/test_control_plane.py   # Core logic
uv run swarm/tools/test_gen_adapters.py    # Generator integration
make check-adapters                         # CI gate
```

Coverage:
- ✓ Valid model values only
- ✓ Decision precedence (override > config > default)
- ✓ Audit logging (timestamps, sources, change tracking)
- ✓ `inherit` preservation through pipeline
- ✓ Platform overrides
- ✓ `model_tier` metadata (ignored by generator, available for future use)
- ✓ Error handling (clear messages for invalid models)

## Current State (2025-11-30)

**45 agents, all config-backed:**
- 38 agents use `model: inherit` (defer to model selector)
- 4 agents explicitly pin to `model: haiku`:
  - `artifact-auditor`
  - `deploy-monitor`
  - `receipt-checker`
  - `smoke-verifier`

All agents pass generator check (`check-all`), validator check (`validate-swarm`), and swarm design constraints.

---

**This contract is stable and authoritative for platform:claude in Phase 1.**
When OpenAI/Gemini adapters are added, this document serves as the reference for how model configuration *should* work.
