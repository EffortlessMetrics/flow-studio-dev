#!/usr/bin/env python3
"""
record_event.py - Record RunEvents from Claude flows into the runtime event stream.

This CLI tool allows Claude flows (slash commands) to emit structured RunEvents
that appear in Flow Studio's Events Timeline, bridging the gap between Claude's
black-box execution and the runtime's observability layer.

Usage:
    # Record a step start event
    uv run swarm/tools/record_event.py \
        --run-id "run-20251208-143022-abc123" \
        --flow-key "build" \
        --step-id "author_tests" \
        --kind "step_start"

    # Record a critic result with payload
    uv run swarm/tools/record_event.py \
        --run-id "$RUN_ID" \
        --flow-key "build" \
        --step-id "author_tests" \
        --agent-key "test-critic" \
        --kind "critic_result" \
        --payload '{"status": "UNVERIFIED", "can_further_iteration_help": true}'

    # Record from payload file
    uv run swarm/tools/record_event.py \
        --run-id "$RUN_ID" \
        --flow-key "build" \
        --kind "llm_step_complete" \
        --payload-file /tmp/step_result.json

Event Kinds:
    step_start      - Step execution beginning
    step_end        - Step execution completed successfully
    step_error      - Step execution failed
    critic_result   - Critic verdict (include status, can_further_iteration_help)
    loop_iteration  - Microloop iteration boundary
    llm_step_complete - LLM step finished (can include transcript_path in payload)
    artifact_written - Artifact file created
    log             - General log message

Exit Codes:
    0 - Event recorded successfully
    1 - Error (missing args, invalid JSON, storage error)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# Add parent path for imports when running directly
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from swarm.runtime import storage
from swarm.runtime.types import RunEvent


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Record a RunEvent from Claude flows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--run-id",
        required=True,
        help="The run identifier (e.g., run-20251208-143022-abc123)",
    )
    parser.add_argument(
        "--flow-key",
        required=True,
        help="The flow key (signal, plan, build, gate, deploy, wisdom)",
    )
    parser.add_argument(
        "--step-id",
        required=False,
        default=None,
        help="Optional step identifier within the flow",
    )
    parser.add_argument(
        "--agent-key",
        required=False,
        default=None,
        help="Optional agent key that produced this event",
    )
    parser.add_argument(
        "--kind",
        required=True,
        help="Event kind (step_start, step_end, critic_result, etc.)",
    )
    parser.add_argument(
        "--payload",
        required=False,
        default=None,
        help='Inline JSON payload (e.g., \'{"status": "VERIFIED"}\')',
    )
    parser.add_argument(
        "--payload-file",
        required=False,
        default=None,
        help="Path to JSON file containing event payload",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress success output",
    )

    return parser.parse_args()


def load_payload(
    inline_payload: Optional[str],
    payload_file: Optional[str],
) -> Dict[str, Any]:
    """Load payload from inline JSON or file.

    Args:
        inline_payload: JSON string passed via --payload
        payload_file: Path to JSON file passed via --payload-file

    Returns:
        Parsed payload dictionary.

    Raises:
        ValueError: If JSON parsing fails.
    """
    if payload_file:
        try:
            with open(payload_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {payload_file}: {e}") from e
        except FileNotFoundError:
            raise ValueError(f"Payload file not found: {payload_file}")

    if inline_payload:
        try:
            return json.loads(inline_payload)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid inline JSON: {e}") from e

    return {}


def record_event(
    run_id: str,
    flow_key: str,
    kind: str,
    step_id: Optional[str] = None,
    agent_key: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> RunEvent:
    """Create and persist a RunEvent.

    Args:
        run_id: The run identifier.
        flow_key: The flow key.
        kind: Event kind.
        step_id: Optional step identifier.
        agent_key: Optional agent key.
        payload: Optional event payload.

    Returns:
        The created RunEvent.

    Raises:
        RuntimeError: If event cannot be persisted.
    """
    event = RunEvent(
        run_id=run_id,
        ts=datetime.now(timezone.utc),
        kind=kind,
        flow_key=flow_key,
        step_id=step_id,
        agent_key=agent_key,
        payload=payload or {},
    )

    try:
        storage.append_event(run_id, event)
    except Exception as e:
        raise RuntimeError(f"Failed to persist event: {e}") from e

    return event


def main() -> int:
    """Main entry point."""
    args = parse_args()

    try:
        payload = load_payload(args.payload, args.payload_file)
    except ValueError as e:
        print(f"Error loading payload: {e}", file=sys.stderr)
        return 1

    try:
        event = record_event(
            run_id=args.run_id,
            flow_key=args.flow_key,
            kind=args.kind,
            step_id=args.step_id,
            agent_key=args.agent_key,
            payload=payload,
        )
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not args.quiet:
        ts_str = event.ts.strftime("%H:%M:%S")
        agent_str = f" [{args.agent_key}]" if args.agent_key else ""
        step_str = f" step={args.step_id}" if args.step_id else ""
        print(f"[{ts_str}] Recorded: {args.kind}{agent_str}{step_str} -> {args.run_id}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
