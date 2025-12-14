# hello-selftest Specification

**Version**: 1.0
**Target**: Minimal adoption specimen for selftest-core
**Audience**: Teams with a single Python service wanting CI guardrails without the full swarm

---

## Purpose

Create a **boring, minimal Python repository** that demonstrates:

1. Adding `selftest-core` to an existing service
2. Defining KERNEL/GOVERNANCE tiers appropriate for a small team
3. Running selftest locally and in CI
4. Achieving "zero to green CI in ≤10 commands" from clone

**Non-goals**:
- Flow Studio (no visualization)
- Agents or orchestration (no swarm complexity)
- Templates or scaffolding (direct dependency on selftest-core)
- Multi-service repos (single service only)

This is the **simplest possible adoption path**: one service, one selftest config, one CI file.

---

## Constraints

| Constraint | Value | Rationale |
|------------|-------|-----------|
| Total LOC | 300-600 | Fits in a single review session |
| Python version | 3.10+ | Match Flow Studio baseline |
| Dependencies | Minimal | Only selftest-core + dev tools |
| Selftest tiers | KERNEL + GOVERNANCE | Demonstrate two-tier model |
| CI provider | GitHub Actions | Most common, simplest setup |

---

## Repository Structure

```text
hello-selftest/
├── pyproject.toml              # UV-managed project with selftest-core
├── selftest.yaml               # Minimal 3-5 step configuration
├── src/
│   └── app.py                  # Tiny application logic (~30-50 LOC)
├── tests/
│   └── test_app.py             # Basic tests (~50-80 LOC)
├── .github/
│   └── workflows/
│       └── selftest.yml        # CI configuration (~20-30 lines)
├── README.md                   # Quick start guide
└── LICENSE                     # MIT or Apache 2.0
```

**Total**: ~400-500 LOC

---

## File Specifications

### 1. `pyproject.toml`

```toml
[project]
name = "hello-selftest"
version = "0.1.0"
description = "Minimal Python service demonstrating selftest-core adoption"
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
dev = [
    "selftest-core>=0.1.0",
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
]

[tool.uv]
dev-dependencies = [
    "selftest-core>=0.1.0",
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
ignore = []

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--verbose --tb=short"

[tool.coverage.run]
source = ["src"]
omit = ["tests/*"]

[tool.coverage.report]
fail_under = 80
precision = 2
show_missing = true
```

**Key points**:
- No runtime dependencies (pure Python example)
- Dev dependencies include selftest-core + standard tools
- Ruff configured for basic linting
- Coverage threshold at 80% (governance requirement)

---

### 2. `selftest.yaml`

```yaml
# Minimal selftest configuration for a single Python service
# See: https://github.com/EffortlessMetrics/flow-studio

tiers:
  kernel:
    description: "Must-pass checks for every commit (local dev loop)"
    blocking: true
  governance:
    description: "Policy checks that block merges (CI gate)"
    blocking: true
  optional:
    description: "Nice-to-have checks (non-blocking warnings)"
    blocking: false

steps:
  # KERNEL tier: fast checks for local dev
  - id: lint
    tier: kernel
    command: uv run ruff check src tests
    description: "Static analysis with ruff"
    timeout: 30

  - id: test
    tier: kernel
    command: uv run pytest tests -v
    description: "Run unit tests"
    timeout: 60

  # GOVERNANCE tier: policy enforcement for CI
  - id: coverage
    tier: governance
    command: uv run pytest tests --cov=src --cov-report=term-missing --cov-fail-under=80
    description: "Enforce 80% code coverage"
    timeout: 60

  # OPTIONAL tier: non-blocking nice-to-haves
  - id: format-check
    tier: optional
    command: uv run ruff format --check src tests
    description: "Check code formatting (non-blocking)"
    timeout: 30
```

**Key design decisions**:
- **3 tiers**: KERNEL (fast), GOVERNANCE (policy), OPTIONAL (nice-to-have)
- **4 steps total**: lint, test, coverage, format-check
- **Explicit timeouts**: prevent hanging CI
- **Coverage as governance**: demonstrates policy enforcement vs dev speed

---

### 3. `src/app.py`

```python
"""
hello-selftest: Minimal Python service demonstrating selftest-core adoption.

This module provides basic arithmetic and string utilities to demonstrate
test coverage and CI integration.
"""


def add(a: int, b: int) -> int:
    """Add two integers.

    Args:
        a: First integer
        b: Second integer

    Returns:
        Sum of a and b

    Examples:
        >>> add(2, 3)
        5
    """
    return a + b


def subtract(a: int, b: int) -> int:
    """Subtract b from a.

    Args:
        a: First integer
        b: Second integer

    Returns:
        Difference a - b

    Examples:
        >>> subtract(5, 3)
        2
    """
    return a - b


def greet(name: str) -> str:
    """Generate a greeting message.

    Args:
        name: Name to greet

    Returns:
        Greeting string

    Examples:
        >>> greet("World")
        'Hello, World!'
    """
    return f"Hello, {name}!"


def main() -> None:
    """Entry point for the application."""
    print(greet("selftest"))
    print(f"2 + 3 = {add(2, 3)}")
    print(f"5 - 3 = {subtract(5, 3)}")


if __name__ == "__main__":
    main()
```

