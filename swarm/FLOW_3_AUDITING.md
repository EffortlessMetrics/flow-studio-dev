# Flow 3 Auditing: Ground Truth Binding and Critic Hard Rules

## Problem Statement

Flow 3 (Build) was **functionally correct** but **narratively unreliable**. The orchestrator could write working code and tests, but critics and reporters were **cooperative instead of adversarial**:

1. **Narrative drift**: Claimed "196 tests total" but pytest output clearly indicated different counts
2. **Over-promotion of FR status**: Marked FRs "VERIFIED ✓" when tests were xfailed or missing
3. **Mutation as vibes, not gates**: Different runs reported different mutation scores with no explicit thresholds or binding

The root cause: Critics and reporters were **summarizers**, not **auditors**. They accepted input, polished prose, and output claims without binding to ground truth.

---

## Solution: Ground Truth Binding + Hard Rules

Flow 3 now enforces a **two-layer auditing model**:

1. **Ground Truth Sources** (canonical):
   - pytest summary (test counts)
   - mutation tool output (mutation score)
   - ADR, requirements, contracts (design conformance)

2. **Critic Hard Rules**:
   - Critics MUST bind reported metrics to ground truth
   - Critics MUST detect FR-to-test and FR-to-code mappings
   - Critics MUST flag gaps explicitly
   - Critics MUST reject any claim that contradicts ground truth

3. **Reporter Discipline**:
   - Reporters are neutral summarizers, NOT narrators
   - Reporters consume (never upgrade) verdicts from critics
   - Reporters preserve FR status distinctions (FULLY_VERIFIED vs MVP_VERIFIED vs PARTIAL)
   - Reporters never recompute metrics

---

## FR Status Scheme

Each FR has an explicit status after Flow 3:

### FULLY_VERIFIED
- All tests for this FR pass (no xfail/skip)
- Negative cases asserted (bad input handling)
- Code implementation found and reviewed
- No exceptions or workarounds

### MVP_VERIFIED
- All MVP-tagged tests pass
- Extended/optional tests may be xfailed
- Code implements MVP scope
- **Explicitly acceptable limitation** (xfailed tests must be tagged @EXT or @FUTURE)

### PARTIAL
- Some tests pass, some fail, or implementation missing
- Cannot claim readiness
- Blocked or deferred
- Requires additional work

### UNKNOWN
- Insufficient information; coverage unclear
- Requires investigation

**Hard Rule**: No FR may be marked FULLY_VERIFIED if any of its tests are xfailed or skipped.

---

## Critic Hard Rules (by Agent)

### test-critic Hard Rules

1. **Pytest binding**: All test counts MUST come from pytest output. Quote the pytest summary verbatim.

2. **FR-to-test mapping**: Identify which tests cover which FRs (via naming, markers, or manual review). If no tests found for an FR, note "[NO TESTS FOUND]".

3. **xfail detection**: If any test for a core FR is xfailed and FR claims FULLY_VERIFIED, set Status: UNVERIFIED. Only MVP_VERIFIED may have xfailed tests (@EXT).

4. **Metrics consistency**: If prose claims "196 tests" but pytest shows "191+4+1 = 196" (breakdown matters), document both. If inconsistency found (e.g., 196 vs 224), set Status: BLOCKED and require upstream fix.

5. **Output format**: test_critique.md MUST include:
   - Exact pytest summary (canonical)
   - FR-to-test mapping table
   - Metrics consistency check result
   - List of xfailed tests and their FR association

### code-critic Hard Rules

1. **FR-to-code mapping**: For each FR, locate implementation (file:line, function/module). If not found, flag "[NO IMPLEMENTATION FOUND]".

2. **Gap detection**: If an FR claims FULLY_VERIFIED but code-critic cannot find both implementation AND test coverage, set Status: UNVERIFIED.

3. **xfailed core behavior**: If a test for a core FR is xfailed, that FR cannot be FULLY_VERIFIED.

4. **Architectural violations**: ADR violations are blocking issues.

5. **Output format**: code_critique.md MUST include:
   - FR implementation coverage table (with file:line)
   - Explicit gaps if any

### mutator Hard Rules

1. **Mutation score binding**: Report the actual score from the tool (killed / total). Do not invent thresholds or round scores.

2. **No threshold labels**: Do not say "strong/weak/acceptable" based on judgment. Report observed facts.

3. **Surviving mutation → FR gap**: Map surviving mutations to FRs. If a surviving mutation is in code for REQ-001, note "test gap for REQ-001".

4. **Critical path focus**: Flag surviving mutations in critical code paths (per ADR or requirements) for fixer attention.

### self-reviewer Hard Rules

1. **Never recalculate metrics**: All numbers MUST come verbatim from pytest, mutation reports. If you cannot find a source, set `metrics_binding: hard_coded` and Status: UNVERIFIED.

2. **Consume, never upgrade FR status**: If test-critic says "MVP_VERIFIED", you report MVP_VERIFIED. You do NOT infer "well, it's probably FULLY_VERIFIED."

