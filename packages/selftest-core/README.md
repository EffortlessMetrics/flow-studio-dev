# selftest-core

Core framework for layered selftest governance.

## Overview

`selftest-core` provides a reusable framework for implementing layered selftest governance in any project. It supports:

## Safety & Scope

`selftest-core` is a **validation framework only** (no auto-remediation):

**What it does:**
- Runs shell commands and captures exit codes/output
- Classifies results by tier (KERNEL/GOVERNANCE/OPTIONAL)
- Reports in JSON for CI integration

**What it doesn't do:**
- Auto-fix failures
- Execute remediation commands
- Make merge decisions (humans do)
- Trigger deployments

- **Three-tier model**: KERNEL (must pass), GOVERNANCE (should pass), OPTIONAL (nice-to-have)
- **Degraded mode**: Allow progress while tracking technical debt
- **Doctor diagnostic**: Separate environment issues from code issues
- **JSON reporting**: Machine-parseable reports for CI integration
- **Extensible**: Add custom steps, checks, and reporters

## Installation

```bash
pip install selftest-core
```

Or with development dependencies:

```bash
pip install selftest-core[dev]
```

## Embedding selftest-core in Your Repo

### Installation

```bash
# Using pip
pip install selftest-core

# Using uv (recommended)
uv pip install selftest-core

# Using pipx (for CLI-only usage)
pipx install selftest-core
```

### Minimal Configuration

Create a `selftest.yaml` in your repo root:

```yaml
mode: strict
steps:
  - id: lint
    tier: kernel
    command: ruff check .
    description: Python linting

  - id: test
    tier: kernel
    command: pytest tests/
    description: Unit tests
```

### Minimal Python Usage

```python
from selftest_core import SelfTestRunner, Step, Tier

# Define steps programmatically
steps = [
    Step(id="lint", tier=Tier.KERNEL, command="ruff check ."),
    Step(id="test", tier=Tier.KERNEL, command="pytest tests/"),
]

runner = SelfTestRunner(steps)
result = runner.run()

# Exit code: 0 if PASS, 1 if FAIL
exit(0 if result["status"] == "PASS" else 1)
```

### CI Integration (GitHub Actions)

```yaml
name: Selftest

on: [push, pull_request]

jobs:
  selftest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install selftest-core
        run: pip install selftest-core

      - name: Run selftest
        run: selftest run --config selftest.yaml
```

### Quick Commands

```bash
# Diagnose environment issues
selftest doctor

# Run all checks
selftest run --config selftest.yaml

# Run kernel-only (fast)
selftest run --kernel-only

# JSON output for CI
selftest run --json
```

---

## Quick Start

### Python API

```python
from selftest_core import SelfTestRunner, Step, Tier

# Define your steps
steps = [
    Step(
        id="lint",
        tier=Tier.KERNEL,
        command="ruff check .",
        description="Python linting",
    ),
    Step(
        id="test",
        tier=Tier.KERNEL,
        command="pytest tests/",
        description="Unit tests",
    ),
    Step(
        id="coverage",
        tier=Tier.OPTIONAL,
        command="pytest --cov=src --cov-fail-under=80",
        description="Coverage threshold",
    ),
]

# Run selftest
runner = SelfTestRunner(steps)
result = runner.run()

if result["status"] == "PASS":
    print("All checks passed!")
else:
    print(f"Failed steps: {result['failed_steps']}")
```

### Configuration File

Create a `selftest.yaml` file:

```yaml
mode: strict
steps:
  - id: lint
    tier: kernel
    command: ruff check .
    description: Python linting
    severity: critical
    category: correctness

  - id: typecheck
    tier: kernel
    command: mypy src/
    description: Type checking
    severity: critical
    category: correctness

  - id: test
    tier: kernel
    command: pytest tests/
    description: Unit tests
    dependencies:
      - lint

  - id: security
    tier: governance
    command: pip-audit
    description: Dependency security scan
    severity: warning
    category: security
    allow_fail_in_degraded: true

  - id: coverage
    tier: optional
    command: pytest --cov=src --cov-fail-under=80
    description: Coverage threshold
    severity: info
    category: governance
```

Then run:

```bash
selftest run
```

### CLI Usage

```bash
# Run all steps (strict mode)
selftest run

# Run with degraded mode (only KERNEL failures block)
selftest run --degraded

# Run only KERNEL tier steps
selftest run --kernel-only

# Run a specific step
selftest run --step lint

# Show execution plan
selftest plan

# Run diagnostics
selftest doctor

# Output JSON report
selftest run --json

# Write report to file
selftest run --report selftest_report.json
```

