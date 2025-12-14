# Implementation Changes Summary: P5.2 Cross-Repo Template (Phase 1)

## Overview

Implemented Phase 1 (Extract Core Framework) of P5.2: Cross-Repo Selftest Template based on the design at `docs/designs/CROSS_REPO_TEMPLATE_DESIGN.md`.

## Files Created

### Package Structure

```
packages/selftest-core/
├── pyproject.toml                    # Package metadata and dependencies
├── README.md                         # Package documentation
├── selftest.yaml                     # Example configuration
├── src/
│   └── selftest_core/
│       ├── __init__.py               # Package exports (version, classes)
│       ├── runner.py                 # Core execution engine
│       ├── config.py                 # Configuration handling (YAML, dict)
│       ├── reporter.py               # JSON and console report generation
│       ├── doctor.py                 # Diagnostic tool
│       └── cli.py                    # Command-line interface
└── tests/
    ├── __init__.py
    ├── test_runner.py                # Runner tests (23 tests)
    ├── test_config.py                # Config tests (22 tests)
    └── test_doctor.py                # Doctor tests (15 tests)
```

## Key Components

### 1. Runner (`runner.py`)

Core execution engine with:
- `Tier` enum: KERNEL, GOVERNANCE, OPTIONAL
- `Severity` enum: CRITICAL, WARNING, INFO
- `Category` enum: SECURITY, PERFORMANCE, CORRECTNESS, GOVERNANCE
- `Step` dataclass: Step definition with validation
- `StepResult` dataclass: Execution result
- `SelfTestRunner` class: Main execution engine

Features:
- Three execution modes: strict, degraded, kernel-only
- Dependency management (skips steps with failed dependencies)
- Step callbacks for progress tracking
- Timeout handling
- Severity and category breakdown in results

### 2. Configuration (`config.py`)

Configuration handling with:
- `step_from_dict()`: Create Step from dictionary
- `load_steps_from_yaml()`: Load from YAML file
- `load_steps_from_list()`: Load from list of dicts
- `SelftestConfig` class: Configuration container
- `validate_steps()`: Validation (duplicates, invalid deps, cycles)

Features:
- YAML and dict configuration sources
- Command list joining (`[cmd1, cmd2]` -> `cmd1 && cmd2`)
- Automatic field defaults
- Comprehensive validation

### 3. Reporter (`reporter.py`)

Report generation with:
- `ReportMetadata` dataclass: Run context
- `ReportSummary` dataclass: Aggregate stats
- `ReportGenerator` class: JSON report generation (v1/v2 formats)
- `ConsoleReporter` class: Human-readable output

Features:
- Two report versions (v1 legacy, v2 with full metadata)
- Git branch/commit detection
- Severity and category breakdowns
- Actionable hints for failures

### 4. Doctor (`doctor.py`)

Diagnostic tool with:
- `DiagnosticCheck` dataclass: Check definition
- `SelfTestDoctor` class: Diagnostic runner
- Helper functions: `make_command_check()`, `make_python_package_check()`, `make_env_var_check()`

Features:
- Harness vs service issue separation
- HEALTHY / HARNESS_ISSUE / SERVICE_ISSUE summary
- Extensible check system
- Default checks (Python env, git state, Python syntax)

### 5. CLI (`cli.py`)

Command-line interface with subcommands:
- `selftest run`: Execute steps
- `selftest plan`: Show execution plan
- `selftest doctor`: Run diagnostics
- `selftest list`: List available steps

Options:
- `--config`: Specify config file
- `--degraded`: Degraded mode
- `--kernel-only`: KERNEL steps only
- `--step`: Run specific step
- `--json`: JSON output
- `--report`: Write report to file

## Tests Addressed

All 60 tests pass:
- `test_runner.py`: 23 tests covering Step, StepResult, SelfTestRunner, enums
- `test_config.py`: 22 tests covering step_from_dict, YAML loading, validation
- `test_doctor.py`: 15 tests covering SelfTestDoctor, helper functions

## Verification

1. Package installation verified:
   ```bash
   uv pip install -e packages/selftest-core
   ```

2. Python API verified:
   ```python
   from selftest_core import SelfTestRunner, Step, Tier
   steps = [Step(id='test', tier=Tier.KERNEL, command='true')]
   runner = SelfTestRunner(steps)
   result = runner.run()
   # Status: PASS
   ```

3. CLI verified:
   ```bash
   selftest --version  # selftest-core 0.1.0
   selftest doctor     # HEALTHY
   selftest plan       # Shows execution plan
   selftest run        # Executes steps
   ```

## Design Decisions

1. **Minimal dependencies**: Only `pyyaml>=6.0` required; `pytest` optional for dev.

2. **No Click dependency**: Used argparse for CLI to minimize dependencies. Click can be added in Phase 3.

3. **Two report versions**: v1 for backward compatibility, v2 for full metadata.

4. **Extensible doctor**: Custom checks can be added via `doctor.add_check()`.

5. **Callbacks for progress**: `on_step_start` and `on_step_complete` callbacks enable custom UIs.

## Trade-offs

1. **argparse vs Click**: Chose argparse for zero dependencies; CLI is simpler but less polished.

2. **No async support**: Steps run synchronously; async support deferred to Phase 2.

3. **No degradation logging**: Degradation JSONL logging deferred; runner tracks failures but doesn't persist.

4. **No override management**: Override escape hatch deferred to Phase 2.

## Status

**VERIFIED**: All code implemented, tests pass, standalone installation works.

## Next Steps (Phase 2)

1. Create Copier template for bootstrapping
2. Add language-specific presets (Python, Rust, Node, Go)
3. Add CI workflow templates
4. Implement `selftest init` and `selftest upgrade` commands
5. Add degradation logging and override management
