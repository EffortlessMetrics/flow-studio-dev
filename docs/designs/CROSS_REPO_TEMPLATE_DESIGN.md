# ADR: Cross-Repo Selftest Template (P5.2)

## Status

Proposed

## Context

The selftest system in this repository provides a layered, degradable governance framework that validates swarm health without treating every failure as "everything is broken." This system has proven valuable:

- Three-tier model (KERNEL/GOVERNANCE/OPTIONAL) distinguishes critical from nice-to-have
- Degraded mode allows progress while tracking technical debt
- Doctor diagnostic separates environment from code issues
- JSON reporting enables tooling integration
- Override system provides auditable escape hatches

However, the current implementation is tightly coupled to this repository's specific governance checks (agent validation, flow graph invariants, BDD scenarios). Other projects could benefit from the same **framework** without inheriting the swarm-specific **checks**.

### Problem Statement

1. **Tight coupling**: `selftest.py` imports `selftest_config.py` which hardcodes swarm-specific steps
2. **No abstraction layer**: Step definitions mix framework concerns (tiers, dependencies) with implementation concerns (specific commands)
3. **Manual replication**: Teams wanting similar governance must copy-paste and heavily modify
4. **Maintenance burden**: Each fork diverges; improvements don't flow back
5. **Missing bootstrapping**: No "selftest init" experience for new repos

### Goal

Package selftest as a **reusable template** that can be bootstrapped into any repository, providing:

- The three-tier governance model (KERNEL/GOVERNANCE/OPTIONAL)
- Degraded mode with degradation logging
- Doctor diagnostic for environment vs code separation
- JSON reporting and status API
- Override escape hatch with audit logging
- Customizable step definitions per-repo

## Decision

We choose **Option A: Copier Template with Python Package Core** as the distribution mechanism.

This hybrid approach provides:
1. A **Python package** (`selftest-governance`) containing the framework (runner, reporter, doctor)
2. A **Copier template** for bootstrapping step definitions, Makefile targets, and CI workflows

## Alternatives Considered

### Option A: Copier Template with Python Package Core (Selected)

**Summary**: Framework logic lives in a pip-installable package; Copier generates the repo-specific configuration layer.

```bash
# Install the framework
pip install selftest-governance

# Bootstrap step definitions and CI in your repo
copier copy gh:EffortlessMetrics/selftest-template .
```

**Strengths**:
- Clean separation: Framework (package) vs Configuration (template)
- Framework updates via `pip install --upgrade`
- Template updates via `copier update`
- Step definitions remain local (version controlled with the repo)
- No runtime dependency on external services

**Weaknesses**:
- Two distribution mechanisms to maintain
- Users must understand both pip and copier
- Initial setup has two steps

**Rejected because**: This is the **selected** option.

### Option B: Pure Python Package

**Summary**: Everything in a pip package with an `init` subcommand.

```bash
pip install selftest-governance
selftest init  # Generates config files
selftest run
```

**Strengths**:
- Single distribution mechanism
- Familiar to Python developers
- CLI-first experience

**Weaknesses**:
- `init` generates static files; updates are manual
- No copier-style templating (prompts, conditionals)
- CI workflows must be generated separately
- Harder to customize for non-Python repos

**Rejected because**: Less flexible templating; worse for polyglot repos.

### Option C: GitHub Template Repository

**Summary**: A GitHub template repo that users fork/clone.

```
Use this template -> creates new repo with selftest
```

**Strengths**:
- Zero tooling required
- Works for any language
- GitHub-native experience

**Weaknesses**:
- One-time copy; no update mechanism
- Customization means editing generated files
- Divergence between template and adopters
- Not suitable for adding selftest to existing repos

**Rejected because**: No update mechanism; poor for existing repos.

### Option D: Monorepo Submodule

**Summary**: Selftest lives in a git submodule.

```bash
git submodule add gh:EffortlessMetrics/selftest .selftest
```

**Strengths**:
- Updates via `git submodule update`
- Framework and config co-evolve
- Works for any language

**Weaknesses**:
- Git submodules are notoriously painful
- Nested repos confuse tooling
- CI setup more complex
- Not Pythonic

