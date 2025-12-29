"""
User Traffic-Based Clustering Module

Enhances user clustering by combining AD groups with traffic pattern analysis.
This identifies users with similar network access patterns who may need different
SGT assignments than their AD groups suggest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import logging
import json
from collections import Counter, defaultdict

import numpy as np
import hdbscan
from sklearn.preprocessing import StandardScaler

from clarion.storage import get_database
from clarion.clustering.user_clusterer import UserClusterer, UserCluster

logger = logging.getLogger(__name__)


@dataclass
class UserTrafficFeatures:
    """Traffic-based features for a user."""
    user_id: str
    bytes_in: float = 0.0
    bytes_out: float = 0.0
    total_bytes: float = 0.0
    total_flows: float = 0.0
    unique_peers: float = 0.0
    unique_services: float = 0.0
    # Port diversity (entropy of port distribution)
    port_diversity: float = 0.0
    # Protocol distribution
    protocol_tcp: float = 0.0
    protocol_udp: float = 0.0
    protocol_other: float = 0.0


class UserTrafficBasedClusterer:
    """
    Cluster users based on AD groups AND traffic patterns.
    
    This combines:
    1. AD group-based clustering (organizational structure)
    2. Traffic pattern clustering (actual network behavior)
    
    This enables identification of:
    - Users who should be in different groups than AD groups suggest
    - Users with similar access patterns who need the same SGT
    - Security anomalies (users accessing resources outside their AD group scope)
    
    Example:
        >>> clusterer = UserTrafficBasedClusterer()
        >>> clusters = clusterer.cluster_users()
        >>> for cluster in clusters:
        ...     print(f"{cluster.name}: {cluster.user_count} users")
    """
    
    def __init__(
        self,
        min_cluster_size: int = 5,
        group_threshold: float = 0.3,
        traffic_weight: float = 0.5,  # Weight for traffic vs AD group clustering
        min_traffic_flows: int = 10,  # Minimum flows to include in traffic clustering
    ):
        """
        Initialize the traffic-based user clusterer.
        
        Args:
            min_cluster_size: Minimum users to form a cluster
            group_threshold: Minimum ratio for AD group to be significant
            traffic_weight: Weight for traffic pattern similarity (0.0-1.0)
            min_traffic_flows: Minimum flows required to use traffic-based clustering
        """
        self.min_cluster_size = min_cluster_size
        self.group_threshold = group_threshold
        self.traffic_weight = traffic_weight
        self.min_traffic_flows = min_traffic_flows
        self.db = get_database()
        self._base_clusterer = UserClusterer(
            min_cluster_size=min_cluster_size,
            group_threshold=group_threshold,
        )
    
    def extract_traffic_features(self) -> Dict[str, UserTrafficFeatures]:
        """
        Extract traffic features for all users with traffic data.
        
        Returns:
            Dictionary mapping user_id to UserTrafficFeatures
        """
        conn = self.db._get_connection()
        
        # Get all users with traffic patterns
        query = """
            SELECT 
                user_id,
                total_bytes_in,
                total_bytes_out,
                total_flows,
                unique_peers,
                unique_services,
                top_ports,
                top_protocols
            FROM user_traffic_patterns
            WHERE total_flows >= ?
        """
        
        rows = conn.execute(query, (self.min_traffic_flows,)).fetchall()
        
        features = {}
        for row in rows:
            user_id = row['user_id']
            bytes_in = float(row['total_bytes_in'] or 0)
            bytes_out = float(row['total_bytes_out'] or 0)
            total_flows = float(row['total_flows'] or 0)
            unique_peers = float(row['unique_peers'] or 0)
            unique_services = float(row['unique_services'] or 0)
            
            # Parse top_ports and top_protocols (JSON)
            top_ports_json = row.get('top_ports', '[]')
            top_protocols_json = row.get('top_protocols', '[]')
            
            try:
                top_ports = json.loads(top_ports_json) if top_ports_json else []
                top_protocols = json.loads(top_protocols_json) if top_protocols_json else []
            except (json.JSONDecodeError, TypeError):
                top_ports = []
                top_protocols = []
            
            # Calculate port diversity (entropy-like measure)
            # More diverse ports = higher entropy
            port_diversity = 0.0
            if top_ports and isinstance(top_ports, list):
                total_port_bytes = sum(p.get('bytes', 0) for p in top_ports if isinstance(p, dict))
                if total_port_bytes > 0:
                    port_probs = [p.get('bytes', 0) / total_port_bytes for p in top_ports if isinstance(p, dict)]
                    port_diversity = -sum(p * np.log(p + 1e-10) for p in port_probs if p > 0)
            
            # Calculate protocol distribution
            protocol_tcp = 0.0
            protocol_udp = 0.0
            protocol_other = 0.0
            
            if top_protocols and isinstance(top_protocols, list):
                total_proto_bytes = sum(p.get('bytes', 0) for p in top_protocols if isinstance(p, dict))
                if total_proto_bytes > 0:
                    for proto_entry in top_protocols:
                        if isinstance(proto_entry, dict):
                            proto = proto_entry.get('protocol', 0)
                            bytes_count = proto_entry.get('bytes', 0)
                            ratio = bytes_count / total_proto_bytes
                            
                            # Protocol numbers: 6=TCP, 17=UDP
                            if proto == 6:
                                protocol_tcp = ratio
                            elif proto == 17:
                                protocol_udp = ratio
                            else:
                                protocol_other += ratio
            
            feature = UserTrafficFeatures(
                user_id=user_id,
                bytes_in=bytes_in,
                bytes_out=bytes_out,
                total_bytes=bytes_in + bytes_out,
                total_flows=total_flows,
                unique_peers=unique_peers,
                unique_services=unique_services,
                port_diversity=port_diversity,
                protocol_tcp=protocol_tcp,
                protocol_udp=protocol_udp,
                protocol_other=protocol_other,
            )
            features[user_id] = feature
        
        logger.info(f"Extracted traffic features for {len(features)} users")
        return features
    
    def cluster_by_traffic(self, features: Dict[str, UserTrafficFeatures]) -> Dict[int, List[str]]:
        """
        Cluster users by traffic patterns using HDBSCAN.
        
        Args:
            features: Dictionary of user_id -> UserTrafficFeatures
            
        Returns:
            Dictionary mapping cluster_id -> list of user_ids
        """
        if len(features) < self.min_cluster_size:
            logger.warning(f"Not enough users with traffic data ({len(features)} < {self.min_cluster_size})")
            return {}
        
        # Convert to feature matrix
        user_ids = list(features.keys())
        feature_matrix = []
        
        for user_id in user_ids:
            feat = features[user_id]
            # Use log-scale for bytes to handle large variations
            feature_vector = [
                np.log1p(feat.bytes_in),  # log(1+x) to handle zeros
                np.log1p(feat.bytes_out),
                np.log1p(feat.total_flows),
                np.log1p(feat.unique_peers),
                np.log1p(feat.unique_services),
                feat.port_diversity,
                feat.protocol_tcp,
                feat.protocol_udp,
                feat.protocol_other,
            ]
            feature_matrix.append(feature_vector)
        
        X = np.array(feature_matrix)
        
        # Normalize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Run HDBSCAN
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=max(2, self.min_cluster_size // 3),
            metric='euclidean',
            core_dist_n_jobs=-1,
        )
        
        labels = clusterer.fit_predict(X_scaled)
        
        # Group users by cluster
        traffic_clusters: Dict[int, List[str]] = defaultdict(list)
        for user_id, label in zip(user_ids, labels):
            traffic_clusters[label].append(user_id)
        
        # Remove noise cluster (-1)
        if -1 in traffic_clusters:
            noise_users = traffic_clusters.pop(-1)
            logger.info(f"Traffic clustering: {len(traffic_clusters)} clusters, {len(noise_users)} noise users")
        
        return dict(traffic_clusters)
    
    def merge_clusters(
        self,
        ad_clusters: List[UserCluster],
        traffic_clusters: Dict[int, List[str]],
    ) -> List[UserCluster]:
        """
        Merge AD group clusters with traffic-based clusters.
        
        Strategy:
        1. Start with AD group clusters as base
        2. For users with similar traffic patterns but different AD groups,
           create new clusters or adjust existing ones
        3. Identify users whose traffic suggests they should be in different groups
        
        Args:
            ad_clusters: Clusters from AD group-based clustering
            traffic_clusters: Clusters from traffic-based clustering
            
        Returns:
            Merged list of UserCluster objects
        """
        if not traffic_clusters:
            logger.info("No traffic clusters to merge, returning AD clusters only")
            return ad_clusters
        
        # Create user_id -> AD cluster mapping
        user_to_ad_cluster: Dict[str, int] = {}
        for cluster in ad_clusters:
            for user_id in cluster.user_ids:
                user_to_ad_cluster[user_id] = cluster.cluster_id
        
        # Start with AD clusters as base
        merged_clusters: Dict[int, UserCluster] = {
            cluster.cluster_id: cluster for cluster in ad_clusters
        }
        next_cluster_id = max(cluster.cluster_id for cluster in ad_clusters) + 1 if ad_clusters else 0
        
        # Process traffic clusters
        for traffic_cluster_id, user_ids in traffic_clusters.items():
            if len(user_ids) < self.min_cluster_size:
                continue
            
            # Check AD group composition of this traffic cluster
            ad_group_counts: Dict[int, int] = Counter()
            for user_id in user_ids:
                if user_id in user_to_ad_cluster:
                    ad_cluster_id = user_to_ad_cluster[user_id]
                    ad_group_counts[ad_cluster_id] += 1
            
            # If most users in this traffic cluster come from the same AD cluster,
            # they're already well-grouped, skip
            if ad_group_counts and max(ad_group_counts.values()) / len(user_ids) > 0.8:
                # 80%+ from same AD cluster, no need to create new cluster
                continue
            
            # Traffic pattern suggests different grouping than AD groups
            # Create a new cluster or merge into existing
            # Get user details for naming
            conn = self.db._get_connection()
            users_query = """
                SELECT 
                    u.user_id,
                    u.department,
                    GROUP_CONCAT(DISTINCT agm.group_name) as ad_groups
                FROM users u
                LEFT JOIN ad_group_memberships agm ON u.user_id = agm.user_id
                WHERE u.user_id IN ({})
                GROUP BY u.user_id, u.department
            """.format(','.join(['?' for _ in user_ids]))
            
            users_data = conn.execute(users_query, user_ids).fetchall()
            
            # Get primary department and AD groups
            departments = [u['department'] for u in users_data if u.get('department')]
            dept_counter = Counter(departments)
            primary_dept = dept_counter.most_common(1)[0][0] if dept_counter else None
            
            ad_groups_list = []
            for u in users_data:
                groups_str = u.get('ad_groups', '')
                if groups_str:
                    ad_groups_list.extend([g.strip() for g in groups_str.split(',') if g.strip()])
            
            # Create cluster name based on traffic similarity
            cluster_name = f"Traffic Pattern Cluster {traffic_cluster_id}"
            if primary_dept:
                cluster_name = f"{primary_dept} (Traffic-Based)"
            
            # Create new cluster
            new_cluster = UserCluster(
                cluster_id=next_cluster_id,
                name=cluster_name,
                user_count=len(user_ids),
                primary_department=primary_dept,
                departments=list(set(departments)),
                ad_groups=list(set(ad_groups_list)),
                user_ids=user_ids,
                confidence=0.7,  # Medium confidence for traffic-based clusters
            )
            
            merged_clusters[next_cluster_id] = new_cluster
            next_cluster_id += 1
            
            logger.info(f"Created traffic-based cluster: {cluster_name} with {len(user_ids)} users")
        
        return list(merged_clusters.values())
    
    def cluster_users(self) -> List[UserCluster]:
        """
        Cluster users using both AD groups and traffic patterns.
        
        Returns:
            List of UserCluster objects
        """
        logger.info("Starting traffic-enhanced user clustering...")
        
        # Step 1: Get AD group-based clusters
        logger.info("Step 1: AD group-based clustering...")
        ad_clusters = self._base_clusterer.cluster_users()
        logger.info(f"Found {len(ad_clusters)} AD group-based clusters")
        
        # Step 2: Extract traffic features
        logger.info("Step 2: Extracting traffic features...")
        traffic_features = self.extract_traffic_features()
        
        if not traffic_features:
            logger.warning("No traffic features available, returning AD clusters only")
            return ad_clusters
        
        # Step 3: Cluster by traffic patterns
        logger.info("Step 3: Traffic pattern clustering...")
        traffic_clusters = self.cluster_by_traffic(traffic_features)
        logger.info(f"Found {len(traffic_clusters)} traffic-based clusters")
        
        # Step 4: Merge clusters
        logger.info("Step 4: Merging AD and traffic clusters...")
        merged_clusters = self.merge_clusters(ad_clusters, traffic_clusters)
        logger.info(f"Final merged clusters: {len(merged_clusters)}")
        
        return merged_clusters
    
    def store_user_clusters(self, clusters: List[UserCluster]) -> None:
        """Store user clusters in the database."""
        self._base_clusterer.store_user_clusters(clusters)


def cluster_users_with_traffic() -> List[UserCluster]:
    """
    Convenience function to cluster users with traffic analysis and store results.
    
    Returns:
        List of UserCluster objects
    """
    clusterer = UserTrafficBasedClusterer()
    clusters = clusterer.cluster_users()
    clusterer.store_user_clusters(clusters)
    return clusters

