# Demo Swarm Cheatsheet

> For: Daily operators who need command reference at a glance.

One-screen reference for common operations.

---

## Minimum Muscle Memory

These 5 commands cover 90% of daily work:

```bash
make dev-check        # Validate swarm health
make selftest         # Full governance suite
make flow-studio      # Launch visualizer
make validate-swarm   # Check agent/flow alignment
uv run pytest         # Run all tests
```

---

## Setup

```bash
uv sync                    # Install dependencies
pre-commit install         # (Optional) Enable pre-commit hooks
make dev-check             # Validate everything works
```

## Core Commands

| Command | What it does |
|---------|--------------|
| `make dev-check` | Full validation suite (adapters, flows, selftest) |
| `make selftest` | Run all 16 selftest steps |
| `make selftest-fast` | KERNEL-only check (~400ms) |
| `make validate-swarm` | Validate agent/flow definitions |
| `make flow-studio` | Launch Flow Studio at http://localhost:5000 |
| `make demo-run` | Populate example run artifacts |
| `make list` | Show all available make targets |

## Quick Validation

```bash
make selftest-fast         # Fast kernel check
make quick-check           # Validator only (no selftest)
make check-adapters        # Verify config → adapter sync
make check-flows           # Validate flow definitions
```

## Debugging Failures

| Problem | Command |
|---------|---------|
| Selftest failed | `make selftest-doctor` |
| See degradation log | `make selftest-degradations` |
| Get fix suggestions | `make selftest-suggest-remediation` |
| Apply fixes | `make selftest-remediate` |
| Generate incident pack | `make selftest-incident-pack` |

## Agent Operations

```bash
make agents-help           # Full workflow reference
make agents-models         # Show model distribution (inherit vs pinned)

# Edit agent config:
$EDITOR swarm/config/agents/<key>.yaml

# Then regenerate:
make gen-adapters && make check-adapters && make validate-swarm
```

## Flow Operations

```bash
make flows-help            # Flow commands reference
make gen-flows             # Regenerate flow definitions
make check-flows           # Validate flow invariants
```

## Wisdom & Maintenance

```bash
make wisdom-cycle          # Aggregate wisdom, preview cleanup (full lifecycle)
make runs-clean            # Clean stale runs from swarm/runs/
```

## Agent SDK

Run Claude Agent SDK examples (requires Claude Code login):

```bash
make agent-sdk-help        # Documentation and prerequisites
make agent-sdk-ts-demo     # Run TypeScript example (examples/agent-sdk-ts/)
make agent-sdk-py-demo     # Run Python example (examples/agent-sdk-py/)
```

## Common Recovery

**"Selftest failed on agents-governance"**
```bash
make selftest-doctor                    # Diagnose the issue
cat selftest_degradations.log           # Check persistent log
make selftest-suggest-remediation       # Get fix suggestions
```

**"Flow Studio shows 0 flows"**
```bash
make check-flows                        # Validate flow configs
make gen-flows                          # Regenerate if needed
```

**"Adapters out of sync"**
```bash
make gen-adapters                       # Regenerate from config
make check-adapters                     # Verify sync
```

## Key Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Full reference for Claude Code |
| `DEMO_RUN.md` | 2-minute walkthrough |
| `docs/WHY_DEMO_SWARM.md` | Philosophy and core ideas |
| `docs/SELFTEST_SYSTEM.md` | Selftest design & troubleshooting |
| `GLOSSARY.md` | Term definitions |

## Exit Codes

- `0` — All checks passed
- `1` — Validation/test failed
- `2` — Fatal error (environment issue)

## selftest-core Standalone

Install the selftest framework for use in any repo:

```bash
# Install selftest-core standalone
uv pip install selftest-core
# or
pipx install selftest-core

# Run selftest in any repo
selftest doctor
selftest run --config selftest.yaml
```

See `packages/selftest-core/README.md` for embedding instructions.

## Links

- Flow Studio: http://localhost:5000
- Governance view: http://localhost:5000/?tab=validation
- Operator mode: http://localhost:5000/?mode=operator
