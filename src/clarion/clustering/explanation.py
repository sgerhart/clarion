"""
Cluster Explanation Generator

Generates human-readable explanations for why devices are grouped together.
This provides explainability for the clustering decisions.
"""

from typing import List, Dict, Optional
from clarion.clustering.labeling import ClusterLabel


def generate_cluster_explanation(label: ClusterLabel) -> str:
    """
    Generate a detailed explanation of why devices are grouped together (or why not).
    
    For regular clusters: explains why devices are grouped
    For noise cluster (-1): explains why devices are NOT grouped
    
    This explanation helps users understand:
    - Why these devices share the same SGT (will have same SGACL applied)
    - What characteristics they have in common
    - The confidence level of the grouping
    
    Args:
        label: ClusterLabel with all the cluster metadata
        
    Returns:
        Human-readable explanation text
    """
    lines = []
    
    # Special handling for noise/unclustered devices
    if label.cluster_id == -1:
        return generate_noise_explanation(label)
    
    # Primary reason (already computed)
    lines.append(f"**Primary Reason:** {label.primary_reason}")
    lines.append("")
    
    # Why they're grouped together (SGACL context)
    lines.append("**Why These Devices Are Grouped:**")
    lines.append(
        "These devices are grouped together because they share similar characteristics "
        "and will have the same Security Group Access Control List (SGACL) policies applied. "
        "This ensures consistent network access controls for devices with similar roles and behaviors."
    )
    lines.append("")
    
    # Supporting evidence
    lines.append("**Supporting Evidence:**")
    
    # AD Groups
    if label.top_ad_groups:
        lines.append(f"- **AD Group Membership:** {len(label.top_ad_groups)} distinct groups found")
        for group, ratio in label.top_ad_groups[:3]:
            lines.append(f"  - {group}: {ratio*100:.0f}% of devices")
    
    # ISE Profiles
    if label.top_ise_profiles:
        lines.append(f"- **ISE Profiles:** {len(label.top_ise_profiles)} distinct profiles found")
        for profile, ratio in label.top_ise_profiles[:3]:
            lines.append(f"  - {profile}: {ratio*100:.0f}% of devices")
    
    # Device Types
    if label.top_device_types:
        lines.append(f"- **Device Types:** {len(label.top_device_types)} distinct types found")
        for dtype, ratio in label.top_device_types[:3]:
            lines.append(f"  - {dtype}: {ratio*100:.0f}% of devices")
    
    # Behavioral patterns
    lines.append("- **Behavioral Patterns:**")
    if label.is_server_cluster:
        lines.append("  - Server-like behavior (receives more traffic than it sends)")
        lines.append(f"  - Average in/out ratio: {label.avg_in_out_ratio:.2f} (higher = more server-like)")
    else:
        if label.avg_in_out_ratio < 0.3:
            lines.append("  - Client-like behavior (sends more traffic than it receives)")
        else:
            lines.append("  - Balanced communication pattern")
        lines.append(f"  - Average in/out ratio: {label.avg_in_out_ratio:.2f}")
    
    lines.append(f"  - Average peer diversity: {label.avg_peer_diversity:.2f}")
    
    lines.append("")
    
    # Confidence and member count
    lines.append(f"**Group Statistics:**")
    lines.append(f"- Total devices in group: {label.member_count}")
    lines.append(f"- Confidence level: {label.confidence*100:.0f}%")
    
    if label.confidence >= 0.7:
        confidence_desc = "High - Strong evidence for this grouping"
    elif label.confidence >= 0.5:
        confidence_desc = "Medium - Good evidence for this grouping"
    else:
        confidence_desc = "Low - Limited evidence, may need review"
    
    lines.append(f"- Confidence assessment: {confidence_desc}")
    lines.append("")
    
    # SGACL policy context
    lines.append("**Policy Implications:**")
    lines.append(
        f"All {label.member_count} devices in this group will share the same SGT ({label.cluster_id if label.cluster_id >= 0 else 'Unassigned'}) "
        "and will have identical SGACL policies applied. This means they will have the same "
        "network access permissions based on their common characteristics and behaviors."
    )
    
    return "\n".join(lines)


def generate_noise_explanation(label: ClusterLabel) -> str:
    """
    Generate explanation for noise/unclustered devices (cluster -1).
    
    Explains why these devices are NOT grouped with others.
    
    Args:
        label: ClusterLabel for the noise cluster
        
    Returns:
        Human-readable explanation text
    """
    lines = []
    
    lines.append("**Why These Devices Are NOT Grouped:**")
    lines.append("")
    lines.append(
        "These devices did not fit into any of the identified clusters because they exhibit "
        "unique or outlier behavioral patterns that differ significantly from other devices in the network."
    )
    lines.append("")
    
    # Analyze why they're outliers
    reasons = []
    
    # Check for high diversity (talk to many different places)
    if label.avg_peer_diversity > 50:
        reasons.append(
            f"- **High Peer Diversity ({label.avg_peer_diversity:.1f}):** These devices communicate with "
            f"many different endpoints, making their behavior pattern unique and difficult to categorize."
        )
    
    # Check for unusual traffic patterns
    if label.avg_in_out_ratio < 0.2:
        reasons.append(
            f"- **Unusual Traffic Pattern:** These devices primarily send traffic (client-like) but don't "
            f"match the patterns of typical client devices in the network."
        )
    elif label.avg_in_out_ratio > 0.8:
        reasons.append(
            f"- **Unusual Traffic Pattern:** These devices primarily receive traffic (server-like) but "
            f"don't match the patterns of typical servers in the network."
        )
    
    # Check for low activity
    if label.member_count > 0:
        # Estimate activity (we don't have this directly, but can infer)
        if label.avg_peer_diversity < 5:
            reasons.append(
                f"- **Low Activity:** These devices have very limited network activity ({label.avg_peer_diversity:.1f} peers), "
                f"making it difficult to determine their role or group them with similar devices."
            )
    
    # Check for mixed device types
    if label.top_device_types:
        if len(label.top_device_types) > 1:
            types_list = ", ".join([t[0] for t in label.top_device_types[:3]])
            reasons.append(
                f"- **Mixed Device Types:** These devices represent a mix of different types ({types_list}), "
                f"preventing them from forming a cohesive group."
            )
    
    # Check for lack of identity context
    if not label.top_ad_groups and not label.top_ise_profiles:
        reasons.append(
            f"- **Lack of Identity Context:** These devices lack clear identity markers (AD groups, ISE profiles) "
            f"that would help categorize them, making grouping decisions uncertain."
        )
    
    if reasons:
        lines.append("**Specific Reasons:**")
        lines.extend(reasons)
        lines.append("")
    else:
        lines.append(
            "- **Outlier Behavior:** These devices exhibit behavioral patterns that don't match any "
            "established cluster, likely due to unique roles, configurations, or usage patterns."
        )
        lines.append("")
    
    # What this means
    lines.append("**What This Means:**")
    lines.append(
        f"These {label.member_count} devices will remain unclustered (no SGT assigned automatically). "
        "Administrators should review these devices individually to determine if they should be:"
    )
    lines.append("1. Manually assigned to an existing cluster/SGT")
    lines.append("2. Assigned to a new cluster/SGT if they represent a new device category")
    lines.append("3. Left unclustered if they are truly unique or require special handling")
    lines.append("")
    lines.append(
        "**Recommendation:** Review the device details and traffic patterns to determine the appropriate "
        "SGT assignment. These devices may represent new device types, misconfigured endpoints, or "
        "devices with legitimate but unique network requirements."
    )
    
    return "\n".join(lines)

