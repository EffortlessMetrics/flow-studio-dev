// swarm/tools/flow_studio_ui/src/graph_outline.ts
// Semantic graph companion for accessibility and LLM agents
//
// This module provides:
// - getCurrentGraphState(): Export graph state as JSON (for snapshots/testing)
// - renderFlowOutline(): DOM companion tree mirroring the graph structure
//
// The DOM outline provides ARIA tree semantics for screen readers and
// a text representation for LLM agents that can't "see" the Cytoscape canvas.
import { state, FLOW_KEYS } from "./state.js";
// ============================================================================
// Graph State Export
// ============================================================================
/**
 * Get the current graph state as a JSON-serializable object.
 * Useful for snapshots, tests, and LLM agent context.
 */
export function getCurrentGraphState() {
    if (!state.currentFlowKey || !state.cy)
        return null;
    // Sort nodes by ID for deterministic output
    const nodes = state.cy.nodes()
        .map((node) => ({
        id: node.id(),
        type: node.data("type"),
        label: node.data("label"),
        flow: node.data("flow"),
        step_id: node.data("step_id") || null,
        order: node.data("order") || null,
        color: node.data("color") || null,
        status: node.data("status") || null
    }))
        .sort((a, b) => a.id.localeCompare(b.id));
    // Sort edges by ID for deterministic output
    const edges = state.cy.edges()
        .map((edge) => ({
        id: edge.id(),
        type: edge.data("type"),
        source: edge.data("source"),
        target: edge.data("target")
    }))
        .sort((a, b) => a.id.localeCompare(b.id));
    return {
        version: "flow_graph.v1",
        flow_key: state.currentFlowKey,
        run_id: state.currentRunId || null,
        view_mode: state.currentViewMode,
        timestamp: new Date().toISOString(),
        nodes,
        edges
    };
}
// ============================================================================
// DOM Outline Rendering
// ============================================================================
/**
 * Render a semantic DOM tree mirroring the graph structure.
 * This provides:
 * - ARIA tree semantics for screen readers
 * - Text representation for LLM agents
 * - Stable selectors for testing (data-uiid)
 *
 * The outline is rendered into #flow-outline (visually hidden but accessible).
 */
export function renderFlowOutline() {
    const outline = document.getElementById("flow-outline");
    if (!outline)
        return;
    const graphState = getCurrentGraphState();
    if (!graphState) {
        outline.innerHTML = "";
        outline.setAttribute("aria-busy", "false");
        return;
    }
    outline.setAttribute("aria-busy", "true");
    outline.innerHTML = "";
    // Group nodes by type
    const steps = graphState.nodes
        .filter(n => n.type === "step")
        .sort((a, b) => (a.order || 0) - (b.order || 0));
    const agents = graphState.nodes.filter(n => n.type === "agent");
    const artifacts = graphState.nodes.filter(n => n.type === "artifact");
    // Create flow info
    const flowInfo = document.createElement("div");
    flowInfo.setAttribute("role", "treeitem");
    flowInfo.setAttribute("aria-level", "1");
    flowInfo.dataset.uiid = `flow_studio.canvas.outline.flow:${graphState.flow_key}`;
    flowInfo.textContent = `Flow: ${graphState.flow_key} (${steps.length} steps, ${agents.length} agents)`;
    outline.appendChild(flowInfo);
    // Create steps group
    if (steps.length > 0) {
        const stepsGroup = document.createElement("div");
        stepsGroup.setAttribute("role", "group");
        stepsGroup.setAttribute("aria-label", "Steps");
        stepsGroup.dataset.uiid = "flow_studio.canvas.outline.steps";
        steps.forEach((step, index) => {
            const stepItem = document.createElement("div");
            stepItem.setAttribute("role", "treeitem");
            stepItem.setAttribute("aria-level", "2");
            stepItem.dataset.uiid = `flow_studio.canvas.outline.step:${step.id}`;
            stepItem.textContent = `${index + 1}. ${step.label || step.step_id || step.id}`;
            // Find agents connected to this step
            const connectedAgentIds = graphState.edges
                .filter(e => e.source === step.id && e.type === "step-agent")
                .map(e => e.target);
            const connectedAgents = agents.filter(a => connectedAgentIds.includes(a.id));
            if (connectedAgents.length > 0) {
                const agentsList = document.createElement("div");
                agentsList.setAttribute("role", "group");
                agentsList.setAttribute("aria-label", `Agents for ${step.label}`);
                connectedAgents.forEach(agent => {
                    const agentItem = document.createElement("div");
                    agentItem.setAttribute("role", "treeitem");
                    agentItem.setAttribute("aria-level", "3");
                    agentItem.dataset.uiid = `flow_studio.canvas.outline.agent:${agent.id}`;
                    agentItem.textContent = `→ ${agent.label || agent.id}`;
                    agentsList.appendChild(agentItem);
                });
                stepItem.appendChild(agentsList);
            }
            // Find artifacts connected to this step (if in artifacts view)
            const connectedArtifactIds = graphState.edges
                .filter(e => e.source === step.id && e.type === "step-artifact")
                .map(e => e.target);
            const connectedArtifacts = artifacts.filter(a => connectedArtifactIds.includes(a.id));
            if (connectedArtifacts.length > 0) {
                const artifactsList = document.createElement("div");
                artifactsList.setAttribute("role", "group");
                artifactsList.setAttribute("aria-label", `Artifacts for ${step.label}`);
                connectedArtifacts.forEach(artifact => {
                    const artifactItem = document.createElement("div");
                    artifactItem.setAttribute("role", "treeitem");
                    artifactItem.setAttribute("aria-level", "3");
                    artifactItem.dataset.uiid = `flow_studio.canvas.outline.artifact:${artifact.id}`;
                    const statusIndicator = artifact.status === "present" ? "✓"
                        : artifact.status === "missing" ? "✗"
                            : "○";
                    artifactItem.textContent = `${statusIndicator} ${artifact.label || artifact.id}`;
                    artifactsList.appendChild(artifactItem);
                });
                stepItem.appendChild(artifactsList);
            }
            stepsGroup.appendChild(stepItem);
        });
        outline.appendChild(stepsGroup);
    }
    outline.setAttribute("aria-busy", "false");
}
// ============================================================================
// Debug Export (development only)
// ============================================================================
// Expose for browser console debugging (development only)
if (typeof window !== "undefined") {
    window.__flowStudioGraph = {
        getCurrentGraphState,
        renderFlowOutline
    };
}
