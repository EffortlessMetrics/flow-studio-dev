# Problem Statement

Add a minimal health-check endpoint to `demo-service` so external systems can probe service liveness.

Goals:
- Provide `GET /health` returning 200 and `{ "status": "ok" }`.
- No auth required.
- Include tests and a short README note.

Out of scope:
- Deep dependency checks (DB, external APIs).