3. **Detect metric mismatches**: If artifacts claim different test counts, flag Status: UNVERIFIED with "metrics inconsistent" note.

4. **Pytest summary binding**: self_review.md MUST include the exact pytest summary line (e.g., "191 passed, 4 xfailed, 1 xpassed, 0 failed").

5. **critic_verdicts are read-only**: Copy verdicts from critics exactly. Do not interpret.

6. **Output format**: build_receipt.json MUST include:
   - `metrics_binding: pytest | hard_coded`
   - `tests.metrics_consistency: OK | MISMATCH`
   - `requirements.fr_status` (mapping of FR → status)
   - `critic_verdicts` (copied from critics)

### gh-reporter Hard Rules

1. **No metric recomputation**: Report what the receipt says, verbatim. Do not recalculate.

2. **No status upgrades**: If receipt says "PARTIAL", report "PARTIAL". Do not say "but we're 90% done."

3. **Preserve FR status distinctions**: FULLY_VERIFIED ≠ MVP_VERIFIED. Label them distinctly.

4. **Link, don't duplicate**: Reference build_receipt.json and critiques. Summarize, don't invent.

5. **Neutral tone**: State gaps plainly ("REQ-003 incomplete; code-critic flagged missing implementation"). Do not spin as "future work."

---

## Build Receipt Structure (Updated)

The `build_receipt.json` is now the audit trail for Flow 4 (Gate):

```json
{
  "run_id": "<run-id>",
  "branch": "<branch-name>",
  "timestamp": "<iso8601>",

  "metrics_binding": "pytest | hard_coded",

  "requirements": {
    "touched": ["REQ-001", "REQ-004"],
    "untouched": ["REQ-007"],
    "fr_status": {
      "REQ-001": "FULLY_VERIFIED",
      "REQ-004": "MVP_VERIFIED",
      "REQ-007": "PARTIAL"
    }
  },

  "tests": {
    "status": "VERIFIED | UNVERIFIED | BLOCKED",
    "total": "<PYTEST_TOTAL>",
    "passed": "<PYTEST_PASSED>",
    "failed": "<PYTEST_FAILED>",
    "xfailed": "<PYTEST_XFAILED>",
    "xpassed": "<PYTEST_XPASSED>",
    "skipped": "<PYTEST_SKIPPED>",
    "pytest_summary_source": "test_critique.md",
    "metrics_consistency": "OK | MISMATCH"
  },

  "code": {
    "status": "VERIFIED | UNVERIFIED | BLOCKED",
    "summary_file": "code_critique.md"
  },

  "mutation": {
    "status": "VERIFIED | NOT_RUN | BLOCKED",
    "score": "<MUTATION_SCORE>",
    "killed": "<MUTATIONS_KILLED>",
    "total": "<MUTATIONS_TOTAL>"
  },

  "critic_verdicts": {
    "test_critic": "VERIFIED",
    "code_critic": "VERIFIED",
    "mutation": "VERIFIED"
  },

  "files_changed": ["src/...", "tests/..."],
  "assumptions": ["..."],
  "unresolved": ["REQ-003 incomplete"],
  "ready_for_gate": true,

  "notes": [
    "REQ-004 is MVP_VERIFIED with xfailed EXT tests; not claiming full coverage",
    "Mutation score <MUTATION_SCORE> with documented surviving mutations"
  ]
}
```

**Template Note**: The values shown in angle brackets (`<PYTEST_TOTAL>`, `<MUTATION_SCORE>`, etc.) are **placeholders only**. Always extract metrics directly from pytest output or mutation tool; never copy template numbers as actual values.

**Key invariants**:

- If `metrics_binding: hard_coded`, receipt status must be UNVERIFIED.
- If `metrics_consistency: MISMATCH`, receipt status must be UNVERIFIED.
- `fr_status` values are copied from test-critic and code-critic, not invented.

---

## Practical Example

### Before (Cooperative)

**pytest output**:
```
<PYTEST_PASSED> passed, <PYTEST_XFAILED> xfailed, <PYTEST_XPASSED> xpassed, <PYTEST_FAILED> failed
```

**test-critic said**:
```
Tests: good coverage, <PYTEST_TOTAL> tests total
Status: VERIFIED
```

**self-reviewer said**:
```
Tests: <PYTEST_TOTAL> total, <PYTEST_PASSED> passing
Status: VERIFIED
```

**Problem**: Claims numbers don't match pytest breakdown. Metric mismatch ignored.

### After (Auditing)

**pytest output** (ground truth):
```
<PYTEST_PASSED> passed, <PYTEST_XFAILED> xfailed, <PYTEST_XPASSED> xpassed, <PYTEST_FAILED> failed
```

