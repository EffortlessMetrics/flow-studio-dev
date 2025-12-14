# Selftest Governance Reference

This document provides a quick reference for the selftest system: the 16 steps, their governance tiers, common errors, and remediation strategies.

**Related documents:**
- `specs/spec_ledger.yaml` — Master specification with acceptance criteria
- `features/selftest.feature` — BDD scenarios verifying all ACs
- `.claude/skills/heal_selftest/SKILL.md` — Diagnostic skill with detailed procedures
- `docs/SELFTEST_SYSTEM.md` — Architecture and design documentation

---

## Quick Reference: The 16 Selftest Steps

| # | Step ID | Tier | Expected Runtime | Description |
|---|---------|------|------------------|-------------|
| 1 | `core-checks` | **KERNEL** | ~0.1s | Python linting: `ruff check`, `compileall` (or Rust: cargo fmt, clippy, test in template-repo) |
| 2 | `skills-governance` | GOVERNANCE | ~0.05s | Validate `.claude/skills/*/SKILL.md` frontmatter and structure |
| 3 | `agents-governance` | GOVERNANCE | ~0.1s | Validate `.claude/agents/*.md` frontmatter against `swarm/AGENTS.md` |
| 4 | `bdd-scenarios` | GOVERNANCE | ~0.2s | Validate Gherkin syntax in `features/*.feature` |
| 5 | `ac-status` | GOVERNANCE | ~0.1s | Check acceptance criteria coverage in `specs/spec_ledger.yaml` |
| 6 | `policy-tests` | GOVERNANCE | ~0.3s | Run OPA/Conftest policy validation (if configured) |
| 7 | `devex-contract` | GOVERNANCE | ~0.2s | Validate swarm manifest: flows, commands, skills alignment |
| 8 | `graph-invariants` | GOVERNANCE | ~0.15s | Verify flow graph connectivity and agent references |
| 9 | `ac-coverage` | OPTIONAL | ~0.3s | Check that ACs have sufficient test coverage (threshold: 80%) |
| 10 | `extras` | OPTIONAL | ~0.2s | Experimental checks (linting, extra validation) |

**Total baseline runtime:** ~2.0 seconds (KERNEL + GOVERNANCE)

---

## Governance Tiers

### KERNEL Tier

**What it is**: Core repository health. If KERNEL fails, the repo is fundamentally broken and **no merges are allowed**.

**Steps in KERNEL**:
- `core-checks` — Python tooling (ruff linting, compile check) in Flow Studio; Rust tooling (fmt, clippy, tests) in template-repo

**When it fails** (Flow Studio example):
- Python code fails `ruff check` → Linting errors (unused imports, f-string issues, etc.)
- Python code fails `compileall` → Module doesn't compile/has syntax errors

**When it fails** (Rust template example):
- Rust code fails `cargo fmt --check` → Code style is inconsistent
- Rust code fails `cargo clippy` → Static analysis issues
- Rust code fails `cargo test --lib` → Unit tests fail

**Common causes**:
- Unused imports or variables in Python code (Flow Studio)
- Syntax errors that prevent compilation
- Developer didn't run linting before committing

**How to fix** (Flow Studio):
1. Run `uv run ruff check swarm/tools --fix` to auto-fix most issues
2. Review and fix remaining issues manually
3. Commit the fixes: `git add . && git commit -m "fix: resolve kernel health issues"`

**How to fix** (Rust template):
1. Run `cargo fmt` to auto-format code
2. Run `cargo clippy --fix` to auto-fix clippy warnings (verify each fix!)
3. Run `cargo test --lib` and fix any failing tests
4. Commit the fixes: `git add . && git commit -m "fix: resolve kernel health issues"`

**Escalation**:
- If KERNEL is broken, **stop all other work**
- Fix KERNEL before proceeding to GOVERNANCE or merge
- KERNEL cannot be ignored, even in `--degraded` mode

---

### GOVERNANCE Tier

