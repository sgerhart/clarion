"""
Confidence Scoring - Calculate confidence scores for clustering and SGT assignments.

Provides consistent confidence scoring across the system:
- Cluster assignment confidence
- SGT assignment confidence
- Distance-based confidence (for incremental clustering)
- Probability-based confidence (from HDBSCAN)
"""

from __future__ import annotations

from typing import Optional, Dict, Any
import logging
import numpy as np

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """
    Calculate confidence scores for various assignments.
    
    Confidence scores are normalized to 0.0-1.0 range where:
    - 1.0 = Very high confidence
    - 0.8-0.9 = High confidence
    - 0.6-0.8 = Medium confidence
    - 0.4-0.6 = Low confidence
    - <0.4 = Very low confidence
    """
    
    @staticmethod
    def from_distance(distance: float, threshold: float = 2.0) -> float:
        """
        Calculate confidence from distance to cluster centroid.
        
        Closer = higher confidence.
        
        Args:
            distance: Distance to centroid
            threshold: Maximum distance for full confidence (beyond this = 0)
            
        Returns:
            Confidence score (0.0-1.0)
        """
        if threshold <= 0:
            return 0.0
        
        if distance > threshold:
            return 0.0
        
        # Linear decay: confidence = 1.0 - (distance / threshold)
        confidence = max(0.0, 1.0 - (distance / threshold))
        return float(confidence)
    
    @staticmethod
    def from_probability(probability: float) -> float:
        """
        Calculate confidence from HDBSCAN cluster membership probability.
        
        Args:
            probability: HDBSCAN membership probability (0.0-1.0)
            
        Returns:
            Confidence score (0.0-1.0)
        """
        return float(max(0.0, min(1.0, probability)))
    
    @staticmethod
    def from_cluster_size(cluster_size: int, min_size: int = 10, max_size: int = 1000) -> float:
        """
        Calculate confidence based on cluster size.
        
        Larger, well-established clusters = higher confidence.
        
        Args:
            cluster_size: Number of endpoints in cluster
            min_size: Minimum size for full confidence
            max_size: Size where confidence starts to decrease
            
        Returns:
            Confidence score (0.0-1.0)
        """
        if cluster_size < min_size:
            # Very small clusters are less reliable
            return float(min(0.7, cluster_size / min_size))
        
        if cluster_size >= max_size:
            # Very large clusters might be too heterogeneous
            return 0.9
        
        # Medium-sized clusters get high confidence
        return 1.0
    
    @staticmethod
    def from_silhouette_score(silhouette: float) -> float:
        """
        Calculate confidence from cluster silhouette score.
        
        Higher silhouette = better defined cluster = higher confidence.
        
        Args:
            silhouette: Silhouette score (-1.0 to 1.0)
            
        Returns:
            Confidence score (0.0-1.0)
        """
        # Normalize to 0-1 range: (silhouette + 1) / 2
        normalized = (silhouette + 1.0) / 2.0
        return float(max(0.0, min(1.0, normalized)))
    
    @staticmethod
    def combined(
        distance_confidence: Optional[float] = None,
        probability_confidence: Optional[float] = None,
        size_confidence: Optional[float] = None,
        silhouette_confidence: Optional[float] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        Combine multiple confidence scores into a single score.
        
        Uses weighted average with default weights:
        - probability: 0.4 (highest weight - most reliable)
        - distance: 0.3
        - size: 0.2
        - silhouette: 0.1
        
        Args:
            distance_confidence: Confidence from distance
            probability_confidence: Confidence from HDBSCAN probability
            size_confidence: Confidence from cluster size
            silhouette_confidence: Confidence from silhouette score
            weights: Optional custom weights dict
            
        Returns:
            Combined confidence score (0.0-1.0)
        """
        if weights is None:
            weights = {
                'probability': 0.4,
                'distance': 0.3,
                'size': 0.2,
                'silhouette': 0.1,
            }
        
        scores = []
        total_weight = 0.0
        
        if probability_confidence is not None:
            scores.append(('probability', probability_confidence, weights.get('probability', 0.4)))
            total_weight += weights.get('probability', 0.4)
        
        if distance_confidence is not None:
            scores.append(('distance', distance_confidence, weights.get('distance', 0.3)))
            total_weight += weights.get('distance', 0.3)
        
        if size_confidence is not None:
            scores.append(('size', size_confidence, weights.get('size', 0.2)))
            total_weight += weights.get('size', 0.2)
        
        if silhouette_confidence is not None:
            scores.append(('silhouette', silhouette_confidence, weights.get('silhouette', 0.1)))
            total_weight += weights.get('silhouette', 0.1)
        
        if not scores or total_weight == 0:
            return 0.5  # Default to medium confidence if no scores provided
        
        # Weighted average
        weighted_sum = sum(score * weight for _, score, weight in scores)
        combined = weighted_sum / total_weight
        
        return float(max(0.0, min(1.0, combined)))
    
    @staticmethod
    def classify(confidence: float) -> str:
        """
        Classify confidence score into category.
        
        Args:
            confidence: Confidence score (0.0-1.0)
            
        Returns:
            Category string: 'very_high', 'high', 'medium', 'low', 'very_low'
        """
        if confidence >= 0.9:
            return 'very_high'
        elif confidence >= 0.8:
            return 'high'
        elif confidence >= 0.6:
            return 'medium'
        elif confidence >= 0.4:
            return 'low'
        else:
            return 'very_low'
    
    @staticmethod
    def for_cluster_assignment(
        cluster_id: int,
        distance: Optional[float] = None,
        probability: Optional[float] = None,
        cluster_size: Optional[int] = None,
        silhouette: Optional[float] = None,
    ) -> float:
        """
        Calculate confidence for cluster assignment.
        
        Convenience method that combines available metrics.
        
        Args:
            cluster_id: Cluster ID (-1 for noise)
            distance: Distance to centroid
            probability: HDBSCAN membership probability
            cluster_size: Size of cluster
            silhouette: Cluster silhouette score
            distance_threshold: Threshold for distance-based confidence
            
        Returns:
            Confidence score (0.0-1.0)
        """
        if cluster_id == -1:
            # Noise cluster always has low confidence
            return 0.2
        
        confidences = {}
        
        if distance is not None:
            confidences['distance'] = ConfidenceScorer.from_distance(distance)
        
        if probability is not None:
            confidences['probability'] = ConfidenceScorer.from_probability(probability)
        
        if cluster_size is not None:
            confidences['size'] = ConfidenceScorer.from_cluster_size(cluster_size)
        
        if silhouette is not None:
            confidences['silhouette'] = ConfidenceScorer.from_silhouette_score(silhouette)
        
        if not confidences:
            return 0.5  # Default if no metrics available
        
        # Use combined if multiple metrics, otherwise use the single one
        if len(confidences) > 1:
            return ConfidenceScorer.combined(
                distance_confidence=confidences.get('distance'),
                probability_confidence=confidences.get('probability'),
                size_confidence=confidences.get('size'),
                silhouette_confidence=confidences.get('silhouette'),
            )
        else:
            return list(confidences.values())[0]
    
    @staticmethod
    def for_sgt_assignment(
        cluster_confidence: float,
        sgt_confidence: Optional[float] = None,
        assignment_history_count: int = 0,
    ) -> float:
        """
        Calculate confidence for SGT assignment.
        
        Based on cluster confidence and SGT assignment stability.
        
        Args:
            cluster_confidence: Confidence of cluster assignment
            sgt_confidence: Optional confidence from SGT mapping
            assignment_history_count: Number of times this SGT has been assigned (stability)
            
        Returns:
            Confidence score (0.0-1.0)
        """
        # Base confidence from cluster
        base_confidence = cluster_confidence
        
        # Boost if SGT has been assigned multiple times (stable assignment)
        stability_boost = min(0.1, assignment_history_count * 0.01)
        
        # Use SGT-specific confidence if provided
        if sgt_confidence is not None:
            # Average cluster and SGT confidence, then add stability
            combined = (base_confidence + sgt_confidence) / 2.0
            return min(1.0, combined + stability_boost)
        
        # Otherwise use cluster confidence with stability boost
        return min(1.0, base_confidence + stability_boost)

