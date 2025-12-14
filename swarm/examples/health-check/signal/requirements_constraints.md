# Constraints

- No authentication for `/health` (must be reachable by probes).
- Keep response minimal; avoid heavy dependency checks.
- Changes must include tests and documentation.
