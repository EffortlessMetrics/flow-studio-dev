# Timeline Overlays Implementation Spec

**Status:** Ready for implementation
**Priority:** Track 1 (highest value, backend ready)
**Effort:** ~2-3 hours
**Files to modify:**
- FastAPI backend (default): `swarm/tools/flow_studio_fastapi.py`
- Flask backend (legacy): `swarm/tools/flow_studio.py`

---

## Goal

Make timing data visible in Flow Studio's UI. Operators should be able to answer:
- "What ran when?"
- "What was slow?"
- "How long did this flow/step take?"

All timing APIs already exist (`/api/runs/<run>/timeline`, `/api/runs/<run>/timing`, etc.). This spec covers the UI rendering only.

---

## Deliverables

### 1. Run-Level Timeline Panel (in Run tab)

When nothing is selected in the graph and "Run" tab is active, show a vertical timeline of flow execution.

**Location:** Details panel, Run tab content
**Data source:** `GET /api/runs/<run_id>/timeline`

**Visual design:**

```
Run Timeline
────────────────────────────────
09:00  ● Signal     started
09:45  ✓ Signal     completed (45m)
       └─ problem_statement.md verified
09:50  ● Plan       started
10:25  ✓ Plan       completed (35m)
       └─ adr_current.md verified
10:30  ● Build      started
11:30  ✓ Build      completed (1h)
       └─ 1 test iteration, 1 code iteration
...
────────────────────────────────
Total: 26 hours
```

### 2. Flow Timing Summary (when flow selected)

When a flow node is clicked (or flow is selected from sidebar), show timing in the details panel.

**Location:** Details panel, after flow description
**Data source:** `GET /api/runs/<run_id>/flows/<flow>/timing`

**Visual design:**

```
Flow: Build
Duration: 1h 0m
Started: 2025-01-15 10:30
Ended:   2025-01-15 11:30

Slowest Steps
─────────────────────────
implement     35m ████████████
author_tests  15m ████
self_review   10m ███
```

### 3. Step Timing Display (when step selected)

When a step node is clicked, show timing in the Run tab.

**Location:** Step details → Run tab, after "Step Status"
**Data source:** Already included in `GET /api/runs/<run_id>/flows/<flow>/steps/<step>` response

**Visual design:**

```
Step Status
COMPLETE

Timing
─────────────────────────
Started: 10:40:00
Ended:   11:15:00
Duration: 35m 0s
```

### 4. Visual Timing Hints on Graph Nodes (optional)

Add subtle timing badge to step nodes that have timing data.

**Visual design:** Small `⏱` icon or duration text appended to node label when timing exists.

---

## Implementation Details

### File: `swarm/tools/flow_studio.py`

#### Change 1: Add CSS for timeline components

**Location:** Inside `_INDEX_HTML` string, in `<style>` section (around line 1017)

**Add after `.governance-fix` styles (around line 1510):**

```css
/* Timeline styles */
.timeline-container {
  margin-top: 12px;
  font-size: 12px;
}
.timeline-header {
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid #e5e7eb;
}
.timeline-event {
  display: flex;
  gap: 8px;
  padding: 4px 0;
  border-left: 2px solid #e5e7eb;
  margin-left: 4px;
  padding-left: 12px;
}
.timeline-event.started {
  border-left-color: #3b82f6;
}
.timeline-event.completed {
  border-left-color: #22c55e;
}
.timeline-event.failed {
  border-left-color: #ef4444;
}
.timeline-time {
  font-family: ui-monospace, monospace;
  font-size: 11px;
  color: #6b7280;
  min-width: 50px;
}
.timeline-icon {
  font-size: 12px;
}
.timeline-flow {
  font-weight: 500;
}
.timeline-status {
  color: #6b7280;
}
.timeline-duration {
  color: #059669;
  font-weight: 500;
}
.timeline-note {
  font-size: 11px;
  color: #6b7280;
  margin-left: 70px;
  margin-top: 2px;
}
.timeline-total {
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px solid #e5e7eb;
  font-weight: 600;
}

/* Timing summary styles */
.timing-summary {
  margin-top: 12px;
  padding: 8px;
  background: #f9fafb;
  border-radius: 6px;
  font-size: 12px;
}
.timing-summary-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.timing-summary-duration {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}
.timing-summary-range {
  font-size: 11px;
  color: #6b7280;
}
.timing-bar-container {
  margin-top: 8px;
}
.timing-bar-label {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  margin-bottom: 2px;
}
.timing-bar {
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 6px;
}
.timing-bar-fill {
  height: 100%;
  background: #3b82f6;
  border-radius: 4px;
}
.timing-bar-fill.slow {
  background: #f59e0b;
}

/* Step timing inline */
.step-timing {
  margin-top: 8px;
  padding: 6px 8px;
  background: #f0fdf4;
  border-radius: 4px;
  font-size: 11px;
}
.step-timing-row {
  display: flex;
  justify-content: space-between;
  padding: 2px 0;
}
.step-timing-label {
  color: #6b7280;
}
.step-timing-value {
  font-family: ui-monospace, monospace;
  color: #059669;
}
```

