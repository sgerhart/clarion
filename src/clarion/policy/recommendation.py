"""
Policy Recommendation Engine.

Generates ISE authorization policy recommendations based on cluster analysis.
Maps clusters to policy conditions (AD groups, device types, etc.) and recommended SGTs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
from collections import Counter
import logging

logger = logging.getLogger(__name__)


@dataclass
class PolicyCondition:
    """
    Represents a condition for an ISE authorization policy.
    
    Examples:
    - AD group membership: {"type": "ad_group", "value": "HR-Users"}
    - Device profile: {"type": "device_profile", "value": "CorporatePhone"}
    - Device type: {"type": "device_type", "value": "server"}
    """
    type: str  # 'ad_group', 'device_profile', 'device_type', 'network_attribute'
    value: str
    operator: str = "EQUALS"  # ISE operators: EQUALS, CONTAINS, MATCHES, etc.
    
    def to_ise_expression(self) -> str:
        """Convert to ISE policy condition expression."""
        # Map condition type to ISE attribute names
        ise_attribute_map = {
            "ad_group": "AD:Groups",
            "device_profile": "Device:Profile",
            "device_type": "Device:Type",
            "network_attribute": "Network:Attribute",
        }
        
        attribute = ise_attribute_map.get(self.type, self.type)
        return f"{attribute} {self.operator} '{self.value}'"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "type": self.type,
            "value": self.value,
            "operator": self.operator,
            "ise_expression": self.to_ise_expression(),
        }


@dataclass
class PolicyRule:
    """
    Represents an ISE authorization policy rule.
    
    Contains conditions and the action (SGT assignment).
    """
    name: str
    conditions: List[PolicyCondition]
    action: str  # e.g., "Assign SGT 12"
    sgt_value: int
    justification: str
    
    def to_ise_condition_string(self) -> str:
        """Generate ISE condition string (OR-separated conditions)."""
        expressions = [cond.to_ise_expression() for cond in self.conditions]
        return " OR ".join(expressions)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "conditions": [cond.to_dict() for cond in self.conditions],
            "action": self.action,
            "sgt_value": self.sgt_value,
            "justification": self.justification,
            "ise_condition_string": self.to_ise_condition_string(),
        }


@dataclass
class PolicyRecommendation:
    """
    Policy recommendation for a cluster or device.
    
    Contains the recommended policy rule and impact analysis.
    """
    # Required fields (no defaults)
    cluster_id: int
    recommended_sgt: int
    policy_rule: PolicyRule
    
    # Optional fields (with defaults)
    id: Optional[int] = None  # Database ID if stored
    recommended_sgt_name: Optional[str] = None
    
    # Impact analysis
    devices_affected: int = 0
    ad_groups_affected: List[str] = field(default_factory=list)
    device_profiles_affected: List[str] = field(default_factory=list)
    device_types_affected: List[str] = field(default_factory=list)
    
    # Status
    status: str = "pending"  # 'pending', 'accepted', 'rejected', 'deployed'
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # For device-specific recommendations (when cluster assignment changes)
    endpoint_id: Optional[str] = None
    old_cluster_id: Optional[int] = None
    old_sgt: Optional[int] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "cluster_id": self.cluster_id,
            "recommended_sgt": self.recommended_sgt,
            "recommended_sgt_name": self.recommended_sgt_name,
            "policy_rule": self.policy_rule.to_dict(),
            "devices_affected": self.devices_affected,
            "ad_groups_affected": self.ad_groups_affected,
            "device_profiles_affected": self.device_profiles_affected,
            "device_types_affected": self.device_types_affected,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "endpoint_id": self.endpoint_id,
            "old_cluster_id": self.old_cluster_id,
            "old_sgt": self.old_sgt,
        }


class PolicyRecommendationEngine:
    """
    Engine for generating ISE policy recommendations from cluster analysis.
    
    Analyzes cluster members to identify common attributes (AD groups, device types, etc.)
    and generates policy rule recommendations.
    """
    
    def __init__(self, db):
        """
        Initialize the recommendation engine.
        
        Args:
            db: ClarionDatabase instance
        """
        self.db = db
    
    def analyze_cluster_attributes(
        self,
        cluster_id: int,
        min_percentage: float = 0.5,
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        Analyze cluster members to identify common attributes.
        
        Returns dictionaries of attribute type -> list of (value, percentage) tuples.
        
        Args:
            cluster_id: Cluster ID to analyze
            min_percentage: Minimum percentage threshold for including attributes
            
        Returns:
            Dictionary with keys: 'ad_groups', 'device_profiles', 'device_types'
            Each value is a list of (attribute_value, percentage) tuples, sorted by frequency.
        """
        conn = self.db._get_connection()
        
        # Get all endpoints in the cluster
        members_cursor = conn.execute("""
            SELECT DISTINCT ca.endpoint_id
            FROM cluster_assignments ca
            WHERE ca.cluster_id = ?
        """, (cluster_id,))
        
        endpoint_ids = [row['endpoint_id'] for row in members_cursor.fetchall()]
        
        if not endpoint_ids:
            return {
                "ad_groups": [],
                "device_profiles": [],
                "device_types": [],
            }
        
        # Get identity data for cluster members
        # Join identity table on MAC address (endpoint_id = mac_address)
        if not endpoint_ids:
            return {
                "ad_groups": [],
                "device_profiles": [],
                "device_types": [],
            }
        
        placeholders = ','.join('?' * len(endpoint_ids))
        
        identity_cursor = conn.execute(f"""
            SELECT DISTINCT
                i.ad_groups,
                i.ise_profile,
                i.device_name,
                ca.endpoint_id
            FROM cluster_assignments ca
            LEFT JOIN identity i ON ca.endpoint_id = i.mac_address
            WHERE ca.cluster_id = ? AND ca.endpoint_id IN ({placeholders})
        """, [cluster_id] + endpoint_ids)
        
        identity_rows = identity_cursor.fetchall()
        
        # Count attributes
        ad_group_counter = Counter()
        device_profile_counter = Counter()
        device_type_counter = Counter()
        total_devices = len(identity_rows)
        
        if total_devices == 0:
            return {
                "ad_groups": [],
                "device_profiles": [],
                "device_types": [],
            }
        
        for row in identity_rows:
            # Count AD groups
            ad_groups_json = row.get('ad_groups')
            if ad_groups_json:
                try:
                    import json
                    ad_groups = json.loads(ad_groups_json) if isinstance(ad_groups_json, str) else ad_groups_json
                    if isinstance(ad_groups, list):
                        for group in ad_groups:
                            ad_group_counter[group] += 1
                except (json.JSONDecodeError, TypeError):
                    pass
            
            # Count ISE profiles
            ise_profile = row.get('ise_profile')
            if ise_profile:
                device_profile_counter[ise_profile] += 1
            
            # Infer device type from device_name
            device_name = row.get('device_name', '').lower() if row.get('device_name') else ''
            if device_name:
                if 'server' in device_name or 'svr' in device_name:
                    device_type_counter['server'] += 1
                elif 'laptop' in device_name:
                    device_type_counter['laptop'] += 1
                elif 'phone' in device_name or 'ip-phone' in device_name:
                    device_type_counter['ip_phone'] += 1
                elif 'printer' in device_name:
                    device_type_counter['printer'] += 1
                elif 'iot' in device_name or 'camera' in device_name:
                    device_type_counter['iot'] += 1
                elif 'mobile' in device_name or 'phone' in device_name:
                    device_type_counter['mobile'] += 1
        
        # Convert to percentages and filter by threshold
        def filter_by_percentage(counter: Counter) -> List[Tuple[str, float]]:
            result = []
            for value, count in counter.most_common():
                percentage = count / total_devices if total_devices > 0 else 0.0
                if percentage >= min_percentage:
                    result.append((value, percentage))
            return result
        
        return {
            "ad_groups": filter_by_percentage(ad_group_counter),
            "device_profiles": filter_by_percentage(device_profile_counter),
            "device_types": filter_by_percentage(device_type_counter),
        }
    
    def generate_policy_conditions(
        self,
        attributes: Dict[str, List[Tuple[str, float]]],
        max_conditions: int = 5,
    ) -> List[PolicyCondition]:
        """
        Generate policy conditions from cluster attributes.
        
        Args:
            attributes: Dictionary from analyze_cluster_attributes()
            max_conditions: Maximum number of conditions to include
            
        Returns:
            List of PolicyCondition objects
        """
        conditions = []
        
        # Prioritize: AD groups > Device profiles > Device types
        priority_order = [
            ("ad_groups", "ad_group"),
            ("device_profiles", "device_profile"),
            ("device_types", "device_type"),
        ]
        
        for attr_key, condition_type in priority_order:
            if len(conditions) >= max_conditions:
                break
            
            attr_list = attributes.get(attr_key, [])
            for value, percentage in attr_list[:max_conditions - len(conditions)]:
                conditions.append(PolicyCondition(
                    type=condition_type,
                    value=value,
                    operator="EQUALS",
                ))
        
        return conditions
    
    def generate_cluster_recommendation(
        self,
        cluster_id: int,
        min_percentage: float = 0.5,
    ) -> Optional[PolicyRecommendation]:
        """
        Generate policy recommendation for a cluster.
        
        Args:
            cluster_id: Cluster ID
            min_percentage: Minimum percentage threshold for attributes
            
        Returns:
            PolicyRecommendation object, or None if cluster has no recommended SGT
        """
        conn = self.db._get_connection()
        
        # Get cluster info and recommended SGT
        cluster_cursor = conn.execute("""
            SELECT 
                c.cluster_id,
                c.cluster_label,
                COALESCE(
                    (SELECT sm.sgt_value
                     FROM cluster_assignments ca2
                     JOIN sgt_membership sm ON ca2.endpoint_id = sm.endpoint_id
                     WHERE ca2.cluster_id = c.cluster_id
                     GROUP BY sm.sgt_value
                     ORDER BY COUNT(*) DESC
                     LIMIT 1),
                    NULL
                ) as recommended_sgt,
                (SELECT sr.sgt_name
                 FROM cluster_assignments ca2
                 JOIN sgt_membership sm ON ca2.endpoint_id = sm.endpoint_id
                 LEFT JOIN sgt_registry sr ON sm.sgt_value = sr.sgt_value
                 WHERE ca2.cluster_id = c.cluster_id
                 GROUP BY sm.sgt_value, sr.sgt_name
                 ORDER BY COUNT(*) DESC
                 LIMIT 1) as recommended_sgt_name,
                COUNT(DISTINCT ca.endpoint_id) as endpoint_count
            FROM clusters c
            LEFT JOIN cluster_assignments ca ON c.cluster_id = ca.cluster_id
            WHERE c.cluster_id = ?
            GROUP BY c.cluster_id
        """, (cluster_id,))
        
        cluster_row = cluster_cursor.fetchone()
        if not cluster_row:
            return None
        
        recommended_sgt = cluster_row.get('recommended_sgt')
        if not recommended_sgt:
            # No SGT assigned to this cluster yet
            logger.warning(f"Cluster {cluster_id} has no recommended SGT, cannot generate policy recommendation")
            return None
        
        cluster_label = cluster_row.get('cluster_label', f"Cluster {cluster_id}")
        recommended_sgt_name = cluster_row.get('recommended_sgt_name') or f"SGT-{recommended_sgt}"
        endpoint_count = cluster_row.get('endpoint_count', 0)
        
        # Analyze cluster attributes
        attributes = self.analyze_cluster_attributes(cluster_id, min_percentage)
        
        # Generate policy conditions
        conditions = self.generate_policy_conditions(attributes)
        
        if not conditions:
            # No identifiable attributes, use cluster-based condition
            conditions = [PolicyCondition(
                type="cluster_id",
                value=str(cluster_id),
                operator="EQUALS",
            )]
            justification = f"Cluster '{cluster_label}' contains {endpoint_count} devices. Recommended SGT {recommended_sgt} based on behavioral clustering."
        else:
            # Build justification from top attributes
            top_attrs = []
            if attributes.get('ad_groups'):
                top_attrs.append(f"{attributes['ad_groups'][0][0]} AD group")
            if attributes.get('device_profiles'):
                top_attrs.append(f"{attributes['device_profiles'][0][0]} device profile")
            if attributes.get('device_types'):
                top_attrs.append(f"{attributes['device_types'][0][0]} devices")
            
            justification = f"Cluster '{cluster_label}' ({endpoint_count} devices) shares common attributes: {', '.join(top_attrs[:3])}. Recommended SGT {recommended_sgt} ({recommended_sgt_name})."
        
        # Generate policy rule
        policy_rule = PolicyRule(
            name=f"Assign-SGT-{recommended_sgt}-{cluster_label.replace(' ', '-')}",
            conditions=conditions,
            action=f"Assign SGT {recommended_sgt}",
            sgt_value=recommended_sgt,
            justification=justification,
        )
        
        # Build impact analysis
        ad_groups_affected = [attr[0] for attr in attributes.get('ad_groups', [])]
        device_profiles_affected = [attr[0] for attr in attributes.get('device_profiles', [])]
        device_types_affected = [attr[0] for attr in attributes.get('device_types', [])]
        
        return PolicyRecommendation(
            cluster_id=cluster_id,
            recommended_sgt=recommended_sgt,
            recommended_sgt_name=recommended_sgt_name,
            policy_rule=policy_rule,
            devices_affected=endpoint_count,
            ad_groups_affected=ad_groups_affected,
            device_profiles_affected=device_profiles_affected,
            device_types_affected=device_types_affected,
            status="pending",
            created_at=datetime.utcnow(),
        )
    
    def generate_device_recommendation(
        self,
        endpoint_id: str,
        new_cluster_id: int,
        old_cluster_id: Optional[int] = None,
    ) -> Optional[PolicyRecommendation]:
        """
        Generate policy recommendation when a device is moved to a new cluster.
        
        Args:
            endpoint_id: Endpoint ID (MAC address)
            new_cluster_id: New cluster ID
            old_cluster_id: Previous cluster ID (if known)
            
        Returns:
            PolicyRecommendation object
        """
        # Get old SGT if available
        old_sgt = None
        if old_cluster_id:
            conn = self.db._get_connection()
            old_sgt_cursor = conn.execute("""
                SELECT sm.sgt_value
                FROM cluster_assignments ca
                JOIN sgt_membership sm ON ca.endpoint_id = sm.endpoint_id
                WHERE ca.cluster_id = ?
                GROUP BY sm.sgt_value
                ORDER BY COUNT(*) DESC
                LIMIT 1
            """, (old_cluster_id,))
            old_sgt_row = old_sgt_cursor.fetchone()
            if old_sgt_row:
                old_sgt = old_sgt_row.get('sgt_value')
        
        # Generate cluster-based recommendation
        recommendation = self.generate_cluster_recommendation(new_cluster_id)
        if not recommendation:
            return None
        
        # Add device-specific context
        recommendation.endpoint_id = endpoint_id
        recommendation.old_cluster_id = old_cluster_id
        recommendation.old_sgt = old_sgt
        
        # Update policy rule name and justification
        recommendation.policy_rule.name = f"Move-Device-{endpoint_id[:8]}-To-SGT-{recommendation.recommended_sgt}"
        recommendation.policy_rule.justification = (
            f"Device {endpoint_id} moved to cluster {new_cluster_id}. "
            f"Recommended policy to assign SGT {recommendation.recommended_sgt} ({recommendation.recommended_sgt_name})."
        )
        
        return recommendation

