"""
types.py - Core type definitions for the RunService architecture

This module provides the foundational data types for the swarm runtime system.
It defines the contracts for representing runs, events, specifications, and
backend capabilities used throughout the RunService and its components.

All types use dataclasses with full type annotations to ensure consistency
and enable static type checking across the runtime layer.

Usage:
    from swarm.runtime.types import (
        RunId, BackendId, RunStatus, SDLCStatus,
        RunSpec, RunSummary, RunEvent, BackendCapabilities,
        generate_run_id,
        run_spec_to_dict, run_spec_from_dict,
        run_summary_to_dict, run_summary_from_dict,
        run_event_to_dict, run_event_from_dict,
    )
"""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

# Type aliases
RunId = str
BackendId = Literal[
    "claude-harness",
    "claude-agent-sdk",
    "claude-step-orchestrator",
    "gemini-cli",
    "gemini-step-orchestrator",
    "custom-cli",
]


class RunStatus(str, Enum):
    """Status of a run's execution lifecycle."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class SDLCStatus(str, Enum):
    """Status reflecting SDLC health/quality outcome."""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class RunSpec:
    """Specification for starting a new run.

    Captures the intent of what should be executed, including which flows
    to run, which profile to use, which backend to execute on, and any
    additional parameters needed by the backend.

    Attributes:
        flow_keys: List of flow keys to execute (e.g., ["signal", "build"]).
        profile_id: Optional profile ID from profile_registry.
        backend: Backend identifier for execution.
        initiator: Source of the run ("cli", "flow-studio", "api", "ci").
        params: Arbitrary per-backend extra parameters.
    """

    flow_keys: List[str]
    profile_id: Optional[str] = None
    backend: BackendId = "claude-harness"
    initiator: str = "cli"
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RunSummary:
    """Summary of a run's current state.

    Provides a comprehensive view of a run including its specification,
    status, timing, errors, artifacts, and teaching/exemplar metadata.

    Attributes:
        id: Unique run identifier.
        spec: The original run specification.
        status: Current execution status.
        sdlc_status: SDLC quality/health outcome.
        created_at: When the run was created.
        updated_at: When the run was last updated.
        started_at: When execution actually started (None if pending).
        completed_at: When execution finished (None if not complete).
        error: Error message if failed (None otherwise).
        artifacts: Dictionary of produced artifacts by flow/step.
        is_exemplar: Whether this run is marked as a teaching example.
        tags: List of tags for categorization and filtering.
    """

    id: RunId
    spec: RunSpec
    status: RunStatus
    sdlc_status: SDLCStatus
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    artifacts: Dict[str, Any] = field(default_factory=dict)
    is_exemplar: bool = False
    tags: List[str] = field(default_factory=list)
    title: Optional[str] = None  # Human-readable run title
    path: Optional[str] = None  # Filesystem path to run directory
    description: Optional[str] = None  # Human-readable run description


@dataclass
class RunEvent:
    """A single event in a run's timeline.

    Represents an observable occurrence during run execution, enabling
    streaming updates, debugging, and audit trails.

    Attributes:
        run_id: The run this event belongs to.
        ts: Timestamp of the event.
        kind: Event type (e.g., "tool_start", "tool_end", "step_start",
              "step_end", "log", "error").
        flow_key: The flow this event occurred in.
        step_id: Optional step identifier within the flow.
        agent_key: Optional agent that produced this event.
        payload: Arbitrary event-specific data.
    """

    run_id: RunId
    ts: datetime
    kind: str
    flow_key: str
    step_id: Optional[str] = None
    agent_key: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BackendCapabilities:
    """Describes what a backend can do.

    Used to communicate backend features to the UI and orchestration
    layers so they can adapt behavior accordingly.

    Attributes:
        id: Backend identifier.
        label: Human-readable backend name.
        supports_streaming: Whether the backend can stream events.
        supports_events: Whether the backend emits structured events.
        supports_cancel: Whether runs can be canceled mid-execution.
        supports_replay: Whether past runs can be replayed.
    """

    id: BackendId
    label: str
    supports_streaming: bool = False
    supports_events: bool = True
    supports_cancel: bool = False
    supports_replay: bool = False


# -----------------------------------------------------------------------------
# Run ID Generation
# -----------------------------------------------------------------------------


def generate_run_id() -> RunId:
    """Generate a unique run ID.

    Creates IDs in the format: run-YYYYMMDD-HHMMSS-xxxxxx
    where xxxxxx is a random 6-character alphanumeric suffix.

    Returns:
        A unique run identifier string.

    Example:
        >>> run_id = generate_run_id()
        >>> run_id  # e.g., "run-20251208-143022-abc123"
    """
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    suffix = "".join(
        secrets.choice(string.ascii_lowercase + string.digits) for _ in range(6)
    )
    return f"run-{timestamp}-{suffix}"


# -----------------------------------------------------------------------------
# Serialization Helpers
# -----------------------------------------------------------------------------


def _datetime_to_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO format string with Z suffix."""
    if dt is None:
        return None
    return dt.isoformat() + "Z" if not dt.isoformat().endswith("Z") else dt.isoformat()


