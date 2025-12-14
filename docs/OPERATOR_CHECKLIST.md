# Operator Checklist: Selftest System Runbook

This document provides a **step-by-step runbook** for operators, SREs, and maintainers who deploy, monitor, or troubleshoot the selftest system.

Use this checklist to:
- **Verify** selftest health before release
- **Monitor** self test in production
- **Troubleshoot** failures with confidence
- **Understand** what's normal vs. what's broken

---

## Quick Health Check (2 min)

Run this daily or before any release:

```bash
# 1. Kernel smoke (fast baseline)
uv run swarm/tools/kernel_smoke.py
# Expected: "HEALTHY" or "BROKEN" + exit code 0/1

# 2. Full selftest plan (see all steps)
uv run swarm/tools/selftest.py --plan
# Expected: 10+ steps listed with tiers (KERNEL, GOVERNANCE, OPTIONAL)

# 3. Full selftest execution (takes ~2s)
uv run swarm/tools/selftest.py
# Expected: All steps PASS, exit code 0
# If any GOVERNANCE fails: Run `make selftest-doctor` to diagnose
```

If any of these fail, **stop and investigate before proceeding**. See § Troubleshooting below.

---

## Pre-Release Checklist

Before cutting a release or deploying selftest to production, verify:

### ✅ 1. Code & Contracts

- [ ] All Python lint checks pass: `uv run ruff check swarm/tools swarm/validator`
- [ ] All selftest steps are in config: `uv run swarm/tools/selftest_config.py` has 10+ steps
- [ ] No circular dependencies in steps: `uv run pytest tests/test_selftest_api_contract.py::test_selftest_plan_api_contract_no_circular_dependencies -v`
- [ ] AC IDs match Gherkin: `uv run pytest tests/test_selftest_ac_traceability.py -v`
- [ ] API contract tests pass: `uv run pytest tests/test_selftest_api_contract.py -v`
- [ ] Degradation log tests pass: `uv run pytest tests/test_selftest_degradation_log.py -v`

**Command to verify all**:

```bash
make validate-swarm && make kernel-smoke && uv run pytest tests/test_selftest_*.py -v
```

### ✅ 2. CLI & Tools

- [ ] `--plan` works: `uv run swarm/tools/selftest.py --plan` returns valid output in < 0.5s
- [ ] `--plan --json` works: `uv run swarm/tools/selftest.py --plan --json | jq . > /dev/null` (valid JSON)
- [ ] `--step` works: `uv run swarm/tools/selftest.py --step core-checks` completes
- [ ] `--degraded` works: `uv run swarm/tools/selftest.py --degraded` exits with code 0 or 1
- [ ] Degradation viewer works: `uv run swarm/tools/show_selftest_degradations.py` shows any existing logs
- [ ] Full selftest passes: `uv run swarm/tools/selftest.py` returns exit code 0

### ✅ 3. Flow Studio Integration

- [ ] Flow Studio starts: `make flow-studio`
- [ ] Selftest tab loads: Open http://localhost:5000, click **Selftest** tab
- [ ] Plan modal opens: Click "View Full Plan" button → modal appears
- [ ] Step details show: Click any step → drilldown modal with AC IDs appears
- [ ] Degradations visible: If any, "Degradations" section shows log entries
- [ ] Status endpoint works: `curl http://localhost:5000/platform/status | jq .selftest.plan` returns plan data

**UI Smoke Test** (manual):

```bash
# Start Flow Studio
make flow-studio &
sleep 2

# Check endpoints
curl -s http://localhost:5000/api/selftest/plan | jq '.summary'
curl -s http://localhost:5000/platform/status | jq '.state'

# Verify no 500 errors in the browser console
# (should see only 200 responses for /api and /platform endpoints)
```

### ✅ 4. Documentation & Links

- [ ] `SELFTEST_SYSTEM.md` is up-to-date
- [ ] `SELFTEST_API_CONTRACT.md` documents all endpoints
- [ ] `SELFTEST_AC_MATRIX.md` lists all ACs and their tests
- [ ] `SELFTEST_GOVERNANCE.md` has troubleshooting guide
- [ ] `README.md` links to this checklist

---

## Daily Monitoring

### Check 1: Kernel Health (Every 4 hours in production)

```bash
# Health endpoint (if running Flow Studio)
curl -s http://localhost:5000/platform/status | jq '.state'
# Expected: "HEALTHY", "DEGRADED", or "BROKEN"

# If not running:
uv run swarm/tools/kernel_smoke.py
# Expected: "HEALTHY" + exit 0
```

**Action if broken**:
- Run `make selftest-doctor` to get diagnostics
- Check which step failed: `grep FAIL <latest-report>`
- Run individual step: `uv run swarm/tools/selftest.py --step <failed-step>`

### Check 2: Degradation Log Size (Weekly)

```bash
# Check if degradations exist and are recent
ls -lah selftest_degradations.log 2>/dev/null || echo "No degradations"

# If it exists, show recent entries
tail -5 selftest_degradations.log | jq .

# If too many (> 100 lines), consider cleanup:
# wc -l selftest_degradations.log
# rm selftest_degradations.log  # Warning: deletes history
```

