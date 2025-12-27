"""
SGT Mapper - Map Clusters to TrustSec Security Group Tags.

Generates SGT recommendations based on cluster analysis,
including suggested SGT values, names, and confidence scores.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import logging

from clarion.sketches import EndpointSketch
from clarion.ingest.sketch_builder import SketchStore
from clarion.clustering.clusterer import ClusterResult
from clarion.clustering.labeling import ClusterLabel, SemanticLabeler

logger = logging.getLogger(__name__)


@dataclass
class SGTRecommendation:
    """
    SGT recommendation for a cluster.
    
    Contains the proposed SGT value, name, and justification.
    """
    cluster_id: int
    sgt_value: int
    sgt_name: str
    
    # Source cluster info
    cluster_label: str
    cluster_size: int
    
    # Confidence and justification
    confidence: float  # 0.0 - 1.0
    justification: str
    
    # Affected endpoints
    endpoint_count: int
    sample_endpoints: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "cluster_id": self.cluster_id,
            "sgt_value": self.sgt_value,
            "sgt_name": self.sgt_name,
            "cluster_label": self.cluster_label,
            "cluster_size": self.cluster_size,
            "confidence": self.confidence,
            "justification": self.justification,
            "endpoint_count": self.endpoint_count,
            "sample_endpoints": self.sample_endpoints[:10],
        }


@dataclass
class SGTTaxonomy:
    """
    Complete SGT taxonomy recommended for the network.
    
    Contains all SGT recommendations and statistics.
    """
    recommendations: List[SGTRecommendation]
    
    # Coverage statistics
    total_endpoints: int = 0
    covered_endpoints: int = 0
    uncovered_endpoints: int = 0
    
    # Summary
    n_sgts: int = 0
    avg_confidence: float = 0.0
    
    def coverage_ratio(self) -> float:
        """Calculate endpoint coverage ratio."""
        if self.total_endpoints == 0:
            return 0.0
        return self.covered_endpoints / self.total_endpoints
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "recommendations": [r.to_dict() for r in self.recommendations],
            "total_endpoints": self.total_endpoints,
            "covered_endpoints": self.covered_endpoints,
            "uncovered_endpoints": self.uncovered_endpoints,
            "coverage_ratio": self.coverage_ratio(),
            "n_sgts": self.n_sgts,
            "avg_confidence": self.avg_confidence,
        }
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"SGT Taxonomy: {self.n_sgts} Security Group Tags",
            f"Coverage: {self.covered_endpoints}/{self.total_endpoints} "
            f"({self.coverage_ratio()*100:.1f}%)",
            "",
            "Recommended SGTs:",
        ]
        
        for rec in sorted(self.recommendations, key=lambda r: r.sgt_value):
            lines.append(
                f"  SGT {rec.sgt_value:3d} | {rec.sgt_name:25s} | "
                f"{rec.endpoint_count:5d} endpoints | "
                f"conf={rec.confidence:.2f}"
            )
        
        return "\n".join(lines)


class SGTMapper:
    """
    Map clusters to TrustSec SGT recommendations.
    
    Takes cluster labels and generates a proposed SGT taxonomy,
    including SGT values, names, and endpoint assignments.
    
    Example:
        >>> mapper = SGTMapper()
        >>> taxonomy = mapper.generate_taxonomy(store, cluster_result, labels)
        >>> print(taxonomy.summary())
    """
    
    # Default SGT value ranges by category
    SGT_RANGES = {
        "users": (2, 9),       # User groups
        "servers": (10, 19),   # Servers and services
        "devices": (20, 29),   # Printers, IoT, etc.
        "special": (30, 39),   # Special purpose
    }
    
    # SGT name templates
    SGT_TEMPLATES = {
        "Corporate Laptops": ("Corp-Users", "users"),
        "Corporate Workstations": ("Corp-Users", "users"),
        "Engineering Users": ("Engineering", "users"),
        "IT Staff": ("IT-Staff", "users"),
        "Privileged Admins": ("Privileged-IT", "users"),
        "HR Users": ("HR-Users", "users"),
        "Sales Team": ("Sales", "users"),
        "Marketing Team": ("Marketing", "users"),
        "Finance Users": ("Finance", "users"),
        "Operations Staff": ("Operations", "users"),
        "Servers": ("Servers", "servers"),
        "Server-Like Endpoints": ("Servers", "servers"),
        "Printers": ("Printers", "devices"),
        "IoT Devices": ("IoT", "devices"),
        "Mobile Devices": ("Mobile", "users"),
        "Security Cameras": ("Cameras", "devices"),
    }
    
    def __init__(
        self,
        base_sgt_value: int = 2,
        min_cluster_size: int = 10,
    ):
        """
        Initialize the mapper.
        
        Args:
            base_sgt_value: Starting SGT value for assignments
            min_cluster_size: Minimum cluster size for SGT recommendation
        """
        self.base_sgt_value = base_sgt_value
        self.min_cluster_size = min_cluster_size
        self._next_sgt = {
            "users": self.SGT_RANGES["users"][0],
            "servers": self.SGT_RANGES["servers"][0],
            "devices": self.SGT_RANGES["devices"][0],
            "special": self.SGT_RANGES["special"][0],
        }
    
    def generate_taxonomy(
        self,
        store: SketchStore,
        result: ClusterResult,
        labels: Dict[int, ClusterLabel],
    ) -> SGTTaxonomy:
        """
        Generate SGT taxonomy from cluster labels.
        
        Args:
            store: SketchStore with endpoint sketches
            result: ClusterResult with cluster assignments
            labels: Dict of cluster labels from SemanticLabeler
            
        Returns:
            SGTTaxonomy with all recommendations
        """
        logger.info(f"Generating SGT taxonomy from {len(labels)} clusters")
        
        recommendations = []
        covered_endpoints = 0
        
        # Reset SGT counters
        self._next_sgt = {
            "users": self.SGT_RANGES["users"][0],
            "servers": self.SGT_RANGES["servers"][0],
            "devices": self.SGT_RANGES["devices"][0],
            "special": self.SGT_RANGES["special"][0],
        }
        
        # Used names to avoid duplicates
        used_names: Set[str] = set()
        
        for cluster_id, label in sorted(labels.items()):
            # Skip noise cluster and small clusters
            if cluster_id == -1:
                continue
            if label.member_count < self.min_cluster_size:
                continue
            
            # Generate SGT recommendation
            rec = self._create_recommendation(
                cluster_id, label, result, used_names
            )
            
            if rec:
                recommendations.append(rec)
                covered_endpoints += rec.endpoint_count
                used_names.add(rec.sgt_name)
        
        # Calculate statistics
        total_endpoints = len(result.endpoint_ids)
        uncovered = total_endpoints - covered_endpoints
        
        avg_confidence = 0.0
        if recommendations:
            avg_confidence = sum(r.confidence for r in recommendations) / len(recommendations)
        
        taxonomy = SGTTaxonomy(
            recommendations=recommendations,
            total_endpoints=total_endpoints,
            covered_endpoints=covered_endpoints,
            uncovered_endpoints=uncovered,
            n_sgts=len(recommendations),
            avg_confidence=avg_confidence,
        )
        
        logger.info(
            f"Generated taxonomy: {taxonomy.n_sgts} SGTs, "
            f"{taxonomy.coverage_ratio()*100:.1f}% coverage"
        )
        
        return taxonomy
    
    def _create_recommendation(
        self,
        cluster_id: int,
        label: ClusterLabel,
        result: ClusterResult,
        used_names: Set[str],
    ) -> Optional[SGTRecommendation]:
        """
        Create an SGT recommendation for a cluster.
        
        Args:
            cluster_id: Cluster ID
            label: ClusterLabel for this cluster
            result: ClusterResult for endpoint lookup
            used_names: Set of already-used SGT names
            
        Returns:
            SGTRecommendation or None if skipped
        """
        # Determine SGT name and category
        sgt_name, category = self._determine_sgt_name(label, used_names)
        
        # Allocate SGT value
        sgt_value = self._allocate_sgt_value(category)
        
        # Get sample endpoints
        member_ids = result.get_cluster_members(cluster_id)
        sample = member_ids[:10]
        
        # Generate justification
        justification = self._generate_justification(label)
        
        return SGTRecommendation(
            cluster_id=cluster_id,
            sgt_value=sgt_value,
            sgt_name=sgt_name,
            cluster_label=label.name,
            cluster_size=label.member_count,
            confidence=label.confidence,
            justification=justification,
            endpoint_count=label.member_count,
            sample_endpoints=sample,
        )
    
    def _determine_sgt_name(
        self,
        label: ClusterLabel,
        used_names: Set[str],
    ) -> Tuple[str, str]:
        """
        Determine SGT name and category from cluster label.
        
        Returns:
            Tuple of (sgt_name, category)
        """
        # Check if we have a template for this label
        if label.name in self.SGT_TEMPLATES:
            base_name, category = self.SGT_TEMPLATES[label.name]
        else:
            # Infer from behavioral patterns
            if label.is_server_cluster:
                base_name = "Servers"
                category = "servers"
            elif label.avg_in_out_ratio > 0.6:
                base_name = "Receivers"
                category = "servers"
            else:
                base_name = "Users"
                category = "users"
        
        # Make name unique if needed
        name = base_name
        counter = 2
        while name in used_names:
            name = f"{base_name}-{counter}"
            counter += 1
        
        return name, category
    
    def _allocate_sgt_value(self, category: str) -> int:
        """Allocate the next available SGT value in a category."""
        value = self._next_sgt.get(category, self.base_sgt_value)
        
        # Increment for next use
        self._next_sgt[category] = value + 1
        
        # Check bounds
        min_val, max_val = self.SGT_RANGES.get(category, (2, 99))
        if value > max_val:
            # Overflow to special range
            value = self._next_sgt["special"]
            self._next_sgt["special"] += 1
        
        return value
    
    def _generate_justification(self, label: ClusterLabel) -> str:
        """Generate human-readable justification for the SGT."""
        parts = [label.primary_reason]
        
        if label.top_device_types:
            dtype, ratio = label.top_device_types[0]
            if ratio > 0.5:
                parts.append(f"Device type: {dtype} ({ratio*100:.0f}%)")
        
        if label.is_server_cluster:
            parts.append(
                f"Server behavior (avg in/out ratio: {label.avg_in_out_ratio:.2f})"
            )
        
        return "; ".join(parts)
    
    def apply_to_store(
        self,
        store: SketchStore,
        result: ClusterResult,
        taxonomy: SGTTaxonomy,
    ) -> int:
        """
        Apply SGT assignments to sketches in store.
        
        Note: This sets a recommended_sgt field, not the actual SGT.
        
        Args:
            store: SketchStore to update
            result: ClusterResult with cluster assignments
            taxonomy: SGTTaxonomy with recommendations
            
        Returns:
            Number of endpoints updated
        """
        # Build cluster_id → sgt_value mapping
        cluster_to_sgt = {
            rec.cluster_id: rec.sgt_value
            for rec in taxonomy.recommendations
        }
        
        # Build endpoint → cluster mapping
        endpoint_to_cluster = dict(zip(result.endpoint_ids, result.labels))
        
        updated = 0
        for sketch in store:
            cluster_id = endpoint_to_cluster.get(sketch.endpoint_id, -1)
            if cluster_id in cluster_to_sgt:
                # Store as attribute (would need to add to EndpointSketch)
                # For now, we use the local_cluster_id to track the mapping
                sketch.local_cluster_id = cluster_id
                updated += 1
        
        logger.info(f"Applied SGT recommendations to {updated} endpoints")
        return updated


def generate_sgt_taxonomy(
    store: SketchStore,
    result: ClusterResult,
) -> SGTTaxonomy:
    """
    Convenience function to generate SGT taxonomy.
    
    Runs semantic labeling and SGT mapping in one step.
    
    Args:
        store: SketchStore with enriched sketches
        result: ClusterResult with cluster assignments
        
    Returns:
        SGTTaxonomy with recommendations
    """
    labeler = SemanticLabeler()
    labels = labeler.label_clusters(store, result)
    
    mapper = SGTMapper()
    return mapper.generate_taxonomy(store, result, labels)