#### Change 2: Add timeline rendering functions

**Location:** Inside `<script>` section, after `renderAgentUsage` function (around line 3802)

**Add new functions:**

```javascript
// Format duration in human-readable form
function formatDuration(seconds) {
  if (seconds == null) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${mins}m`;
}

// Format timestamp to time only (HH:MM)
function formatTime(isoString) {
  if (!isoString) return "—";
  const d = new Date(isoString);
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
}

// Format timestamp to date + time
function formatDateTime(isoString) {
  if (!isoString) return "—";
  const d = new Date(isoString);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) +
         ' ' + d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
}

// Render run-level timeline
async function renderRunTimeline(container) {
  if (!currentRunId) {
    container.innerHTML = '<div class="muted">Select a run to see timeline</div>';
    return;
  }

  container.innerHTML = '<div class="muted">Loading timeline...</div>';

  try {
    const data = await fetchJSON(`/api/runs/${encodeURIComponent(currentRunId)}/timeline`);
    const events = data.events || [];

    if (events.length === 0) {
      container.innerHTML = '<div class="muted">No timeline data available for this run</div>';
      return;
    }

    let html = '<div class="timeline-container">';
    html += '<div class="timeline-header">Run Timeline</div>';

    events.forEach(event => {
      const icon = event.status === 'started' ? '●' :
                   event.status === 'completed' ? '✓' :
                   event.status === 'failed' ? '✗' : '•';
      const time = formatTime(event.timestamp);
      const duration = event.duration_ms ? formatDuration(event.duration_ms / 1000) : '';

      html += `
        <div class="timeline-event ${event.status}">
          <span class="timeline-time">${time}</span>
          <span class="timeline-icon">${icon}</span>
          <span class="timeline-flow">${event.flow}</span>
          <span class="timeline-status">${event.status}</span>
          ${duration ? `<span class="timeline-duration">(${duration})</span>` : ''}
        </div>
      `;

      if (event.note) {
        html += `<div class="timeline-note">└─ ${event.note}</div>`;
      }
    });

    // Add total duration if available
    const timingData = await fetchJSON(`/api/runs/${encodeURIComponent(currentRunId)}/timing`);
    if (timingData.timing?.total_duration_seconds) {
      html += `<div class="timeline-total">Total: ${formatDuration(timingData.timing.total_duration_seconds)}</div>`;
    }

    html += '</div>';
    container.innerHTML = html;
  } catch (err) {
    console.error("Failed to load timeline", err);
    container.innerHTML = '<div class="muted">Timeline not available</div>';
  }
}

// Render flow timing summary
async function renderFlowTiming(container, flowKey) {
  if (!currentRunId || !flowKey) {
    return;
  }

  try {
    const data = await fetchJSON(`/api/runs/${encodeURIComponent(currentRunId)}/flows/${encodeURIComponent(flowKey)}/timing`);
    const timing = data.timing;

    if (!timing || !timing.duration_seconds) {
      return; // No timing data, don't render anything
    }

    let html = '<div class="timing-summary">';
    html += '<div class="timing-summary-header">';
    html += `<span class="timing-summary-duration">${formatDuration(timing.duration_seconds)}</span>`;
    if (timing.started_at && timing.ended_at) {
      html += `<span class="timing-summary-range">${formatDateTime(timing.started_at)} → ${formatDateTime(timing.ended_at)}</span>`;
    }
    html += '</div>';

    // Render step timing bars if we have step data
    const steps = timing.steps || [];
    if (steps.length > 0 && steps.some(s => s.duration_seconds)) {
      // Sort by duration descending, take top 5
      const sortedSteps = steps
        .filter(s => s.duration_seconds)
        .sort((a, b) => (b.duration_seconds || 0) - (a.duration_seconds || 0))
        .slice(0, 5);

      if (sortedSteps.length > 0) {
        const maxDuration = sortedSteps[0].duration_seconds;
        html += '<div class="timing-bar-container">';
        html += '<div style="font-size: 11px; color: #6b7280; margin-bottom: 6px;">Slowest Steps</div>';

        sortedSteps.forEach(step => {
          const pct = Math.round((step.duration_seconds / maxDuration) * 100);
          const isSlow = step.duration_seconds > timing.duration_seconds * 0.3;
          html += `
            <div class="timing-bar-label">
              <span>${step.step_id}</span>
              <span>${formatDuration(step.duration_seconds)}</span>
            </div>
            <div class="timing-bar">
              <div class="timing-bar-fill ${isSlow ? 'slow' : ''}" style="width: ${pct}%"></div>
            </div>
          `;
        });

        html += '</div>';
      }
    }

    html += '</div>';
    container.insertAdjacentHTML('beforeend', html);
  } catch (err) {
    console.error("Failed to load flow timing", err);
    // Silently fail - timing is optional
  }
}

