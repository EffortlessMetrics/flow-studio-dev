# Flow Studio Front-End Refactor Plan

This document outlines the modularization of Flow Studio's front-end from a single
monolithic script into focused ES modules.

## 0. Goals & Constraints

### Goals

1. **Modularize the Flow Studio front-end**
   - Break the current god-script (search, runs, flows, graph, details, governance,
     tours, selftest, timing) into focused ES modules.

2. **Avoid circular dependencies**
   - No module webs where everything imports everything.

3. **Keep behavior and APIs stable**
   - HTML IDs and `/api/*` endpoints don't change.
   - Deep links (`?run=…&flow=…&step=…&mode=…&view=…&tour=…`) keep working.

4. **Play nicely with existing tooling**
   - `make dev-check`, `make selftest`, governance checks, Flow Studio smoke tests,
     etc. keep passing at each phase.

### Non-Goals

- No framework rewrite (no React/Vue).
- No big visual redesign.
- No TypeScript migration (yet).

---

## 1. Final Architecture (Target State)

### 1.1 File Structure

```text
flow-studio/
  index.html

  css/
    flow-studio.base.css        # All existing CSS (can be split later)
    # flow-studio.components.css (optional, future)
    # flow-studio.modals.css     (optional, future)

  js/
    main.js                     # Entry; wiring & orchestration
    state.js                    # Global state
    api.js                      # All fetch() wrappers
    utils.js                    # Clipboard, formatting, helpers

    graph.js                    # Cytoscape graph + rendering
    runs_flows.js               # Runs, flows, SDLC bar, setActiveFlow
    details.js                  # Details panel (step, agent, artifact)

    search.js                   # Search box and dropdown
    keyboard.js                 # Keyboard shortcuts

    governance.js               # Governance badge, overlays, FR badges
    selftest.js                 # Selftest modal + plan tab
    tours.js                    # Tour dropdown + guided cards
    timing.js                   # Timeline + timing summary for runs/flows
```

You can introduce the last four (`governance/selftest/tours/timing`) after the
core three (`graph`, `runs_flows`, `details`) are stable.

### 1.2 Dependency Graph (Import Rules)

Think of it as layers:

**Core (no DOM assumptions beyond simple `document.getElementById`)**

- `state.js`
- `api.js`
- `utils.js`

**Feature modules**

- `graph.js` (depends on: `state`, maybe `utils`)
- `runs_flows.js` (depends on: `state`, `api`, `graph`)
- `details.js` (depends on: `state`, `api`, `utils`)
- `search.js` (depends on: `api`, `state` optionally)
- `keyboard.js` (depends on: `state`, maybe `graph`)
- `governance.js` (depends on: `api`, `state`, maybe `graph`, `runs_flows`)
- `selftest.js` (depends on: `api`, `state`, `utils`)
- `tours.js` (depends on: `api`, `state`, `graph`)
- `timing.js` (depends on: `api`, `state`, `utils`)

**Orchestrator**

- `main.js` imports from *everything*, but nothing imports `main.js`.

**Key rule**: Feature modules **don't import each other in rings**. If A needs to
invoke logic from B, it should get a **callback** from `main.js`.

Example pattern:

```js
// graph.js
let callbacks = { onStepClick: null };
export function initGraph(opts = {}) {
  callbacks = { ...callbacks, ...opts };
  // ...
  cy.on("tap", "node", (ev) => {
    const d = ev.target.data();
    if (d.type === "step" && callbacks.onStepClick) callbacks.onStepClick(d);
  });
}

// main.js
import { initGraph } from "./graph.js";
import { showStepDetails } from "./details.js";

initGraph({
  onStepClick: showStepDetails,
});
```

---

## 2. Module Responsibilities & Interfaces

### 2.1 `state.js`

Single source of truth for all global state.

```js
// state.js
export const state = {
  cy: null,

  currentFlowKey: null,
  currentRunId: null,
  compareRunId: null,

  runStatus: {},         // /api/runs/:id/summary
  comparisonData: null,  // /api/runs/compare
  availableRuns: [],

  governanceStatus: null,
  validationData: null,
  governanceOverlayEnabled: false,

  currentMode: "author",   // "author" | "operator"
  currentViewMode: "agents"// "agents" | "artifacts"
};

// Optional small helpers
export const setMode = (mode) => (state.currentMode = mode);
export const setViewMode = (view) => (state.currentViewMode = view);
export const setCurrentRun = (runId) => (state.currentRunId = runId);
export const setCurrentFlow = (flowKey) => (state.currentFlowKey = flowKey);
```

