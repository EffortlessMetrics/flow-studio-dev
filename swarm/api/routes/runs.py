"""
Run control endpoints for Flow Studio API.

This module aggregates route modules for runs, autopilot, and issue ingestion.
The router is mounted at /runs by the server (prefix is managed externally).

For new development, import directly from the specific route modules:
- runs_routes: Run CRUD and lifecycle endpoints
- autopilot_routes: Autopilot start/stop/tick endpoints
- issue_routes: Issue ingestion endpoints

This module also re-exports commonly used types and functions for backward
compatibility with existing code.
"""

from __future__ import annotations

from fastapi import APIRouter

# Import sub-routers
from .autopilot_routes import router as autopilot_router
from .issue_routes import router as issue_router
from .runs_routes import router as runs_router

# Create the main router that aggregates all sub-routers
# The server mounts this at /api, so we need /runs prefix here
router = APIRouter(prefix="/runs", tags=["runs"])

# Include sub-routers
# runs_router handles base /runs/* endpoints (CRUD, pause, resume, etc.)
router.include_router(runs_router)

# autopilot_router handles /runs/autopilot/* endpoints
router.include_router(autopilot_router, prefix="/autopilot")

# issue_router handles /runs/from-issue endpoint (already has the path in the route)
router.include_router(issue_router)


# =============================================================================
# Backward Compatibility Exports
#
# These re-exports ensure existing code that imports from this module
# continues to work. New code should import directly from the source modules.
# =============================================================================

# Re-export RunStateManager and get_state_manager for backward compatibility
from ..services.run_state import RunStateManager, get_state_manager

# For backward compatibility, alias the old private function
_get_state_manager = get_state_manager

# Re-export Pydantic models from runs_routes
from .runs_routes import (
    InjectRequest,
    InterruptionFrameResponse,
    InterruptionStackResponse,
    InterruptRequest,
    PauseRequest,
    ResumeRequest,
    RunActionResponse,
    RunListResponse,
    RunStartRequest,
    RunStartResponse,
    RunState,
    RunSummary,
    StopReportInfo,
    StopRequest,
    StopResponse,
)

# Re-export Pydantic models from autopilot_routes
from .autopilot_routes import (
    AutopilotStartRequest,
    AutopilotStartResponse,
    AutopilotStatusResponse,
    AutopilotStopRequest,
    WisdomApplyResultResponse,
)

# Re-export Pydantic models from issue_routes
from .issue_routes import (
    IssueIngestionRequest,
    IssueIngestionResponse,
    IssueSnapshot,
)

# Re-export autopilot controller getter for backward compatibility
from .autopilot_routes import _get_autopilot_controller

__all__ = [
    # Main router
    "router",
    # Services
    "RunStateManager",
    "get_state_manager",
    "_get_state_manager",  # Deprecated alias
    # Run models
    "RunStartRequest",
    "RunStartResponse",
    "RunSummary",
    "RunListResponse",
    "RunState",
    "RunActionResponse",
    "InjectRequest",
    "InterruptRequest",
    "PauseRequest",
    "ResumeRequest",
    "StopRequest",
    "StopReportInfo",
    "StopResponse",
    "InterruptionFrameResponse",
    "InterruptionStackResponse",
    # Autopilot models
    "AutopilotStartRequest",
    "AutopilotStartResponse",
    "AutopilotStatusResponse",
    "AutopilotStopRequest",
    "WisdomApplyResultResponse",
    "_get_autopilot_controller",
    # Issue models
    "IssueIngestionRequest",
    "IssueIngestionResponse",
    "IssueSnapshot",
]
