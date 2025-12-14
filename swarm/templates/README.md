# Templates (Phase 2+)

This directory will contain Jinja2 templates that render agent and command files for each platform.

**Phase 0–1 (now):** Empty. Adapters are hand-authored in `.claude/agents/`, `.claude/commands/`, etc.

**Phase 2 (future):** Will contain platform-specific subdirectories:

- `claude/` – templates for Claude Code `.claude/agents/*.md` and `.claude/commands/*.md`
  - `agent.md.j2` – template for agent files
  - `command.md.j2` – template for slash command files
- `openai/` – templates for OpenAI adapter layer
  - `agent.json.j2` or similar (OpenAI format)
- `gemini/` – templates for Gemini adapter layer
  - etc.

Each template:

- Takes agent metadata + platform profile as input
- Renders platform-specific syntax (model field, tool declarations, etc.)
- Includes `GENERATED` header so validator knows it's a build artifact

**Related:** See `swarm/ARCHITECTURE_MULTI_PLATFORM.md` for the roadmap.
