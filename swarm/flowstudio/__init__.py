"""
Flow Studio - Visual learning interface for swarm SDLC.

This package provides:
- FlowStudioConfig: Configuration for Flow Studio paths
- FlowStudioCore: Core business logic for Flow Studio
- Flow Studio Flask app (in swarm/tools/flow_studio.py)
- Flow Studio FastAPI app (in swarm/tools/flow_studio_fastapi.py)
- Run Inspector for artifact status (in swarm/tools/run_inspector.py)
"""

from swarm.flowstudio.config import FlowStudioConfig
from swarm.flowstudio.core import FlowStudioCore

__all__ = ["FlowStudioConfig", "FlowStudioCore"]
