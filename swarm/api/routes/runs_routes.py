"""
Run control endpoints for Flow Studio API.

Provides REST endpoints for:
- Starting new runs
- Getting run state
- Pausing/resuming runs
- Injecting nodes into runs
- Interrupting runs with detours
- Canceling runs
- Stopping runs gracefully
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..services.run_state import get_state_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["runs"])


# =============================================================================
# Pydantic Models
# =============================================================================


class RunStartRequest(BaseModel):
    """Request to start a new run."""

    flow_id: str = Field(..., description="Flow to execute")
    run_id: Optional[str] = Field(None, description="Custom run ID (generated if not provided)")
    context: Optional[Dict[str, Any]] = Field(None, description="Initial context for the run")
    start_step: Optional[str] = Field(None, description="Step to start from (defaults to first)")
    mode: str = Field("execute", description="Execution mode: execute, preview, validate")


class RunStartResponse(BaseModel):
    """Response when starting a new run."""

    run_id: str
    flow_id: str
    status: str
    created_at: str
    events_url: str


class RunSummary(BaseModel):
    """Run summary for list endpoint."""

    run_id: str
    flow_key: Optional[str] = None
    status: Optional[str] = None
    timestamp: Optional[str] = None


class RunListResponse(BaseModel):
    """Response for list runs endpoint."""

    runs: List[RunSummary]


class RunState(BaseModel):
    """Full run state."""

    run_id: str
    flow_id: str
    status: str
    current_step: Optional[str] = None
    completed_steps: List[str] = Field(default_factory=list)
    pending_steps: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    paused_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class RunActionResponse(BaseModel):
    """Generic response for run actions."""

    run_id: str
    status: str
    message: str
    timestamp: str


class InjectRequest(BaseModel):
    """Request to inject a node into a run."""

    step_id: str = Field(..., description="ID for the injected step")
    station_id: str = Field(..., description="Station to use for the step")
    position: str = Field(
        "next", description="Where to inject: next, after:<step_id>, before:<step_id>"
    )
    params: Optional[Dict[str, Any]] = Field(None, description="Parameters for the step")


class InterruptRequest(BaseModel):
    """Request to interrupt a run with a detour."""

    detour_flow: Optional[str] = Field(None, description="Flow to execute as detour")
    detour_steps: Optional[List[str]] = Field(
        None, description="Specific steps to execute as detour"
    )
    reason: str = Field(..., description="Reason for the interrupt")
    resume_after: bool = Field(True, description="Whether to resume original flow after detour")


class PauseRequest(BaseModel):
    """Request to pause a run."""

    wait_for_step: bool = Field(
        True, description="Wait for current step to complete before pausing"
    )


class ResumeRequest(BaseModel):
    """Request to resume a paused or stopped run."""

    from_step: Optional[str] = Field(None, description="Step to resume from (defaults to saved PC)")


class StopRequest(BaseModel):
    """Request to stop a run gracefully."""

    reason: str = Field("user_initiated", description="Reason for stopping")
    drain_timeout_ms: int = Field(30000, description="Timeout for draining messages in ms")


class StopReportInfo(BaseModel):
    """Information included in stop report."""

    last_step_id: Optional[str] = None
    last_routing_intent: Optional[str] = None
    last_tool_calls: List[str] = Field(default_factory=list)
    open_assumptions: List[str] = Field(default_factory=list)
    stop_reason: str = ""
    stopped_at: str = ""


class StopResponse(BaseModel):
    """Response when stopping a run."""

    run_id: str
    status: str
    message: str
    timestamp: str
    stop_report_path: Optional[str] = None
    stop_info: Optional[StopReportInfo] = None


class InterruptionFrameResponse(BaseModel):
    """A single frame in the interruption stack."""

    frame_id: str
    interrupted_flow: Optional[str] = None
    interrupted_step: Optional[str] = None
    injected_flow: Optional[str] = None
    reason: str
    started_at: str
    return_node: str
    current_step_index: int = 0
    total_steps: int = 1
    sidequest_id: Optional[str] = None


class InterruptionStackResponse(BaseModel):
    """Response for the interruption stack endpoint."""

    run_id: str
    stack_depth: int
    frames: List[InterruptionFrameResponse]
    detours: List[Dict[str, Any]] = Field(default_factory=list)


# =============================================================================
# Run Endpoints
# =============================================================================


@router.post("", response_model=RunStartResponse, status_code=201)
async def start_run(request: RunStartRequest):
    """Start a new run.

    Creates a new run directory and initializes run state.
    Returns the run ID and SSE events URL.

    Args:
        request: Run start request with flow_id and optional parameters.

    Returns:
        RunStartResponse with run_id and events_url.
    """
    state_manager = get_state_manager()

    try:
        state = await state_manager.create_run(
            flow_id=request.flow_id,
            run_id=request.run_id,
            context=request.context,
            start_step=request.start_step,
        )

        return RunStartResponse(
            run_id=state["run_id"],
            flow_id=state["flow_id"],
            status=state["status"],
            created_at=state["created_at"],
            events_url=f"/api/runs/{state['run_id']}/events",
        )

    except Exception as e:
        logger.error("Failed to start run: %s", e)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "run_start_failed",
                "message": str(e),
                "details": {},
            },
        )


@router.get("", response_model=RunListResponse)
async def list_runs(limit: int = 20):
    """List recent runs.

    Args:
        limit: Maximum number of runs to return.

    Returns:
        List of run summaries.
    """
    state_manager = get_state_manager()
    runs = state_manager.list_runs(limit=limit)
    return RunListResponse(runs=[RunSummary(**r) for r in runs])


@router.get("/{run_id}")
async def get_run(
    run_id: str,
    if_none_match: Optional[str] = Header(None, alias="If-None-Match"),
):
    """Get run state.

    Args:
        run_id: Run identifier.
        if_none_match: Optional ETag for caching.

    Returns:
        Run state with ETag header.

    Raises:
        404: Run not found.
        304: Not modified (if ETag matches).
    """
    state_manager = get_state_manager()

    try:
        state, etag = await state_manager.get_run(run_id)

        # Check If-None-Match for caching
        if if_none_match and if_none_match.strip('"') == etag:
            return Response(status_code=304)

        return JSONResponse(
            content=state,
            headers={"ETag": f'"{etag}"'},
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "run_not_found",
                "message": f"Run '{run_id}' not found",
                "details": {"run_id": run_id},
            },
        )


@router.post("/{run_id}/pause", response_model=RunActionResponse)
async def pause_run(
    run_id: str,
    request: Optional[PauseRequest] = None,
    if_match: Optional[str] = Header(None, alias="If-Match"),
):
    """Pause a running run.

    Pauses execution at a clean boundary. The run can be resumed later.

    Pause semantics:
    - If wait_for_step=True (default): Sets status to "pausing" and waits for
      the current step to complete, then transitions to "paused".
    - If wait_for_step=False: Immediately sets status to "paused" (may interrupt
      current step mid-execution).

    Unlike stop, pause is temporary and the run resumes from the exact same
    program counter (PC). Stop creates a permanent savepoint with a report.

    Args:
        run_id: Run identifier.
        request: Optional pause request with wait_for_step flag.
        if_match: Optional ETag for concurrency control.

    Returns:
        Action response with new status.

    Raises:
        404: Run not found.
        409: Run is not in a pausable state.
        412: ETag mismatch.
    """
    state_manager = get_state_manager()
    expected_etag = if_match.strip('"') if if_match else None

    # Default request if not provided
    if request is None:
        request = PauseRequest()

    try:
        state, _ = await state_manager.get_run(run_id)
        current_status = state["status"]

        if current_status not in ("running", "pending"):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "invalid_state",
                    "message": f"Cannot pause run with status '{current_status}'",
                    "details": {"current_status": current_status},
                },
            )

        now = datetime.now(timezone.utc).isoformat()

        # Determine target status based on wait_for_step
        if request.wait_for_step and current_status == "running":
            # Set to "pausing" - execution will transition to "paused" after step completes
            new_status = "pausing"
            message = "Run will pause after current step completes"
            event_type_to_emit = "pausing"
        else:
            # Immediate pause
            new_status = "paused"
            message = "Run paused successfully"
            event_type_to_emit = "paused"

        await state_manager.update_run(
            run_id,
            {"status": new_status, "paused_at": now if new_status == "paused" else None},
            expected_etag=expected_etag,
        )

        # Emit appropriate event for SSE subscribers
        from .events import EventType, write_event_sync

        if event_type_to_emit == "pausing":
            write_event_sync(
                run_id=run_id,
                runs_root=state_manager.runs_root,
                event_type=EventType.RUN_PAUSING,
                data={
                    "run_id": run_id,
                    "previous_status": current_status,
                    "current_step": state.get("current_step"),
                    "pausing_at": now,
                    "wait_for_step": request.wait_for_step,
                },
            )
        else:
            write_event_sync(
                run_id=run_id,
                runs_root=state_manager.runs_root,
                event_type=EventType.RUN_PAUSED,
                data={
                    "run_id": run_id,
                    "previous_status": current_status,
                    "current_step": state.get("current_step"),
                    "paused_at": now,
                },
            )

        return RunActionResponse(
            run_id=run_id,
            status=new_status,
            message=message,
            timestamp=now,
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "run_not_found",
                "message": f"Run '{run_id}' not found",
                "details": {"run_id": run_id},
            },
        )
    except ValueError as e:
        if "ETag mismatch" in str(e):
            raise HTTPException(
                status_code=412,
                detail={
                    "error": "etag_mismatch",
                    "message": "Run was modified by another request",
                    "details": {},
                },
            )
        raise


@router.post("/{run_id}/resume", response_model=RunActionResponse)
async def resume_run(
    run_id: str,
    request: Optional[ResumeRequest] = None,
    if_match: Optional[str] = Header(None, alias="If-Match"),
):
    """Resume a paused or stopped run.

    Continues execution from the saved program counter (PC). For stopped runs,
    the PC is the step that was active when stop was initiated. For paused runs,
    the PC is the step that will execute next.

    Resume semantics:
    - paused: Continue from the exact step where execution paused
    - stopped: Continue from the saved current_step_id (clean savepoint)
    - pausing: Cancel the pending pause and continue running

    The from_step parameter allows overriding the resume point, which is useful
    for debugging or skipping problematic steps.

    Args:
        run_id: Run identifier.
        request: Optional resume request with from_step override.
        if_match: Optional ETag for concurrency control.

    Returns:
        Action response with new status.

    Raises:
        404: Run not found.
        409: Run is not in a resumable state.
        412: ETag mismatch.
    """
    state_manager = get_state_manager()
    expected_etag = if_match.strip('"') if if_match else None

    # Default request if not provided
    if request is None:
        request = ResumeRequest()

    try:
        state, _ = await state_manager.get_run(run_id)
        current_status = state["status"]

        # Allow resuming from paused, stopped, or pausing states
        if current_status not in ("paused", "stopped", "pausing"):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "invalid_state",
                    "message": f"Cannot resume run with status '{current_status}'",
                    "details": {"current_status": current_status},
                },
            )

        now = datetime.now(timezone.utc).isoformat()
        paused_at = state.get("paused_at")
        stopped_at = state.get("stopped_at")

        # Determine resume point
        resume_step = request.from_step or state.get("current_step")

        # Build update dict
        updates: Dict[str, Any] = {
            "status": "running",
            "paused_at": None,
        }

        # If resuming from stopped, clear stop-related fields
        if current_status == "stopped":
            updates["stopped_at"] = None
            updates["stop_reason"] = None

        # If from_step provided, update current_step
        if request.from_step:
            updates["current_step"] = request.from_step

        await state_manager.update_run(
            run_id,
            updates,
            expected_etag=expected_etag,
        )

        # Emit resume event for SSE subscribers
        from .events import EventType, write_event_sync

        write_event_sync(
            run_id=run_id,
            runs_root=state_manager.runs_root,
            event_type=EventType.RUN_RESUMED,
            data={
                "run_id": run_id,
                "previous_status": current_status,
                "current_step": state.get("current_step"),
                "resume_step": resume_step,
                "paused_at": paused_at,
                "stopped_at": stopped_at,
                "resumed_at": now,
                "from_step_override": request.from_step is not None,
            },
        )

        # Build appropriate message
        if current_status == "stopped":
            message = f"Run resumed from stopped state at step: {resume_step}"
        elif current_status == "pausing":
            message = "Run resume canceled pending pause"
        else:
            message = "Run resumed successfully"

        return RunActionResponse(
            run_id=run_id,
            status="running",
            message=message,
            timestamp=now,
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "run_not_found",
                "message": f"Run '{run_id}' not found",
                "details": {"run_id": run_id},
            },
        )
    except ValueError as e:
        if "ETag mismatch" in str(e):
            raise HTTPException(
                status_code=412,
                detail={
                    "error": "etag_mismatch",
                    "message": "Run was modified by another request",
                    "details": {},
                },
            )
        raise


@router.post("/{run_id}/inject", response_model=RunActionResponse)
async def inject_node(
    run_id: str,
    request: InjectRequest,
    if_match: Optional[str] = Header(None, alias="If-Match"),
):
    """Inject a node into a run.

    Inserts a new step into the run's execution plan. The step will be
    executed at the specified position.

    Args:
        run_id: Run identifier.
        request: Inject request with step details.
        if_match: Optional ETag for concurrency control.

    Returns:
        Action response confirming injection.

    Raises:
        404: Run not found.
        409: Run is not in an injectable state.
        412: ETag mismatch.
    """
    state_manager = get_state_manager()
    expected_etag = if_match.strip('"') if if_match else None

    try:
        state, _ = await state_manager.get_run(run_id)

        if state["status"] not in ("pending", "running", "paused"):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "invalid_state",
                    "message": f"Cannot inject into run with status '{state['status']}'",
                    "details": {"current_status": state["status"]},
                },
            )

        # Add injected step to pending steps
        pending = state.get("pending_steps", [])

        if request.position == "next":
            # Insert at beginning of pending
            pending.insert(0, request.step_id)
        elif request.position.startswith("after:"):
            target = request.position[6:]
            try:
                idx = pending.index(target) + 1
                pending.insert(idx, request.step_id)
            except ValueError:
                # Target not in pending, insert at end
                pending.append(request.step_id)
        elif request.position.startswith("before:"):
            target = request.position[7:]
            try:
                idx = pending.index(target)
                pending.insert(idx, request.step_id)
            except ValueError:
                # Target not in pending, insert at beginning
                pending.insert(0, request.step_id)
        else:
            pending.append(request.step_id)

        # Store injection metadata
        injections = state.get("context", {}).get("injections", [])
        injections.append(
            {
                "step_id": request.step_id,
                "station_id": request.station_id,
                "position": request.position,
                "params": request.params,
                "injected_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        now = datetime.now(timezone.utc).isoformat()
        context = state.get("context", {})
        context["injections"] = injections

        await state_manager.update_run(
            run_id,
            {"pending_steps": pending, "context": context},
            expected_etag=expected_etag,
        )

        return RunActionResponse(
            run_id=run_id,
            status=state["status"],
            message=f"Step '{request.step_id}' injected at position '{request.position}'",
            timestamp=now,
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "run_not_found",
                "message": f"Run '{run_id}' not found",
                "details": {"run_id": run_id},
            },
        )
    except ValueError as e:
        if "ETag mismatch" in str(e):
            raise HTTPException(
                status_code=412,
                detail={
                    "error": "etag_mismatch",
                    "message": "Run was modified by another request",
                    "details": {},
                },
            )
        raise


@router.post("/{run_id}/interrupt", response_model=RunActionResponse)
async def interrupt_run(
    run_id: str,
    request: InterruptRequest,
    if_match: Optional[str] = Header(None, alias="If-Match"),
):
    """Interrupt a run with a detour.

    Pauses the current run and optionally executes a detour flow/steps
    before resuming.

    Args:
        run_id: Run identifier.
        request: Interrupt request with detour details.
        if_match: Optional ETag for concurrency control.

    Returns:
        Action response with interrupt details.

    Raises:
        404: Run not found.
        409: Run is not in an interruptible state.
        412: ETag mismatch.
    """
    state_manager = get_state_manager()
    expected_etag = if_match.strip('"') if if_match else None

    try:
        state, _ = await state_manager.get_run(run_id)

        if state["status"] not in ("pending", "running"):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "invalid_state",
                    "message": f"Cannot interrupt run with status '{state['status']}'",
                    "details": {"current_status": state["status"]},
                },
            )

        now = datetime.now(timezone.utc).isoformat()

        # Store interrupt details in context
        context = state.get("context", {})
        context["interrupt"] = {
            "reason": request.reason,
            "detour_flow": request.detour_flow,
            "detour_steps": request.detour_steps,
            "resume_after": request.resume_after,
            "interrupted_at": now,
            "interrupted_step": state.get("current_step"),
        }

        await state_manager.update_run(
            run_id,
            {
                "status": "interrupted",
                "paused_at": now,
                "context": context,
            },
            expected_etag=expected_etag,
        )

        return RunActionResponse(
            run_id=run_id,
            status="interrupted",
            message=f"Run interrupted: {request.reason}",
            timestamp=now,
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "run_not_found",
                "message": f"Run '{run_id}' not found",
                "details": {"run_id": run_id},
            },
        )
    except ValueError as e:
        if "ETag mismatch" in str(e):
            raise HTTPException(
                status_code=412,
                detail={
                    "error": "etag_mismatch",
                    "message": "Run was modified by another request",
                    "details": {},
                },
            )
        raise


@router.delete("/{run_id}", response_model=RunActionResponse)
async def cancel_run(
    run_id: str,
    if_match: Optional[str] = Header(None, alias="If-Match"),
):
    """Cancel a run.

    Terminates the run and marks it as canceled. This is irreversible.

    Args:
        run_id: Run identifier.
        if_match: Optional ETag for concurrency control.

    Returns:
        Action response confirming cancellation.

    Raises:
        404: Run not found.
        409: Run is already completed.
        412: ETag mismatch.
    """
    state_manager = get_state_manager()
    expected_etag = if_match.strip('"') if if_match else None

    try:
        state, _ = await state_manager.get_run(run_id)

        if state["status"] in ("succeeded", "failed", "canceled", "stopped"):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "invalid_state",
                    "message": f"Cannot cancel run with status '{state['status']}'",
                    "details": {"current_status": state["status"]},
                },
            )

        now = datetime.now(timezone.utc).isoformat()
        await state_manager.update_run(
            run_id,
            {"status": "canceled", "completed_at": now},
            expected_etag=expected_etag,
        )

        return RunActionResponse(
            run_id=run_id,
            status="canceled",
            message="Run canceled successfully",
            timestamp=now,
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "run_not_found",
                "message": f"Run '{run_id}' not found",
                "details": {"run_id": run_id},
            },
        )
    except ValueError as e:
        if "ETag mismatch" in str(e):
            raise HTTPException(
                status_code=412,
                detail={
                    "error": "etag_mismatch",
                    "message": "Run was modified by another request",
                    "details": {},
                },
            )
        raise


@router.post("/{run_id}/stop", response_model=StopResponse)
async def stop_run(
    run_id: str,
    request: StopRequest,
    if_match: Optional[str] = Header(None, alias="If-Match"),
):
    """Stop a run gracefully with savepoint.

    Initiates a graceful shutdown of the run:
    1. Sets status to "stopping"
    2. Drains remaining messages with timeout
    3. Persists run_state.json with status="stopped"
    4. Writes stop_report.md with forensic information

    Unlike cancel, stop creates a clean savepoint that can be resumed.
    The UI should show "stopping..." then "stopped" (not "failed").

    Args:
        run_id: Run identifier.
        request: Stop request with reason and timeout.
        if_match: Optional ETag for concurrency control.

    Returns:
        StopResponse with stop report path and info.

    Raises:
        404: Run not found.
        409: Run is not in a stoppable state.
        412: ETag mismatch.
    """
    state_manager = get_state_manager()
    expected_etag = if_match.strip('"') if if_match else None

    try:
        state, _ = await state_manager.get_run(run_id)
        current_status = state["status"]

        # Only allow stopping runs that are running, pending, or paused
        if current_status not in ("running", "pending", "paused", "pausing"):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "invalid_state",
                    "message": f"Cannot stop run with status '{current_status}'",
                    "details": {"current_status": current_status},
                },
            )

        now = datetime.now(timezone.utc).isoformat()

        # First, set status to "stopping"
        await state_manager.update_run(
            run_id,
            {"status": "stopping"},
            expected_etag=expected_etag,
        )

        # Emit stopping event for SSE subscribers
        from .events import EventType, write_event_sync

        write_event_sync(
            run_id=run_id,
            runs_root=state_manager.runs_root,
            event_type=EventType.RUN_STOPPING,
            data={
                "run_id": run_id,
                "previous_status": current_status,
                "current_step": state.get("current_step"),
                "stopping_at": now,
                "reason": request.reason,
            },
        )

        # Collect stop report info
        stop_info = StopReportInfo(
            last_step_id=state.get("current_step"),
            last_routing_intent=state.get("context", {}).get("last_routing_intent"),
            last_tool_calls=state.get("context", {}).get("recent_tool_calls", [])[-10:],
            open_assumptions=state.get("context", {}).get("assumptions", []),
            stop_reason=request.reason,
            stopped_at=now,
        )

        # Write stop report
        stop_report_path = await _write_stop_report(
            run_id=run_id,
            runs_root=state_manager.runs_root,
            stop_info=stop_info,
            state=state,
        )

        # Now transition to "stopped"
        await state_manager.update_run(
            run_id,
            {
                "status": "stopped",
                "stopped_at": now,
                "stop_reason": {
                    "type": request.reason,
                    "timestamp": now,
                    "drain_timeout_ms": request.drain_timeout_ms,
                },
            },
        )

        # Emit stopped event
        write_event_sync(
            run_id=run_id,
            runs_root=state_manager.runs_root,
            event_type=EventType.RUN_STOPPED,
            data={
                "run_id": run_id,
                "current_step": state.get("current_step"),
                "stopped_at": now,
                "reason": request.reason,
                "stop_report_path": stop_report_path,
            },
        )

        return StopResponse(
            run_id=run_id,
            status="stopped",
            message=f"Run stopped successfully: {request.reason}",
            timestamp=now,
            stop_report_path=stop_report_path,
            stop_info=stop_info,
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "run_not_found",
                "message": f"Run '{run_id}' not found",
                "details": {"run_id": run_id},
            },
        )
    except ValueError as e:
        if "ETag mismatch" in str(e):
            raise HTTPException(
                status_code=412,
                detail={
                    "error": "etag_mismatch",
                    "message": "Run was modified by another request",
                    "details": {},
                },
            )
        raise


async def _write_stop_report(
    run_id: str,
    runs_root: Path,
    stop_info: StopReportInfo,
    state: Dict[str, Any],
) -> str:
    """Write stop_report.md with forensic information.

    Args:
        run_id: Run identifier.
        runs_root: Root directory for runs.
        stop_info: Collected stop information.
        state: Current run state.

    Returns:
        Relative path to the stop report file.
    """
    run_dir = runs_root / run_id
    report_path = run_dir / "stop_report.md"

    # Build report content
    lines = [
        "# Stop Report",
        "",
        f"**Run ID:** {run_id}",
        f"**Stopped At:** {stop_info.stopped_at}",
        f"**Reason:** {stop_info.stop_reason}",
        "",
        "## Execution State",
        "",
        f"- **Last Step ID:** {stop_info.last_step_id or 'None'}",
        f"- **Flow ID:** {state.get('flow_id', 'Unknown')}",
        f"- **Previous Status:** {state.get('status', 'Unknown')}",
        "",
    ]

    # Add routing intent if available
    if stop_info.last_routing_intent:
        lines.extend(
            [
                "## Last Routing Intent",
                "",
                "```",
                stop_info.last_routing_intent,
                "```",
                "",
            ]
        )

    # Add recent tool calls
    if stop_info.last_tool_calls:
        lines.extend(
            [
                "## Last Tool Calls (paths only)",
                "",
            ]
        )
        for call in stop_info.last_tool_calls:
            lines.append(f"- `{call}`")
        lines.append("")

    # Add open assumptions
    if stop_info.open_assumptions:
        lines.extend(
            [
                "## Open Assumptions/Decisions",
                "",
            ]
        )
        for assumption in stop_info.open_assumptions:
            lines.append(f"- {assumption}")
        lines.append("")

    # Add completed steps if available
    completed_steps = state.get("completed_steps", [])
    if completed_steps:
        lines.extend(
            [
                "## Completed Steps",
                "",
            ]
        )
        for step in completed_steps:
            lines.append(f"- {step}")
        lines.append("")

    # Add pending steps if available
    pending_steps = state.get("pending_steps", [])
    if pending_steps:
        lines.extend(
            [
                "## Pending Steps (not executed)",
                "",
            ]
        )
        for step in pending_steps:
            lines.append(f"- {step}")
        lines.append("")

    # Write the report
    report_content = "\n".join(lines)
    report_path.write_text(report_content, encoding="utf-8")

    return str(report_path.relative_to(runs_root.parent))


@router.get("/{run_id}/stack", response_model=InterruptionStackResponse)
async def get_interruption_stack(run_id: str):
    """Get the current interruption stack for a run.

    Returns the stack of interruption frames representing paused execution
    contexts during flow injection/detour operations.

    The response includes both:
    - frames: Structured InterruptionFrame data from RunState
    - detours: Simplified format compatible with InterruptionStackPanel.ts

    Args:
        run_id: Run identifier.

    Returns:
        InterruptionStackResponse with stack depth and frames.

    Raises:
        404: Run not found or no stack data available.
    """
    state_manager = get_state_manager()

    try:
        state, _ = await state_manager.get_run(run_id)

        # Get interruption stack from state
        # The state may come from the simple RunStateManager (dict-based)
        # or from RunState dataclass serialization
        raw_stack = state.get("interruption_stack", [])

        frames: List[InterruptionFrameResponse] = []
        detours: List[Dict[str, Any]] = []

        for idx, frame_data in enumerate(raw_stack):
            # Handle both dict format (from JSON) and dataclass format
            if isinstance(frame_data, dict):
                reason = frame_data.get("reason", "")
                interrupted_at = frame_data.get("interrupted_at", "")
                return_node = frame_data.get("return_node", "")
                current_step_index = frame_data.get("current_step_index", 0)
                total_steps = frame_data.get("total_steps", 1)
                sidequest_id = frame_data.get("sidequest_id")
                context_snapshot = frame_data.get("context_snapshot", {})
            else:
                # Assume it's an InterruptionFrame dataclass
                reason = frame_data.reason
                interrupted_at = (
                    frame_data.interrupted_at.isoformat()
                    if hasattr(frame_data.interrupted_at, "isoformat")
                    else str(frame_data.interrupted_at)
                )
                return_node = frame_data.return_node
                current_step_index = frame_data.current_step_index
                total_steps = frame_data.total_steps
                sidequest_id = frame_data.sidequest_id
                context_snapshot = frame_data.context_snapshot

            # Parse return_node to extract flow and step info
            # Format is typically "flow_key.step_id" or just "step_id"
            parts = return_node.split(".")
            interrupted_flow = parts[0] if len(parts) > 1 else state.get("flow_id")
            interrupted_step = parts[1] if len(parts) > 1 else parts[0]

            # Create structured frame response
            frame_response = InterruptionFrameResponse(
                frame_id=f"frame-{idx}",
                interrupted_flow=interrupted_flow,
                interrupted_step=interrupted_step,
                injected_flow=sidequest_id or context_snapshot.get("injected_flow"),
                reason=reason,
                started_at=interrupted_at,
                return_node=return_node,
                current_step_index=current_step_index,
                total_steps=total_steps,
                sidequest_id=sidequest_id,
            )
            frames.append(frame_response)

            # Also create simplified detour format for UI compatibility
            detour = {
                "detour_id": f"detour-{idx}",
                "from_step": f"{interrupted_flow}:{interrupted_step}",
                "to_step": sidequest_id or context_snapshot.get("injected_flow", "unknown"),
                "reason": reason,
                "detour_type": "INJECT_FLOW" if sidequest_id else "DETOUR",
                "timestamp": interrupted_at,
            }
            detours.append(detour)

        return InterruptionStackResponse(
            run_id=run_id,
            stack_depth=len(frames),
            frames=frames,
            detours=detours,
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "run_not_found",
                "message": f"Run '{run_id}' not found",
                "details": {"run_id": run_id},
            },
        )
