# Handover - Test Harness, Governance & Docs (v2.3.1)

> **Scope:** This handover is for the person taking over the **test harness**, **selftest/governance**, **doc/metadata system**, and related Flow Studio + reporting surfaces in Flow Studio.
>
> The goal is that you can:
>
> * Run everything and know what "good" looks like.
> * Understand how tests, selftest, docs, and Flow Studio fit together.
> * Change things (add steps, agents, features) without silently breaking governance.
> * See what's left to push this to the next release.

---

## 1. Baseline (v2.3.1) - Where Things Stand

### 1.1 Test & selftest status

As of v2.3.1 (verified December 10, 2025):

* **Pytest suite**

  * **~1750** tests passed
  * **41** tests skipped (env/migration-gated, intentional)
  * **0** xfailed
  * **0** xpassed
  * **0** warnings in summary

* **Selftest harness**

  * **16** steps total:

    * 1 **KERNEL**
    * 13 **GOVERNANCE**
    * 2 **OPTIONAL**
  * All 16/16 steps pass in **STRICT** mode.

### 1.2 Core counts (computed, not hardcoded)

These are computed from real config and enforced by tests:

* **Agents**

  * 45 domain agents (files under `.claude/agents/*.md`)
  * 3 built-in infra agents (no `.claude/agents` files)
  * **48 total** agents

* **Skills**

  * 4 global skills:

    * `test-runner`
    * `auto-linter`
    * `policy-runner`
    * `heal_selftest`

These numbers are not manually duplicated in docs; they come from `swarm/meta.py` and are propagated into docs via generators and checked in tests.

---

## 2. Big Picture - What This Layer Is

At this level, the repo is:

> A **governed SDLC harness** with:
>
> * A **16-step selftest** with clear tiers and ACs, acting as a governance gate.
> * A large **pytest suite** with explicit marks (unit/integration/slow/bdd/performance).
> * A **validator** (`validate_swarm.py`) that checks the swarm and emits JSON/Markdown reports.
> * A **Flow Studio** (FastAPI + TS UI) that visualizes flows, runs, and wisdom summaries.
> * A **metadata + doc invariants** system that keeps code and docs in sync.
> * **CI wiring** that runs the right mix of tests and checks for merges.

You're inheriting all the plumbing that makes this stable and explainable.

---

## 3. File Map - Where the Important Pieces Live

This section is your "map" for when you have to debug or extend something.

### 3.1 Selftest system & AC matrix

**Config & narrative**

* `swarm/tools/selftest_config.py`
  Source of truth for selftest:

  * Step IDs and names.
  * `tier` (KERNEL / GOVERNANCE / OPTIONAL).
  * Execution waves (ordering and grouping).

* `swarm/SELFTEST_SYSTEM.md`
  Human-readable overview:

  * Tier explanation.
  * Step descriptions.
  * META section for step counts (generated from metadata).

* `docs/SELFTEST_AC_MATRIX.md`
  Acceptance criteria (ACs) mapped to selftest steps and surfaces.

**Tests that guard it**

* `tests/selftest_plan_test.py` - step count and plan shape.
* `tests/test_selftest_ac_bijection.py` - AC <-> step bijection correctness.
* `tests/test_ac_freshness_checker.py` - ensures AC lists in:

  * Gherkin,
  * AC matrix,
  * Selftest config
    stay aligned.

These tests **must stay green** when you add/remove/rename selftest steps or ACs.

---

### 3.2 Validation & reporting (`validate_swarm.py`)

**Script**

* `swarm/tools/validate_swarm.py`

Responsibilities:

* Validates:

  * Agent registry <-> config.
  * Flow definitions and references.
  * Skills.
  * RUN_BASE paths and consistency.

* Output modes:

  * **Standard** - human-readable log to stdout.
  * **Detailed JSON** - `--json` flag:

    * Structured dump used by other tools.
  * **Reporting**:

    * `--report json`:

      * Simplified, FR-style JSON report with:

        * `timestamp`, `status`, `checks`, `total_checks`, `passed`, `failed`, `errors`, `warnings`.
    * `--report markdown`:

      * Human-readable Markdown report with:

        * Title, timestamp, status.
        * Checklist of checks.
        * Error and warning sections.