**test-critic says**:
```
Pytest Summary (Canonical): <PYTEST_PASSED> passed, <PYTEST_XFAILED> xfailed, <PYTEST_XPASSED> xpassed, <PYTEST_FAILED> failed

FR-to-Test Mapping:
- REQ-001: ✓ tests/<feature>_test.rs::test_<behavior> (PASS)
- REQ-002: ✓ tests/<feature>_test.rs::test_<behavior> (XFAIL @EXT)
- REQ-003: ✗ [NO TESTS FOUND]

Metrics Consistency: OK (counts align)
Status: UNVERIFIED (REQ-002 has xfailed test; REQ-003 has no tests)
```

**code-critic says**:
```
FR Implementation Coverage:
- REQ-001: ✓ src/<module>.rs:<START_LINE>-<END_LINE>
- REQ-002: ✓ src/<module>.rs:<START_LINE>-<END_LINE> (MVP only)
- REQ-003: ✗ [NO IMPLEMENTATION FOUND]

Status: UNVERIFIED (REQ-003 missing implementation AND tests)
```

**self-reviewer says**:
```
Pytest Summary: <PYTEST_PASSED> passed, <PYTEST_XFAILED> xfailed, <PYTEST_XPASSED> xpassed, <PYTEST_FAILED> failed

FR Status Summary:
- REQ-001: FULLY_VERIFIED
- REQ-002: MVP_VERIFIED (xfailed extended tests)
- REQ-003: PARTIAL (no implementation, no tests)

Metrics Consistency: OK
Status: UNVERIFIED (REQ-003 incomplete)
```

**build_receipt.json**:
```json
{
  "metrics_binding": "pytest",
  "requirements": {
    "fr_status": {
      "REQ-001": "FULLY_VERIFIED",
      "REQ-002": "MVP_VERIFIED",
      "REQ-003": "PARTIAL"
    }
  },
  "tests": {
    "total": "<PYTEST_TOTAL>",
    "passed": "<PYTEST_PASSED>",
    "xfailed": "<PYTEST_XFAILED>",
    "metrics_consistency": "OK"
  },
  "status": "UNVERIFIED",
  "notes": [
    "REQ-001 fully verified",
    "REQ-002 MVP_VERIFIED with documented xfailed EXT tests",
    "REQ-003 PARTIAL—no implementation or tests found"
  ]
}
```

**gh-reporter says**:
```markdown
## Flow 3 Complete: Build

**Status**: UNVERIFIED

**Metrics** (from pytest):
- Tests: <PYTEST_PASSED> passed, <PYTEST_XFAILED> xfailed, <PYTEST_XPASSED> xpassed, <PYTEST_FAILED> failed
- Metrics Binding: pytest

**Functional Requirements**:
- REQ-001: FULLY_VERIFIED
- REQ-002: MVP_VERIFIED (extended tests xfailed)
- REQ-003: PARTIAL (no implementation)

### Key Finding
REQ-003 has no implementation or tests. Requires additional work before gate.
```

**Gate reads this and understands**:
- REQ-001 is ready
- REQ-002 is MVP-ready but incomplete
- REQ-003 is incomplete
- No ambiguity; metrics are bound to pytest; no rounding or reinterpretation

---

## Validation Checklist for Flow 3 Runs

Before considering Flow 3 complete, verify:

- [ ] test_critique.md includes exact pytest summary
- [ ] test_critique.md includes FR-to-test mapping
- [ ] code_critique.md includes FR-to-code mapping
- [ ] mutation_report.md reports exact score (killed/total)
- [ ] build_receipt.json has `metrics_binding: pytest` (or explicitly `hard_coded` if not)
- [ ] build_receipt.json `tests.metrics_consistency` is OK (not MISMATCH)
- [ ] FR statuses in receipt are FULLY_VERIFIED, MVP_VERIFIED, or PARTIAL (not invented)
- [ ] self_review.md includes verbatim pytest summary
- [ ] No artifact claims different test counts than pytest reports
- [ ] No FR marked FULLY_VERIFIED if any of its tests are xfailed

---

## Rationale

This approach trades **prose polish** for **auditability**. By binding critics and reporters to ground truth:

1. **Humans can verify claims**: Pytest summary is quoted; claims are checkable.
2. **No cooperative fudging**: Critics cannot gloss over xfails or missing tests.
3. **FR status is earned**: FULLY_VERIFIED means all tests pass; MVP_VERIFIED means extended tests are explicitly deferred.
4. **Metrics are immutable**: Reporters cannot recompute or "round" test counts.
5. **Gate has clear input**: Flow 4 reads a receipt that matches ground truth.

The cost: Some runs will report Status: UNVERIFIED or PARTIAL, which may look less polished. **That's the point.** Better to be honest about what's incomplete than to claim green and have Gate catch it later.

---

## Further Reading

- `swarm/flows/flow-build.md` — Flow 3 spec with FR status scheme and critic hard rules
- `.claude/agents/test-critic.md` — Updated with ground truth binding
- `.claude/agents/code-critic.md` — Updated with FR coverage checking
- `.claude/agents/mutator.md` — Updated with score binding
- `.claude/agents/self-reviewer.md` — Updated with auditing constraints
- `.claude/agents/gh-reporter.md` — Updated with summarizer discipline
