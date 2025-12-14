#!/usr/bin/env python3
"""
Flow Studio smoke test - Validates governance health via in-process selftest.

This is a fast check that runs selftest in-process and evaluates kernel/governance
health. It replaces the previous HTTP-based approach (FastAPI TestClient) which
had ~30-40s overhead due to app initialization.

Checks:
- Selftest KERNEL tier passes (critical)
- Selftest GOVERNANCE tier passes (warning)

Usage:
    uv run python -m swarm.tools.flow_studio_smoke

Exit codes:
    0 - Selftest summary is healthy (KERNEL and GOVERNANCE pass)
    1 - Selftest indicates failures (KERNEL or GOVERNANCE failed)
    2 - Fatal error (could not compute selftest summary)
    3 - Timeout (test did not complete in allowed time)
"""

from __future__ import annotations

import os
import signal
import sys
from contextlib import contextmanager
from typing import Generator

# Default timeout for the entire smoke test (seconds)
# Fast path: in-process selftest summary typically completes in ~5-10s
DEFAULT_TIMEOUT = int(os.environ.get("FLOWSTUDIO_SMOKE_TIMEOUT", "15"))


class FlowStudioSmokeTimeout(Exception):
    """Raised when a flow studio smoke test times out."""

    pass


@contextmanager
def timeout_handler(seconds: int) -> Generator[None, None, None]:
    """
    Context manager to enforce a timeout on operations.

    Uses SIGALRM on Unix systems. On Windows, this is a no-op (timeout not enforced).

    Args:
        seconds: Maximum time to allow for the operation

    Raises:
        TimeoutError: If the operation exceeds the timeout
    """
    if sys.platform == "win32":
        # SIGALRM not available on Windows
        yield
        return

    def alarm_handler(signum: int, frame: object) -> None:
        raise FlowStudioSmokeTimeout(f"Operation timed out after {seconds} seconds")

    # Set the signal handler
    old_handler = signal.signal(signal.SIGALRM, alarm_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        # Restore the old handler and cancel the alarm
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def run_smoke_test() -> int:
    """
    Run smoke test against Flow Studio endpoints.

    Two-layer timeout defense:
    1. Inner: SIGALRM-based timeout (DEFAULT_TIMEOUT, typically 30s)
       - Works when Python can handle signals (main thread, non-blocking I/O)
       - May not fire during blocking C extension calls
    2. Outer: subprocess timeout in selftest.py (typically 45s)
       - Always fires via OS-level process termination
       - Catches cases where SIGALRM doesn't interrupt

    Returns:
        0 on success, 1 on failure, 2 on fatal error, 3 on timeout
    """
    # Check for skip flag using shared parser
    # Import works both when run directly and as module
    try:
        from selftest_paths import parse_skip_steps
    except ImportError:
        from swarm.tools.selftest_paths import parse_skip_steps

    skip_set = parse_skip_steps(os.environ.get("SELFTEST_SKIP_STEPS", ""))
    if {"flowstudio-smoke", "flowstudio"} & skip_set:
        print("SKIP: flowstudio-smoke skipped via SELFTEST_SKIP_STEPS")
        return 0

    # Apply inner timeout wrapper (SIGALRM-based, belt-and-suspenders with outer subprocess timeout)
    try:
        with timeout_handler(DEFAULT_TIMEOUT):
            return _run_smoke_test_inner()
    except FlowStudioSmokeTimeout as e:
        print(f"FAIL: {e}", file=sys.stderr)
        print(
            "Hint: Flow Studio smoke test timed out. This can happen if the FastAPI",
            file=sys.stderr,
        )
        print(
            "TestClient hangs. Try running with SELFTEST_SKIP_STEPS=flowstudio-smoke",
            file=sys.stderr,
        )
        return 3


def _run_smoke_test_inner() -> int:
    """
    Fast Flow Studio smoke test.

    Instead of spinning up a full FastAPI app + TestClient, this uses the
    in-process selftest summary to evaluate Flow Studio-related health.

    This is a performance optimization to avoid the ~30-40s overhead of
    FastAPI/TestClient initialization during CI and local smoke tests.

    Exit codes:
        0 - All relevant selftests passing (HEALTHY)
        1 - Selftests report governance failures (BROKEN)
        2 - Fatal error while computing selftest summary
    """
    try:
        from swarm.tools.status_provider import get_selftest_summary
    except ImportError:
        # Fallback for when run as module from swarm/tools
        from status_provider import get_selftest_summary

    print("Running in-process selftest summary check...", flush=True)

    try:
        snapshot = get_selftest_summary(degraded=False)
    except Exception as e:
        print(f"FATAL: error while computing selftest summary: {e}", file=sys.stderr)
        return 2

    kernel_ok = snapshot.kernel_ok
    governance_ok = snapshot.governance_ok
    failed_steps = snapshot.failed_steps

    print(f"  KERNEL:     {'OK' if kernel_ok else 'FAIL'}")
    print(f"  GOVERNANCE: {'OK' if governance_ok else 'FAIL'}")

    if kernel_ok and governance_ok:
        print("\nHEALTHY: Flow Studio selftest summary is OK")
        return 0

    print("\nBROKEN: Flow Studio selftest indicates failures")
    if failed_steps:
        print(f"Failed steps: {', '.join(failed_steps)}")

    # Provide actionable hints
    if snapshot.kernel_failed:
        print("\n⚠ KERNEL failure(s) block all merges:")
        for step_id in snapshot.kernel_failed:
            print(f"  Run: uv run swarm/tools/selftest.py --step {step_id}")
    if snapshot.governance_failed:
        print("\n💡 GOVERNANCE failure(s):")
        for step_id in snapshot.governance_failed:
            print(f"  Run: uv run swarm/tools/selftest.py --step {step_id}")
        print("  Or: uv run swarm/tools/selftest.py --degraded to work around")

    return 1


def main() -> None:
    """Main entry point."""
    sys.exit(run_smoke_test())


if __name__ == "__main__":
    main()