**Helpers**

* `build_report_json(result: ValidationResult) -> Dict[str, Any]`
* `build_report_markdown(result: ValidationResult) -> str`

**Tests**

* `tests/test_reporting.py`:

  * Verifies JSON report format, fields, and determinism.
  * Verifies Markdown report structure and contents.
  * Covers both "healthy repo" and error cases.

All 33 tests in `test_reporting.py` pass as **regular** tests (no xfail).

---

### 3.3 YAML/frontmatter/skills parsing

**Parser**

* `swarm/validator/yaml.py`

Key behaviors:

* `SimpleYAMLParser.parse(..., strict=True)`:

  * Detects junk lines and malformed YAML.
  * Uses `_check_unclosed_quote()` to catch unclosed quotes.
  * Tracks line offsets so error messages can say:

    > `Malformed YAML on line 3: this is junk`

**Error model**

* `swarm/validator/errors.py`:

  * `ValidationError` holds:

    * `error_type`
    * `file_path`
    * `location`
    * `line_number`
    * `problem`
    * `fix_action` (optional)
  * `ValidationResult` aggregate.

These errors are what feed JSON and Markdown reports, and the line numbers are surfaced for frontmatter/skills.

**Frontmatter errors**

* Validator code (in `validate_swarm.py` / related) now:

  * Uses `SimpleYAMLParser` for frontmatter.
  * Extracts line numbers from YAML exceptions.
  * Creates `ValidationError` objects with `line_number` set.
  * Produces error messages that clearly mention the line and context.

**Skill YAML errors**

* Skill loader/validator:

  * Detects malformed YAML in `.claude/skills` (or relevant skill config).
  * Reports errors with file + line number and a clear message.

**Tests**

* `tests/test_frontmatter.py`:

  * `test_frontmatter_error_includes_line_number`:

    * Asserts that frontmatter errors include line numbers and are formatted as expected.

* `tests/test_skill.py`:

  * `test_skill_with_malformed_yaml`:

    * Asserts malformed YAML in skills is handled gracefully and reported with correct metadata.

These are now **baseline behavior** (no xfail markers).

---

### 3.4 Flow Studio & wisdom

**Backend API**

* `swarm/tools/flow_studio_fastapi.py`

Key endpoints:

* `/api/health`, `/api/flows`, `/api/graph/{flow_key}` - health and static graph info.
* `/api/runs` - paginated list of runs.
* `/api/runs/{run_id}/summary` - summary of a single run.
* `/api/runs/{run_id}/wisdom/summary` - JSON view of `wisdom_summary.json` for that run.

**UI**

* `swarm/tools/flow_studio_ui/` structure:

  * TypeScript:

    * `src/flow-studio-app.ts`

      * Bootstraps the app, manages global state and caches (including wisdom cache).
    * `src/runs_flows.ts`

      * Loads runs and flows, manages run selection and canvas fill, toggles the "empty state" overlay.
    * `src/run_detail_modal.ts`

      * Implements the run detail modal:

        * Shows event history, metadata, and wisdom panel.
        * Contains logic for "Load Wisdom" button (fetching from `/wisdom/summary`).
    * `src/domain.ts`

      * Types for Flow Studio:

        * Domain types (runs, flows, wisdom).
        * **FlowStudioUIID** union - the canonical list of `data-uiid` attributes.

  * HTML & CSS:

    * `fragments/*.html` - Flow Studio layout fragments compiled into `index.html`.
    * `css/flow-studio.base.css` - styling.

**Docs**

* `docs/FLOW_STUDIO.md` and `docs/FLOW_STUDIO_API.md`:

  * Describe:

    * Flow Studio entrypoint (`make flow-studio`).
    * Wisdom endpoints and UI, plus expected behaviors.

---

### 3.5 Metadata & doc invariants

**Metadata engine**

* `swarm/meta.py`

Core functions:

