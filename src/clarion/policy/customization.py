"""
Policy Customization - Human-in-the-loop review and modification.

Allows security teams to review, approve, and customize AI-generated
recommendations before deployment.

Key features:
- Review SGT recommendations (approve/reject/modify)
- Customize SGT names and values
- Merge or split clusters
- Add/remove/modify SGACL rules
- Override traffic patterns
- Persist customizations for reuse
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Any
import json
import logging
import copy

from clarion.clustering.sgt_mapper import SGTTaxonomy, SGTRecommendation
from clarion.policy.sgacl import SGACLPolicy, SGACLRule

logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Status of a recommendation."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"


@dataclass
class SGTCustomization:
    """
    Customization for an SGT recommendation.
    
    Tracks what was changed from the original recommendation.
    """
    original_cluster_id: int
    original_sgt_value: int
    original_sgt_name: str
    
    # Current values (may be modified)
    sgt_value: int
    sgt_name: str
    
    # Status
    status: ApprovalStatus = ApprovalStatus.PENDING
    
    # Merge target (if this cluster was merged into another)
    merged_into: Optional[int] = None
    
    # Comments from reviewer
    comments: List[str] = field(default_factory=list)
    
    # Who made the change
    modified_by: Optional[str] = None
    modified_at: Optional[datetime] = None
    
    @property
    def is_modified(self) -> bool:
        """Check if values differ from original."""
        return (
            self.sgt_value != self.original_sgt_value or
            self.sgt_name != self.original_sgt_name or
            self.merged_into is not None
        )
    
    def rename(self, new_name: str, modified_by: Optional[str] = None) -> None:
        """Rename the SGT."""
        self.sgt_name = new_name
        self.status = ApprovalStatus.MODIFIED
        self.modified_by = modified_by
        self.modified_at = datetime.now()
    
    def reassign_value(self, new_value: int, modified_by: Optional[str] = None) -> None:
        """Reassign the SGT value."""
        self.sgt_value = new_value
        self.status = ApprovalStatus.MODIFIED
        self.modified_by = modified_by
        self.modified_at = datetime.now()
    
    def approve(self, modified_by: Optional[str] = None, comment: Optional[str] = None) -> None:
        """Approve the recommendation."""
        self.status = ApprovalStatus.APPROVED
        self.modified_by = modified_by
        self.modified_at = datetime.now()
        if comment:
            self.comments.append(comment)
    
    def reject(self, modified_by: Optional[str] = None, reason: Optional[str] = None) -> None:
        """Reject the recommendation."""
        self.status = ApprovalStatus.REJECTED
        self.modified_by = modified_by
        self.modified_at = datetime.now()
        if reason:
            self.comments.append(f"Rejected: {reason}")
    
    def add_comment(self, comment: str, author: Optional[str] = None) -> None:
        """Add a comment."""
        prefix = f"[{author}] " if author else ""
        self.comments.append(f"{prefix}{comment}")
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "original_cluster_id": self.original_cluster_id,
            "original_sgt_value": self.original_sgt_value,
            "original_sgt_name": self.original_sgt_name,
            "sgt_value": self.sgt_value,
            "sgt_name": self.sgt_name,
            "status": self.status.value,
            "merged_into": self.merged_into,
            "comments": self.comments,
            "modified_by": self.modified_by,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "is_modified": self.is_modified,
        }
    
    @classmethod
    def from_recommendation(cls, rec: SGTRecommendation) -> "SGTCustomization":
        """Create from an SGT recommendation."""
        return cls(
            original_cluster_id=rec.cluster_id,
            original_sgt_value=rec.sgt_value,
            original_sgt_name=rec.sgt_name,
            sgt_value=rec.sgt_value,
            sgt_name=rec.sgt_name,
        )


@dataclass
class RuleCustomization:
    """
    Customization for an SGACL rule.
    """
    action: str  # "add", "remove", "modify"
    rule: SGACLRule
    original_rule: Optional[SGACLRule] = None  # For modifications
    reason: Optional[str] = None
    added_by: Optional[str] = None
    added_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "action": self.action,
            "rule": self.rule.to_dict(),
            "original_rule": self.original_rule.to_dict() if self.original_rule else None,
            "reason": self.reason,
            "added_by": self.added_by,
            "added_at": self.added_at.isoformat() if self.added_at else None,
        }


@dataclass
class PolicyCustomization:
    """
    Customization for an SGACL policy.
    """
    policy_name: str
    src_sgt: int
    dst_sgt: int
    
    # Rule modifications
    rule_changes: List[RuleCustomization] = field(default_factory=list)
    
    # Override default action
    default_action_override: Optional[str] = None  # "permit" or "deny"
    
    # Status
    status: ApprovalStatus = ApprovalStatus.PENDING
    comments: List[str] = field(default_factory=list)
    
    def add_permit_rule(
        self,
        protocol: str,
        port: int,
        reason: Optional[str] = None,
        added_by: Optional[str] = None,
    ) -> None:
        """Add a permit rule."""
        rule = SGACLRule(
            action="permit",
            protocol=protocol,
            port=port,
        )
        self.rule_changes.append(RuleCustomization(
            action="add",
            rule=rule,
            reason=reason,
            added_by=added_by,
            added_at=datetime.now(),
        ))
    
    def remove_rule(
        self,
        protocol: str,
        port: int,
        reason: Optional[str] = None,
        added_by: Optional[str] = None,
    ) -> None:
        """Mark a rule for removal."""
        rule = SGACLRule(
            action="permit",
            protocol=protocol,
            port=port,
        )
        self.rule_changes.append(RuleCustomization(
            action="remove",
            rule=rule,
            reason=reason,
            added_by=added_by,
            added_at=datetime.now(),
        ))
    
    def add_deny_rule(
        self,
        protocol: str,
        port: int,
        reason: Optional[str] = None,
        added_by: Optional[str] = None,
    ) -> None:
        """Add an explicit deny rule."""
        rule = SGACLRule(
            action="deny",
            protocol=protocol,
            port=port,
            log=True,
        )
        self.rule_changes.append(RuleCustomization(
            action="add",
            rule=rule,
            reason=reason,
            added_by=added_by,
            added_at=datetime.now(),
        ))
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "policy_name": self.policy_name,
            "src_sgt": self.src_sgt,
            "dst_sgt": self.dst_sgt,
            "rule_changes": [rc.to_dict() for rc in self.rule_changes],
            "default_action_override": self.default_action_override,
            "status": self.status.value,
            "comments": self.comments,
        }


@dataclass
class CustomizationSession:
    """
    A complete customization session.
    
    Tracks all modifications made to recommendations and policies
    during a review session.
    """
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    created_by: Optional[str] = None
    
    # SGT customizations by cluster_id
    sgt_customizations: Dict[int, SGTCustomization] = field(default_factory=dict)
    
    # Policy customizations by (src_sgt, dst_sgt)
    policy_customizations: Dict[tuple, PolicyCustomization] = field(default_factory=dict)
    
    # Global settings
    settings: Dict[str, Any] = field(default_factory=dict)
    
    # Reserved SGT values (can't be reassigned)
    reserved_sgt_values: Set[int] = field(default_factory=set)
    
    def __post_init__(self):
        """Initialize with standard reserved values."""
        # Cisco reserved SGT values
        self.reserved_sgt_values = {
            0,      # Unknown
            1,      # DEFAULT (implicit)
            2,      # TrustSec Devices
            65535,  # Reserved
        }
    
    def add_sgt_customization(self, rec: SGTRecommendation) -> SGTCustomization:
        """Add an SGT for customization."""
        custom = SGTCustomization.from_recommendation(rec)
        self.sgt_customizations[rec.cluster_id] = custom
        return custom
    
    def get_sgt_customization(self, cluster_id: int) -> Optional[SGTCustomization]:
        """Get customization for a cluster."""
        return self.sgt_customizations.get(cluster_id)
    
    def rename_sgt(
        self,
        cluster_id: int,
        new_name: str,
        modified_by: Optional[str] = None,
    ) -> bool:
        """Rename an SGT."""
        custom = self.sgt_customizations.get(cluster_id)
        if custom is None:
            logger.warning(f"No customization found for cluster {cluster_id}")
            return False
        
        custom.rename(new_name, modified_by)
        logger.info(f"Renamed SGT for cluster {cluster_id}: {new_name}")
        return True
    
    def reassign_sgt_value(
        self,
        cluster_id: int,
        new_value: int,
        modified_by: Optional[str] = None,
    ) -> bool:
        """Reassign an SGT value."""
        # Check if value is reserved
        if new_value in self.reserved_sgt_values:
            logger.error(f"SGT value {new_value} is reserved")
            return False
        
        # Check if value is already used
        for cid, custom in self.sgt_customizations.items():
            if cid != cluster_id and custom.sgt_value == new_value:
                logger.error(f"SGT value {new_value} already assigned to cluster {cid}")
                return False
        
        custom = self.sgt_customizations.get(cluster_id)
        if custom is None:
            logger.warning(f"No customization found for cluster {cluster_id}")
            return False
        
        custom.reassign_value(new_value, modified_by)
        logger.info(f"Reassigned SGT value for cluster {cluster_id}: {new_value}")
        return True
    
    def merge_clusters(
        self,
        source_cluster_id: int,
        target_cluster_id: int,
        modified_by: Optional[str] = None,
    ) -> bool:
        """Merge one cluster into another."""
        source = self.sgt_customizations.get(source_cluster_id)
        target = self.sgt_customizations.get(target_cluster_id)
        
        if source is None or target is None:
            logger.error("Both clusters must exist for merge")
            return False
        
        source.merged_into = target_cluster_id
        source.status = ApprovalStatus.MODIFIED
        source.modified_by = modified_by
        source.modified_at = datetime.now()
        source.add_comment(f"Merged into cluster {target_cluster_id} ({target.sgt_name})")
        
        logger.info(f"Merged cluster {source_cluster_id} into {target_cluster_id}")
        return True
    
    def approve_sgt(
        self,
        cluster_id: int,
        modified_by: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> bool:
        """Approve an SGT recommendation."""
        custom = self.sgt_customizations.get(cluster_id)
        if custom is None:
            return False
        custom.approve(modified_by, comment)
        return True
    
    def reject_sgt(
        self,
        cluster_id: int,
        modified_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> bool:
        """Reject an SGT recommendation."""
        custom = self.sgt_customizations.get(cluster_id)
        if custom is None:
            return False
        custom.reject(modified_by, reason)
        return True
    
    def approve_all_pending(self, modified_by: Optional[str] = None) -> int:
        """Approve all pending SGT recommendations."""
        count = 0
        for custom in self.sgt_customizations.values():
            if custom.status == ApprovalStatus.PENDING:
                custom.approve(modified_by)
                count += 1
        return count
    
    def get_policy_customization(
        self,
        src_sgt: int,
        dst_sgt: int,
    ) -> PolicyCustomization:
        """Get or create policy customization."""
        key = (src_sgt, dst_sgt)
        if key not in self.policy_customizations:
            self.policy_customizations[key] = PolicyCustomization(
                policy_name=f"SGACL_{src_sgt}_to_{dst_sgt}",
                src_sgt=src_sgt,
                dst_sgt=dst_sgt,
            )
        return self.policy_customizations[key]
    
    def add_permit_rule(
        self,
        src_sgt: int,
        dst_sgt: int,
        protocol: str,
        port: int,
        reason: Optional[str] = None,
        added_by: Optional[str] = None,
    ) -> None:
        """Add a permit rule to a policy."""
        custom = self.get_policy_customization(src_sgt, dst_sgt)
        custom.add_permit_rule(protocol, port, reason, added_by)
    
    def remove_permit_rule(
        self,
        src_sgt: int,
        dst_sgt: int,
        protocol: str,
        port: int,
        reason: Optional[str] = None,
        added_by: Optional[str] = None,
    ) -> None:
        """Remove a permit rule from a policy."""
        custom = self.get_policy_customization(src_sgt, dst_sgt)
        custom.remove_rule(protocol, port, reason, added_by)
    
    def add_deny_rule(
        self,
        src_sgt: int,
        dst_sgt: int,
        protocol: str,
        port: int,
        reason: Optional[str] = None,
        added_by: Optional[str] = None,
    ) -> None:
        """Add an explicit deny rule."""
        custom = self.get_policy_customization(src_sgt, dst_sgt)
        custom.add_deny_rule(protocol, port, reason, added_by)
    
    def summary(self) -> Dict:
        """Get session summary."""
        sgt_status = {
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "modified": 0,
        }
        for custom in self.sgt_customizations.values():
            sgt_status[custom.status.value] += 1
        
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "sgt_count": len(self.sgt_customizations),
            "sgt_status": sgt_status,
            "policy_customizations": len(self.policy_customizations),
            "total_rule_changes": sum(
                len(pc.rule_changes) for pc in self.policy_customizations.values()
            ),
        }
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "sgt_customizations": {
                str(k): v.to_dict() for k, v in self.sgt_customizations.items()
            },
            "policy_customizations": {
                f"{k[0]}_{k[1]}": v.to_dict() for k, v in self.policy_customizations.items()
            },
            "settings": self.settings,
            "reserved_sgt_values": list(self.reserved_sgt_values),
        }
    
    def save(self, path: str) -> None:
        """Save session to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Saved customization session to {path}")
    
    @classmethod
    def load(cls, path: str) -> "CustomizationSession":
        """Load session from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        
        session = cls(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            created_by=data.get("created_by"),
        )
        
        # Restore SGT customizations
        for cluster_id_str, custom_data in data.get("sgt_customizations", {}).items():
            cluster_id = int(cluster_id_str)
            custom = SGTCustomization(
                original_cluster_id=custom_data["original_cluster_id"],
                original_sgt_value=custom_data["original_sgt_value"],
                original_sgt_name=custom_data["original_sgt_name"],
                sgt_value=custom_data["sgt_value"],
                sgt_name=custom_data["sgt_name"],
                status=ApprovalStatus(custom_data["status"]),
                merged_into=custom_data.get("merged_into"),
                comments=custom_data.get("comments", []),
                modified_by=custom_data.get("modified_by"),
                modified_at=datetime.fromisoformat(custom_data["modified_at"]) if custom_data.get("modified_at") else None,
            )
            session.sgt_customizations[cluster_id] = custom
        
        # Restore policy customizations
        for key_str, policy_data in data.get("policy_customizations", {}).items():
            src_sgt, dst_sgt = map(int, key_str.split("_"))
            key = (src_sgt, dst_sgt)
            
            policy_custom = PolicyCustomization(
                policy_name=policy_data["policy_name"],
                src_sgt=src_sgt,
                dst_sgt=dst_sgt,
                default_action_override=policy_data.get("default_action_override"),
                status=ApprovalStatus(policy_data["status"]),
                comments=policy_data.get("comments", []),
            )
            
            # Restore rule changes
            for rc_data in policy_data.get("rule_changes", []):
                rule = SGACLRule(
                    action=rc_data["rule"]["action"],
                    protocol=rc_data["rule"]["protocol"],
                    port=rc_data["rule"].get("port"),
                )
                rule_custom = RuleCustomization(
                    action=rc_data["action"],
                    rule=rule,
                    reason=rc_data.get("reason"),
                    added_by=rc_data.get("added_by"),
                    added_at=datetime.fromisoformat(rc_data["added_at"]) if rc_data.get("added_at") else None,
                )
                policy_custom.rule_changes.append(rule_custom)
            
            session.policy_customizations[key] = policy_custom
        
        session.settings = data.get("settings", {})
        session.reserved_sgt_values = set(data.get("reserved_sgt_values", [0, 1, 2, 65535]))
        
        logger.info(f"Loaded customization session from {path}")
        return session


class PolicyCustomizer:
    """
    Apply customizations to policies and taxonomy.
    
    Takes a customization session and applies all modifications
    to generate the final policies.
    
    Example:
        >>> session = CustomizationSession("review-001")
        >>> # ... add customizations ...
        >>> customizer = PolicyCustomizer(session)
        >>> final_taxonomy = customizer.apply_to_taxonomy(original_taxonomy)
        >>> final_policies = customizer.apply_to_policies(original_policies)
    """
    
    def __init__(self, session: CustomizationSession):
        """Initialize with a customization session."""
        self.session = session
    
    def apply_to_taxonomy(self, taxonomy: SGTTaxonomy) -> SGTTaxonomy:
        """
        Apply customizations to an SGT taxonomy.
        
        Returns a new taxonomy with all approved and modified recommendations.
        Rejected recommendations are excluded.
        """
        new_recommendations = []
        
        for rec in taxonomy.recommendations:
            custom = self.session.sgt_customizations.get(rec.cluster_id)
            
            if custom is None:
                # No customization - keep as-is
                new_recommendations.append(rec)
                continue
            
            if custom.status == ApprovalStatus.REJECTED:
                # Skip rejected recommendations
                logger.info(f"Excluding rejected SGT: {rec.sgt_name}")
                continue
            
            if custom.merged_into is not None:
                # Skip merged clusters (they're absorbed into another)
                logger.info(f"Excluding merged cluster {rec.cluster_id}")
                continue
            
            # Apply modifications
            new_rec = SGTRecommendation(
                cluster_id=rec.cluster_id,
                sgt_value=custom.sgt_value,
                sgt_name=custom.sgt_name,
                cluster_label=rec.cluster_label,
                cluster_size=rec.cluster_size,
                confidence=rec.confidence,
                justification=rec.justification,
                endpoint_count=rec.endpoint_count,
                sample_endpoints=rec.sample_endpoints,
            )
            new_recommendations.append(new_rec)
        
        return SGTTaxonomy(
            recommendations=new_recommendations,
            total_endpoints=taxonomy.total_endpoints,
        )
    
    def apply_to_policies(
        self,
        policies: List[SGACLPolicy],
        taxonomy: Optional[SGTTaxonomy] = None,
    ) -> List[SGACLPolicy]:
        """
        Apply customizations to SGACL policies.
        
        Applies rule additions/removals and updates SGT names
        based on taxonomy customizations.
        """
        # Build SGT name lookup from customizations
        sgt_names: Dict[int, str] = {}
        for custom in self.session.sgt_customizations.values():
            sgt_names[custom.sgt_value] = custom.sgt_name
        
        new_policies = []
        
        for policy in policies:
            # Check if we have customizations for this policy
            key = (policy.src_sgt, policy.dst_sgt)
            custom = self.session.policy_customizations.get(key)
            
            # Deep copy the policy
            new_policy = SGACLPolicy(
                name=policy.name,
                src_sgt=policy.src_sgt,
                src_sgt_name=sgt_names.get(policy.src_sgt, policy.src_sgt_name),
                dst_sgt=policy.dst_sgt,
                dst_sgt_name=sgt_names.get(policy.dst_sgt, policy.dst_sgt_name),
                rules=list(policy.rules),  # Copy rules
                total_observed_flows=policy.total_observed_flows,
                covered_flows=policy.covered_flows,
                default_action=policy.default_action,
            )
            
            if custom:
                self._apply_rule_changes(new_policy, custom)
            
            new_policies.append(new_policy)
        
        return new_policies
    
    def _apply_rule_changes(
        self,
        policy: SGACLPolicy,
        custom: PolicyCustomization,
    ) -> None:
        """Apply rule changes to a policy."""
        # Track rules to remove
        rules_to_remove: Set[tuple] = set()
        rules_to_add: List[SGACLRule] = []
        
        for change in custom.rule_changes:
            rule_key = (change.rule.protocol, change.rule.port)
            
            if change.action == "remove":
                rules_to_remove.add(rule_key)
            elif change.action == "add":
                rules_to_add.append(change.rule)
        
        # Remove marked rules
        new_rules = []
        for rule in policy.rules:
            rule_key = (rule.protocol, rule.port)
            if rule_key not in rules_to_remove:
                new_rules.append(rule)
            else:
                logger.info(f"Removed rule: {rule.to_cisco_syntax()}")
        
        # Add new rules (before the final deny)
        deny_rule = None
        if new_rules and new_rules[-1].action == "deny" and new_rules[-1].protocol == "ip":
            deny_rule = new_rules.pop()
        
        for rule in rules_to_add:
            new_rules.append(rule)
            logger.info(f"Added rule: {rule.to_cisco_syntax()}")
        
        # Re-add deny rule at end
        if deny_rule:
            new_rules.append(deny_rule)
        
        policy.rules = new_rules
        
        # Apply default action override
        if custom.default_action_override:
            policy.default_action = custom.default_action_override


def create_review_session(
    taxonomy: SGTTaxonomy,
    session_id: Optional[str] = None,
    created_by: Optional[str] = None,
) -> CustomizationSession:
    """
    Create a new review session from an SGT taxonomy.
    
    Args:
        taxonomy: The AI-generated taxonomy to review
        session_id: Optional session identifier
        created_by: Who is creating the session
        
    Returns:
        CustomizationSession ready for review
    """
    if session_id is None:
        session_id = f"review-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    session = CustomizationSession(
        session_id=session_id,
        created_by=created_by,
    )
    
    # Add all recommendations for review
    for rec in taxonomy.recommendations:
        session.add_sgt_customization(rec)
    
    logger.info(
        f"Created review session {session_id} with "
        f"{len(taxonomy.recommendations)} SGT recommendations"
    )
    
    return session


def generate_review_report(session: CustomizationSession) -> str:
    """
    Generate a human-readable review report.
    
    Shows all customizations made during the session.
    """
    lines = [
        "=" * 70,
        "POLICY CUSTOMIZATION REVIEW REPORT",
        "=" * 70,
        f"Session ID: {session.session_id}",
        f"Created: {session.created_at.isoformat()}",
        f"Created by: {session.created_by or 'Unknown'}",
        "",
    ]
    
    # Summary
    summary = session.summary()
    lines.extend([
        "SUMMARY",
        "-" * 40,
        f"Total SGTs reviewed: {summary['sgt_count']}",
        f"  - Approved: {summary['sgt_status']['approved']}",
        f"  - Modified: {summary['sgt_status']['modified']}",
        f"  - Rejected: {summary['sgt_status']['rejected']}",
        f"  - Pending:  {summary['sgt_status']['pending']}",
        f"",
        f"Policy customizations: {summary['policy_customizations']}",
        f"Total rule changes: {summary['total_rule_changes']}",
        "",
    ])
    
    # SGT Details
    lines.extend([
        "SGT RECOMMENDATIONS",
        "-" * 40,
    ])
    
    for cluster_id, custom in sorted(session.sgt_customizations.items()):
        status_icon = {
            ApprovalStatus.APPROVED: "✓",
            ApprovalStatus.REJECTED: "✗",
            ApprovalStatus.MODIFIED: "~",
            ApprovalStatus.PENDING: "?",
        }[custom.status]
        
        line = f"  [{status_icon}] Cluster {cluster_id}: SGT {custom.sgt_value} - {custom.sgt_name}"
        
        if custom.is_modified:
            if custom.sgt_name != custom.original_sgt_name:
                line += f" (was: {custom.original_sgt_name})"
            if custom.sgt_value != custom.original_sgt_value:
                line += f" (value was: {custom.original_sgt_value})"
        
        if custom.merged_into:
            line += f" [MERGED into {custom.merged_into}]"
        
        lines.append(line)
        
        for comment in custom.comments:
            lines.append(f"      → {comment}")
    
    # Policy Details
    if session.policy_customizations:
        lines.extend([
            "",
            "POLICY CUSTOMIZATIONS",
            "-" * 40,
        ])
        
        for (src, dst), custom in sorted(session.policy_customizations.items()):
            lines.append(f"  {custom.policy_name} (SGT {src} → SGT {dst}):")
            
            for change in custom.rule_changes:
                action_icon = {"add": "+", "remove": "-", "modify": "~"}[change.action]
                lines.append(f"    [{action_icon}] {change.rule.to_cisco_syntax()}")
                if change.reason:
                    lines.append(f"        Reason: {change.reason}")
    
    lines.extend([
        "",
        "=" * 70,
    ])
    
    return "\n".join(lines)

