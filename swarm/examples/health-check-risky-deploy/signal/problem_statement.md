# Problem Statement

Add a minimal health-check endpoint to `demo-service` so external systems can probe service liveness.

Goals:
- Provide `GET /health` returning 200 and `{ "status": "ok" }`.
- No auth required.
- Include tests and a short README note.

Out of scope:
- Deep dependency checks (DB, external APIs).

## Context

External load balancers and Kubernetes probes need a lightweight endpoint to verify service availability. Current lack of health endpoint forces probes to use root path, which triggers unnecessary application logic.