### 2.2 `api.js`

All network calls live here.

```js
// api.js
async function fetchJSON(url, options) {
  const resp = await fetch(url, options);
  if (!resp.ok) throw new Error(`HTTP ${resp.status} for ${url}`);
  return resp.json();
}

export const Api = {
  getRuns: () => fetchJSON("/api/runs"),
  getRunSummary: (runId) =>
    fetchJSON(`/api/runs/${encodeURIComponent(runId)}/summary`),
  getRunTimeline: (runId) =>
    fetchJSON(`/api/runs/${encodeURIComponent(runId)}/timeline`),
  getRunTiming: (runId) =>
    fetchJSON(`/api/runs/${encodeURIComponent(runId)}/timing`),
  getFlowTiming: (runId, flowKey) =>
    fetchJSON(
      `/api/runs/${encodeURIComponent(runId)}/flows/${encodeURIComponent(
        flowKey
      )}/timing`
    ),

  getFlows: () => fetchJSON("/api/flows"),
  getFlowGraphAgents: (flowKey) =>
    fetchJSON(`/api/graph/${encodeURIComponent(flowKey)}`),
  getFlowGraphArtifacts: (flowKey, runId) => {
    const runParam = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
    return fetchJSON(
      `/api/graph/${encodeURIComponent(flowKey)}/artifacts${runParam}`
    );
  },
  getFlowDetail: (flowKey) =>
    fetchJSON(`/api/flows/${encodeURIComponent(flowKey)}`),

  search: (q) => fetchJSON(`/api/search?q=${encodeURIComponent(q)}`),
  reloadConfig: () => fetchJSON("/api/reload", { method: "POST" }),

  getGovernanceStatus: () => fetchJSON("/platform/status"),
  getValidationData: () => fetchJSON("/api/validation"),

  getAgentUsage: (agentKey) =>
    fetchJSON(`/api/agents/${encodeURIComponent(agentKey)}/usage`),

  getRunsComparison: ({ runA, runB, flow }) =>
    fetchJSON(
      `/api/runs/compare?run_a=${encodeURIComponent(
        runA
      )}&run_b=${encodeURIComponent(runB)}&flow=${encodeURIComponent(flow)}`
    ),

  getTours: () => fetchJSON("/api/tours"),
  getTourById: (id) =>
    fetchJSON(`/api/tours/${encodeURIComponent(id)}`),

  getSelftestPlan: () => fetchJSON("/api/selftest/plan")
};
```

### 2.3 `utils.js`

General helpers:

```js
// utils.js
export function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export function formatDuration(sec) { /* your existing logic */ }
export function formatTime(iso) { /* your existing logic */ }
export function formatDateTime(iso) { /* your existing logic */ }

export function copyToClipboard(text) { /* with fallback */ }

export function createCopyButton(text, label = "Copy") { /* existing logic */ }

export function createQuickCommands(commands) { /* existing logic */ }
```

### 2.4 `graph.js`

Responsible for:
- Creating and storing the Cytoscape instance.
- Defining graph styles.
- Rendering nodes/edges.
- Exposing click events via callbacks.

```js
// graph.js
import { state } from "./state.js";

let callbacks = {
  onStepClick: null,
  onAgentClick: null,
  onArtifactClick: null
};

export function initGraph(opts = {}) {
  callbacks = { ...callbacks, ...opts };

  const cy = cytoscape({
    container: document.getElementById("graph"),
    elements: [],
    layout: { name: "breadthfirst", directed: true, padding: 16 },
    style: [ /* your existing style objects */ ]
  });

  cy.on("tap", "node", (ev) => {
    const data = ev.target.data();
    if (data.type === "step" && callbacks.onStepClick) callbacks.onStepClick(data);
    else if (data.type === "agent" && callbacks.onAgentClick) callbacks.onAgentClick(data);
    else if (data.type === "artifact" && callbacks.onArtifactClick) callbacks.onArtifactClick(data);
  });

  state.cy = cy;
  return cy;
}

export function getCy() {
  return state.cy;
}

export function renderGraph(graph, detail) {
  const cy = state.cy || initGraph();
  const elements = [...(graph.nodes || []), ...(graph.edges || [])];

  cy.elements().remove();
  cy.add(elements);
  cy.layout({ name: "breadthfirst", directed: true, padding: 16 }).run();
}
```

Note: **no imports from `details.js`** – callbacks handle that.

