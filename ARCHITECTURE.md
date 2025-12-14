# Swarm Architecture Overview

**Status:** Phase 0 (teaching repo with single platform)
**Last Updated:** 2025-11-28

This document describes the swarm's overall architecture: what we have now (Phase 0), what we're planning (Phases 1–3), and how everything fits together.

---

## High-Level Design

The swarm is organized into **three layers**:

### 1. Spec Layer (`swarm/`)

**Source of truth** for the SDLC harness.

- **`AGENTS.md`** – canonical agent registry (name, role, flows, color, description)
- **`flows/flow-*.md`** – flow specifications (question, outputs, agents, orchestration)
- **`CLAUDE.md`** – patterns, constraints, architectural decisions
- **`tools/validate_swarm.py`** – validator enforcing spec + platform constraints
- **`runs/<run-id>/`** – concrete receipts from actual flow executions

### 2. Adapter Layer (`.claude/` and future `.openai/`, `.gemini/`, etc.)

**Platform-specific** implementation of the spec.

Currently:

- `.claude/agents/*.md` – Claude Code agent definitions (YAML frontmatter + prompts)
- `.claude/commands/flow-*.md` – slash command entrypoints
- `.claude/skills/*/SKILL.md` – reusable capabilities

Future (Phase 2+):

- Generated from `swarm/config/` + templates, not hand-authored
- One adapter layer per platform (Claude, OpenAI, Gemini, etc.)

### 3. Enforcement Layer (CI + pre-commit + branch rules)

**Operational** protection of the SDLC.

- `.github/workflows/ci.yml` – CI validator + test jobs
- `.pre-commit-config.yaml` – local pre-commit hooks
- Branch protection rules – main requires passing checks

(Operationalized by Flow 5 / `deploy-decider` agent)

---

## Phase 0 – Current State (Teaching Repo)

**Scope:** Single platform (Claude Code), hand-maintained adapters.

**Invariants:**

- Spec layer (`swarm/`) is machine-readable (YAML + markdown).
- Adapter layer (`.claude/`) is hand-authored.
- Spec + adapter are kept in sync by human discipline + validator.

**Validation:**

- `validate_swarm.py` checks:
  - Agent bijection (every AGENTS.md entry has a `.claude/agents` file)
  - Frontmatter correctness (required fields, type validation, design constraints)
  - Flow references (agents mentioned in flows exist)
  - Skill existence (declared skills have SKILL.md files)
  - RUN_BASE paths (no hardcoded paths, only `RUN_BASE/<flow>/`)

**Flows:** 6 fully specified, implemented, and runnable locally.

**Agents:** 48 (3 built-in Claude infra + 45 domain agents in `.claude/agents/`).

**Enforcement:** CI (2 jobs) + pre-commit hook + branch protection (via Flow 5 verification).

---

## Phase 1 – Explicit Configuration (Optional, ~2–3 weeks)

**Scope:** Add machine-readable config layer; validate bijection; prepare for generation.

**New Artifacts:**

- `swarm/config/agents.yaml` – extracted from `AGENTS.md`
- `swarm/config/flows.yaml` – extracted from `swarm/flows/flow-*.md`
- `swarm/platforms/claude.yaml` – Claude profile (model defaults, frontmatter rules)
- Optional: `swarm/config/requirements.yaml` – FR-001..014 + FR-OP-001..005 as config

**Validation Enhancements:**

- Config ↔ registry bijection (agents.yaml ↔ AGENTS.md ↔ .claude/agents)
- Flow ↔ agent references validated against config
- New error type: "Spec drift" (detected via config mismatch)

**Benefit:** Spec becomes programmatically accessible; generation becomes possible.

**No generation yet** – just adding a "configuration layer" so Phase 2 has a clear input.

---

## Phase 2 – Single-Platform Generation (~2–4 weeks after Phase 1)

**Scope:** Automate Claude adapter generation; prove codegen works.

**New Artifacts:**

- `swarm/prompts/agents/*.md` – isolated prompt bodies (extracted from `.claude/agents/`)
- `swarm/templates/claude/agent.md.j2` – Jinja2 template for agent files
- `swarm/templates/claude/command.md.j2` – template for slash commands
- Enhanced `swarm/tools/gen_adapters.py` – generator tool

**Workflow:**

