"""
User Clustering Module

Clusters users based on AD groups, departments, and device usage patterns.
This enables user-based SGT recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import logging
from collections import Counter, defaultdict

from clarion.storage import get_database

logger = logging.getLogger(__name__)


@dataclass
class UserCluster:
    """A cluster of users."""
    cluster_id: int
    name: str
    user_count: int
    primary_department: Optional[str] = None
    primary_ad_group: Optional[str] = None
    departments: List[str] = field(default_factory=list)
    ad_groups: List[str] = field(default_factory=list)
    user_ids: List[str] = field(default_factory=list)
    confidence: float = 0.0


class UserClusterer:
    """
    Cluster users based on AD groups and departments.
    
    This creates user-based clusters that can be used for User SGT recommendations.
    Users are grouped by:
    1. Primary AD group (most specific, non-generic group)
    2. Department
    3. Common device clusters they use
    
    Example:
        >>> clusterer = UserClusterer()
        >>> clusters = clusterer.cluster_users()
        >>> for cluster in clusters:
        ...     print(f"{cluster.name}: {cluster.user_count} users")
    """
    
    def __init__(
        self,
        min_cluster_size: int = 5,
        group_threshold: float = 0.3,
    ):
        """
        Initialize the user clusterer.
        
        Args:
            min_cluster_size: Minimum users to form a cluster
            group_threshold: Minimum ratio for AD group to be significant
        """
        self.min_cluster_size = min_cluster_size
        self.group_threshold = group_threshold
        self.db = get_database()
    
    def cluster_users(self) -> List[UserCluster]:
        """
        Cluster users based on AD groups and departments.
        
        Returns:
            List of UserCluster objects
        """
        logger.info("Clustering users by AD groups and departments...")
        
        # Get all users with their AD groups and departments
        conn = self.db._get_connection()
        
        # Get users with their primary AD group and department
        users_query = """
            SELECT 
                u.user_id,
                u.username,
                u.department,
                u.display_name,
                GROUP_CONCAT(DISTINCT agm.group_name) as ad_groups,
                GROUP_CONCAT(DISTINCT agm.group_id) as group_ids
            FROM users u
            LEFT JOIN ad_group_memberships agm ON u.user_id = agm.user_id
            WHERE u.is_active = 1
            GROUP BY u.user_id, u.username, u.department, u.display_name
        """
        users = conn.execute(users_query).fetchall()
        
        logger.info(f"Found {len(users)} active users to cluster")
        
        # Group users by primary AD group (most specific, non-generic)
        group_clusters: Dict[str, List[Dict]] = defaultdict(list)
        department_clusters: Dict[str, List[Dict]] = defaultdict(list)
        
        for user in users:
            user_dict = dict(user)
            ad_groups_str = user_dict.get('ad_groups', '')
            ad_groups = [g.strip() for g in ad_groups_str.split(',') if g.strip()] if ad_groups_str else []
            
            # Filter out generic groups
            specific_groups = [
                g for g in ad_groups
                if g.lower() not in ('all-employees', 'domain-users', 'everyone')
            ]
            
            # Use primary AD group if available
            if specific_groups:
                primary_group = specific_groups[0]  # Use first specific group
                group_clusters[primary_group].append(user_dict)
            elif user_dict.get('department'):
                # Fall back to department if no specific AD groups
                department_clusters[user_dict['department']].append(user_dict)
            else:
                # No grouping info - put in "Unassigned" cluster
                group_clusters['Unassigned'].append(user_dict)
        
        # Create clusters from AD groups
        clusters: List[UserCluster] = []
        cluster_id = 0
        
        # Process AD group clusters
        for group_name, user_list in group_clusters.items():
            if len(user_list) >= self.min_cluster_size:
                # Get departments for this cluster
                departments = [u.get('department') for u in user_list if u.get('department')]
                dept_counter = Counter(departments)
                primary_dept = dept_counter.most_common(1)[0][0] if dept_counter else None
                
                cluster = UserCluster(
                    cluster_id=cluster_id,
                    name=self._group_to_cluster_name(group_name),
                    user_count=len(user_list),
                    primary_ad_group=group_name,
                    primary_department=primary_dept,
                    departments=list(set(departments)),
                    ad_groups=[group_name],
                    user_ids=[u['user_id'] for u in user_list],
                    confidence=min(1.0, len(user_list) / 100.0),  # Higher confidence for larger clusters
                )
                clusters.append(cluster)
                cluster_id += 1
        
        # Process department clusters (for users without specific AD groups)
        for dept_name, user_list in department_clusters.items():
            if len(user_list) >= self.min_cluster_size:
                # Check if these users are already in an AD group cluster
                existing_user_ids = set()
                for cluster in clusters:
                    existing_user_ids.update(cluster.user_ids)
                
                # Only add users not already clustered
                new_users = [u for u in user_list if u['user_id'] not in existing_user_ids]
                if len(new_users) >= self.min_cluster_size:
                    cluster = UserCluster(
                        cluster_id=cluster_id,
                        name=f"{dept_name} Department",
                        user_count=len(new_users),
                        primary_department=dept_name,
                        departments=[dept_name],
                        user_ids=[u['user_id'] for u in new_users],
                        confidence=min(1.0, len(new_users) / 100.0),
                    )
                    clusters.append(cluster)
                    cluster_id += 1
        
        logger.info(f"Created {len(clusters)} user clusters")
        return clusters
    
    def _group_to_cluster_name(self, group_name: str) -> str:
        """Convert AD group name to cluster name."""
        # Remove common suffixes
        clean = group_name.replace("-Users", "").replace("_Users", "")
        clean = clean.replace("-users", "").replace("_users", "")
        
        # Special cases
        if "privileged" in clean.lower() or "admin" in clean.lower():
            return "Privileged Admins"
        if "it" in clean.lower() and len(clean) < 5:
            return "IT Staff"
        
        return f"{clean} Users"
    
    def store_user_clusters(self, clusters: List[UserCluster]) -> None:
        """
        Store user clusters in the database.
        
        Args:
            clusters: List of UserCluster objects to store
        """
        conn = self.db._get_connection()
        
        # Create user_clusters table if it doesn't exist
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_clusters (
                cluster_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                user_count INTEGER NOT NULL,
                primary_department TEXT,
                primary_ad_group TEXT,
                departments TEXT,  -- JSON array
                ad_groups TEXT,     -- JSON array
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create user_cluster_assignments table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_cluster_assignments (
                assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                cluster_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (cluster_id) REFERENCES user_clusters(cluster_id),
                UNIQUE(user_id, cluster_id)
            )
        """)
        
        import json
        
        # Store clusters
        for cluster in clusters:
            conn.execute("""
                INSERT OR REPLACE INTO user_clusters
                (cluster_id, name, user_count, primary_department, primary_ad_group,
                 departments, ad_groups, confidence, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                cluster.cluster_id,
                cluster.name,
                cluster.user_count,
                cluster.primary_department,
                cluster.primary_ad_group,
                json.dumps(cluster.departments),
                json.dumps(cluster.ad_groups),
                cluster.confidence,
            ))
            
            # Store user assignments
            for user_id in cluster.user_ids:
                conn.execute("""
                    INSERT OR REPLACE INTO user_cluster_assignments
                    (user_id, cluster_id)
                    VALUES (?, ?)
                """, (user_id, cluster.cluster_id))
        
        conn.commit()
        logger.info(f"Stored {len(clusters)} user clusters in database")


def cluster_users() -> List[UserCluster]:
    """
    Convenience function to cluster users and store results.
    
    Returns:
        List of UserCluster objects
    """
    clusterer = UserClusterer()
    clusters = clusterer.cluster_users()
    clusterer.store_user_clusters(clusters)
    return clusters

