"""
Semantic Labeling for Clusters.

Labels clusters with human-readable names based on:
- AD group membership patterns
- ISE endpoint profiles
- Device types
- Behavioral patterns
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import logging

from clarion.sketches import EndpointSketch
from clarion.ingest.sketch_builder import SketchStore
from clarion.clustering.clusterer import ClusterResult

logger = logging.getLogger(__name__)


@dataclass
class ClusterLabel:
    """
    Semantic label for a cluster.
    
    Contains the human-readable name and justification.
    """
    cluster_id: int
    name: str  # e.g., "Corporate Users", "Servers", "IoT Devices"
    
    # Justification data
    primary_reason: str  # e.g., "80% are in Engineering-Users AD group"
    confidence: float  # 0.0 - 1.0
    
    # Supporting statistics
    member_count: int = 0
    top_ad_groups: List[Tuple[str, float]] = field(default_factory=list)
    top_ise_profiles: List[Tuple[str, float]] = field(default_factory=list)
    top_device_types: List[Tuple[str, float]] = field(default_factory=list)
    
    # Behavioral summary
    avg_peer_diversity: float = 0.0
    avg_in_out_ratio: float = 0.5
    is_server_cluster: bool = False
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "cluster_id": self.cluster_id,
            "name": self.name,
            "primary_reason": self.primary_reason,
            "confidence": self.confidence,
            "member_count": self.member_count,
            "top_ad_groups": self.top_ad_groups,
            "top_ise_profiles": self.top_ise_profiles,
            "top_device_types": self.top_device_types,
            "avg_peer_diversity": self.avg_peer_diversity,
            "avg_in_out_ratio": self.avg_in_out_ratio,
            "is_server_cluster": self.is_server_cluster,
        }


class SemanticLabeler:
    """
    Label clusters with semantic names.
    
    Analyzes cluster members to determine the best label based on:
    1. Dominant AD group membership
    2. ISE endpoint profile distribution
    3. Device type distribution
    4. Behavioral patterns (client vs server)
    
    Example:
        >>> labeler = SemanticLabeler()
        >>> labels = labeler.label_clusters(store, cluster_result)
        >>> for label in labels.values():
        ...     print(f"Cluster {label.cluster_id}: {label.name}")
    """
    
    # Label templates based on characteristics
    LABEL_TEMPLATES = {
        # By AD group patterns
        "engineering": "Engineering Users",
        "it": "IT Staff",
        "hr": "HR Users",
        "sales": "Sales Team",
        "marketing": "Marketing Team",
        "finance": "Finance Users",
        "operations": "Operations Staff",
        "facilities": "Facilities Staff",
        "legal": "Legal Team",
        "r&d": "R&D Team",
        "privileged": "Privileged Admins",
        
        # By device type
        "laptop": "Corporate Laptops",
        "server": "Servers",
        "printer": "Printers",
        "iot": "IoT Devices",
        "phone": "Mobile Devices",
        
        # By behavior
        "high_peer": "High-Activity Endpoints",
        "server_behavior": "Server-Like Endpoints",
        "low_activity": "Low-Activity Endpoints",
    }
    
    def __init__(
        self,
        min_confidence: float = 0.5,
        group_threshold: float = 0.3,
    ):
        """
        Initialize the labeler.
        
        Args:
            min_confidence: Minimum confidence for labeling
            group_threshold: Minimum ratio for AD group to be significant
        """
        self.min_confidence = min_confidence
        self.group_threshold = group_threshold
    
    def label_clusters(
        self,
        store: SketchStore,
        result: ClusterResult,
    ) -> Dict[int, ClusterLabel]:
        """
        Label all clusters.
        
        Args:
            store: SketchStore with enriched sketches
            result: ClusterResult with cluster assignments
            
        Returns:
            Dict mapping cluster_id to ClusterLabel
        """
        logger.info(f"Labeling {result.n_clusters} clusters")
        
        # Build endpoint lookup
        endpoint_lookup = {s.endpoint_id: s for s in store}
        
        labels = {}
        for cluster_id in range(result.n_clusters):
            # Get cluster members
            member_ids = result.get_cluster_members(cluster_id)
            members = [
                endpoint_lookup[eid] 
                for eid in member_ids 
                if eid in endpoint_lookup
            ]
            
            if not members:
                continue
            
            # Analyze and label the cluster
            label = self._label_cluster(cluster_id, members)
            labels[cluster_id] = label
        
        # Also label noise cluster (-1) if it exists
        if result.n_noise > 0:
            noise_ids = result.get_cluster_members(-1)
            noise_members = [
                endpoint_lookup[eid]
                for eid in noise_ids
                if eid in endpoint_lookup
            ]
            if noise_members:
                # Calculate behavioral metrics for noise cluster
                n_noise = len(noise_members)
                avg_peer_diversity = sum(m.peer_diversity for m in noise_members) / n_noise
                avg_in_out_ratio = sum(m.in_out_ratio for m in noise_members) / n_noise
                
                # Count statistics for noise cluster
                ad_groups = self._count_ad_groups(noise_members)
                ise_profiles = self._count_ise_profiles(noise_members)
                device_types = self._count_device_types(noise_members)
                
                labels[-1] = ClusterLabel(
                    cluster_id=-1,
                    name="Unclustered (Noise)",
                    primary_reason="Did not fit any cluster pattern",
                    confidence=0.0,
                    member_count=n_noise,
                    top_ad_groups=ad_groups[:5],
                    top_ise_profiles=ise_profiles[:5],
                    top_device_types=device_types[:5],
                    avg_peer_diversity=avg_peer_diversity,
                    avg_in_out_ratio=avg_in_out_ratio,
                    is_server_cluster=False,
                )
        
        logger.info(f"Labeled {len(labels)} clusters")
        return labels
    
    def _label_cluster(
        self,
        cluster_id: int,
        members: List[EndpointSketch],
    ) -> ClusterLabel:
        """
        Generate a label for a single cluster.
        
        Tries multiple strategies in order:
        1. ISE profile if dominant
        2. Device type if dominant
        3. AD group if dominant
        4. Behavioral pattern as fallback
        """
        n_members = len(members)
        
        # Collect statistics
        ad_groups = self._count_ad_groups(members)
        ise_profiles = self._count_ise_profiles(members)
        device_types = self._count_device_types(members)
        
        # Calculate behavioral metrics
        avg_peer_diversity = sum(m.peer_diversity for m in members) / n_members
        avg_in_out_ratio = sum(m.in_out_ratio for m in members) / n_members
        server_count = sum(1 for m in members if m.is_likely_server)
        is_server_cluster = server_count / n_members > 0.5
        
        # Try to find the best label
        name, reason, confidence = self._determine_label(
            ad_groups, ise_profiles, device_types,
            avg_in_out_ratio, is_server_cluster,
            n_members
        )
        
        return ClusterLabel(
            cluster_id=cluster_id,
            name=name,
            primary_reason=reason,
            confidence=confidence,
            member_count=n_members,
            top_ad_groups=ad_groups[:5],
            top_ise_profiles=ise_profiles[:5],
            top_device_types=device_types[:5],
            avg_peer_diversity=avg_peer_diversity,
            avg_in_out_ratio=avg_in_out_ratio,
            is_server_cluster=is_server_cluster,
        )
    
    def _determine_label(
        self,
        ad_groups: List[Tuple[str, float]],
        ise_profiles: List[Tuple[str, float]],
        device_types: List[Tuple[str, float]],
        avg_in_out_ratio: float,
        is_server_cluster: bool,
        n_members: int,
    ) -> Tuple[str, str, float]:
        """
        Determine the best label for a cluster.
        
        Returns:
            Tuple of (name, reason, confidence)
        """
        # Strategy 1: Check ISE profile
        if ise_profiles and ise_profiles[0][1] >= self.group_threshold:
            profile, ratio = ise_profiles[0]
            name = self._profile_to_name(profile)
            return (
                name,
                f"{ratio*100:.0f}% have ISE profile '{profile}'",
                ratio,
            )
        
        # Strategy 2: Check device type, but use traffic patterns to refine
        if device_types and device_types[0][1] >= self.group_threshold:
            dtype, ratio = device_types[0]
            
            # Special handling for phones: distinguish IP phones from mobile phones
            # This is critical because they have completely different traffic patterns
            if dtype in ("phone", "mobile"):
                # Analyze traffic patterns to distinguish
                # IP phones: low peer diversity, high destination concentration, VoIP ports
                # Mobile phones: high peer diversity, low destination concentration, many protocols
                avg_peer_div = sum(m.peer_diversity for m in members) / len(members) if members else 0
                avg_dest_conc = sum(
                    (1.0 / (1.0 + math.log1p(m.peer_diversity))) if m.peer_diversity > 0 else 1.0
                    for m in members
                ) / len(members) if members else 0
                
                # IP phone pattern: low peer diversity (< 10), high concentration (> 0.6)
                # IP phones talk primarily to call manager (1-3 destinations)
                # Mobile phones talk to many services (email, web, apps, etc.)
                if avg_peer_div < 10 and avg_dest_conc > 0.6:
                    name = "IP Phones"
                    reason = f"{ratio*100:.0f}% are phones with IP phone traffic pattern (low peer diversity {avg_peer_div:.1f}, VoIP-like)"
                else:
                    name = "Mobile Devices"
                    reason = f"{ratio*100:.0f}% are phones with mobile device traffic pattern (high peer diversity {avg_peer_div:.1f})"
                
                return (name, reason, ratio)
            
            # For other device types, use standard naming
            name = self._device_type_to_name(dtype)
            return (
                name,
                f"{ratio*100:.0f}% are {dtype} devices",
                ratio,
            )
        
        # Strategy 3: Check AD groups (only if available)
        if ad_groups:
            # Filter out generic groups like "All-Employees"
            specific_groups = [
                (g, r) for g, r in ad_groups
                if g.lower() not in ("all-employees", "domain-users")
            ]
            if specific_groups and specific_groups[0][1] >= self.group_threshold:
                group, ratio = specific_groups[0]
                name = self._ad_group_to_name(group)
                return (
                    name,
                    f"{ratio*100:.0f}% are in '{group}' AD group",
                    ratio,
                )
        
        # Strategy 4: Behavioral pattern (works for all device types)
        if is_server_cluster:
            return (
                "Server-Like Endpoints",
                "Majority have server behavior (receive > send)",
                0.6 if avg_in_out_ratio > 0.7 else 0.5,
            )
        
        # Strategy 5: Client behavior pattern (for non-AD devices)
        if avg_in_out_ratio < 0.3:
            return (
                "Client Devices",
                "Majority have client behavior (send > receive)",
                0.5,
            )
        
        # Fallback: use member count as identifier (works for any device)
        return (
            f"Endpoint Group {n_members}",
            "Could not determine dominant characteristic (no identity data)",
            0.3,
        )
    
    def _count_ad_groups(
        self,
        members: List[EndpointSketch],
    ) -> List[Tuple[str, float]]:
        """Count AD group membership, return sorted by frequency."""
        counter: Counter = Counter()
        n_with_groups = 0
        
        for m in members:
            if m.ad_groups:
                n_with_groups += 1
                for group in m.ad_groups:
                    counter[group] += 1
        
        if n_with_groups == 0:
            return []
        
        # Convert to ratios
        result = [
            (group, count / len(members))
            for group, count in counter.most_common(10)
        ]
        return result
    
    def _count_ise_profiles(
        self,
        members: List[EndpointSketch],
    ) -> List[Tuple[str, float]]:
        """Count ISE profiles, return sorted by frequency."""
        counter: Counter = Counter()
        
        for m in members:
            if m.ise_profile:
                counter[m.ise_profile] += 1
        
        if not counter:
            return []
        
        return [
            (profile, count / len(members))
            for profile, count in counter.most_common(10)
        ]
    
    def _count_device_types(
        self,
        members: List[EndpointSketch],
    ) -> List[Tuple[str, float]]:
        """Count device types, return sorted by frequency."""
        counter: Counter = Counter()
        
        for m in members:
            if m.device_type:
                counter[m.device_type] += 1
        
        if not counter:
            return []
        
        return [
            (dtype, count / len(members))
            for dtype, count in counter.most_common(10)
        ]
    
    def _profile_to_name(self, profile: str) -> str:
        """Convert ISE profile to cluster name."""
        profile_lower = profile.lower()
        
        if "laptop" in profile_lower or "workstation" in profile_lower:
            return "Corporate Workstations"
        if "server" in profile_lower:
            return "Servers"
        if "printer" in profile_lower:
            return "Printers"
        if "iot" in profile_lower or "camera" in profile_lower:
            return "IoT Devices"
        if "phone" in profile_lower or "mobile" in profile_lower:
            return "Mobile Devices"
        
        return f"{profile} Devices"
    
    def _device_type_to_name(self, device_type: str) -> str:
        """Convert device type to cluster name."""
        dtype_lower = device_type.lower()
        mapping = {
            # Windows devices
            "laptop": "Corporate Laptops",
            "workstation": "Corporate Workstations",
            "desktop": "Corporate Desktops",
            
            # Linux devices
            "linux": "Linux Devices",
            "linux-server": "Linux Servers",
            "linux-workstation": "Linux Workstations",
            
            # Mac devices
            "mac": "Mac Devices",
            "macbook": "Mac Users",
            "imac": "Mac Users",
            
            # Servers (any OS)
            "server": "Servers",
            "windows-server": "Windows Servers",
            
            # IoT and embedded
            "iot": "IoT Devices",
            "printer": "Printers",
            "camera": "Security Cameras",
            "sensor": "Sensors",
            "phone": "Mobile Devices",
            "mobile": "Mobile Devices",
            
            # Network devices
            "switch": "Network Switches",
            "router": "Network Routers",
            "firewall": "Network Firewalls",
        }
        return mapping.get(dtype_lower, f"{device_type.title()} Devices")
    
    def _ad_group_to_name(self, group: str) -> str:
        """Convert AD group name to cluster name."""
        # Remove common suffixes
        clean = group.replace("-Users", "").replace("_Users", "")
        clean = clean.replace("-users", "").replace("_users", "")
        
        # Special cases
        if "privileged" in clean.lower() or "admin" in clean.lower():
            return "Privileged Admins"
        if "it" in clean.lower() and len(clean) < 5:
            return "IT Staff"
        
        return f"{clean} Users"

