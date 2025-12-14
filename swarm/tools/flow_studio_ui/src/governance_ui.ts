// swarm/tools/flow_studio_ui/src/governance_ui.ts
// Governance UI for Flow Studio
//
// This module handles:
// - Loading governance and validation status
// - Governance badge and overlay rendering
// - Validation issue counts and flow list badges
// - Graph node governance overlays
// - Governance details panel

import { state } from "./state.js";
import { Api } from "./api.js";
import { escapeHtml } from "./utils.js";
import type {
  NodeData,
  FRCheck,
  GovernanceStatus,
  NodeGovernanceInfo,
  ResolutionHint,
  NormalizedSelftestStatus,
  LegacySelftestStatus,
} from "./domain.js";

// ============================================================================
// Status Normalization
// ============================================================================

/**
 * Normalize legacy selftest status (GREEN/YELLOW/RED/UNKNOWN) to the 4-state model.
 * This provides backward compatibility with API responses while using the new vocabulary.
 *
 * Mapping:
 * - GREEN -> ok
 * - YELLOW -> warning
 * - RED -> error
 * - UNKNOWN -> unknown
 * - Already normalized values pass through unchanged
 */
function normalizeSelftestStatus(status: string): NormalizedSelftestStatus {
  const legacyMap: Record<LegacySelftestStatus, NormalizedSelftestStatus> = {
    GREEN: "ok",
    YELLOW: "warning",
    RED: "error",
    UNKNOWN: "unknown",
  };

  // Check if it's a legacy value
  if (status in legacyMap) {
    return legacyMap[status as LegacySelftestStatus];
  }

  // Check if it's already a normalized value
  const normalizedValues: NormalizedSelftestStatus[] = ["ok", "warning", "error", "unknown"];
  if (normalizedValues.includes(status as NormalizedSelftestStatus)) {
    return status as NormalizedSelftestStatus;
  }

  // Default to unknown for any unexpected value
  return "unknown";
}

/** Icon mapping for the 4-state model */
const selftestStatusIconMap: Record<NormalizedSelftestStatus, string> = {
  ok: "\u2705",      // Checkmark
  warning: "\u26a0\ufe0f",  // Warning sign
  error: "\u274c",   // X mark
  unknown: "\u2022", // Bullet (dot)
};

/** Text mapping for the 4-state model */
const selftestStatusTextMap: Record<NormalizedSelftestStatus, string> = {
  ok: "Healthy",
  warning: "Degraded",
  error: "Issues",
  unknown: "Unknown",
};

/** Background color mapping for the 4-state model */
const selftestStatusBgMap: Record<NormalizedSelftestStatus, string> = {
  ok: "#dcfce7",      // Green
  warning: "#fef3c7", // Yellow
  error: "#fee2e2",   // Red
  unknown: "#f3f4f6", // Gray
};

// ============================================================================
// Governance Status Loading
// ============================================================================

/**
 * Load governance status from API and update UI elements.
 */
export async function loadGovernanceStatus(): Promise<void> {
  const iconEl = document.getElementById("governance-icon");
  const textEl = document.getElementById("governance-text");
  const badgeEl = document.getElementById("governance-badge");

  try {
    const data = await Api.getGovernanceStatus();
    state.governanceStatus = data;

    // Determine overall status using the 4-state model
    const kernel = data.governance?.kernel?.status || "unknown";
    const rawSelftest = data.governance?.selftest?.status || "unknown";
    const selftestStatus = normalizeSelftestStatus(rawSelftest);

    // Derive combined status: kernel healthy + selftest status
    let combinedStatus: NormalizedSelftestStatus;
    if (kernel === "HEALTHY") {
      combinedStatus = selftestStatus;
    } else if (kernel === "unknown") {
      combinedStatus = "unknown";
    } else {
      // kernel is BROKEN or any other non-healthy state
      combinedStatus = "error";
    }

    const icon = selftestStatusIconMap[combinedStatus];
    const text = selftestStatusTextMap[combinedStatus];
    const bgColor = selftestStatusBgMap[combinedStatus];

    if (iconEl) iconEl.textContent = icon;
    if (textEl) textEl.textContent = text;
    if (badgeEl) (badgeEl as HTMLElement).style.background = bgColor;

    // Also load validation data for overlays
    try {
      const valData = await Api.getValidationData();
      state.validationData = valData;
      updateValidationIssuesCount();
      updateFlowListGovernance();
    } catch (valErr) {
      console.error("Failed to load validation data", valErr);
      state.validationData = null;
    }
  } catch (err) {
    console.error("Failed to load governance status", err);
    if (iconEl) iconEl.textContent = selftestStatusIconMap.unknown;
    if (textEl) textEl.textContent = selftestStatusTextMap.unknown;
    if (badgeEl) (badgeEl as HTMLElement).style.background = selftestStatusBgMap.unknown;
  }
}

