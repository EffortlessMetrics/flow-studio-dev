# Health-check scenario — expected artifacts per flow

This document lists the concrete files each flow is expected to produce for the "health-check endpoint" example. Use this as the checklist when you run the flows; `swarm/tools/run_flow_dry.py` will list which of these exist.

Flow 1 — Signal (`/flow-signal`)
- `issue_normalized.md` — normalized incoming signal
- `internal_research.md` — related issues/PRs/incidents (explore)
- `external_research.md` — vendor docs / standards found (explore)
- `context_brief.md` — summarized internal context
- `doc_research.md` — summarized external research
- `related_links.json` — links/refs map
- `problem_statement.md` — canonical problem statement
- `clarification_questions.md` — first-pass questions for humans
- `gap_research.md` — docs found for doc-answerable gaps
- `clarification_questions_final.md` — final human-only questions

Flow 2 — Plan (`/flow-plan`)
- `impact_map.json` — impact mapping for change
- `iac_surface_map.md` — infra/CI/config surface
- `design_options.md` — candidate designs/options
- `adr_current.md` — ADR for chosen option
- `api_contracts.yaml` and/or `interface_spec.md` — API contract
- `data_spec.md` and optional `migrations/*.sql` — data model
- `observability_spec.md` — telemetry/traces/metrics spec
- `test_plan.md` — test strategy derived from features/impact
- `policy_plan.md` — policy checks to run in Gate
- `implementation_plan.md` — subtasks, branches, rollout
- `design_feasibility.md` — feasibility check output

Flow 3 — Build (`/flow-build`)
- `subtask_context_manifest.json` — small context bundle for implementer
- `tests/` (unit/integration) and `tests/*` files
- `test_changes_summary.md` — what tests were added/changed
- `fuzz/` harnesses and `fuzz_changes_summary.md` (optional)
- `test_critique.md` — critic report on tests
- `impl_changes_summary.md` — summary of code changes
- `code_critique.md` — code critique output
- `mutation_report.md` — mutation testing results (optional)
- `refactor_notes.md` — refactorer notes
- `doc_updates_summary.md` — docs updated
- `self_review.md` and `build_receipt.json` — self-review + machine-readable receipt

Flow 4 — Gate (`/flow-gate`)
- `build_receipt.json` — consumed from Build
- `contract_status.md` — API/contract verification
- `security_status.md` — security scan / SAST summary
- `perf_status.md` — perf / load quick checks
- `gate_fix_summary.md` — trivial fixes applied (lint/format/docs)
- `gate_risk_report.md` — aggregated risk signals
- `policy_verdict.md` — policy gate outcome (READY/BLOCKED/ESCALATE)
- `merge_recommendation.md` — final recommendation (merge/bounce)

Flow 5 — Operate (`/flow-operate`) — optional post-deploy
- `observability_spec.md` (input)
- `deployment_verification.md` and/or `deployment_status.json`
- `regression_report.md` — post-deploy regressions or errors
- `flow_history.json` and `flow_timeline.md` — run history / timeline
- `playbook_update.md` — suggested playbook updates based on incidents

Notes
- `run_flow_dry.py` is intentionally informational: it lists expected artifacts and whether they exist. Missing artifacts are normal until you run flows for a scenario or create a demo snapshot.
- When you want a committed demo snapshot, produce the real artifacts under `swarm/examples/health-check/` and commit that directory.