### 2.5 `runs_flows.js`

Responsible for:
- Loading runs and flows.
- Setting `currentRunId`, `currentFlowKey`.
- Rendering the SDLC bar and flow list.
- Calling `renderGraph` with the right data.
- Updating node labels with status icons.

```js
// runs_flows.js
import { state, setCurrentRun, setCurrentFlow } from "./state.js";
import { Api } from "./api.js";
import { renderGraph } from "./graph.js";

export const STATUS_ICONS = {
  done: "✅",
  in_progress: "⏳",
  not_started: "—",
  complete: "✅",
  partial: "⚠️",
  missing: "❌",
  "n/a": "—"
};

const FLOW_ORDER = ["signal", "plan", "build", "gate", "deploy", "wisdom"];
const FLOW_TITLES = { signal: "Signal", /* ... */ };

export async function loadRuns() { /* /api/runs logic */ }
export async function loadRunStatus() { /* /api/runs/:id/summary */ }
export async function loadFlows() { /* /api/flows + sidebar list */ }

export async function setActiveFlow(flowKey, { force = false } = {}) {
  if (state.currentFlowKey === flowKey && !force) return;
  setCurrentFlow(flowKey);
  markActiveFlow(flowKey);

  const [graph, detail] =
    state.currentViewMode === "artifacts"
      ? await Promise.all([
          Api.getFlowGraphArtifacts(flowKey, state.currentRunId),
          Api.getFlowDetail(flowKey)
        ])
      : await Promise.all([
          Api.getFlowGraphAgents(flowKey),
          Api.getFlowDetail(flowKey)
        ]);

  renderGraph(graph, detail);
  if (state.runStatus.flows) updateGraphStatus();
}

export function updateSDLCBar() { /* SDLC bar logic */ }
export function updateFlowListStatus() { /* apply icons to flow list */ }
export function updateGraphStatus() { /* label step nodes with ✅/⚠️/❌ */ }
function markActiveFlow(flowKey) { /* toggles .flow-item/.sdlc-flow active class */ }
```

### 2.6 `details.js`

Responsible for **everything inside the right-hand "Details" panel**:

```js
// details.js
import { state } from "./state.js";
import { Api } from "./api.js";
import { createQuickCommands } from "./utils.js";

export function showStepDetails(stepData) { /* existing implementation */ }
export function showAgentDetails(agentData) { /* existing implementation */ }
export function showArtifactDetails(artifactData) { /* existing implementation */ }
```

### 2.7 `search.js`

Encapsulates search input, dropdown, keyboard navigation.

```js
// search.js
import { Api } from "./api.js";

export function initSearch({ onFlowResult, onStepResult, onAgentResult, onArtifactResult }) {
  const input = document.getElementById("search-input");
  const dropdown = document.getElementById("search-dropdown");
  // Debounce logic, render results, call appropriate callbacks
}
```

### 2.8 `keyboard.js`

All global shortcuts:

```js
// keyboard.js
const FLOW_KEYS = ["signal", "plan", "build", "gate", "deploy", "wisdom"];

export function initKeyboard({ onSearchFocus, onShowHelp, onFlowShortcut, onNextStep, onPrevStep }) {
  document.addEventListener("keydown", (e) => {
    const el = document.activeElement;
    if (el && ["INPUT", "TEXTAREA"].includes(el.tagName)) return;

    if (e.key === "/") { e.preventDefault(); onSearchFocus(); }
    else if (e.key === "?" || (e.shiftKey && e.key === "/")) { e.preventDefault(); onShowHelp(); }
    else if (e.key >= "1" && e.key <= "6") { onFlowShortcut(FLOW_KEYS[Number(e.key) - 1]); }
    else if (e.key === "ArrowRight") { onNextStep(); }
    else if (e.key === "ArrowLeft") { onPrevStep(); }
  });
}
```

### 2.9 `governance.js`

Responsible for:
- Fetching `/platform/status` & `/api/validation`.
- Updating the top governance badge.
- Applying governance styles / FR overlays to graph nodes.

```js
// governance.js
import { state } from "./state.js";
import { Api } from "./api.js";

export async function initGovernance({ onStatusLoaded }) {
  // Fetch governanceStatus & validationData, store in state
  // Update badge DOM
  // Hook up #governance-badge click => showGovernanceDetails()
  if (onStatusLoaded) onStatusLoaded();
}

export function applyGovernanceOverlay(cy) { /* inspect state.validationData */ }
export function showGovernanceDetails() { /* render into #details */ }
```