// ============================================================================
// Validation Issues Count
// ============================================================================

/**
 * Update the issues count badge in the header.
 */
export function updateValidationIssuesCount(): void {
  const countEl = document.getElementById("governance-issues-count");
  if (!countEl) return;

  const totalIssues = (state.validationData?.summary?.agents_with_issues?.length || 0) +
                      (state.validationData?.summary?.flows_with_issues?.length || 0) +
                      (state.validationData?.summary?.steps_with_issues?.length || 0);

  if (totalIssues > 0) {
    countEl.textContent = String(totalIssues);
    (countEl as HTMLElement).style.display = "inline";
  } else {
    (countEl as HTMLElement).style.display = "none";
  }
}

// ============================================================================
// Flow List Governance Badges
// ============================================================================

/**
 * Update flow list items with governance warning badges.
 */
export function updateFlowListGovernance(): void {
  if (!state.validationData) return;

  const flowsWithIssues = state.validationData.summary?.flows_with_issues || [];

  document.querySelectorAll(".flow-item").forEach(item => {
    const flowKey = (item as HTMLElement).dataset.key;
    const existingBadge = item.querySelector(".flow-governance-badge");
    if (existingBadge) existingBadge.remove();

    if (flowKey && flowsWithIssues.includes(flowKey)) {
      const badge = document.createElement("span");
      badge.className = "flow-governance-badge has-issues";
      badge.innerHTML = "\u26a0\ufe0f";
      badge.title = "This flow has governance issues";
      item.appendChild(badge);
    }
  });
}

// ============================================================================
// Graph Governance Overlay
// ============================================================================

/**
 * Toggle governance overlay on graph nodes.
 */
export function toggleGovernanceOverlay(enabled: boolean): void {
  state.governanceOverlayEnabled = enabled;

  const toggle = document.getElementById("governance-toggle");
  if (toggle) toggle.classList.toggle("active", enabled);

  updateGraphGovernanceOverlay();

  // Also apply FR status badges when overlay enabled
  if (enabled) {
    applyFRStatusToNodes();
  }
}

/**
 * Update graph nodes with governance issue highlighting.
 */
export function updateGraphGovernanceOverlay(): void {
  if (!state.cy || !state.validationData) return;

  const agentsWithIssues = state.validationData.summary?.agents_with_issues || [];
  const stepsWithIssues = state.validationData.summary?.steps_with_issues || [];

  state.cy.nodes().forEach(node => {
    const nodeData = node.data() as NodeData;
    let hasIssue = false;

    if (nodeData.type === "agent" && nodeData.agent_key && agentsWithIssues.includes(nodeData.agent_key)) {
      hasIssue = true;
    }
    if (nodeData.type === "step") {
      const stepKey = nodeData.flow + ":" + nodeData.step_id;
      if (stepsWithIssues.includes(stepKey)) hasIssue = true;
    }

    // Use style method with type assertion
    const styleNode = node as unknown as { style(obj: Record<string, unknown>): void };
    if (state.governanceOverlayEnabled && hasIssue) {
      styleNode.style({
        "border-width": 3,
        "border-color": "#f59e0b",
        "border-style": "solid"
      });
    } else {
      styleNode.style({
        "border-width": nodeData.type === "step" ? 2 : 1,
        "border-color": nodeData.type === "step" ? "#0d9488" : "#d1d5db",
        "border-style": "solid"
      });
    }
  });
}

