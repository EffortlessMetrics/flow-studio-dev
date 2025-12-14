# Skills Usage (Claude Code)

- Skills are global, model-invoked capabilities; domain agents (and Explore when helpful) may leverage them as tools. They are not bound per-agent; `allowed-tools` limits which tools can run while a Skill is active.
- We treat Skills as horizontal procedures (tests, lint/format, policy). Domain agents remain responsible for writing schema-bound artifacts in `RUN_BASE/*`.
- Explore is a built-in Haiku scout (read-only) that can call Skills for discovery but never owns artifacts.
- Current project Skills:
  - `test-runner`: run suites, log to `test_output.log` and `test_summary.md`.
  - `auto-linter`: run mechanical lint/format fixes when requested.
  - `policy-runner`: execute policy checks per `policy_plan.md`.
  - `heal_selftest`: diagnose and repair selftest failures by running diagnostic commands and proposing fixes (governance, critical tier).
