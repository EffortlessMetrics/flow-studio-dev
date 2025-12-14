# Platform Profiles (Phase 1+)

This directory will contain YAML profiles that describe how each platform (Claude Code, OpenAI, Gemini, etc.) maps the provider-neutral spec to platform-specific syntax and tooling.

**Phase 0 (now):** Empty. Only `.claude/` adapter layer exists, and it's hand-maintained.

**Phase 1 (future):** Will contain:

- `claude.yaml` – Claude Code profile (model defaults, frontmatter rules, adapter dirs, CLI conventions)
- `openai.yaml` – OpenAI Codecs profile
- `gemini.yaml` – Gemini profile
- etc.

Each profile specifies:

- Target directory for generated agent files (e.g., `.claude/agents`)
- Model selection logic (which model for which role family)
- Frontmatter rules (required, optional, forbidden fields)
- Tool/skill mappings (platform-specific capability names)
- Command syntax (slash commands, function calls, etc.)

**Related:** See `swarm/ARCHITECTURE_MULTI_PLATFORM.md` for the roadmap.