/**
 * Apply FR status classes to graph nodes for visual feedback.
 */
export function applyFRStatusToNodes(): void {
  if (!state.cy || !state.validationData || !state.governanceOverlayEnabled) return;

  const agentsWithIssues = state.validationData.summary?.agents_with_issues || [];
  const failedAgents: string[] = [];
  const warnAgents: string[] = [];

  // Determine which agents have fail vs warn status
  agentsWithIssues.forEach(agentKey => {
    const agentData = state.validationData?.agents?.[agentKey];
    if (agentData && agentData.checks) {
      const hasFailures = Object.values(agentData.checks).some(c => c.status === 'fail');
      if (hasFailures) {
        failedAgents.push(agentKey);
      } else {
        warnAgents.push(agentKey);
      }
    }
  });

  // Apply FR status classes
  state.cy.nodes('[type = "agent"]').forEach(node => {
    const agentKey = node.data('agent_key') as string;
    const classNode = node as unknown as {
      removeClass(cls: string): void;
      addClass(cls: string): void;
    };
    classNode.removeClass('fr-status-fail fr-status-warn fr-status-pass');

    if (failedAgents.includes(agentKey)) {
      classNode.addClass('fr-status-fail');
    } else if (warnAgents.includes(agentKey)) {
      classNode.addClass('fr-status-warn');
    }
  });
}

// ============================================================================
// Node Governance Info
// ============================================================================

/**
 * Get governance info for a specific node.
 */
export function getNodeGovernanceInfo(nodeData: NodeData): NodeGovernanceInfo | null {
  if (!state.validationData) return null;

  if (nodeData.type === "agent" && nodeData.agent_key) {
    const agentData = state.validationData.agents?.[nodeData.agent_key];
    if (agentData && agentData.has_issues) return agentData;
  } else if (nodeData.type === "step" && nodeData.step_id && nodeData.flow) {
    const stepKey = nodeData.flow + ":" + nodeData.step_id;
    const stepData = (state.validationData as unknown as { steps?: Record<string, NodeGovernanceInfo> }).steps?.[stepKey];
    if (stepData && stepData.has_issues) return stepData;
  }

  return null;
}

/**
 * Get FR status badges HTML for a node.
 */
export function getNodeFRBadges(nodeData: NodeData): string | null {
  if (!state.validationData) return null;

  if (nodeData.type === "agent" && nodeData.agent_key) {
    const agentData = state.validationData.agents?.[nodeData.agent_key];
    if (agentData && agentData.checks) {
      return formatFRBadges(agentData.checks);
    }
  }

  return null;
}

/**
 * Format FR checks as HTML badges.
 */
export function formatFRBadges(checks: Record<string, FRCheck>): string {
  if (!checks) return '<div class="fr-none">No FR data</div>';

  const badges = Object.entries(checks)
    .map(([fr, check]) => {
      const status = check.status || 'unknown';
      const message = check.message || fr;
      const title = message ? ` title="${escapeHtml(message)}"` : '';
      return `<span class="fr-badge fr-${status}"${title}>${fr}</span>`;
    })
    .join('');

  return `<div class="fr-badges">${badges}</div>`;
}

// ============================================================================
// Governance Section Rendering
// ============================================================================

/**
 * Render governance section in details panel.
 */
