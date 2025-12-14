#!/usr/bin/env python3
"""Demo stepwise backend execution.

This script runs stepwise demos with configurable backends, flows, and engine modes.
Used by make targets like `make demo-run-gemini-stepwise`.

Usage:
    uv run swarm/tools/demo_stepwise_run.py --backend gemini-step-orchestrator --flows signal,plan
    uv run swarm/tools/demo_stepwise_run.py --backend claude-step-orchestrator --flows signal
    uv run swarm/tools/demo_stepwise_run.py --backend claude-step-orchestrator --mode cli --flows build
    uv run swarm/tools/demo_stepwise_run.py --list-backends
    uv run swarm/tools/demo_stepwise_run.py --list-engines
    uv run swarm/tools/demo_stepwise_run.py --help

Engine Modes:
    stub  - Simulated execution for testing (default, no real API calls)
    sdk   - Claude Agent SDK execution (requires ANTHROPIC_API_KEY)
    cli   - Claude/Gemini CLI execution (requires installed CLI)

Environment Variables:
    SWARM_GEMINI_STUB=1              Force Gemini stub mode (default)
    SWARM_GEMINI_STUB=0              Use real Gemini CLI
    SWARM_CLAUDE_STEP_ENGINE_MODE    Set Claude engine mode (stub, sdk, cli)
    ANTHROPIC_API_KEY                Required for sdk mode
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from swarm.runtime.backends import get_backend, list_backends
from swarm.runtime.types import RunSpec, RunStatus


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run stepwise demo with specified backend",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--backend",
        choices=["gemini-step-orchestrator", "claude-step-orchestrator"],
        help="Backend to use for stepwise execution",
    )
    parser.add_argument(
        "--flows",
        help="Comma-separated flow keys (e.g., signal,plan,build)",
    )
    parser.add_argument(
        "--mode",
        choices=["stub", "sdk", "cli"],
        help="Engine mode: stub (simulated), sdk (Agent SDK), cli (CLI invocation)",
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=60,
        help="Maximum seconds to wait for completion (default: 60)",
    )
    parser.add_argument(
        "--list-backends",
        action="store_true",
        help="List available backends and exit",
    )
    parser.add_argument(
        "--list-engines",
        action="store_true",
        help="List available engines with their modes and exit",
    )
    args = parser.parse_args()

    if args.list_backends:
        print("Available stepwise backends:")
        for cap in list_backends():
            if "step" in cap.id:
                print(f"  {cap.id}: {cap.label}")
        return 0

    if args.list_engines:
        from swarm.runtime.engines import list_available_engines

        print("Available step engines:")
        for eng in list_available_engines():
            print(f"  {eng['id']}: {eng['label']}")
            print(f"    Modes: {', '.join(eng['modes'])}")
            print(f"    Default: {eng['default_mode']}")
            print(f"    Provider: {eng['provider']}")
        return 0

    # Validate required args when not listing backends
    if not args.backend:
        parser.error("--backend is required")
    if not args.flows:
        parser.error("--flows is required")

    # Set engine mode via environment if specified
    if args.mode:
        if "claude" in args.backend:
            os.environ["SWARM_CLAUDE_STEP_ENGINE_MODE"] = args.mode
            print(f"  Engine mode: {args.mode} (set via SWARM_CLAUDE_STEP_ENGINE_MODE)")
        elif "gemini" in args.backend:
            if args.mode == "stub":
                os.environ["SWARM_GEMINI_STUB"] = "1"
            else:
                os.environ["SWARM_GEMINI_STUB"] = "0"
            print(f"  Engine mode: {args.mode} (set via SWARM_GEMINI_STUB)")

    # Parse flow keys
    flow_keys = [f.strip() for f in args.flows.split(",")]

    # Get backend and create spec
    backend = get_backend(args.backend)
    spec = RunSpec(
        flow_keys=flow_keys,
        backend=args.backend,
        initiator="demo-stepwise-tool",
    )

    print("Starting stepwise demo run...")
    print(f"  Backend: {args.backend}")
    print(f"  Flows: {flow_keys}")
    if args.mode:
        print(f"  Mode: {args.mode}")

    # Start run
    run_id = backend.start(spec)
    print(f"  Run ID: {run_id}")
    print()

    # Wait for completion
    print(f"Waiting for completion (max {args.wait}s)...")
    start_time = time.time()

    while time.time() - start_time < args.wait:
        summary = backend.get_summary(run_id)
        if summary and summary.status in (RunStatus.SUCCEEDED, RunStatus.FAILED):
            break
        time.sleep(1)
        print(".", end="", flush=True)

    print()

    # Final status
    summary = backend.get_summary(run_id)
    if summary:
        print(f"Run completed with status: {summary.status.value}")
        print()
        print("View results:")
        print(f"  - Run directory: swarm/runs/{run_id}/")
        print(f"  - Flow Studio: make flow-studio -> http://localhost:5000/?run={run_id}")
    else:
        print("Warning: Could not get run summary")

    return 0 if summary and summary.status == RunStatus.SUCCEEDED else 1


if __name__ == "__main__":
    sys.exit(main())
