# Artifact and Junk File Scan Report

**Scan Date:** 2025-12-13
**Output Directory:** `.runs/release-align-20251213-034703/scans/`

---

## Summary

**Status: CLEAN ✓**

- No `.runs/` files are tracked by git
- No tracked files exceed 1MB threshold
- `.gitignore` includes all recommended patterns

---

## 1. Tracked `.runs/` Files

**Result:** None found (0 files)

The `.runs/` directory is properly gitignored. No files from this directory are tracked by git.

See: `tracked_runs_files.txt` (empty file confirms clean state)

---

## 2. Largest Tracked Files

**Result:** No files exceed 1MB threshold

The largest tracked file is `swarm/tools/flow_studio_ui/index.html` at **381,504 bytes** (373 KB).

All tracked files are under 1MB, which is appropriate for source code, documentation, and configuration files.

### Top 10 Largest Files:

| Size (bytes) | Size (KB) | File |
|--------------|-----------|------|
| 381,504 | 373 KB | swarm/tools/flow_studio_ui/index.html |
| 174,352 | 170 KB | uv.lock |
| 101,916 | 100 KB | swarm/tools/validate_swarm.py |
| 89,208 | 87 KB | docs/flowstudio-openapi.json |
| 87,617 | 86 KB | swarm/examples/stepwise-sdlc-claude/events.jsonl |
| 78,903 | 77 KB | swarm/examples/stepwise-deploy-claude/events.jsonl |
| 75,135 | 73 KB | swarm/runtime/engines.py |
| 72,625 | 71 KB | docs/SELFTEST_ENVIRONMENT_OPERATIONS.md |
| 71,614 | 70 KB | swarm/examples/stepwise-gate-claude/events.jsonl |
| 69,377 | 68 KB | packages/selftest-core/uv.lock |

See: `largest_tracked_files.txt` (full list of top 50 files)

---

## 3. .gitignore Pattern Analysis

**Result:** All recommended patterns present ✓

The `.gitignore` file includes comprehensive patterns for:

### Required Patterns (all present):

#### `.runs/` Directory
```gitignore
/swarm/runs/
/RUN_BASE/
```
Status: ✓ Covered (`.runs/` would be untracked anyway as untracked directory)

#### Python Cache Files
```gitignore
__pycache__/
*.py[cod]
```
Status: ✓ Present (lines 33-34)

#### Virtual Environments
```gitignore
.venv/
venv/
```
Status: ✓ Present (lines 35-36)

#### Node Modules
```gitignore
swarm/tools/flow_studio_ui/node_modules/
```
Status: ✓ Present (line 30)

#### Environment Files
```gitignore
# No explicit .env pattern found
```
Status: ⚠️ Missing `.env` pattern

### Additional Patterns Found:

The `.gitignore` includes many other appropriate patterns:
- Test artifacts (`.pytest_cache/`, `.coverage`, `htmlcov/`)
- Build artifacts (`/target/`, `*.bak`, `BUILD_SUMMARY.md`)
- IDE files (`.vscode/`, `.idea/`, `*.swp`)
- OS files (`.DS_Store`, `Thumbs.db`)
- Smoke test artifacts (`/artifacts/flowstudio_smoke/`)
- Playwright MCP artifacts (`.playwright-mcp/`)

---

## Recommendations

### 1. Add `.env` Pattern (Low Priority)

**Current State:** No explicit pattern for `.env` files
**Risk:** Low (no `.env` files currently tracked)
**Action:** Consider adding:

```gitignore
# Environment files (secrets, local config)
.env
.env.*
!.env.example
```

This would prevent accidental commits of local environment configuration files containing secrets or API keys.

### 2. Consider Adding `.runs/` Pattern (Very Low Priority)

**Current State:** `.runs/` not explicitly in `.gitignore`
**Risk:** Very Low (untracked directories are not committed by default)
**Action:** Optional - add explicit pattern for documentation:

```gitignore
# Release and operational artifacts
.runs/
```

This would make the intention more explicit, though the directory is already untracked.

---

## Verification Commands Run

1. Check tracked `.runs/` files:
   ```bash
   git ls-files .runs > tracked_runs_files.txt
   ```

2. Find 50 largest tracked files:
   ```bash
   git ls-files -z | xargs -0 -I {} stat -c '%s %n' {} 2>/dev/null | \
     sort -rn | head -50 > largest_tracked_files.txt
   ```

3. Review `.gitignore` patterns:
   ```bash
   cat .gitignore
   ```

---

## Conclusion

The repository is in good shape regarding artifact and junk file management:

- **No accidentally tracked artifacts** in `.runs/` or other transient directories
- **No large binary files** that might be generated artifacts
- **Comprehensive `.gitignore`** covering most common patterns

The only minor suggestion is adding explicit `.env` pattern for defense-in-depth against accidental secret commits, though no such files are currently tracked.
