# Design Document: P5.1 Distributed Selftest Execution

## Status

**Draft** - Ready for ADR authoring

## Overview

This document proposes architecture for distributed/parallel execution of selftest steps to reduce CI feedback time. The current sequential implementation takes approximately 2 minutes for all 11 steps; parallel execution targets a 2.5-4x speedup.

---

## Problem Statement

### Current State

The selftest system runs 11 steps sequentially:

```
core-checks (KERNEL) ~10-30s
    |
    v
skills-governance (GOVERNANCE) ~100ms
    |
    v
agents-governance (GOVERNANCE) ~1s
    |
    v
bdd (GOVERNANCE) ~500ms
    |
    v
ac-status (GOVERNANCE) ~100ms
    |
    v
policy-tests (GOVERNANCE) ~500ms
    |
    v
devex-contract (GOVERNANCE) ~2s [depends: core-checks]
    |
    v
graph-invariants (GOVERNANCE) ~500ms [depends: devex-contract]
    |
    v
flowstudio-smoke (GOVERNANCE) ~200ms
    |
    v
ac-coverage (OPTIONAL) ~100ms
    |
    v
extras (OPTIONAL) ~100ms
```

**Total sequential time**: ~15-35 seconds (excluding core-checks cargo tests)

### Pain Points

1. **Sequential execution is slow**: Steps that could run in parallel wait unnecessarily
2. **CI feedback delayed**: Developers wait for full selftest even when only specific areas are affected
3. **Resource underutilization**: Multi-core systems run single-threaded validation
4. **Dependency bottlenecks**: Linear chain when only some steps have real dependencies

### Goals

1. Reduce selftest wall-clock time by 2.5-4x through parallelization
2. Maintain correctness: respect step dependencies
3. Preserve existing CLI interface (backward compatible)
4. Enable future distributed execution across workers

---

## Step Dependency Graph

Based on analysis of `selftest_config.py`, the actual dependency graph is:

```
                         core-checks (KERNEL)
                               |
           +-------------------+-------------------+
           |                   |                   |
           v                   v                   v
   skills-governance    agents-governance    bdd
           |                   |                   |
           v                   v                   v
      ac-status         policy-tests      flowstudio-smoke
           |                   |
           v                   v
   devex-contract <------------+
           |
           v
   graph-invariants
           |
           v
      ac-coverage
           |
           v
        extras
```

**Actual dependencies from code**:
- `devex-contract` depends on `core-checks`
- `graph-invariants` depends on `devex-contract`
- All other GOVERNANCE steps have no dependencies (can run after core-checks)

### Parallelization Waves

Based on the dependency graph:

**Wave 0** (blocking, must complete first):
- `core-checks` (KERNEL tier - must pass before any GOVERNANCE)

**Wave 1** (parallel after core-checks):
- `skills-governance`
- `agents-governance`
- `bdd`
- `ac-status`
- `policy-tests`
- `flowstudio-smoke`

**Wave 2** (after Wave 1 + core-checks):
- `devex-contract` (explicitly depends on core-checks)

**Wave 3** (after devex-contract):
- `graph-invariants` (depends on devex-contract)

**Wave 4** (after all GOVERNANCE):
- `ac-coverage` (OPTIONAL)
- `extras` (OPTIONAL)

---

## Architecture Options

### Option A: ProcessPoolExecutor (Recommended for MVP)

**Summary**: Use Python's `concurrent.futures.ProcessPoolExecutor` for local parallelization within a single machine. Simple, stdlib-only, no infrastructure.

**Implementation**:

```python
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List

class DistributedSelfTestRunner:
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.results: Dict[str, SelfTestResult] = {}

    def run_wave(self, steps: List[SelfTestStep]) -> List[SelfTestResult]:
        """Execute a wave of independent steps in parallel."""
        with ProcessPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(self._run_step_isolated, step): step
                for step in steps
            }
            results = []
            for future in as_completed(futures):
                step = futures[future]
                try:
                    result = future.result(timeout=60)
                    results.append(result)
                except Exception as e:
                    results.append(self._create_error_result(step, e))
            return results

    def run_distributed(self) -> int:
        """Execute selftest with wave-based parallelization."""
        # Wave 0: KERNEL (blocking)
        wave0_results = self.run_wave([get_step_by_id("core-checks")])
        if not all(r.passed for r in wave0_results):
            return 1  # KERNEL failure blocks all

        # Wave 1: Independent GOVERNANCE steps
        wave1_steps = [
            get_step_by_id(s) for s in [
                "skills-governance", "agents-governance", "bdd",
                "ac-status", "policy-tests", "flowstudio-smoke"
            ]
        ]
        wave1_results = self.run_wave(wave1_steps)

        # Wave 2: devex-contract (depends on core-checks)
        wave2_results = self.run_wave([get_step_by_id("devex-contract")])

        # Wave 3: graph-invariants (depends on devex-contract)
        if all(r.passed for r in wave2_results):
            wave3_results = self.run_wave([get_step_by_id("graph-invariants")])
        else:
            wave3_results = [self._create_skip_result(get_step_by_id("graph-invariants"))]

        # Wave 4: OPTIONAL steps
        wave4_steps = [get_step_by_id(s) for s in ["ac-coverage", "extras"]]
        wave4_results = self.run_wave(wave4_steps)

        # Aggregate and return
        return self._compute_exit_code()

    def _run_step_isolated(self, step: SelfTestStep) -> SelfTestResult:
        """Run a step in an isolated subprocess."""
        # Each step runs in its own process
        # Returns serializable result dict
        pass
```

**Strengths**:
- Stdlib only, no external dependencies
- Works on any Python 3.8+ system
- Simple mental model: waves execute in order, steps within wave are parallel
- Backward compatible: `--distributed` flag opts in

**Weaknesses**:
- Limited to single machine
- Process spawn overhead (~100ms per process on Linux)
- IPC overhead for result serialization

**Estimated effort**: 1-2 weeks

---

### Option B: GitHub Actions Matrix Strategy

**Summary**: Leverage GitHub Actions' native matrix strategy to run steps as parallel jobs. Zero infrastructure; uses existing CI.

**Implementation** (`.github/workflows/selftest-distributed.yml`):

```yaml
name: Distributed Selftest

on: [push, pull_request]

jobs:
  kernel:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - name: Run core-checks
        run: uv run swarm/tools/selftest.py --step core-checks
      - name: Upload result
        uses: actions/upload-artifact@v4
        with:
          name: kernel-result
          path: selftest_report.json

  governance:
    needs: kernel
    runs-on: ubuntu-latest
    strategy:
      matrix:
        step: [skills-governance, agents-governance, bdd, ac-status, policy-tests, flowstudio-smoke]
      fail-fast: false
    steps:
      - uses: actions/checkout@v4
      - name: Run ${{ matrix.step }}
        run: uv run swarm/tools/selftest.py --step ${{ matrix.step }}
      - name: Upload result
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.step }}-result
          path: selftest_report.json

  devex:
    needs: kernel
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run devex-contract
        run: uv run swarm/tools/selftest.py --step devex-contract

  graph:
    needs: devex
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run graph-invariants
        run: uv run swarm/tools/selftest.py --step graph-invariants

  aggregate:
    needs: [kernel, governance, devex, graph]
    runs-on: ubuntu-latest
    steps:
      - name: Download all results
        uses: actions/download-artifact@v4
      - name: Aggregate results
        run: python scripts/aggregate_selftest.py
```

**Strengths**:
- Native GitHub parallelization
- No infrastructure to manage
- Visual job graph in GitHub UI
- Scales to any number of parallel jobs