### 2.10 `selftest.js`

Responsible for:
- Selftest modal (open/close).
- Selftest plan rendering.

```js
// selftest.js
import { Api } from "./api.js";
import { state } from "./state.js";

export function initSelftestModal() { /* wire up modal */ }
export async function renderSelftestTab(container) { /* load /api/selftest/plan */ }
export async function showSelftestStepModal(stepId) { /* fetch plan, render step */ }
```

### 2.11 `tours.js`

Responsible for:
- Loading available tours.
- Showing the tour card.
- Callbacks for focusing flows/steps.

```js
// tours.js
import { Api } from "./api.js";
import { state } from "./state.js";

export function initTours({ onFlowSelected, onStepSelected }) {
  // load tours, render dropdown, wire menu click
}
```

### 2.12 `timing.js`

Timeline and timing display:

```js
// timing.js
import { Api } from "./api.js";
import { state } from "./state.js";
import { formatDuration, formatTime, formatDateTime } from "./utils.js";

export async function renderRunTimeline(container) { /* /api/runs/:id/timeline */ }
export async function renderFlowTiming(container, flowKey) { /* timing endpoint */ }
export function renderStepTiming(timing) { /* returns HTML string */ }
```

### 2.13 `main.js` (Orchestrator)

The glue:

```js
// main.js
import { state, setMode, setViewMode } from "./state.js";
import { initGraph, getCy } from "./graph.js";
import { loadRuns, loadFlows, setActiveFlow, loadRunStatus } from "./runs_flows.js";
import { showStepDetails, showAgentDetails, showArtifactDetails } from "./details.js";
import { initSearch } from "./search.js";
import { initKeyboard } from "./keyboard.js";
import { initGovernance, applyGovernanceOverlay } from "./governance.js";
import { initSelftestModal } from "./selftest.js";
import { initTours } from "./tours.js";
import { Api } from "./api.js";

window.addEventListener("load", async () => {
  initModeFromURL();
  initSearchWiring();
  initKeyboardWiring();
  initGraphWiring();
  initGovernanceWiring();
  initSelftestModal();
  initToursWiring();
  initRunSelector();
  initReloadButton();
  initLegendToggle();
  initShortcutsHelpButton();

  await loadRuns();
  await loadFlows();
  if (state.validationData && state.cy) applyGovernanceOverlay(state.cy);
});
```

---

## 3. HTML & CSS Updates

### 3.1 HTML Changes

1. Move `<style>...</style>` into `css/flow-studio.base.css`.
2. Replace inline script with:

```html
<script src="https://unpkg.com/cytoscape@3.26.0/dist/cytoscape.min.js" defer></script>
<script type="module" src="js/main.js"></script>
```

3. Leave all DOM structure (IDs/classes) intact:
   - `#app`, `#graph`, `#details`, `#sidebar`, `#sdlc-bar`, etc.
   - `#run-selector`, `#compare-selector`
   - `#search-input`, `#search-dropdown`
   - `#governance-badge`, `#governance-overlay-checkbox`
   - `#tour-btn`, `#tour-menu`, `#tour-card`, etc.

### 3.2 CSS Changes

Initially: **no behavioral changes**, just move to `flow-studio.base.css`.

Optional future splits:
- `flow-studio.layout.css` (grid, header/sidebar)
- `flow-studio.components.css` (legend, modals, buttons)
- `flow-studio.governance.css` (badges, FR overlays)

---

## 4. Migration Plan (Step-by-Step)

### Phase 0 – Extract Files, Keep Everything Global ✅

**Objective:** Flow Studio still works identically, but CSS/JS live in external files.

**Status:** COMPLETE (2025-12-05)

**Tasks:**

- [x] Create `css/flow-studio.base.css` and move `<style>` into it (1348 lines).
- [x] Create `js/flow-studio-app.js` (originally `flow-studio-legacy.js`) and move `<script>…</script>` into it (3068 lines).
- [x] Update `index.html` to reference external files (218 lines).
- [x] Add static file serving to FastAPI backend (`flow_studio_fastapi.py`).
- [x] Run:
  - [x] `make dev-check` — all checks pass
  - [x] Flow Studio smoke test — PASS
  - [x] Selftest (11/11 steps) — PASS

### Phase 1 – Introduce `state.js`, `api.js`, `utils.js` and ESM

**Objective:** Move off globals/fetch scattered everywhere into a cleaner base.

**Tasks:**

