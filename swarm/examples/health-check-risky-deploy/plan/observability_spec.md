# Observability Specification

## Metrics

### Health Endpoint Metrics

**Metric Name**: `http_health_check_requests_total`
- **Type**: Counter
- **Labels**: `status_code`, `method`
- **Description**: Total number of health check requests

**Metric Name**: `http_health_check_latency_seconds`
- **Type**: Histogram
- **Buckets**: [0.001, 0.005, 0.010, 0.050, 0.100]
- **Labels**: `status_code`
- **Description**: Health check request latency distribution

## Alerts

### HealthCheckHighVolume

**Condition**: `rate(http_health_check_requests_total[5m]) > 100`
- **Severity**: WARNING
- **Description**: Health check request rate exceeds expected threshold
- **Runbook**: Check for misconfigured probes or DDoS attempt

### HealthCheckHighLatency

**Condition**: `http_health_check_latency_seconds{quantile="0.99"} > 0.010`
- **Severity**: WARNING
- **Description**: Health check p99 latency exceeds 10ms
- **Runbook**: Investigate service health, check resource contention

## Dashboards

Add to service dashboard:
- Health check request rate (requests/sec)
- Health check latency p50, p95, p99
- Health check error rate (non-200 responses)

## Logging

Health endpoint should NOT log individual requests (too noisy). Log only:
- Service startup: "Health endpoint registered at /health"
- Errors: Log if handler returns non-200 (should never happen)

## Risk Mitigation

These metrics address the MEDIUM performance risk identified in early risk assessment by providing visibility into:
- Request volume (detect probe misconfiguration)
- Latency distribution (detect performance degradation)
- Error patterns (detect implementation issues)
