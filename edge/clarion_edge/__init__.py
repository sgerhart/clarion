"""
Clarion Edge - Lightweight flow collector for Cisco App Hosting.

Runs on Catalyst 9K switches to:
1. Collect NetFlow/IPFIX data locally
2. Build behavioral sketches (HyperLogLog, Count-Min Sketch)
3. Run lightweight clustering (Mini-Batch K-Means)
4. Stream sketches to the central backend

Designed for constrained environments:
- 256 MB RAM limit
- 200 CPU units (0.2 vCPU)
- 1 GB disk
"""

__version__ = "0.2.0"

from clarion_edge.agent import EdgeAgent, EdgeConfig
from clarion_edge.simulator import FlowSimulator, SimulatorConfig
from clarion_edge.sketch import EdgeSketch, EdgeSketchStore

__all__ = [
    "__version__",
    "EdgeAgent",
    "EdgeConfig",
    "FlowSimulator",
    "SimulatorConfig",
    "EdgeSketch",
    "EdgeSketchStore",
]
