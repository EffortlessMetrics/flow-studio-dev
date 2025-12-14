# Runs Retention Policy Runbook

> This runbook documents the runs retention policy and garbage collection operations.

## TL;DR

```bash
make runs-list        # See current run count and status
make runs-prune-dry   # Preview what would be deleted
make runs-prune       # Apply retention policy
```

---

## Retention Policy (v2.3.0 Defaults)

| Setting | Default | Environment Override |
|---------|---------|---------------------|
| Retention days | 30 | `SWARM_RUNS_RETENTION_DAYS` |
| Max runs | 300 | `SWARM_RUNS_MAX_COUNT` |
| Dry-run mode | off | `SWARM_RUNS_DRY_RUN=1` |

**Preserved patterns** (never deleted):
- Named runs: `demo-health-check`, `demo-run`
- Prefixes: `stepwise-`, `baseline-`
- Tags: `pinned`, `golden`
- Example runs in `swarm/examples/`

**Per-flow overrides** (in `runs_retention.yaml`):
- `gate`, `deploy`, `wisdom`: 60 days (longer audit trail)
- `signal`, `plan`, `build`: 30 days

---

## Commands Reference

### Inspection

```bash
# Quick stats
make runs-list

# Verbose listing with age/size
make runs-list-v

# Full GC help
make runs-gc-help
```

### Cleanup

```bash
# Preview what would be deleted (SAFE)
make runs-prune-dry

# Apply retention policy
make runs-prune

# Override retention days
SWARM_RUNS_RETENTION_DAYS=7 make runs-prune-dry
```

### Quarantine (Corrupt Runs)

```bash
# Preview corrupt runs
make runs-quarantine-dry

# Move corrupt runs to swarm/runs/_corrupt/
make runs-quarantine
```

### Nuclear Option

```bash
# Delete all run-* directories (preserves named examples)
make runs-clean
```

> **When to use nuclear vs surgical:**
>
> | Approach | Command | When to Use |
> |----------|---------|-------------|
> | **Surgical (preferred)** | `make runs-prune` | Daily cleanup, before demos, CI maintenance |
> | **Quarantine** | `make runs-quarantine` | Corrupt runs causing parse errors |
> | **Nuclear** | `make runs-clean` | Fresh dev environment, post-conference reset, disk emergency |
>
> **Prefer surgical**: `runs-prune` respects retention policy and preserves important runs.
> Use `runs-clean` only when you want a complete reset.

---

## When to Run GC

1. **Before demos**: `make runs-prune-dry && make runs-prune` to clean up stale runs
2. **After CI failures**: Check if corrupt runs are causing issues
3. **Disk space alerts**: Run `make runs-list` to see total size
4. **Flow Studio slow**: Too many runs can slow `/api/runs` endpoint

---

## Troubleshooting

### Symptom: Flow Studio shows stale runs
```bash
make runs-prune-dry  # Review
make runs-prune      # Apply
make flow-studio     # Restart
```

### Symptom: "Failed to parse summary" in logs
```bash
make runs-quarantine-dry  # Identify corrupt runs
make runs-quarantine      # Move to _corrupt/
```

### Symptom: Runs directory very large
```bash
make runs-list-v | head -20  # See biggest/oldest runs
SWARM_RUNS_MAX_COUNT=100 make runs-prune  # Reduce count
```

### Symptom: Important run was deleted
- Check git history (runs are gitignored, but examples aren't)
- Check `swarm/runs/_corrupt/` for quarantined runs
- Regenerate from examples: `make demo-run`

---

## Configuration File

**Location:** `swarm/config/runs_retention.yaml`

```yaml
policy:
  enabled: true
  default_retention_days: 30
  strict_mode: false

runs:
  max_count: 300
  preserve:
    named_runs:
      - "demo-health-check"
    prefixes:
      - "stepwise-"
      - "baseline-"
    tags:
      - "pinned"
      - "golden"
  preserve_examples: true

features:
  dry_run: false
  log_deletions: true
  quarantine_corrupt: true
```

---

## See Also

- [RUN_LIFECYCLE.md](../../docs/RUN_LIFECYCLE.md) - Full run lifecycle documentation
- [STEPWISE_BACKENDS.md](../../docs/STEPWISE_BACKENDS.md) - How stepwise runs are created
- [FLOW_STUDIO.md](../../docs/FLOW_STUDIO.md) - How Flow Studio displays runs
