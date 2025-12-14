# Functional Requirements

1. FR1: Expose `GET /health` returning HTTP 200 when service is running.
2. FR2: Response body must be valid JSON: `{ "status": "ok" }`.
3. FR3: Endpoint requires no authentication and is accessible to probes.
