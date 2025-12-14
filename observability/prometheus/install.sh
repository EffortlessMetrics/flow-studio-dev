#!/bin/bash
# Install Prometheus rules for selftest
#
# This script installs recording and alert rules for Prometheus.
# It supports both standalone Prometheus and Kubernetes deployments.
#
# Usage:
#   ./install.sh                    # Install to default location
#   ./install.sh --kubernetes       # Apply Kubernetes CRDs
#   ./install.sh --dry-run          # Show what would be done
#
# Environment Variables:
#   PROMETHEUS_CONFIG_DIR   - Directory for Prometheus rules (default: /etc/prometheus/rules)
#   PROMETHEUS_URL          - Prometheus URL for reload (default: http://localhost:9090)
#   KUBECONFIG              - Kubernetes config file (for --kubernetes)
#   NAMESPACE               - Kubernetes namespace (default: selftest)
#
# Reference: docs/designs/OBSERVABILITY_PLUGINS_DESIGN.md

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROM_CONFIG_DIR="${PROMETHEUS_CONFIG_DIR:-/etc/prometheus/rules}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
NAMESPACE="${NAMESPACE:-selftest}"
DRY_RUN=false
KUBERNETES=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Install Prometheus recording and alert rules for selftest.

Options:
    --kubernetes, -k    Apply Kubernetes CRDs instead of file copy
    --dry-run, -n       Show what would be done without making changes
    --help, -h          Show this help message

Environment Variables:
    PROMETHEUS_CONFIG_DIR   Directory for Prometheus rules (default: /etc/prometheus/rules)
    PROMETHEUS_URL          Prometheus URL for reload (default: http://localhost:9090)
    NAMESPACE               Kubernetes namespace (default: selftest)

Examples:
    # Install to standalone Prometheus
    ./install.sh

    # Install to Kubernetes with Prometheus Operator
    ./install.sh --kubernetes

    # Preview changes without installing
    ./install.sh --dry-run
EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --kubernetes|-k)
            KUBERNETES=true
            shift
            ;;
        --dry-run|-n)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate prerequisites
validate_files() {
    local missing=0

    if [[ ! -f "$SCRIPT_DIR/recording_rules.yaml" ]]; then
        log_error "Missing: $SCRIPT_DIR/recording_rules.yaml"
        missing=1
    fi

    if [[ ! -f "$SCRIPT_DIR/alert_rules.yaml" ]]; then
        log_error "Missing: $SCRIPT_DIR/alert_rules.yaml"
        missing=1
    fi

    if [[ $KUBERNETES == true ]] && [[ ! -f "$SCRIPT_DIR/../kubernetes/service_monitor.yaml" ]]; then
        log_error "Missing: $SCRIPT_DIR/../kubernetes/service_monitor.yaml"
        missing=1
    fi

    return $missing
}

# Install to standalone Prometheus
install_standalone() {
    log_info "Installing to standalone Prometheus..."

    # Create rules directory if needed
    if [[ ! -d "$PROM_CONFIG_DIR" ]]; then
        if [[ $DRY_RUN == true ]]; then
            log_info "[DRY-RUN] Would create directory: $PROM_CONFIG_DIR"
        else
            log_info "Creating directory: $PROM_CONFIG_DIR"
            sudo mkdir -p "$PROM_CONFIG_DIR"
        fi
    fi

    # Copy recording rules
    if [[ $DRY_RUN == true ]]; then
        log_info "[DRY-RUN] Would copy recording_rules.yaml to $PROM_CONFIG_DIR/selftest_recording.yaml"
    else
        log_info "Installing recording rules..."
        sudo cp "$SCRIPT_DIR/recording_rules.yaml" "$PROM_CONFIG_DIR/selftest_recording.yaml"
        log_info "Installed: $PROM_CONFIG_DIR/selftest_recording.yaml"
    fi

    # Copy alert rules
    if [[ $DRY_RUN == true ]]; then
        log_info "[DRY-RUN] Would copy alert_rules.yaml to $PROM_CONFIG_DIR/selftest_alerts.yaml"
    else
        log_info "Installing alert rules..."
        sudo cp "$SCRIPT_DIR/alert_rules.yaml" "$PROM_CONFIG_DIR/selftest_alerts.yaml"
        log_info "Installed: $PROM_CONFIG_DIR/selftest_alerts.yaml"
    fi

    # Reload Prometheus
    if [[ $DRY_RUN == true ]]; then
        log_info "[DRY-RUN] Would reload Prometheus at $PROMETHEUS_URL"
    else
        log_info "Reloading Prometheus..."
        if curl -sf -X POST "$PROMETHEUS_URL/-/reload" > /dev/null 2>&1; then
            log_info "Prometheus reloaded successfully"
        else
            log_warn "Could not reload Prometheus automatically"
            log_warn "Manual reload required: curl -X POST $PROMETHEUS_URL/-/reload"
            log_warn "Or restart Prometheus service"
        fi
    fi
}