def _iso_to_datetime(iso_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO format string to datetime."""
    if iso_str is None:
        return None
    # Remove Z suffix if present for parsing
    if iso_str.endswith("Z"):
        iso_str = iso_str[:-1]
    return datetime.fromisoformat(iso_str)


def run_spec_to_dict(spec: RunSpec) -> Dict[str, Any]:
    """Convert RunSpec to a dictionary for serialization.

    Args:
        spec: The RunSpec to convert.

    Returns:
        Dictionary representation suitable for JSON/YAML serialization.
    """
    return {
        "flow_keys": list(spec.flow_keys),
        "profile_id": spec.profile_id,
        "backend": spec.backend,
        "initiator": spec.initiator,
        "params": dict(spec.params),
    }


def run_spec_from_dict(data: Dict[str, Any]) -> RunSpec:
    """Parse RunSpec from a dictionary.

    Args:
        data: Dictionary with RunSpec fields.

    Returns:
        Parsed RunSpec instance.
    """
    return RunSpec(
        flow_keys=list(data.get("flow_keys", [])),
        profile_id=data.get("profile_id"),
        backend=data.get("backend", "claude-harness"),
        initiator=data.get("initiator", "unknown"),
        params=dict(data.get("params", {})),
    )


def run_summary_to_dict(summary: RunSummary) -> Dict[str, Any]:
    """Convert RunSummary to a dictionary for serialization.

    Args:
        summary: The RunSummary to convert.

    Returns:
        Dictionary representation suitable for JSON/YAML serialization.
    """
    return {
        "id": summary.id,
        "spec": run_spec_to_dict(summary.spec),
        "status": summary.status.value,
        "sdlc_status": summary.sdlc_status.value,
        "created_at": _datetime_to_iso(summary.created_at),
        "updated_at": _datetime_to_iso(summary.updated_at),
        "started_at": _datetime_to_iso(summary.started_at),
        "completed_at": _datetime_to_iso(summary.completed_at),
        "error": summary.error,
        "artifacts": dict(summary.artifacts),
        "is_exemplar": summary.is_exemplar,
        "tags": list(summary.tags),
        "title": summary.title,
        "path": summary.path,
        "description": summary.description,
    }


def run_summary_from_dict(data: Dict[str, Any]) -> RunSummary:
    """Parse RunSummary from a dictionary.

    Args:
        data: Dictionary with RunSummary fields.

    Returns:
        Parsed RunSummary instance.
    """
    now = datetime.now(timezone.utc)
    return RunSummary(
        id=data.get("id", ""),
        spec=run_spec_from_dict(data.get("spec", {})),
        status=RunStatus(data.get("status", "pending")),
        sdlc_status=SDLCStatus(data.get("sdlc_status", "unknown")),
        created_at=_iso_to_datetime(data.get("created_at")) or now,
        updated_at=_iso_to_datetime(data.get("updated_at")) or now,
        started_at=_iso_to_datetime(data.get("started_at")),
        completed_at=_iso_to_datetime(data.get("completed_at")),
        error=data.get("error"),
        artifacts=dict(data.get("artifacts", {})),
        is_exemplar=data.get("is_exemplar", False),
        tags=list(data.get("tags", [])),
        title=data.get("title"),
        path=data.get("path"),
        description=data.get("description"),
    )


def run_event_to_dict(event: RunEvent) -> Dict[str, Any]:
    """Convert RunEvent to a dictionary for serialization.

    Args:
        event: The RunEvent to convert.

    Returns:
        Dictionary representation suitable for JSON/YAML serialization.
    """
    return {
        "run_id": event.run_id,
        "ts": _datetime_to_iso(event.ts),
        "kind": event.kind,
        "flow_key": event.flow_key,
        "step_id": event.step_id,
        "agent_key": event.agent_key,
        "payload": dict(event.payload),
    }


def run_event_from_dict(data: Dict[str, Any]) -> RunEvent:
    """Parse RunEvent from a dictionary.

    Args:
        data: Dictionary with RunEvent fields.

    Returns:
        Parsed RunEvent instance.
    """
    return RunEvent(
        run_id=data.get("run_id", ""),
        ts=_iso_to_datetime(data.get("ts")) or datetime.now(timezone.utc),
        kind=data.get("kind", "unknown"),
        flow_key=data.get("flow_key", ""),
        step_id=data.get("step_id"),
        agent_key=data.get("agent_key"),
        payload=dict(data.get("payload", {})),
    )
