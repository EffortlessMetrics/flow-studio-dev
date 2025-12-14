#!/bin/bash

################################################################################
# ci_validate_swarm.sh - Swarm CI Gate Validator
#
# A CI-friendly wrapper around validate_swarm.py --json that enforces
# specific FR (Functional Requirement) conditions in CI pipelines.
#
# USAGE:
#   ./swarm/tools/ci_validate_swarm.sh [FLAGS]
#
# FLAGS:
#   --fail-on-fail      Exit 1 if any check fails (default behavior)
#   --fail-on-warn      Exit 1 if any check fails OR warns (stricter)
#   --enforce-fr FRS    Only check specific FRs (comma-separated, no spaces)
#                       Example: --enforce-fr FR-001,FR-002,FR-003
#   --list-issues       Print detailed issue breakdown (default: summary only)
#   --summary           Print only summary line (quiet mode)
#   --help              Show this help text
#
# EXIT CODES:
#   0  Validation passed (all enforced checks passed)
#   1  Validation failed (checks failed or warnings detected in strict mode)
#   2  Fatal error (validator crashed, invalid JSON, missing tools)
#
# EXAMPLES:
#
#   # CI gate: fail if any validation failure
#   ./swarm/tools/ci_validate_swarm.sh --fail-on-fail
#
#   # Strict gate: fail on warnings too
#   ./swarm/tools/ci_validate_swarm.sh --fail-on-warn
#
#   # Debug: show all issues with details
#   ./swarm/tools/ci_validate_swarm.sh --list-issues --fail-on-fail
#
#   # Conservative: only enforce FR-001 (bijection) and FR-002 (frontmatter)
#   ./swarm/tools/ci_validate_swarm.sh --enforce-fr FR-001,FR-002 --fail-on-fail
#
# GITHUB ACTIONS INTEGRATION:
#
#   # .github/workflows/swarm-validate.yml
#   - name: Validate swarm configuration
#     run: |
#       ./swarm/tools/ci_validate_swarm.sh --fail-on-fail --list-issues
#     continue-on-error: false  # Hard fail the workflow
#
# MAKE INTEGRATION:
#
#   # Add to Makefile:
#   .PHONY: ci-validate
#   ci-validate:
#   	./swarm/tools/ci_validate_swarm.sh --fail-on-fail --list-issues
#
#   # Then in CI:
#   make ci-validate
#
################################################################################

set -o pipefail

# ANSI color codes for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

# Configuration flags (defaults)
FAIL_ON_WARN=false
LIST_ISSUES=false
SUMMARY_ONLY=false
ENFORCE_FRS=""

# Counters
TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_WARNINGS=0

################################################################################
# parse_args: Parse command-line arguments
################################################################################
parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --fail-on-fail)
        # This is the default behavior, nothing to do
        shift
        ;;
      --fail-on-warn)
        FAIL_ON_WARN=true
        shift
        ;;
      --list-issues)
        LIST_ISSUES=true
        shift
        ;;
      --summary)
        SUMMARY_ONLY=true
        shift
        ;;
      --enforce-fr)
        ENFORCE_FRS="$2"
        shift 2
        ;;
      --help)
        usage
        exit 0
        ;;
      *)
        echo "Unknown flag: $1" >&2
        usage
        exit 2
        ;;
    esac
  done
}

################################################################################
# usage: Print help text
################################################################################
usage() {
  cat << 'EOF'
ci_validate_swarm.sh - Swarm CI Gate Validator

A CI-friendly wrapper around validate_swarm.py --json that enforces
specific FR (Functional Requirement) conditions in CI pipelines.

USAGE:
  ./swarm/tools/ci_validate_swarm.sh [FLAGS]

FLAGS:
  --fail-on-fail      Exit 1 if any check fails (default behavior)
  --fail-on-warn      Exit 1 if any check fails OR warns (stricter)
  --enforce-fr FRS    Only check specific FRs (comma-separated, no spaces)
                      Example: --enforce-fr FR-001,FR-002,FR-003
  --list-issues       Print detailed issue breakdown (default: summary only)
  --summary           Print only summary line (quiet mode)
  --help              Show this help text

EXIT CODES:
  0  Validation passed (all enforced checks passed)
  1  Validation failed (checks failed or warnings detected in strict mode)
  2  Fatal error (validator crashed, invalid JSON, missing tools)

EXAMPLES:
  # CI gate: fail if any validation failure
  ./swarm/tools/ci_validate_swarm.sh --fail-on-fail

  # Strict gate: fail on warnings too
  ./swarm/tools/ci_validate_swarm.sh --fail-on-warn

  # Debug: show all issues with details
  ./swarm/tools/ci_validate_swarm.sh --list-issues --fail-on-fail

  # Conservative: only enforce FR-001 (bijection) and FR-002 (frontmatter)
  ./swarm/tools/ci_validate_swarm.sh --enforce-fr FR-001,FR-002 --fail-on-fail

GITHUB ACTIONS INTEGRATION:
  # .github/workflows/swarm-validate.yml
  - name: Validate swarm configuration
    run: |
      ./swarm/tools/ci_validate_swarm.sh --fail-on-fail --list-issues
    continue-on-error: false

MAKE INTEGRATION:
  # Add to Makefile:
  .PHONY: ci-validate
  ci-validate:
  	./swarm/tools/ci_validate_swarm.sh --fail-on-fail --list-issues

  # Then in CI:
  make ci-validate
EOF
}