**Rejected because**: Submodule UX is poor; not aligned with Python ecosystem.

## Consequences

### Positive

- **Reusability**: Any repo can adopt selftest governance with a clear bootstrap path
- **Maintainability**: Framework updates flow through the package; template updates flow through copier
- **Flexibility**: Step definitions are fully customizable per-repo
- **Consistency**: Core concepts (tiers, degradation, doctor) are shared; only checks differ
- **Versioning**: Semantic versioning for both package and template
- **Polyglot support**: Works for Python, Rust, Node, Go, etc.

### Negative

- **Two systems**: Users must understand both pip and copier
- **Initial complexity**: Setup has two steps instead of one
- **Maintenance overhead**: Must maintain package, template, and documentation
- **Testing burden**: Must test package, template generation, and integration

### Risks

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| Copier is not widely known | Medium | Document installation; provide shell script wrapper |
| Package/template version mismatch | Medium | Version compatibility matrix in README; CI checks |
| Step schema breaks between versions | Low | Semantic versioning; migration guides |
| Users skip copier and copy files manually | Medium | Document the "right way"; provide migration script |

---

## Detailed Design

### 1. Package Structure

The `selftest-governance` Python package contains the core framework:

```
selftest-governance/
├── pyproject.toml
├── src/
│   └── selftest/
│       ├── __init__.py
│       ├── runner.py           # SelfTestRunner (tier-aware execution)
│       ├── config.py           # SelfTestStep, SelfTestTier, config loading
│       ├── doctor.py           # Diagnostic harness vs service separation
│       ├── reporter.py         # JSON report generation (v1, v2 formats)
│       ├── degradation.py      # Degradation logging (JSONL)
│       ├── override.py         # Override management with audit
│       ├── status.py           # StatusProvider for /platform/status
│       ├── metrics.py          # Optional Prometheus/StatsD integration
│       └── cli.py              # Click-based CLI (selftest run, doctor, etc.)
├── tests/
│   ├── test_runner.py
│   ├── test_config.py
│   ├── test_doctor.py
│   └── ...
└── README.md
```

### 2. Template Structure

The Copier template generates repo-specific configuration:

```
selftest-template/
├── copier.yaml                  # Template configuration
├── {{ project_name }}/
│   ├── selftest_config.py       # Step definitions (customizable)
│   ├── Makefile.selftest        # Makefile targets (included by main Makefile)
│   └── .github/
│       └── workflows/
│           └── selftest.yml     # CI workflow (platform-specific)
├── hooks/
│   └── post_gen_project.py      # Post-generation setup
└── tests/
    └── test_template.py         # Template generation tests
```

### 3. Configuration File Format

The generated `selftest_config.py` uses a declarative format:

```python
"""
selftest_config.py - Project-specific selftest step definitions

This file is generated by `copier copy gh:EffortlessMetrics/selftest-template .`
and customized for your project. Edit freely; this is your source of truth.

To update the selftest framework (not this file), run:
  pip install --upgrade selftest-governance
"""

from selftest import Step, Tier, Severity, Category

# Define your selftest steps
STEPS = [
    # KERNEL tier: Must always pass. Block on failure.
    Step(
        id="lint",
        name="Lint Check",
        description="Static analysis and code style",
        tier=Tier.KERNEL,
        severity=Severity.CRITICAL,
        category=Category.CORRECTNESS,
        command=["ruff check src/"],  # Customize for your project
    ),
    Step(
        id="typecheck",
        name="Type Check",
        description="Static type checking",
        tier=Tier.KERNEL,
        severity=Severity.CRITICAL,
        category=Category.CORRECTNESS,
        command=["mypy src/"],
    ),
    Step(
        id="test",
        name="Unit Tests",
        description="Fast unit test suite",
        tier=Tier.KERNEL,
        severity=Severity.CRITICAL,
        category=Category.CORRECTNESS,
        command=["pytest tests/unit -q"],
    ),

    # GOVERNANCE tier: Should pass. Allowed to fail in degraded mode.
    Step(
        id="integration",
        name="Integration Tests",
        description="Integration test suite",
        tier=Tier.GOVERNANCE,
        severity=Severity.WARNING,
        category=Category.CORRECTNESS,
        command=["pytest tests/integration -q"],
        allow_fail_in_degraded=True,
    ),
    Step(
        id="security",
        name="Security Scan",
        description="Dependency vulnerability scan",
        tier=Tier.GOVERNANCE,
        severity=Severity.WARNING,
        category=Category.SECURITY,
        command=["pip-audit"],
        allow_fail_in_degraded=True,
    ),

    # OPTIONAL tier: Nice-to-have. Informational only.
    Step(
        id="coverage",
        name="Coverage Report",
        description="Code coverage threshold check",
        tier=Tier.OPTIONAL,
        severity=Severity.INFO,
        category=Category.GOVERNANCE,
        command=["pytest --cov=src --cov-fail-under=80"],
    ),
]
```

