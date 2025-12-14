# P1 Fix List: Regular Docs (Should Fix)

> **Target**: Non-archive docs should not contain personal paths or repo identity leaks

## Issues Found: 2 files

### 1. docs/designs/CROSS_REPO_TEMPLATE_DESIGN.md

**Lines 727-729**: Contains absolute paths

```
- `/home/steven/code/Swarm/demo-swarm-dev/swarm/tools/selftest.py` - Current implementation
- `/home/steven/code/Swarm/demo-swarm-dev/swarm/tools/selftest_config.py` - Step definitions
- `/home/steven/code/Swarm/demo-swarm-dev/swarm/SELFTEST_SYSTEM.md` - System documentation
```

**Fix**: Replace with relative paths:
```
- `swarm/tools/selftest.py` - Current implementation
- `swarm/tools/selftest_config.py` - Step definitions
- `swarm/SELFTEST_SYSTEM.md` - System documentation
```

### 2. packages/selftest-core/LICENSE

**Line 3**: Contains old repo name

```
Copyright (c) 2024-2025 demo-swarm-dev contributors
```

**Fix**: Replace with:
```
Copyright (c) 2024-2025 Flow Studio contributors
```

## NOT Issues (Classified Correctly)

The following "staging" references are **environment names**, not repo identity:

| File | Context | Verdict |
|------|---------|---------|
| `observability/**` | "staging environment" SLOs/alerts | OK |
| `docs/SELFTEST_OBSERVABILITY_SPEC.md` | "staging" = deployment tier | OK |
| `docs/SELFTEST_ENVIRONMENT_OPERATIONS.md` | "staging" = deployment tier | OK |
| `.claude/agents/work-planner.md` | "Deploy migrations to staging" | OK |
| `REPO_MAP.md` | "staging" = git staging area | OK |

## Fix Commands

```bash
# Fix CROSS_REPO_TEMPLATE_DESIGN.md
sed -i 's|/home/steven/code/Swarm/demo-swarm-dev/||g' docs/designs/CROSS_REPO_TEMPLATE_DESIGN.md

# Fix LICENSE
sed -i 's/demo-swarm-dev contributors/Flow Studio contributors/' packages/selftest-core/LICENSE
```