export function renderGovernanceSection(container: HTMLElement, govInfo: NodeGovernanceInfo): void {
  if (!govInfo || !govInfo.checks) return;

  const section = document.createElement("div");
  section.className = "governance-section" + (govInfo.has_issues ? "" : " healthy");

  const h3 = document.createElement("h3");
  h3.innerHTML = govInfo.has_issues ? "\u26a0\ufe0f Governance" : "\u2705 Governance";
  section.appendChild(h3);

  Object.entries(govInfo.checks || {}).forEach(([checkId, check]) => {
    const checkDiv = document.createElement("div");
    checkDiv.className = "governance-check";

    const nameSpan = document.createElement("span");
    nameSpan.className = "governance-check-name";
    nameSpan.textContent = checkId;

    const statusSpan = document.createElement("span");
    statusSpan.className = "governance-check-status " + check.status;
    const statusIcon = check.status === "pass" ? "\u2705" : check.status === "fail" ? "\u274c" : "\u26a0\ufe0f";
    statusSpan.innerHTML = statusIcon + " " + check.status.toUpperCase();

    checkDiv.appendChild(nameSpan);
    checkDiv.appendChild(statusSpan);
    section.appendChild(checkDiv);

    if (check.message && check.status !== "pass") {
      const msgDiv = document.createElement("div");
      msgDiv.className = "governance-fix";
      msgDiv.textContent = check.message;
      section.appendChild(msgDiv);
    }

    if (check.fix && check.status === "fail") {
      const fixDiv = document.createElement("div");
      fixDiv.className = "governance-fix";
      fixDiv.textContent = "Fix: " + check.fix;
      section.appendChild(fixDiv);
    }
  });

  container.appendChild(section);
}

// ============================================================================
// Resolution Hints
// ============================================================================

interface ResolutionPattern {
  type: "failure" | "advisory" | "workaround";
  root_cause: string;
  command: string;
  docs: string;
}

/**
 * Generate resolution hints based on governance status.
 */
export function generateResolutionHints(governanceStatus: GovernanceStatus): ResolutionHint[] {
  const hints: ResolutionHint[] = [];
  const failedSteps = governanceStatus?.governance?.selftest?.failed_steps || [];
  const degradedSteps = governanceStatus?.governance?.selftest?.degraded_steps || [];

  const patterns: Record<string, ResolutionPattern> = {
    "core-checks": {
      type: "failure",
      root_cause: "Python lint or compile errors in swarm/ directory",
      command: "ruff check swarm/ && python -m compileall -q swarm/",
      docs: "docs/SELFTEST_SYSTEM.md"
    },
    "skills-governance": {
      type: "failure",
      root_cause: "Invalid or missing skill YAML frontmatter",
      command: "uv run swarm/tools/validate_swarm.py --check-skills",
      docs: "CLAUDE.md \u00a7 Skills"
    },
    "agents-governance": {
      type: "failure",
      root_cause: "Agent bijection, color, or frontmatter validation failed",
      command: "uv run swarm/tools/validate_swarm.py --check-agents",
      docs: "CLAUDE.md \u00a7 Agent Ops"
    },
    "bdd": {
      type: "advisory",
      root_cause: "BDD feature files missing or malformed",
      command: "find features/ -name '*.feature' | head",
      docs: "docs/SELFTEST_SYSTEM.md"
    },
    "ac-status": {
      type: "advisory",
      root_cause: "Acceptance criteria tracking incomplete",
      command: "uv run swarm/tools/selftest.py --step ac-status",
      docs: "docs/SELFTEST_SYSTEM.md"
    },
    "policy-tests": {
      type: "failure",
      root_cause: "OPA policy validation failed",
      command: "make policy-tests",
      docs: "swarm/policies/README.md"
    },
    "flowstudio-smoke": {
      type: "workaround",
      root_cause: "Flow Studio smoke tests failed (may be missing deps)",
      command: "uv run pytest tests/test_flow_studio_fastapi_smoke.py -v",
      docs: "swarm/tools/flow_studio.py"
    }
  };

  failedSteps.forEach(step => {
    const pattern = patterns[step];
    if (pattern) {
      hints.push({
        type: "failure",
        step: step,
        root_cause: pattern.root_cause,
        command: pattern.command,
        docs: pattern.docs
      });
    } else {
      hints.push({
        type: "failure",
        step: step,
        root_cause: "Check selftest output for details",
        command: `uv run swarm/tools/selftest.py --step ${step}`,
        docs: "docs/SELFTEST_SYSTEM.md"
      });
    }
  });

  degradedSteps.forEach(step => {
    const pattern = patterns[step];
    if (pattern) {
      hints.push({
        type: "advisory",
        step: step,
        root_cause: pattern.root_cause + " (non-blocking in degraded mode)",
        command: pattern.command,
        docs: pattern.docs
      });
    }
  });

  return hints;
}

