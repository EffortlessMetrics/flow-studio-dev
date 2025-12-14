# Selftest System

The selftest system provides a composable, layered validation framework for ensuring the swarm's governance constraints are satisfied. It's designed for both developers running quick checks and CI systems requiring comprehensive validation.

## Quick Start

```bash
# Run full selftest (recommended for CI)
uv run swarm/tools/selftest.py

# Quick kernel check (~300-400ms)
make kernel-smoke

# Show execution plan without running
uv run swarm/tools/selftest.py --plan

# Run in degraded mode (only KERNEL failures block)
uv run swarm/tools/selftest.py --degraded
```

## Concepts

### Tiers

Selftest steps are organized into three tiers based on criticality:

| Tier | Behavior | Examples |
|------|----------|----------|
| **KERNEL** | Must pass; failures block merges | Python linting, compile checks |
| **GOVERNANCE** | Should pass; warnings in degraded mode | Agent validation, BDD scenarios |
| **OPTIONAL** | Nice-to-have; informational | Coverage thresholds, experimental checks |

### Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Strict** (default) | KERNEL + GOVERNANCE failures block | CI, pre-merge checks |
| **Degraded** (`--degraded`) | Only KERNEL failures block | Work around governance issues |
| **Kernel-only** (`--kernel-only`) | Run only KERNEL tier | Fast development feedback |

### Step Status

Each step results in one of four statuses:

| Status | Meaning |
|--------|---------|
| **PASS** | Step completed successfully (exit code 0) |
| **FAIL** | Step failed (non-zero exit code) |
| **SKIP** | Step explicitly skipped (user request or dependency failure) |
| **TIMEOUT** | Step exceeded time limit |

## Commands

### Running Selftest

```bash
# Full selftest (strict mode)
uv run swarm/tools/selftest.py

# Kernel-only (fastest)
uv run swarm/tools/selftest.py --kernel-only

# Degraded mode (KERNEL blocks, GOVERNANCE warns)
uv run swarm/tools/selftest.py --degraded

# Run single step
uv run swarm/tools/selftest.py --step core-checks

# Run steps up to a specific step
uv run swarm/tools/selftest.py --until devex-contract

# Verbose output with timing
uv run swarm/tools/selftest.py --verbose
```

### Plan Inspection

```bash
# Show plan (human-readable)
uv run swarm/tools/selftest.py --plan

# Show plan (JSON)
uv run swarm/tools/selftest.py --plan --json

# Show plan (JSON v2 with severity/category breakdown)
uv run swarm/tools/selftest.py --plan --json-v2
```

### Output Formats

```bash
# Human-readable (default)
uv run swarm/tools/selftest.py

# JSON (machine-parseable)
uv run swarm/tools/selftest.py --json

# JSON v2 (with severity/category breakdown)
uv run swarm/tools/selftest.py --json-v2
```

## Skipping Steps

Steps can be skipped using the `--skip-steps` flag or `SELFTEST_SKIP_STEPS` environment variable:

```bash
# Skip via flag
uv run swarm/tools/selftest.py --skip-steps flowstudio-smoke,extras

# Skip via environment variable
SELFTEST_SKIP_STEPS=flowstudio-smoke uv run swarm/tools/selftest.py

# Both can be combined (merged)
SELFTEST_SKIP_STEPS=flowstudio-smoke uv run swarm/tools/selftest.py --skip-steps extras
```

**Recommended CI usage**: Skip non-deterministic or slow steps in noisy environments:
```bash
SELFTEST_SKIP_STEPS=flowstudio-smoke make selftest
```

## Degradation Logging

When running in degraded mode, GOVERNANCE and OPTIONAL failures are logged to `selftest_degradations.log` as JSONL (one JSON object per line).

### Log Location

```
<repo-root>/selftest_degradations.log
```

### Log Schema (v1.1)

Each log entry contains:

| Field | Description |
|-------|-------------|
| `timestamp` | ISO 8601 UTC timestamp |
| `step_id` | Step identifier (e.g., "agents-governance") |
| `step_name` | Human-readable description |
| `tier` | "governance" or "optional" (never "kernel") |
| `status` | "FAIL" or "TIMEOUT" |
| `reason` | Why step ended in this status |
| `message` | Error output (stderr/stdout) |
| `severity` | "critical", "warning", or "info" |
| `remediation` | Suggested fix command |

### Example Entry

