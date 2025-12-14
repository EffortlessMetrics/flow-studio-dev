# Implementation Plan

## Subtasks

- ST1: Add handler `handlers::health::health_handler`
  - Description: implement GET /health returning 200 + {"status":"ok"}
  - Affected files: `src/handlers/health.rs`, `src/router.rs`
  - Related tests: `tests/health_check_tests.rs`
  - Dependencies: routing infra

- ST2: Add unit tests for handler
- ST3: Add integration test that spins server on random port and requests /health
- ST4: Update README with endpoint note

## Rollout

- Deploy as a feature branch; no DB migration required.