# Install to Kubernetes
install_kubernetes() {
    log_info "Installing to Kubernetes..."

    # Check kubectl is available
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Please install kubectl first."
        exit 1
    fi

    # Create namespace if needed
    if [[ $DRY_RUN == true ]]; then
        log_info "[DRY-RUN] Would create namespace: $NAMESPACE"
    else
        if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
            log_info "Creating namespace: $NAMESPACE"
            kubectl create namespace "$NAMESPACE"
        fi
    fi

    # Apply ServiceMonitor and PrometheusRule
    if [[ $DRY_RUN == true ]]; then
        log_info "[DRY-RUN] Would apply: $SCRIPT_DIR/../kubernetes/service_monitor.yaml"
        kubectl apply -f "$SCRIPT_DIR/../kubernetes/service_monitor.yaml" -n "$NAMESPACE" --dry-run=client
    else
        log_info "Applying Kubernetes manifests..."
        kubectl apply -f "$SCRIPT_DIR/../kubernetes/service_monitor.yaml" -n "$NAMESPACE"
        log_info "Applied ServiceMonitor and PrometheusRule to namespace: $NAMESPACE"
    fi

    # Verify installation
    if [[ $DRY_RUN == false ]]; then
        log_info "Verifying installation..."
        if kubectl get servicemonitor selftest -n "$NAMESPACE" &> /dev/null; then
            log_info "ServiceMonitor 'selftest' created successfully"
        else
            log_warn "ServiceMonitor not found - Prometheus Operator may not be installed"
        fi

        if kubectl get prometheusrule selftest-rules -n "$NAMESPACE" &> /dev/null; then
            log_info "PrometheusRule 'selftest-rules' created successfully"
        else
            log_warn "PrometheusRule not found - Prometheus Operator may not be installed"
        fi
    fi
}

# Verify rules syntax
verify_rules() {
    log_info "Verifying rule syntax..."

    # Check if promtool is available
    if command -v promtool &> /dev/null; then
        if promtool check rules "$SCRIPT_DIR/recording_rules.yaml" && \
           promtool check rules "$SCRIPT_DIR/alert_rules.yaml"; then
            log_info "Rule syntax verification passed"
        else
            log_error "Rule syntax verification failed"
            return 1
        fi
    else
        log_warn "promtool not found - skipping syntax verification"
        log_warn "Install promtool for rule validation: https://prometheus.io/docs/prometheus/latest/installation/"
    fi
}

# Main
main() {
    log_info "Selftest Prometheus Rules Installer"
    log_info "===================================="

    # Validate files exist
    if ! validate_files; then
        log_error "Required files missing. Aborting."
        exit 1
    fi

    # Verify rules syntax
    verify_rules || true  # Don't fail if promtool not available

    # Install based on mode
    if [[ $KUBERNETES == true ]]; then
        install_kubernetes
    else
        install_standalone
    fi

    log_info "Installation complete!"

    if [[ $DRY_RUN == true ]]; then
        log_info "(This was a dry run - no changes were made)"
    fi
}

main "$@"