// Render step timing inline
function renderStepTiming(timing) {
  if (!timing || (!timing.started_at && !timing.duration_seconds)) {
    return '';
  }

  let html = '<div class="step-timing">';

  if (timing.started_at) {
    html += `
      <div class="step-timing-row">
        <span class="step-timing-label">Started</span>
        <span class="step-timing-value">${formatTime(timing.started_at)}</span>
      </div>
    `;
  }

  if (timing.ended_at) {
    html += `
      <div class="step-timing-row">
        <span class="step-timing-label">Ended</span>
        <span class="step-timing-value">${formatTime(timing.ended_at)}</span>
      </div>
    `;
  }

  if (timing.duration_seconds) {
    html += `
      <div class="step-timing-row">
        <span class="step-timing-label">Duration</span>
        <span class="step-timing-value">${formatDuration(timing.duration_seconds)}</span>
      </div>
    `;
  }

  html += '</div>';
  return html;
}
```

#### Change 3: Update `renderGraph` to show timeline when no node selected

**Location:** `renderGraph` function (around line 3459)

**Find this section** (around line 3517-3531):

```javascript
  const operatorHint = document.createElement("div");
  operatorHint.className = "muted operator-only";
  operatorHint.innerHTML = `
    <div style="margin-top: 8px;">
      Select a step or agent in the graph to see its status and artifacts.
      <br/><br/>
      Use the <strong>Run</strong> selector on the left to switch between runs.
    </div>
  `;
```

**Replace with:**

```javascript
  const operatorHint = document.createElement("div");
  operatorHint.className = "operator-only";
  operatorHint.id = "flow-overview-timeline";
  operatorHint.innerHTML = `
    <div class="muted" style="margin-top: 8px;">
      Select a step or agent in the graph to see its status and artifacts.
    </div>
  `;

  // Load timeline in operator mode
  if (currentMode === "operator" && currentRunId) {
    renderRunTimeline(operatorHint);
    renderFlowTiming(operatorHint, flow.key);
  }
```

#### Change 4: Update `showStepDetails` to include timing

**Location:** `showStepDetails` function, in the "Run tab content" section (around line 3616)

**Find this section:**

```javascript
  runTab.innerHTML = `
    <div class="kv-label">Run</div>
    <div class="mono">${currentRunId || "None selected"}</div>
    <div class="kv-label">Step Status</div>
    <div class="${statusClass}" style="font-weight: 600;">${stepStatus.toUpperCase()}</div>
    ...
```

**Before the closing backtick, add timing section:**

First, **add this code before `runTab.innerHTML =`** to fetch step timing:

```javascript
  // Get step timing if available
  let stepTimingHtml = '';
  if (currentRunId && stepData.timing) {
    stepTimingHtml = renderStepTiming(stepData.timing);
  }
```

Then **modify the `runTab.innerHTML` template** to include timing after step status:

```javascript
  runTab.innerHTML = `
    <div class="kv-label">Run</div>
    <div class="mono">${currentRunId || "None selected"}</div>
    <div class="kv-label">Step Status</div>
    <div class="${statusClass}" style="font-weight: 600;">${stepStatus.toUpperCase()}</div>
    <div style="font-size: 11px; color: #6b7280; margin-top: 2px;">
      ${stepData.required_present || 0}/${stepData.required_total || 0} required,
      ${stepData.optional_present || 0}/${stepData.optional_total || 0} optional
    </div>
    ${stepData.note ? `<div class="muted" style="margin-top: 4px; font-style: italic;">${stepData.note}</div>` : ""}
    ${stepTimingHtml}
    <div class="kv-label">Artifacts</div>
    ...
  `;
```

