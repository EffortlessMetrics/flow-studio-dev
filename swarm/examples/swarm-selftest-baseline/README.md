# Swarm Selftest Baseline Example

This directory contains a captured example of the **Swarm Selftest** output for a healthy swarm configuration.

## Files

- **`selftest_report.json`** — Full structured output from `make selftest`
  - Tier breakdown (Kernel, Governance, Optional)
  - Per-step status, exit codes, and timing
  - Metadata (run ID, timestamp, hostname, git state)
  - Summary statistics

- **`status_snapshot.json`** — Compact governance status snapshot
  - High-level overview for `/platform/status` endpoints
  - Kernel/Governance/Optional health summaries
  - Pass/fail counts by severity

- **`notes.md`** — Commentary on this snapshot
  - What this particular run illustrates
  - Key step statuses and their meanings
  - How to interpret the report structure

## Purpose

This is **teaching material**, not an active test or CI artifact. It exists to:

- Show agents how to interpret selftest reports
- Provide a stable fixture for Flow 6 (Wisdom) integration examples
- Demonstrate the 10-step pattern in action

## How to Update

To refresh this example with current swarm output:

```bash
cd /path/to/flow-studio
make selftest
# Copy the report to this directory:
cp swarm/runs/<run-id>/build/selftest_report.json swarm/examples/swarm-selftest-baseline/selftest_report.json
```

Then update `notes.md` with any changes to the step structure or new observations.

## Related Documentation

- `swarm/SELFTEST_SYSTEM.md` — Complete selftest system specification
- `docs/adr/00001-swarm-selftest-scope.md` — ADR clarifying swarm vs service selftest scopes
