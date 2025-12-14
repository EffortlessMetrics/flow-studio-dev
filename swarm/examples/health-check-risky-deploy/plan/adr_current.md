# ADR: Add minimal health endpoint with monitoring

Decision: Implement a minimal `GET /health` endpoint returning 200 and `{ "status": "ok" }` at routing layer. No dependency checks. Include metrics instrumentation for request volume and latency tracking.

Rationale: Minimal surface area, easy to test, satisfies Kubernetes probe needs. Metrics address performance risk identified in early risk assessment.

## Risk Mitigation

Performance impact mitigated by:
1. Handler instrumented with metrics (request count, latency)
2. Response is minimal (no expensive operations)
3. No database or external API calls
4. Monitoring alerts configured for anomalous traffic

## Alternatives Considered

1. **Health endpoint with dependency checks**: Rejected - too expensive for high-frequency probes
2. **Cached health response**: Rejected - unnecessary complexity for minimal endpoint
3. **No health endpoint**: Rejected - forces probes to use application endpoints
