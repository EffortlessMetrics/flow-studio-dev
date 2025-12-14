# Observability Backend Integration

This directory contains configuration for selftest observability backends. The selftest system can emit metrics and events to multiple monitoring platforms simultaneously.

## Quick Start

### Default Configuration (Zero Setup Required)

By default, selftest emits JSON-formatted events to stdout:

```bash
make selftest
# or
uv run swarm/tools/selftest.py
```

You'll see JSON lines like:
```json
{"timestamp": "2025-12-01T12:44:44+00:00", "event_type": "run_started", "run_id": "selftest-1764593084", "tier": "kernel"}
{"timestamp": "2025-12-01T12:44:44+00:00", "event_type": "step_completed", "step_id": "core-checks", "duration_ms": 44, "result": "PASS", "tier": "kernel"}
{"timestamp": "2025-12-01T12:44:45+00:00", "event_type": "run_completed", "run_id": "selftest-1764593084", "result": "PASS", "duration_ms": 1500}
```

### Enable Prometheus Metrics

1. Install prometheus_client:
   ```bash
   pip install prometheus_client
   ```

2. Edit `swarm/config/observability_backends.yaml`:
   ```yaml
   backends:
     prometheus:
       enabled: true
       serve_port: 8000  # Metrics exposed at http://localhost:8000
   ```

3. Run selftest:
   ```bash
   make selftest
   ```

4. Scrape metrics:
   ```bash
   curl http://localhost:8000/metrics
   ```

### Enable Datadog

1. Install datadog library:
   ```bash
   pip install datadog
   ```

2. Set API key:
   ```bash
   export DATADOG_API_KEY=your-api-key-here
   ```

3. Edit `swarm/config/observability_backends.yaml`:
   ```yaml
   backends:
     datadog:
       enabled: true
       tags:
         - "service:selftest"
         - "team:platform"
       metric_prefix: "swarm.selftest"
   ```

4. Run selftest (metrics will be pushed to Datadog):
   ```bash
   make selftest
   ```

### Enable CloudWatch

1. Install boto3:
   ```bash
   pip install boto3
   ```

2. Configure AWS credentials (use AWS CLI or environment variables):
   ```bash
   aws configure
   # or
   export AWS_ACCESS_KEY_ID=your-access-key
   export AWS_SECRET_ACCESS_KEY=your-secret-key
   export AWS_DEFAULT_REGION=us-east-1
   ```

3. Edit `swarm/config/observability_backends.yaml`:
   ```yaml
   backends:
     cloudwatch:
       enabled: true
       namespace: "SelfTest"
       region: "us-east-1"
   ```

4. Run selftest (metrics will be sent to CloudWatch):
   ```bash
   make selftest
   ```

## Configuration Reference

### Backend: Logs (Always Enabled)

```yaml
backends:
  logs:
    enabled: true
    format: "json"  # or "text"
    output: "stdout"  # or "stderr" or "/path/to/file.log"
    level: "INFO"
    include_output: false  # Include step stdout/stderr in events
    timestamp_format: "iso8601"  # or "unix"
```

**Event Types:**
- `run_started`: Emitted when selftest starts
- `step_completed`: Emitted after each step completes (PASS/FAIL/SKIP)
- `step_failed`: Emitted when a step fails (includes error message)
- `run_completed`: Emitted when selftest finishes (includes summary)

### Backend: Prometheus

```yaml
backends:
  prometheus:
    enabled: true
    pushgateway_url: null  # Optional: "http://localhost:9091"
    serve_port: 8000
    serve_addr: "127.0.0.1"
    job_name: "selftest"
    labels:
      environment: "local"
      team: "platform"
```

**Metrics Exposed:**
- `selftest_runs_total{tier, result}`: Counter of runs
- `selftest_steps_total{step_id, tier, result}`: Counter of steps
- `selftest_step_duration_seconds{step_id, tier}`: Histogram of step durations
- `selftest_run_duration_seconds{tier}`: Histogram of run durations
- `selftest_failures_total{step_id, tier, severity}`: Counter of failures

### Backend: Datadog

```yaml
backends:
  datadog:
    enabled: true
    api_endpoint: "https://api.datadoghq.com"
    api_key: null  # Auto-detected from DATADOG_API_KEY env var
    site: "datadoghq.com"
    tags:
      - "service:selftest"
      - "team:platform"
    metric_prefix: "swarm.selftest"
```

**Metrics Sent:**
- `swarm.selftest.step.duration`: Step execution time
- `swarm.selftest.step.count`: Step execution count
- `swarm.selftest.failure.count`: Failure count
- `swarm.selftest.run.duration`: Total run duration
- `swarm.selftest.run.count`: Run count
- `swarm.selftest.steps.passed`: Number of passed steps
- `swarm.selftest.steps.failed`: Number of failed steps

**Events Sent:**
- Run started/completed
- Step failures

### Backend: CloudWatch

```yaml
backends:
  cloudwatch:
    enabled: true
    namespace: "SelfTest"
    region: "us-east-1"  # Uses AWS_DEFAULT_REGION if not set
    dimensions:
      - name: "Environment"
        value: "local"
      - name: "Service"
        value: "selftest"
    storage_resolution: 60  # High resolution (1-60 seconds)
```