################################################################################
# check_dependencies: Verify jq and uv are available
################################################################################
check_dependencies() {
  if ! command -v jq &> /dev/null; then
    echo -e "${RED}ERROR${NC}: jq is required but not found. Install with: apt-get install jq" >&2
    return 2
  fi

  if ! command -v uv &> /dev/null; then
    echo -e "${RED}ERROR${NC}: uv is required but not found. See: https://docs.astral.sh/uv/getting-started/installation/" >&2
    return 2
  fi

  return 0
}

################################################################################
# run_validator: Run validate_swarm.py and capture JSON output
################################################################################
run_validator() {
  local raw_output json_output
  # Use --quiet to suppress uv's venv setup messages
  raw_output=$(uv run --quiet swarm/tools/validate_swarm.py --json 2>&1)
  local exit_code=$?

  # Extract JSON from output (in case uv still outputs non-JSON content)
  # JSON starts with '{' and ends with '}'
  json_output=$(echo "$raw_output" | sed -n '/^{/,/^}$/p')

  if [[ $exit_code -ne 0 ]]; then
    echo -e "${RED}ERROR${NC}: Validator failed with exit code $exit_code" >&2
    echo "Output: $raw_output" >&2
    return 2
  fi

  # Validate JSON is well-formed
  if [[ -z "$json_output" ]] || ! echo "$json_output" | jq empty 2>/dev/null; then
    echo -e "${RED}ERROR${NC}: Validator produced invalid JSON" >&2
    echo "Raw output: $raw_output" >&2
    return 2
  fi

  echo "$json_output"
  return 0
}

################################################################################
# extract_summary: Extract and display summary statistics
################################################################################
extract_summary() {
  local json="$1"

  TOTAL_PASSED=$(echo "$json" | jq '.summary.passed // 0')
  TOTAL_FAILED=$(echo "$json" | jq '.summary.failed // 0')
  TOTAL_WARNINGS=$(echo "$json" | jq '.summary.warnings // 0')

  local status=$(echo "$json" | jq -r '.summary.status // "UNKNOWN"')
  local total=$(echo "$json" | jq '.summary.total_checks // 0')
  local total_count=$((TOTAL_PASSED + TOTAL_FAILED + TOTAL_WARNINGS))

  # Color-code status
  local status_color="$GREEN"
  if [[ "$status" == "FAIL" ]]; then
    status_color="$RED"
  elif [[ "$TOTAL_WARNINGS" -gt 0 && "$FAIL_ON_WARN" == "true" ]]; then
    status_color="$YELLOW"
  fi

  if [[ "$SUMMARY_ONLY" != "true" ]]; then
    echo -e "${BLUE}=== Swarm Validation Summary ===${NC}"
    echo -e "Status:        ${status_color}${status}${NC}"
    echo -e "Total checks:  ${total_count}"
    echo -e "Passed:        ${GREEN}${TOTAL_PASSED}${NC}"
    echo -e "Failed:        ${RED}${TOTAL_FAILED}${NC}"
    echo -e "Warnings:      ${YELLOW}${TOTAL_WARNINGS}${NC}"
  else
    echo -e "Validation: ${status_color}${status}${NC} (P: ${TOTAL_PASSED}, F: ${TOTAL_FAILED}, W: ${TOTAL_WARNINGS})"
  fi
}

################################################################################
# list_agent_issues: Print detailed agent issues
################################################################################
list_agent_issues() {
  local json="$1"
  local agents_with_issues

  agents_with_issues=$(echo "$json" | jq -r '.summary.agents_with_issues[]? // empty')

  if [[ -z "$agents_with_issues" ]]; then
    return
  fi

  if [[ "$SUMMARY_ONLY" != "true" ]]; then
    echo ""
    echo -e "${YELLOW}Agents with issues:${NC}"

    while IFS= read -r agent_key; do
      [[ -z "$agent_key" ]] && continue

      local agent_file=$(echo "$json" | jq -r ".agents[\"$agent_key\"].file // \"unknown\"")
      echo -e "  ${YELLOW}*${NC} ${agent_key} (${agent_file})"

      # Print per-check status
      local checks=$(echo "$json" | jq -r ".agents[\"$agent_key\"].checks | to_entries[] | select(.value.status != \"pass\") | \"\(.key)=\(.value.status)\"")
      while IFS= read -r check_status; do
        [[ -z "$check_status" ]] && continue
        local fr_code="${check_status%%=*}"
        local fr_status="${check_status##*=}"

        local color="$RED"
        [[ "$fr_status" == "warn" ]] && color="$YELLOW"

        echo -e "      ${color}${fr_code}: ${fr_status}${NC}"
      done <<< "$checks"
    done <<< "$agents_with_issues"
  fi
}

