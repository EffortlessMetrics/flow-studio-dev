# Maintaining Flow Studio

This guide documents how to maintain and evolve Flow Studio, the web-based flow visualization tool built on FastAPI + Pydantic + Cytoscape.

**Target audience**: maintainers making changes to Flow Studio's schema, API, or UI.

> **New owner?** Start with [`docs/FLOW_STUDIO_UX_HANDOVER.md`](./FLOW_STUDIO_UX_HANDOVER.md) for context, guarantees, and next steps.

**Related docs**:
- `FLOW_STUDIO.md` — user guide (what it is, how to use it)
- `swarm/FLOW_STUDIO.md` — technical deep dive (architecture, contract)
- `FASTAPI_MIGRATION_COMPLETE.md` — migration history (v2.2.0)

---

## Architecture Overview

Flow Studio consists of three layers:

1. **Data Schema** (`swarm/flowstudio/schema.py`)
   - Pydantic models defining flows, steps, agents, skills
   - Source of truth for API contracts
   - Validated via tests in `tests/test_flow_studio_schema_stability.py`

2. **FastAPI Backend** (`swarm/tools/flow_studio_fastapi.py`)
   - REST API serving `/api/flows`, `/api/health`, `/api/selftest/plan`
   - OpenAPI schema auto-generated from Pydantic models
   - Prometheus metrics on ephemeral ports (configurable via `PROMETHEUS_PORT`)

3. **HTML UI** (`swarm/tools/flow_studio_ui/`)
   - Extracted static HTML with embedded JavaScript
   - Cytoscape.js for graph rendering
   - Served at `/` by FastAPI

**Contract baseline**: `docs/flowstudio-openapi.json` (committed)

---

## Adding or Changing Fields

When you add a field to `FlowStep`, `FlowAgent`, or other Pydantic models:

### 1. Update the Schema

Edit `swarm/flowstudio/schema.py`:

```python
class FlowStep(BaseModel):
    id: str
    role: str
    agents: list[str]
    # NEW FIELD:
    priority: Optional[int] = None
```

### 2. Update FastAPI Routes (if needed)

If the new field requires new API behavior, update `swarm/tools/flow_studio_fastapi.py`:

```python
@app.get("/api/flows")
def get_flows():
    flows = parse_flows_with_agents()
    # Add any new logic here if needed
    return flows
```

### 3. Regenerate OpenAPI Schema

```bash
make dump-openapi-schema
```

This writes `docs/flowstudio-openapi.json` with the updated schema.

### 4. Validate Schema Stability

```bash
make validate-openapi-schema
```

This runs tests in `tests/test_flow_studio_schema_stability.py` to ensure:
- Required endpoints still exist
- Endpoint methods not removed
- No breaking changes to response structure

**Note**: Adding fields is non-breaking. Removing required fields or endpoints is breaking.

### 5. Update UI (if needed)

If the new field should be displayed in the graph or detail panel:

1. Edit `swarm/tools/flow_studio_ui/index.html`
2. Find the relevant rendering code (Cytoscape or detail panel)
3. Add display logic for the new field

**Testing**: After changes, run:
```bash
make flow-studio
# Open http://localhost:5000 and verify new field appears
```

### 6. Run Full Validation

```bash
make dev-check
```

This ensures:
- Schema parses correctly
- FastAPI app starts without errors
- OpenAPI schema is consistent
- All tests pass

---

## Breaking vs Non-Breaking Changes

**Non-breaking changes** (safe):
- Adding optional fields to Pydantic models
- Adding new endpoints
- Adding new HTTP methods to existing endpoints
- Expanding response data (adding fields to responses)

**Breaking changes** (dangerous):
- Removing endpoints
- Removing HTTP methods from endpoints
- Removing required fields from responses
- Changing field types in incompatible ways
- Renaming endpoints or methods

**How to handle breaking changes**:
1. Increment major version (e.g., v3.0.0)
2. Document in CHANGELOG.md under "Breaking Changes"
3. Update `FASTAPI_MIGRATION_COMPLETE.md` with migration guide
4. Consider deprecation path (serve both old and new for one release)

---

## OpenAPI Schema Management

The schema baseline (`docs/flowstudio-openapi.json`) is the **contract** for Flow Studio's API.

### Makefile Targets

```bash
make dump-openapi-schema           # Export current schema from FastAPI app
make validate-openapi-schema       # Run stability tests
make check-openapi-breaking-changes # Detect removals
make diff-openapi-schema           # Show git diff of schema
```

### When to Update the Baseline

**Always update** after:
- Adding new endpoints
- Adding new fields to existing responses
- Changing FastAPI route signatures

**Never update blindly**:
- Review `git diff docs/flowstudio-openapi.json` carefully
- Ensure changes are intentional
- Run `make validate-openapi-schema` first

### Schema Stability Tests

Located in `tests/test_flow_studio_schema_stability.py`:

```python
class TestOpenAPISchemaStability:
    def test_required_endpoints_still_documented(self):
        # Ensures /api/flows, /api/health, etc. exist

    def test_endpoint_methods_not_removed(self):
        # Ensures GET methods not removed from endpoints

    def test_no_response_schema_regression(self):
        # Ensures response structures unchanged
```

These tests fail if you accidentally remove endpoints or methods.

---

## Flask Quarantine

As of v2.2.0, Flask is **completely removed** from the runtime.

**Quarantine tests** (`tests/test_no_flask_in_runtime.py`) ensure:
- No `from flask import` statements in active code
- No `Flask(__name__)` instantiations
- No `@app.route` decorators using Flask
- Legacy Flask backend archived in `swarm/tools/_archive/`