### 4. Template Questions (copier.yaml)

The template prompts users for customization:

```yaml
_min_copier_version: "9.0.0"

project_name:
  type: str
  help: Your project name (used in generated files)
  default: "{{ _folder_name }}"

governance_tier:
  type: str
  help: How much governance do you want?
  choices:
    minimal: "Just KERNEL checks (lint, test)"
    standard: "KERNEL + GOVERNANCE (integration, security)"
    full: "All tiers including OPTIONAL"
  default: standard

language:
  type: str
  help: Primary language (determines default steps)
  choices:
    python: "Python (ruff, pytest, mypy)"
    rust: "Rust (cargo fmt, clippy, test)"
    node: "Node.js (eslint, jest, tsc)"
    go: "Go (gofmt, go vet, go test)"
    generic: "Generic (bring your own commands)"
  default: python

observability:
  type: str
  help: Observability backend for metrics
  choices:
    none: "No metrics (just JSON logs)"
    jsonl: "JSON Lines logging (default)"
    prometheus: "Prometheus push gateway"
    datadog: "Datadog StatsD"
  default: jsonl

ci_platform:
  type: str
  help: CI platform for workflow generation
  choices:
    github-actions: "GitHub Actions"
    gitlab-ci: "GitLab CI"
    none: "No CI workflow"
  default: github-actions

include_doctor:
  type: bool
  help: Include selftest doctor diagnostic?
  default: true

include_overrides:
  type: bool
  help: Include override escape hatch?
  default: true
```

### 5. CLI Interface

The `selftest-governance` package provides a CLI:

```bash
# Run selftest
selftest run                     # Full suite (strict mode)
selftest run --degraded          # Degraded mode
selftest run --kernel-only       # KERNEL tier only
selftest run --step lint         # Single step
selftest run --until integration # Steps up to and including

# Inspect selftest
selftest plan                    # Show execution plan
selftest plan --json             # Plan as JSON
selftest list                    # List all steps

# Diagnostics
selftest doctor                  # Harness vs service diagnosis
selftest status                  # Current health status

# Degradation management
selftest degradations            # Show degradation log
selftest degradations --since 24h

# Override management
selftest override create STEP --reason "..." --approver "..."
selftest override list
selftest override revoke STEP

# Report generation
selftest report                  # Generate JSON report
selftest report --format v2      # V2 format with severity breakdown

# Template management (requires copier)
selftest init                    # Bootstrap selftest in current repo
selftest upgrade                 # Update template files
```

### 6. Language-Specific Templates

The template includes presets for common languages:

**Python preset**:
```python
KERNEL_STEPS = [
    Step(id="lint", command=["ruff check ."]),
    Step(id="typecheck", command=["mypy src/"]),
    Step(id="test", command=["pytest tests/unit -q"]),
]
```

**Rust preset**:
```python
KERNEL_STEPS = [
    Step(id="fmt", command=["cargo fmt --check"]),
    Step(id="clippy", command=["cargo clippy --all-targets --all-features -- -D warnings"]),
    Step(id="test", command=["cargo test --workspace"]),
]
```

**Node.js preset**:
```python
KERNEL_STEPS = [
    Step(id="lint", command=["npm run lint"]),
    Step(id="typecheck", command=["npm run typecheck"]),
    Step(id="test", command=["npm test"]),
]
```

