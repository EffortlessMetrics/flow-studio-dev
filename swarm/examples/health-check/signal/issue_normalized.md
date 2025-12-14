Title: Add GET /health endpoint

Summary:
- Service: demo-service
- Requested change: add a minimal unauthenticated `GET /health` endpoint that returns 200 OK and `{ "status": "ok" }`.

Context:
- Incoming from an engineering request to provide a readiness/liveness probe for Kubernetes and uptime monitoring.
Title: Add /health endpoint to demo-service

Short description:
- Add a simple GET /health (or /live) HTTP endpoint to `demo-service` that returns 200 OK and a small JSON payload `{ "status": "ok" }`.

Context:
- Service: `demo-service` (HTTP API, Rust)
- No existing health/liveness endpoint discovered in the codebase scan.
- Intended use: Kubernetes / uptime probes; no auth required.

Priority: quick, low-risk improvement with tests and minimal docs.
