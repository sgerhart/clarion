"""
ISE Authorization Policy Exporter.

Generates ISE authorization policy configurations from policy recommendations.
Creates ISE-compatible JSON/XML/CLI formats for authorization policies that assign SGTs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import json
import logging
import xml.etree.ElementTree as ET

from clarion.policy.recommendation import PolicyRecommendation, PolicyRule, PolicyCondition

logger = logging.getLogger(__name__)


@dataclass
class ISEAuthorizationPolicyExport:
    """
    ISE authorization policy export package.
    
    Contains authorization policy configurations in multiple formats.
    """
    generated_at: datetime = field(default_factory=datetime.utcnow)
    clarion_version: str = "0.5.0"
    
    # Policy definitions
    authorization_policies: List[Dict] = field(default_factory=list)
    
    # Export formats
    json_config: str = ""
    xml_config: str = ""
    cli_config: str = ""
    
    # ISE ERS API payloads (for authorization policy creation)
    ise_api_payloads: List[Dict] = field(default_factory=list)
    
    # Deployment guide
    deployment_guide: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export."""
        return {
            "metadata": {
                "generated_at": self.generated_at.isoformat(),
                "clarion_version": self.clarion_version,
            },
            "authorization_policies": self.authorization_policies,
            "ise_api_payloads": self.ise_api_payloads,
        }


