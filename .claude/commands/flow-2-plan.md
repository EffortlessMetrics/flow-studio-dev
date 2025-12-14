---
description: Run Flow 2 (Spec to Design): produce ADR, contracts, observability spec, test/work plans, design validation.
---

# Flow 2: Spec to Design

You are orchestrating Flow 2 of the SDLC swarm.

## RUN_BASE

All artifacts for this flow belong under:

```
RUN_BASE = swarm/runs/<run-id>/plan/
```

where `<run-id>` matches the identifier from Flow 1.

Ensure this directory exists before delegating to agents.

## Your goal

- Turn requirements into architecture decisions
- Define API contracts and data models
- Create observability, test, and work plans
- Validate design feasibility

**Before you begin**: Use the TodoWrite tool to create a TODO list of the subagent calls and major steps. This helps track progress.

If you encounter ambiguity or missing information, **document it and continue**. Write assumptions clearly in artifacts.

## Subagents to use

Flow 2 uses 8 domain agents plus cross-cutting agents:

### Domain agents (in order)
- impact-analyzer
- design-optioneer
- adr-author
- interface-designer
- observability-designer
- test-strategist
- work-planner
- design-critic

### Cross-cutting agents
- clarifier (if ambiguities found)
- risk-analyst (if risk patterns identified)
- policy-analyst (policy compliance check)
- gh-reporter (post summary to GitHub)

## Upstream Inputs

Read from `RUN_BASE/signal/`:
- `problem_statement.md`
- `requirements.md`
- `requirements_critique.md`
- `features/*.feature`
- `example_matrix.md`
- `stakeholders.md`
- `early_risks.md`
- `scope_estimate.md`

## Orchestration outline

1. **Map impact**
   - `impact-analyzer` -> `impact_map.json`

2. **Propose design options**
   - `design-optioneer` -> `design_options.md`

3. **Write ADR**
   - `adr-author` -> `adr.md`

4. **Define contracts and schema** (can run in parallel with steps 5-7)
   - `interface-designer` -> `api_contracts.yaml`, `schema.md`, `migrations/*.sql`

5. **Plan observability** (parallel)
   - `observability-designer` -> `observability_spec.md`

6. **Plan testing** (parallel)
   - `test-strategist` -> `test_plan.md`

7. **Plan work** (parallel)
   - `work-planner` -> `work_plan.md`

8. **Validate design**
   - `design-critic` -> `design_validation.md`

9. **Check policy compliance**
   - `policy-analyst` -> `policy_analysis.md`

10. **Report to GitHub**
    - `gh-reporter` -> post ADR + validation summary to PR/issue

## Design Loop (Optional)

After `design-critic` completes:

- If `status == UNVERIFIED` and issues are **local and clear**:
  - Consider one re-pass: `design-optioneer` -> `adr-author` -> affected parallel agents -> `design-critic`
- If `status == VERIFIED` or concerns are **structural**:
  - Proceed to completion; structural issues mean re-run Flow 2 later with more info

**Important**: Agents do not know they are in a loop. They read inputs, write outputs, and set a status. The orchestrator interprets status to decide routing.

## Downstream Contract

Flow 2 is complete when these exist (even if imperfect):

- `impact_map.json` - services, modules, data, external systems affected
- `design_options.md` - 2-3 architecture options with trade-offs
- `adr.md` - chosen option with rationale and consequences
- `api_contracts.yaml` - endpoints, schemas, error shapes
- `schema.md` - data models, relationships, invariants
- `migrations/*.sql` - draft migrations (optional, if DB changes needed)
- `observability_spec.md` - metrics, logs, traces, SLOs, alerts
- `test_plan.md` - BDD to test types mapping, priorities
- `work_plan.md` - subtasks, ordering, dependencies
- `design_validation.md` - feasibility assessment, known issues

## Status States

Agents set status in their output artifacts:

- **VERIFIED**: Artifact complete for its purpose
- **UNVERIFIED**: Artifact created but has issues
- **BLOCKED**: Could not meaningfully complete

Use `design-critic` status to decide whether to loop or proceed.

## Notes

- Steps 4-7 can run in parallel after `adr-author` completes
- `design-critic` reviews ALL artifacts before policy check
- Human gate at end: "Is this the right design?"
- Agents never block; they document concerns and continue
