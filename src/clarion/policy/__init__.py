"""
Clarion Policy Module

Policy generation from observed traffic patterns.

Key components:
- PolicyMatrix: SGT → SGT communication matrix
- SGACLGenerator: Generate SGACL rules from traffic
- ImpactAnalyzer: Analyze policy enforcement impact
- ISEExporter: Export policies in ISE-ready format
- CustomizationSession: Human-in-the-loop review and modification
"""

from clarion.policy.matrix import PolicyMatrix, MatrixCell, build_policy_matrix
from clarion.policy.sgacl import SGACLGenerator, SGACLRule, SGACLPolicy
from clarion.policy.impact import ImpactAnalyzer, ImpactReport
from clarion.policy.exporter import ISEExporter, PolicyExport
from clarion.policy.customization import (
    ApprovalStatus,
    SGTCustomization,
    PolicyCustomization,
    RuleCustomization,
    CustomizationSession,
    PolicyCustomizer,
    create_review_session,
    generate_review_report,
)
from clarion.policy.recommendation import (
    PolicyCondition,
    PolicyRule,
    PolicyRecommendation,
    PolicyRecommendationEngine,
)
from clarion.policy.authorization_exporter import (
    ISEAuthorizationPolicyExporter,
    ISEAuthorizationPolicyExport,
)
from clarion.policy.user_sgt_recommendation import (
    UserSGTRecommendation,
    UserSGTRecommendationEngine,
    generate_user_sgt_recommendation,
)

__all__ = [
    # Matrix
    "PolicyMatrix",
    "MatrixCell",
    "build_policy_matrix",
    # SGACL
    "SGACLGenerator",
    "SGACLRule",
    "SGACLPolicy",
    # Impact
    "ImpactAnalyzer",
    "ImpactReport",
    # Export
    "ISEExporter",
    "PolicyExport",
    # Customization
    "ApprovalStatus",
    "SGTCustomization",
    "PolicyCustomization",
    "RuleCustomization",
    "CustomizationSession",
    "PolicyCustomizer",
    "create_review_session",
    "generate_review_report",
    # Recommendations
    "PolicyCondition",
    "PolicyRule",
    "PolicyRecommendation",
    "PolicyRecommendationEngine",
    # Authorization Export
    "ISEAuthorizationPolicyExporter",
    "ISEAuthorizationPolicyExport",
    # User SGT Recommendations
    "UserSGTRecommendation",
    "UserSGTRecommendationEngine",
    "generate_user_sgt_recommendation",
]