**Key points**:
- ~50 LOC of actual logic
- Docstrings for coverage demonstration
- Simple, testable functions
- Entry point for manual verification

---

### 4. `tests/test_app.py`

```python
"""Tests for hello-selftest application logic."""

import pytest

from src.app import add, greet, subtract


class TestArithmetic:
    """Test arithmetic operations."""

    def test_add_positive_numbers(self):
        """Test addition of positive integers."""
        assert add(2, 3) == 5
        assert add(10, 20) == 30

    def test_add_negative_numbers(self):
        """Test addition with negative integers."""
        assert add(-5, -3) == -8
        assert add(-10, 5) == -5

    def test_add_zero(self):
        """Test addition with zero."""
        assert add(0, 0) == 0
        assert add(5, 0) == 5
        assert add(0, 5) == 5

    def test_subtract_positive_numbers(self):
        """Test subtraction of positive integers."""
        assert subtract(5, 3) == 2
        assert subtract(10, 5) == 5

    def test_subtract_negative_numbers(self):
        """Test subtraction with negative integers."""
        assert subtract(-5, -3) == -2
        assert subtract(5, -3) == 8

    def test_subtract_zero(self):
        """Test subtraction with zero."""
        assert subtract(5, 0) == 5
        assert subtract(0, 5) == -5


class TestGreeting:
    """Test greeting functionality."""

    def test_greet_simple_name(self):
        """Test greeting with a simple name."""
        assert greet("World") == "Hello, World!"
        assert greet("Alice") == "Hello, Alice!"

    def test_greet_empty_string(self):
        """Test greeting with empty string."""
        assert greet("") == "Hello, !"

    def test_greet_special_characters(self):
        """Test greeting with special characters."""
        assert greet("世界") == "Hello, 世界!"
        assert greet("123") == "Hello, 123!"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_large_numbers(self):
        """Test arithmetic with large integers."""
        assert add(1_000_000, 2_000_000) == 3_000_000
        assert subtract(1_000_000, 2_000_000) == -1_000_000

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            (0, 0, 0),
            (1, 1, 2),
            (-1, 1, 0),
            (100, -100, 0),
        ],
    )
    def test_add_parametrized(self, a, b, expected):
        """Test addition with parametrized inputs."""
        assert add(a, b) == expected
```

**Key points**:
- ~80 LOC covering core functionality
- Achieves >80% coverage (governance requirement)
- Demonstrates pytest patterns (classes, parametrize)
- Edge cases and boundary testing

---

### 5. `.github/workflows/selftest.yml`

```yaml
name: Selftest CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  selftest-kernel:
    name: Selftest (KERNEL tier)
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up UV
        uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Run selftest (KERNEL only)
        run: uv run selftest run --kernel-only

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-results-kernel
          path: |
            .selftest/
            htmlcov/

  selftest-full:
    name: Selftest (Full)
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up UV
        uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Run selftest (KERNEL + GOVERNANCE)
        run: uv run selftest run --until governance

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-results-full
          path: |
            .selftest/
            htmlcov/
            coverage.xml
```

**Key design decisions**:
- **Two jobs**: Separate KERNEL (fast feedback) from full governance
- **Artifact upload**: Preserve test results for debugging
- **UV caching**: Speed up CI runs
- **Both push and PR triggers**: Catch issues early

---

### 6. `README.md`

```markdown
# hello-selftest

Minimal Python service demonstrating [selftest-core](https://github.com/EffortlessMetrics/flow-studio/tree/main/packages/selftest-core) adoption.

**Goal**: Zero to green CI in ≤10 commands.

## Quick Start

### Prerequisites

- Python 3.10+
- [UV](https://docs.astral.sh/uv/) installed

### Setup

```bash
# Clone and enter directory
git clone <this-repo>
cd hello-selftest

# Install dependencies
uv sync --extra dev

# Run application
uv run python -m src.app

# Run tests
uv run pytest tests -v

# Run selftest (KERNEL only, fast)
uv run selftest run --kernel-only

