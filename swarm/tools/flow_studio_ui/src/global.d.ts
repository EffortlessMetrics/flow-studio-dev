/**
 * Global type declarations for Flow Studio
 *
 * These types augment the global scope for:
 * - Window properties used by our modules
 * - Cytoscape loaded from CDN
 * - Debug utilities exposed for browser console
 */

import type { GraphState, CytoscapeInstance, FlowStudioSDK } from "./domain.js";

declare global {
  // ============================================================================
  // Window Extensions
  // ============================================================================

  interface Window {
    /**
     * Toggle the selftest modal visibility.
     * Used by inline onclick handlers in HTML.
     */
    toggleSelftestModal(show: boolean): void;

    /**
     * Copy a command and optionally execute it.
     * Optional - only present when command execution is enabled.
     */
    copyAndRun?(command: string): void;

    /**
     * Show the selftest plan modal.
     * Optional - only present when selftest UI is loaded.
     */
    showSelftestPlanModal?(): void;

    /**
     * Show a specific selftest step modal.
     * Optional - only present when selftest UI is loaded.
     */
    showSelftestStepModal?(stepId: string): void;

    /**
     * Copy a command to clipboard.
     * Optional - only present when selftest UI is loaded.
     */
    copyToClipboard?(text: string): void;

    /**
     * Debug API for graph inspection.
     * Exposed for browser console debugging and LLM agent introspection.
     */
    __flowStudioGraph?: {
      getCurrentGraphState(): GraphState | null;
      renderFlowOutline(): void;
    };

    /**
     * Flow Studio SDK for agents and automation.
     * Stable, typed API surface for programmatic access.
     */
    __flowStudio?: FlowStudioSDK;
  }

  // ============================================================================
  // Cytoscape Global (loaded from CDN)
  // ============================================================================

  /**
   * Cytoscape constructor function.
   * Loaded from: https://unpkg.com/cytoscape@3.26.0/dist/cytoscape.min.js
   */
  function cytoscape(options: CytoscapeOptions): CytoscapeInstance;

  /**
   * Cytoscape initialization options
   */
  interface CytoscapeOptions {
    container: HTMLElement | null;
    elements?: {
      nodes?: object[];
      edges?: object[];
    };
    style?: CytoscapeStylesheet[];
    layout?: {
      name: string;
      [key: string]: unknown;
    };
    minZoom?: number;
    maxZoom?: number;
    wheelSensitivity?: number;
    boxSelectionEnabled?: boolean;
    autounselectify?: boolean;
  }

  /**
   * Cytoscape stylesheet entry
   */
  interface CytoscapeStylesheet {
    selector: string;
    style: Record<string, unknown>;
  }
}

// This export is required to make this file a module
export {};