## Tier Model

The three-tier model provides graduated governance:

| Tier | Description | Failure Behavior |
|------|-------------|------------------|
| **KERNEL** | Critical checks that must pass | Always blocks |
| **GOVERNANCE** | Important checks that should pass | Blocks in strict mode; warns in degraded |
| **OPTIONAL** | Nice-to-have checks | Informational only |

### Strict Mode (default)

- KERNEL and GOVERNANCE failures block
- OPTIONAL failures are informational

### Degraded Mode

- Only KERNEL failures block
- GOVERNANCE failures become warnings
- Progress allowed while tracking debt

### Kernel-Only Mode

- Runs only KERNEL tier steps
- Fastest path for quick validation

## Step Configuration

Each step supports these fields:

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `id` | Yes | - | Unique step identifier |
| `tier` | Yes | - | kernel, governance, or optional |
| `command` | Yes | - | Shell command to execute |
| `description` | No | "" | Human-readable description |
| `severity` | No | warning | critical, warning, or info |
| `category` | No | correctness | security, performance, correctness, or governance |
| `timeout` | No | 60 | Max execution time (seconds) |
| `dependencies` | No | [] | Step IDs that must pass first |
| `allow_fail_in_degraded` | No | false | Treat as warning in degraded mode |

## Doctor Diagnostic

The doctor helps diagnose why selftest is failing:

```python
from selftest_core.doctor import SelfTestDoctor

doctor = SelfTestDoctor()
diagnosis = doctor.diagnose()

if diagnosis["summary"] == "HARNESS_ISSUE":
    print("Environment problem - fix before running selftest")
elif diagnosis["summary"] == "SERVICE_ISSUE":
    print("Code issue - run selftest for details")
else:
    print("All healthy!")
```

### Diagnostic Summary

- **HEALTHY**: Everything works
- **HARNESS_ISSUE**: Environment problems (Python, git, toolchain)
- **SERVICE_ISSUE**: Code or configuration is broken

### Custom Checks

Add custom diagnostic checks:

```python
from selftest_core.doctor import (
    SelfTestDoctor,
    make_command_check,
    make_python_package_check,
)

doctor = SelfTestDoctor()

# Check for a required command
doctor.add_check(make_command_check(
    name="docker",
    command="docker --version",
    error_message="Install Docker: https://docs.docker.com/get-docker/",
))

# Check for a Python package
doctor.add_check(make_python_package_check("numpy"))

diagnosis = doctor.diagnose()
```

## Reporting

### JSON Report

```python
from selftest_core import SelfTestRunner
from selftest_core.reporter import ReportGenerator

runner = SelfTestRunner(steps)
result = runner.run()

generator = ReportGenerator(result)

# Write v2 report (with full metadata)
generator.write_json("report.json", version="v2")

# Or get JSON string
json_str = generator.to_json()
```

### Console Output

```python
from selftest_core.reporter import ConsoleReporter

reporter = ConsoleReporter(result, verbose=True)
reporter.print_full_report()
```

## Integration Examples

### GitHub Actions

```yaml
name: Selftest

on: [push, pull_request]

jobs:
  selftest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install selftest-core
        run: pip install selftest-core

      - name: Run kernel smoke
        run: selftest run --kernel-only

      - name: Run full selftest
        run: selftest run

      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: selftest-report
          path: selftest_report.json
```

### Makefile

```makefile
.PHONY: selftest selftest-degraded kernel-smoke

selftest:
	selftest run

selftest-degraded:
	selftest run --degraded

kernel-smoke:
	selftest run --kernel-only

selftest-doctor:
	selftest doctor
```

## API Reference

### Core Classes

- `SelfTestRunner`: Main execution engine
- `Step`: Step definition dataclass
- `StepResult`: Step execution result
- `Tier`: Tier enum (KERNEL, GOVERNANCE, OPTIONAL)
- `Severity`: Severity enum (CRITICAL, WARNING, INFO)
- `Category`: Category enum (SECURITY, PERFORMANCE, CORRECTNESS, GOVERNANCE)

### Configuration

- `SelftestConfig`: Configuration container
- `load_config()`: Load config from file or dict
- `load_steps_from_yaml()`: Load steps from YAML file
- `validate_steps()`: Validate step consistency

### Reporting

- `ReportGenerator`: Generate JSON reports
- `ConsoleReporter`: Console output formatting

### Diagnostics

- `SelfTestDoctor`: Diagnostic runner
- `DiagnosticCheck`: Custom check definition
- `make_command_check()`: Create command-based check
- `make_python_package_check()`: Create package check

## License

MIT