**Action if concerning**:
- Same failed step repeatedly → escalate to Fix step owner
- New failures → investigate root cause
- Very old entries → safe to cleanup (commit history to git first)

### Check 3: Test Coverage (Monthly)

Run full suite:

```bash
# All selftest tests (should take < 30s)
uv run pytest tests/test_selftest_*.py -v --tb=short

# Check coverage thresholds
make test-selftest-contracts  # If available
```

**Expected**: All green ✅

---

## Flow Studio Operator UI Checklist

When running `make flow-studio` and navigating to the Selftest tab:

### Layout & Navigation

- [ ] **Status banner** shows HEALTHY / BROKEN / DEGRADED (color-coded)
- [ ] **Tier breakdown** shows counts: KERNEL (1), GOVERNANCE (8), OPTIONAL (2)
- [ ] **"View Full Plan"** button is clickable
- [ ] Modal opens/closes with Esc or clicking outside

### Modal: Step List

- [ ] Steps are sorted in execution order
- [ ] Each step shows: **id** (bold), **tier** (color), **AC IDs** (badges)
- [ ] Steps with dependencies show "Depends on: ..." if applicable
- [ ] Clicking a step opens detail modal

### Modal: Step Details

- [ ] **Step name** and **description** visible
- [ ] **AC IDs** shown as clickable badges
- [ ] **Remediation command** provided (e.g., "Run: uv run ... --step agents-governance")
- [ ] **Tier** and **severity** clearly labeled
- [ ] **Status** (PASS/FAIL/SKIP) visible with color

### Degradations Section (if present)

- [ ] **"Degradations"** section appears if `selftest_degradations.log` exists
- [ ] Entries show: **timestamp**, **step_id**, **message** snippet, **Fix** command
- [ ] Clicking a fix command copies it to clipboard (if implemented)
- [ ] Entries are sorted newest-first

### Console (Dev Tools)

- [ ] No 500 errors (all endpoints return 200 or 503)
- [ ] Network tab shows:
  - `/api/selftest/plan` → 200 (or 503 if unavailable)
  - `/platform/status` → 200
- [ ] Response times: < 100ms typical (> 1s is slow, investigate)

---

## Troubleshooting Decision Tree

### Problem: `kernel_smoke.py` fails

```
├─ Check ruff:
│  └─ uv run ruff check swarm/tools swarm/validator
│     ├─ Has errors? → Fix linting issues
│     └─ Clean? → Next
│
├─ Check compile:
│  └─ uv run python -m compileall swarm/tools swarm/validator
│     ├─ Has errors? → Fix syntax errors
│     └─ Clean? → Next
│
└─ Escalate: KERNEL error, must block work
   └─ Run: make selftest-doctor
```

### Problem: A single step fails (e.g., `agents-governance`)

```
├─ Is it KERNEL or GOVERNANCE?
│  ├─ KERNEL? → Must fix before proceeding
│  └─ GOVERNANCE? → Can use `--degraded` mode
│
├─ Run that step in isolation:
│  └─ uv run swarm/tools/selftest.py --step agents-governance
│     ├─ Shows detailed error → Fix root cause
│     └─ Still fails? → Next
│
├─ Check docstring & recent commits:
│  └─ Did something change recently?
│     ├─ Yes? → Revert or fix that change
│     └─ No? → Next
│
└─ Ask for help:
   └─ Post in #engineering-platforms:
      "agents-governance failing since 2025-12-01, see run X"
```

### Problem: Degradation log is growing (many failed steps)

```
├─ Is this degraded mode (--degraded flag)?
│  ├─ Yes? → By design; steps allowed to fail
│  │         Show selftest_degradations.log to stakeholders
│  └─ No? → Should not happen; investigate
│
├─ Are the same steps failing repeatedly?
│  ├─ Yes? → Known issue, document in SELFTEST_GOVERNANCE.md
│  └─ No? → Different failures; escalate each
│
└─ Cleanup (optional):
   └─ rm selftest_degradations.log
      git add -A && git commit -m "chore: clear selftest degradations"
      # (history lost; only do if intentional)
```

### Problem: Flow Studio API endpoint returns 503

```
├─ Is the FastAPI server running?
│  └─ curl http://localhost:5000/health
│     ├─ 200? → Server OK, next
│     └─ Connection refused? → Start: make flow-studio
│
├─ Check selftest module availability:
│  └─ uv run swarm/tools/selftest.py --plan
│     ├─ Works? → Selftest module OK, but API not loading it
│     └─ Fails? → Selftest module broken, fix it first
│
├─ Check server logs:
│  └─ (Check whatever process manager is running FastAPI)
│     ├─ Syntax error? → Fix swarm/tools/flow_studio_fastapi.py
│     └─ Import error? → Check selftest_config imports
│
└─ Restart:
   └─ kill $(lsof -t -i :5000)
      make flow-studio
```

