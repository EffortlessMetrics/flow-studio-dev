#!/usr/bin/env python3
"""
selftest_paths.py - Centralized path definitions for selftest system.

This module provides a single source of truth for file paths used by:
- selftest.py (the runner/producer)
- BDD step definitions (the test consumers)

By importing from this module, both producer and consumer use identical
paths, eliminating path computation mismatches across different working
directories or CI environments.
"""

from pathlib import Path

# This file lives in swarm/tools/
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent

# Degradation log: JSONL file at repo root recording GOVERNANCE failures
# Written by selftest.py, consumed by BDD tests and observability tools
DEGRADATIONS_LOG_PATH = _REPO_ROOT / "selftest_degradations.log"

# Convenience export for repo root (useful for other path computations)
REPO_ROOT = _REPO_ROOT


def parse_skip_steps(raw: str) -> set[str]:
    """
    Parse a comma-separated skip steps string into a set of step IDs.

    This is used by both selftest.py and flow_studio_smoke.py to interpret
    the SELFTEST_SKIP_STEPS environment variable consistently.

    Args:
        raw: Comma-separated string of step IDs (e.g., "flowstudio-smoke,extras")

    Returns:
        Set of step IDs with whitespace stripped, empty strings filtered out.

    Example:
        >>> parse_skip_steps("flowstudio-smoke, extras")
        {'flowstudio-smoke', 'extras'}
        >>> parse_skip_steps("")
        set()
    """
    return {s.strip() for s in raw.split(",") if s.strip()}
