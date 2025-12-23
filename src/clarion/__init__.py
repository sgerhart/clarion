"""
Clarion - TrustSec Policy Copilot

Scale-first network segmentation using edge processing and unsupervised learning.

Modules:
- sketches: Probabilistic data structures for behavioral fingerprinting
- ingest: Data loading and sketch building
- identity: Identity resolution (IP → User → AD Groups)
- clustering: Unsupervised learning for endpoint grouping
- policy: SGT mapping and SGACL generation (coming soon)
"""

__version__ = "0.2.0"
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
from clarion.clustering import (
    FeatureExtractor,
    FeatureVector,
    EndpointClusterer,
    ClusterResult,
    SemanticLabeler,
    ClusterLabel,
    SGTMapper,
    SGTRecommendation,
)
from clarion.clustering.sgt_mapper import SGTTaxonomy, generate_sgt_taxonomy

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
    # Clustering
    "FeatureExtractor",
    "FeatureVector",
    "EndpointClusterer",
    "ClusterResult",
    "SemanticLabeler",
    "ClusterLabel",
    "SGTMapper",
    "SGTRecommendation",
    "SGTTaxonomy",
    "generate_sgt_taxonomy",
]
