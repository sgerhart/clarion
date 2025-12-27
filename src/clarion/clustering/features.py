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
    
    # Traffic pattern features (for distinguishing similar device types)
    destination_concentration: float = 0.0  # Low = many destinations, High = few (IP phone pattern)
    protocol_concentration: float = 0.0  # Low = many protocols, High = few (IP phone uses SIP/RTP)
    voip_port_usage: float = 0.0  # Ratio of traffic on VoIP ports (5060, 5061, RTP range)
    stationary_pattern: float = 0.0  # Activity consistency (IP phones are stationary)
    
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
            # Traffic pattern features for distinguishing similar device types
            self.destination_concentration,
            self.protocol_concentration,
            self.voip_port_usage,
            self.stationary_pattern,
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
            # Traffic pattern features
            "destination_concentration",
            "protocol_concentration",
            "voip_port_usage",
            "stationary_pattern",
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
        
        # Traffic pattern features for distinguishing similar device types
        # These help separate IP phones from mobile phones, etc.
        fv.destination_concentration = self._calc_destination_concentration(sketch)
        fv.protocol_concentration = self._calc_protocol_concentration(sketch)
        fv.voip_port_usage = self._calc_voip_port_usage(sketch)
        fv.stationary_pattern = self._calc_stationary_pattern(sketch)
        
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
    
    def _calc_destination_concentration(self, sketch: EndpointSketch) -> float:
        """
        Calculate destination concentration (inverse of peer diversity).
        
        High concentration (low diversity) = talks to few destinations (IP phone pattern)
        Low concentration (high diversity) = talks to many destinations (mobile phone pattern)
        
        Returns: 0.0 (many destinations) to 1.0 (few destinations)
        """
        if sketch.peer_diversity == 0:
            return 1.0  # No peers = maximum concentration
        
        # Normalize: more peers = lower concentration
        # Use inverse log scale: 1 / (1 + log(peers))
        # This gives: 1 peer = 1.0, 10 peers = 0.5, 100 peers = 0.25
        concentration = 1.0 / (1.0 + self._log_scale(sketch.peer_diversity))
        return min(1.0, max(0.0, concentration))
    
    def _calc_protocol_concentration(self, sketch: EndpointSketch) -> float:
        """
        Calculate protocol/service concentration.
        
        IP phones use primarily SIP (5060/5061) and RTP (high ports)
        Mobile phones use many protocols (HTTP, HTTPS, SMTP, IMAP, etc.)
        
        Returns: 0.0 (many protocols) to 1.0 (few protocols)
        """
        if sketch.service_diversity == 0:
            return 1.0
        
        # Similar to destination concentration
        concentration = 1.0 / (1.0 + self._log_scale(sketch.service_diversity))
        return min(1.0, max(0.0, concentration))
    
    def _calc_voip_port_usage(self, sketch: EndpointSketch) -> float:
        """
        Calculate ratio of traffic on VoIP-related ports.
        
        IP phones use:
        - SIP: 5060 (UDP/TCP), 5061 (TLS)
        - RTP: 16384-32767 (dynamic range)
        
        Returns: 0.0 (no VoIP ports) to 1.0 (all traffic on VoIP ports)
        """
        # VoIP ports: SIP (5060, 5061) and RTP range (16384-32767)
        voip_ports = {5060, 5061}
        rtp_min, rtp_max = 16384, 32767
        
        # We don't have port frequency breakdown in the sketch easily accessible
        # So we'll use a heuristic: if device_type is phone and has low peer diversity,
        # it's likely an IP phone using VoIP ports
        device_type = (sketch.device_type or "").lower()
        is_phone_like = device_type in ("phone", "mobile", "voip", "ip-phone")
        
        if not is_phone_like:
            return 0.0
        
        # Heuristic: IP phones have low peer diversity and talk to call manager
        # If peer_diversity < 5 and is_phone, likely IP phone
        if sketch.peer_diversity < 5 and device_type in ("phone", "voip", "ip-phone"):
            return 0.8  # High likelihood of VoIP
        elif sketch.peer_diversity < 10 and device_type in ("phone", "voip", "ip-phone"):
            return 0.5  # Medium likelihood
        else:
            return 0.2  # Low likelihood (probably mobile phone)
    
    def _calc_stationary_pattern(self, sketch: EndpointSketch) -> float:
        """
        Calculate stationary pattern score.
        
        IP phones are stationary (same switch, consistent activity)
        Mobile phones move around (different switches, variable activity)
        
        Uses business_hours_ratio as proxy: IP phones are active during business hours
        Mobile phones are active 24/7
        
        Returns: 0.0 (mobile/variable) to 1.0 (stationary/consistent)
        """
        # High business hours ratio = stationary (IP phone pattern)
        # Low business hours ratio = mobile/24-7 (mobile phone pattern)
        # But we need to account for both extremes
        
        if sketch.active_hour_count == 0:
            return 0.5
        
        business_ratio = self._calc_business_hours_ratio(sketch)
        
        # IP phones: high business hours activity (0.7-1.0) = stationary
        # Mobile phones: more distributed activity (0.3-0.7) = mobile
        if business_ratio > 0.7:
            return business_ratio  # High business hours = stationary
        elif business_ratio < 0.3:
            return 0.2  # Low business hours = likely mobile/24-7
        else:
            return 0.5  # Mixed pattern
    
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

