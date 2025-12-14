# ADR: Add minimal health endpoint

Decision: Implement a minimal `GET /health` endpoint returning 200 and `{ "status": "ok" }` at routing layer. No dependency checks.

Rationale: Minimal surface area, easy to test, satisfies Kubernetes probe needs.