1. Edit spec or prompt: `swarm/config/agents.yaml`, `swarm/prompts/agents/foo.md`
2. Regenerate: `uv run swarm/tools/gen_adapters.py --platform claude`
3. Validate: `uv run swarm/tools/validate_swarm.py` (detects stale or hand-edits)
4. Commit: `.claude/agents/*.md` are now **build artifacts**, not sources

**Key Invariant:** `.claude/agents/*.md` files get a `GENERATED` header; validator flags hand-edits.

**Benefit:** Change an agent's prompt once, update multiple files atomically.

---

## Phase 3 – Multi-Platform Scale (~4–8 weeks after Phase 2)

**Scope:** Scale to N platforms (OpenAI, Gemini, etc.) without multiplying hand-work.

**New Artifacts:**

- `swarm/platforms/openai.yaml`, `swarm/platforms/gemini.yaml` – platform profiles
- `swarm/templates/openai/agent.json.j2` – OpenAI-specific templates
- `swarm/templates/gemini/…` – Gemini-specific templates
- Enhanced `gen_adapters.py` – supports multiple platforms: `--platform claude openai gemini`

**Scaling Benefit:**

Adding a new platform is now:

1. Write `swarm/platforms/<name>.yaml` (tool mappings, model aliases, syntax rules)
2. Write `swarm/templates/<name>/*.j2` (prompt structure, frontmatter)
3. Run: `uv run swarm/tools/gen_adapters.py --platform <name>`
4. Done – all 48 agents + 6 flows + all flows automatically wired for the new platform

No hand-editing of 45+ domain agent files per platform.

---

## Architecture Decisions

### Why Three Layers?

1. **Spec** – describes *what* the swarm is, in a platform-agnostic way
2. **Adapter** – describes *how* each platform implements it
3. **Enforcement** – describes *how* we keep both honest

Separating them lets you:

- Change the spec without touching adapters (until regen)
- Change adapter syntax without changing the spec
- Add new platforms without redesigning the spec or enforcement

### Why Hand-Maintain Adapters in Phase 0?

- Demonstrates the full SDLC end-to-end with minimal tooling
- Lets you understand what the spec is *actually saying* by seeing how it's implemented
- Generation is an optimization, not a requirement
- Deferring it keeps the teaching repo simple

### Why Config in Phase 1?

- Makes the spec machine-readable without breaking current workflows
- Enables validation of spec ↔ impl bijection
- Sets up Phase 2 generation with a clear input
- Forces clarity (e.g., "what are the actual 45 agent keys?")

### Why Generation in Phase 2?

- Proves the pattern works at scale
- Reduces hand-maintenance burden
- Lets validator detect drift automatically
- Natural stepping stone to Phase 3 multi-platform

---

## Current Locations

### Spec (`swarm/`)

```
swarm/
  AGENTS.md                          # Source of truth: agent registry
  CLAUDE.md                          # Spec reference: flows, patterns, constraints
  flows/
    flow-signal.md, flow-plan.md, … # Flow 1–6 specifications
  tools/
    validate_swarm.py                # Two-layer validator
  config/                            # Phase 1+ (empty for now)
  platforms/                         # Phase 1+ (empty for now)
  prompts/agents/                    # Phase 2+ (empty for now)
  templates/                         # Phase 2+ (empty for now)
  runs/<run-id>/                     # Actual execution receipts (git-tracked)
  examples/                          # Curated demo runs
```

### Adapters (`.claude/`)

```
.claude/
  agents/
    (45 agent files, e.g., requirements-author.md)
  commands/flows/
    (6 slash command entrypoints, e.g., flow-1-signal.md)
  skills/
    test-runner/SKILL.md
    auto-linter/SKILL.md
    policy-runner/SKILL.md
  settings.json
```

### Enforcement (`.github/` + `.pre-commit-config.yaml`)

```
.github/workflows/
  ci.yml                             # Validator + test jobs (FR-OP-001/002)
  swarm-validate.yml                 # Legacy single-job (kept for demo)
.pre-commit-config.yaml              # Local validation hook (FR-OP-003)
RUNBOOK.md                           # Enforcement documentation (FR-OP-005)
```

---

## Validation Strategy

`validate_swarm.py` has **two layers**:

### Layer 1 – Platform Spec

Checks that all files are valid inputs for Claude Code:

- YAML frontmatter parses
- Required fields present: `name`, `description`, `model`
- Field types correct: `skills` is a list, `model` in `{inherit, haiku, sonnet, opus}`
- No syntax errors