### Problem: Test suite fails (pytest)

```
├─ Single test failing?
│  ├─ uv run pytest tests/test_selftest_api_contract.py::test_name -vvs
│     ├─ Shows assertion error → Read carefully, fix code
│     └─ Shows import error → Next
│
├─ Import error (no module named ...)?
│  ├─ uv sync --upgrade
│  └─ uv run pytest ...
│
├─ Multiple tests failing?
│  ├─ uv run pytest tests/test_selftest_*.py --tb=short
│     (shows pattern of failures)
│     ├─ Same root cause? → Fix one, rerun
│     └─ Different? → Escalate
│
└─ Ask for help:
   └─ Include:
      - Command you ran
      - Full error output
      - Python version (python --version)
      - Recent commits to swarm/ or tests/
```

---

## Common Fixes

### "Agent 'X' not found in registry" (agents-governance fails)

```bash
# Did you add a new agent?
# 1. Register in swarm/AGENTS.md
# 2. Create .claude/agents/<key>.md with matching name
# 3. Validate: make validate-swarm
# 4. Regenerate: make gen-adapters && make check-adapters
```

### "RUN_BASE placeholder not found" (devex-contract fails)

```bash
# Check that flow specs use RUN_BASE/<flow>/ format
grep -r "RUN_BASE" swarm/flows/
# Should see: "RUN_BASE/signal/", "RUN_BASE/build/", etc.
# NOT: hardcoded paths like "swarm/runs/my-ticket/build/"
```

### "Selftest step duration > 2 seconds"

```bash
# Profiling (slow step):
time uv run swarm/tools/selftest.py --step <slow-step>

# If > 0.5s:
# ├─ Is it a shell command? (ruff, validate_swarm.py, etc.)
# │  └─ Is the repo large? → Expected, no action
# │
# └─ Is it a Python import loop?
#    └─ Check swarm/tools/*.py for heavy imports at module level
#       (Move to function level)
```

### "Degradation log has corrupted JSONL" (bad entry)

```bash
# Validate each line
uv run python3 -c "
import json
with open('selftest_degradations.log') as f:
    for i, line in enumerate(f, 1):
        try:
            json.loads(line)
        except:
            print(f'Line {i}: INVALID JSON')
"

# If found, remove the bad line manually:
sed -i '/<line-number>d' selftest_degradations.log
```

---

## Escalation Paths

### 🟡 KERNEL Failure (selftest blocks all work)

**Severity**: CRITICAL
**Owner**: Platform/Infra team
**Response time**: < 1 hour

```
1. Run: make selftest-doctor
2. Identify which step failed
3. Run that step in isolation
4. Check recent commits to swarm/
5. If blocking all work, revert problematic change
6. Escalate to #engineering-platforms
```

**Example**: `core-checks` fails because of linting error in swarm/tools/.

### 🟠 GOVERNANCE Failure (selftest can be degraded)

**Severity**: HIGH
**Owner**: Relevant step owner
**Response time**: < 4 hours

```
1. Run: uv run swarm/tools/selftest.py --degraded
2. Check: uv run swarm/tools/show_selftest_degradations.py
3. Identify root cause (agent config, flow contract, policy, etc.)
4. Open issue: "Fix <step>: <brief description>"
5. Assign to step owner
6. Meanwhile: Use --degraded mode to unblock work
```

**Example**: `agents-governance` fails because a new agent isn't registered.

### 🔵 OPTIONAL Failure (selftest informational)

**Severity**: LOW
**Owner**: Metrics/QA team
**Response time**: < 1 week

```
1. Check: uv run swarm/tools/selftest.py --step <optional-step>
2. If it's a known limitation: Document in SELFTEST_GOVERNANCE.md
3. If fixable: File issue for next sprint
4. No action needed: OPTIONAL failures don't block work
```

**Example**: `ac-coverage` fails because coverage is 95% (target 98%).

---

## References

- **System Design**: `docs/SELFTEST_SYSTEM.md` — Architecture, tiers, design goals
- **API Contract**: `docs/SELFTEST_API_CONTRACT.md` — Endpoint specs
- **AC Matrix**: `docs/SELFTEST_AC_MATRIX.md` — AC-to-step traceability
- **Governance**: `docs/SELFTEST_GOVERNANCE.md` — Common issues & fixes
- **Config**: `swarm/tools/selftest_config.py` — Step definitions
- **Tests**: `tests/test_selftest_*.py` — Comprehensive test suite

---

## Questions?

Before escalating:

1. ✅ Run `make selftest-doctor` (diagnoses common issues)
2. ✅ Check `docs/SELFTEST_GOVERNANCE.md` (common fixes)
3. ✅ Search recent commits for changes to `swarm/tools/` or `tests/`
4. ✅ Try running the step in isolation: `uv run swarm/tools/selftest.py --step <id>`

Then post in **#engineering-platforms** with:
- What you ran
- What you expected
- What actually happened
- Full error output (or screenshot)
- Link to selftest run artifact (if available)