**What it is**: Swarm specification compliance. GOVERNANCE failures mean the swarm's contracts are violated (agents misconfigured, flows broken, etc.). **Merges are blocked unless `--degraded` mode is used.**

**Steps in GOVERNANCE**:
- `skills-governance` — Skill definitions
- `agents-governance` — Agent definitions
- `bdd-scenarios` — BDD test scenarios
- `ac-status` — Acceptance criteria tracking
- `policy-tests` — Policy validation
- `devex-contract` — Flows, commands, skills manifest
- `graph-invariants` — Flow graph connectivity

**When it fails** (examples):
- Agent frontmatter is missing required field (`color`, `model`, etc.)
- Agent in flow spec doesn't exist in `swarm/AGENTS.md`
- Skill file is missing or has invalid frontmatter
- BDD scenario has Gherkin syntax error
- Flow spec has a hard-coded path instead of `RUN_BASE` placeholder

**Common causes**:
- Manual edits to agent/skill files without running validation
- Agent registries got out of sync (added agent but didn't update all references)
- Flow specs reference old agent names
- Gherkin feature files have syntax errors
- Missing AC entries in spec_ledger

**How to fix**:

**Option 1: Immediate fixes (mechanical)**
1. Run `make selftest --step agents-governance --verbose` to see the exact error
2. Use the heal_selftest skill: `make heal-selftest --step agents-governance`
3. Apply the suggested fixes (usually: run `make gen-adapters`, update AGENTS.md, fix Gherkin)
4. Commit: `git add . && git commit -m "fix: resolve governance issues"`

**Option 2: Workaround (if fix is large)**
1. Document the governance failure in `selftest_degradations.log`
2. Run with `--degraded` mode: `make selftest --degraded`
3. Proceed with merge (humans will see the degraded state in CI)
4. Create a follow-up GitHub issue to fix the underlying governance problem

**Escalation**:
- GOVERNANCE failures can be **temporarily ignored** with `--degraded` mode
- Use this **only for short-term workarounds** (e.g., waiting for a new agent to be fully onboarded)
- Always create a GitHub issue to track the fix
- Mark severity as P1 (must fix before next release) or P2 (fix in next sprint)

---

### OPTIONAL Tier

**What it is**: Nice-to-have checks that improve code quality but don't block merges. OPTIONAL failures are warnings; they never affect exit codes.

**Steps in OPTIONAL**:
- `ac-coverage` — Acceptance criteria test coverage (threshold: 80%)
- `extras` — Experimental checks, linting, future requirements

**When it fails** (examples):
- AC test coverage is 75% (below 80% threshold)
- Experimental linting check suggests improvements
- Optional code quality metric is below target

**Common causes**:
- New AC was added without sufficient test coverage
- Experimental checker is being strict (may be configurable)
- Code coverage threshold was recently raised

**How to fix**:
- OPTIONAL failures don't block merges
- If you want to fix: run `make selftest --step ac-coverage --verbose` to see specifics
- Add missing tests or re-evaluate the threshold
- Use `--degraded` mode if you want to ignore for now

**Escalation**:
- OPTIONAL failures never escalate
- They're warnings only
- Humans can choose to fix or ignore based on urgency

---

## Error Categories and Remediation

### Category: Agent Governance Failures

**Symptoms**:
```
FAIL agents-governance: Agent 'foo-bar' registered but .claude/agents/foo-bar.md not found
```

**Root causes**:
1. Agent added to `swarm/AGENTS.md` but no `.md` file created
2. Agent filename doesn't match registry key (case-sensitive)
3. Config-backed agent not regenerated

**Fixes**:
```bash
# Fix 1: Create missing agent file
touch .claude/agents/foo-bar.md
# Add required frontmatter (see CLAUDE.md template)

# Fix 2: Check filename matches exactly (case-sensitive)
ls -la .claude/agents/ | grep "foo-bar"

# Fix 3: Regenerate config-backed adapters
make gen-adapters
make check-adapters
```

---

### Category: Skill Governance Failures

**Symptoms**:
```
FAIL skills-governance: Skill 'heal-selftest' frontmatter invalid: missing 'name'
```

**Root causes**:
1. Skill SKILL.md file is missing required frontmatter field
2. YAML frontmatter not properly delimited with `---`
3. Tilde (`~`) in description without escaping

**Fixes**:
```bash
# Check skill file structure
cat .claude/skills/heal-selftest/SKILL.md | head -15

# Ensure frontmatter has all required fields:
# ---
# name: heal-selftest
# description: (text)
# allowed-tools: (list)
# category: (category)
# tier: (tier)
# ---

# Escape special characters in YAML
# Bad: description: ~
# Good: description: "N/A" or description: ""
```

---

### Category: Flow/Devex Contract Failures

**Symptoms**:
```
FAIL devex-contract: Flow 'flow-3-build' references unknown agent 'test-critic'
```

**Root causes**:
1. Agent typo in flow spec (Levenshtein distance suggested in error)
2. Agent was renamed but flow spec not updated
3. Agent not registered in `swarm/AGENTS.md`

**Fixes**:
```bash
# Check if agent exists
grep "test-critic" swarm/AGENTS.md

# If not found, check spelling in flow spec
grep "test-critic" swarm/config/flows/flow-3.yaml

# If spelling wrong, fix and regenerate
# make gen-flows

# If agent missing, register it and regenerate
```

---

### Category: BDD Syntax Errors

**Symptoms**:
```
FAIL bdd-scenarios: features/selftest.feature:15: Expected 'Scenario' or 'Scenario Outline' but got 'Sceario'
```

**Root causes**:
1. Typo in Gherkin keywords (Scenario, Given, When, Then, etc.)
2. Indentation errors
3. Missing colon after Scenario/Feature/Rule

**Fixes**:
```bash
# View the problematic lines
sed -n '10,20p' features/selftest.feature

# Common fixes:
# Bad: "Sceario:" → Good: "Scenario:"
# Bad: "Given foo" (no: prefix) → Good: "Given something happens"
# Bad: "  Feature:" → Good: "Feature:" (no indent)

# Re-check syntax
make selftest --step bdd-scenarios --verbose
```

---

### Category: Acceptance Criteria Tracking Failures

**Symptoms**:
```
FAIL ac-status: AC 'AC-SELFTEST-KERNEL-FAST' in spec_ledger.yaml has no linked tests
```

**Root causes**:
1. AC in spec_ledger.yaml has empty `tests` array
2. AC has no corresponding BDD scenario tag
3. AC exists but no status field

**Fixes**:
```bash
# Check spec_ledger.yaml for missing tests
grep -A5 "AC-SELFTEST-KERNEL-FAST" specs/spec_ledger.yaml | grep -c "tests:"

# Add tests array to AC if missing:
# acceptance_criteria:
#   - id: AC-SELFTEST-KERNEL-FAST
#     tests:
#       - type: integration
#         command: "make kernel-smoke"

# Add BDD scenario with matching tag:
# @AC-SELFTEST-KERNEL-FAST
# Scenario: Kernel smoke check is fast
```

---

## When to Use `--degraded` Mode

Use `make selftest --degraded` when:

1. **A GOVERNANCE failure is blocking your merge, and:**
   - The underlying issue is known
   - A fix is in progress (in a separate PR)
   - You need to ship code now for a production reason
   - You have approval from your tech lead

2. **Example**: Agent config is being migrated, causing a temporary mismatch in `agents-governance` check

**Steps**:
```bash
# 1. Run degraded mode
make selftest --degraded

# 2. Check what failed
cat selftest_degradations.log

# 3. Document in your PR description:
#    "⚠️ This PR runs with --degraded due to agent migration.
#     See #123 for tracking the fix."

# 4. Human review must acknowledge the degraded state

# 5. KERNEL failures still block you!
if [ $(cat selftest_degradations.log | grep KERNEL) ]; then
    echo "ERROR: KERNEL failures cannot be ignored"
    exit 1
fi
```

**Never use `--degraded`**:
- For KERNEL failures (they must be fixed)
- As a permanent workaround (create a tracking issue instead)
- Without documenting why in your commit/PR description

---

## Escalation Decision Tree

```
Does selftest fail?
│
├─→ NO → All good, proceed to next gate
│
└─→ YES → Is it a KERNEL failure?
    │
    ├─→ YES → P0 CRITICAL
    │        Action: Stop. Fix immediately.
    │        Command: make kernel-smoke --verbose
    │        Escalation: Block merge, notify team
    │
    └─→ NO → Is it a GOVERNANCE failure?
        │
        ├─→ YES → Is the fix small?
        │        │
        │        ├─→ YES (< 10 min) → P1 SHOULD FIX
        │        │                   Action: Fix now (make gen-adapters, etc.)
        │        │                   Command: make selftest --step <id> --verbose
        │        │
        │        └─→ NO (> 10 min) → P2 DEFER
        │                           Action: Use --degraded mode
        │                           Document in PR, create tracking issue
        │
        └─→ NO → OPTIONAL failure → P3 INFO
                 Action: Ignore or fix if quick
                 No blocking
```

---

## Remediation Strategy Reference Table

| Error Type | Tier | Likely Cause | Quick Fix | Tool |
|-----------|------|-------------|-----------|------|
| fmt/clippy fail | KERNEL | Code style or warnings | `cargo fmt && cargo clippy --fix` | make kernel-smoke |
| Unit tests fail | KERNEL | Logic error | Run failing test, read output, fix code | cargo test --lib |
| Agent mismatch | GOVERNANCE | Agent not registered | Run `make gen-adapters` | agents-governance |
| Flow reference broken | GOVERNANCE | Agent renamed or typo | Check `swarm/AGENTS.md`, update flow | devex-contract |
| Gherkin syntax error | GOVERNANCE | Typo in Gherkin | Fix keyword or indent | bdd-scenarios |
| Skill frontmatter invalid | GOVERNANCE | Missing field or YAML error | Add field, check delimiters | skills-governance |
| AC coverage low | OPTIONAL | Tests missing for AC | Add test scenario or update AC | ac-coverage |

---

## Common Commands Quick Reference

```bash
# Check kernel health
make kernel-smoke

# See full selftest plan
make selftest --plan

# Run only one step
make selftest --step core-checks

# Run steps up to a point
make selftest --until agents-governance

# Run with degraded mode (governance OK if kernel passes)
make selftest --degraded

# Run with verbose output
make selftest --verbose

# See failures in JSON format
make selftest --json | jq '.failures'

# Check what changed since last run
make selftest --compare-baseline

# Heal a specific failure
.claude/skills/heal_selftest/diagnose.sh --step agents-governance

# View degradation log
cat selftest_degradations.log
tail -n 10 selftest_degradations.log  # Last 10 entries
```

---

## Integration with Swarm Flows

**Flow 3 (Build)**:
- Selftest runs at the **end** of code implementation
- `--strict` mode (all failures block)
- Part of the build receipt

**Flow 4 (Gate)**:
- Selftest is re-run for verification
- Checks that Flow 3 produced passing selftest
- May bounce back to Flow 3 if selftest is broken

**Flows 5-6 (Deploy, Wisdom)**:
- Selftest state is included in artifact metadata
- Regressions in selftest are tracked

---

## See Also

- **Specs**: `specs/spec_ledger.yaml` — All acceptance criteria with tests
- **Scenarios**: `features/selftest.feature` — BDD test coverage
- **Diagnostic**: `.claude/skills/heal_selftest/SKILL.md` — Detailed healing procedures
- **Architecture**: `docs/SELFTEST_SYSTEM.md` — Design and philosophy
- **Flows**: `docs/SWARM_FLOWS.md` — How selftest fits into Flows 1-6
