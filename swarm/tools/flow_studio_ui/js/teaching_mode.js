// swarm/tools/flow_studio_ui/src/teaching_mode.ts
// Teaching Mode state management for Flow Studio
//
// Teaching Mode is a pedagogical overlay that:
// - Highlights exemplar runs for learning
// - Defaults Run History to "Examples" filter
// - Enables additional educational features
//
// State is persisted to localStorage for session persistence.
// ============================================================================
// Constants
// ============================================================================
const STORAGE_KEY = "flowStudio.teachingMode";
// ============================================================================
// Internal State
// ============================================================================
let _isEnabled = false;
let _initialized = false;
// ============================================================================
// localStorage Helpers
// ============================================================================
/**
 * Read teaching mode state from localStorage.
 * Returns false if localStorage is unavailable or key is missing.
 */
function readFromStorage() {
    if (typeof window === "undefined")
        return false;
    try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (raw === null)
            return false;
        return raw === "true";
    }
    catch {
        // localStorage blocked or unavailable
        return false;
    }
}
/**
 * Write teaching mode state to localStorage.
 * Silently fails if localStorage is unavailable.
 */
function writeToStorage(enabled) {
    if (typeof window === "undefined")
        return;
    try {
        window.localStorage.setItem(STORAGE_KEY, enabled ? "true" : "false");
    }
    catch {
        // Ignore - UX still works, just loses persistence
    }
}
// ============================================================================
// State Management
// ============================================================================
/**
 * Initialize teaching mode from localStorage.
 * Call this once during app startup.
 */
export function initTeachingMode() {
    if (_initialized)
        return;
    _isEnabled = readFromStorage();
    _initialized = true;
    // Apply initial state to DOM
    applyTeachingModeClass();
}
/**
 * Get the current teaching mode state.
 * @returns true if Teaching Mode is enabled
 */
export function getTeachingMode() {
    return _isEnabled;
}
/**
 * Set the teaching mode state.
 * Persists to localStorage and updates the DOM.
 * Notifies all registered callbacks of the change.
 *
 * @param enabled - Whether Teaching Mode should be enabled
 */
export function setTeachingMode(enabled) {
    const wasEnabled = _isEnabled;
    _isEnabled = enabled;
    writeToStorage(enabled);
    applyTeachingModeClass();
    updateToggleButtonState();
    // Notify callbacks only if state actually changed
    if (wasEnabled !== enabled) {
        notifyCallbacks();
    }
}
/**
 * Toggle the teaching mode state.
 * Convenience method that inverts the current state.
 *
 * @returns The new state after toggling
 */
export function toggleTeachingMode() {
    setTeachingMode(!_isEnabled);
    return _isEnabled;
}
// ============================================================================
// DOM Updates
// ============================================================================
/**
 * Apply teaching-mode class to body based on current state.
 */
function applyTeachingModeClass() {
    if (typeof document === "undefined")
        return;
    if (_isEnabled) {
        document.body.classList.add("teaching-mode");
    }
    else {
        document.body.classList.remove("teaching-mode");
    }
}
/**
 * Update the toggle button's active state.
 */
function updateToggleButtonState() {
    if (typeof document === "undefined")
        return;
    const toggleBtn = document.querySelector('[data-uiid="flow_studio.header.teaching_mode.toggle"]');
    if (toggleBtn) {
        toggleBtn.classList.toggle("active", _isEnabled);
        toggleBtn.setAttribute("aria-pressed", _isEnabled ? "true" : "false");
        toggleBtn.title = _isEnabled
            ? "Teaching Mode is ON - click to disable"
            : "Enable Teaching Mode for learning-focused features";
    }
}
/** Registered callbacks */
const _callbacks = [];
/**
 * Register a callback to be notified when Teaching Mode changes.
 * Useful for components that need to update when teaching mode is toggled.
 *
 * @param callback - Function called with the new state when teaching mode changes
 */
export function onTeachingModeChange(callback) {
    _callbacks.push(callback);
}
/**
 * Notify all registered callbacks of a state change.
 */
function notifyCallbacks() {
    _callbacks.forEach(cb => {
        try {
            cb(_isEnabled);
        }
        catch (err) {
            console.error("Teaching mode callback error:", err);
        }
    });
}
// ============================================================================
// Integration Helpers
// ============================================================================
/**
 * Get the default Run History filter based on Teaching Mode.
 * When Teaching Mode is enabled, defaults to "example" filter.
 *
 * @returns "example" if Teaching Mode is on, "all" otherwise
 */
export function getDefaultRunHistoryFilter() {
    return _isEnabled ? "example" : "all";
}
/**
 * Initialize the toggle button event handler.
 * Call this after the DOM is ready.
 */
export function initToggleButtonHandler() {
    const toggleBtn = document.querySelector('[data-uiid="flow_studio.header.teaching_mode.toggle"]');
    if (toggleBtn) {
        toggleBtn.addEventListener("click", () => {
            toggleTeachingMode();
        });
        // Set initial button state
        updateToggleButtonState();
    }
}
