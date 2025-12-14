# Pull Request

## Selftest Impact

Please confirm the selftest impact of this change:

- [ ] **No selftest changes** (routine code/docs update)
- [ ] **Selftest config or tests changed**
  - [ ] AC matrix updated (`specs/spec_ledger.yaml`) if new ACs added
  - [ ] New/modified acceptance criteria documented in `features/selftest.feature`
  - [ ] Tests added for new ACs (if applicable)
  - [ ] `make validate-swarm` passes locally
  - [ ] `make selftest` passes locally

**If selftest is failing in CI:**
- [ ] I have run `make selftest-doctor` to diagnose the issue
- [ ] I have documented the failure and fix in this PR description

**For degraded mode merges** (GOVERNANCE failures only):
- [ ] KERNEL passes (`make kernel-smoke` exits 0)
- [ ] Degradation is documented in "Selftest Status" section below
- [ ] Follow-up issue created to fix degradation: #<issue-number>
- [ ] Approval obtained from tech lead: @<username>

---

## Description

<!-- Brief description of what this PR does -->

---

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Swarm config change (agents, flows, skills)
- [ ] Test-only change

---

## How Has This Been Tested?

<!-- Describe the tests you ran to verify your changes -->

- [ ] Unit tests pass (`uv run pytest tests/`)
- [ ] Selftest passes (`make selftest`)
- [ ] Manual testing performed (describe below)

**Manual testing steps:**
1.
2.
3.

---

## Checklist

### For all PRs:

- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published in downstream modules

### For swarm changes (agents, flows, skills):

- [ ] Agent config changes are in `swarm/config/agents/*.yaml` (not hand-edited frontmatter)
- [ ] I have run `make gen-adapters && make check-adapters` (for agent changes)
- [ ] I have run `make gen-flows && make check-flows` (for flow changes)
- [ ] I have run `make validate-swarm` (for all swarm changes)
- [ ] Agent colors match role family (see `CLAUDE.md` § Agent Taxonomy)
- [ ] Flow references use `RUN_BASE/<flow>/` placeholders (not hardcoded paths)

### For test changes:

- [ ] BDD scenarios are tagged with `@AC-*` (e.g., `@AC-SELFTEST-MY-FEATURE`)
- [ ] New scenarios are marked `@executable` if they have pytest implementations
- [ ] AC matrix updated (`docs/SELFTEST_AC_MATRIX.md`) for new ACs
- [ ] Pytest tests exist in `tests/test_*.py` for all `@executable` scenarios

---

## Selftest Status

<!-- Only fill this out if merging with degraded mode (GOVERNANCE failures) -->

**Status**: HEALTHY | DEGRADED

**If degraded:**

- **Tier**: GOVERNANCE (never KERNEL)
- **Failed step**: <step-id>
- **Reason for degradation**: <explanation>
- **Fix planned**: Follow-up PR #<issue-number>
- **Approved by**: @<tech-lead-username>
- **Degradation logged**: [ ] Yes (automatically logged to `selftest_degradations.log`)

---

## Related Issues

<!-- Link to GitHub issues this PR addresses -->

Closes #<issue-number>
Relates to #<issue-number>

---

## Screenshots (if applicable)

<!-- Add screenshots to help explain your changes -->

---

## Additional Context

<!-- Add any other context about the PR here -->

---

## Quick Links

**For reviewers:**

- [Selftest Developer Workflow](/docs/SELFTEST_DEVELOPER_WORKFLOW.md) — How to run selftest locally
- [Selftest Ownership](/docs/SELFTEST_OWNERSHIP.md) — Escalation paths
- [Selftest System](/docs/SELFTEST_SYSTEM.md) — Architecture deep dive
- [CLAUDE.md](/CLAUDE.md) — Swarm validation reference

**Quick commands for reviewers:**

```bash
# Check out this PR
gh pr checkout <pr-number>

# Run fast checks (KERNEL only, ~400ms)
make selftest-fast

# Run full selftest (all 16 steps)
make selftest

# Diagnose any failures
make selftest-doctor
```