/**
 * Render resolution hints in the details panel.
 */
export function renderResolutionHints(container: HTMLElement, governanceStatus: GovernanceStatus): void {
  const hints = generateResolutionHints(governanceStatus);

  if (hints.length === 0) {
    return;
  }

  const section = document.createElement("div");
  section.style.marginTop = "16px";

  const header = document.createElement("div");
  header.className = "kv-label";
  header.textContent = "Resolution Hints";
  section.appendChild(header);

  hints.forEach(hint => {
    const card = document.createElement("div");
    const bgColors: Record<string, string> = {
      failure: "#fee",
      advisory: "#fff3cd",
      workaround: "#e0f2fe"
    };
    card.className = "fs-text-sm";
    card.style.background = bgColors[hint.type] || "#f9fafb";
    card.style.border = "1px solid #e5e7eb";
    card.style.borderRadius = "4px";
    card.style.padding = "8px";
    card.style.marginTop = "8px";

    const typeLabel = document.createElement("div");
    typeLabel.style.fontWeight = "600";
    typeLabel.style.marginBottom = "4px";
    const allowedHintTypes = ["failure", "advisory", "workaround"];
    const safeType = allowedHintTypes.includes(hint.type) ? hint.type : "unknown";
    typeLabel.textContent = `${safeType.toUpperCase()}: ${hint.step || ''}`;
    card.appendChild(typeLabel);

    const rootCause = document.createElement("div");
    rootCause.style.marginBottom = "4px";
    rootCause.innerHTML = `<strong>Root Cause:</strong> ${escapeHtml(hint.root_cause || '')}`;
    card.appendChild(rootCause);

    const commandDiv = document.createElement("div");
    commandDiv.style.display = "flex";
    commandDiv.style.alignItems = "center";
    commandDiv.style.gap = "8px";
    commandDiv.style.marginBottom = "4px";
    commandDiv.innerHTML = `<strong>Command:</strong> <span class="mono">${escapeHtml(hint.command || '')}</span>`;

    const copyBtn = document.createElement("button");
    copyBtn.textContent = "Copy";
    copyBtn.className = "fs-text-xs";
    copyBtn.style.padding = "2px 6px";
    copyBtn.style.cursor = "pointer";
    copyBtn.style.border = "1px solid #d1d5db";
    copyBtn.style.background = "#fff";
    copyBtn.style.borderRadius = "3px";
    copyBtn.onclick = () => {
      navigator.clipboard.writeText(hint.command).then(() => {
        copyBtn.textContent = "Copied!";
        setTimeout(() => copyBtn.textContent = "Copy", 2000);
      }).catch((err) => {
        console.error("Failed to copy command:", err);
        copyBtn.textContent = "Failed";
        setTimeout(() => copyBtn.textContent = "Copy", 2000);
      });
    };
    commandDiv.appendChild(copyBtn);
    card.appendChild(commandDiv);

    const docsDiv = document.createElement("div");
    docsDiv.className = "muted";
    docsDiv.innerHTML = `<strong>Docs:</strong> <span class="mono">${escapeHtml(hint.docs || '')}</span>`;
    card.appendChild(docsDiv);

    section.appendChild(card);
  });

  container.appendChild(section);
}

// ============================================================================
// Selftest Plan Rendering (for governance details)
// ============================================================================

/**
 * Render selftest plan table HTML.
 */
