# P0 Fix List: Front Door (Must Fix Before Release)

> **Target**: Zero hits in README, GETTING_STARTED, INDEX, FLOW_STUDIO, EVALUATION_CHECKLIST, SUPPORT, CONTRIBUTING

## Status: CLEAN

All P0 front-door docs have been cleaned in the current working tree:

| File | Status | Issue |
|------|--------|-------|
| `README.md` | Modified | Staging refs removed |
| `docs/GETTING_STARTED.md` | Modified | Staging refs removed |
| `docs/INDEX.md` | Modified | Staging refs removed |
| `docs/drafts/PUBLISH.md` | Deleted | Internal-only doc |
| `docs/drafts/flow-studio-public-README.md` | Deleted | Draft superseded |
| `docs/HANDOVER_PR_42_COMPLETE.md` | Moved to archive | Internal handover |

## Verification Commands

```bash
# Confirm zero personal path leaks in front door
rg -n "/home/steven|/Users/|C:\\\\Code" README.md docs/GETTING_STARTED.md docs/INDEX.md docs/FLOW_STUDIO.md docs/EVALUATION_CHECKLIST.md SUPPORT.md CONTRIBUTING.md

# Confirm zero staging repo refs in front door
rg -n "flow-studio-staging|demo-swarm-dev" README.md docs/GETTING_STARTED.md docs/INDEX.md docs/FLOW_STUDIO.md docs/EVALUATION_CHECKLIST.md SUPPORT.md CONTRIBUTING.md
```

## Action Required

**Commit the pending changes** to finalize P0 cleanup:

```bash
git add -A
git commit -m "docs: remove staging references and purge drafts"
```
