# Release Alignment Summary

## Promotion Candidate

- **Tag**: `v2.4.5`
- **SHA**: `3c1ab25ef777cd0cb253d2ae21fb6f12f7c28733`
- **Created**: 2025-12-12

## What Changed

### Commit 1: `af527ec` - docs: sanitize internal path leaks and align attribution
- **P1 Fix**: Replaced `/home/steven/code/Swarm/demo-swarm-dev` with `<repo-root>` in `docs/designs/CROSS_REPO_TEMPLATE_DESIGN.md`
- **P1 Fix**: Updated LICENSE attribution to "Flow Studio contributors" in `packages/selftest-core/LICENSE`
- **P2 Fix**: Sanitized 7 archive docs to remove personal path leaks
- **Promotion Hygiene**: Removed staging/promotion narrative from:
  - `CLAUDE.md`
  - `README.md`
  - `docs/GETTING_STARTED.md`
  - `docs/INDEX.md`
- **Cleanup**: Moved `HANDOVER_PR_42_COMPLETE.md` to archive
- **Cleanup**: Deleted draft promotion docs (no longer needed)

### Commit 2: `3c1ab25` - docs(flowstudio): rebaseline OpenAPI schema and document new endpoints
- **OpenAPI Baseline**: Regenerated `docs/flowstudio-openapi.json` (37 endpoints)
- **API Docs**: Updated Key Endpoints table in `docs/FLOW_STUDIO_API.md`
- All changes additive; no breaking changes
- New endpoints documented:
  - `/api/profile`, `/api/profiles`, `/api/backends`
  - `/api/run`, `/api/runs/{run_id}/events` (UI-internal)
  - `/api/agents`, `/api/validation`, `/api/search`

## Confirmation Scans

### Front-door scan (clean)
```
rg "flow-studio-staging|staging2|demo-swarm-dev|/home/steven" README.md CLAUDE.md docs/GETTING_STARTED.md docs/INDEX.md
(no matches found)
```

### Archive scan (clean)
```
rg "/home/steven|/Users/|C:\\Code" docs/archive/
(no matches found)
```

## Gates Passed

| Gate | Status |
|------|--------|
| `make dev-check` | ✅ PASS |
| `make check-ui-drift` | ✅ PASS |
| `make validate-openapi-schema` | ✅ PASS |
| Selftest (16 steps) | ✅ 16/16 GREEN |

## Next Steps

1. **Push to staging remote**:
   ```bash
   git push origin main --tags
   ```

2. **Promote to prod repo** (from tag commit):
   ```bash
   gh repo create EffortlessMetrics/flow-studio --public
   git remote add prod git@github.com:EffortlessMetrics/flow-studio.git
   git push prod 'v2.4.5^{commit}:refs/heads/main'
   git push prod v2.4.5
   ```

3. **Stranger smoke test** (fresh clone):
   ```bash
   cd /tmp
   git clone https://github.com/EffortlessMetrics/flow-studio.git
   cd flow-studio
   uv sync --extra dev
   make demo-run
   make flow-studio
   make flowstudio-smoke-external
   ```

## Deferred Items

None. All release blockers resolved.
