"""
Clarion Ingest Module

Data loading and sketch building for Clarion.

Key components:
- DataLoader: Load CSV/Parquet datasets
- ClarionDataset: Container for all data tables
- SketchBuilder: Convert flows to EndpointSketches
- SketchStore: In-memory storage for sketches
"""

from clarion.ingest.loader import (
    DataLoader,
    ClarionDataset,
    load_dataset,
)
from clarion.ingest.sketch_builder import (
    SketchBuilder,
    SketchStore,
    build_sketches,
)

__all__ = [
    "DataLoader",
    "ClarionDataset",
    "load_dataset",
    "SketchBuilder",
    "SketchStore",
    "build_sketches",
]
