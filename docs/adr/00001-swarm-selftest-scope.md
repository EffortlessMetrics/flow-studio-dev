# ADR-00001: Swarm Selftest vs Service Selftest

**Status:** Accepted
**Date:** 2025-11-30
**Deciders:** Demo Swarm Team

## Context

This repo implements a **swarm kernel** (`demo-swarm-dev`) that orchestrates agentic flows. As the swarm matures, we now have two related but distinct "selftest" concepts:

### 1. Swarm Selftest (this repo, Python)
- **Scope:** Validates swarm configuration health
- **What it checks:**
  - Agent definitions (bijection, frontmatter, color schemes)
  - Skill definitions and references
  - Flow specifications (syntax, invariants, references)
  - BDD feature structure for swarm examples
  - Governance contracts (agent registry, flow configs)
- **Implementation:**
  - Python tools in `swarm/tools/selftest.py` and siblings
  - Layered severity (Kernel / Governance / Optional tiers)
  - JSON report export (`selftest_report.json`)
  - Doctor + override tooling for degraded mode
  - CLI entry points: `make selftest`, `make kernel-smoke`, `make selftest-degraded`
- **Artifacts:**
  - `swarm/runs/<run-id>/build/selftest_report.json`
  - Status summary for Flow 6 (Wisdom) analysis

### 2. Service Selftest (Rust Template, `cargo xtask selftest`)
- **Scope:** Validates a concrete Rust service cell kernel
- **What it checks (design):**
  - Rust syntax, format, clippy (core-checks)
  - xtask scaffolding and BDD integration
  - Spec ledger runtime (if service uses specs)
  - Policy/OPA validation (if applicable)
  - Acceptance criteria coverage (if service defines AC)
  - Graph invariants and flow connectivity (if service uses flows)
- **Implementation:**
  - Rust code in `xtask/selftest/` (in the service template)
  - Same tier/severity/JSON pattern as swarm selftest (design alignment)
  - Runs via: `cargo xtask selftest` in the Rust workspace
- **Artifacts:**
  - `./target/selftest/report.json` (or similar service-level path)
  - Not in swarm's `RUN_BASE/` (that's for flow artifacts)

## Problem

The naming overlap is intentional (both implement the same **design pattern** for layered health checks), but the scopes are completely different:

- **Swarm selftest** validates *configuration orchestration*.
- **Service selftest** validates *kernel implementation*.

Without explicit clarification, future contributors might:
- Try to use the Python swarm selftest to validate Rust services (wrong layer)
- Assume one is a "template" for the other (they're siblings, not parent/child)
- Duplicate logic across repos unnecessarily

## Decision

We adopt the following naming and scoping discipline:

### Naming Convention
- This repo's health check is called **Swarm Selftest** (not "the selftest")
- References consistently say:
  - "Swarm selftest" when discussing this repo's Python tools
  - "Service selftest" when discussing the Rust template's xtask integration
  - "10-step selftest pattern" when referring to the shared design (kernel + governance + optional tiers)

### Scoping
- **Swarm Selftest** is scoped to:
  - Swarm configuration (agents, flows, skills)
  - Swarm governance invariants (role families, color schemes, RUN_BASE usage)
  - Teaching the 10-step pattern via example
  - **Not:** validating service-level code, tests, or binaries

- **Service Selftest** (in rust-as-spec template) is scoped to:
  - Service kernel health (Rust code, xtask, binary readiness)
  - Service-level governance (AC, OPA, specs)
  - **Not:** swarm configuration (that's upstream in Flow 1)

### Integration Points (Future)
When the swarm orchestrator (Flow 6 or a health-check agent) needs to reason about a concrete Rust service:

1. It will **invoke** `cargo xtask selftest` as an external subprocess
2. Parse the JSON output (once service template adds JSON export)
3. Include service health in the swarm's wisdom/feedback loop
4. **Not** embed or re-implement service selftest logic in Python

This keeps concerns cleanly separated and allows each kernel to evolve independently.

## Consequences

### Documentation
- `CLAUDE.md` will be updated to consistently use "Swarm selftest" terminology
- `SELFTEST_SYSTEM.md` clarifies scope as "swarm configuration validation"
- When rust-as-spec grows its `cargo xtask selftest`, we'll add a note to this repo's docs
- Flow 6 (Wisdom) spec will mention selftest reports as optional inputs for correlation

### Implementation
- The Python swarm selftest remains in place; no changes to code structure
- Rust service template will implement its own `xtask selftest` when ready
- Both will use JSON export for interoperability
- The swarm's `explore` or `context-loader` agent can read service selftest reports if needed

### Risk Mitigation
- ADR makes the distinction explicit and discoverable
- When new agents reference "selftest," docs will clarify which one
- Example runs under `swarm/examples/` will show swarm selftest output (not service output)

## Alternatives Considered

### A. Rename Swarm Selftest to Something Else
- **Pros:** Avoids naming confusion with service selftest
- **Cons:** The pattern is called "10-step selftest," and both implementations follow it. Renaming to "validation," "health," or "governance-check" obscures the shared design.
- **Rejected:** Too much rename friction; clarification via docs/ADR is better.

### B. Remove Python Swarm Selftest; Keep Only Service Selftest
- **Pros:** Reduces machinery in this repo
- **Cons:** Loses a useful agent-friendly interface for swarm health; discards already-implemented tooling; makes demo-swarm less self-contained.
- **Rejected:** The swarm needs its own health story; service health is separate concern.

### C. Merge Both into a Single "Universal Selftest"
- **Pros:** Single codebase, single pattern
- **Cons:** Forces Rust/Python cross-language coupling; makes both less portable; testing becomes complex
- **Rejected:** Each kernel is independent; shared pattern ≠ shared code.

## References

- `swarm/SELFTEST_SYSTEM.md` — Swarm selftest system documentation and CLI
- `swarm/positioning.md` — Swarm philosophy and architecture
- `swarm/infrastructure/` — Production extension patterns (for service-level integration)
- FUTURE: `rust-as-spec` repo's ADR on service xtask selftest design

## Related Issues

- Diagonal: When deploying a swarm-orchestrated service, Flow 5 (Deploy) may consume the service's selftest output
- Feedback: Flow 6 (Wisdom) may correlate swarm health with service health in learnings/regressions
