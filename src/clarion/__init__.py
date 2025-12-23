"""
Clarion - TrustSec Policy Copilot

Scale-first network segmentation using edge processing and unsupervised learning.

Modules:
- sketches: Probabilistic data structures for behavioral fingerprinting
- ingest: Data loading and sketch building
- identity: Identity resolution (IP → User → AD Groups)
- clustering: Unsupervised learning for endpoint grouping (coming soon)
- policy: SGT mapping and SGACL generation (coming soon)
"""

__version__ = "0.1.0"
__author__ = "Clarion Development Team"

# Re-export key classes for convenience
from clarion.sketches import EndpointSketch, HyperLogLogSketch, CountMinSketch
from clarion.ingest import (
    DataLoader,
    ClarionDataset,
    SketchBuilder,
    SketchStore,
    load_dataset,
    build_sketches,
)
from clarion.identity import (
    IdentityResolver,
    IdentityContext,
    enrich_sketches,
)

__all__ = [
    # Version
    "__version__",
    # Sketches
    "EndpointSketch",
    "HyperLogLogSketch", 
    "CountMinSketch",
    # Ingest
    "DataLoader",
    "ClarionDataset",
    "SketchBuilder",
    "SketchStore",
    "load_dataset",
    "build_sketches",
    # Identity
    "IdentityResolver",
    "IdentityContext",
    "enrich_sketches",
]
