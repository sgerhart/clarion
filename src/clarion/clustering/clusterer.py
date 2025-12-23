"""
Endpoint Clustering using HDBSCAN.

Clusters endpoints based on behavioral features to identify
natural groupings for SGT assignment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import logging

import numpy as np
import hdbscan
from sklearn.cluster import MiniBatchKMeans
from sklearn.metrics import silhouette_score

from clarion.sketches import EndpointSketch
from clarion.ingest.sketch_builder import SketchStore
from clarion.clustering.features import FeatureExtractor, FeatureVector

logger = logging.getLogger(__name__)


@dataclass
class ClusterResult:
    """
    Result of clustering operation.
    
    Contains cluster assignments and metadata.
    """
    # Core results
    labels: np.ndarray  # Cluster label per endpoint (-1 = noise)
    endpoint_ids: List[str]  # Endpoint ID for each label
    
    # Cluster info
    n_clusters: int
    n_noise: int
    
    # Quality metrics
    silhouette: Optional[float] = None
    
    # Cluster sizes
    cluster_sizes: Dict[int, int] = field(default_factory=dict)
    
    # Probabilities (HDBSCAN provides soft clustering)
    probabilities: Optional[np.ndarray] = None
    
    def get_cluster_members(self, cluster_id: int) -> List[str]:
        """Get endpoint IDs for a specific cluster."""
        return [
            eid for eid, label in zip(self.endpoint_ids, self.labels)
            if label == cluster_id
        ]
    
    def get_endpoint_cluster(self, endpoint_id: str) -> int:
        """Get cluster ID for an endpoint."""
        try:
            idx = self.endpoint_ids.index(endpoint_id)
            return int(self.labels[idx])
        except ValueError:
            return -1
    
    def summary(self) -> Dict:
        """Get clustering summary."""
        return {
            "n_endpoints": len(self.endpoint_ids),
            "n_clusters": self.n_clusters,
            "n_noise": self.n_noise,
            "noise_ratio": self.n_noise / len(self.endpoint_ids) if self.endpoint_ids else 0,
            "silhouette": self.silhouette,
            "cluster_sizes": dict(self.cluster_sizes),
        }


class EndpointClusterer:
    """
    Cluster endpoints using HDBSCAN.
    
    HDBSCAN is chosen because:
    - Finds clusters of varying densities
    - Doesn't require specifying k (number of clusters)
    - Identifies noise/outliers (cluster -1)
    - Provides soft cluster memberships
    
    Example:
        >>> clusterer = EndpointClusterer()
        >>> result = clusterer.cluster(sketch_store)
        >>> print(f"Found {result.n_clusters} clusters")
    """
    
    def __init__(
        self,
        min_cluster_size: int = 50,
        min_samples: int = 10,
        cluster_selection_epsilon: float = 0.0,
        metric: str = "euclidean",
    ):
        """
        Initialize the clusterer.
        
        Args:
            min_cluster_size: Minimum points to form a cluster
            min_samples: Minimum samples in neighborhood for core points
            cluster_selection_epsilon: Distance threshold for cluster merging
            metric: Distance metric (euclidean, manhattan, etc.)
        """
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.cluster_selection_epsilon = cluster_selection_epsilon
        self.metric = metric
        
        self._clusterer: Optional[hdbscan.HDBSCAN] = None
        self._feature_extractor = FeatureExtractor()
    
    def cluster(
        self,
        store: SketchStore,
        features: Optional[List[FeatureVector]] = None,
    ) -> ClusterResult:
        """
        Cluster endpoints in a sketch store.
        
        Args:
            store: SketchStore with endpoint sketches
            features: Optional pre-extracted features
            
        Returns:
            ClusterResult with assignments
        """
        logger.info(f"Clustering {len(store)} endpoints")
        
        # Extract features if not provided
        if features is None:
            features = self._feature_extractor.extract_all(store)
        
        # Convert to matrix
        X, endpoint_ids = self._feature_extractor.to_matrix(features)
        
        if len(X) == 0:
            logger.warning("No endpoints to cluster")
            return ClusterResult(
                labels=np.array([]),
                endpoint_ids=[],
                n_clusters=0,
                n_noise=0,
            )
        
        # Run HDBSCAN
        logger.info(
            f"Running HDBSCAN with min_cluster_size={self.min_cluster_size}, "
            f"min_samples={self.min_samples}"
        )
        
        self._clusterer = hdbscan.HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            cluster_selection_epsilon=self.cluster_selection_epsilon,
            metric=self.metric,
            core_dist_n_jobs=-1,  # Use all cores
        )
        
        labels = self._clusterer.fit_predict(X)
        probabilities = self._clusterer.probabilities_
        
        # Calculate metrics
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = int(np.sum(labels == -1))
        
        # Calculate silhouette score (only if we have clusters)
        silhouette = None
        if n_clusters > 1:
            # Exclude noise points for silhouette
            mask = labels != -1
            if np.sum(mask) > 1:
                try:
                    silhouette = float(silhouette_score(X[mask], labels[mask]))
                except Exception as e:
                    logger.warning(f"Could not calculate silhouette: {e}")
        
        # Calculate cluster sizes
        cluster_sizes = {}
        for label in set(labels):
            cluster_sizes[int(label)] = int(np.sum(labels == label))
        
        result = ClusterResult(
            labels=labels,
            endpoint_ids=endpoint_ids,
            n_clusters=n_clusters,
            n_noise=n_noise,
            silhouette=silhouette,
            cluster_sizes=cluster_sizes,
            probabilities=probabilities,
        )
        
        logger.info(
            f"Clustering complete: {n_clusters} clusters, "
            f"{n_noise} noise points ({n_noise/len(labels)*100:.1f}%), "
            f"silhouette={silhouette:.3f}" if silhouette else ""
        )
        
        return result
    
    def apply_to_store(
        self,
        store: SketchStore,
        result: ClusterResult,
    ) -> None:
        """
        Apply cluster assignments back to the sketch store.
        
        Updates each sketch's local_cluster_id field.
        
        Args:
            store: SketchStore to update
            result: ClusterResult with assignments
        """
        id_to_cluster = dict(zip(result.endpoint_ids, result.labels))
        
        updated = 0
        for sketch in store:
            if sketch.endpoint_id in id_to_cluster:
                sketch.local_cluster_id = int(id_to_cluster[sketch.endpoint_id])
                updated += 1
        
        logger.info(f"Applied cluster assignments to {updated} sketches")


class LightweightClusterer:
    """
    Lightweight K-means clusterer for edge processing.
    
    Uses Mini-Batch K-Means which is faster and uses less memory
    than full K-Means, suitable for running on switches.
    
    Example:
        >>> clusterer = LightweightClusterer(n_clusters=8)
        >>> labels = clusterer.fit_predict(X)
    """
    
    def __init__(
        self,
        n_clusters: int = 8,
        batch_size: int = 100,
        max_iter: int = 100,
    ):
        """
        Initialize the lightweight clusterer.
        
        Args:
            n_clusters: Number of clusters (k)
            batch_size: Mini-batch size
            max_iter: Maximum iterations
        """
        self.n_clusters = n_clusters
        self.batch_size = batch_size
        self.max_iter = max_iter
        
        self._clusterer = MiniBatchKMeans(
            n_clusters=n_clusters,
            batch_size=batch_size,
            max_iter=max_iter,
            random_state=42,
        )
    
    def fit_predict(self, X: np.ndarray) -> np.ndarray:
        """
        Fit and predict cluster labels.
        
        Args:
            X: Feature matrix (n_samples, n_features)
            
        Returns:
            Cluster labels (0 to k-1)
        """
        return self._clusterer.fit_predict(X)
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict cluster labels for new data.
        
        Args:
            X: Feature matrix
            
        Returns:
            Cluster labels
        """
        return self._clusterer.predict(X)
    
    @property
    def cluster_centers(self) -> np.ndarray:
        """Get cluster centroids."""
        return self._clusterer.cluster_centers_

