"""
mcp-mesh-ui: Real-time Topology Visualizer & Observability Dashboard for mcp-mesh.
Satellite 2 of Existential Cloud AI Studio.
Curated by Van Schulist (@VanSchulist).
"""

from .core import MeshTelemetryStore, TelemetrySummary, TopologyNode, TopologyLink
from .web_server import run_server
from .tui import render_dashboard, run_tui_loop

__version__ = "1.0.0"
__author__ = "Van Schulist (Existential Cloud)"
__license__ = "MIT"

__all__ = [
    "MeshTelemetryStore",
    "TelemetrySummary",
    "TopologyNode",
    "TopologyLink",
    "run_server",
    "render_dashboard",
    "run_tui_loop",
    "__version__",
]
