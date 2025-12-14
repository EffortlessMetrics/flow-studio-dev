# P2 Optional: Archive Docs (Historical, Low Priority)

> **Policy Decision**: Archive docs can remain historical OR be sanitized. Both are valid.

## Files with Personal Paths in `docs/archive/`

| File | Line Count | Issue |
|------|------------|-------|
| `docs/archive/FLOW_STUDIO_SELFTEST_ENHANCEMENTS.md` | 2 | `/home/steven/code/Swarm/demo-swarm-dev/` |
| `docs/archive/TEST_CHANGES_ITERATION_2.md` | 1 | `/home/steven/code/Swarm/demo-swarm-dev/` |
| `docs/archive/FLOW3_CONTEXT_INDEX.md` | 12 | `/home/steven/code/Swarm/demo-swarm-dev/` |
| `docs/archive/WORKFLOW_CONTEXT_LOADER_OUTPUT.md` | 9 | `/home/steven/code/Swarm/demo-swarm-dev/` |
| `docs/archive/IMPLEMENTATION_NOTES.md` | 2 | `/home/steven/code/Swarm/demo-swarm-dev/` |
| `docs/archive/FLOW_STUDIO_GOVERNANCE_INDEX.md` | 1 | `/home/steven/code/Swarm/demo-swarm-dev/` |
| `docs/archive/GOVERNANCE_IMPLEMENTATION_GUIDE.md` | 2 | `/home/steven/code/Swarm/demo-swarm-dev/` |

## Files with Old Repo Identity in `docs/archive/`

| File | Issue |
|------|-------|
| `docs/archive/REPO_MAP.md` | Title: "demo-swarm-dev" |
| `docs/archive/ux_manifest.json` | `"name": "demo-swarm-dev Flow Studio UX"` |
| `docs/archive/RELEASE_NOTES/v2.1.1.md` | GitHub link to `demo-swarm-dev` |
| `docs/archive/DEMO_SWARM_COMPREHENSIVE_WALKTHROUGH.md` | Multiple `demo-swarm-dev` references |
| `docs/archive/TRACK_C_PLAN.md` | Scope mentions `demo-swarm-dev` |

## Option A: Sanitize (Recommended)

Run bulk replacement to make paths generic:

```bash
# Replace absolute paths with generic placeholder
find docs/archive -name "*.md" -exec sed -i 's|/home/steven/code/Swarm/demo-swarm-dev/|<repo-root>/|g' {} \;

# Or use relative paths
find docs/archive -name "*.md" -exec sed -i 's|/home/steven/code/Swarm/demo-swarm-dev/||g' {} \;
```

## Option B: Leave Historical with Notice

Add `docs/archive/README.md`:

```markdown
# Archive

Historical design documents and implementation notes.

> **Note**: These documents may contain machine-specific paths and old repo names
> from the development history. They are preserved for historical context.
```

## localhost:5000 References

**Verdict**: NOT an issue. These are documentation examples showing defaults.

- 150+ references across docs showing `http://localhost:5000`
- This is the documented default behavior
- Docs already mention `--port` flag for alternatives

**Optional Enhancement**: Add a note in GETTING_STARTED.md:

```markdown
> Flow Studio defaults to port 5000. Use `--port 5001` if 5000 is busy.
```

## ADR Reference

`docs/adr/00001-swarm-selftest-scope.md` line 9 mentions `demo-swarm-dev` in context. This is an architectural decision record - modifying it changes history. **Leave as-is**.
