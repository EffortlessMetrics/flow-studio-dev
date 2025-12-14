---
description: Run Flow 5 (Artifact -> Prod): execute GitHub-native deployment, monitor CI, verify, create audit trail.
---

# Flow 5: Artifact -> Prod (Deploy)

You are orchestrating Flow 5 of the SDLC swarm.

## RUN_BASE

All artifacts for this flow belong under:

```
RUN_BASE = swarm/runs/<run-id>/deploy/
```

where `<run-id>` matches the identifier from Flows 1-4.

Ensure this directory exists before delegating to agents.

## Your Goal

Move an approved artifact from "ready to merge" to "deployed"—execute deployment, verify health, create audit trail.

**Flow 5 is always callable.** Its behavior depends on Gate's decision:
- If Gate said MERGE: merge, verify, report.
- If Gate said BOUNCE/ESCALATE: don't merge, write receipts explaining why.

**Before you begin**: Use the TodoWrite tool to create a TODO list of the deployment steps.

This flow uses **git and GitHub** (via `gh` CLI). No external deployment platform required.

**For production extensions** (k8s, canary, metrics): See `swarm/infrastructure/flow-5-extensions.md`

## Agents to Use

| Agent | Responsibility |
|-------|----------------|
| repo-operator | Merge PR, create git tag/release (only if Gate approved MERGE) |
| deploy-monitor | Watch CI and deployment events, write verification_report.md |
| smoke-verifier | Health checks, artifact verification, append to verification_report.md |
| deploy-decider | Synthesize verification into deployment_decision.md |
| gh-reporter | Post deployment summary to PR/issue |

## Orchestration Outline

### Step 0: Read Gate Decision

Before anything else, read `RUN_BASE/gate/merge_decision.md`:
- Parse the `decision:` field (MERGE, BOUNCE, or ESCALATE)
- This determines the entire flow path

### Path A: Gate Decision = MERGE

1. **Merge & Tag** (repo-operator)
   - Execute `gh pr merge`, create git tag + GitHub release
   - Write `RUN_BASE/deploy/deployment_log.md` with merge details

2. **Monitor CI** (deploy-monitor)
   - Watch GitHub Actions status on main branch
   - Write `RUN_BASE/deploy/verification_report.md` with CI status

3. **Smoke Tests** (smoke-verifier)
   - If URL available, curl health endpoints; else verify artifacts
   - Append results to `RUN_BASE/deploy/verification_report.md`

4. **Decide** (deploy-decider)
   - Synthesize CI + smoke results
   - Write `RUN_BASE/deploy/deployment_decision.md` with verdict:
     - STABLE: All verification passes
     - INVESTIGATE: Warnings or anomalies
     - ROLLBACK: Critical issues

5. **Report** (gh-reporter)
   - Post deployment summary to PR/issue

### Path B: Gate Decision = BOUNCE or ESCALATE

1. **Skip Merge** (no repo-operator merge)
   - Write `RUN_BASE/deploy/deployment_log.md` noting: "No merge performed; Gate decision = <verdict>"

2. **Minimal Monitoring** (deploy-monitor)
   - Write `RUN_BASE/deploy/verification_report.md` noting: "No deployment to verify; Gate decision = <verdict>"
   - Status: NOT_DEPLOYED

3. **Decision** (deploy-decider)
   - Write `RUN_BASE/deploy/deployment_decision.md` with:
     - Verdict: NOT_DEPLOYED
     - Explanation of why deployment did not occur
     - Reference to Gate's concerns

4. **Report** (gh-reporter)
   - Post summary explaining why deployment was not performed

## Output Artifacts

| Artifact | Description |
|----------|-------------|
| `deployment_log.md` | Record of merge, tag, release actions (or why skipped) |
| `verification_report.md` | CI status + smoke check results |
| `deployment_decision.md` | Final verdict: STABLE / INVESTIGATE / ROLLBACK / NOT_DEPLOYED |
| `gh_report_status.md` | Log of GitHub posting (optional) |

## deploy-decider Verdicts

| Verdict | Meaning |
|---------|---------|
| STABLE | All verification passes; deployment healthy |
| INVESTIGATE | Warnings or anomalies; needs attention but not critical |
| ROLLBACK | Critical issues; should revert |
| NOT_DEPLOYED | Gate did not approve merge; no deployment attempted |

## Completion

Flow 5 is complete when:
- `deployment_log.md` exists (even if minimal for BOUNCE/ESCALATE)
- `verification_report.md` exists
- `deployment_decision.md` exists with valid verdict

Human gate at end: "Did deployment succeed?" (or "Why didn't we deploy?")
