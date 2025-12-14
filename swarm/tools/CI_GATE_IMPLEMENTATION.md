# CI Gate Implementation Summary

This document provides a complete overview of the CI gate validation system for enforcing swarm configuration integrity.

## Deliverables

### 1. CI Gate Script: `swarm/tools/ci_validate_swarm.sh`

**Location**: `swarm/tools/ci_validate_swarm.sh`

**Purpose**: Bash script that wraps `validate_swarm.py --json` to provide CI-friendly validation with flexible enforcement modes.

**Key Features**:
- Parses validator JSON output using `jq`
- Supports multiple enforcement modes:
  - `--fail-on-fail` (default): Exit 1 if any FR check fails
  - `--fail-on-warn`: Exit 1 if any check fails OR warns (stricter)
  - `--enforce-fr FR-001,FR-002`: Check only specific FRs
- Output modes:
  - Default: Summary + detailed issues
  - `--summary`: One-line output for logs
  - `--list-issues`: Verbose issue breakdown
- No external dependencies beyond `bash`, `jq`, and `uv`
- Proper exit codes: 0 (pass), 1 (fail), 2 (fatal error)

**Usage Examples**:

```bash
# Default: fail if any check fails
./swarm/tools/ci_validate_swarm.sh --fail-on-fail

# Strict: fail on warnings too
./swarm/tools/ci_validate_swarm.sh --fail-on-warn

# Conservative: only check bijection and frontmatter
./swarm/tools/ci_validate_swarm.sh --enforce-fr FR-001,FR-002,FR-002b

# Quiet mode for logs
./swarm/tools/ci_validate_swarm.sh --summary

# Debug mode with full details
./swarm/tools/ci_validate_swarm.sh --list-issues --fail-on-fail
```

**Implementation Details**:
- ~400 lines of well-commented bash
- Modular functions: parse_args, check_dependencies, run_validator, extract_summary, list_agent_issues, list_flow_issues, check_enforcement, check_specific_frs, main
- Color-coded output (green/red/yellow for terminal clarity)
- Graceful error handling for missing tools or invalid JSON

### 2. CI Gate Documentation: `swarm/tools/CI_GATE_GUIDE.md`

**Location**: `swarm/tools/CI_GATE_GUIDE.md`

**Contents**:
- Complete usage guide with examples
- Functional Requirements (FR) reference table
- GitHub Actions integration examples
- Make integration patterns
- Exit code reference
- JSON output contract documentation
- JQ filter reference for custom analysis
- Troubleshooting guide
- Advanced patterns (branch-specific gates, check reporting, progressive enforcement)
- Performance notes

### 3. GitHub Actions Workflow: `.github/workflows/swarm-validate.yml`

**Location**: `.github/workflows/swarm-validate.yml`

**Updates**:
- Integrated `ci_validate_swarm.sh` into the validation workflow
- Separate enforcement policies:
  - Strict on main branch: `--fail-on-warn --list-issues`
  - Lenient on PRs: `--fail-on-fail --list-issues`
  - Incremental validation for PRs (optional, for performance)
- Proper permissions and timeouts
- Clear job naming and documentation

**What it does**:
1. Runs on all pushes to main/develop and all PRs when swarm/claude paths are modified
2. Installs Python, uv, and jq dependencies
3. Runs strict gate on main (fail on warnings), lenient on PRs (fail on failures only)
4. Includes optional FR-specific validation jobs for detailed checking

### 4. Makefile Integration

**Location**: `Makefile`

**New Targets**:
```makefile
.PHONY: ci-validate
ci-validate:
	./swarm/tools/ci_validate_swarm.sh --fail-on-fail --list-issues

.PHONY: ci-validate-strict
ci-validate-strict:
	./swarm/tools/ci_validate_swarm.sh --fail-on-warn --list-issues
```

**Updated help text** to mention new targets.

**Usage**:
```bash
make ci-validate          # Run CI gate locally (fail on failures)
make ci-validate-strict   # Run strict gate locally (fail on warnings too)
```

## How It Works

### Script Flow

1. **Parse arguments**: Handle flags (--fail-on-fail, --fail-on-warn, etc.)
2. **Check dependencies**: Verify `jq` and `uv` are available
3. **Run validator**: Execute `validate_swarm.py --json` and capture output
4. **Validate JSON**: Ensure output is well-formed
5. **Extract summary**: Parse and display summary stats
6. **List issues** (optional): Print detailed agent/flow issues
7. **Enforce rules**: Check if validation passed enforcement criteria
8. **Return exit code**: 0 for pass, 1 for fail, 2 for fatal error

### JSON Parsing Strategy

The script uses `jq` for all JSON operations:

```jq
# Extract summary status
.summary.status

# Count issues
.summary.passed, .summary.failed, .summary.warnings

# Get agents/flows with issues
.summary.agents_with_issues[]
.summary.flows_with_issues[]

# Check specific FR across all agents/flows
.agents[].checks["FR-001"]?
.flows[].checks["FR-001"]?

# Filter to failures/warnings
| select(.status == "fail") | .status
```

