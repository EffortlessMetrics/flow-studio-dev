---
description: Run Flow 4 (Code → Artifact): verify receipts, contracts, security, policies; recommend merge or bounce.
---

# Flow 4: Code → Artifact (Gate)

You are orchestrating Flow 4 of the SDLC swarm.

## RUN_BASE

All artifacts for this flow belong under:

```
RUN_BASE = swarm/runs/<run-id>/gate/
```

where `<run-id>` matches the identifier from Flows 1-3.

Ensure this directory exists before delegating to agents.

## Your goal

- Verify build receipts exist and are complete
- Check API/schema contracts
- Scan security and coverage
- Enforce policies
- Decide: MERGE / BOUNCE / ESCALATE

**Before you begin**: Use the TodoWrite tool to create a TODO list of the audits, checks, and decision steps. This helps track which gates have been verified.

If you encounter missing receipts or unclear state, **document it and continue with available information**. Gate agents should note gaps in their reports rather than blocking.

## Subagents to use

Domain agents (Flow 4 specific):
- receipt-checker
- contract-enforcer
- security-scanner
- coverage-enforcer
- gate-fixer (mechanical only)
- merge-decider

Cross-cutting agents:
- risk-analyst
- policy-analyst
- gh-reporter

## Orchestration outline

1. **Verify receipts**
   - `receipt-checker` -> `receipt_audit.md`

2. **Check contracts** (can run in parallel with security/coverage)
   - `contract-enforcer` -> `contract_compliance.md`

3. **Security scan** (can run in parallel with contracts/coverage)
   - `security-scanner` -> `security_scan.md`

4. **Coverage** (can run in parallel with contracts/security)
   - `coverage-enforcer` -> `coverage_audit.md`

5. **Mechanical fixes** (after verification agents complete)
   - `gate-fixer` -> `gate_fix_summary.md` (lint/format/docs only)

6. **Risk assessment**
   - `risk-analyst` -> `risk_assessment.md`

7. **Policy compliance**
   - `policy-analyst` -> `policy_analysis.md`

8. **Merge decision**
   - `merge-decider` -> `merge_decision.md` (MERGE/BOUNCE/ESCALATE)

9. **Report to GitHub**
   - `gh-reporter` -> post verdict to PR

## Bounce Semantics

Gate-fixer applies **mechanical fixes only**. For non-mechanical issues:

**BOUNCE to Build (Flow 3)**:
- Logic errors
- Test failures
- API contract violations
- Security vulnerabilities
- Coverage below threshold

**BOUNCE to Plan (Flow 2)**:
- Design flaws
- Architecture issues
- Missing requirements

## Status States

Agents set status in their output artifacts:

- **VERIFIED**: Check passed; here's why.
- **UNVERIFIED**: Check has concerns; here are the issues.
- **BLOCKED**: Couldn't run check; here's what's missing.

`merge-decider` synthesizes all statuses into a merge decision.

## Merge Decision States

`merge-decider` outputs one of:

- **MERGE**: All checks pass or concerns are acceptable; ready to deploy.
- **BOUNCE**: Issues found; specifies target flow (Build or Plan) and reasons.
- **ESCALATE**: Needs human judgment; explains why automated decision isn't sufficient.
