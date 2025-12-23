"""
Feature Extraction for Endpoint Clustering.

Extracts normalized feature vectors from EndpointSketches for use
in clustering algorithms. Features capture behavioral patterns that
distinguish different types of endpoints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import logging
import math

import numpy as np
from sklearn.preprocessing import StandardScaler

from clarion.sketches import EndpointSketch
from clarion.ingest.sketch_builder import SketchStore

logger = logging.getLogger(__name__)


@dataclass
class FeatureVector:
    """
    Feature vector for a single endpoint.
    
    Contains both raw and normalized features for clustering.
    """
    endpoint_id: str
    
    # Raw features
    peer_diversity: float = 0.0
    service_diversity: float = 0.0
    port_diversity: float = 0.0
    in_out_ratio: float = 0.5
    total_bytes: float = 0.0
    total_flows: float = 0.0
    active_hours: float = 0.0
    business_hours_ratio: float = 0.0
    
    # Computed features
    bytes_per_flow: float = 0.0
    is_likely_server: float = 0.0
    
    # Identity features (if available)
    has_user: float = 0.0
    group_count: float = 0.0
    is_privileged: float = 0.0
    
    # Device type features (one-hot encoded)
    is_laptop: float = 0.0
    is_server: float = 0.0
    is_printer: float = 0.0
    is_iot: float = 0.0
    is_phone: float = 0.0
    
    def to_array(self) -> np.ndarray:
        """Convert to numpy array for clustering."""
        return np.array([
            self.peer_diversity,
            self.service_diversity,
            self.port_diversity,
            self.in_out_ratio,
            self.total_bytes,
            self.total_flows,
            self.active_hours,
            self.business_hours_ratio,
            self.bytes_per_flow,
            self.is_likely_server,
            self.has_user,
            self.group_count,
            self.is_privileged,
            self.is_laptop,
            self.is_server,
            self.is_printer,
            self.is_iot,
            self.is_phone,
        ])
    
    @staticmethod
    def feature_names() -> List[str]:
        """Return feature names in order."""
        return [
            "peer_diversity",
            "service_diversity",
            "port_diversity",
            "in_out_ratio",
            "total_bytes",
            "total_flows",
            "active_hours",
            "business_hours_ratio",
            "bytes_per_flow",
            "is_likely_server",
            "has_user",
            "group_count",
            "is_privileged",
            "is_laptop",
            "is_server",
            "is_printer",
            "is_iot",
            "is_phone",
        ]


class FeatureExtractor:
    """
    Extract feature vectors from EndpointSketches.
    
    Converts behavioral sketches into normalized feature vectors
    suitable for clustering algorithms.
    
    Example:
        >>> extractor = FeatureExtractor()
        >>> features = extractor.extract_all(sketch_store)
        >>> X = extractor.to_matrix(features)
    """
    
    def __init__(
        self,
        normalize: bool = True,
        log_transform_bytes: bool = True,
    ):
        """
        Initialize the feature extractor.
        
        Args:
            normalize: Whether to normalize features (StandardScaler)
            log_transform_bytes: Apply log transform to byte counts
        """
        self.normalize = normalize
        self.log_transform_bytes = log_transform_bytes
        self._scaler: Optional[StandardScaler] = None
        self._feature_names = FeatureVector.feature_names()
    
    def extract(self, sketch: EndpointSketch) -> FeatureVector:
        """
        Extract features from a single sketch.
        
        Args:
            sketch: EndpointSketch to extract features from
            
        Returns:
            FeatureVector with raw features
        """
        fv = FeatureVector(endpoint_id=sketch.endpoint_id)
        
        # Diversity features (log-scaled for better distribution)
        fv.peer_diversity = self._log_scale(sketch.peer_diversity)
        fv.service_diversity = self._log_scale(sketch.service_diversity)
        fv.port_diversity = self._log_scale(sketch.port_diversity)
        
        # Traffic features
        fv.in_out_ratio = sketch.in_out_ratio
        total_bytes = sketch.bytes_in + sketch.bytes_out
        fv.total_bytes = self._log_scale(total_bytes) if self.log_transform_bytes else total_bytes
        fv.total_flows = self._log_scale(sketch.flow_count)
        
        # Temporal features
        fv.active_hours = sketch.active_hour_count / 24.0  # Normalize to 0-1
        fv.business_hours_ratio = self._calc_business_hours_ratio(sketch)
        
        # Computed features
        if sketch.flow_count > 0:
            fv.bytes_per_flow = self._log_scale(total_bytes / sketch.flow_count)
        fv.is_likely_server = 1.0 if sketch.is_likely_server else 0.0
        
        # Identity features
        fv.has_user = 1.0 if sketch.username else 0.0
        fv.group_count = self._log_scale(len(sketch.ad_groups))
        fv.is_privileged = 1.0 if self._is_privileged(sketch) else 0.0
        
        # Device type one-hot encoding
        device_type = (sketch.device_type or "").lower()
        fv.is_laptop = 1.0 if device_type == "laptop" else 0.0
        fv.is_server = 1.0 if device_type == "server" else 0.0
        fv.is_printer = 1.0 if device_type == "printer" else 0.0
        fv.is_iot = 1.0 if device_type in ("iot", "camera", "sensor") else 0.0
        fv.is_phone = 1.0 if device_type in ("phone", "mobile") else 0.0
        
        return fv
    
    def extract_all(self, store: SketchStore) -> List[FeatureVector]:
        """
        Extract features from all sketches in a store.
        
        Args:
            store: SketchStore with endpoint sketches
            
        Returns:
            List of FeatureVectors
        """
        logger.info(f"Extracting features from {len(store)} sketches")
        features = [self.extract(sketch) for sketch in store]
        logger.info(f"Extracted {len(features)} feature vectors")
        return features
    
    def to_matrix(
        self, 
        features: List[FeatureVector],
        fit_scaler: bool = True,
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Convert feature vectors to a numpy matrix.
        
        Args:
            features: List of FeatureVectors
            fit_scaler: Whether to fit the scaler (False for inference)
            
        Returns:
            Tuple of (feature matrix, endpoint IDs)
        """
        if not features:
            return np.array([]), []
        
        # Build matrix
        X = np.array([fv.to_array() for fv in features])
        endpoint_ids = [fv.endpoint_id for fv in features]
        
        # Normalize if requested
        if self.normalize:
            if fit_scaler or self._scaler is None:
                self._scaler = StandardScaler()
                X = self._scaler.fit_transform(X)
            else:
                X = self._scaler.transform(X)
        
        return X, endpoint_ids
    
    def _log_scale(self, value: float) -> float:
        """Apply log1p scaling for better distribution."""
        return math.log1p(value)
    
    def _calc_business_hours_ratio(self, sketch: EndpointSketch) -> float:
        """Calculate ratio of activity during business hours (8-18)."""
        if sketch.active_hour_count == 0:
            return 0.5
        
        business_mask = 0b000000111111111100000000  # Hours 8-17
        business_hours = bin(sketch.active_hours & business_mask).count('1')
        return business_hours / max(sketch.active_hour_count, 1)
    
    def _is_privileged(self, sketch: EndpointSketch) -> bool:
        """Check if endpoint belongs to privileged groups."""
        privileged_groups = {
            "Privileged-IT", "Network-Admins", "DevOps",
            "privileged-it", "network-admins", "devops"
        }
        return bool(set(sketch.ad_groups) & privileged_groups)
    
    @property
    def feature_names(self) -> List[str]:
        """Return feature names."""
        return self._feature_names
    
    def feature_importance(self, X: np.ndarray) -> Dict[str, float]:
        """
        Calculate feature variance (proxy for importance in clustering).
        
        Args:
            X: Feature matrix
            
        Returns:
            Dict mapping feature name to variance
        """
        variances = np.var(X, axis=0)
        return dict(zip(self._feature_names, variances))