class ISEAuthorizationPolicyExporter:
    """
    Exports policy recommendations as ISE authorization policy configurations.
    
    Generates:
    - ISE ERS API JSON payloads (for programmatic import)
    - XML configuration (for manual import/backup)
    - CLI-like configuration (for documentation)
    - Deployment guide
    """
    
    def __init__(
        self,
        ise_version: str = "3.1",
        include_comments: bool = True,
    ):
        """
        Initialize the exporter.
        
        Args:
            ise_version: Target ISE version
            include_comments: Include descriptive comments in CLI config
        """
        self.ise_version = ise_version
        self.include_comments = include_comments
    
    def export_recommendation(
        self,
        recommendation: PolicyRecommendation,
    ) -> ISEAuthorizationPolicyExport:
        """
        Export a single policy recommendation as ISE authorization policy.
        
        Args:
            recommendation: PolicyRecommendation to export
            
        Returns:
            ISEAuthorizationPolicyExport with all formats
        """
        export = ISEAuthorizationPolicyExport()
        
        # Generate ISE authorization policy structure
        policy_def = self._generate_policy_definition(recommendation)
        export.authorization_policies = [policy_def]
        
        # Generate ISE ERS API payload
        export.ise_api_payloads = [self._generate_ers_api_payload(recommendation)]
        
        # Generate JSON config
        export.json_config = json.dumps(export.to_dict(), indent=2)
        
        # Generate XML config
        export.xml_config = self._generate_xml_config(recommendation)
        
        # Generate CLI config
        export.cli_config = self._generate_cli_config(recommendation)
        
        # Generate deployment guide
        export.deployment_guide = self._generate_deployment_guide(recommendation)
        
        return export
    
    def export_recommendations(
        self,
        recommendations: List[PolicyRecommendation],
    ) -> ISEAuthorizationPolicyExport:
        """
        Export multiple policy recommendations as ISE authorization policies.
        
        Args:
            recommendations: List of PolicyRecommendations to export
            
        Returns:
            ISEAuthorizationPolicyExport with all policies
        """
        export = ISEAuthorizationPolicyExport()
        
        # Generate policy definitions
        export.authorization_policies = [
            self._generate_policy_definition(rec) for rec in recommendations
        ]
        
        # Generate ISE ERS API payloads
        export.ise_api_payloads = [
            self._generate_ers_api_payload(rec) for rec in recommendations
        ]
        
        # Generate JSON config
        export.json_config = json.dumps(export.to_dict(), indent=2)
        
        # Generate XML config
        export.xml_config = self._generate_xml_config_multiple(recommendations)
        
        # Generate CLI config
        export.cli_config = self._generate_cli_config_multiple(recommendations)
        
        # Generate deployment guide
        export.deployment_guide = self._generate_deployment_guide_multiple(recommendations)
        
        return export
    
    def _generate_policy_definition(
        self,
        recommendation: PolicyRecommendation,
    ) -> Dict:
        """
        Generate ISE authorization policy definition structure.
        
        This represents the policy structure that would be created in ISE.
        """
        policy_rule = recommendation.policy_rule
        
        # Build condition dictionary
        conditions = {}
        for condition in policy_rule.conditions:
            condition_type = condition.type
            if condition_type == "ad_group":
                if "AD:Groups" not in conditions:
                    conditions["AD:Groups"] = []
                conditions["AD:Groups"].append(condition.value)
            elif condition_type == "device_profile":
                if "Device:Profile" not in conditions:
                    conditions["Device:Profile"] = []
                conditions["Device:Profile"].append(condition.value)
            elif condition_type == "device_type":
                if "Device:Type" not in conditions:
                    conditions["Device:Type"] = []
                conditions["Device:Type"].append(condition.value)
        
        return {
            "name": policy_rule.name,
            "description": policy_rule.justification,
            "condition": policy_rule.to_ise_condition_string(),
            "conditions": conditions,
            "action": {
                "type": "AssignSGT",
                "sgt_value": recommendation.recommended_sgt,
                "sgt_name": recommendation.recommended_sgt_name,
            },
            "status": recommendation.status,
            "devices_affected": recommendation.devices_affected,
            "ad_groups_affected": recommendation.ad_groups_affected,
            "device_profiles_affected": recommendation.device_profiles_affected,
            "device_types_affected": recommendation.device_types_affected,
        }
    
    def _generate_ers_api_payload(
        self,
        recommendation: PolicyRecommendation,
    ) -> Dict:
        """
        Generate ISE ERS API payload for authorization policy creation.
        
        ISE ERS API format for authorization policies.
        Note: Exact API format may vary by ISE version.
        """
        policy_rule = recommendation.policy_rule
        
        # Build condition attribute list for ISE API
        condition_attributes = []
        for condition in policy_rule.conditions:
            # Map condition type to ISE attribute names
            ise_attribute_map = {
                "ad_group": "AD1:Groups",
                "device_profile": "Device:Profile",
                "device_type": "Device:Type",
            }
            ise_attr = ise_attribute_map.get(condition.type, condition.type)
            condition_attributes.append({
                "attributeName": ise_attr,
                "attributeValue": condition.value,
                "conditionType": "EQUALS",
            })
        
        # Build policy result (assign SGT)
        policy_result = {
            "result": "PERMIT",
            "securityGroup": f"SGT:{recommendation.recommended_sgt}",
        }
        
        return {
            "AuthorizationProfile": {
                "name": policy_rule.name,
                "description": policy_rule.justification[:256] if policy_rule.justification else "",
                "trackMovement": False,
                "serviceTemplate": False,
            },
            "Policy": {
                "name": policy_rule.name,
                "description": policy_rule.justification[:256] if policy_rule.justification else "",
                "condition": {
                    "conditionType": "AND",
                    "isNegate": False,
                    "attributeName": "CompoundCondition",
                    "attributeValue": "OR",
                    "children": condition_attributes,
                },
                "result": policy_result,
                "rank": 0,  # Policy rank (lower = higher priority)
            },
        }
    
    def _generate_xml_config(
        self,
        recommendation: PolicyRecommendation,
    ) -> str:
        """
        Generate XML configuration for ISE authorization policy.
        
        XML format for ISE policy import/backup.
        """
        policy_rule = recommendation.policy_rule
        
        # Create XML structure
        root = ET.Element("AuthorizationPolicy")
        root.set("name", policy_rule.name)
        root.set("description", policy_rule.justification or "")
        
        # Conditions
        conditions_elem = ET.SubElement(root, "Conditions")
        for condition in policy_rule.conditions:
            cond_elem = ET.SubElement(conditions_elem, "Condition")
            cond_elem.set("attribute", condition.type)
            cond_elem.set("operator", condition.operator)
            cond_elem.set("value", condition.value)
        
        # Result (assign SGT)
        result_elem = ET.SubElement(root, "Result")
        result_elem.set("action", "PERMIT")
        result_elem.set("sgt_value", str(recommendation.recommended_sgt))
        if recommendation.recommended_sgt_name:
            result_elem.set("sgt_name", recommendation.recommended_sgt_name)
        
        # Convert to string
        ET.indent(root, space="  ")
        return ET.tostring(root, encoding="unicode")
    
    def _generate_xml_config_multiple(
        self,
        recommendations: List[PolicyRecommendation],
    ) -> str:
        """Generate XML config for multiple policies."""
        root = ET.Element("AuthorizationPolicies")
        root.set("generated_at", datetime.utcnow().isoformat())
        
        for rec in recommendations:
            policy_elem = ET.SubElement(root, "AuthorizationPolicy")
            policy_elem.set("name", rec.policy_rule.name)
            
            # Conditions
            conditions_elem = ET.SubElement(policy_elem, "Conditions")
            for condition in rec.policy_rule.conditions:
                cond_elem = ET.SubElement(conditions_elem, "Condition")
                cond_elem.set("attribute", condition.type)
                cond_elem.set("operator", condition.operator)
                cond_elem.set("value", condition.value)
            
            # Result
            result_elem = ET.SubElement(policy_elem, "Result")
            result_elem.set("action", "PERMIT")
            result_elem.set("sgt_value", str(rec.recommended_sgt))
            if rec.recommended_sgt_name:
                result_elem.set("sgt_name", rec.recommended_sgt_name)
        
        ET.indent(root, space="  ")
        return ET.tostring(root, encoding="unicode")
    
    def _generate_cli_config(
        self,
        recommendation: PolicyRecommendation,
    ) -> str:
        """
        Generate CLI-like configuration for documentation.
        
        This is a human-readable format, not actual ISE CLI commands
        (ISE doesn't have a CLI for policy creation).
        """
        lines = []
        policy_rule = recommendation.policy_rule
        
        if self.include_comments:
            lines.extend([
                "!" + "=" * 60,
                f"! ISE Authorization Policy: {policy_rule.name}",
                f"! Generated: {datetime.utcnow().isoformat()}",
                "!" + "=" * 60,
                "",
            ])
        
        # Policy name and description
        lines.append(f"Policy Name: {policy_rule.name}")
        if policy_rule.justification:
            lines.append(f"Description: {policy_rule.justification}")
        lines.append("")
        
        # Conditions
        lines.append("Conditions:")
        for condition in policy_rule.conditions:
            lines.append(f"  - {condition.to_ise_expression()}")
        lines.append("")
        
        # Action
        lines.append("Action:")
        lines.append(f"  - Assign SGT {recommendation.recommended_sgt}")
        if recommendation.recommended_sgt_name:
            lines.append(f"    SGT Name: {recommendation.recommended_sgt_name}")
        lines.append("")
        
        # Impact
        if recommendation.devices_affected > 0:
            lines.append("Impact:")
            lines.append(f"  - Devices Affected: {recommendation.devices_affected}")
            if recommendation.ad_groups_affected:
                lines.append(f"  - AD Groups: {', '.join(recommendation.ad_groups_affected)}")
            if recommendation.device_profiles_affected:
                lines.append(f"  - Device Profiles: {', '.join(recommendation.device_profiles_affected)}")
            lines.append("")
        
        if self.include_comments:
            lines.append("!" + "=" * 60)
        
        return "\n".join(lines)
    
    def _generate_cli_config_multiple(
        self,
        recommendations: List[PolicyRecommendation],
    ) -> str:
        """Generate CLI config for multiple policies."""
        if not recommendations:
            return ""
        
        lines = []
        
        if self.include_comments:
            lines.extend([
                "!" + "=" * 60,
                "! ISE Authorization Policy Configuration",
                f"! Generated: {datetime.utcnow().isoformat()}",
                f"! Total Policies: {len(recommendations)}",
                "!" + "=" * 60,
                "",
            ])
        
        for i, rec in enumerate(recommendations, 1):
            lines.append(self._generate_cli_config(rec))
            if i < len(recommendations):
                lines.append("")
                lines.append("!" + "-" * 60)
                lines.append("")
        
        return "\n".join(lines)
    
    def _generate_deployment_guide(
        self,
        recommendation: PolicyRecommendation,
    ) -> str:
        """Generate deployment guide for a single policy."""
        policy_rule = recommendation.policy_rule
        
        lines = [
            f"# ISE Authorization Policy Deployment Guide: {policy_rule.name}",
            "",
            f"Generated: {datetime.utcnow().isoformat()}",
            "",
            "## Policy Overview",
            "",
            f"**Policy Name:** {policy_rule.name}",
            f"**Description:** {policy_rule.justification}",
            "",
            "## Policy Conditions",
            "",
        ]
        
        for condition in policy_rule.conditions:
            lines.append(f"- {condition.to_ise_expression()}")
        
        lines.extend([
            "",
            "## Policy Action",
            "",
            f"**Assign SGT:** {recommendation.recommended_sgt}",
        ])
        
        if recommendation.recommended_sgt_name:
            lines.append(f"**SGT Name:** {recommendation.recommended_sgt_name}")
        
        lines.extend([
            "",
            "## Impact Analysis",
            "",
            f"- **Devices Affected:** {recommendation.devices_affected}",
        ])
        
        if recommendation.ad_groups_affected:
            lines.append(f"- **AD Groups:** {', '.join(recommendation.ad_groups_affected)}")
        if recommendation.device_profiles_affected:
            lines.append(f"- **Device Profiles:** {', '.join(recommendation.device_profiles_affected)}")
        if recommendation.device_types_affected:
            lines.append(f"- **Device Types:** {', '.join(recommendation.device_types_affected)}")
        
        lines.extend([
            "",
            "## Deployment Steps",
            "",
            "### Option 1: ISE GUI",
            "",
            "1. Log into ISE Admin portal",
            "2. Navigate to Policy > Authorization > Authorization Policies",
            "3. Click 'Insert new row above' or 'Insert new row below'",
            "4. Configure policy:",
            f"   - **Name:** {policy_rule.name}",
            f"   - **Condition:** {policy_rule.to_ise_condition_string()}",
            f"   - **Profiles:** Create or select authorization profile that assigns SGT {recommendation.recommended_sgt}",
            "5. Save and deploy policy",
            "",
            "### Option 2: ISE ERS API",
            "",
            "1. Use the JSON payload provided in the export",
            "2. POST to ISE ERS API endpoint: `/ers/config/authorizationprofile`",
            "3. Create authorization profile with SGT assignment",
            "4. POST to ISE ERS API endpoint: `/ers/config/authorizationpolicy`",
            "5. Create authorization policy with conditions and profile reference",
            "",
            "### Verification",
            "",
            "1. Test with a device/user matching the policy conditions",
            f"2. Verify that SGT {recommendation.recommended_sgt} is assigned",
            "3. Check ISE live logs to confirm policy match",
            "4. Monitor for any issues",
            "",
        ])
        
        return "\n".join(lines)
    
    def _generate_deployment_guide_multiple(
        self,
        recommendations: List[PolicyRecommendation],
    ) -> str:
        """Generate deployment guide for multiple policies."""
        lines = [
            "# ISE Authorization Policy Deployment Guide",
            "",
            f"Generated: {datetime.utcnow().isoformat()}",
            "",
            f"**Total Policies:** {len(recommendations)}",
            "",
            "## Summary",
            "",
            "This export contains the following authorization policies:",
            "",
        ]
        
        for rec in recommendations:
            lines.append(f"- **{rec.policy_rule.name}**: Assign SGT {rec.recommended_sgt} ({rec.devices_affected} devices)")
        
        lines.extend([
            "",
            "## Deployment Steps",
            "",
            "### Option 1: ISE GUI (Recommended for First-Time Deployment)",
            "",
            "1. Log into ISE Admin portal",
            "2. Navigate to Policy > Authorization > Authorization Policies",
            "3. Review each policy configuration",
            "4. Deploy policies one at a time, testing after each deployment",
            "",
            "### Option 2: ISE ERS API (For Automated Deployment)",
            "",
            "1. Review the JSON payloads in the export",
            "2. Deploy in order (authorization profiles first, then policies)",
            "3. Use ISE ERS API endpoints:",
            "   - `/ers/config/authorizationprofile` (create profiles)",
            "   - `/ers/config/authorizationpolicy` (create policies)",
            "",
            "### Best Practices",
            "",
            "1. **Deploy in Monitor Mode First**: If available, deploy policies in monitor mode",
            "2. **Test Incrementally**: Deploy one policy at a time and verify",
            "3. **Review Impact**: Check how many devices/users will be affected",
            "4. **Verify SGT Assignment**: Confirm SGTs are assigned correctly",
            "5. **Monitor Logs**: Watch ISE logs for any issues or conflicts",
            "",
            "## Policy Details",
            "",
        ])
        
        for rec in recommendations:
            lines.append(f"### {rec.policy_rule.name}")
            lines.append("")
            lines.append(f"**Conditions:** {rec.policy_rule.to_ise_condition_string()}")
            lines.append(f"**Action:** Assign SGT {rec.recommended_sgt}")
            if rec.recommended_sgt_name:
                lines.append(f"**SGT Name:** {rec.recommended_sgt_name}")
            lines.append(f"**Devices Affected:** {rec.devices_affected}")
            lines.append("")
        
        return "\n".join(lines)

