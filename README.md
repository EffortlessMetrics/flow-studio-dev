# Flow Studio

> **For:** Platform engineers, DevEx leads, and teams exploring governed agentic SDLC.
>
> **Status:** Demo harness is green in CI; releases are tagged.
>
> **Issues:** Use the issue templates in this repo's **Issues** tab.

Flow Studio is a **swarm runner + UI** for visualizing SDLC flows, runs, and governance state.

What's in this repo:

- **FastAPI backend** (Flow Studio APIs + local static UI serving)
- **Flow Studio UI** (TypeScript source + **compiled JS committed** for "clone → run" reliability)
- **Demo harness** (flows, runs, selftest, validation, golden examples)
- **`.claude/` swarm definitions** (the specimen used by the harness)
- **Stepwise execution backends** (stub/CLI/SDK modes)

Related repos:

- [`EffortlessMetrics/demo-swarm`](https://github.com/EffortlessMetrics/demo-swarm) — Portable `.claude` pack for running flows directly in Claude Code.

> **Evaluating this for your team?** Start with
> [docs/EVALUATION_CHECKLIST.md](docs/EVALUATION_CHECKLIST.md).

This repo implements an agentic SDLC covering the full lifecycle of a
change: shaping tickets, planning, implementing with test-first loops,
gating PRs with contract checks, verifying deploys, and extracting learnings.

Agents do the grinding; you review the receipts.

**What's in here**:

- **Six flows** covering signal → specs → plan → build → gate → deploy →
  wisdom
- **48 agents** (3 built-in + 45 domain; think interns, not wizards)
- **Receipts on disk** so you can trace every decision

**The core trade**: Spend tokens freely to save senior engineer attention.
Let agents iterate until tests pass and critics approve, then review the
proof instead of babysitting the process.

**What this is good for**:

- Platform/DevEx teams building SDLC automation
- Teams that want audit trails, not vibes
- Environments where you can trade compute for human attention

**What this isn't**:

- Not a magic autopilot (agents are narrow interns, not autonomous engineers)
- Not for small teams or simple projects (this is overkill if you just need
  code completion)
- Not a product (it's a reference implementation you fork and adapt)
- Not a SaaS or hosted service (runs entirely local or in your CI)
- Not a compliance solution (pattern library for governed AI, not turnkey compliance)

**License & Contributions**: Apache-2.0. PRs welcome—must keep tests and governance green.
See [SUPPORT.md](SUPPORT.md) for engagement expectations.

**Three core ideas**:

1. **Flows as first-class spec** — Not chat; structured SDLC with RUN_BASE artifact paths, mermaid diagrams, agent rosters
2. **Selftest as governance gate** — Layered validation (KERNEL/GOVERNANCE/OPTIONAL) with JSON reports
3. **Agent surfaces are structured** — All inputs/outputs on disk under `RUN_BASE/<flow>/`, traced decisions, no magic

---

## Quick Start

### Prereqs

- **Python + uv**
- **GNU Make**
- **Node.js is optional** (only needed if you edit the UI or want to run TS checks locally)

Windows note: if you don't have `make`, use WSL2 or follow the Windows section in
[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md).

### Run the demo

```bash
uv sync --extra dev
make demo-run
make flow-studio
# Open: http://localhost:5000/?run=demo-health-check&mode=operator
```

If port 5000 is busy:

```bash
uv run uvicorn swarm.tools.flow_studio_fastapi:app --host 127.0.0.1 --port 5001
```

What you should see:

* **Left sidebar**: flows
* **Center graph**: steps + agents
* **Top bar**: SDLC status
* **Right panel**: details, artifacts, validation

Read [docs/FLOW_STUDIO.md](./docs/FLOW_STUDIO.md) for a guided tour, or see
[DEMO_RUN.md](./DEMO_RUN.md) for a narrative walkthrough.

---

## Try Stepwise Execution (60 Seconds)

Want to see per-step observability? Run a stepwise demo:

```bash
make demo-run-stepwise      # Run both Gemini and Claude stepwise backends
make flow-studio            # View the run
# Open http://localhost:5000/?run=stepwise-claude
```

**What you'll see**: Each step executes separately with its own transcript and receipt. Click any step in Flow Studio to see:
- When it started/ended
- Which agent executed it
- Token usage (in real mode)
- The actual LLM conversation

**Why stepwise?** Traditional batch execution is a black box. Stepwise gives you per-step observability, context handoff between steps, and error isolation. See [STEPWISE_BACKENDS.md](docs/STEPWISE_BACKENDS.md) for details.

---

## Stepwise SDLC Quick Reference

Three ways to run the full SDLC stepwise:

```bash
# 1. Stub mode (no API keys, instant, for demos)
make stepwise-sdlc-stub

# 2. Claude CLI mode (uses Claude Code or GLM Coding Plan)
make stepwise-sdlc-claude-cli

# 3. Claude SDK mode (with ANTHROPIC_API_KEY)
ANTHROPIC_API_KEY=sk-... make stepwise-sdlc-claude-sdk
```

| Mode | Requires | Token Cost | Use Case |
|------|----------|------------|----------|
| `stub` | Nothing | Zero | CI, demos, structure testing |
| `cli` | Claude Code or GLM Coding Plan | Real | Development, interactive |
| `sdk` | `ANTHROPIC_API_KEY` | Real | Automation, batch runs |

**Golden examples** with all 6 flows: `swarm/examples/stepwise-sdlc-claude/`

For architecture details, see:
- [STEPWISE_BACKENDS.md](docs/STEPWISE_BACKENDS.md) -- Backend/engine configuration
- [stepwise-fastpath.md](swarm/runbooks/stepwise-fastpath.md) -- Quick 5-minute walkthrough
- [LONG_RUNNING_HARNESSES.md](docs/LONG_RUNNING_HARNESSES.md) -- How this maps to Anthropic's patterns

---

## Agent SDK Quick Start

The Agent SDK is "headless Claude Code" — it reuses your existing Claude subscription (Max/Team/Enterprise) without requiring an API key:

```bash
make agent-sdk-ts-demo   # Run TypeScript example
make agent-sdk-py-demo   # Run Python example
make agent-sdk-help      # Full documentation
```

| Surface | Auth | Use Case |
|---------|------|----------|
| **Agent SDK** (TS/Python) | Claude login | Local dev, building agents |
| **CLI** (`claude --output-format`) | Claude login | Shell integration, debugging |
| **HTTP API** (`api.anthropic.com`) | API key | Server-side, CI, multi-tenant |

For detailed integration patterns, see:
- [docs/AGENT_SDK_INTEGRATION.md](docs/AGENT_SDK_INTEGRATION.md) -- Integration guide
- TypeScript example: `examples/agent-sdk-ts/`
- Python example: `examples/agent-sdk-py/`

---

## Sanity Check in 10 Minutes

New clone, new machine, or demo prep? Run the [10-minute health check](./swarm/runbooks/10min-health-check.md):

```bash
uv sync --extra dev && make dev-check   # Validate environment
make selftest                           # Run full governance suite
make flow-studio                        # Start UI at http://localhost:5000
```

This walks you through validating the swarm is healthy, running selftest, and doing a keyboard-only walkthrough of Flow Studio.

---

## Run Lifecycle & Cleanup

Day-to-day run management:

```bash
make runs-list           # Show run statistics and retention eligibility
make runs-list-v         # Verbose: individual runs with age/size
make runs-prune-dry      # Preview what would be deleted
make runs-prune          # Apply retention policy
make runs-gc-help        # Full GC command reference
```

When Flow Studio logs "Failed to parse summary...":

```bash
make runs-quarantine-dry   # Preview corrupt runs
make runs-quarantine       # Move corrupt runs to _corrupt/
make flow-studio           # Restart
```

**Configuration:** `swarm/config/runs_retention.yaml`
- Default retention: 30 days, max 300 runs
- Preserved prefixes: `demo-`, `stepwise-`, `baseline-`
- Examples in `swarm/examples/` are never deleted

See [docs/RUN_LIFECYCLE.md](docs/RUN_LIFECYCLE.md) for the full run lifecycle documentation.

---

## Flow 6: Wisdom from Runs

After you've been running stepwise flows for a while, extract cross-run learnings:

```bash
make wisdom-summary RUN_ID=stepwise-claude     # Summarize a single run
make wisdom-aggregate                          # Aggregate across all runs
make wisdom-report                             # Markdown report for notes/decks
make wisdom-cycle RUN_ID=stepwise-claude       # Full cycle: summarize + aggregate + preview cleanup
```

**What wisdom captures:**
- Artifact completeness (what's present/missing across flows)
- Regression patterns (what got worse, by type and severity)
- Flow execution timeline (timestamps, durations, handoffs)
- Learnings and recommendations (patterns that worked/failed)
- Feedback actions (issues to create, docs to update)

**How it connects to runs lifecycle:**
- Raw runs in `swarm/runs/` → wisdom summaries (`wisdom_summary.json`)
- Periodic aggregation → cross-run trend analysis
- Then `make runs-prune` trims the raw event clutter

See [swarm/flows/flow-wisdom.md](swarm/flows/flow-wisdom.md) for the full Flow 6 specification,
and [swarm/runbooks/runs-retention.md](swarm/runbooks/runs-retention.md) for the retention runbook.

---

## How to Engage: Four Tracks

Pick your track based on how much time you have and what you want to learn:

| Track | Time | You Want To... | Start Here |
|-------|------|----------------|------------|
| **Observer** | 10–15 min | See it work, understand the shape | Run `make selftest && make flow-studio`, read [TOUR_20_MIN.md](docs/TOUR_20_MIN.md) |
| **Operator** | 1–2 hours | Understand flows, run golden examples, explore governance | [GETTING_STARTED.md](docs/GETTING_STARTED.md) + [SELFTEST_SYSTEM.md](docs/SELFTEST_SYSTEM.md) |
| **Presenter** | 15 min prep | Demo this to your team with timing and talking points | [DEMO_RUN_OPERATORS.md](docs/DEMO_RUN_OPERATORS.md) + [PRE_DEMO_CHECKLIST.md](docs/PRE_DEMO_CHECKLIST.md) |
| **Adopter** | Multi-day | Integrate into your repo, wire CI gates, customize flows | [ADOPTING_SWARM_VALIDATION.md](docs/ADOPTING_SWARM_VALIDATION.md) + [ADOPTION_PLAYBOOK.md](docs/ADOPTION_PLAYBOOK.md) |

**Quick decision tree:**
- Just curious? → Observer track
- Evaluating for your team? → Operator track + [EVALUATION_CHECKLIST.md](docs/EVALUATION_CHECKLIST.md)
- Giving a demo? → Presenter track
- Ready to integrate? → Adopter track

---

## Lost? Start Here

This repo is the **canonical governed Flow Studio demo harness**. See
[`docs/GOLDEN_RUNS.md`](docs/GOLDEN_RUNS.md) and
[`docs/WHY_DEMO_SWARM.md`](docs/WHY_DEMO_SWARM.md) for the why, and Flow
Studio for the how.

## Related Repos

- [`EffortlessMetrics/demo-swarm`](https://github.com/EffortlessMetrics/demo-swarm) — Portable `.claude` pack for running flows in your own repo

- **New to the swarm?** → [`docs/INDEX.md`](docs/INDEX.md) (75-min guided tour)
- **Quick overview?** → [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md) (10 min, two paths)
- **Want to adopt this?** → [`docs/ADOPTING_SWARM_VALIDATION.md`](docs/ADOPTING_SWARM_VALIDATION.md) (5-min TL;DR)
- **Understand the why?** → [`docs/WHY_DEMO_SWARM.md`](docs/WHY_DEMO_SWARM.md) (philosophy & scope)

---

## Are You Ready to Adopt This?

Before diving in, check these prerequisites:

- [ ] Have at least one repo where you control CI
- [ ] Can add a GitHub Action or equivalent
- [ ] Can tolerate a 5-10 minute CI step on PR
- [ ] Have *someone* who owns keeping KERNEL checks green
- [ ] Willing to have build failures block merges

If you checked all boxes, start with [docs/ADOPTION_PLAYBOOK.md](docs/ADOPTION_PLAYBOOK.md).

If you're not sure, try [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) first for a 20-minute tour.

---

## Status

This is an **early re-implementation** of a swarm pattern I've used before.

It's been run through the bundled examples and a small set of demo scenarios; outside that, you're in new territory. Details will move. If you hit something confusing or broken, open an issue.

---

## Learning Paths: Three Ways to Get Started

Pick your path based on what you want to do. Each path is self-contained but
links to the others.

### Lane 1: 20-Minute Tour (Curious Engineers)

**Goal**: See the swarm in action and understand its basic idea.

**What you'll do**: `make demo-run && make flow-studio` — explore interactive
UI, click through agents, see flow artifacts.

**Read**: [docs/TOUR_20_MIN.md](./docs/TOUR_20_MIN.md)

**Key takeaway**: Swarm is 6 flows × 48 agents; agents iterate on code/tests
/docs, you review receipts. Click the **Selftest** tab to see the new plan
modal — selftest tab is the fastest way to validate the swarm.

### Lane 2: 1-Hour Deep Dive (Maintainers & Regular Users)

**Goal**: Understand flow structure, agent design, how to extend the swarm.

**What you'll do**: Deep dive into Flow Studio, understand agent roles, learn
how to add/modify agents and flows.

**Read**: [docs/FLOW_STUDIO.md](./docs/FLOW_STUDIO.md)

**Tech reference**:

- Flow Studio uses FastAPI backend exclusively
- Understand the `/platform/status` endpoint, degraded mode, and governance
  tiers
- How to use Flow Studio to visualize and edit flows in `swarm/config/`

**Key takeaway**: The swarm is specification-first; you can extend it by
editing YAML config and regenerating adapters.

### Lane 3: Adoption TL;DR (Platform/DevEx Teams)

**Goal**: Get the swarm validation working in your repo ASAP.

**What you'll do**: Copy selftest tooling, wire CI gate, understand validation
workflow.

**Read**: Top of
[docs/ADOPTING_SWARM_VALIDATION.md](./docs/ADOPTING_SWARM_VALIDATION.md) for
5-min TL;DR, then full guide for implementation.

**Key takeaway**: Selftest is your CI gate; 3-tier blocking model
(KERNEL/GOVERNANCE/OPTIONAL); you control what blocks merges.

→ See [`docs/INDEX.md`](docs/INDEX.md) for the complete documentation map.

---

### Quick Commands for All Lanes

Validate the swarm locally before committing:

```bash
make dev-check         # Full validation + selftest (repo health check)
make selftest-fast     # Fast: KERNEL checks only (~400ms, inner-loop iteration)
make selftest          # Full 16-step suite with detailed output
make selftest-govern   # Governance checks only (no code tests)
```

**Developer workflow**: See [docs/SELFTEST_DEVELOPER_WORKFLOW.md](./docs/SELFTEST_DEVELOPER_WORKFLOW.md) for the complete guide to local testing, CI integration, and debugging.

---

## Further Reading

Once you've picked a lane, explore these as needed:

- **Getting Started**: [docs/GETTING_STARTED.md](./docs/GETTING_STARTED.md) —
  10 min, two guided paths (SDLC or governance track)
- **Narrative walkthrough**: [DEMO_RUN.md](./DEMO_RUN.md) — Step-by-step
  example of all 6 flows
- **Golden runs**: [docs/GOLDEN_RUNS.md](./docs/GOLDEN_RUNS.md) — Curated
  example runs for teaching and validation
- **Full documentation map**: [docs/INDEX.md](./docs/INDEX.md) — Complete
  index of all documentation
- **Philosophy**: [docs/WHY_DEMO_SWARM.md](./docs/WHY_DEMO_SWARM.md) — Core
  ideas and design choices
- **Claude Code integration**: [CLAUDE.md](./CLAUDE.md) — How to use this
  swarm with Claude Code

### Governance & Validation

- **Selftest system**: [docs/SELFTEST_SYSTEM.md](./docs/SELFTEST_SYSTEM.md) —
  Tiers (KERNEL/GOVERNANCE/OPTIONAL), AC traceability, Gherkin→pytest mapping
- **Developer workflow**: [docs/SELFTEST_DEVELOPER_WORKFLOW.md](./docs/SELFTEST_DEVELOPER_WORKFLOW.md) —
  Local testing, CI integration, debugging guide (TL;DR: 3 commands you need)
- **Branch protection setup**: [docs/BRANCH_PROTECTION_SETUP.md](./docs/BRANCH_PROTECTION_SETUP.md) —
  Enforce selftest as a mandatory merge gate (for repo admins)
- **AC matrix**: [docs/SELFTEST_AC_MATRIX.md](./docs/SELFTEST_AC_MATRIX.md) —
  Complete mapping of acceptance criteria to tests and surfaces
- **Operator runbook**: [docs/OPERATOR_CHECKLIST.md](./docs/OPERATOR_CHECKLIST.md) —
  Health checks, UI smoke tests, troubleshooting guide, escalation paths
- **Governance quick reference**: [docs/SELFTEST_GOVERNANCE.md](./docs/SELFTEST_GOVERNANCE.md) —
  Common issues and quick fixes
- **Ownership & escalation**: [docs/SELFTEST_OWNERSHIP.md](./docs/SELFTEST_OWNERSHIP.md) —
  Maintainer contact, escalation paths, decision log
- **Validation walkthrough**: [docs/VALIDATION_WALKTHROUGH.md](./docs/VALIDATION_WALKTHROUGH.md) —
  Learn by example: add a fake agent, see validation errors, understand why each check matters
- **CI gate setup**: [swarm/tools/CI_GATE_QUICK_START.md](./swarm/tools/CI_GATE_QUICK_START.md)
  — GitHub Actions integration

### Release Notes & Contracts

- **Release notes**: See `docs/RELEASE_NOTES_*.md` for version-specific changes
- **Stepwise contract**: [docs/STEPWISE_CONTRACT.md](./docs/STEPWISE_CONTRACT.md) —
  Receipt schema, event kinds, transcript format, behavioral invariants
- **Context budgets**: [docs/CONTEXT_BUDGETS.md](./docs/CONTEXT_BUDGETS.md) —
  Token discipline, history truncation, priority-aware selection

### More

- **Writing style**: [VOICE.md](./docs/archive/VOICE.md) — How we write; style guide
- **Lost?** Run `make help` for all available commands

---

## If You Use This

We'd like to hear from you! Here's how to participate:

| Want to... | Do this |
|------------|---------|
| **Report a bug** | Open an issue with the [Bug Report template](../../issues/new?template=bug_report.md) |
| **Ask a question** | Open an issue with the [Adoption Question template](../../issues/new?template=adoption_question.md) |
| **Contribute** | PRs welcome for: doc clarifications, new evaluation recipes, golden examples, bug fixes |
| **Share feedback** | Star the repo, file issues, or open discussions |

See [SUPPORT.md](SUPPORT.md) for full engagement guidelines and what to expect.

## Validating the Swarm

Before committing changes to agents, flows, or skills, validate alignment:

```bash
uv run swarm/tools/validate_swarm.py
```

For incremental validation (only files changed vs main branch):

```bash
uv run swarm/tools/validate_swarm.py --check-modified
```

To enforce strict swarm design constraints:

```bash
uv run swarm/tools/validate_swarm.py --strict
```

The validator checks five functional requirements:

- **FR-001**: Agent-file bijection (1:1 mapping between registry and files)
- **FR-002**: Frontmatter validation (required fields, type checking, design
  constraints)
- **FR-003**: Flow reference integrity (agents must exist in registry or
  be built-ins)
- **FR-004**: Skill file validation (declared skills have valid SKILL.md
  files)
- **FR-005**: RUN_BASE path placeholders (flows use `RUN_BASE/<flow>/` not
  hardcoded paths)

See [CLAUDE.md > Validation](./CLAUDE.md#validation) for detailed
documentation, common errors, and troubleshooting.

## Swarm Selftest System

This repo includes a **layered selftest** to validate swarm health without
treating every failure as broken: **KERNEL** (core Python checks),
**GOVERNANCE** (swarm alignment), and **OPTIONAL** (advanced validation).

### One Golden Command

Before committing changes to swarm/ or .claude/:

```bash
make dev-check   # Adapters + flows + validation + selftest (the repo health check)
```

For local dev iteration (faster):

```bash
make kernel-smoke   # 0.3s: Python checks only (KERNEL tier)
```

Other commands:

```bash
make selftest              # Full suite (16 steps)
make selftest-degraded     # Only KERNEL failures block
make selftest-doctor       # Diagnose failures
```

See [docs/SELFTEST_SYSTEM.md](./docs/SELFTEST_SYSTEM.md) for the full 16-step
breakdown and detailed documentation.

## Operationalization Status

This demo repo includes **working validation and CI integration** (FR-OP-001,
FR-OP-002):

- ✅ **CI validation**: `swarm-validate.yml` GitHub Actions workflow runs
  `make dev-check` on every PR
- ✅ **Local dev check**: `make dev-check` validates before each workflow
- ⚠️ **Pre-commit hook**: Documented in `CLAUDE.md`; optional via
  `pre-commit install`
- ⚠️ **Org-level policy enforcement**: Deferred to Phase 2 (branch
  protection rules, SLA dashboards)
- **Local validation**: Priority focus (make dev-check, selftest, CI gate)

**In brief**: This is a reference implementation prioritizing working code and
local validation over production infrastructure. For enterprise deployments, see
`swarm/infrastructure/` extension guides.

## Phase 0.5: Config-Driven Adapters

This swarm has entered **Phase 0.5**, introducing config-driven adapter
generation. Rather than hand-editing `.claude/agents/*.md` files, you can
now define agents in provider-neutral YAML and generate platform-specific
adapters.

### Quick Start: Generate Agents from Config

```bash
# Check if a config-driven agent is ready to generate
uv run swarm/tools/gen_adapters.py --platform claude \
  --agent deploy-decider --mode check

# Generate the Claude Code adapter
uv run swarm/tools/gen_adapters.py --platform claude \
  --agent deploy-decider --mode generate
```

This writes a fully-formed `.claude/agents/deploy-decider.md` from
`swarm/config/agents/deploy-decider.yaml` and the Jinja2 template in
`swarm/templates/claude/`.

### Key Files

- **`swarm/config/agents/`** — Provider-neutral agent definitions (YAML)
- **`swarm/platforms/claude.yaml`** — Claude Code platform profile
- **`swarm/templates/claude/`** — Jinja2 templates for Claude Code adapter
- **`swarm/tools/gen_adapters.py`** — Generator (check/generate modes)

### Status

Currently **2 pilot agents** are using config-driven generation:
`deploy-decider` and `merge-decider`. These agents demonstrate the pattern
for multi-platform support. Future phases (1–3) will expand config-driven
generation to all 45 agents and support additional platforms (GitLab,
Bitbucket, GitHub Actions).

See [docs/ROADMAP_2_4.md](./docs/ROADMAP_2_4.md) for the roadmap.

## Using This Swarm with Other Orchestrators

This repository is **Claude-native** (implemented using Claude Code), but
the swarm specification in `swarm/` is **portable** to other orchestrators.

### For Claude Code Users

- Entry point: `.claude/` directory
- Run flows with slash commands: `/flow-1-signal`, `/flow-2-plan`,
  `/flow-3-build`, `/flow-4-gate`, `/flow-5-deploy`, `/flow-6-wisdom`
- Quick start: See `DEMO_RUN.md` for a step-by-step walkthrough
- Complete reference: See `CLAUDE.md` for detailed usage guide

### For Non-Claude Implementers

To implement this swarm on another agentic system, you need to:

1. **Parse the swarm specification**:
   - `swarm/AGENTS.md` — roster of 48 agents (3 built-in + 45 domain)
   - `swarm/flows/flow-*.md` — flow graphs with nodes, RUN_BASE paths,
     and mermaid diagrams
   - `swarm/skills.md` — skill specifications

2. **Implement runtime primitives**:
   - **Explore agent** — fast, read-only search using Glob/Grep/Read/Bash
     (Haiku-powered in Claude)
   - **Skills** — global capabilities invoked by agents:
     - `test-runner` — execute tests, write logs and summaries
     - `auto-linter` — format and lint code
     - `policy-runner` — policy-as-code validation
   - **Git operations** — safe git commands via `repo-operator` agent

3. **Respect the RUN_BASE layout**:
   - All flow artifacts go under `swarm/runs/<run-id>/<flow>/`
   - Code/tests remain in standard locations: `src/`, `tests/`,
     `features/`, etc.
   - See `swarm/flows/` for exact RUN_BASE paths per flow

4. **Implement microloops**:
   - Critics never fix; they write harsh receipts
   - Implementers may be called multiple times until critics approve
   - See `swarm/flows/flow-3-build.md` for microloop patterns

5. **Reference the example**:
   - `swarm/examples/health-check/` is a self-contained demo showing all
     flow artifacts

For architectural details, see `ARCHITECTURE.md` which documents the spec vs
adapter layer separation.

## Recommended VS Code Setup

This repository includes a curated set of recommended VS Code extensions to
make working with the agentic SDLC flows pleasant and productive. Install
the suggested extensions from the prompt when you open this repo in VS Code.

- **AI & Swarm (Claude)**: Official Claude Code extension — run `/flow-*`
  commands and iterate on subagents inline. See the `anthropic.claude-dev`
  recommendation.
- **Languages & LSPs**: `rust-lang.rust-analyzer`,
  `dbaeumer.vscode-eslint`, `esbenp.prettier-vscode`,
  `redhat.vscode-yaml` (plus Terraform/Kubernetes support if you use
  those).
- **Testing & BDD**: Test Explorer, Cucumber/Gherkin support, Error Lens
  (`hbenl.vscode-test-explorer`, `cucumberopen.cucumber-official`,
  `usernamehw.errorlens`).
- **Docs & Diagrams**: `yzhang.markdown-all-in-one`,
  `bierner.markdown-mermaid`, `streetsidesoftware.code-spell-checker`,
  `davidanson.vscode-markdownlint`.
- **Infra / Containers / K8s**: `hashicorp.terraform`,
  `ms-azuretools.vscode-docker`,
  `ms-kubernetes-tools.vscode-kubernetes-tools` (optional).
- **Git & Collaboration**: `eamodio.gitlens`,
  `github.vscode-pull-request-github`.

The full list of recommendations lives in `.vscode/extensions.json`.
