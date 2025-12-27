"""
SGACL Generator - Generate Security Group ACL rules.

Creates SGACL rules from observed traffic patterns in the policy matrix.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import logging

from clarion.policy.matrix import PolicyMatrix, MatrixCell

logger = logging.getLogger(__name__)


@dataclass
class SGACLRule:
    """
    A single SGACL rule (ACE - Access Control Entry).
    
    Attributes:
        action: permit or deny
        protocol: tcp, udp, ip, icmp
        port: destination port (None for all)
        source_port: source port (None for all)
        log: whether to log matches
    """
    action: str  # "permit" or "deny"
    protocol: str  # "tcp", "udp", "ip", "icmp"
    port: Optional[int] = None  # dst port
    source_port: Optional[int] = None
    log: bool = False
    
    # Metadata
    flow_count: int = 0  # Flows that matched this pattern
    confidence: float = 1.0
    
    def to_cisco_syntax(self) -> str:
        """Generate Cisco IOS SGACL syntax."""
        parts = [self.action, self.protocol]
        
        if self.port:
            parts.append(f"dst eq {self.port}")
        
        if self.log:
            parts.append("log")
        
        return " ".join(parts)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "action": self.action,
            "protocol": self.protocol,
            "port": self.port,
            "source_port": self.source_port,
            "log": self.log,
            "flow_count": self.flow_count,
            "confidence": self.confidence,
            "cisco_syntax": self.to_cisco_syntax(),
        }


@dataclass
class SGACLPolicy:
    """
    Complete SGACL policy for an SGT pair.
    
    Contains ordered list of rules (first match wins).
    """
    name: str
    src_sgt: int
    src_sgt_name: str
    dst_sgt: int
    dst_sgt_name: str
    
    rules: List[SGACLRule] = field(default_factory=list)
    
    # Policy metadata
    total_observed_flows: int = 0
    covered_flows: int = 0
    default_action: str = "deny"
    
    def add_rule(self, rule: SGACLRule) -> None:
        """Add a rule to the policy."""
        self.rules.append(rule)
    
    def coverage_ratio(self) -> float:
        """Calculate what percentage of observed flows are covered by permit rules."""
        if self.total_observed_flows == 0:
            return 0.0
        return self.covered_flows / self.total_observed_flows
    
    def to_cisco_syntax(self) -> str:
        """Generate complete Cisco SGACL configuration."""
        lines = [
            f"! SGACL: {self.name}",
            f"! Source: SGT {self.src_sgt} ({self.src_sgt_name})",
            f"! Destination: SGT {self.dst_sgt} ({self.dst_sgt_name})",
            f"cts role-based permissions from {self.src_sgt} to {self.dst_sgt}",
            f"ip access-list role-based {self.name}",
        ]
        
        for rule in self.rules:
            lines.append(f"  {rule.to_cisco_syntax()}")
        
        # Add default deny if not already present
        if not any(r.action == "deny" and r.protocol == "ip" for r in self.rules):
            log_suffix = " log" if self.default_action == "deny" else ""
            lines.append(f"  {self.default_action} ip{log_suffix}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "src_sgt": self.src_sgt,
            "src_sgt_name": self.src_sgt_name,
            "dst_sgt": self.dst_sgt,
            "dst_sgt_name": self.dst_sgt_name,
            "rules": [r.to_dict() for r in self.rules],
            "total_observed_flows": self.total_observed_flows,
            "covered_flows": self.covered_flows,
            "coverage_ratio": self.coverage_ratio(),
            "default_action": self.default_action,
        }


class SGACLGenerator:
    """
    Generate SGACL policies from a policy matrix.
    
    Creates permit rules for observed traffic patterns and
    deny rules for everything else.
    
    Example:
        >>> generator = SGACLGenerator()
        >>> policies = generator.generate(matrix)
        >>> for policy in policies:
        ...     print(policy.to_cisco_syntax())
    """
    
    # Well-known ports that should use service names
    PORT_NAMES = {
        22: "ssh",
        25: "smtp",
        53: "dns",
        80: "http",
        88: "kerberos",
        110: "pop3",
        123: "ntp",
        135: "msrpc",
        143: "imap",
        161: "snmp",
        389: "ldap",
        443: "https",
        445: "smb",
        464: "kpasswd",
        465: "smtps",
        587: "submission",
        636: "ldaps",
        993: "imaps",
        995: "pop3s",
        1433: "mssql",
        1521: "oracle",
        3306: "mysql",
        3389: "rdp",
        5432: "postgresql",
        8080: "http-alt",
        8443: "https-alt",
    }
    
    def __init__(
        self,
        min_flow_count: int = 10,
        min_flow_ratio: float = 0.01,
        consolidate_ports: bool = True,
        add_logging: bool = True,
    ):
        """
        Initialize the generator.
        
        Args:
            min_flow_count: Minimum flows to create a permit rule
            min_flow_ratio: Minimum ratio of total flows for a port
            consolidate_ports: Group similar ports into ranges
            add_logging: Add log keyword to deny rules
        """
        self.min_flow_count = min_flow_count
        self.min_flow_ratio = min_flow_ratio
        self.consolidate_ports = consolidate_ports
        self.add_logging = add_logging
    
    def generate(self, matrix: PolicyMatrix) -> List[SGACLPolicy]:
        """
        Generate SGACL policies for all matrix cells.
        
        Args:
            matrix: PolicyMatrix with observed traffic
            
        Returns:
            List of SGACLPolicy objects
        """
        logger.info(f"Generating SGACLs for {matrix.n_cells} matrix cells")
        
        policies = []
        
        for (src_sgt, dst_sgt), cell in matrix.cells.items():
            policy = self._generate_policy(cell)
            policies.append(policy)
        
        logger.info(f"Generated {len(policies)} SGACL policies")
        return policies
    
    def _generate_policy(self, cell: MatrixCell) -> SGACLPolicy:
        """Generate a policy for a single matrix cell."""
        # Generate policy name
        name = self._generate_name(cell.src_sgt_name, cell.dst_sgt_name)
        
        policy = SGACLPolicy(
            name=name,
            src_sgt=cell.src_sgt,
            src_sgt_name=cell.src_sgt_name,
            dst_sgt=cell.dst_sgt,
            dst_sgt_name=cell.dst_sgt_name,
            total_observed_flows=cell.total_flows,
        )
        
        # Generate permit rules for significant ports
        rules = self._generate_permit_rules(cell)
        
        for rule in rules:
            policy.add_rule(rule)
            policy.covered_flows += rule.flow_count
        
        # Add final deny
        deny_rule = SGACLRule(
            action="deny",
            protocol="ip",
            log=self.add_logging,
        )
        policy.add_rule(deny_rule)
        
        return policy
    
    def _generate_permit_rules(self, cell: MatrixCell) -> List[SGACLRule]:
        """Generate permit rules from observed ports."""
        rules = []
        
        # Group ports by protocol
        tcp_ports: Dict[int, int] = {}
        udp_ports: Dict[int, int] = {}
        
        for port_key, count in cell.observed_ports.items():
            parts = port_key.split("/")
            if len(parts) != 2:
                continue
            
            proto, port_str = parts
            try:
                port = int(port_str)
            except ValueError:
                continue
            
            if proto == "tcp":
                tcp_ports[port] = count
            elif proto == "udp":
                udp_ports[port] = count
        
        # Generate rules for significant TCP ports
        for port, count in sorted(tcp_ports.items(), key=lambda x: -x[1]):
            if self._is_significant(count, cell.total_flows):
                rules.append(SGACLRule(
                    action="permit",
                    protocol="tcp",
                    port=port,
                    flow_count=count,
                    confidence=count / cell.total_flows,
                ))
        
        # Generate rules for significant UDP ports
        for port, count in sorted(udp_ports.items(), key=lambda x: -x[1]):
            if self._is_significant(count, cell.total_flows):
                rules.append(SGACLRule(
                    action="permit",
                    protocol="udp",
                    port=port,
                    flow_count=count,
                    confidence=count / cell.total_flows,
                ))
        
        return rules
    
    def _is_significant(self, count: int, total: int) -> bool:
        """Check if a port has enough traffic to warrant a rule."""
        if count < self.min_flow_count:
            return False
        if total > 0 and count / total < self.min_flow_ratio:
            return False
        return True
    
    def _generate_name(self, src_name: str, dst_name: str) -> str:
        """Generate a policy name from SGT names."""
        # Clean up names for use in ACL names
        src_clean = self._sanitize_name(src_name)
        dst_clean = self._sanitize_name(dst_name)
        return f"SGACL_{src_clean}_to_{dst_clean}"
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize a name for use in Cisco ACL names."""
        # Replace spaces and special chars with underscores
        result = ""
        for c in name:
            if c.isalnum():
                result += c
            elif c in " -_":
                result += "_"
        # Remove consecutive underscores
        while "__" in result:
            result = result.replace("__", "_")
        return result.strip("_")
    
    def generate_summary(self, policies: List[SGACLPolicy]) -> str:
        """Generate a summary of all policies."""
        lines = [
            "=" * 60,
            "SGACL Policy Summary",
            "=" * 60,
            f"Total policies: {len(policies)}",
            f"Total rules: {sum(len(p.rules) for p in policies)}",
            "",
        ]
        
        for policy in sorted(policies, key=lambda p: (p.src_sgt, p.dst_sgt)):
            permit_count = sum(1 for r in policy.rules if r.action == "permit")
            lines.append(
                f"  {policy.src_sgt_name:20s} → {policy.dst_sgt_name:20s}: "
                f"{permit_count} permit rules, {policy.coverage_ratio()*100:.0f}% coverage"
            )
        
        return "\n".join(lines)