export async function renderSelftestPlan(): Promise<string> {
  try {
    const plan = await Api.getSelftestPlan();

    const tierColors: Record<string, string> = {
      kernel: "#dc2626",
      governance: "#d97706",
      optional: "#6b7280"
    };

    let stepsHtml = '<table class="artifact-table fs-text-sm">';
    stepsHtml += '<thead><tr><th>Step</th><th>Tier</th><th>Severity</th><th>Category</th><th>Dependencies</th></tr></thead><tbody>';

    plan.steps.forEach(step => {
      const tierColor = tierColors[step.tier] || "#6b7280";
      const failedSteps = (state.governanceStatus?.governance?.selftest?.failed_steps || []);
      const degradedSteps = (state.governanceStatus?.governance?.selftest?.degraded_steps || []);
      const isFailed = failedSteps.includes(step.id);
      const isDegraded = degradedSteps.includes(step.id);
      const statusIcon = isFailed ? "\u274c" : isDegraded ? "\u26a0\ufe0f" : "\u2705";
      const deps = step.depends_on.length ? step.depends_on.join(", ") : "\u2014";

      stepsHtml += `<tr style="${isFailed ? 'background: #fee;' : isDegraded ? 'background: #fff3cd;' : ''}">
        <td>${statusIcon} <span class="mono">${escapeHtml(step.id)}</span></td>
        <td><span style="color: ${tierColor}; font-weight: 600;">${escapeHtml(step.tier)}</span></td>
        <td>${escapeHtml(step.severity)}</td>
        <td>${escapeHtml(step.category)}</td>
        <td class="muted">${escapeHtml(deps)}</td>
      </tr>`;
    });

    stepsHtml += '</tbody></table>';

    const summary = plan.summary;
    const commands = `
      <div style="margin-top: 12px;">
        <div class="kv-label">Quick Commands</div>
        <button class="fs-text-sm" onclick="navigator.clipboard.writeText('make selftest')" style="margin: 4px; padding: 4px 8px; cursor: pointer; border: 1px solid #d1d5db; background: #f3f4f6; border-radius: 3px;">Copy: make selftest</button>
        <button class="fs-text-sm" onclick="navigator.clipboard.writeText('make kernel-smoke')" style="margin: 4px; padding: 4px 8px; cursor: pointer; border: 1px solid #d1d5db; background: #f3f4f6; border-radius: 3px;">Copy: make kernel-smoke</button>
        <button class="fs-text-sm" onclick="navigator.clipboard.writeText('make selftest-doctor')" style="margin: 4px; padding: 4px 8px; cursor: pointer; border: 1px solid #d1d5db; background: #f3f4f6; border-radius: 3px;">Copy: make selftest-doctor</button>
      </div>
    `;

    return `
      <div class="kv-label">Selftest Plan (${summary.total} steps)</div>
      <div class="fs-text-sm" style="margin-bottom: 8px;">
        <span style="color: ${tierColors.kernel}; font-weight: 600;">Kernel: ${summary.by_tier.kernel}</span> |
        <span style="color: ${tierColors.governance}; font-weight: 600;">Governance: ${summary.by_tier.governance}</span> |
        <span style="color: ${tierColors.optional};">Optional: ${summary.by_tier.optional}</span>
      </div>
      ${stepsHtml}
      ${commands}
      <div class="muted fs-text-xs" style="margin-top: 8px;">
        \ud83d\udcd6 Docs: <span class="mono">docs/SELFTEST_SYSTEM.md</span>
      </div>
    `;
  } catch (error) {
    console.error("Failed to load selftest plan:", error);
    return `<div class="muted">Failed to load selftest plan: ${escapeHtml((error as Error).message)}</div>`;
  }
}

/**
 * Show full governance details in the details panel.
 */