**Weaknesses**:
- Limited to CI context (can't run locally in parallel)
- Job startup overhead (~30s per job)
- Artifact download/upload latency
- Requires aggregation script

**Estimated effort**: 1 week

---

### Option C: Celery Workers with Redis

**Summary**: Distributed task queue using Celery for cross-machine parallelization. Production-grade, highly scalable, complex setup.

**Implementation**:

```python
# tasks.py
from celery import Celery

app = Celery('selftest', broker='redis://localhost:6379/0')

@app.task(bind=True, max_retries=3)
def run_selftest_step(self, step_id: str) -> dict:
    """Execute a single selftest step as a Celery task."""
    from selftest_config import get_step_by_id
    from selftest import SelfTestRunner

    step = get_step_by_id(step_id)
    runner = SelfTestRunner()
    result = runner.run_step(step, {})
    return result.to_dict()

# orchestrator.py
from celery import group, chain

def run_distributed_selftest():
    """Orchestrate distributed selftest execution."""
    # Wave 0: KERNEL
    kernel_task = run_selftest_step.s("core-checks")
    kernel_result = kernel_task.apply_async().get(timeout=120)

    if kernel_result["status"] != "PASS":
        return {"status": "FAIL", "blocker": "core-checks"}

    # Wave 1: Parallel GOVERNANCE
    wave1_group = group([
        run_selftest_step.s(step_id)
        for step_id in ["skills-governance", "agents-governance", "bdd",
                        "ac-status", "policy-tests", "flowstudio-smoke"]
    ])
    wave1_results = wave1_group.apply_async().get(timeout=300)

    # Wave 2-3: Sequential dependencies
    chain_task = chain(
        run_selftest_step.s("devex-contract"),
        run_selftest_step.s("graph-invariants")
    )
    chain_results = chain_task.apply_async().get(timeout=120)

    # Aggregate
    return aggregate_results([kernel_result] + wave1_results + chain_results)
```

**Strengths**:
- True distributed execution across machines
- Battle-tested task queue
- Retry logic, result backends, monitoring
- Scales horizontally

**Weaknesses**:
- Requires Redis/RabbitMQ infrastructure
- Operational complexity (broker, workers, monitoring)
- Overkill for single-repo selftest
- Dependency management across workers

**Estimated effort**: 3-4 weeks

---

## Result Aggregation

All options need a common result aggregation format:

```json
{
  "version": "2.0",
  "execution_mode": "distributed",
  "run_id": "distributed-1701432000",
  "metadata": {
    "timestamp": "2025-12-01T12:00:00Z",
    "workers": 4,
    "git_branch": "main",
    "git_commit": "abc123"
  },
  "waves": [
    {
      "wave": 0,
      "steps": ["core-checks"],
      "duration_ms": 25000,
      "all_passed": true,
      "results": [
        {
          "step_id": "core-checks",
          "status": "PASS",
          "duration_ms": 25000,
          "worker": "main"
        }
      ]
    },
    {
      "wave": 1,
      "steps": ["skills-governance", "agents-governance", "bdd", "ac-status", "policy-tests", "flowstudio-smoke"],
      "duration_ms": 1200,
      "all_passed": true,
      "parallel": true,
      "results": [
        {"step_id": "skills-governance", "status": "PASS", "duration_ms": 100, "worker": "worker-1"},
        {"step_id": "agents-governance", "status": "PASS", "duration_ms": 800, "worker": "worker-2"},
        {"step_id": "bdd", "status": "PASS", "duration_ms": 450, "worker": "worker-3"},
        {"step_id": "ac-status", "status": "PASS", "duration_ms": 50, "worker": "worker-4"},
        {"step_id": "policy-tests", "status": "PASS", "duration_ms": 400, "worker": "worker-1"},
        {"step_id": "flowstudio-smoke", "status": "PASS", "duration_ms": 200, "worker": "worker-2"}
      ]
    },
    {
      "wave": 2,
      "steps": ["devex-contract"],
      "duration_ms": 1800,
      "all_passed": true,
      "results": [
        {"step_id": "devex-contract", "status": "PASS", "duration_ms": 1800, "worker": "main"}
      ]
    },
    {
      "wave": 3,
      "steps": ["graph-invariants"],
      "duration_ms": 400,
      "all_passed": true,
      "results": [
        {"step_id": "graph-invariants", "status": "PASS", "duration_ms": 400, "worker": "main"}
      ]
    },
    {
      "wave": 4,
      "steps": ["ac-coverage", "extras"],
      "duration_ms": 150,
      "all_passed": true,
      "parallel": true,
      "results": [
        {"step_id": "ac-coverage", "status": "PASS", "duration_ms": 80, "worker": "worker-1"},
        {"step_id": "extras", "status": "PASS", "duration_ms": 70, "worker": "worker-2"}
      ]
    }
  ],
  "summary": {
    "total_steps": 11,
    "passed": 11,
    "failed": 0,
    "skipped": 0,
    "sequential_estimate_ms": 30000,
    "actual_duration_ms": 28550,
    "parallel_duration_ms": 27350,
    "speedup": "1.1x",
    "status": "PASS"
  }
}
```

---

## Configuration Schema

```yaml
# swarm/config/selftest_distributed.yaml
distributed:
  enabled: true
  max_workers: 4
  timeout_per_step_seconds: 60
  timeout_total_seconds: 300

  # Wave definitions (derived from dependency graph)
  waves:
    - name: kernel
      blocking: true
      steps:
        - core-checks

    - name: governance-parallel
      blocking: false
      parallel: true
      steps:
        - skills-governance
        - agents-governance
        - bdd
        - ac-status
        - policy-tests
        - flowstudio-smoke

    - name: devex
      blocking: false
      depends_on: [kernel]
      steps:
        - devex-contract

    - name: graph
      blocking: false
      depends_on: [devex]
      steps:
        - graph-invariants

    - name: optional
      blocking: false
      parallel: true
      steps:
        - ac-coverage
        - extras

  # Error handling
  on_wave_failure:
    kernel: abort        # Stop immediately
    governance: continue # Complete wave, then decide
    optional: continue   # Always continue

  # Retry configuration
  retry:
    max_attempts: 2
    retry_on_timeout: true
    retry_delay_seconds: 5
```

---

## CLI Interface

```bash
# Sequential (current, unchanged)
make selftest
uv run swarm/tools/selftest.py

# Distributed (new)
make selftest-distributed
uv run swarm/tools/selftest.py --distributed

# With worker count
make selftest-distributed WORKERS=8
uv run swarm/tools/selftest.py --distributed --workers 8

# Distributed with JSON output
uv run swarm/tools/selftest.py --distributed --json-v2

# Show distributed plan
uv run swarm/tools/selftest.py --distributed --plan

# Distributed kernel-only (Wave 0 only)
uv run swarm/tools/selftest.py --distributed --kernel-only
```

---

## Error Handling

### Wave Failure Semantics

1. **If any step in Wave N fails**:
   - Complete all running steps in Wave N (don't abort mid-wave)
   - Collect all results for reporting
   - Evaluate whether to proceed to Wave N+1

2. **Wave continuation rules**:
   - KERNEL wave (Wave 0): Any failure aborts entire run
   - GOVERNANCE waves: Failures logged, continue to next wave
   - OPTIONAL waves: Failures logged, continue

3. **Timeout handling**:
   - Per-step timeout: 60 seconds default
   - Total run timeout: 300 seconds default
   - Timeout treated as step failure

4. **Worker failure**:
   - If worker process dies, mark step as FAIL
   - Log error details in result
   - Continue with remaining workers

### Error Aggregation

```python
class DistributedErrorAggregator:
    def aggregate_wave_errors(self, wave_results: List[SelfTestResult]) -> WaveError:
        """Aggregate errors from a wave of parallel results."""
        errors = []
        for result in wave_results:
            if not result.passed:
                errors.append({
                    "step_id": result.step.id,
                    "tier": result.step.tier.value,
                    "exit_code": result.exit_code,
                    "stderr": result.stderr[:500],
                    "worker": result.worker_id,
                })

        return WaveError(
            wave_id=wave_results[0].wave_id,
            error_count=len(errors),
            errors=errors,
            blocking=any(e["tier"] == "kernel" for e in errors),
        )
```

---

## Performance Targets

| Mode | Current Baseline | Target | Expected Speedup |
|------|-----------------|--------|------------------|
| Sequential | ~30s | - | 1.0x |
| Distributed (2 workers) | - | ~18s | 1.7x |
| Distributed (4 workers) | - | ~12s | 2.5x |
| Distributed (8 workers) | - | ~8s | 3.8x |

**Bottleneck analysis**:
- `core-checks` dominates (~25s with cargo tests)
- Without cargo tests (Python-only): ~5s sequential, ~2s distributed
- Wave 1 parallelization yields highest gains (6 steps in parallel)

**Diminishing returns**:
- Beyond 6 workers, limited by Wave 1 step count
- Process spawn overhead (~100ms) limits gains on fast steps

---

## Implementation Plan

### Phase 1: ProcessPoolExecutor MVP (Recommended)

**Week 1**:
1. Add `DistributedSelfTestRunner` class to `selftest.py`
2. Implement wave-based execution with `ProcessPoolExecutor`
3. Add `--distributed` and `--workers` CLI flags
4. Update JSON output schema for wave results

**Week 2**:
1. Implement result aggregation
2. Add distributed plan output (`--distributed --plan`)
3. Write tests for parallel execution
4. Update documentation

**Deliverables**:
- `selftest.py` with `--distributed` flag
- `selftest_distributed_config.yaml`
- Updated `SELFTEST_SYSTEM.md`
- Test coverage for wave execution

### Phase 2: GitHub Actions Integration

**Week 3**:
1. Create `.github/workflows/selftest-distributed.yml`
2. Implement artifact-based result passing
3. Add aggregation script
4. Visual workflow graph

### Phase 3: Celery Workers (Future)

**Deferred**: Only if cross-machine distribution is required.

---

## Trade-Off Analysis

| Criterion | Option A (ProcessPool) | Option B (GH Actions) | Option C (Celery) |
|-----------|----------------------|---------------------|------------------|
| **Complexity** | Low | Medium | High |
| **Infrastructure** | None | GitHub | Redis + Workers |
| **Local execution** | Yes | No | Requires broker |
| **CI integration** | Manual | Native | Manual |
| **Scalability** | Single machine | Cloud workers | Unlimited |
| **Effort** | 1-2 weeks | 1 week | 3-4 weeks |
| **Maintenance** | Low | Low | High |

---

## Recommendation

**Recommended Option: A (ProcessPoolExecutor)**

### Rationale

1. **Scope fit**: Delivers 2-3x speedup with minimal complexity
2. **Swarm alignment**: Works locally; no external dependencies
3. **Backward compatible**: Opt-in via `--distributed` flag
4. **Fast shipping**: 1-2 weeks to completion
5. **Future extensible**: Can add GH Actions (Option B) later as CI optimization

### When to Consider Option B

Adopt Option B additionally if:
- CI time is critical bottleneck
- Native GitHub parallelization preferred
- Visual workflow graph adds value

### When to Consider Option C

Adopt Option C only if:
- Cross-machine distribution required
- Thousands of selftest steps (not current scale)
- Event-driven architecture already in use

---

## Acceptance Criteria

| AC ID | Description | Validation |
|-------|-------------|------------|
| AC-DIST-001 | `--distributed` flag enables parallel execution | CLI test |
| AC-DIST-002 | Wave 0 (KERNEL) blocks Wave 1+ | Integration test |
| AC-DIST-003 | Wave 1 steps run in parallel | Timing test |
| AC-DIST-004 | Step dependencies respected | Unit test |
| AC-DIST-005 | JSON output includes wave metadata | Schema test |
| AC-DIST-006 | Speedup >= 2x with 4 workers | Performance test |
| AC-DIST-007 | Timeout handling per step | Unit test |
| AC-DIST-008 | Backward compatible (no flag = sequential) | Regression test |

---

## Open Questions

1. **Should Wave 1 wait for all steps or use first-failure abort?**
   - Current design: Wait for all, then aggregate
   - Alternative: Abort remaining on first failure

2. **How to handle step stdout/stderr in parallel?**
   - Current design: Capture per-step, aggregate in result
   - Alternative: Interleaved output with step prefixes

3. **Should we auto-detect optimal worker count?**
   - Current design: Manual `--workers N` flag
   - Alternative: Default to `os.cpu_count() - 1`

---

## References

- `swarm/tools/selftest.py` - Current sequential implementation
- `swarm/tools/selftest_config.py` - Step definitions and dependencies
- `swarm/SELFTEST_SYSTEM.md` - Selftest documentation
- `swarm/runs/selftest-resilience/plan/design_options.md` - Prior design work

---

## Status

**VERIFIED** - Design document complete with clear architecture options, trade-offs, and recommendation. Ready for ADR authoring.
