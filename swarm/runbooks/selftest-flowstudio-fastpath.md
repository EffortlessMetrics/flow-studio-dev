# Runbook: Flow Studio Fast Path for Selftest

**Branch**: `selftest-flowstudio-fastpath` (after PR #10 merges)

## Goal

Make Flow Studio smoke checks *bounded and representative* without blocking inner-loop dev. Replace "spawn a full FastAPI app + TestClient" with a lighter-weight, in-process status probe where possible.

## Constraints

- Keep the existing governance semantics:
  - `flowstudio-smoke` remains GOVERNANCE tier as it is today
  - In strict mode, GOVERNANCE failures still block merges
  - In `--degraded`, GOVERNANCE failures go to `selftest_degradations.log`

- Maintain backward compatibility:
  - Existing CLI flags and exit codes unchanged
  - `dev-check-fast` continues to skip `flowstudio-smoke`

## Invariants (Don't Break These)

1. `SelfTestRunner.build_summary()` remains the single source of truth for selftest status
2. `/platform/status` still reads the same contract locked down in PR #10
3. `dev-check-fast` continues to skip `flowstudio-smoke` and stays < ~10–20s

## Technical Steps

### Step 1: Refactor status provider to support "in-process selftest"

In `swarm/tools/status_provider.py`:

- Introduce a helper:

  ```python
  def get_selftest_summary(self, *, degraded: bool = False) -> dict:
      """Run selftest in-process (no subprocess) and return build_summary()."""
      from . import selftest  # local import to avoid import cycles

      runner = selftest.SelfTestRunner(
          degraded=degraded,
          kernel_only=False,
          json_output=False,
          json_v2=True,
          write_report=False,
      )
      steps = selftest.get_steps_in_order()
      runner.run(steps)
      return runner.build_summary()
  ```

- Wire `get_validation_snapshot()` (or a sibling helper) to call this instead of shelling out to `uv run swarm/tools/selftest.py` for the "quick" health check path.

- Add unit tests in `tests/test_status_provider_selftest_inprocess.py`:
  - Happy-path: returns a dict with `mode`, tier flags, `failed_steps`, `hints`
  - Failure path: force a known GOVERNANCE failure and assert `governance_ok=False` and `failed_steps` contains expected IDs

### Step 2: Teach `flow_studio_smoke.py` to prefer the in-process path

In `swarm/tools/flow_studio_smoke.py`:

- Replace the `FastAPI TestClient` round-trip for `/status` with a direct call into the new helper when running in CI / headless mode:

  ```python
  from .status_provider import StatusProvider

  def _run_smoke_test_inner() -> int:
      provider = StatusProvider(...)
      snapshot = provider.get_selftest_snapshot(fast=True)  # or similar
      # Evaluate snapshot["governance"]["selftest"] and return:
      #   0: all good
      #   1: required endpoint failed / unhealthy
      #   2: fatal error
      #   3: timeout (propagated from outer runner)
  ```

- Keep the existing signature and return codes; you're just swapping a networked FastAPI call for a direct function call.

- Add `tests/test_flow_studio_smoke_fast.py`:
  - Case: all green → exit code 0, "HEALTHY" in output
  - Case: forced Flow Studio misconfig → exit code 1, includes a clear error

### Step 3: Tighten timeouts now that the implementation is cheaper

Once the blocking I/O is gone:

- Drop `flowstudio-smoke.timeout` from 45s to something like 10s
- Make the inner `DEFAULT_TIMEOUT` even smaller (e.g. 5s)
- Update `SELFTEST_SYSTEM.md` with a "Flow Studio Gate" section:
  - What's being checked
  - Why two timeouts exist
  - What "DEGRADED" vs "UNHEALTHY" mean when Flow Studio is down

### Step 4: Update dev workflows and docs

In `Makefile` / docs:

- `dev-check` still runs full selftest (including flowstudio-smoke) but should now finish in a sane amount of time
- `dev-check-fast` remains the recommended inner-loop command; mention that it skips Flow Studio smoke entirely

In `docs/selftest.md` / `swarm/SELFTEST_SYSTEM.md`:

- Document the Flow Studio gate as a first-class GOVERNANCE step
- Show example `selftest_degradations.log` entries for Flow Studio being down

### Step 5: Tests to pin behaviour

In the Flow Studio PR, your test plan should include:

```bash
# Core smoke
uv run pytest tests/test_flow_studio_smoke_fast.py -v

# Status / selftest coherence (re-use the ones from PR #10)
uv run pytest tests/test_selftest_api_contract_coherence.py -v

# Selftest & BDD
uv run pytest tests/test_selftest_bdd.py -v

# Full dev check (with bounded flowstudio-smoke)
make dev-check
make dev-check-fast
```

## Success Criteria

1. `flowstudio-smoke` step completes in < 15s (down from current 132s+)
2. `make dev-check` completes in < 30s total
3. 3 BDD scenarios that currently timeout now pass:
   - `test_failed_selftest_provides_actionable_hints`
   - `test_failure_output_includes_hints_for_debugging`
   - `test_platformstatus_includes_failure_hints_in_response`
4. All existing selftest contracts remain satisfied
5. `/platform/status` endpoint contract unchanged

## Dependencies

- PR #10 (`selftest-status-contract`) must be merged first
- This work builds on the `build_summary()` contract established there

## Files to Modify

- `swarm/tools/status_provider.py` - add in-process selftest helper
- `swarm/tools/flow_studio_smoke.py` - use in-process path
- `swarm/SELFTEST_SYSTEM.md` - document Flow Studio gate
- `docs/FLOW_STUDIO.md` - add troubleshooting section

## Files to Create

- `tests/test_status_provider_selftest_inprocess.py`
- `tests/test_flow_studio_smoke_fast.py`
