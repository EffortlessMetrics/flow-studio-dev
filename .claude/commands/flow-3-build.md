---
description: Run Flow 3 (Design -> Code): implement via adversarial microloops, self-verify, produce receipts.
# argument-hint: [subtask-id]
---

# Flow 3: Design -> Code

You are orchestrating Flow 3 of the SDLC swarm.

## RUN_BASE

All artifacts for this flow belong under:

```
RUN_BASE = swarm/runs/<run-id>/build/
```

where `<run-id>` matches the identifier from Flows 1-2.

Code/tests remain in `src/`, `tests/`, `features/`, `fuzz/` as usual.

Ensure this directory exists before delegating to agents.

## Your goal

- Implement via adversarial microloops (test <-> critic, code <-> critic)
- Strengthen tests (unit/integration/mutation)
- Update docs
- Produce `build_receipt.json` and `self_review.md`

**Before you begin**: Use the TodoWrite tool to create a TODO list of major steps. Use behavioral descriptions for microloops--one TODO per loop, not per agent call:

- `Tighten tests: loop between author and critic while `Status == UNVERIFIED` and `can_further_iteration_help: yes`; exit when `Status == VERIFIED` or `can_further_iteration_help: no`
- `Tighten code: loop between implementer and critic while `Status == UNVERIFIED` and `can_further_iteration_help: yes`; exit when `Status == VERIFIED` or `can_further_iteration_help: no`
- `Harden via mutation: run mutation tests, fix weak spots, re-verify as needed`

Track progress at the loop level, not the individual agent call level.

If you encounter ambiguity, **document it and continue**. Write assumptions in artifacts.

## Subagents to use

**Git operations (cross-cutting)**:
- repo-operator -- branch at start, commit at end

**Context loading**:
- context-loader -- load relevant files for subtask

**Test microloop**:
- test-author -- write/update tests
- test-critic -- harsh review of tests (never fixes)

**Code microloop**:
- code-implementer -- implement code to pass tests
- code-critic -- harsh review of code (never fixes)

**Hardening**:
- mutator -- run mutation tests
- fixer -- apply targeted fixes from critiques

**Polish and wrap-up**:
- doc-writer -- update documentation
- self-reviewer -- final review, generate build receipt

**Cross-cutting agents**:
- clarifier -- detect ambiguities in specs/design, document assumptions
- gh-reporter -- post summary to GitHub

## Orchestration outline

1. **Git prep**: `repo-operator` -> ensure clean tree, create/switch to feature branch

2. **Load context**: `context-loader` -> `subtask_context_manifest.json`

3. **Clarify**: `clarifier` -> `clarification_questions.md` (non-blocking)
   - Scan ADR, contracts, and loaded context for ambiguities
   - Document assumptions being made to proceed
   - Continue regardless of questions found

4. **Tighten tests**: Loop between `test-author` and `test-critic` while the
   critic indicates further iteration can help:
   - Call `test-author` to write/update tests
   - Call `test-critic` to review them (with `can_further_iteration_help` field)
   - If VERIFIED, proceed to code
   - If UNVERIFIED with `can_further_iteration_help: yes`, route back to
     `test-author` with specific feedback
   - If UNVERIFIED with `can_further_iteration_help: no`, proceed (remaining
     issues acknowledged as not addressable within scope)

5. **Tighten code**: Loop between `code-implementer` and `code-critic` while
   the critic indicates further iteration can help:
   - Call `code-implementer` to implement behavior
   - Call `code-critic` to review code (with `can_further_iteration_help` field)
   - If VERIFIED, proceed to hardening
   - If UNVERIFIED with `can_further_iteration_help: yes`, route back to
     `code-implementer` with specific feedback
   - If UNVERIFIED with `can_further_iteration_help: no`, proceed (remaining
     issues acknowledged as not addressable within scope)

6. **Harden**: `mutator` -> `fixer`:
   - Run mutation tests with `mutator` -> `mutation_report.md`
   - Apply targeted fixes with `fixer` -> `fix_summary.md`
   - Re-verify with test-runner as needed

7. **Polish**: `doc-writer` -> `doc_updates.md`

8. **Self-review**: `self-reviewer` -> `self_review.md` + `build_receipt.json`

9. **Commit**: `repo-operator` -> stage changes, compose commit message, commit

10. **Report**: `gh-reporter` -> post summary to GitHub PR/issue (if applicable)

## Status States

Agents report one of:
- **VERIFIED**: Work is adequate for its purpose
- **UNVERIFIED**: Work has issues; concrete concerns documented
- **BLOCKED**: Could not meaningfully complete; dependencies missing

Use critic status to decide whether to loop or proceed.

## Microloop Termination

Move forward when:
- Critic says VERIFIED, or
- Critic says UNVERIFIED but marks `can_further_iteration_help: no`
  (explicitly judges no viable fix path remains)

No hard iteration caps--context limits and runtime naturally stop loops. The
critic's explicit `can_further_iteration_help` judgment drives termination, not
subjective heuristics about feedback repetitiveness.

## Output Artifacts

After this flow completes, `RUN_BASE/build/` should contain:
- `subtask_context_manifest.json`
- `clarification_questions.md`
- `test_changes_summary.md`
- `test_critique.md`
- `impl_changes_summary.md`
- `code_critique.md`
- `mutation_report.md`
- `fix_summary.md`
- `doc_updates.md`
- `self_review.md`
- `build_receipt.json`

Code/test changes in `src/`, `tests/`, `features/`.
