# Health-Check Example

> Complete end-to-end demonstration of all 5 flows in the industrial agentic SDLC swarm.

## Purpose

This directory contains a **curated snapshot** of a full run through the swarm's 5 flows:

1. **Signal → Specs** (`signal/`)
2. **Specs → Plan** (`plan/`)
3. **Plan → Draft** (`build/`)
4. **Draft → Verify** (`gate/`)
5. **Operate → Learn** (`operate/`)

The example implements a simple health-check endpoint and demonstrates:

- Problem framing and requirements extraction
- ADR authoring and contract design
- Adversarial microloops (test ⇄ critic, code ⇄ critic)
- Pre-merge gate verification
- Post-deploy regression detection

---

## Directory Structure

```
health-check/
├── code-snapshot/          # Copy of code/tests/features at snapshot time
│   ├── 0001_add_health_endpoint.sql
│   ├── example_fuzz.rs
│   └── health.feature
│
├── signal/                 # Flow 1 artifacts
│   ├── problem_statement.md
│   ├── requirements_functional.md
│   ├── requirements_constraints.md
│   ├── early_risk_assessment.md
│   └── clarification_questions.md
│
├── plan/                   # Flow 2 artifacts
│   ├── adr_current.md
│   ├── api_contracts.yaml
│   ├── data_spec.md
│   ├── design_feasibility.md
│   ├── design_options.md
│   ├── iac_surface_map.md
│   ├── impact_map.json
│   ├── implementation_plan.md
│   ├── interface_spec.md
│   ├── observability_spec.md
│   ├── policy_plan.md
│   └── test_plan.md
│
├── build/                  # Flow 3 artifacts
│   ├── build_receipt.json
│   ├── code_critique.md
│   ├── doc_updates_summary.md
│   ├── fuzz_changes_summary.md
│   ├── impl_changes_summary.md
│   ├── mutation_report.md
│   ├── refactor_notes.md
│   ├── self_review.md
│   ├── subtask_context_manifest.json
│   ├── test_changes_summary.md
│   ├── test_critique.md
│   └── test_summary.md
│
├── gate/                   # Flow 4 artifacts
│   ├── contract_status.md
│   ├── gate_fix_summary.md
│   ├── gate_risk_report.md
│   ├── merge_recommendation.md
│   ├── perf_status.md
│   ├── policy_verdict.md
│   ├── receipt_audit.md
│   └── security_status.md
│
├── operate/                # Flow 5 artifacts
│   ├── deployment_verification.md
│   ├── flow_history.json
│   ├── flow_timeline.md
│   ├── playbook_update.md
│   └── regression_report.md
│
├── reports/                # Generated diagnostics
│   ├── flow-build-report.txt
│   ├── flow-gate-report.txt
│   ├── flow-operate-report.txt
│   ├── flow-plan-report.txt
│   └── flow-signal-report.txt
│
├── EXPECTED_ARTIFACTS.md   # Lists all artifacts each flow should produce
└── README.md               # This file
```

---

## About `code-snapshot/`

This directory contains **copies** of the relevant code, tests, and features at the time this snapshot was captured:

- **0001_add_health_endpoint.sql** — SQL migration (copy from `migrations/`)
- **example_fuzz.rs** — Fuzz harness (copy from `fuzz/`)
- **health.feature** — BDD scenario (copy from `features/`)

### Important

The **authoritative** copies of code and tests live in the repo root:

- Code: `src/handlers/health.rs`
- Tests: `tests/health_check_tests.rs`
- Features: `features/health.feature`
- Migrations: `migrations/0001_add_health_endpoint.sql`
- Fuzz: `fuzz/example_fuzz.rs`

`code-snapshot/` exists only to make this example self-contained for teaching purposes. Do not edit these copies directly.

---

## How to Read This Example

### For New Users

1. **Start with `signal/problem_statement.md`** — See how the swarm frames a raw requirement
2. **Read `plan/adr_current.md`** — See how design decisions are documented
3. **Browse `build/build_receipt.json`** — See the structured output of Flow 3
4. **Check `gate/merge_recommendation.md`** — See how the gate evaluates readiness
5. **Review `operate/regression_report.md`** — See post-deploy verification

### For Agent Authors

- **`signal/` artifacts** show what Flow 1 agents produce (problem-framer, requirements-drafter, bdd-scenarist, early-risk-screener)
- **`plan/` artifacts** show what Flow 2 agents produce (architecture-optioneer, adr-author, interface-designer, test-strategist, work-planner)
- **`build/` artifacts** show what Flow 3 agents produce (test-author, code-implementer, test-critic, code-critic, mutator, self-reviewer-receipt)
- **`gate/` artifacts** show what Flow 4 agents produce (receipt-auditor, contract-guardian, security-gate-auditor, perf-gate-auditor, merge-recommender)
- **`operate/` artifacts** show what Flow 5 agents produce (deployment-verifier, regression-hunter, flow-historian, pattern-miner)

### For Orchestrator Implementers

This snapshot defines the **contract** your orchestrator must implement:

- **RUN_BASE layout**: Artifacts under `<flow>/` subdirectories
- **Artifact shapes**: See JSON schemas in build_receipt.json, flow_history.json, impact_map.json
- **Microloop evidence**: Check test_critique.md → test_changes_summary.md cycles
- **Git ops**: Look for git_status.txt, commit messages in build/

If your orchestrator can produce these artifacts in this structure, it's compatible with the swarm spec.

---

## Expected Artifacts

See `EXPECTED_ARTIFACTS.md` for a complete checklist of what each flow should produce.

---

## Regenerating This Example

If you want to regenerate this snapshot from scratch:

1. Clear the example:

   ```bash
   rm -rf swarm/examples/health-check/{signal,plan,build,gate,operate,reports}
   ```

2. Run all 5 flows with `run-id=health-check-v2`:

   ```bash
   /flow-1-signal health-check-v2 "Add a health-check endpoint"
   /flow-2-plan health-check-v2
   /flow-3-build health-check-v2
   /flow-4-gate health-check-v2
   /flow-5-deploy health-check-v2
   ```

3. Copy artifacts from `swarm/runs/health-check-v2/` to `swarm/examples/health-check/`

4. Copy code/tests to `code-snapshot/`

5. Run `uv run swarm/tools/run_flow_dry.py` to generate reports

---

## Philosophy

This example embodies the swarm's core principles:

- **Receipts over vibes**: Every flow produces auditable artifacts
- **Compute for attention**: Agents iterate; humans review receipts
- **Harsh critics**: test-critic and code-critic reject weak work
- **Heavy context**: Agents load 20-50k tokens to avoid downstream re-search
- **Bounce-backs**: Gate may return work to Build or Plan if not ready

For more on the philosophy, see `swarm/positioning.md`.
