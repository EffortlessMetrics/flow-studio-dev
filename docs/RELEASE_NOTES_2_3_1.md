# v2.3.1 Release Notes

> **Release Date:** December 2025
>
> This release resolves all xfail tests from v2.3.0, implements missing validator features,
> and establishes a clean baseline with ~1750 passed tests and zero xfails/warnings.

---

## Highlights

- **Clean test baseline**: ~1750 passed, 41 skipped, 0 xfailed, 0 warnings
- **Validator reporting**: `--report json/markdown` flags fully implemented
- **Enhanced error messages**: Frontmatter errors include line numbers
- **Skill validation**: YAML content validation now detects malformed skill files
- **Documentation tooling**: Meta documentation generation and invariant checking

---

## Test Surface Summary

| Category | Count | Notes |
|----------|-------|-------|
| Passed | ~1750 | All core functionality |
| Skipped | 41 | Env-gated (SDK, observability, archived Flask) |
| XFailed | 0 | All resolved (was 3 in v2.3.0) |
| XPassed | 0 | N/A |
| Warnings | 0 | All filtered or registered |

### Performance Tests

Performance tests are **non-gating** because they are hardware-dependent. They are marked with `@pytest.mark.performance` and excluded from CI.

```bash
make test-performance    # Run performance benchmarks locally
```

### Baseline Tracking

Test counts are now tracked in `docs/DEFINITION_OF_DONE.md` as the authoritative baseline. Any regression in these counts must be justified and documented.

---

## Resolved Limitations from v2.3.0

The following xfail tests have been promoted to regular passing tests:

### 1. Validator Reporting (`--report json/markdown`)

**Status:** Implemented

The `--report` flag now supports both `json` and `markdown` output formats:

```bash
uv run swarm/tools/validate_swarm.py --report json    # Structured JSON output
uv run swarm/tools/validate_swarm.py --report markdown # Human-readable markdown
```

All 14 reporting tests in `test_reporting.py` now pass.

### 2. Frontmatter Error Line Numbers

**Status:** Implemented

Validation errors now include line numbers for precise error location:

```
ERROR: .claude/agents/context-loader.md:3: Invalid model 'claude-x'
```

This makes it easier to locate and fix frontmatter issues without manual scanning.

### 3. Skill YAML Content Validation

**Status:** Implemented

Skill files are now validated for:
- Valid YAML syntax
- Required fields presence
- Proper structure

Malformed skill YAML is properly detected and reported with actionable error messages.

---

## New Documentation Tooling

### Meta Documentation Generation

Generate documentation metadata and validation reports:

```bash
make gen-doc-meta    # Generate documentation metadata
```

This produces structured metadata about documentation coverage, cross-references, and freshness.

### Documentation Invariants Check

Verify documentation consistency:

```bash
make docs-check      # Check documentation invariants
```

This validates:
- Cross-reference integrity (no broken links)
- Version string consistency
- Required sections presence
- Example code validity

---

## Test Categories

Tests are now clearly categorized with pytest markers:

| Marker | Gating? | Description |
|--------|---------|-------------|
| `@pytest.mark.unit` | Yes | Fast, isolated tests |
| `@pytest.mark.integration` | Yes | Cross-component tests |
| `@pytest.mark.slow` | Yes | Tests taking >5s |
| `@pytest.mark.bdd` | Yes | Gherkin scenario tests |
| `@pytest.mark.performance` | **No** | Benchmark tests |

The `performance` marker was added to prevent hardware-dependent tests from causing CI flakiness.

---

## Skipped Tests Breakdown

The 41 skipped tests are intentionally gated by environment:

| Category | Count | Reason |
|----------|-------|--------|
| Flask backend tests | ~15 | Archived (FastAPI is primary) |
| Observability tests | ~12 | Requires external services |
| SDK smoke tests | ~8 | Requires ANTHROPIC_API_KEY |
| MCP UX spec tests | ~6 | Requires MCP server config |

These tests run when their required environment is available but are safely skipped in standard CI.

---

## Upgrade Notes

### From v2.3.0

This is a non-breaking point release:

1. Run `uv sync --extra dev` to update dependencies
2. Run `make selftest` to verify all 16 steps pass
3. Run `uv run pytest tests/` to confirm test baseline

### Validator Users

If you were using custom scripts with the validator:

- `--report json` is now available for machine-readable output
- `--report markdown` provides formatted reports for documentation
- Error messages now include line numbers (update any regex parsers)

---

## Definition of Done Update

The `docs/DEFINITION_OF_DONE.md` file now includes the official baseline:

```markdown
## Current Baseline (v2.3.1)

| Metric | Value |
|--------|-------|
| Tests Passed | ~1750 |
| Tests Skipped | 41 (env-gated) |
| Tests XFailed | 0 |
| Warnings | 0 |
```

This baseline should be maintained or improved with each release.

---

## See Also

- [RELEASE_NOTES_2_3_0.md](./RELEASE_NOTES_2_3_0.md): Previous release (v2.3.0)
- [DEFINITION_OF_DONE.md](./DEFINITION_OF_DONE.md): Baseline tracking
- [CHANGELOG.md](../CHANGELOG.md): Full changelog
- [GETTING_STARTED.md](./GETTING_STARTED.md): Quick start guide
- [VALIDATION_RULES.md](./VALIDATION_RULES.md): Validation rule details
