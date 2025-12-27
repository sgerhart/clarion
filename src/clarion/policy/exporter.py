"""
ISE Exporter - Export policies in Cisco ISE-ready format.

Generates configuration files and API payloads for importing
policies into Cisco Identity Services Engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import json
import logging

from clarion.policy.matrix import PolicyMatrix
from clarion.policy.sgacl import SGACLPolicy
from clarion.policy.impact import ImpactReport
from clarion.clustering.sgt_mapper import SGTTaxonomy

logger = logging.getLogger(__name__)


@dataclass
class PolicyExport:
    """
    Complete policy export package.
    
    Contains all artifacts needed to deploy policies.
    """
    # Metadata
    generated_at: datetime = field(default_factory=datetime.now)
    clarion_version: str = "0.2.0"
    
    # SGT definitions
    sgt_definitions: List[Dict] = field(default_factory=list)
    
    # SGACL definitions
    sgacl_definitions: List[Dict] = field(default_factory=list)
    
    # Policy matrix bindings
    matrix_bindings: List[Dict] = field(default_factory=list)
    
    # Cisco CLI configuration
    cisco_cli_config: str = ""
    
    # ISE ERS API payloads
    ise_api_payloads: Dict[str, List[Dict]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export."""
        return {
            "metadata": {
                "generated_at": self.generated_at.isoformat(),
                "clarion_version": self.clarion_version,
            },
            "sgt_definitions": self.sgt_definitions,
            "sgacl_definitions": self.sgacl_definitions,
            "matrix_bindings": self.matrix_bindings,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Export as JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def save(self, base_path: str) -> List[str]:
        """
        Save all export artifacts to files.
        
        Args:
            base_path: Base path for output files
            
        Returns:
            List of created file paths
        """
        import os
        
        created_files = []
        os.makedirs(base_path, exist_ok=True)
        
        # Save JSON export
        json_path = os.path.join(base_path, "clarion_policy_export.json")
        with open(json_path, "w") as f:
            f.write(self.to_json())
        created_files.append(json_path)
        
        # Save Cisco CLI config
        if self.cisco_cli_config:
            cli_path = os.path.join(base_path, "cisco_cli_config.txt")
            with open(cli_path, "w") as f:
                f.write(self.cisco_cli_config)
            created_files.append(cli_path)
        
        # Save ISE API payloads
        for api_type, payloads in self.ise_api_payloads.items():
            api_path = os.path.join(base_path, f"ise_api_{api_type}.json")
            with open(api_path, "w") as f:
                json.dump(payloads, f, indent=2)
            created_files.append(api_path)
        
        logger.info(f"Saved {len(created_files)} export files to {base_path}")
        return created_files


class ISEExporter:
    """
    Export policies in Cisco ISE-compatible formats.
    
    Generates:
    - Cisco CLI configuration for direct switch deployment
    - ISE ERS API payloads for programmatic import
    - JSON export for backup/documentation
    
    Example:
        >>> exporter = ISEExporter()
        >>> export = exporter.export(taxonomy, policies, matrix)
        >>> export.save("./policy_export")
    """
    
    def __init__(
        self,
        include_comments: bool = True,
        ise_version: str = "3.1",
    ):
        """
        Initialize the exporter.
        
        Args:
            include_comments: Include descriptive comments in CLI config
            ise_version: Target ISE version for API payloads
        """
        self.include_comments = include_comments
        self.ise_version = ise_version
    
    def export(
        self,
        taxonomy: SGTTaxonomy,
        policies: List[SGACLPolicy],
        matrix: Optional[PolicyMatrix] = None,
        impact_report: Optional[ImpactReport] = None,
    ) -> PolicyExport:
        """
        Create a complete policy export.
        
        Args:
            taxonomy: SGT taxonomy with recommendations
            policies: List of SGACL policies
            matrix: Optional policy matrix for additional context
            impact_report: Optional impact analysis
            
        Returns:
            PolicyExport with all artifacts
        """
        logger.info("Exporting policies to ISE-compatible format")
        
        export = PolicyExport()
        
        # Generate SGT definitions
        export.sgt_definitions = self._export_sgts(taxonomy)
        
        # Generate SGACL definitions
        export.sgacl_definitions = self._export_sgacls(policies)
        
        # Generate matrix bindings
        export.matrix_bindings = self._export_bindings(policies)
        
        # Generate Cisco CLI config
        export.cisco_cli_config = self._generate_cli_config(
            taxonomy, policies, impact_report
        )
        
        # Generate ISE ERS API payloads
        export.ise_api_payloads = self._generate_api_payloads(
            taxonomy, policies
        )
        
        logger.info(
            f"Export complete: {len(export.sgt_definitions)} SGTs, "
            f"{len(export.sgacl_definitions)} SGACLs"
        )
        
        return export
    
    def _export_sgts(self, taxonomy: SGTTaxonomy) -> List[Dict]:
        """Export SGT definitions."""
        sgts = []
        
        for rec in taxonomy.recommendations:
            sgts.append({
                "name": rec.sgt_name,
                "value": rec.sgt_value,
                "description": f"Auto-generated from cluster analysis. {rec.justification}",
                "isReadOnly": False,
            })
        
        return sgts
    
    def _export_sgacls(self, policies: List[SGACLPolicy]) -> List[Dict]:
        """Export SGACL definitions."""
        sgacls = []
        
        for policy in policies:
            # Build ACL content
            acl_content = []
            for rule in policy.rules:
                acl_content.append(rule.to_cisco_syntax())
            
            sgacls.append({
                "name": policy.name,
                "description": f"SGACL for {policy.src_sgt_name} to {policy.dst_sgt_name}",
                "aclcontent": "\n".join(acl_content),
                "ipVersion": "IP_AGNOSTIC",
            })
        
        return sgacls
    
    def _export_bindings(self, policies: List[SGACLPolicy]) -> List[Dict]:
        """Export SGT-to-SGACL bindings."""
        bindings = []
        
        for policy in policies:
            bindings.append({
                "sourceSgtName": policy.src_sgt_name,
                "sourceSgtValue": policy.src_sgt,
                "destinationSgtName": policy.dst_sgt_name,
                "destinationSgtValue": policy.dst_sgt,
                "sgaclName": policy.name,
                "status": "ENABLED",
            })
        
        return bindings
    
    def _generate_cli_config(
        self,
        taxonomy: SGTTaxonomy,
        policies: List[SGACLPolicy],
        impact_report: Optional[ImpactReport],
    ) -> str:
        """Generate Cisco CLI configuration."""
        lines = []
        
        # Header
        lines.extend([
            "!" + "=" * 60,
            "! Clarion TrustSec Policy Configuration",
            f"! Generated: {datetime.now().isoformat()}",
            "!" + "=" * 60,
            "",
        ])
        
        # Impact warning if applicable
        if impact_report and impact_report.has_critical_issues():
            lines.extend([
                "! WARNING: Critical blocking issues detected!",
                f"! {impact_report.critical_blocks} critical ports would be blocked",
                "! Review impact report before deployment",
                "",
            ])
        
        # SGT definitions
        if self.include_comments:
            lines.append("! ===== SGT Definitions =====")
        
        for rec in taxonomy.recommendations:
            if self.include_comments:
                lines.append(f"! SGT {rec.sgt_value}: {rec.justification[:60]}")
            lines.append(f"cts role-based sgt-map {rec.sgt_value} sgt-name {rec.sgt_name}")
        
        lines.append("")
        
        # SGACL definitions
        if self.include_comments:
            lines.append("! ===== SGACL Definitions =====")
        
        for policy in policies:
            lines.append("")
            lines.append(policy.to_cisco_syntax())
        
        lines.append("")
        
        # Role-based permissions (matrix bindings)
        if self.include_comments:
            lines.append("! ===== Role-Based Permissions =====")
        
        for policy in policies:
            lines.append(
                f"cts role-based permissions from {policy.src_sgt} to {policy.dst_sgt} "
                f"{policy.name}"
            )
        
        lines.extend([
            "",
            "! ===== End of Configuration =====",
        ])
        
        return "\n".join(lines)
    
    def _generate_api_payloads(
        self,
        taxonomy: SGTTaxonomy,
        policies: List[SGACLPolicy],
    ) -> Dict[str, List[Dict]]:
        """Generate ISE ERS API payloads."""
        payloads = {}
        
        # SGT creation payloads
        payloads["sgt"] = []
        for rec in taxonomy.recommendations:
            payloads["sgt"].append({
                "Sgt": {
                    "name": rec.sgt_name,
                    "value": rec.sgt_value,
                    "description": rec.justification[:256],
                    "propogateToApic": False,
                }
            })
        
        # SGACL creation payloads
        payloads["sgacl"] = []
        for policy in policies:
            acl_lines = [rule.to_cisco_syntax() for rule in policy.rules]
            payloads["sgacl"].append({
                "Sgacl": {
                    "name": policy.name,
                    "description": f"SGACL for {policy.src_sgt_name} to {policy.dst_sgt_name}",
                    "aclcontent": "\n".join(acl_lines),
                    "ipVersion": "IP_AGNOSTIC",
                }
            })
        
        # SGACL mapping payloads
        payloads["egressmatrixcell"] = []
        for policy in policies:
            payloads["egressmatrixcell"].append({
                "EgressMatrixCell": {
                    "sourceSgtId": str(policy.src_sgt),
                    "destinationSgtId": str(policy.dst_sgt),
                    "sgacls": [policy.name],
                    "status": "ENABLED",
                }
            })
        
        return payloads
    
    def generate_deployment_guide(
        self,
        export: PolicyExport,
        impact_report: Optional[ImpactReport] = None,
    ) -> str:
        """Generate a deployment guide document."""
        lines = [
            "# Clarion Policy Deployment Guide",
            "",
            f"Generated: {export.generated_at.isoformat()}",
            "",
            "## Summary",
            "",
            f"- **SGT Definitions:** {len(export.sgt_definitions)}",
            f"- **SGACL Policies:** {len(export.sgacl_definitions)}",
            f"- **Matrix Bindings:** {len(export.matrix_bindings)}",
            "",
        ]
        
        if impact_report:
            lines.extend([
                "## Impact Analysis",
                "",
                f"- **Traffic Permitted:** {impact_report.permit_ratio()*100:.1f}%",
                f"- **Traffic Blocked:** {impact_report.block_ratio()*100:.1f}%",
                f"- **Critical Issues:** {impact_report.critical_blocks}",
                "",
            ])
            
            if impact_report.has_critical_issues():
                lines.extend([
                    "### ⚠️ Critical Issues Detected",
                    "",
                    "The following traffic would be blocked by these policies:",
                    "",
                ])
                
                for blocked in impact_report.blocked_traffic[:10]:
                    if blocked.risk_level == "critical":
                        lines.append(
                            f"- **{blocked.src_sgt_name}** → **{blocked.dst_sgt_name}** "
                            f"on {blocked.port}: {blocked.flow_count} flows"
                        )
                
                lines.append("")
        
        lines.extend([
            "## Deployment Steps",
            "",
            "### Option 1: Cisco CLI",
            "",
            "1. Copy the contents of `cisco_cli_config.txt`",
            "2. Apply to ISE Policy Administration Node",
            "3. Push to network devices",
            "",
            "### Option 2: ISE ERS API",
            "",
            "1. Use `ise_api_sgt.json` to create SGTs",
            "2. Use `ise_api_sgacl.json` to create SGACLs",
            "3. Use `ise_api_egressmatrixcell.json` to create bindings",
            "",
            "### Recommended Deployment Approach",
            "",
            "1. **Monitor Mode First:** Deploy SGACLs in monitor mode",
            "2. **Analyze Logs:** Review SGACL hit counters for 1-2 weeks",
            "3. **Refine Policies:** Add any missing permit rules",
            "4. **Enforce Gradually:** Enable enforcement per SGT pair",
            "",
        ])
        
        return "\n".join(lines)


