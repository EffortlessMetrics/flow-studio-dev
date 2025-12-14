# Observability Spec

- Metric: `health_check_requests_total` (counter)
- Log: health endpoint should log a single-line access entry.
- Alert: high error rate on /health (>= 5% over 5m) should trigger investigation.
