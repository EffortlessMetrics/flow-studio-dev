# AC Matrix Freshness Checker

## Purpose

The AC freshness checker validates that acceptance criteria (ACs) are consistently defined across three sources:

1. **Gherkin feature files** (`features/selftest.feature`) — test scenarios with `@AC-SELFTEST-*` tags
2. **AC Matrix documentation** (`docs/SELFTEST_AC_MATRIX.md`) — canonical AC documentation with `### AC-SELFTEST-*` headers
3. **Selftest configuration** (`swarm/tools/selftest_config.py`) — implementation tracking via `ac_ids` lists

## Why This Matters

**Problem**: As the selftest system evolves, it's easy for ACs to drift:
- A new test scenario is added but not documented in the matrix
- Documentation describes an AC that's not actually enforced in config
- Config references an AC that's no longer documented

**Solution**: This tool enforces bidirectional consistency:
- All Gherkin tags → Matrix (ensures test scenarios are documented)
- All Matrix headers → Config (ensures documented ACs are tracked)
- All Config ACs → Matrix (prevents orphaned/undocumented ACs)

## Usage

### Basic Check (CI/Local)

```bash
make check-ac-freshness
# Output:
# ✓ AC Matrix Freshness Check
#   6 ACs OK (all layers aligned)
#   Gherkin: 6, Matrix: 6, Config: 6
```

Exit code: `0` if all checks pass, `1` if any check fails.

### Verbose Mode (Debugging)

```bash
make check-ac-freshness-verbose
# Output includes per-AC status breakdown:
#   ✓ AC-SELFTEST-KERNEL-FAST        [OK                  ] (GHERKIN, MATRIX, CONFIG)
#   ✓ AC-SELFTEST-INTROSPECTABLE     [OK                  ] (GHERKIN, MATRIX, CONFIG)
#   ...
```

### JSON Mode (Tooling Integration)

```bash
uv run swarm/tools/check_selftest_ac_freshness.py --json
# Output: JSON with status, checks, counts, and optional per-AC details
```

Example JSON output:
```json
{
  "status": "PASS",
  "total_acs": 6,
  "checks": {
    "gherkin_to_matrix": {
      "pass": true,
      "missing": []
    },
    "matrix_to_config": {
      "pass": true,
      "missing": []
    },
    "config_to_matrix": {
      "pass": true,
      "orphaned": []
    }
  },
  "counts": {
    "gherkin": 6,
    "matrix": 6,
    "config": 6
  }
}
```

### JSON + Verbose (Full Details)

```bash
uv run swarm/tools/check_selftest_ac_freshness.py --json --verbose
# Includes "acs" array with per-AC status, sources, and alignment
```

## Common Failure Scenarios

### Scenario 1: New Gherkin Tag, Missing in Matrix

**Symptom**:
```
✗ AC Matrix Freshness Check FAILED

  ✗ Gherkin → Matrix: 1 missing
    - AC-SELFTEST-NEW-FEATURE
  Fix: Add these ACs as '### <AC-ID>' headers in docs/SELFTEST_AC_MATRIX.md
```

**Resolution**:
1. Edit `docs/SELFTEST_AC_MATRIX.md`
2. Add a new section:
   ```markdown
   ### AC-SELFTEST-NEW-FEATURE

   **Status**: ⚠️ In Progress

   | Field | Value |
   |-------|-------|
   | **Description** | ... |
   | **Implemented In Steps** | ... |
   | **Tier** | GOVERNANCE |
   ```
3. Re-run checker

### Scenario 2: Matrix AC, Missing in Config

**Symptom**:
```
✗ Matrix → Config: 1 missing
  - AC-SELFTEST-DOCUMENTED-FEATURE
Fix: Add these ACs to appropriate step 'ac_ids' lists in swarm/tools/selftest_config.py
```

**Resolution**:
1. Edit `swarm/tools/selftest_config.py`
2. Find the appropriate `SelfTestStep` definition
3. Add the AC to its `ac_ids` list:
   ```python
   SelfTestStep(
       id="some-step",
       ...
       ac_ids=["AC-SELFTEST-KERNEL-FAST", "AC-SELFTEST-DOCUMENTED-FEATURE"],
   ),
   ```