# Run full selftest (KERNEL + GOVERNANCE)
uv run selftest run --until governance
```

**Expected output**: All checks pass in < 5 seconds (KERNEL) or < 15 seconds (full).

## What This Demonstrates

### Selftest Tiers

| Tier | Steps | Purpose | Blocking |
|------|-------|---------|----------|
| **KERNEL** | `lint`, `test` | Fast dev loop checks | Yes |
| **GOVERNANCE** | `coverage` | Policy enforcement (80% coverage) | Yes |
| **OPTIONAL** | `format-check` | Nice-to-have (non-blocking) | No |

### Local Workflow

```bash
# During development (fast feedback)
uv run selftest run --kernel-only

# Before pushing (full validation)
uv run selftest run --until governance
```

### CI Integration

See `.github/workflows/selftest.yml`:
- **KERNEL job**: Runs on every push/PR for fast feedback
- **Full job**: Runs KERNEL + GOVERNANCE for merge gate

## Project Structure

```text
hello-selftest/
├── pyproject.toml       # Dependencies and tool config
├── selftest.yaml        # Selftest tier configuration
├── src/
│   └── app.py           # Application logic
├── tests/
│   └── test_app.py      # Unit tests (>80% coverage)
└── .github/workflows/
    └── selftest.yml     # CI configuration
```

## Adopting This Pattern

### For Your Service

1. Copy `selftest.yaml` to your repo
2. Add `selftest-core` to `pyproject.toml`:
   ```toml
   [tool.uv]
   dev-dependencies = ["selftest-core>=0.1.0"]
   ```
3. Adjust step commands to match your project structure
4. Copy `.github/workflows/selftest.yml` and customize job names

### Customizing Tiers

Edit `selftest.yaml`:
- **Add steps**: Append to `steps:` array
- **Change thresholds**: Modify `--cov-fail-under` value
- **Add tiers**: Define new tier in `tiers:` section

Example: Add type checking to GOVERNANCE:
```yaml
- id: typecheck
  tier: governance
  command: uv run mypy src
  description: "Type checking with mypy"
  timeout: 60
```

## Why Selftest?

Traditional CI is a binary "pass/fail" gate. Selftest introduces **tiers**:

- **KERNEL**: Must-pass for every commit (< 5s)
- **GOVERNANCE**: Policy checks for merge (< 30s)
- **OPTIONAL**: Nice-to-have (non-blocking)

This separates "dev loop speed" from "policy enforcement" explicitly.

## Resources

- [selftest-core package](https://github.com/EffortlessMetrics/flow-studio/tree/main/packages/selftest-core)
- [Flow Studio](https://github.com/EffortlessMetrics/flow-studio) (full specimen with flows + agents)
- [Adoption Playbook](https://github.com/EffortlessMetrics/flow-studio/blob/main/docs/ADOPTION_PLAYBOOK.md)
- [Selftest Templates](https://github.com/EffortlessMetrics/flow-studio/blob/main/docs/SELFTEST_TEMPLATES.md)

## License

MIT
```

**Key sections**:
- **Quick Start**: Get to green in 6 commands
- **What This Demonstrates**: Explicit tier explanation
- **Adopting This Pattern**: Copy-paste guidance
- **Why Selftest**: Value proposition vs traditional CI

---

## CLI Acceptance Criteria

From a fresh clone to green CI:

```bash
# 1. Clone repository
git clone <repo-url> hello-selftest
cd hello-selftest

# 2. Install dependencies
uv sync --extra dev

# 3. Run KERNEL checks (local dev loop)
uv run selftest run --kernel-only

# 4. Run full selftest (KERNEL + GOVERNANCE)
uv run selftest run --until governance

# 5. Verify application works
uv run python -m src.app

# 6. Push and verify CI green
git remote add origin <your-fork>
git push -u origin main
# Check GitHub Actions → both jobs green
```

**Total commands**: 6 (clone, sync, kernel, full, verify, push)
**Time to first green**: < 2 minutes
**Time to CI green**: < 3 minutes

---

## Test Coverage Requirements

| File | Coverage Target | Rationale |
|------|----------------|-----------|
| `src/app.py` | ≥90% | Simple logic, easy to test |
| Overall | ≥80% | Governance requirement |

**Enforcement**: `pytest --cov=src --cov-fail-under=80` in GOVERNANCE tier

---

## CI Job Matrix

| Job | Tiers | Trigger | Artifact |
|-----|-------|---------|----------|
| `selftest-kernel` | KERNEL only | Push, PR | Test results |
| `selftest-full` | KERNEL + GOVERNANCE | Push, PR | Test results + coverage |

**Why two jobs?**
- KERNEL job gives fast feedback (~30s)
- Full job provides complete validation (~60s)
- Developers see "kernel failing" vs "governance failing" immediately

---

## Integration with Flow Studio

### Documentation Updates

Once hello-selftest is live, update these files in Flow Studio:

1. **docs/SELFTEST_TEMPLATES.md**
   - Add decision table with hello-selftest row
   - Link to hello-selftest repo

2. **README.md**
   - Update "Already convinced?" box to point to decision table
   - Add hello-selftest as primary adoption path for small services

3. **docs/GETTING_STARTED.md**
   - Add "Quick Start for Small Services" section at top
   - Link to hello-selftest before full swarm walkthrough

4. **docs/ADOPTION_PLAYBOOK.md**
   - Archetype 1 ("Single team, single service"): default to hello-selftest
   - Archetype 2 ("Platform team"): mention hello-selftest as building block

### Link Format

```markdown
| Scenario | Template | Link |
|----------|----------|------|
| Small Python service, CI-only | `hello-selftest` | [hello-selftest](https://github.com/EffortlessMetrics/hello-selftest) |
```

---

## Future Enhancements (Out of Scope)

These are explicitly **not** in v1.0:

- **Multiple services**: Keep it single-service
- **Flow Studio**: No visualization layer
- **Agents**: No orchestration
- **Templates**: Direct dependency, not scaffolding
- **Docker**: Keep dependencies minimal
- **Database migrations**: Pure Python logic only
- **API server**: No web framework overhead

If teams want these, they graduate to `selftest-minimal` template or full Flow Studio.

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Time to first green (local) | < 2 min | From clone to `selftest run --kernel-only` passing |
| Time to CI green | < 3 min | From push to GitHub Actions green check |
| Commands to green | ≤ 10 | Count from "Prerequisites met" to "CI green" |
| Lines of code | 300-600 | Total excluding comments/blank lines |
| Cognitive load | Low | Junior dev can reproduce without asking questions |

---

## Implementation Checklist

### Phase 1: Core Implementation
- [ ] Create repository: `hello-selftest`
- [ ] Add `pyproject.toml` with selftest-core dependency
- [ ] Implement `src/app.py` (~50 LOC)
- [ ] Write `tests/test_app.py` (~80 LOC)
- [ ] Create `selftest.yaml` (4 steps: lint, test, coverage, format)
- [ ] Add `.github/workflows/selftest.yml` (two jobs)
- [ ] Write `README.md` with quick start and adoption guide
- [ ] Verify locally: `uv run selftest run --until governance` → green

### Phase 2: CI Validation
- [ ] Push to GitHub
- [ ] Verify both CI jobs green
- [ ] Test artifact uploads work
- [ ] Verify timing: KERNEL < 60s, Full < 120s

### Phase 3: Documentation Integration
- [ ] Update `flow-studio/docs/SELFTEST_TEMPLATES.md` with decision table
- [ ] Update `flow-studio/README.md` "Already convinced?" box
- [ ] Add section to `flow-studio/docs/GETTING_STARTED.md`
- [ ] Update `flow-studio/docs/ADOPTION_PLAYBOOK.md` archetypes
- [ ] Cross-link from `selftest-core` package README

### Phase 4: Validation
- [ ] Fresh clone test: Verify ≤10 commands to green
- [ ] Junior dev test: Have someone unfamiliar try it
- [ ] CI timing test: Confirm < 3 min to green
- [ ] Coverage test: Verify 80% threshold enforced
- [ ] Break test: Introduce failure, verify clear error message

---

## Questions for Implementer

Before starting implementation, resolve:

1. **Repository location**: Under EffortlessMetrics org or personal account?
2. **Naming**: `hello-selftest` or `selftest-hello` or other?
3. **License**: MIT, Apache 2.0, or match Flow Studio?
4. **Initial maintainers**: Who can merge PRs to this repo?
5. **Release cadence**: Pin to selftest-core version or track latest?

---

## Appendix: Command Reference

### Local Development

```bash
# Fast feedback (KERNEL only)
uv run selftest run --kernel-only

# Full validation (KERNEL + GOVERNANCE)
uv run selftest run --until governance

# Show selftest plan
uv run selftest run --plan

# Run specific step
uv run selftest run --step lint
uv run selftest run --step coverage

# Check coverage report
uv run pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### CI Debugging

```bash
# Reproduce CI locally
uv sync --extra dev
uv run selftest run --until governance

# Check specific failure
uv run selftest run --step coverage --verbose

# Generate coverage XML for CI
uv run pytest --cov=src --cov-report=xml
```

### Maintenance

```bash
# Update dependencies
uv lock --upgrade

# Run ruff auto-fixes
uv run ruff check --fix src tests
uv run ruff format src tests

# Bump version
# Edit pyproject.toml: version = "0.2.0"
git tag v0.2.0
git push origin v0.2.0
```

---

**End of Specification**

**Next Steps**:
1. Review and approve this spec
2. Create `hello-selftest` repository
3. Implement per checklist
4. Update Flow Studio docs once live