**Metrics Sent:**
- `StepDuration`: Duration of each step
- `StepCount`: Count of step executions
- `FailureCount`: Count of failures
- `RunDuration`: Total run duration
- `RunCount`: Count of runs
- `StepsPassed`: Number of passed steps
- `StepsFailed`: Number of failed steps

### Global Settings

```yaml
global:
  enabled: true  # Master switch for all backends
  strict_mode: false  # If true, backend init failures crash selftest
  timeout: 5.0  # Timeout for backend operations (seconds)
```

## Design Philosophy

### Graceful Degradation

Observability is **optional** and **never crashes selftest**:

- Missing credentials → backend disabled, logged but non-blocking
- Missing libraries (prometheus_client, datadog, boto3) → backend skipped
- Backend errors → logged, other backends continue
- Config errors → fall back to defaults

### Zero-Config Default

By default:
- Logs backend is enabled (writes JSON to stdout)
- All other backends are disabled
- No external dependencies required
- Works immediately on clone

### Multi-Backend Support

All enabled backends receive **all events**:
- Run multiple backends simultaneously
- Each backend independently fails/succeeds
- Errors in one backend don't affect others

## Example: Complete CI Setup

For a complete CI pipeline with Datadog monitoring:

```yaml
# .github/workflows/selftest.yml
name: Selftest

on: [push, pull_request]

env:
  DATADOG_API_KEY: ${{ secrets.DATADOG_API_KEY }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install dependencies
        run: |
          pip install uv
          uv pip install datadog prometheus_client

      - name: Enable observability
        run: |
          cat > swarm/config/observability_backends.yaml << EOF
          backends:
            logs:
              enabled: true
              output: "stdout"
            datadog:
              enabled: true
              tags:
                - "service:selftest"
                - "env:ci"
                - "repo:flow-studio"
            prometheus:
              enabled: false
          EOF

      - name: Run selftest
        run: make selftest
```

## Troubleshooting

### Prometheus metrics not showing

**Problem**: `curl http://localhost:8000/metrics` fails

**Solutions**:
- Check `prometheus_client` is installed: `pip list | grep prometheus`
- Verify port is not in use: `lsof -i :8000`
- Check config: `cat swarm/config/observability_backends.yaml`
- Look for warning: `prometheus_client not installed, Prometheus backend disabled`

### Datadog events not appearing

**Problem**: Events not visible in Datadog UI

**Solutions**:
- Verify API key: `echo $DATADOG_API_KEY`
- Check library: `pip list | grep datadog`
- Enable verbose logging: `export DATADOG_DEBUG=true`
- Check tags match your Datadog org

### CloudWatch metrics missing

**Problem**: Metrics not showing in CloudWatch console

**Solutions**:
- Check AWS credentials: `aws sts get-caller-identity`
- Verify boto3: `pip list | grep boto3`
- Check namespace/region in config
- Look for IAM permission errors in logs

### Selftest crashes with observability error

**Problem**: Selftest exits with backend error

**Solutions**:
- Disable strict mode in config: `strict_mode: false`
- Disable problematic backend: `enabled: false`
- Check backend-specific logs
- File a bug with full error trace

## Testing

Run the observability backend test suite:

```bash
uv run pytest tests/test_observability_backends.py -vv
```

This tests:
- Config loading and validation
- Backend initialization
- Credential detection
- Graceful degradation
- Event emission
- JSON log format

## Architecture

### Abstract Backend Interface

All backends implement `ObservabilityBackend`:

```python
class ObservabilityBackend(ABC):
    def emit_run_started(self, run_id, tier, timestamp): ...
    def emit_step_completed(self, step_id, duration_ms, result, tier): ...
    def emit_step_failed(self, step_id, severity, error_message, tier): ...
    def emit_run_completed(self, run_id, result, duration_ms, summary): ...
    def close(self): ...
```

### Backend Manager

`BackendManager` orchestrates all backends:
- Loads config from YAML
- Initializes enabled backends
- Forwards events to all backends
- Handles errors gracefully
- Closes all backends on exit

### Integration Points

Selftest integration:
- `SelfTestRunner.__init__()`: Initialize `BackendManager`
- `run()` start: Emit `run_started`
- After each step: Emit `step_completed`
- On step failure: Emit `step_failed`
- `run()` end: Emit `run_completed`, close backends

## Future Enhancements

Planned backends:
- **New Relic**: APM and infrastructure monitoring
- **Grafana Cloud**: Unified observability platform
- **Honeycomb**: Distributed tracing and observability
- **Statsd**: Push to local statsd daemon
- **OpenTelemetry**: OTLP export for vendor-neutral observability

Planned features:
- Sampling (emit subset of events for high-volume tests)
- Batching (buffer events, send in batches)
- Async emission (non-blocking event delivery)
- Custom dimensions/tags per backend
- Dynamic backend enable/disable (REST API)

## Contributing

To add a new backend:

1. Implement `ObservabilityBackend` interface
2. Add config schema to `observability_backends.yaml`
3. Register in `BackendManager._initialize_backends()`
4. Add tests to `test_observability_backends.py`
5. Update this README with config reference

See `swarm/tools/observability_backends.py` for examples.