**Goal:** "Claude Code can plausibly run this."

### Layer 2 – Swarm Design Constraints

Enforces this repo's opinionated design:

- Bijection: every agent key in `AGENTS.md` has a `.claude/agents/<key>.md`
- Frontmatter: `name` matches filename; `color` matches role family; no `tools:` or `permissionMode:` in domain agents
- References: flow specs only reference registered agents or built-ins
- Skills: every skill declaration has a `.claude/skills/<name>/SKILL.md`
- RUN_BASE: flow specs use `RUN_BASE/<flow>/` placeholders, not hardcoded paths

**Goal:** "This swarm's design invariants hold."

---

## Key Patterns

### Microloops (Flows 1 & 3)

Requirements author ⇄ critic, test author ⇄ critic, code author ⇄ critic.

Orchestrator loops while critic signals `Status: UNVERIFIED` + `can_further_iteration_help: yes`.

Stops when critic signals `Status: VERIFIED` or `Status: UNVERIFIED` + `can_further_iteration_help: no`.

### Agents Never Block

Agents always produce receipts, even if the receipt says "we hit a constraint and can't move forward."

The only honest failure is "no receipt."

### When to Use BLOCKED Status

BLOCKED is reserved for **missing external dependencies**, not for ambiguity:

| Status | When to Use |
|--------|-------------|
| **VERIFIED** | Work adequate for purpose; assumptions documented |
| **UNVERIFIED** | Work has issues but produced; assumptions document uncertainty |
| **BLOCKED** | Cannot produce meaningful work due to missing inputs |

**BLOCKED examples** (exceptional):
- Receipt file missing entirely
- Required input artifact does not exist
- External service unreachable (in Flows 5-6)

**NOT BLOCKED** (use UNVERIFIED with assumptions instead):
- Problem statement ambiguous → write best interpretation, document assumptions
- Requirements vague → write testable versions, note gaps
- Scope unclear → estimate based on stated info, list unknowns

The key test: **"Can I write something meaningful even with uncertainty?"**
- If yes → UNVERIFIED + documented assumptions
- If no (missing artifact) → BLOCKED

### Assumptive-but-Transparent Work

When facing ambiguity, agents:
1. Make a reasonable assumption
2. Document the assumption explicitly (what, why, impact if wrong)
3. Note what would change if the assumption is wrong
4. Proceed with work

This enables re-running flows with better inputs. Humans answer clarification questions at flow boundaries, not mid-flow. Each flow is designed to be **run again** with refined inputs.

### Critics Don't Fix

Critics write harsh assessments with explicit status + routing hints.

Implementers (authors, fixers) apply fixes based on critique.

### One Spec, N Platforms (Phase 2+)

After Phase 2 generation is working:

- Edit `swarm/config/agents.yaml`, `swarm/prompts/agents/foo.md`, `swarm/platforms/claude.yaml`
- Run `gen_adapters.py`
- All `.claude/agents/*.md` files update automatically
- Same prompt bodies, different frontmatter per platform

---

## Phase 0 → Phase 1 Transition

No code changes needed to start Phase 1. Just:

1. Create `swarm/config/agents.yaml` (copy metadata from `AGENTS.md`)
2. Create `swarm/config/flows.yaml` (copy structure from `swarm/flows/`)
3. Create `swarm/platforms/claude.yaml` (describe Claude's profile)
4. Extend `validate_swarm.py` to cross-check config ↔ registry ↔ files
5. Update this document

Everything else can stay the same.

---

## When to Move Forward

- **Phase 1:** When `swarm-alignment` Flow 6 (Wisdom) completes and you understand the teaching story
- **Phase 2:** When you're tired of editing `.claude/agents/*.md` by hand and want automation
- **Phase 3:** When a second platform (OpenAI, Gemini, etc.) needs support

You can live in Phase 0 indefinitely; generation is always optional.

---

## References

- `swarm/positioning.md` – design philosophy
- `swarm/ARCHITECTURE_MULTI_PLATFORM.md` – detailed multi-platform RFC
- `swarm/tools/validate_swarm.py` – validator implementation
- `CLAUDE.md` – project-level instructions
- `RUNBOOK.md` – operational procedures

---

**Next step:** After Flow 6 completes, review this and decide: does Phase 1 make sense for your project?
