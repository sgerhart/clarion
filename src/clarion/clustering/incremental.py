"""
Incremental Clustering - Fast path for assigning new endpoints to existing clusters.

This module provides fast assignment of new endpoints to existing clusters
without running full clustering, by using stored cluster centroids and
nearest-neighbor assignment.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any
import logging
import numpy as np

from clarion.sketches import EndpointSketch
from clarion.clustering.features import FeatureExtractor, FeatureVector
from clarion.clustering.clusterer import ClusterResult
from clarion.clustering.confidence import ConfidenceScorer
from clarion.storage import get_database

logger = logging.getLogger(__name__)


class IncrementalClusterer:
    """
    Assigns new endpoints to existing clusters using centroid-based nearest neighbor.
    
    Key features:
    - Fast assignment (<100ms per endpoint)
    - Uses stored cluster centroids
    - Calculates distance-based confidence scores
    - Handles noise/outliers (assigns to noise cluster if too far)
    
    Example:
        >>> clusterer = IncrementalClusterer()
        >>> 
        >>> # Load centroids from database
        >>> clusterer.load_centroids()
        >>> 
        >>> # Assign a new endpoint
        >>> assignment = clusterer.assign_endpoint(sketch)
        >>> print(f"Assigned to cluster {assignment['cluster_id']} with confidence {assignment['confidence']}")
    """
    
    def __init__(
        self,
        feature_extractor: Optional[FeatureExtractor] = None,
        db=None,
        max_distance_threshold: float = 2.0,  # Max distance for assignment
    ):
        """
        Initialize incremental clusterer.
        
        Args:
            feature_extractor: FeatureExtractor instance (creates new if None)
            db: Database instance (uses get_database() if None)
            max_distance_threshold: Maximum distance to assign (else assign to noise cluster -1)
        """
        self.feature_extractor = feature_extractor or FeatureExtractor()
        self.db = db or get_database()
        self.max_distance_threshold = max_distance_threshold
        
        # Cluster centroids cache: cluster_id -> feature_vector
        self._centroids: Dict[int, np.ndarray] = {}
        self._centroid_metadata: Dict[int, Dict[str, Any]] = {}
        self._loaded = False
    
    def load_centroids(self) -> int:
        """
        Load all cluster centroids from database.
        
        Returns:
            Number of centroids loaded
        """
        centroids = self.db.list_all_centroids()
        
        self._centroids = {}
        self._centroid_metadata = {}
        
        for centroid_data in centroids:
            cluster_id = centroid_data['cluster_id']
            feature_vector = centroid_data.get('feature_vector')
            
            if feature_vector and isinstance(feature_vector, list):
                self._centroids[cluster_id] = np.array(feature_vector, dtype=np.float32)
                self._centroid_metadata[cluster_id] = {
                    'sgt_value': centroid_data.get('sgt_value'),
                    'member_count': centroid_data.get('member_count', 0),
                    'updated_at': centroid_data.get('updated_at'),
                }
        
        self._loaded = True
        logger.info(f"Loaded {len(self._centroids)} cluster centroids")
        return len(self._centroids)
    
    def assign_endpoint(
        self,
        sketch: EndpointSketch,
        return_distances: bool = False,
    ) -> Dict[str, Any]:
        """
        Assign an endpoint to the nearest existing cluster.
        
        Args:
            sketch: EndpointSketch to assign
            return_distances: If True, include distance to all centroids
            
        Returns:
            Dict with:
            - cluster_id: Assigned cluster ID (-1 for noise if too far)
            - confidence: Confidence score (0.0-1.0)
            - distance: Distance to nearest centroid
            - sgt_value: SGT value of assigned cluster (if available)
            - distances: (optional) Dict of cluster_id -> distance
        """
        if not self._loaded:
            self.load_centroids()
        
        if not self._centroids:
            logger.warning("No centroids available for incremental assignment")
            return {
                'cluster_id': -1,
                'confidence': 0.0,
                'distance': float('inf'),
                'sgt_value': None,
            }
        
        # Extract features from sketch
        feature_vector = self.feature_extractor.extract(sketch)
        feature_array = feature_vector.to_array()
        
        # Calculate distances to all centroids
        distances = {}
        for cluster_id, centroid in self._centroids.items():
            distance = np.linalg.norm(feature_array - centroid)
            distances[cluster_id] = float(distance)
        
        # Find nearest cluster
        nearest_cluster_id = min(distances.keys(), key=lambda k: distances[k])
        min_distance = distances[nearest_cluster_id]
        
        # Assign to noise cluster if too far
        if min_distance > self.max_distance_threshold:
            cluster_id = -1
            confidence = 0.0
        else:
            cluster_id = nearest_cluster_id
            # Use ConfidenceScorer for consistent confidence calculation
            cluster_size = self._centroid_metadata.get(cluster_id, {}).get('member_count')
            confidence = ConfidenceScorer.for_cluster_assignment(
                cluster_id=cluster_id,
                distance=min_distance,
                cluster_size=cluster_size,
            )
        
        # Get SGT value if available
        sgt_value = None
        if cluster_id in self._centroid_metadata:
            sgt_value = self._centroid_metadata[cluster_id].get('sgt_value')
        
        result = {
            'cluster_id': cluster_id,
            'confidence': confidence,
            'distance': min_distance,
            'sgt_value': sgt_value,
        }
        
        if return_distances:
            result['distances'] = distances
        
        return result
    
    def assign_endpoints_bulk(
        self,
        sketches: List[EndpointSketch],
        store_assignments: bool = True,
        update_centroids: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Assign multiple endpoints in bulk.
        
        Args:
            sketches: List of EndpointSketch objects
            store_assignments: If True, store assignments in database
            update_centroids: If True, update centroids after assignment
            
        Returns:
            List of assignment dicts (same format as assign_endpoint)
        """
        assignments = []
        for sketch in sketches:
            assignment = self.assign_endpoint(sketch)
            assignment['endpoint_id'] = sketch.endpoint_id
            assignments.append(assignment)
        
        # Store assignments in database
        if store_assignments:
            for assignment in assignments:
                if assignment['cluster_id'] != -1:  # Don't store noise assignments
                    self.db.assign_endpoint_to_cluster(
                        endpoint_id=assignment['endpoint_id'],
                        cluster_id=assignment['cluster_id'],
                        confidence=assignment['confidence'],
                        assigned_by='incremental',
                    )
        
        # Update centroids if requested
        if update_centroids:
            self._update_centroids_after_assignment(assignments)
        
        logger.info(f"Assigned {len(assignments)} endpoints incrementally")
        return assignments
    
    def assign_and_store(
        self,
        sketch: EndpointSketch,
        update_centroid: bool = True,
    ) -> Dict[str, Any]:
        """
        Assign endpoint and store assignment in database.
        
        Args:
            sketch: EndpointSketch to assign
            update_centroid: If True, update the assigned cluster's centroid
            
        Returns:
            Assignment dict with cluster_id, confidence, etc.
        """
        assignment = self.assign_endpoint(sketch)
        assignment['endpoint_id'] = sketch.endpoint_id
        
        # Store assignment in database
        if assignment['cluster_id'] != -1:
            self.db.assign_endpoint_to_cluster(
                endpoint_id=assignment['endpoint_id'],
                cluster_id=assignment['cluster_id'],
                confidence=assignment['confidence'],
                assigned_by='incremental',
            )
            
            # Update centroid if requested
            if update_centroid:
                self._update_centroid_for_cluster(assignment['cluster_id'])
        
        return assignment
    
    def _update_centroid_for_cluster(self, cluster_id: int) -> None:
        """
        Recalculate and update centroid for a cluster after new assignment.
        
        This should be called after assigning endpoints to update the centroid.
        For MVP, we use a simple approach: average of all member feature vectors.
        
        Args:
            cluster_id: Cluster ID to update
        """
        # Get all endpoints in this cluster from database
        conn = self.db._get_connection()
        cursor = conn.execute("""
            SELECT endpoint_id FROM cluster_assignments 
            WHERE cluster_id = ?
        """, (cluster_id,))
        endpoint_ids = [row[0] for row in cursor.fetchall()]
        
        if not endpoint_ids:
            return
        
        # Get sketches for these endpoints (would need to load from database)
        # For MVP, we'll use a simpler approach: keep existing centroid
        # In full implementation, we'd recalculate from all member sketches
        
        # For now, just update the member count
        self.db.update_centroid_member_count(cluster_id, len(endpoint_ids))
        logger.debug(f"Updated member count for cluster {cluster_id} to {len(endpoint_ids)}")
    
    def _update_centroids_after_assignment(self, assignments: List[Dict[str, Any]]) -> None:
        """
        Update centroids for clusters that received new assignments.
        
        Args:
            assignments: List of assignment dicts
        """
        clusters_to_update = set()
        for assignment in assignments:
            if assignment['cluster_id'] != -1:
                clusters_to_update.add(assignment['cluster_id'])
        
        for cluster_id in clusters_to_update:
            self._update_centroid_for_cluster(cluster_id)
    
    def update_centroid(
        self,
        cluster_id: int,
        feature_vector: List[float],
        sgt_value: Optional[int] = None,
        member_count: Optional[int] = None,
    ) -> None:
        """
        Update a cluster centroid in database and cache.
        
        Args:
            cluster_id: Cluster ID
            feature_vector: New centroid feature vector
            sgt_value: Optional SGT value
            member_count: Optional member count
        """
        # Store in database
        self.db.store_cluster_centroid(
            cluster_id=cluster_id,
            feature_vector=feature_vector,
            sgt_value=sgt_value,
            member_count=member_count or 0,
        )
        
        # Update cache
        self._centroids[cluster_id] = np.array(feature_vector, dtype=np.float32)
        if cluster_id not in self._centroid_metadata:
            self._centroid_metadata[cluster_id] = {}
        self._centroid_metadata[cluster_id]['sgt_value'] = sgt_value
        self._centroid_metadata[cluster_id]['member_count'] = member_count or 0
        
        logger.info(f"Updated centroid for cluster {cluster_id}")
    
    def get_centroid(self, cluster_id: int) -> Optional[np.ndarray]:
        """
        Get a cluster centroid from cache.
        
        Args:
            cluster_id: Cluster ID
            
        Returns:
            Centroid feature vector as numpy array, or None if not found
        """
        if not self._loaded:
            self.load_centroids()
        
        return self._centroids.get(cluster_id)
    
    def has_centroids(self) -> bool:
        """Check if centroids are loaded."""
        if not self._loaded:
            self.load_centroids()
        return len(self._centroids) > 0
    
    def clear_cache(self) -> None:
        """Clear the centroid cache (forces reload on next access)."""
        self._centroids: Dict[int, np.ndarray] = {}
        self._centroid_metadata: Dict[int, Dict[str, Any]] = {}
        self._loaded = False
    
    def store_centroids_from_clustering(
        self,
        cluster_result: ClusterResult,
        feature_vectors: List[FeatureVector],
        sgt_mapping: Optional[Dict[int, int]] = None,
    ) -> int:
        """
        Store cluster centroids from a full clustering result.
        
        This should be called after running full clustering to store centroids
        for future incremental assignments.
        
        Args:
            cluster_result: ClusterResult from full clustering
            feature_vectors: FeatureVector objects (one per endpoint)
            sgt_mapping: Optional dict mapping cluster_id -> sgt_value
            
        Returns:
            Number of centroids stored
        """
        if len(feature_vectors) != len(cluster_result.endpoint_ids):
            raise ValueError("Feature vectors must match endpoint IDs")
        
        # Build feature matrix - FeatureVector has to_array() method
        feature_matrix = np.array([fv.to_array() for fv in feature_vectors], dtype=np.float32)
        
        # Calculate centroids for each cluster
        stored_count = 0
        # Convert numpy int64 to Python int for SQLite compatibility
        unique_cluster_ids = set(int(cid) for cid in set(cluster_result.labels))
        for cluster_id in unique_cluster_ids:
            if cluster_id == -1:
                continue  # Skip noise cluster
            
            # Get members of this cluster
            member_indices = np.where(cluster_result.labels == cluster_id)[0]
            if len(member_indices) == 0:
                continue
            
            # Calculate centroid (mean of all members)
            cluster_features = feature_matrix[member_indices]
            centroid = np.mean(cluster_features, axis=0)
            # Convert numpy array to Python list of floats for JSON serialization
            centroid_list = [float(x) for x in centroid.tolist()]
            
            # Get SGT value if mapping provided
            sgt_value = None
            if sgt_mapping:
                sgt_value = sgt_mapping.get(cluster_id)
            
            # Store centroid
            self.update_centroid(
                cluster_id=cluster_id,
                feature_vector=centroid_list,
                sgt_value=sgt_value,
                member_count=len(member_indices),
            )
            stored_count += 1
        
        logger.info(f"Stored {stored_count} cluster centroids from clustering result")
        return stored_count

