---
description: Run Flow 1 (Signal -> Spec): shape the problem, identify stakeholders, flag early risks, estimate scope.
---

# Flow 1: Signal -> Spec

You are orchestrating Flow 1 of the SDLC swarm.

## RUN_BASE

All artifacts for this flow belong under:

```
RUN_BASE = swarm/runs/<run-id>/
```

where `<run-id>` is a ticket ID, branch name, or unique identifier for this change (e.g., `ticket-123`, `feat-auth`).

Artifacts are written to `RUN_BASE/signal/`. Ensure this directory exists before delegating to agents.

## Your goal

- Turn messy input into testable requirements
- Identify affected stakeholders (teams, systems, users)
- Flag early security/compliance/performance risks
- Estimate scope (S/M/L/XL t-shirt size)
- Produce BDD scenarios
- Post summary to issue

**Before you begin**: Use the TodoWrite tool to create a TODO list of major steps. Use behavioral descriptions for the requirements loop--one TODO, not per agent:

- `Refine requirements: loop between author and critic while `Status == UNVERIFIED` and `can_further_iteration_help: yes`; exit when `Status == VERIFIED` or `can_further_iteration_help: no`

Track progress at the step level, not the individual agent call level.

If you encounter ambiguity or missing information, **document it and continue**. Do not stop. Write questions to `clarification_questions.md` and proceed with your best interpretation.

### Assumptions + Questions Contract

All Flow 1 agents must emit:
- **Assumptions Made to Proceed**: What was assumed, why, and impact if wrong
- **Questions / Clarifications Needed**: Questions that would change the spec, with defaults

These sections enable humans to review what was assumed at the flow boundary, and to re-run with better inputs if needed. Flow 1 is designed to be re-run—each run refines the output based on newly resolved ambiguity.

**BLOCKED is exceptional**: Set BLOCKED only when input artifacts don't exist. Ambiguity uses documented assumptions + UNVERIFIED status, not BLOCKED.

## Agents to use

### Domain agents (Flow 1 specific)
- signal-normalizer
- problem-framer
- requirements-author
- requirements-critic
- bdd-author
- scope-assessor

### Cross-cutting agents
- clarifier
- risk-analyst
- gh-reporter

## Orchestration outline

1. **Normalize signal**: `signal-normalizer` -> `issue_normalized.md`, `context_brief.md`

2. **Frame the problem**: `problem-framer` -> `problem_statement.md`

3. **Clarify**: `clarifier` -> `clarification_questions.md` (non-blocking)

4. **Refine requirements**: Loop between `requirements-author` and `requirements-critic`
   while the critic indicates further iteration can help:
   - `requirements-author` -> `requirements.md`
   - `requirements-critic` -> `requirements_critique.md`
     (with `can_further_iteration_help` field)
   - If VERIFIED, proceed to BDD scenarios
   - If UNVERIFIED with `can_further_iteration_help: yes`, route back to
     `requirements-author` with specific feedback
   - If UNVERIFIED with `can_further_iteration_help: no`, proceed (remaining
     issues acknowledged as not addressable within scope)

5. **BDD scenarios**: `bdd-author` -> `features/*.feature`, `example_matrix.md`

6. **Assess scope**: `scope-assessor` -> `stakeholders.md`, `early_risks.md`, `scope_estimate.md`

7. **Analyze risks**: `risk-analyst` -> enriches `early_risks.md` with risk patterns

8. **Report to GitHub**: `gh-reporter` -> summary comment on issue/PR

## Artifact outputs

All written to `RUN_BASE/signal/`:

- `issue_normalized.md` - structured summary of the raw signal
- `context_brief.md` - related history and context
- `problem_statement.md` - goals, non-goals, constraints
- `clarification_questions.md` - open questions and assumptions
- `requirements.md` - functional + non-functional requirements with IDs
- `requirements_critique.md` - verdict on requirements quality
- `features/*.feature` - BDD scenarios (Gherkin)
- `example_matrix.md` - example mapping for BDD
- `stakeholders.md` - teams, systems, users affected
- `early_risks.md` - first-pass risk identification
- `scope_estimate.md` - S/M/L/XL estimate with rationale

## Status states

Agents set status in their output artifacts:

- **VERIFIED** - Work is adequate for its purpose; assumptions documented
- **UNVERIFIED** - Work has issues; contains concrete concerns and assumptions
- **BLOCKED** - Required input artifacts missing (exceptional; NOT for ambiguity)

**Key rule**: If agents can read inputs and form an opinion, status is VERIFIED or UNVERIFIED with assumptions, never BLOCKED.

Use `requirements_critique.md` status to decide whether to loop or proceed.

## Completion

Flow 1 is complete when all artifacts exist (even if imperfect). Human gate at
end: "Is this the right problem to solve?"
