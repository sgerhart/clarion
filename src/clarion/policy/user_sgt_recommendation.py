"""
User SGT Recommendation Engine.

Generates user SGT recommendations by comparing AD group assignments (baseline)
with actual traffic patterns. This enables security-focused recommendations
that suggest SGT assignments based on actual network access patterns rather
than just organizational structure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
from collections import Counter, defaultdict
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class UserSGTRecommendation:
    """
    SGT recommendation for a user or user cluster.
    
    Compares AD group-based expectation vs actual traffic pattern.
    """
    user_id: Optional[str] = None  # None for cluster-level recommendations
    user_cluster_id: Optional[int] = None
    recommended_sgt: int = 0
    recommended_sgt_name: Optional[str] = None
    
    # Baseline (AD group based)
    ad_group_based_sgt: Optional[int] = None
    ad_group_based_sgt_name: Optional[str] = None
    primary_ad_groups: List[str] = field(default_factory=list)
    
    # Traffic-based analysis
    traffic_suggested_sgt: Optional[int] = None
    traffic_suggested_sgt_name: Optional[str] = None
    traffic_pattern_summary: Optional[Dict] = None
    
    # Recommendation metadata
    recommendation_type: str = "traffic_aligned"  # 'traffic_aligned', 'traffic_diverges', 'security_concern'
    confidence: float = 0.0
    justification: str = ""
    
    # Impact
    users_affected: int = 1  # For cluster-level recommendations
    security_concerns: List[str] = field(default_factory=list)
    
    # Status
    id: Optional[int] = None  # Database ID if stored
    status: str = "pending"  # 'pending', 'accepted', 'rejected', 'deployed'
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_cluster_id": self.user_cluster_id,
            "recommended_sgt": self.recommended_sgt,
            "recommended_sgt_name": self.recommended_sgt_name,
            "ad_group_based_sgt": self.ad_group_based_sgt,
            "ad_group_based_sgt_name": self.ad_group_based_sgt_name,
            "primary_ad_groups": self.primary_ad_groups,
            "traffic_suggested_sgt": self.traffic_suggested_sgt,
            "traffic_suggested_sgt_name": self.traffic_suggested_sgt_name,
            "traffic_pattern_summary": self.traffic_pattern_summary,
            "recommendation_type": self.recommendation_type,
            "confidence": self.confidence,
            "justification": self.justification,
            "users_affected": self.users_affected,
            "security_concerns": self.security_concerns,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserSGTRecommendationEngine:
    """
    Engine for generating user SGT recommendations.
    
    Strategy:
    1. Lead with AD groups (baseline organizational structure)
    2. Compare with traffic patterns to identify discrepancies
    3. Suggest more secure SGT assignments when traffic diverges from AD groups
    4. Identify security concerns (users accessing resources outside their scope)
    """
    
    def __init__(self, db):
        """
        Initialize the user SGT recommendation engine.
        
        Args:
            db: ClarionDatabase instance
        """
        self.db = db
    
    def get_user_traffic_pattern(self, user_id: str) -> Optional[Dict]:
        """Get traffic pattern for a user."""
        conn = self.db._get_connection()
        cursor = conn.execute("""
            SELECT * FROM user_traffic_patterns WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        if row:
            result = dict(row)
            # Parse JSON fields
            if result.get('top_ports'):
                try:
                    result['top_ports'] = json.loads(result['top_ports'])
                except (json.JSONDecodeError, TypeError):
                    result['top_ports'] = []
            if result.get('top_protocols'):
                try:
                    result['top_protocols'] = json.loads(result['top_protocols'])
                except (json.JSONDecodeError, TypeError):
                    result['top_protocols'] = []
            return result
        return None
    
    def get_user_ad_groups(self, user_id: str) -> List[str]:
        """Get AD groups for a user."""
        ad_groups = self.db.get_user_groups(user_id)
        return [g['group_name'] for g in ad_groups if g.get('group_name')]
    
    def analyze_user_traffic_access(self, user_id: str) -> Dict:
        """
        Analyze what resources a user accesses based on traffic patterns.
        
        Returns summary of access patterns for security analysis.
        """
        traffic = self.get_user_traffic_pattern(user_id)
        if not traffic:
            return {
                "has_traffic": False,
                "total_flows": 0,
                "unique_peers": 0,
                "top_ports": [],
                "access_scope": "unknown",
            }
        
        # Analyze port access (identify services/resources)
        top_ports = traffic.get('top_ports', [])
        unique_peers = traffic.get('unique_peers', 0)
        total_flows = traffic.get('total_flows', 0)
        
        # Common service ports
        service_ports = {
            80: "HTTP",
            443: "HTTPS",
            22: "SSH",
            3389: "RDP",
            3306: "MySQL",
            5432: "PostgreSQL",
            1433: "MSSQL",
            445: "SMB",
            135: "RPC",
            5985: "WinRM-HTTP",
            5986: "WinRM-HTTPS",
        }
        
        accessed_services = []
        for port_entry in top_ports[:10]:  # Top 10 ports
            if isinstance(port_entry, dict):
                port = port_entry.get('port')
                if port in service_ports:
                    accessed_services.append(service_ports[port])
        
        # Determine access scope
        access_scope = "limited"
        if unique_peers > 100:
            access_scope = "broad"
        elif unique_peers > 20:
            access_scope = "moderate"
        
        return {
            "has_traffic": True,
            "total_flows": total_flows,
            "unique_peers": unique_peers,
            "top_ports": [p.get('port') if isinstance(p, dict) else p for p in top_ports[:10]],
            "accessed_services": accessed_services,
            "access_scope": access_scope,
            "total_bytes": (traffic.get('total_bytes_in', 0) or 0) + (traffic.get('total_bytes_out', 0) or 0),
        }
    
    def map_ad_groups_to_sgt(self, ad_groups: List[str]) -> Optional[Tuple[int, str]]:
        """
        Map AD groups to expected SGT (baseline assignment).
        
        This would ideally come from ISE policy mappings or configuration.
        For now, we use a simple heuristic based on group names.
        """
        # This is a placeholder - in production, this would query ISE or config
        # For now, we'll look for existing SGT assignments for similar users
        
        if not ad_groups:
            return None
        
        conn = self.db._get_connection()
        
        # Find users with similar AD groups who already have SGT assignments
        # Use the most common SGT assignment for users with overlapping AD groups
        placeholders = ','.join(['?' for _ in ad_groups])
        query = f"""
            SELECT usm.sgt_value, sr.sgt_name, COUNT(*) as count
            FROM user_sgt_membership usm
            JOIN sgt_registry sr ON usm.sgt_value = sr.sgt_value
            JOIN ad_group_memberships agm ON usm.user_id = agm.user_id
            WHERE agm.group_name IN ({placeholders})
            GROUP BY usm.sgt_value, sr.sgt_name
            ORDER BY count DESC
            LIMIT 1
        """
        
        cursor = conn.execute(query, ad_groups)
        row = cursor.fetchone()
        if row:
            return (row['sgt_value'], row['sgt_name'])
        
        return None
    
    def suggest_sgt_from_traffic(self, user_id: str, user_cluster_id: Optional[int] = None) -> Optional[Tuple[int, str]]:
        """
        Suggest SGT based on traffic patterns.
        
        Uses user cluster to find similar users and their SGT assignments.
        """
        # If user is in a traffic-based cluster, use cluster's SGT
        if user_cluster_id:
            conn = self.db._get_connection()
            
            # Find other users in the same cluster who have SGT assignments
            cursor = conn.execute("""
                SELECT usm.sgt_value, sr.sgt_name, COUNT(*) as count
                FROM user_cluster_assignments uca
                JOIN user_sgt_membership usm ON uca.user_id = usm.user_id
                JOIN sgt_registry sr ON usm.sgt_value = sr.sgt_value
                WHERE uca.user_cluster_id = ? AND uca.user_id != ?
                GROUP BY usm.sgt_value, sr.sgt_name
                ORDER BY count DESC
                LIMIT 1
            """, (user_cluster_id, user_id))
            
            row = cursor.fetchone()
            if row:
                return (row['sgt_value'], row['sgt_name'])
        
        return None
    
    def generate_user_recommendation(
        self,
        user_id: str,
        user_cluster_id: Optional[int] = None,
    ) -> Optional[UserSGTRecommendation]:
        """
        Generate SGT recommendation for a single user.
        
        Compares AD group-based expectation with traffic patterns.
        """
        # Get user's AD groups
        ad_groups = self.get_user_ad_groups(user_id)
        
        # Get AD group-based SGT (baseline)
        ad_sgt = self.map_ad_groups_to_sgt(ad_groups)
        
        # Get traffic-based SGT suggestion
        traffic_sgt = self.suggest_sgt_from_traffic(user_id, user_cluster_id)
        
        # Analyze traffic access patterns
        traffic_analysis = self.analyze_user_traffic_access(user_id)
        
        # Determine recommendation
        recommended_sgt = ad_sgt[0] if ad_sgt else None
        recommended_sgt_name = ad_sgt[1] if ad_sgt else None
        recommendation_type = "traffic_aligned"
        security_concerns = []
        justification = ""
        
        if traffic_sgt and ad_sgt:
            # Compare AD-based vs traffic-based
            if traffic_sgt[0] != ad_sgt[0]:
                # Traffic suggests different SGT
                recommendation_type = "traffic_diverges"
                recommended_sgt = traffic_sgt[0]
                recommended_sgt_name = traffic_sgt[1]
                justification = (
                    f"Traffic patterns suggest SGT {traffic_sgt[0]} ({traffic_sgt[1]}), "
                    f"but AD groups suggest SGT {ad_sgt[0]} ({ad_sgt[1]}). "
                    f"Traffic analysis shows {traffic_analysis['access_scope']} access scope "
                    f"({traffic_analysis['unique_peers']} unique peers)."
                )
            else:
                # Traffic aligns with AD groups
                justification = (
                    f"Traffic patterns align with AD group assignment. "
                    f"User accesses {traffic_analysis['unique_peers']} unique peers, "
                    f"suggesting {traffic_analysis['access_scope']} access scope."
                )
        elif traffic_sgt:
            # Only traffic-based suggestion available
            recommended_sgt = traffic_sgt[0]
            recommended_sgt_name = traffic_sgt[1]
            recommendation_type = "traffic_suggested"
            justification = (
                f"Traffic-based clustering suggests SGT {traffic_sgt[0]} ({traffic_sgt[1]}). "
                f"User shows {traffic_analysis['access_scope']} access patterns."
            )
        elif ad_sgt:
            # Only AD-based available (no traffic data)
            justification = f"AD group-based assignment: SGT {ad_sgt[0]} ({ad_sgt[1]}). No traffic data available."
        else:
            # No basis for recommendation
            logger.warning(f"No basis for SGT recommendation for user {user_id}")
            return None
        
        # Check for security concerns
        if traffic_analysis.get('has_traffic'):
            # Check for unusual access patterns
            if traffic_analysis['unique_peers'] > 200:
                security_concerns.append(f"Very broad access: {traffic_analysis['unique_peers']} unique peers")
            
            # Check for administrative/service ports
            admin_ports = {22, 3389, 3306, 5432, 1433, 5985, 5986}
            accessed_admin_ports = [
                p for p in traffic_analysis['top_ports']
                if isinstance(p, int) and p in admin_ports
            ]
            if accessed_admin_ports and not any('admin' in g.lower() or 'privileged' in g.lower() for g in ad_groups):
                security_concerns.append(f"Accesses administrative ports: {accessed_admin_ports}")
        
        # Calculate confidence
        confidence = 0.5  # Base confidence
        if ad_sgt and traffic_sgt and ad_sgt[0] == traffic_sgt[0]:
            confidence = 0.9  # High confidence when both agree
        elif traffic_sgt:
            confidence = 0.7  # Medium-high for traffic-based
        elif ad_sgt:
            confidence = 0.6  # Medium for AD-based only
        
        if security_concerns:
            recommendation_type = "security_concern"
            confidence = min(confidence, 0.8)  # Lower confidence when security concerns exist
        
        recommendation = UserSGTRecommendation(
            user_id=user_id,
            user_cluster_id=user_cluster_id,
            recommended_sgt=recommended_sgt,
            recommended_sgt_name=recommended_sgt_name,
            ad_group_based_sgt=ad_sgt[0] if ad_sgt else None,
            ad_group_based_sgt_name=ad_sgt[1] if ad_sgt else None,
            primary_ad_groups=ad_groups[:5],  # Top 5 AD groups
            traffic_suggested_sgt=traffic_sgt[0] if traffic_sgt else None,
            traffic_suggested_sgt_name=traffic_sgt[1] if traffic_sgt else None,
            traffic_pattern_summary=traffic_analysis,
            recommendation_type=recommendation_type,
            confidence=confidence,
            justification=justification,
            security_concerns=security_concerns,
            created_at=datetime.utcnow(),
        )
        
        return recommendation
    
    def generate_cluster_recommendation(
        self,
        user_cluster_id: int,
    ) -> Optional[UserSGTRecommendation]:
        """
        Generate SGT recommendation for a user cluster.
        
        Analyzes all users in the cluster and recommends a common SGT.
        """
        conn = self.db._get_connection()
        
        # Get users in cluster
        cursor = conn.execute("""
            SELECT user_id FROM user_cluster_assignments WHERE user_cluster_id = ?
        """, (user_cluster_id,))
        user_ids = [row['user_id'] for row in cursor.fetchall()]
        
        if not user_ids:
            return None
        
        # Get cluster info
        cluster_cursor = conn.execute("""
            SELECT name, primary_ad_group, primary_department
            FROM user_clusters WHERE cluster_id = ?
        """, (user_cluster_id,))
        cluster_row = cluster_cursor.fetchone()
        cluster_name = cluster_row['name'] if cluster_row else f"Cluster {user_cluster_id}"
        
        # Generate recommendations for each user
        user_recommendations = []
        for user_id in user_ids:
            rec = self.generate_user_recommendation(user_id, user_cluster_id)
            if rec:
                user_recommendations.append(rec)
        
        if not user_recommendations:
            return None
        
        # Find most common recommended SGT
        sgt_counter = Counter(rec.recommended_sgt for rec in user_recommendations if rec.recommended_sgt)
        if not sgt_counter:
            return None
        
        most_common_sgt = sgt_counter.most_common(1)[0][0]
        sgt_count = sgt_counter[most_common_sgt]
        
        # Get SGT name
        sgt_cursor = conn.execute("""
            SELECT sgt_name FROM sgt_registry WHERE sgt_value = ?
        """, (most_common_sgt,))
        sgt_row = sgt_cursor.fetchone()
        sgt_name = sgt_row['sgt_name'] if sgt_row else None
        
        # Aggregate AD groups
        all_ad_groups = []
        for rec in user_recommendations:
            all_ad_groups.extend(rec.primary_ad_groups)
        ad_group_counter = Counter(all_ad_groups)
        primary_ad_groups = [g for g, _ in ad_group_counter.most_common(5)]
        
        # Aggregate security concerns
        all_concerns = []
        for rec in user_recommendations:
            all_concerns.extend(rec.security_concerns)
        security_concerns = list(set(all_concerns))  # Unique concerns
        
        # Determine recommendation type
        recommendation_type = "traffic_aligned"
        if security_concerns:
            recommendation_type = "security_concern"
        elif any(rec.recommendation_type == "traffic_diverges" for rec in user_recommendations):
            recommendation_type = "traffic_diverges"
        
        # Calculate confidence (average of user recommendations)
        avg_confidence = sum(rec.confidence for rec in user_recommendations) / len(user_recommendations)
        
        justification = (
            f"Cluster-level recommendation for {cluster_name}. "
            f"{sgt_count} of {len(user_recommendations)} users recommend SGT {most_common_sgt}. "
            f"Primary AD groups: {', '.join(primary_ad_groups[:3])}"
        )
        
        recommendation = UserSGTRecommendation(
            user_cluster_id=user_cluster_id,
            recommended_sgt=most_common_sgt,
            recommended_sgt_name=sgt_name,
            primary_ad_groups=primary_ad_groups,
            recommendation_type=recommendation_type,
            confidence=avg_confidence,
            justification=justification,
            users_affected=len(user_ids),
            security_concerns=security_concerns,
            created_at=datetime.utcnow(),
        )
        
        return recommendation


def generate_user_sgt_recommendation(
    db,
    user_id: Optional[str] = None,
    user_cluster_id: Optional[int] = None,
) -> Optional[UserSGTRecommendation]:
    """
    Convenience function to generate user SGT recommendation.
    
    Args:
        db: ClarionDatabase instance
        user_id: User ID (for user-specific recommendation)
        user_cluster_id: User cluster ID (for cluster-level recommendation)
    
    Returns:
        UserSGTRecommendation object
    """
    engine = UserSGTRecommendationEngine(db)
    
    if user_id:
        return engine.generate_user_recommendation(user_id, user_cluster_id)
    elif user_cluster_id:
        return engine.generate_cluster_recommendation(user_cluster_id)
    else:
        raise ValueError("Must provide either user_id or user_cluster_id")