4. Re-run checker

### Scenario 3: Orphaned AC in Config

**Symptom**:
```
✗ Config → Matrix: 1 orphaned
  - AC-SELFTEST-OBSOLETE-FEATURE
Fix: Add documentation for these ACs in docs/SELFTEST_AC_MATRIX.md or remove from swarm/tools/selftest_config.py
```

**Resolution**:
Either:
- **Option A**: Document it in the Matrix (if it was accidentally undocumented)
- **Option B**: Remove from Config `ac_ids` list (if it's truly obsolete)

## Integration Points

### CI Pipeline

The checker is designed for CI integration:

```yaml
# .github/workflows/swarm-validate.yml
- name: Check AC Matrix Freshness
  run: make check-ac-freshness
```

Exit code `1` will fail the CI job.

### Pre-commit Hook (Optional)

Add to `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: ac-freshness
      name: AC Matrix Freshness
      entry: uv run swarm/tools/check_selftest_ac_freshness.py
      language: system
      pass_filenames: false
      files: ^(features/selftest\.feature|docs/SELFTEST_AC_MATRIX\.md|swarm/tools/selftest_config\.py)$
```

### Flow Studio Integration

The JSON output can power AC status overlays in Flow Studio:

```bash
curl http://localhost:5000/api/selftest/plan | jq '.steps[].ac_ids'
# Cross-reference with freshness check JSON to highlight drift
```

## Testing

The checker includes comprehensive tests:

```bash
uv run pytest tests/test_ac_freshness_checker.py -v
```

Tests verify:
- Script exists and is executable
- Exit codes (0 on pass, 1 on fail)
- JSON schema correctness
- Verbose output includes AC details
- Bidirectional consistency checks

## File Paths

The checker uses these hardcoded paths:

- **Gherkin**: `features/selftest.feature`
- **Matrix**: `docs/SELFTEST_AC_MATRIX.md`
- **Config**: `swarm/tools/selftest_config.py`

Pattern matching:
- Gherkin: `@(AC-SELFTEST-[A-Z-]+)`
- Matrix: `###\s+(AC-SELFTEST-[A-Z-]+)`
- Config: `"(AC-SELFTEST-[A-Z-]+)"`

## Design Philosophy

**No magic, explicit checks**:
- Uses regex patterns identical to test suite (`test_selftest_ac_bijection.py`)
- Clear error messages with actionable fix suggestions
- Idempotent: safe to run multiple times
- No side effects: read-only, never modifies files

**Fail fast, fix forward**:
- Exit code 1 on any check failure (blocks CI)
- Human-readable plain text output by default
- Machine-readable JSON for tooling integration

**Composable with existing tools**:
- Complements `test_selftest_ac_bijection.py` (pytest-based unit tests)
- Integrates with `make dev-check` validation workflow
- Can be invoked standalone or as library module

## Maintenance

When adding a new AC:

1. **Write the Gherkin scenario** with `@AC-SELFTEST-*` tag
2. **Document in Matrix** with `### AC-SELFTEST-*` header
3. **Add to Config** in appropriate step's `ac_ids` list
4. **Verify alignment**: `make check-ac-freshness`

When removing an AC:

1. **Remove from Gherkin** (delete scenario or tag)
2. **Mark as obsolete in Matrix** (or remove section)
3. **Remove from Config** (delete from `ac_ids` list)
4. **Verify alignment**: `make check-ac-freshness`

## Related Tools

- **Test bijection**: `tests/test_selftest_ac_bijection.py` — pytest-based unit tests
- **Selftest runner**: `swarm/tools/selftest.py` — execution engine
- **Selftest plan**: `swarm/tools/selftest.py --plan` — introspection
- **AC Matrix**: `docs/SELFTEST_AC_MATRIX.md` — canonical documentation

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All checks passed (AC matrix is fresh) |
| 1 | At least one check failed (drift detected) |

## See Also

- **SELFTEST_SYSTEM.md** — Full selftest design and philosophy
- **SELFTEST_AC_MATRIX.md** — Canonical AC documentation
- **selftest_config.py** — Step definitions with AC tracking
