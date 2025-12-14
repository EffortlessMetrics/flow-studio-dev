# OpenAPI Baseline Drift Check Report

**Date:** 2025-12-12
**Run ID:** release-align-20251213-034703

---

## Summary

**Overall Status:** ✓ PASS (No Drift Detected)

All checks completed successfully with no schema drift detected.

---

## Test Results

### 1. Schema Validation
**Status:** ✓ PASS

- Command: `make validate-openapi-schema`
- Exit Code: 0
- Tests Passed: 10/10
- Duration: 0.63s

**Tests:**
- ✓ OpenAPI version unchanged (3.1.0)
- ✓ Info version unchanged or increased (2.0.0)
- ✓ Required endpoints still documented
- ✓ Endpoint methods not removed
- ✓ Response definitions present
- ✓ Schema additions logged
- ✓ Baseline schema is valid JSON
- ✓ Baseline matches current structure
- ✓ Dump OpenAPI schema command works
- ✓ Live OpenAPI endpoint matches baseline structure

### 2. Drift Check
**Status:** ✓ PASS (No Drift)

- Command: `git status --porcelain docs/flowstudio-openapi.json`
- Result: No uncommitted changes detected
- Git Diff: Empty (no changes)

**Conclusion:** The baseline schema in `docs/flowstudio-openapi.json` is in sync with the current FastAPI application schema.

### 3. Schema Stability Tests
**Status:** ✓ PASS

- Command: `uv run pytest -q tests/test_flow_studio_schema_stability.py`
- Exit Code: 0
- Tests Passed: 10/10
- Duration: 0.59s

### 4. Deterministic Regeneration Test
**Status:** ✓ PASS (Deterministic)

- First dump: `openapi-first-dump.json`
- Second dump: `openapi-second-dump.json`
- Comparison: IDENTICAL

**Conclusion:** Schema generation is fully deterministic. Running `make dump-openapi-schema` multiple times produces byte-for-byte identical output.

---

## Schema Metadata

- **OpenAPI Version:** 3.1.0
- **API Version:** 2.0.0
- **Baseline File:** `docs/flowstudio-openapi.json`
- **File Size:** 88 KB
- **Number of Endpoints:** 37
- **Last Modified:** 2025-12-12 22:49

---

## Change Analysis

**Breaking Changes:** None
**Additive Changes:** None
**Removals:** None

The schema is stable with no drift from baseline.

---

## Artifacts Generated

### CI Logs
- `/home/steven/code/Swarm/flow-studio-staging2/.runs/release-align-20251213-034703/ci/dump-openapi-schema.log`
- `/home/steven/code/Swarm/flow-studio-staging2/.runs/release-align-20251213-034703/ci/validate-openapi-schema.log`
- `/home/steven/code/Swarm/flow-studio-staging2/.runs/release-align-20251213-034703/ci/schema-stability-tests.log`
- `/home/steven/code/Swarm/flow-studio-staging2/.runs/release-align-20251213-034703/ci/openapi-first-dump.json`
- `/home/steven/code/Swarm/flow-studio-staging2/.runs/release-align-20251213-034703/ci/openapi-second-dump.json`

### Diffs
- No diffs generated (no drift detected)

---

## Recommendations

1. **No Action Required:** Schema is stable and validated
2. **Baseline is Current:** No regeneration needed
3. **Tests Passing:** All 10 schema stability tests pass
4. **Determinism Verified:** Schema generation is reproducible

---

## Notes

- Schema generation completed successfully in both runs
- No git changes detected after regeneration
- All validation tests passed on first attempt
- Deterministic test confirms reliable build reproducibility
