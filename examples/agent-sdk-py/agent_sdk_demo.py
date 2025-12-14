#!/usr/bin/env python3
"""
Agent SDK Demo: Proves Claude Agent SDK works without an API key.

This script demonstrates that the Claude Agent SDK is "headless Claude Code" -
if you're logged into Claude Code, the SDK works automatically. No separate
API billing account or key is needed.

Usage:
    python agent_sdk_demo.py

Prerequisites:
    - Claude Code installed and authenticated (claude login)
    - Python 3.10+
"""

import asyncio
import sys
from pathlib import Path


async def run_demo() -> int:
    """
    Run a simple Agent SDK query to list flows in the repository.

    Returns:
        0 on success, 1 on failure
    """
    print("=" * 60)
    print("Claude Agent SDK Demo")
    print("=" * 60)
    print()
    print("This demo proves: If Claude Code works, Agent SDK works.")
    print("No separate API key or billing account needed.")
    print()

    # Import the SDK - this is where we'd fail if not installed
    try:
        from claude_code_sdk import ClaudeCodeOptions, query
    except ImportError as e:
        print(f"ERROR: Could not import claude_code_sdk: {e}")
        print()
        print("Install with: pip install claude-code-sdk")
        return 1

    print("[1/3] SDK imported successfully")

    # Find the repo root (two levels up from this script)
    repo_root = Path(__file__).parent.parent.parent
    if not (repo_root / "swarm" / "flows").exists():
        print(f"WARNING: Could not find swarm/flows at {repo_root}")
        print("Running from a non-standard location")

    print(f"[2/3] Working directory: {repo_root}")
    print()
    print("Sending query to Claude Agent SDK...")
    print("(This uses your Claude Code login - no API key needed)")
    print()

    # Create options for the query
    options = ClaudeCodeOptions(
        max_turns=1,  # Single turn is enough for this simple query
    )

    # The prompt asks Claude to list the flows
    prompt = """List the 6 SDLC flows defined in this repository.
For each flow, show:
- Flow number and name
- One-line description

Be concise - just the list, no extra commentary."""

    try:
        # Execute the query - this streams results
        result_text = []
        async for message in query(
            prompt=prompt,
            options=options,
        ):
            # Handle different message types
            if hasattr(message, "content"):
                # This is a text message
                if isinstance(message.content, str):
                    result_text.append(message.content)
                elif isinstance(message.content, list):
                    for block in message.content:
                        if hasattr(block, "text"):
                            result_text.append(block.text)

        print("[3/3] Query completed successfully!")
        print()
        print("-" * 60)
        print("RESPONSE:")
        print("-" * 60)
        print("".join(result_text) if result_text else "(No text response)")
        print("-" * 60)
        print()
        print("SUCCESS: Agent SDK is working with your Claude Code login.")
        return 0

    except Exception as e:
        print(f"ERROR during query: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Ensure Claude Code is installed: npm install -g @anthropic-ai/claude-code")
        print("  2. Ensure you're logged in: claude login")
        print("  3. Test Claude Code directly: claude 'hello'")
        return 1


def main() -> None:
    """Entry point for the demo script."""
    exit_code = asyncio.run(run_demo())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
