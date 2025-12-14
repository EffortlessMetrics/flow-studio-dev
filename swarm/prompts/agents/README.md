# Agent Prompts (Phase 2+)

This directory will contain isolated, provider-neutral prompt bodies for each agent.

**Phase 0–1 (now):** Empty. Prompt content lives inline in `.claude/agents/*.md` files.

**Phase 2 (future):** Will contain:

- `requirements-author.md` – prompt body for requirements author (extracted from `.claude/agents/requirements-author.md`)
- `requirements-critic.md` – prompt body for requirements critic
- `deploy-decider.md` – prompt body for deploy decider
- etc. (one file per agent)

When the generator runs, it will:

1. Load the provider-neutral prompt body from here.
2. Wrap it in platform-specific frontmatter (model, skills, etc.).
3. Write the result to `.claude/agents/`, `.openai/agents/`, etc.

**Related:** See `swarm/ARCHITECTURE_MULTI_PLATFORM.md` for the roadmap.
