#!/usr/bin/env python3
"""
MCP Server: ux_spec

Access Flow Studio UX manifest, layout spec, and governance contracts.
This server provides read-only access to the UX contract surface.

Usage (standalone):
    uv run python -m swarm.tools.mcp_ux_spec

Usage (with Claude Code):
    Add to ~/.config/claude/mcp.json:
    {
      "ux_spec": {
        "command": "uv",
        "args": ["run", "python", "-m", "swarm.tools.mcp_ux_spec"],
        "cwd": "/path/to/flow-studio"
      }
    }

Depends on:
    - ux_manifest.json (UX contract index)
    - Flow Studio API at http://localhost:5000 (for live layout screens)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None  # Optional for live API calls

try:
    from mcp.server import Server  # type: ignore[import-not-found]
    from mcp.server.stdio import stdio_server  # type: ignore[import-not-found]
    from mcp.types import TextContent, Tool  # type: ignore[import-not-found]
except ImportError:
    print("ERROR: mcp package required. Install with: uv add mcp", file=sys.stderr)
    sys.exit(1)


# ============================================================================
# Configuration
# ============================================================================

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "ux_manifest.json"
SCHEMA_PATH = REPO_ROOT / "swarm" / "schemas" / "ux_critique.schema.json"
FLOW_STUDIO_BASE_URL = "http://localhost:5000"


# ============================================================================
# Core Functions
# ============================================================================

def load_ux_manifest() -> Dict[str, Any]:
    """Load the ux_manifest.json file."""
    if not MANIFEST_PATH.exists():
        return {"error": f"Manifest not found at {MANIFEST_PATH}"}
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": f"Failed to load manifest: {e}"}


def load_critique_schema() -> Dict[str, Any]:
    """Load the UX critique JSON schema."""
    if not SCHEMA_PATH.exists():
        return {"error": f"Schema not found at {SCHEMA_PATH}"}
    try:
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": f"Failed to load schema: {e}"}


def fetch_layout_screens_from_api() -> Optional[Dict[str, Any]]:
    """Fetch layout screens from the live Flow Studio API."""
    if httpx is None:
        return None
    try:
        with httpx.Client() as client:
            resp = client.get(f"{FLOW_STUDIO_BASE_URL}/api/layout_screens", timeout=10)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None


def get_layout_screens() -> Dict[str, Any]:
    """Get layout screens, preferring live API over static."""
    # Try live API first
    live = fetch_layout_screens_from_api()
    if live:
        return {"source": "live", "data": live}

    # Fallback to manifest reference
    manifest = load_ux_manifest()
    if "error" not in manifest:
        return {
            "source": "manifest",
            "note": "Flow Studio not running; returning manifest reference only",
            "api_endpoint": manifest.get("api", {}).get("endpoints", []),
        }

    return {"error": "Could not load layout screens from API or manifest"}


def get_screen_by_id(screen_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific screen from the layout spec."""
    result = get_layout_screens()
    if "error" in result:
        return None

    if result.get("source") == "live":
        screens = result.get("data", {}).get("screens", [])
        for screen in screens:
            if screen.get("id") == screen_id:
                return screen

    return None


def get_all_known_uiids() -> List[str]:
    """Extract all UIIDs from the layout spec."""
    result = get_layout_screens()
    if "error" in result or result.get("source") != "live":
        return []

    uiids = set()
    screens = result.get("data", {}).get("screens", [])
    for screen in screens:
        for region in screen.get("regions", []):
            for uiid in region.get("uiids", []):
                uiids.add(uiid)

    return sorted(uiids)


# ============================================================================
# MCP Server
# ============================================================================

def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("ux_spec")

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        return [
            Tool(
                name="get_ux_manifest",
                description=(
                    "Return the parsed ux_manifest.json for Flow Studio UX. "
                    "This is the authoritative index of specs, docs, tests, tools, "
                    "API endpoints, SDK methods, and workflows for UX review."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="get_layout_screens",
                description=(
                    "Return list of layout screens and regions from the Flow Studio API. "
                    "Each screen has an id, route, title, description, and regions. "
                    "Each region has a purpose and list of UIIDs."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="get_layout_screen",
                description=(
                    "Get a single screen's layout spec by ID. "
                    "Returns the screen's route, regions, and UIIDs."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "screen_id": {
                            "type": "string",
                            "description": "Screen ID from the layout spec (e.g., 'flows.default')",
                        },
                    },
                    "required": ["screen_id"],
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="get_all_uiids",
                description=(
                    "Get all known UIIDs across all screens. "
                    "Useful for validating UIID references in critiques."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="get_critique_schema",
                description=(
                    "Return the JSON schema for UX critique objects. "
                    "Use this to understand the expected output format for critiques."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        if name == "get_ux_manifest":
            manifest = load_ux_manifest()
            return [TextContent(type="text", text=json.dumps(manifest, indent=2))]

        elif name == "get_layout_screens":
            result = get_layout_screens()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_layout_screen":
            screen_id = arguments["screen_id"]
            screen = get_screen_by_id(screen_id)
            if screen:
                return [TextContent(type="text", text=json.dumps(screen, indent=2))]
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Screen '{screen_id}' not found"}, indent=2),
            )]

        elif name == "get_all_uiids":
            uiids = get_all_known_uiids()
            return [TextContent(
                type="text",
                text=json.dumps({"uiids": uiids, "count": len(uiids)}, indent=2),
            )]

        elif name == "get_critique_schema":
            schema = load_critique_schema()
            return [TextContent(type="text", text=json.dumps(schema, indent=2))]

        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    return server


async def main():
    """Run the MCP server."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