**If you need to touch Flask code**:
1. Do NOT re-introduce Flask imports in active code
2. Only edit files under `swarm/tools/_archive/` (legacy reference)
3. Run `make release-verify` to ensure quarantine holds

---

## Release Verification

Before tagging a release:

```bash
make release-verify
```

This runs:
1. `make dev-check` — full swarm validation + selftest
2. `make validate-openapi-schema` — API contract stability
3. `pytest tests/test_no_flask_in_runtime.py` — Flask quarantine

**Exit code 0** means safe to tag. **Exit code 1** means fix issues first.

---

## Common Maintenance Tasks

### Task: Add a new API endpoint

1. Add route to `swarm/tools/flow_studio_fastapi.py`:
   ```python
   @app.get("/api/agents")
   def get_agents():
       return {"agents": [...]}
   ```

2. Update schema if needed (`swarm/flowstudio/schema.py`)

3. Regenerate and validate:
   ```bash
   make dump-openapi-schema
   make validate-openapi-schema
   ```

4. Test manually:
   ```bash
   make flow-studio
   curl http://localhost:5000/api/agents
   ```

5. Add tests in `tests/test_flow_studio_fastapi_comprehensive.py`

### Task: Change an existing endpoint's response

1. Update Pydantic model in `swarm/flowstudio/schema.py`

2. Update route in `swarm/tools/flow_studio_fastapi.py`

3. Regenerate schema:
   ```bash
   make dump-openapi-schema
   ```

4. Check diff:
   ```bash
   make diff-openapi-schema
   ```

5. If breaking: increment major version and document

6. If non-breaking: commit schema update

### Task: Update UI to show new data

1. Edit `swarm/tools/flow_studio_ui/index.html`

2. Find rendering code (likely in `renderFlowGraph()` or `showDetails()`)

3. Add display logic for new field

4. Test locally:
   ```bash
   make flow-studio
   ```

5. No schema update needed (UI changes don't affect API)

### Task: Fix Prometheus port conflicts

If Flow Studio fails to start due to port conflicts:

```bash
PROMETHEUS_PORT=0 make flow-studio
```

Port `0` means "use ephemeral port" (OS assigns random available port).

**Permanent fix**: Set in environment or shell profile:
```bash
export PROMETHEUS_PORT=0
```

---

## Troubleshooting

### "Port 5000 already in use"

**Cause**: Another process is using port 5000.

**Fix**:
```bash
# Find and kill the process
lsof -ti:5000 | xargs kill -9

# Or use a different port
FLOW_STUDIO_PORT=5001 make flow-studio
```

### "Prometheus port already in use"

**Cause**: Previous Flow Studio instance left Prometheus running.

**Fix**:
```bash
# Use ephemeral port
PROMETHEUS_PORT=0 make flow-studio
```

### "OpenAPI schema validation failed"

**Cause**: Schema changes broke stability tests.

**Fix**:
1. Check `git diff docs/flowstudio-openapi.json`
2. If intentional: update tests in `tests/test_flow_studio_schema_stability.py`
3. If accidental: revert schema changes

```bash
make diff-openapi-schema
# Review changes, then:
git checkout docs/flowstudio-openapi.json  # if accidental
# OR update tests if intentional
```

### "Flask quarantine tests failed"

**Cause**: Flask import detected in active code.

**Fix**:
1. Check `tests/test_no_flask_in_runtime.py` output
2. Remove Flask imports from active code
3. Move Flask code to `swarm/tools/_archive/` if needed

```bash
pytest tests/test_no_flask_in_runtime.py -v
# Fix reported files
```

---

## Testing Strategy

**Smoke tests** (`tests/test_flow_studio_fastapi_smoke.py`):
- Fast sanity checks (~5s)
- Run on every commit
- `/api/health` reachability, basic structure

**Comprehensive tests** (`tests/test_flow_studio_fastapi_comprehensive.py`):
- Full API contract validation (~5-10min)
- Run before releases
- OpenAPI schema validation, CORS, error handling

**Governance tests** (`tests/test_flow_studio_governance.py`):
- 12 policy tests enforcing Flask quarantine
- Run in CI and `make release-verify`

**When to add tests**:
- New endpoint → add to comprehensive suite
- New field → add schema stability test
- New behavior → add smoke test if critical

---

## Reference Commands

```bash
# Development
make flow-studio                    # Start Flow Studio locally
make dump-openapi-schema            # Export OpenAPI schema
make diff-openapi-schema            # Show schema changes

# Validation
make validate-openapi-schema        # Run stability tests
make check-openapi-breaking-changes # Detect endpoint removals
make dev-check                      # Full swarm validation

# Release
make release-verify                 # Complete release gate check

# Testing
pytest tests/test_flow_studio_fastapi_smoke.py -v  # Fast smoke tests
pytest tests/test_flow_studio_fastapi_comprehensive.py -v  # Full tests
pytest tests/test_no_flask_in_runtime.py -v  # Flask quarantine
```

---

## Version History

- **v2.2.0** (2025-12-02): FastAPI-only backend; Flask quarantined; OpenAPI baseline established
- **v2.1.x**: Dual Flask/FastAPI backends (deprecated)
- **v2.0.x**: Original Flask-only implementation (archived)

For migration history, see `FASTAPI_MIGRATION_COMPLETE.md`.

---

## Questions?

If you're unsure whether a change is breaking or how to update the schema:

1. Check `git diff docs/flowstudio-openapi.json` after `make dump-openapi-schema`
2. Run `make validate-openapi-schema` to see what breaks
3. Consult `tests/test_flow_studio_schema_stability.py` for examples
4. If still unclear: ask in team channel or GitHub discussions

**Golden rule**: If `make release-verify` passes, you're safe to merge.