* `compute_meta()`:

  * Reads:

    * `swarm/tools/selftest_config.py` for steps and tiers.
    * `.claude/agents/*.md` for agent counts.
    * Central skills list for skills and counts.
  * Returns a dict with:

    ```python
    {
      "agents": {...},
      "selftest": {...},
      "skills": {...},
    }
    ```

* `get_meta()`:

  * Cached version of `compute_meta()` for use in other tools/tests.

Running:

```bash
make show-meta
# prints a neat "Swarm Metadata (computed from configuration)" summary
```

**Doc generator**

* `swarm/tools/generate_meta_docs.py`

Behavior:

* Looks for META markers in docs:

  ```md
  <!-- META:AGENT_COUNTS -->
  ...auto-generated block...
  <!-- /META:AGENT_COUNTS -->
  ```

* Rebuilds the content between markers using `compute_meta()`.

**Doc invariants checker**

* `swarm/tools/doc_invariants_check.py`

Behavior:

* Imports `compute_meta()` to get the current values.
* Scans a curated list of files (README, WHITEPAPER, AGENTS, SELFTEST_SYSTEM, release notes, etc.).
* Flags things like:

  * `"42 domain agents"` when meta says 45.
  * `"10-step selftest"` when meta says 16.

Usage:

```bash
uv run python swarm/tools/doc_invariants_check.py
```

**Tests**

* `tests/test_invariants.py`:

  * Asserts:

    * Agent counts match meta and filesystem.
    * Selftest step counts and tier breakdown match `selftest_config.py`.
    * Skills list and count match meta.

---

### 3.6 Pytest configuration & marks

**Pytest config**

In `pyproject.toml` -> `[tool.pytest.ini_options]`:

* `testpaths = ["tests"]`

* `python_files = ["test_*.py"]`

* `addopts = "-v --tb=short --color=yes"`

* `markers = [...]` includes:

  * `unit`
  * `integration`
  * `slow`
  * `bdd`
  * `performance`
  * AC-specific markers (e.g., `ac_selftest_*`)

* `filterwarnings` tuned to suppress gherkin deprecation noise in normal runs.

**Conftest**

* `tests/conftest.py`:

  * Contains core fixtures (temp repos, CLI wrappers, etc.).
  * Contains early `warnings.filterwarnings` to ensure gherkin deprecation warnings are suppressed at import time.
  * Contains `pytest_configure` hook with BDD marker registration.

---

## 4. CI & Makefile - What Runs Where

### 4.1 Makefile targets

From repo root:

**Validation & docs**

```bash
make dev-check           # Main developer health gate
make validate-swarm      # Swarm-specific validation
make docs-check          # Doc structure + doc invariants
make gen-doc-meta        # Regenerate META sections in docs
make gen-doc-meta-check  # Check that docs are up-to-date with meta
make show-meta           # Print metadata summary
```

**Tests**

```bash
make test-gating         # pytest -m "not performance"
make test-performance    # pytest -m "performance" --benchmark-enable
make test-ci-smoke       # Quick smoke tests for CI
make test-all            # Full pytest, dev use only
```

**Selftest**

```bash
make selftest            # Full 16-step harness
make selftest-fast       # KERNEL-only fast check
```

**Flow Studio**

```bash
make flow-studio         # Start visualization UI at http://localhost:5000
make ts-check            # Type-check Flow Studio TS
```

### 4.2 CI expectations

In `.github/workflows/ci.yml` (high level):

* **Gating jobs** should run:

  * `make dev-check`
  * `make test-gating`
  * `make docs-check`
  * `make gen-doc-meta-check`

* **Non-gating job** for performance (optional):

  * `make test-performance` with `continue-on-error: true`.

---

## 5. How to Work on This Safely

Here's how to avoid reintroducing drift or flaky behavior.

### 5.1 Before you push or merge

Run:

```bash
make dev-check
make docs-check
make gen-doc-meta-check
make test-gating
make validate-swarm
make ts-check
```

If you've touched perf-sensitive or runtime-heavy logic:

```bash
make test-performance
```

### 5.2 Common change recipes

**Change selftest steps**