################################################################################
# list_flow_issues: Print detailed flow issues
################################################################################
list_flow_issues() {
  local json="$1"
  local flows_with_issues

  flows_with_issues=$(echo "$json" | jq -r '.summary.flows_with_issues[]? // empty')

  if [[ -z "$flows_with_issues" ]]; then
    return
  fi

  if [[ "$SUMMARY_ONLY" != "true" ]]; then
    echo ""
    echo -e "${YELLOW}Flows with issues:${NC}"

    while IFS= read -r flow_key; do
      [[ -z "$flow_key" ]] && continue

      local flow_file=$(echo "$json" | jq -r ".flows[\"$flow_key\"].file // \"unknown\"")
      echo -e "  ${YELLOW}*${NC} ${flow_key} (${flow_file})"

      # Print per-check status
      local checks=$(echo "$json" | jq -r ".flows[\"$flow_key\"].checks | to_entries[] | select(.value.status != \"pass\") | \"\(.key)=\(.value.status)\"")
      while IFS= read -r check_status; do
        [[ -z "$check_status" ]] && continue
        local fr_code="${check_status%%=*}"
        local fr_status="${check_status##*=}"

        local color="$RED"
        [[ "$fr_status" == "warn" ]] && color="$YELLOW"

        echo -e "      ${color}${fr_code}: ${fr_status}${NC}"
      done <<< "$checks"
    done <<< "$flows_with_issues"
  fi
}

################################################################################
# check_enforcement: Determine if validation passes enforcement rules
################################################################################
check_enforcement() {
  local json="$1"

  # If specific FRs are enforced, check only those
  if [[ -n "$ENFORCE_FRS" ]]; then
    check_specific_frs "$json" "$ENFORCE_FRS"
    return $?
  fi

  # Otherwise, check all FRs
  local status=$(echo "$json" | jq -r '.summary.status // "UNKNOWN"')

  if [[ "$status" == "FAIL" ]]; then
    return 1  # Validation failed
  fi

  if [[ "$FAIL_ON_WARN" == "true" && "$TOTAL_WARNINGS" -gt 0 ]]; then
    return 1  # Warnings detected in strict mode
  fi

  return 0  # All checks passed
}

################################################################################
# check_specific_frs: Check only specific FRs across all agents/flows
################################################################################
check_specific_frs() {
  local json="$1"
  local enforce_frs="$2"
  local fr_array=()

  # Parse comma-separated FR list
  IFS=',' read -ra fr_array <<< "$enforce_frs"

  # Check each FR in each agent and flow
  local any_failed=false
  local any_warned=false

  for fr in "${fr_array[@]}"; do
    fr="${fr// /}"  # Trim whitespace

    # Check agents
    local agent_failures=$(echo "$json" | jq -r ".agents[].checks[\"$fr\"]? | select(.status == \"fail\") | .status" 2>/dev/null | wc -l)
    local agent_warnings=$(echo "$json" | jq -r ".agents[].checks[\"$fr\"]? | select(.status == \"warn\") | .status" 2>/dev/null | wc -l)

    # Check flows
    local flow_failures=$(echo "$json" | jq -r ".flows[].checks[\"$fr\"]? | select(.status == \"fail\") | .status" 2>/dev/null | wc -l)
    local flow_warnings=$(echo "$json" | jq -r ".flows[].checks[\"$fr\"]? | select(.status == \"warn\") | .status" 2>/dev/null | wc -l)

    if [[ $((agent_failures + flow_failures)) -gt 0 ]]; then
      any_failed=true
    fi

    if [[ $((agent_warnings + flow_warnings)) -gt 0 ]]; then
      any_warned=true
    fi
  done

  if [[ "$any_failed" == "true" ]]; then
    return 1
  fi

  if [[ "$FAIL_ON_WARN" == "true" && "$any_warned" == "true" ]]; then
    return 1
  fi

  return 0
}

################################################################################
# main: Orchestrate validation flow
################################################################################
main() {
  parse_args "$@"

  # Check dependencies
  check_dependencies
  if [[ $? -ne 0 ]]; then
    return 2
  fi

  # Run validator
  local json
  json=$(run_validator)
  if [[ $? -ne 0 ]]; then
    return 2
  fi

  # Extract summary
  extract_summary "$json"

  # Print detailed issues if requested
  if [[ "$LIST_ISSUES" == "true" ]]; then
    list_agent_issues "$json"
    list_flow_issues "$json"
  fi

  # Check enforcement rules
  check_enforcement "$json"
  local enforcement_result=$?

  if [[ "$enforcement_result" -ne 0 ]]; then
    if [[ "$SUMMARY_ONLY" != "true" ]]; then
      echo ""
      echo -e "${RED}Validation failed. Review issues above.${NC}"
    fi
    return 1
  fi

  if [[ "$SUMMARY_ONLY" != "true" ]]; then
    echo "========================================"
  fi

  return 0
}

# Run main function with all arguments
main "$@"
exit $?
