"""
Flow Studio - Visualize any YAML-defined flow graph.

A minimal Flask-based visualization tool for flow graphs defined in YAML.
Reads flow and agent definitions from config/ directory and renders them
as interactive graphs via Cytoscape.js.
"""

__version__ = "0.1.0"

from .config import FlowStudioConfig
from .server import create_app

__all__ = ["FlowStudioConfig", "create_app", "__version__"]
