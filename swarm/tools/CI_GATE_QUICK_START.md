# CI Gate Quick Start

## TL;DR

Run the CI validation gate to enforce swarm configuration integrity:

```bash
# Local development
make ci-validate
make ci-validate-strict

# Or directly
./swarm/tools/ci_validate_swarm.sh --fail-on-fail
```

## One-Minute Overview

The `ci_validate_swarm.sh` script wraps `validate_swarm.py --json` to provide CI-friendly validation of swarm configuration (agents, flows, skills) with flexible enforcement modes.

**What it checks** (Functional Requirements):
- FR-001: Agent ↔ file bijection
- FR-002: Frontmatter validity (name, description, color, model)
- FR-002b: Color matches role family
- FR-003: All agents referenced in flows exist
- FR-004: All declared skills have SKILL.md files
- FR-005: Flow specs use RUN_BASE placeholders
- FR-CONF: Config matches frontmatter

**Exit codes**:
- `0` = passed
- `1` = failed (checks didn't pass)
- `2` = fatal error (missing tools, invalid JSON)

## Common Commands

```bash
# Standard CI gate (fail if any check fails)
./swarm/tools/ci_validate_swarm.sh --fail-on-fail

# Strict gate (fail on warnings too)
./swarm/tools/ci_validate_swarm.sh --fail-on-warn

# With detailed issue list
./swarm/tools/ci_validate_swarm.sh --fail-on-fail --list-issues

# Only check specific FRs (conservative)
./swarm/tools/ci_validate_swarm.sh --enforce-fr FR-001,FR-002,FR-002b

# Quiet mode for logs
./swarm/tools/ci_validate_swarm.sh --summary

# Via Make
make ci-validate
make ci-validate-strict
```

## GitHub Actions Integration

### Blessed Minimal Snippet

Use this in your `.github/workflows/validate.yml` (or similar):

```yaml
- name: Swarm validation gate
  run: |
    ./swarm/tools/ci_validate_swarm.sh \
      --fail-on-fail \
      --enforce-fr FR-001,FR-002,FR-003,FR-004,FR-005
```

This is the **recommended minimal setup** for any swarm. It:
- Enforces only structural FRs (agent bijection, colors, references, skills, paths)
- Fails the PR if alignment breaks
- Blocks silent drifts before merge

### Already Integrated

This repo has it in `.github/workflows/swarm-validate.yml`:

```yaml
- name: Run swarm validation gate
  run: ./swarm/tools/ci_validate_swarm.sh --fail-on-fail --list-issues
```

Branch-specific enforcement:
- **main branch**: Strict (`--fail-on-warn`) - fail on warnings
- **PRs**: Lenient (`--fail-on-fail`) - fail only on failures

## Troubleshooting

### "jq is required but not found"
```bash
sudo apt-get install jq
```

### "uv is required but not found"
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Script returns exit code 2
Something is broken (missing tools, validator crash). Run:
```bash
./swarm/tools/ci_validate_swarm.sh --fail-on-fail --list-issues
```
for details.

### Want more details
```bash
./swarm/tools/ci_validate_swarm.sh --list-issues --fail-on-fail
```

## Output Examples

### Success
```
=== Swarm Validation Summary ===
Status:        PASS
Total checks:  0
Passed:        0
Failed:        0
Warnings:      0
========================================
```

### Failure with issues
```
=== Swarm Validation Summary ===
Status:        FAIL
Total checks:  5
Passed:        4
Failed:        1
Warnings:      0

Agents with issues:
  * test-agent (.claude/agents/test-agent.md)
      FR-002: fail

Validation failed. Review issues above.
```

## Flags Reference

| Flag | Effect |
|------|--------|
| `--fail-on-fail` | Exit 1 if any check fails (default) |
| `--fail-on-warn` | Exit 1 if any check fails OR warns (stricter) |
| `--enforce-fr FRS` | Only check specific FRs (e.g., `FR-001,FR-002`) |
| `--list-issues` | Print detailed issue breakdown |
| `--summary` | One-line output (quiet mode) |
| `--help` | Show help text |

## For More Information

See:
- `swarm/tools/CI_GATE_GUIDE.md` - Complete guide with examples
- `swarm/tools/CI_GATE_IMPLEMENTATION.md` - Technical details
- `.github/workflows/swarm-validate.yml` - GitHub Actions workflow
- `Makefile` - Make targets (`ci-validate`, `ci-validate-strict`)

Or run:
```bash
./swarm/tools/ci_validate_swarm.sh --help
```
