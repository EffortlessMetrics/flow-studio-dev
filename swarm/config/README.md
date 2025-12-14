# Swarm Config (Phase 1+)

This directory will contain provider-neutral configuration files that serve as the source of truth for multi-platform adaptation.

**Phase 0 (now):** Empty. Spec is hand-maintained in `swarm/AGENTS.md` and `swarm/flows/flow-*.md`.

**Phase 1 (future):** Will contain:

- `agents.yaml` – machine-readable agent registry (extracted from `AGENTS.md`)
- `flows.yaml` – machine-readable flow definitions
- Optional: `requirements.yaml` – functional requirements as config
- Optional: `platforms-enabled.yaml` – which platforms to support

**Related:** See `swarm/ARCHITECTURE_MULTI_PLATFORM.md` for the roadmap.