## FR Reference

The script can enforce these FRs from the validator:

| FR | Check | Description |
|----|-------|-------------|
| FR-001 | Bijection | 1:1 agent↔file mapping |
| FR-002 | Frontmatter | Required YAML fields |
| FR-002b | Color match | Agent color matches role family |
| FR-003 | Flow refs | All referenced agents exist |
| FR-004 | Skills | All declared skills exist |
| FR-005 | RUN_BASE | Paths use placeholders |
| FR-CONF | Config | Config alignment with frontmatter |

## Integration Patterns

### Pattern 1: Basic CI Gate (Recommended)

```yaml
# .github/workflows/swarm-validate.yml
- name: Run swarm validation gate
  run: ./swarm/tools/ci_validate_swarm.sh --fail-on-fail --list-issues
```

### Pattern 2: Branch-Specific Enforcement

```yaml
- name: Validate swarm
  run: |
    if [ "${{ github.ref }}" == "refs/heads/main" ]; then
      ./swarm/tools/ci_validate_swarm.sh --fail-on-warn
    else
      ./swarm/tools/ci_validate_swarm.sh --fail-on-fail
    fi
```

### Pattern 3: FR-Specific Gates

```bash
# Only enforce core FRs (fast)
./swarm/tools/ci_validate_swarm.sh --enforce-fr FR-001,FR-002 --fail-on-fail

# Enforce all FRs (comprehensive)
./swarm/tools/ci_validate_swarm.sh --fail-on-fail
```

### Pattern 4: Local Development

```bash
# Before committing
make ci-validate

# Or strict mode
make ci-validate-strict
```

## Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Validation passed all enforcement criteria | Continue (build succeeds) |
| 1 | Validation failed or warnings in strict mode | Fail (block merge/build) |
| 2 | Fatal error (missing tools, invalid JSON, validator crash) | Fail (investigate system issue) |

## Testing the Gate

Local testing:

```bash
# Test all enforcement modes
./swarm/tools/ci_validate_swarm.sh --fail-on-fail
./swarm/tools/ci_validate_swarm.sh --fail-on-warn
./swarm/tools/ci_validate_swarm.sh --summary
./swarm/tools/ci_validate_swarm.sh --list-issues

# Test FR-specific enforcement
./swarm/tools/ci_validate_swarm.sh --enforce-fr FR-001
./swarm/tools/ci_validate_swarm.sh --enforce-fr FR-001,FR-002,FR-002b

# Test help
./swarm/tools/ci_validate_swarm.sh --help
```

CI testing:

```bash
# Test via make
make ci-validate
make ci-validate-strict

# Test via GitHub Actions (on push)
git push origin feature-branch
# Watch: https://github.com/yourorg/repo/actions
```

## Performance

- Validator runtime: ~1-2 seconds (Python startup + validation)
- JSON parsing: <100ms (jq is fast)
- Total gate latency: ~1-2 seconds on typical repos
- For large swarms (100+ agents): use `validate_swarm.py --check-modified` for incremental validation

## Error Handling

The script handles these error cases gracefully:

1. **Missing jq**: Prints error message, exit code 2
2. **Missing uv**: Prints error message, exit code 2
3. **Validator crash**: Captures stderr, prints error, exit code 2
4. **Invalid JSON**: Detects with `jq empty`, prints error, exit code 2
5. **Validation failure**: Prints issues, exit code 1
6. **Warnings in strict mode**: Treated as failures, exit code 1

## Color Coding

Terminal output uses ANSI colors:
- **Blue**: Section headers
- **Green**: PASS status, passed counts
- **Red**: FAIL status, failed counts, errors
- **Yellow**: WARNING status, warning counts, issues

## Next Steps

1. **Verify locally**:
   ```bash
   make ci-validate
   ```

2. **Enable in GitHub Actions**:
   - The workflow file is already updated
   - Next push to swarm/ or .claude/ will run the gate

3. **Customize enforcement**:
   - Edit `.github/workflows/swarm-validate.yml` to adjust flags
   - Add branch-specific rules as needed
   - See CI_GATE_GUIDE.md for patterns

4. **Monitor gate effectiveness**:
   - Check GitHub Actions logs to see validation details
   - Use `--summary` flag for clean logs
   - Use `--list-issues` for debugging

## Files Modified

- **Created**: `/swarm/tools/ci_validate_swarm.sh` (executable bash script)
- **Created**: `/swarm/tools/CI_GATE_GUIDE.md` (comprehensive guide)
- **Created**: `/swarm/tools/CI_GATE_IMPLEMENTATION.md` (this file)
- **Updated**: `/.github/workflows/swarm-validate.yml` (integrated script)
- **Updated**: `/Makefile` (added ci-validate, ci-validate-strict targets)

## See Also

- `swarm/tools/validate_swarm.py` - Core validation logic
- `swarm/tools/CI_GATE_GUIDE.md` - User guide with examples
- `CLAUDE.md` - Full swarm documentation
- `.github/workflows/swarm-validate.yml` - GitHub Actions workflow