1. Update `swarm/tools/selftest_config.py`.
2. Update `swarm/SELFTEST_SYSTEM.md` (then `make gen-doc-meta`).
3. Update `docs/SELFTEST_AC_MATRIX.md`.
4. Run:

   ```bash
   make gen-doc-meta
   make docs-check
   uv run pytest tests/test_invariants.py
   uv run pytest tests/test_ac_freshness_checker.py tests/test_selftest_ac_bijection.py
   make selftest
   ```

**Add agents**

1. Add `.claude/agents/<agent>.md`.
2. Update any relevant configs (flows, agent configs).
3. Run:

   ```bash
   make show-meta
   uv run pytest tests/test_invariants.py
   make gen-doc-meta && make gen-doc-meta-check
   make dev-check
   ```

**Change error formats for YAML/frontmatter/skills**

1. Update `swarm/validator/yaml.py`, `swarm/validator/errors.py`, `validate_swarm.py`.
2. Update tests:

   * `tests/test_yaml_parser.py`
   * `tests/test_frontmatter.py`
   * `tests/test_skill.py`
   * (`tests/test_reporting.py` if report fields change)
3. Run:

   ```bash
   make test-gating
   make dev-check
   ```

**Touch docs involving counts**

* Don't hand-edit counts in:

  * `swarm/AGENTS.md`
  * `swarm/SELFTEST_SYSTEM.md`
  * Any section guarded by META markers.
* Instead:

  ```bash
  make gen-doc-meta
  make gen-doc-meta-check
  make docs-check
  ```

---

## 6. Known Limitations

### 6.1 Gherkin deprecation warning with `-W error`

When running pytest with `-W error` (strict warning mode), the gherkin library's deprecation warning about `maxsplit` will cause a collection error:

```
ERROR tests/test_selftest_bdd.py - DeprecationWarning: 'maxsplit' is passed as positional argument
```

**This is expected behavior.** The `-W error` command-line flag overrides config-file-level filter warnings. In normal pytest runs (without `-W error`), the warning is properly suppressed via `pyproject.toml` and `conftest.py`.

**Workaround:** Don't use `-W error` mode, or explicitly add ignore patterns on the command line:

```bash
pytest -W "ignore:'maxsplit' is passed as positional argument:DeprecationWarning" ...
```

---

## 7. Future Work - Taking It "Over the Line"

The harness is stable and clean. Future work is mostly **capabilities**, not fixups:

### 7.1 Engine profiles & resume

* Implement `EngineProfile` for different runtime configurations
* Wire `stepwise_resume.py` for resuming partially completed runs

### 7.2 Flow Studio wisdom UX

* Add TS tests for wisdom helper functions
* Improve discoverability of wisdom (filters, tooltips, list views)

### 7.3 Meta/doc generation - expansion

* Add META markers to more docs (README, WHITEPAPER)
* Expand doc-invariants coverage

### 7.4 Performance SLO (optional)

* Stabilize performance tests with environment-aware thresholds
* Document SLOs and interpretation

---

## 8. TL;DR for the Next Maintainer

* The current state is **clean**: ~1750 passed, 41 skipped, 0 xfailed, 0 warnings; selftest 16/16; doc/meta invariants enforced.
* Counts (agents, selftest steps, skills) are **computed**, not hand-coded, and tests enforce them.
* Docs are partially **generated** from metadata and **linted** via `doc_invariants_check.py`.
* Reporting (`--report json/markdown`), frontmatter line numbers, and skill YAML validation are **implemented and tested**.
* Performance tests are clearly marked and **non-gating**; use `make test-performance` when you care.

If you keep those invariants and workflows intact, you can extend the system without sliding back into inconsistent docs, flaky tests, or hidden governance drift.

---

## 9. Verification Commands (Quick Reference)

```bash
# Full test suite
uv run pytest tests/ -q --tb=no
# Expected: ~1750 passed, 41 skipped

# Swarm validation
make validate-swarm
# Expected: "Swarm validation PASSED."

# Show metadata
make show-meta
# Expected: 48 agents (45 domain + 3 built-in), 16 selftest steps, 4 skills

# Selftest
make selftest
# Expected: 16/16 steps pass
```