**Go preset**:
```python
KERNEL_STEPS = [
    Step(id="fmt", command=["gofmt -l . | grep -q . && exit 1 || exit 0"]),
    Step(id="vet", command=["go vet ./..."]),
    Step(id="test", command=["go test ./..."]),
]
```

### 7. CI Workflow Templates

**GitHub Actions** (`.github/workflows/selftest.yml`):
```yaml
name: Selftest

on:
  push:
    branches: [main]
  pull_request:

jobs:
  selftest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install selftest-governance
        run: pip install selftest-governance

      - name: Install project dependencies
        run: pip install -e ".[dev]"

      - name: Run kernel smoke
        run: selftest run --kernel-only

      - name: Run full selftest
        run: selftest run

      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: selftest-report
          path: selftest_report.json
```

**GitLab CI** (`.gitlab-ci.yml`):
```yaml
selftest:
  stage: test
  image: python:3.11
  script:
    - pip install selftest-governance
    - pip install -e ".[dev]"
    - selftest run --kernel-only
    - selftest run
  artifacts:
    reports:
      junit: selftest_report.xml
    paths:
      - selftest_report.json
```

### 8. Makefile Integration

The template generates `Makefile.selftest` which can be included:

```makefile
# Makefile.selftest - Generated by selftest-template
# Include this in your main Makefile: include Makefile.selftest

.PHONY: selftest selftest-degraded kernel-smoke selftest-doctor selftest-plan

selftest:
	selftest run

selftest-degraded:
	selftest run --degraded

kernel-smoke:
	selftest run --kernel-only

selftest-doctor:
	selftest doctor

selftest-plan:
	selftest plan

override-create:
	@test -n "$(STEP)" || (echo "Usage: make override-create STEP=<step> REASON=<reason> APPROVER=<name>"; exit 1)
	selftest override create $(STEP) --reason "$(REASON)" --approver "$(APPROVER)"

override-list:
	selftest override list

override-revoke:
	@test -n "$(STEP)" || (echo "Usage: make override-revoke STEP=<step>"; exit 1)
	selftest override revoke $(STEP)
```

### 9. Versioning Strategy

**Package versioning** (semver):
- Major: Breaking changes to step schema or CLI
- Minor: New features (e.g., new tier, new reporter)
- Patch: Bug fixes, documentation

**Template versioning** (semver):
- Major: Breaking changes to generated files
- Minor: New language presets, CI platforms
- Patch: Template fixes

**Compatibility matrix**:
```
selftest-governance 1.x -> selftest-template 1.x
selftest-governance 2.x -> selftest-template 2.x (migration guide provided)
```

### 10. Migration Path

For repos already using the demo-swarm selftest:

```bash
# Step 1: Install the package
pip install selftest-governance

# Step 2: Run migration tool
selftest migrate --from demo-swarm

# This will:
# - Analyze existing selftest_config.py
# - Generate compatible step definitions
# - Preserve custom commands and dependencies
# - Update imports to use selftest package
```

---

## Implementation Plan

### Phase 1: Extract Core Framework (2 weeks)

**Goal**: Create `selftest-governance` package from existing code.

**Tasks**:
1. Create new repository `selftest-governance`
2. Extract and refactor from demo-swarm:
   - `selftest.py` -> `selftest/runner.py`
   - `selftest_config.py` -> `selftest/config.py` (schema only, no steps)
   - `selftest_doctor.py` -> `selftest/doctor.py`
   - `selftest_report_schema.py` -> `selftest/reporter.py`
   - `override_manager.py` -> `selftest/override.py`
3. Add Click-based CLI (`selftest/cli.py`)
4. Write comprehensive tests
5. Publish to PyPI

**Deliverables**:
- `selftest-governance` package on PyPI
- API documentation
- README with quick start

### Phase 2: Copier Template (1 week)

**Goal**: Create bootstrapping template.

