# Selftest Minimal Template

> For: Teams adopting layered selftest in under 30 minutes

Drop this template into your repo to get a tiered selftest system running quickly.

## Quick Start

1. **Copy this template to your repo root:**

   ```bash
   cp -r templates/selftest-minimal/* your-repo/
   ```

2. **Install dependencies:**

   ```bash
   cd your-repo
   pip install selftest-core
   # Or with uv:
   uv add selftest-core
   ```

3. **Customize your config:**

   Edit `selftest.yaml` to match your project:
   - Update test paths (`tests/` → your test directory)
   - Adjust coverage thresholds
   - Add or remove steps as needed

4. **Run selftest:**

   ```bash
   # Run all steps (strict mode)
   selftest run

   # Run only KERNEL tier (fast smoke test)
   selftest run --kernel-only

   # Run in degraded mode (only KERNEL failures block)
   selftest run --degraded

   # Run a specific step
   selftest run --step lint

   # Show plan without executing
   selftest plan

   # List available steps
   selftest list
   ```

## Three-Tier System

| Tier | Purpose | Failure Behavior |
|------|---------|------------------|
| **KERNEL** | Critical checks (lint, compile, fast tests) | Blocks everything |
| **GOVERNANCE** | Policy checks (security, coverage) | Blocks merge (in strict mode) |
| **OPTIONAL** | Nice-to-have checks (type hints, extras) | Warning only |

## Files

```
your-repo/
├── selftest.yaml           # Selftest configuration (edit this)
├── pyproject.toml          # Project with selftest-core dependency
├── .github/
│   └── workflows/
│       └── selftest.yml    # GitHub Actions workflow
└── src/                    # Your code
```

## Customization

### Adding Custom Steps

Add steps directly in `selftest.yaml`:

```yaml
steps:
  - id: my-check
    tier: governance
    command: ./scripts/my-check.sh
    description: "My custom check"
    severity: warning
    category: governance
    timeout: 60
```

### Step Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique identifier |
| `tier` | Yes | `kernel`, `governance`, or `optional` |
| `command` | Yes | Shell command to run |
| `description` | No | Human-readable description |
| `severity` | No | `critical`, `warning`, or `info` (default: warning) |
| `category` | No | `security`, `performance`, `correctness`, or `governance` |
| `timeout` | No | Timeout in seconds (default: 60) |
| `dependencies` | No | List of step IDs that must run first |

### Step Dependencies

Steps can depend on other steps:

```yaml
steps:
  - id: build
    tier: kernel
    command: make build

  - id: test
    tier: kernel
    command: make test
    dependencies:
      - build  # build runs first
```

## CI Integration

The included GitHub Actions workflow (`.github/workflows/selftest.yml`):

- Runs all selftest steps on push/PR to main
- KERNEL failures fail the workflow immediately
- GOVERNANCE failures fail the workflow
- OPTIONAL failures are logged but don't fail

For other CI systems:

```bash
# Fast kernel smoke test
selftest run --kernel-only

# Full strict check (all tiers, any failure blocks)
selftest run

# Degraded mode (only KERNEL failures block)
selftest run --degraded
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All checks passed (or only non-blocking failures in degraded mode) |
| 1 | One or more blocking checks failed |
| 2 | Configuration error |

## Diagnostics

If selftest fails unexpectedly:

```bash
# Run diagnostics
selftest doctor

# Show execution plan
selftest plan

# Run with verbose output
selftest run -v
```

## Requirements

- Python >= 3.10
- selftest-core >= 0.1.0

## Next Steps

1. Review `selftest.yaml` and customize steps for your project
2. Add custom steps as needed
3. Adjust CI workflow for your branching strategy
4. Consider adding more GOVERNANCE checks (license compliance, etc.)
