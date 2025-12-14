# Release Hygiene Scan Summary

**Scan Date**: 2024-12-12
**Commit Base**: HEAD (7e26081)

## Executive Summary

| Priority | Status | Items | Action |
|----------|--------|-------|--------|
| **P0** | CLEAN | 0 remaining | Commit pending changes |
| **P1** | 2 files | 2 | Quick fixes, include in release commit |
| **P2** | ~15 files | Optional | Sanitize or document as historical |

## What's Already Done (Uncommitted)

The working tree already has these fixes staged:

- `README.md` - Staging refs removed
- `docs/GETTING_STARTED.md` - Staging refs removed
- `docs/INDEX.md` - Staging refs removed
- `docs/drafts/` - Deleted (internal-only)
- `docs/HANDOVER_PR_42_COMPLETE.md` - Moved to archive

## Remaining Work

### Must Do (P1)

1. **docs/designs/CROSS_REPO_TEMPLATE_DESIGN.md** - Replace `/home/steven/...` paths
2. **packages/selftest-core/LICENSE** - Update copyright holder name

### Should Do (P2)

Sanitize `docs/archive/**` to remove personal paths, OR add archive README explaining they're historical.

### Not Issues

- `localhost:5000` references - These are documentation examples, not hardcoded defaults
- "staging" in observability docs - Refers to deployment environment, not repo
- ADR references to old names - ADRs are historical records

## Recommended Commit Sequence

```bash
# 1. Apply P1 fixes
sed -i 's|/home/steven/code/Swarm/demo-swarm-dev/||g' docs/designs/CROSS_REPO_TEMPLATE_DESIGN.md
sed -i 's/demo-swarm-dev contributors/Flow Studio contributors/' packages/selftest-core/LICENSE

# 2. Optional: Apply P2 fixes
find docs/archive -name "*.md" -exec sed -i 's|/home/steven/code/Swarm/demo-swarm-dev/|<repo-root>/|g' {} \;

# 3. Commit all
git add -A
git commit -m "docs: remove staging references, purge drafts, sanitize paths"

# 4. Tag promotion candidate
git tag -a v2.4.5 -m "Promotion candidate: release hygiene complete"
```

## Verification

After commit, run:

```bash
# Zero personal paths in non-archive docs
rg -n "/home/steven|/Users/|C:\\\\Code" --glob '!docs/archive/**' --glob '!.runs/**' .

# Zero staging repo refs in non-archive docs
rg -n "flow-studio-staging|demo-swarm-dev" --glob '!docs/archive/**' --glob '!.runs/**' --glob '!docs/adr/**' .
```