- [ ] Add `<script type="module" src="js/main.js">` and create `main.js`.
- [x] In `main.js`, import `./flow-studio-app.js`.
- [ ] Create:
  - `state.js`
  - `api.js`
  - `utils.js`
- [ ] Replace:
  - `let cy = null; let currentFlowKey = null; …` → properties on `state`.
  - All `fetch()` usages → `Api.*` helpers.
  - Utility functions → move to `utils.js`.

**Checks:**

- [ ] No "undefined variable" console errors.
- [ ] `make dev-check` and selftests still pass.

### Phase 2 – Extract Core Feature Modules

**Objective:** Break the monolith into 3 chunks.

**Tasks:**

1. **graph.js**
   - [ ] Move Cytoscape creation and styling into `initGraph`.
   - [ ] Store `cy` on `state`.
   - [ ] Expose `initGraph({ onStepClick, onAgentClick, onArtifactClick })` and `getCy()`.

2. **details.js**
   - [ ] Move `showStepDetails`, `showAgentDetails`, `showArtifactDetails`.
   - [ ] Import `state`, `Api`, `utils` as needed.

3. **runs_flows.js**
   - [ ] Move `loadRuns`, `loadRunStatus`, `loadFlows`, `setActiveFlow`,
         `updateSDLCBar`, `updateFlowListStatus`, `updateGraphStatus`.
   - [ ] Import `state`, `Api`, `renderGraph`.

4. **main.js**
   - [ ] Call `initGraph(...)` with callbacks to `details.js`.
   - [ ] Use `loadRuns()` + `loadFlows()` on startup.

**Checks:**

- [ ] Manual test: click flows → graph updates, details panel shows step/agent/artifact.
- [ ] Smoke tests & `make dev-check` pass.

### Phase 3 – Extract Search & Keyboard

**Objective:** Make search and keyboard standalone.

**Tasks:**

1. **search.js**
   - [ ] Move search variables + logic.
   - [ ] Export `initSearch({ onFlowResult, onStepResult, ... })`.

2. **keyboard.js**
   - [ ] Move keyboard listeners into `initKeyboard({ ...callbacks })`.

**Checks:**

- [ ] Search finds flows/steps/agents/artifacts correctly.
- [ ] Keyboard shortcuts work.
- [ ] No global `document.addEventListener('keydown'...)` outside `keyboard.js`.

### Phase 4 – Governance, Selftest, Tours, Timing

**Objective:** Peel off advanced features.

**Tasks:**

1. **governance.js**
   - [ ] Move `loadGovernanceStatus`, `updateValidationIssuesCount`,
         governance overlay logic, FR badges.
   - [ ] Store `state.governanceStatus` and `state.validationData`.

2. **selftest.js**
   - [ ] Move selftest modal + plan rendering.
   - [ ] `initSelftestModal()` wires close/backdrop.

3. **tours.js**
   - [ ] Move tour dropdown/card logic.
   - [ ] `initTours({ onFlowSelected, onStepSelected })`.

4. **timing.js**
   - [ ] Move `renderRunTimeline`, `renderFlowTiming`, `renderStepTiming`.

**Checks:**

- [ ] Governance badge updates correctly.
- [ ] "Show Issues" overlay highlights nodes.
- [ ] Selftest tab & modal display correctly.
- [ ] Tours step through flows/steps.
- [ ] Timeline & timing views work.

---

## 5. Testing & Acceptance Criteria

**Functional:**

- Every existing feature still works:
  - SDLC bar + flow selection
  - Node selection → details panel
  - Run selection + compare
  - Search
  - Governance overlays + FR badges
  - Selftest plan and modals
  - Tours
  - Keyboard shortcuts

**Technical:**

- No global variables besides `window` and `cytoscape` from CDN.
- All Flow Studio logic is under `js/*.js` with `type="module"`.
- Circular dependency check reveals:
  - `main.js` at the top with only incoming edges.
  - `state`, `api`, `utils` have no imports from feature modules.

---

## 6. Summary

> We're refactoring Flow Studio's front-end from a single monolithic script into a
> set of ES modules. Core concerns (state, API access, utilities) are separated from
> feature concerns (graph, runs/flows, details, search, keyboard, governance,
> selftest, tours). `main.js` is the only orchestrator: it wires modules together
> through callbacks, avoiding circular imports. All existing endpoints and DOM IDs
> remain unchanged, so the backend and selftest/governance checks keep working.
> The refactor is staged in several small phases so we can keep `make dev-check`
> and Flow Studio smoke tests green throughout.
