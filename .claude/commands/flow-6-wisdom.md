---
description: Run Flow 6 (Prod -> Wisdom): analyze artifacts, detect regressions, extract learnings, close feedback loops.
---

# Flow 6: Prod -> Wisdom

You are orchestrating Flow 6 of the SDLC swarm.

## RUN_BASE

All artifacts for this flow belong under:

```
RUN_BASE = swarm/runs/<run-id>/wisdom/
```

where `<run-id>` matches the identifier from Flows 1-5.

Ensure this directory exists before delegating to agents.

## Your goal

- Verify all flow artifacts exist
- Analyze tests, coverage, and regressions
- Correlate with GitHub issues and git blame
- Compile flow timeline
- Extract learnings from receipts and critiques
- Suggest feedback actions (issues, doc updates)
- Add risk perspective comparing predicted vs actual
- Post learnings and action items to GitHub

**Before you begin**: Use the TodoWrite tool to create a TODO list of the analysis steps and feedback loop items.

This flow uses **flow artifacts and git/GitHub**. No external observability platform required.

**For production extensions** (metrics, logs, traces, incidents, SLOs): See `swarm/infrastructure/flow-6-extensions.md`

## Subagents to use

Domain agents (Flow 6):
- artifact-auditor
- regression-analyst
- flow-historian
- learning-synthesizer
- feedback-applier

Cross-cutting agents:
- risk-analyst
- gh-reporter

## Orchestration outline

This is a **linear pipeline** with no internal loops.

1. **Verify artifacts**
   - `artifact-auditor` -> walk all `RUN_BASE/<flow>/` directories
   - Check expected artifacts against flow specs
   - Produce `artifact_audit.md` with matrix of flows vs artifacts

2. **Analyze regressions**
   - `regression-analyst` -> parse test outputs, coverage reports
   - Correlate with GitHub issues via `gh issue list`
   - Run `git blame` on failing tests to link commits
   - Produce `regression_report.md` with findings by type and severity

3. **Build history**
   - `flow-historian` -> read all artifacts and git history
   - Compile `flow_history.json` timeline linking signal -> spec -> design -> build -> gate -> deploy
   - Include timestamps, commits, decision points

4. **Synthesize learnings**
   - `learning-synthesizer` -> read artifact audit, regression report, flow history
   - Extract patterns: what worked, what didn't, assumptions that broke
   - Produce `learnings.md` narrative with feedback to Flows 1, 2, 3

5. **Apply feedback**
   - `feedback-applier` -> turn learnings into concrete actions
   - Produce `feedback_actions.md` with actionable items
   - Optionally create GitHub issues for test gaps via `gh issue create`

6. **Risk assessment**
   - `risk-analyst` (cross-cutting) -> add risk perspective to learnings
   - Compare predicted risks (`early_risks.md`) vs actual outcomes
   - Produce `risk_assessment.md` or append to existing artifacts

7. **Report**
   - `gh-reporter` -> post mini-postmortem summary to PR/issue
   - Include regressions found, learnings extracted, feedback actions

## Closed Feedback Loops

Flow 6 closes the SDLC loop by feeding learnings back (recommendations, not direct calls):

### -> Flow 1 (Signal)
- `learning-synthesizer` extracts problem patterns
- `feedback-applier` suggests updates to requirement templates
- Builds institutional memory of "problems that recur"

### -> Flow 2 (Plan)
- `feedback-applier` suggests architecture doc updates
- Documents patterns that worked/failed
- Improves design templates and ADR prompts

### -> Flow 3 (Build)
- `feedback-applier` creates GitHub issues for test gaps
- Links regression failures to coverage gaps
- Suggests test pattern improvements

These are **recommendations in artifacts**, not direct flow invocations. Humans decide which to act on.

## Expected Outputs

When complete, `RUN_BASE/wisdom/` should contain:

- `artifact_audit.md` - structural sanity check of all flows
- `regression_report.md` - what got worse and where
- `flow_history.json` - timeline linking all flow events
- `learnings.md` - narrative lessons extracted
- `feedback_actions.md` - concrete follow-ups (issues, doc updates)
- `risk_assessment.md` - risk perspective (optional, if risk-analyst invoked)

## Completion States

Flow 6 agents report:

- **VERIFIED**: Full analysis complete with all artifacts processed
- **UNVERIFIED**: Analysis complete but some data unavailable (GitHub, git, etc.)
- **BLOCKED**: Critical artifacts missing, cannot complete analysis

Any of these are valid outcomes. Document concerns and continue.
