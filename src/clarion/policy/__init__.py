"""
Clarion Policy Module

Policy generation from observed traffic patterns.

Key components:
- PolicyMatrix: SGT → SGT communication matrix
- SGACLGenerator: Generate SGACL rules from traffic
- ImpactAnalyzer: Analyze policy enforcement impact
- ISEExporter: Export policies in ISE-ready format
"""

from clarion.policy.matrix import PolicyMatrix, MatrixCell, build_policy_matrix
from clarion.policy.sgacl import SGACLGenerator, SGACLRule, SGACLPolicy
from clarion.policy.impact import ImpactAnalyzer, ImpactReport
from clarion.policy.exporter import ISEExporter, PolicyExport

__all__ = [
    "PolicyMatrix",
    "MatrixCell",
    "build_policy_matrix",
    "SGACLGenerator",
    "SGACLRule",
    "SGACLPolicy",
    "ImpactAnalyzer",
    "ImpactReport",
    "ISEExporter",
    "PolicyExport",
]

