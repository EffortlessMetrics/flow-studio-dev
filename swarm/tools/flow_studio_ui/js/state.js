// swarm/tools/flow_studio_ui/src/state.ts
// Centralized state management for Flow Studio
/**
 * Application state object. All mutable state lives here.
 */
export const state = {
    // Cytoscape graph instance
    cy: null,
    // Current selection state
    currentFlowKey: null,
    currentRunId: null,
    compareRunId: null,
    // Node selection (unified selection model)
    selectedNodeId: null,
    selectedNodeType: null,
    // Cached data from API
    runStatus: {}, // /api/runs/:id/summary
    comparisonData: null, // /api/runs/compare
    availableRuns: [], // /api/runs list
    // Governance state
    governanceStatus: null,
    validationData: null,
    governanceOverlayEnabled: false,
    // UI mode state
    currentMode: "author", // "author" | "operator"
    currentViewMode: "agents", // "agents" | "artifacts"
    // Search state
    searchDebounceTimer: null,
    searchSelectedIndex: -1,
    searchResults: [],
    // Navigation state
    currentStepIndex: -1,
    // Selftest state
    selftestPlan: null,
    selftestPlanCache: null
};
/**
 * Status icons used throughout the app
 */
export const STATUS_ICONS = {
    done: "\u2705", // Green checkmark
    in_progress: "\u23f3", // Hourglass
    not_started: "\u2014", // Em dash
    complete: "\u2705",
    partial: "\u26a0\ufe0f", // Warning
    missing: "\u274c", // Red X
    "n/a": "\u2014"
};
/**
 * Flow health status metadata for sidebar display.
 * Maps FlowHealthStatus to icon and tooltip text.
 */
export const FLOW_STATUS_META = {
    ok: {
        icon: "\u2705", // Green checkmark
        tooltip: "All required checks passed for this flow.",
    },
    warning: {
        icon: "\u26a0\ufe0f", // Warning sign
        tooltip: "Some non-blocking checks failed or artifacts are missing.",
    },
    error: {
        icon: "\u274c", // Red X
        tooltip: "Blocking failures or required artifacts are missing.",
    },
    unknown: {
        icon: "\u2022", // Bullet dot
        tooltip: "No run data for this flow.",
    },
};
/**
 * Flow key order - re-exported from generated constants
 */
export { FLOW_KEYS } from "./flow_constants.js";
// ============================================================================
// State setters (optional helpers for common operations)
// ============================================================================
/**
 * Set the current UI mode
 */
export function setMode(mode) {
    state.currentMode = mode;
}
/**
 * Set the current view mode
 */
export function setViewMode(view) {
    state.currentViewMode = view;
}
/**
 * Set the current run ID
 */
export function setCurrentRun(runId) {
    state.currentRunId = runId;
}
/**
 * Set the current flow key
 */
export function setCurrentFlow(flowKey) {
    state.currentFlowKey = flowKey;
}
/**
 * Set the comparison run ID
 */
export function setCompareRun(runId) {
    state.compareRunId = runId;
}
/**
 * Toggle the governance overlay
 */
export function setGovernanceOverlay(enabled) {
    state.governanceOverlayEnabled = enabled;
}
/**
 * Set the selected node
 */
export function setSelectedNode(nodeId, nodeType) {
    state.selectedNodeId = nodeId;
    state.selectedNodeType = nodeType;
}
/**
 * Clear the selected node
 */
export function clearSelectedNode() {
    state.selectedNodeId = null;
    state.selectedNodeType = null;
}
