#!/usr/bin/env python3
"""
kernel_smoke.py - Lightweight kernel smoke test

Runs only KERNEL tier selftest steps as a fast health check.
Delegates to selftest.py --kernel-only, ensuring consistency with the
full selftest system.

KERNEL tier checks (from selftest_config):
- core-checks: Python ruff linting + compile checks

Typical usage:
  uv run swarm/tools/kernel_smoke.py
  uv run swarm/tools/kernel_smoke.py --verbose
  uv run swarm/tools/kernel_smoke.py --json

Exit codes:
  0   All KERNEL checks passed
  1   One or more KERNEL checks failed
  2   Configuration error
"""

import argparse
import subprocess
import sys


def main():
    """Main entry point: delegate to selftest.py --kernel-only"""
    parser = argparse.ArgumentParser(
        description="Lightweight kernel smoke test (KERNEL tier checks only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output with timing",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-parseable JSON report",
    )

    args = parser.parse_args()

    # Build selftest command
    cmd = ["uv", "run", "swarm/tools/selftest.py", "--kernel-only"]
    if args.verbose:
        cmd.append("--verbose")
    if args.json:
        cmd.append("--json")

    # Delegate to selftest
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
