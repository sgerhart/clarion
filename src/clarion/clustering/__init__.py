"""
Clarion Clustering Module

Unsupervised learning for endpoint grouping and SGT recommendation.

Key components:
- FeatureExtractor: Extract features from EndpointSketches
- EndpointClusterer: HDBSCAN-based clustering
- SemanticLabeler: Label clusters using AD groups and ISE profiles
- SGTMapper: Map clusters to SGT recommendations
"""

from clarion.clustering.features import FeatureExtractor, FeatureVector
from clarion.clustering.clusterer import EndpointClusterer, ClusterResult
from clarion.clustering.labeling import SemanticLabeler, ClusterLabel
from clarion.clustering.sgt_mapper import SGTMapper, SGTRecommendation
from clarion.clustering.explanation import generate_cluster_explanation
from clarion.clustering.sgt_lifecycle import SGTLifecycleManager
from clarion.clustering.incremental import IncrementalClusterer
from clarion.clustering.confidence import ConfidenceScorer

__all__ = [
    "FeatureExtractor",
    "FeatureVector",
    "EndpointClusterer",
    "ClusterResult",
    "SemanticLabeler",
    "ClusterLabel",
    "SGTMapper",
    "SGTRecommendation",
    "generate_cluster_explanation",
    "SGTLifecycleManager",
    "IncrementalClusterer",
    "ConfidenceScorer",
]