export function showGovernanceDetails(): void {
  const detailsEl = document.getElementById("details");
  if (!detailsEl) return;

  detailsEl.innerHTML = "";

  const h2 = document.createElement("h2");
  h2.textContent = "Governance Status";

  if (!state.governanceStatus) {
    const msg = document.createElement("div");
    msg.className = "muted";
    msg.textContent = "Governance status not available. Run 'make selftest' to generate status.";
    detailsEl.appendChild(h2);
    detailsEl.appendChild(msg);
    return;
  }

  const gov = state.governanceStatus.governance || { kernel: { status: "unknown" }, selftest: { status: "unknown", mode: "unknown", kernel_ok: false, governance_ok: false, optional_ok: false, failed_steps: [], degraded_steps: [] } };
  const kernel = gov.kernel || { status: "unknown" };
  const selftest = gov.selftest || { status: "unknown", mode: "unknown", kernel_ok: false, governance_ok: false, optional_ok: false, failed_steps: [], degraded_steps: [] };

  const allowedKernelStatuses = ["HEALTHY", "BROKEN", "unknown"];
  const rawKernelStatus = kernel.status || "unknown";
  const kernelStatus = allowedKernelStatuses.includes(rawKernelStatus) ? rawKernelStatus : "unknown";
  const kernelIcon = kernelStatus === "HEALTHY" ? "\u2705" : "\u274c";

  // Normalize selftest status to the 4-state model (handles both legacy and new formats)
  const rawSelftestStatus = selftest.status || "unknown";
  const normalizedStatus = normalizeSelftestStatus(rawSelftestStatus);
  const selftestIcon = selftestStatusIconMap[normalizedStatus];
  const selftestDisplayText = selftestStatusTextMap[normalizedStatus];

  const allowedModes = ["strict", "degraded", "kernel-only", "unknown"];
  const rawMode = selftest.mode || "unknown";
  const safeMode = allowedModes.includes(rawMode) ? rawMode : "unknown";

  const content = document.createElement("div");
  content.innerHTML = `
    <div class="kv-label">Kernel</div>
    <div style="font-weight: 600;">${kernelIcon} ${escapeHtml(kernelStatus)}</div>
    ${kernel.error ? `<div class="muted fs-text-sm">${escapeHtml(kernel.error)}</div>` : ""}

    <div class="kv-label">Selftest</div>
    <div style="font-weight: 600;">${selftestIcon} ${escapeHtml(selftestDisplayText)}</div>
    <div class="fs-text-sm fs-text-muted">
      Mode: ${escapeHtml(safeMode)}<br/>
      Kernel OK: ${selftest.kernel_ok ? "\u2705" : "\u274c"}<br/>
      Governance OK: ${selftest.governance_ok ? "\u2705" : "\u274c"}<br/>
      Optional OK: ${selftest.optional_ok ? "\u2705" : "\u274c"}
    </div>

    ${selftest.failed_steps?.length ? `
      <div class="kv-label" style="margin-top: 12px;">Failed Steps (Critical)</div>
      <div class="fs-text-sm">
        ${selftest.failed_steps.map(s => `<span class="mono" style="color: #dc2626;">${escapeHtml(s)}</span>`).join(", ")}
      </div>
    ` : ""}
    ${selftest.degraded_steps?.length ? `
      <div class="kv-label">Degraded Steps (Warning/Info)</div>
      <div class="fs-text-sm">
        ${selftest.degraded_steps.map(s => `<span class="mono" style="color: #d97706;">${escapeHtml(s)}</span>`).join(", ")}
      </div>
    ` : ""}

    <div class="kv-label" style="margin-top: 12px;">Stats</div>
    <table class="artifact-table">
      <tr><td>Critical</td><td class="status-complete">${selftest.critical_passed || 0} passed</td><td class="status-missing">${selftest.critical_failed || 0} failed</td></tr>
      <tr><td>Warning</td><td class="status-complete">${selftest.warning_passed || 0} passed</td><td class="status-partial">${selftest.warning_failed || 0} failed</td></tr>
      <tr><td>Info</td><td class="status-complete">${selftest.info_passed || 0} passed</td><td class="status-na">${selftest.info_failed || 0} failed</td></tr>
    </table>

    <div class="muted" style="margin-top: 16px;">
      <strong>To refresh:</strong>
      <pre class="mono">make selftest</pre>
      Last checked: ${escapeHtml(state.governanceStatus.timestamp || "unknown")}
    </div>
  `;

  detailsEl.appendChild(h2);
  detailsEl.appendChild(content);

  renderResolutionHints(detailsEl, state.governanceStatus);
}
