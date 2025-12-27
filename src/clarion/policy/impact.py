"""
Impact Analyzer - Analyze policy enforcement impact.

Determines what traffic would be blocked if policies were enforced,
helping identify potential issues before deployment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import logging

from clarion.policy.matrix import PolicyMatrix, MatrixCell
from clarion.policy.sgacl import SGACLPolicy, SGACLRule

logger = logging.getLogger(__name__)


@dataclass
class BlockedTraffic:
    """
    Description of traffic that would be blocked.
    """
    src_sgt: int
    src_sgt_name: str
    dst_sgt: int
    dst_sgt_name: str
    
    # What would be blocked
    port: str  # "tcp/443"
    flow_count: int
    bytes_count: int
    
    # Context
    reason: str  # Why it's blocked
    risk_level: str  # "low", "medium", "high", "critical"
    recommendation: str


@dataclass
class ImpactReport:
    """
    Complete impact analysis report.
    """
    # Summary
    total_flows_analyzed: int = 0
    flows_permitted: int = 0
    flows_blocked: int = 0
    
    # Blocked traffic details
    blocked_traffic: List[BlockedTraffic] = field(default_factory=list)
    
    # Risk breakdown
    critical_blocks: int = 0
    high_risk_blocks: int = 0
    medium_risk_blocks: int = 0
    low_risk_blocks: int = 0
    
    # Affected entities
    affected_src_sgts: Set[int] = field(default_factory=set)
    affected_dst_sgts: Set[int] = field(default_factory=set)
    
    def permit_ratio(self) -> float:
        """Percentage of traffic that would be permitted."""
        if self.total_flows_analyzed == 0:
            return 1.0
        return self.flows_permitted / self.total_flows_analyzed
    
    def block_ratio(self) -> float:
        """Percentage of traffic that would be blocked."""
        return 1.0 - self.permit_ratio()
    
    def has_critical_issues(self) -> bool:
        """Check if there are critical blocking issues."""
        return self.critical_blocks > 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "total_flows_analyzed": self.total_flows_analyzed,
            "flows_permitted": self.flows_permitted,
            "flows_blocked": self.flows_blocked,
            "permit_ratio": self.permit_ratio(),
            "block_ratio": self.block_ratio(),
            "blocked_traffic": [
                {
                    "src_sgt": b.src_sgt,
                    "dst_sgt": b.dst_sgt,
                    "port": b.port,
                    "flow_count": b.flow_count,
                    "risk_level": b.risk_level,
                    "reason": b.reason,
                }
                for b in self.blocked_traffic
            ],
            "risk_breakdown": {
                "critical": self.critical_blocks,
                "high": self.high_risk_blocks,
                "medium": self.medium_risk_blocks,
                "low": self.low_risk_blocks,
            },
            "affected_sgts": {
                "sources": list(self.affected_src_sgts),
                "destinations": list(self.affected_dst_sgts),
            },
        }
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            "=" * 60,
            "Policy Impact Analysis",
            "=" * 60,
            f"Total flows analyzed: {self.total_flows_analyzed:,}",
            f"Flows permitted:      {self.flows_permitted:,} ({self.permit_ratio()*100:.1f}%)",
            f"Flows blocked:        {self.flows_blocked:,} ({self.block_ratio()*100:.1f}%)",
            "",
            "Risk Breakdown:",
            f"  Critical: {self.critical_blocks}",
            f"  High:     {self.high_risk_blocks}",
            f"  Medium:   {self.medium_risk_blocks}",
            f"  Low:      {self.low_risk_blocks}",
        ]
        
        if self.blocked_traffic:
            lines.extend([
                "",
                "Top Blocked Traffic:",
            ])
            
            # Sort by flow count
            top_blocked = sorted(
                self.blocked_traffic,
                key=lambda b: -b.flow_count
            )[:10]
            
            for b in top_blocked:
                lines.append(
                    f"  {b.src_sgt_name} → {b.dst_sgt_name} {b.port}: "
                    f"{b.flow_count} flows [{b.risk_level}]"
                )
        
        return "\n".join(lines)


class ImpactAnalyzer:
    """
    Analyze the impact of enforcing SGACL policies.
    
    Compares proposed policies against observed traffic to identify
    what would be blocked if policies were enforced.
    
    Example:
        >>> analyzer = ImpactAnalyzer()
        >>> report = analyzer.analyze(matrix, policies)
        >>> print(report.summary())
    """
    
    # Critical ports that should almost never be blocked
    CRITICAL_PORTS = {
        53: "DNS",
        88: "Kerberos",
        123: "NTP",
        389: "LDAP",
        443: "HTTPS",
        636: "LDAPS",
    }
    
    # High importance ports
    HIGH_IMPORTANCE_PORTS = {
        22: "SSH",
        80: "HTTP",
        445: "SMB",
        464: "Kerberos Password",
        3389: "RDP",
    }
    
    def __init__(
        self,
        critical_flow_threshold: int = 100,
        high_flow_threshold: int = 50,
    ):
        """
        Initialize the analyzer.
        
        Args:
            critical_flow_threshold: Flows above this are critical if blocked
            high_flow_threshold: Flows above this are high risk if blocked
        """
        self.critical_flow_threshold = critical_flow_threshold
        self.high_flow_threshold = high_flow_threshold
    
    def analyze(
        self,
        matrix: PolicyMatrix,
        policies: List[SGACLPolicy],
    ) -> ImpactReport:
        """
        Analyze policy impact.
        
        Args:
            matrix: Policy matrix with observed traffic
            policies: List of proposed SGACL policies
            
        Returns:
            ImpactReport with analysis results
        """
        logger.info("Analyzing policy enforcement impact")
        
        report = ImpactReport()
        
        # Build policy lookup
        policy_lookup: Dict[Tuple[int, int], SGACLPolicy] = {}
        for policy in policies:
            key = (policy.src_sgt, policy.dst_sgt)
            policy_lookup[key] = policy
        
        # Analyze each matrix cell
        for (src_sgt, dst_sgt), cell in matrix.cells.items():
            policy = policy_lookup.get((src_sgt, dst_sgt))
            
            if policy is None:
                # No policy = all blocked (default deny)
                self._analyze_all_blocked(cell, report)
            else:
                # Check what's permitted vs blocked
                self._analyze_with_policy(cell, policy, report)
        
        logger.info(
            f"Impact analysis complete: {report.permit_ratio()*100:.1f}% permitted, "
            f"{report.critical_blocks} critical blocks"
        )
        
        return report
    
    def _analyze_all_blocked(
        self,
        cell: MatrixCell,
        report: ImpactReport,
    ) -> None:
        """Handle case where no policy exists (all blocked)."""
        report.total_flows_analyzed += cell.total_flows
        report.flows_blocked += cell.total_flows
        report.affected_src_sgts.add(cell.src_sgt)
        report.affected_dst_sgts.add(cell.dst_sgt)
        
        # Create blocked traffic entries for top ports
        for port_key, count in cell.top_ports(5):
            blocked = self._create_blocked_traffic(
                cell, port_key, count, cell.total_bytes // max(len(cell.observed_ports), 1),
                "No SGACL policy defined for this SGT pair"
            )
            report.blocked_traffic.append(blocked)
            self._update_risk_counts(report, blocked.risk_level)
    
    def _analyze_with_policy(
        self,
        cell: MatrixCell,
        policy: SGACLPolicy,
        report: ImpactReport,
    ) -> None:
        """Analyze traffic against an existing policy."""
        report.total_flows_analyzed += cell.total_flows
        
        # Build set of permitted ports
        permitted_ports: Set[str] = set()
        for rule in policy.rules:
            if rule.action == "permit" and rule.port:
                permitted_ports.add(f"{rule.protocol}/{rule.port}")
        
        # Check each observed port
        for port_key, count in cell.observed_ports.items():
            if port_key in permitted_ports:
                report.flows_permitted += count
            else:
                report.flows_blocked += count
                report.affected_src_sgts.add(cell.src_sgt)
                report.affected_dst_sgts.add(cell.dst_sgt)
                
                # Create blocked traffic entry
                blocked = self._create_blocked_traffic(
                    cell, port_key, count, 
                    cell.total_bytes * count // max(cell.total_flows, 1),
                    f"Port {port_key} not in SGACL permit list"
                )
                report.blocked_traffic.append(blocked)
                self._update_risk_counts(report, blocked.risk_level)
    
    def _create_blocked_traffic(
        self,
        cell: MatrixCell,
        port_key: str,
        flow_count: int,
        bytes_count: int,
        reason: str,
    ) -> BlockedTraffic:
        """Create a BlockedTraffic entry."""
        # Determine risk level
        risk_level = self._assess_risk(port_key, flow_count)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(port_key, risk_level)
        
        return BlockedTraffic(
            src_sgt=cell.src_sgt,
            src_sgt_name=cell.src_sgt_name,
            dst_sgt=cell.dst_sgt,
            dst_sgt_name=cell.dst_sgt_name,
            port=port_key,
            flow_count=flow_count,
            bytes_count=bytes_count,
            reason=reason,
            risk_level=risk_level,
            recommendation=recommendation,
        )
    
    def _assess_risk(self, port_key: str, flow_count: int) -> str:
        """Assess the risk level of blocking this traffic."""
        # Parse port
        parts = port_key.split("/")
        if len(parts) != 2:
            return "low"
        
        try:
            port = int(parts[1])
        except ValueError:
            return "low"
        
        # Check critical ports
        if port in self.CRITICAL_PORTS:
            return "critical"
        
        # Check high importance ports
        if port in self.HIGH_IMPORTANCE_PORTS:
            if flow_count >= self.high_flow_threshold:
                return "high"
            return "medium"
        
        # Check flow volume
        if flow_count >= self.critical_flow_threshold:
            return "high"
        if flow_count >= self.high_flow_threshold:
            return "medium"
        
        return "low"
    
    def _generate_recommendation(self, port_key: str, risk_level: str) -> str:
        """Generate a recommendation for blocked traffic."""
        if risk_level == "critical":
            return f"CRITICAL: Add permit rule for {port_key} - likely required for core services"
        if risk_level == "high":
            return f"Review and add permit rule for {port_key} if business-justified"
        if risk_level == "medium":
            return f"Consider adding permit rule for {port_key}"
        return f"Low-risk block - verify {port_key} is not needed"
    
    def _update_risk_counts(self, report: ImpactReport, risk_level: str) -> None:
        """Update risk counts in the report."""
        if risk_level == "critical":
            report.critical_blocks += 1
        elif risk_level == "high":
            report.high_risk_blocks += 1
        elif risk_level == "medium":
            report.medium_risk_blocks += 1
        else:
            report.low_risk_blocks += 1