#### Change 5: Update mode toggle to refresh timeline

**Location:** `setMode` function (around line 2563)

**After updating body classes, add:**

```javascript
  // Refresh timeline display if in operator mode and viewing a flow
  if (mode === "operator" && currentRunId && currentFlowKey) {
    const timelineContainer = document.getElementById("flow-overview-timeline");
    if (timelineContainer) {
      renderRunTimeline(timelineContainer);
    }
  }
```

#### Change 6: Ensure step status endpoint returns timing

**Location:** `/api/runs/<run_id>/flows/<flow_key>/steps/<step_id>` endpoint (around line 750)

**Current code should already include timing** - verify this exists. If not, add to the step response:

```python
# In the step endpoint handler
step_dict = asdict(step_result)
# Add timing if available
flow_timing = inspector.get_flow_timing(run_id, flow_key)
if flow_timing:
    for st in flow_timing.steps:
        if st.step_id == step_id:
            step_dict["timing"] = asdict(st)
            break
return jsonify(step_dict)
```

---

## Testing Plan

### Manual Testing

1. **Run timeline display:**
   - Start Flow Studio: `make flow-studio`
   - Select "health-check-risky-deploy" run (has full timeline data)
   - Switch to Operator mode
   - Verify timeline appears in right panel when no node selected
   - Verify events show correct times and durations

2. **Flow timing summary:**
   - Click on a flow in sidebar
   - Verify duration and date range appear
   - Verify "Slowest Steps" bars render correctly

3. **Step timing:**
   - Click on a step node
   - Switch to "Run" tab
   - Verify Started/Ended/Duration appear
   - Verify times are formatted correctly

4. **Edge cases:**
   - Select a run with no timeline data (e.g., new active run)
   - Verify graceful fallback ("No timeline data available")
   - Switch between Author/Operator modes
   - Verify timeline only shows in Operator mode

### Automated Test (optional)

Add to `tests/test_flow_studio.py`:

```python
def test_timeline_api_returns_events(client):
    """Timeline endpoint returns sorted events."""
    resp = client.get("/api/runs/health-check-risky-deploy/timeline")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "events" in data
    assert len(data["events"]) > 0
    # Events should be in chronological order
    timestamps = [e["timestamp"] for e in data["events"]]
    assert timestamps == sorted(timestamps)

def test_flow_timing_returns_duration(client):
    """Flow timing endpoint returns duration data."""
    resp = client.get("/api/runs/health-check-risky-deploy/flows/build/timing")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "timing" in data
    assert data["timing"]["duration_seconds"] > 0
```

---

## Data Format Reference

### Timeline API Response

```json
{
  "run_id": "health-check-risky-deploy",
  "events": [
    {
      "timestamp": "2025-01-15T09:00:00Z",
      "flow": "signal",
      "step": null,
      "status": "started",
      "duration_ms": null,
      "note": null
    },
    {
      "timestamp": "2025-01-15T09:45:00Z",
      "flow": "signal",
      "step": null,
      "status": "completed",
      "duration_ms": 2700000,
      "note": "problem_statement.md verified"
    }
  ]
}
```

### Flow Timing Response

```json
{
  "run_id": "health-check-risky-deploy",
  "flow_key": "build",
  "timing": {
    "flow_key": "build",
    "started_at": "2025-01-15T10:30:00Z",
    "ended_at": "2025-01-15T11:30:00Z",
    "duration_seconds": 3600,
    "steps": [
      {"step_id": "implement", "started_at": "...", "ended_at": "...", "duration_seconds": 2100},
      {"step_id": "author_tests", "started_at": "...", "ended_at": "...", "duration_seconds": 900}
    ]
  }
}
```

---

## Dependencies

- **Backend APIs:** All required endpoints already exist and are tested
- **Example data:** `health-check-risky-deploy` has complete `flow_history.json` with `execution_timeline`
- **No new Python packages required**
- **No database changes**

---

## Rollout

1. Implement CSS changes
2. Implement JavaScript functions
3. Wire into existing render functions
4. Test manually with `health-check-risky-deploy` run
5. Verify no regressions in Author mode
6. Commit with message: `feat(flow-studio): Add timeline overlays for run/flow/step timing`

---

## Future Enhancements (out of scope for this spec)

- **Gantt chart visualization** - horizontal timeline with flow bars
- **Timing comparison** - compare timing between two runs
- **Timing badges on graph nodes** - show `⏱35m` on step nodes
- **Export timeline** - download as CSV/JSON