**Tasks**:
1. Create `selftest-template` repository
2. Implement `copier.yaml` with questions
3. Create language-specific presets (Python, Rust, Node, Go)
4. Create CI workflow templates (GitHub Actions, GitLab CI)
5. Create `Makefile.selftest` template
6. Write template tests (test generation for each preset)
7. Document customization options

**Deliverables**:
- `selftest-template` repository
- Copier template with 4 language presets
- CI workflows for 2 platforms

### Phase 3: CLI Polish (1 week)

**Goal**: Complete the CLI experience.

**Tasks**:
1. Implement `selftest init` (wraps copier)
2. Implement `selftest upgrade` (wraps copier update)
3. Implement `selftest migrate --from demo-swarm`
4. Add shell completions (bash, zsh, fish)
5. Add progress bars and colored output
6. Write CLI documentation

**Deliverables**:
- Complete CLI with init/upgrade/migrate
- Shell completions
- CLI reference documentation

### Phase 4: Documentation and Examples (1 week)

**Goal**: Enable self-service adoption.

**Tasks**:
1. Write comprehensive README for package
2. Write getting started guide
3. Create example repos for each language
4. Write customization guide (adding steps, tiers, reporters)
5. Write troubleshooting FAQ
6. Create video walkthrough (optional)

**Deliverables**:
- Documentation site (GitHub Pages or Read the Docs)
- 4 example repositories
- FAQ and troubleshooting guide

---

## What Gets Templated vs. What Stays Repo-Specific

### Templated (in `selftest-template`)

| Component | Description | Customization |
|-----------|-------------|---------------|
| `selftest_config.py` | Step definitions | Full customization expected |
| `Makefile.selftest` | Make targets | Optional extension |
| CI workflow | Platform-specific | Platform selection |
| `.selftest/` directory | Working directory | Path configurable |

### Framework (in `selftest-governance` package)

| Component | Description | Customization |
|-----------|-------------|---------------|
| `SelfTestRunner` | Tier-aware execution | N/A (use via API) |
| `SelfTestStep` | Step dataclass | Extend with custom fields |
| `SelfTestDoctor` | Environment diagnosis | Override checks |
| `SelfTestReporter` | JSON report generation | Custom report formats |
| `OverrideManager` | Audit-logged escape hatch | Custom expiration policies |
| `DegradationLogger` | JSONL logging | Custom backends |
| `StatusProvider` | Health status API | Custom integrations |

### Repo-Specific (user maintains)

| Component | Description | Source |
|-----------|-------------|--------|
| Step commands | The actual `cargo test`, `pytest`, etc. | User |
| Dependencies | What's needed to run commands | User |
| Custom tiers | Beyond KERNEL/GOVERNANCE/OPTIONAL | User |
| Custom categories | Beyond security/performance/correctness | User |
| Integration hooks | Pre/post step hooks | User |

---

## Success Criteria

### Adoption Metrics

- 10 repos using `selftest-governance` within 6 months
- 3+ contributions from external users
- Zero critical bugs in framework

### User Experience

- Bootstrap time < 5 minutes for new repo
- `selftest init` works on first try for documented languages
- Documentation answers 90% of questions

### Maintenance

- Framework release cadence: monthly
- Template update cadence: quarterly
- Breaking changes: at most 1 per year with migration guide

---

## Open Questions

1. **Naming**: Is `selftest-governance` the right package name? Alternatives:
   - `governance-selftest`
   - `dev-selftest`
   - `layered-selftest`

2. **Tier extensibility**: Should users be able to define custom tiers beyond KERNEL/GOVERNANCE/OPTIONAL?

3. **Step dependencies**: Should the template support step dependencies out of the box, or is that an advanced feature?

4. **Plugin system**: Should there be a plugin architecture for custom reporters, loggers, etc.?

5. **Configuration format**: Python file vs. YAML/TOML for step definitions? Python gives more flexibility but YAML is more portable.

---

## References

- `swarm/tools/selftest.py` - Current implementation
- `swarm/tools/selftest_config.py` - Step definitions
- `swarm/SELFTEST_SYSTEM.md` - System documentation
- [Copier documentation](https://copier.readthedocs.io/)
- [Click CLI documentation](https://click.palletsprojects.com/)