```json
{
  "timestamp": "2025-12-03T12:00:00+00:00",
  "step_id": "agents-governance",
  "step_name": "Agent definitions linting and formatting",
  "tier": "governance",
  "status": "FAIL",
  "reason": "nonzero_exit",
  "message": "Agent 'foo-bar' not found in registry",
  "severity": "warning",
  "remediation": "Run: uv run swarm/tools/selftest.py --step agents-governance for details"
}
```

### What Gets Logged as a Degradation

Degradations are logged when **all three conditions** are met:

1. **Mode is `--degraded`** — Degradation logging only happens in degraded mode
2. **Tier is `GOVERNANCE` or `OPTIONAL`** — KERNEL tier failures are never logged (they block immediately)
3. **Status is `FAIL` or `TIMEOUT`** — Only actual failures are logged (not PASS or SKIP)

This design ensures:
- KERNEL failures always block merges and get immediate attention
- Non-blocking issues are tracked without cluttering normal output
- Operators can review accumulated degradations and prioritize fixes

### Viewing Logs

```bash
# View raw log
cat selftest_degradations.log

# Pretty-print with jq
cat selftest_degradations.log | jq .

# Filter by step
cat selftest_degradations.log | jq 'select(.step_id == "agents-governance")'

# Clear log
rm selftest_degradations.log
```

## The 16 Selftest Steps

| Step | Tier | Description |
|------|------|-------------|
| `core-checks` | KERNEL | Python lint (ruff) + compile check |
| `skills-governance` | GOVERNANCE | Skills YAML validation |
| `agents-governance` | GOVERNANCE | Agent validation (bijection, colors) |
| `bdd` | GOVERNANCE | BDD feature file structure |
| `ac-status` | GOVERNANCE | Acceptance criteria tracking |
| `policy-tests` | GOVERNANCE | OPA policy validation |
| `devex-contract` | GOVERNANCE | Flow/agent/skill contracts |
| `graph-invariants` | GOVERNANCE | Flow graph connectivity |
| `flowstudio-smoke` | GOVERNANCE | Flow Studio API health check |
| `ac-coverage` | OPTIONAL | Coverage thresholds |
| `extras` | OPTIONAL | Experimental checks |

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All pass (or non-blocking failures in degraded mode) |
| `1` | Blocking failure (KERNEL in any mode, GOVERNANCE in strict) |
| `2` | Configuration error or invalid arguments |

## Troubleshooting

### Step Failures

When a step fails, selftest provides hints:

```
KERNEL failure(s): This blocks all merges
  Run: uv run swarm/tools/selftest.py --step core-checks

GOVERNANCE failure(s): Run any of:
  Run: uv run swarm/tools/selftest.py --step agents-governance
  Or try: uv run swarm/tools/selftest.py --degraded to work around
```

### Diagnosing Issues

```bash
# Run diagnostic tool
make selftest-doctor

# Run verbose mode for detailed output
uv run swarm/tools/selftest.py --verbose --step <failing-step>

# Check plan for dependencies
uv run swarm/tools/selftest.py --plan --json | jq '.steps[] | select(.id == "<step>")'
```

### Common Issues

**"flowstudio-smoke timeout"**: The Flow Studio smoke test may hang in some environments. Skip it:
```bash
SELFTEST_SKIP_STEPS=flowstudio-smoke uv run swarm/tools/selftest.py
```

**"agents-governance failure"**: Check for:
- Missing agent files vs `swarm/AGENTS.md` registry
- Color/role family mismatches
- Invalid YAML frontmatter

Run: `uv run swarm/tools/validate_swarm.py --verbose` for details.

## Integration

### CI/CD

```yaml
# GitHub Actions example
- name: Run selftest
  run: |
    uv run swarm/tools/selftest.py --json > selftest_report.json
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
      echo "Selftest failed - see report"
      cat selftest_report.json | jq '.summary'
    fi
    exit $exit_code
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
make kernel-smoke
```

### Makefile Targets

```bash
make selftest           # Full suite (strict mode)
make kernel-smoke       # Fast kernel check (~300-400ms)
make selftest-degraded  # Degraded mode
make selftest-doctor    # Diagnose issues
```

## See Also

- `swarm/SELFTEST_SYSTEM.md` - Detailed system design
- `features/selftest.feature` - BDD specification
- `swarm/tools/selftest.py` - Implementation
