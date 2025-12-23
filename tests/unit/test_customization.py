"""
Unit tests for the Policy Customization module.

Tests:
- SGTCustomization
- PolicyCustomization
- CustomizationSession
- PolicyCustomizer
- Persistence (save/load)
"""

import pytest
import tempfile
import os
from datetime import datetime

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
from clarion.policy.sgacl import SGACLRule, SGACLPolicy
from clarion.clustering.sgt_mapper import SGTRecommendation, SGTTaxonomy


class TestSGTCustomization:
    """Tests for SGTCustomization."""
    
    def test_create_from_recommendation(self):
        """Test creating customization from recommendation."""
        rec = SGTRecommendation(
            cluster_id=0,
            sgt_value=100,
            sgt_name="Employees",
            cluster_label="Employee Workstations",
            cluster_size=50,
            confidence=0.9,
            justification="Based on AD group membership",
            endpoint_count=50,
        )
        
        custom = SGTCustomization.from_recommendation(rec)
        
        assert custom.original_cluster_id == 0
        assert custom.original_sgt_value == 100
        assert custom.original_sgt_name == "Employees"
        assert custom.sgt_value == 100
        assert custom.sgt_name == "Employees"
        assert custom.status == ApprovalStatus.PENDING
        assert not custom.is_modified
    
    def test_rename(self):
        """Test renaming an SGT."""
        custom = SGTCustomization(
            original_cluster_id=0,
            original_sgt_value=100,
            original_sgt_name="Employees",
            sgt_value=100,
            sgt_name="Employees",
        )
        
        custom.rename("Corp-Employees", modified_by="admin")
        
        assert custom.sgt_name == "Corp-Employees"
        assert custom.status == ApprovalStatus.MODIFIED
        assert custom.modified_by == "admin"
        assert custom.is_modified
    
    def test_reassign_value(self):
        """Test reassigning SGT value."""
        custom = SGTCustomization(
            original_cluster_id=0,
            original_sgt_value=100,
            original_sgt_name="Employees",
            sgt_value=100,
            sgt_name="Employees",
        )
        
        custom.reassign_value(150, modified_by="admin")
        
        assert custom.sgt_value == 150
        assert custom.status == ApprovalStatus.MODIFIED
        assert custom.is_modified
    
    def test_approve(self):
        """Test approving a recommendation."""
        custom = SGTCustomization(
            original_cluster_id=0,
            original_sgt_value=100,
            original_sgt_name="Employees",
            sgt_value=100,
            sgt_name="Employees",
        )
        
        custom.approve(modified_by="security_team", comment="Looks good")
        
        assert custom.status == ApprovalStatus.APPROVED
        assert "Looks good" in custom.comments
    
    def test_reject(self):
        """Test rejecting a recommendation."""
        custom = SGTCustomization(
            original_cluster_id=0,
            original_sgt_value=100,
            original_sgt_name="Employees",
            sgt_value=100,
            sgt_name="Employees",
        )
        
        custom.reject(modified_by="security_team", reason="Too broad")
        
        assert custom.status == ApprovalStatus.REJECTED
        assert any("Too broad" in c for c in custom.comments)
    
    def test_to_dict(self):
        """Test dictionary conversion."""
        custom = SGTCustomization(
            original_cluster_id=0,
            original_sgt_value=100,
            original_sgt_name="Employees",
            sgt_value=150,
            sgt_name="Corp-Employees",
        )
        
        d = custom.to_dict()
        
        assert d["original_sgt_value"] == 100
        assert d["sgt_value"] == 150
        assert d["sgt_name"] == "Corp-Employees"
        assert d["is_modified"] == True


class TestPolicyCustomization:
    """Tests for PolicyCustomization."""
    
    def test_add_permit_rule(self):
        """Test adding a permit rule."""
        custom = PolicyCustomization(
            policy_name="SGACL_Test",
            src_sgt=100,
            dst_sgt=200,
        )
        
        custom.add_permit_rule(
            protocol="tcp",
            port=8443,
            reason="Required for internal app",
            added_by="admin",
        )
        
        assert len(custom.rule_changes) == 1
        change = custom.rule_changes[0]
        assert change.action == "add"
        assert change.rule.action == "permit"
        assert change.rule.port == 8443
        assert change.reason == "Required for internal app"
    
    def test_remove_rule(self):
        """Test marking a rule for removal."""
        custom = PolicyCustomization(
            policy_name="SGACL_Test",
            src_sgt=100,
            dst_sgt=200,
        )
        
        custom.remove_rule(
            protocol="tcp",
            port=23,
            reason="Telnet not allowed",
            added_by="security",
        )
        
        assert len(custom.rule_changes) == 1
        change = custom.rule_changes[0]
        assert change.action == "remove"
    
    def test_add_deny_rule(self):
        """Test adding an explicit deny rule."""
        custom = PolicyCustomization(
            policy_name="SGACL_Test",
            src_sgt=100,
            dst_sgt=200,
        )
        
        custom.add_deny_rule(
            protocol="tcp",
            port=22,
            reason="Block SSH explicitly",
        )
        
        assert len(custom.rule_changes) == 1
        change = custom.rule_changes[0]
        assert change.action == "add"
        assert change.rule.action == "deny"
        assert change.rule.log == True


class TestCustomizationSession:
    """Tests for CustomizationSession."""
    
    @pytest.fixture
    def sample_taxonomy(self) -> SGTTaxonomy:
        """Create sample taxonomy for testing."""
        return SGTTaxonomy(
            recommendations=[
                SGTRecommendation(
                    cluster_id=0,
                    sgt_value=100,
                    sgt_name="Employees",
                    cluster_label="Employees",
                    cluster_size=50,
                    confidence=0.9,
                    justification="Employee workstations",
                    endpoint_count=50,
                ),
                SGTRecommendation(
                    cluster_id=1,
                    sgt_value=200,
                    sgt_name="Servers",
                    cluster_label="Servers",
                    cluster_size=20,
                    confidence=0.95,
                    justification="Server infrastructure",
                    endpoint_count=20,
                ),
                SGTRecommendation(
                    cluster_id=2,
                    sgt_value=300,
                    sgt_name="IoT_Devices",
                    cluster_label="IoT",
                    cluster_size=30,
                    confidence=0.85,
                    justification="IoT devices",
                    endpoint_count=30,
                ),
            ],
            total_endpoints=100,
        )
    
    def test_create_session(self):
        """Test creating a session."""
        session = CustomizationSession(
            session_id="test-001",
            created_by="admin",
        )
        
        assert session.session_id == "test-001"
        assert session.created_by == "admin"
        assert len(session.reserved_sgt_values) > 0
    
    def test_add_sgt_customization(self, sample_taxonomy):
        """Test adding SGT customizations."""
        session = create_review_session(sample_taxonomy, "test-001")
        
        assert len(session.sgt_customizations) == 3
        assert 0 in session.sgt_customizations
        assert session.sgt_customizations[0].sgt_name == "Employees"
    
    def test_rename_sgt(self, sample_taxonomy):
        """Test renaming an SGT in session."""
        session = create_review_session(sample_taxonomy, "test-001")
        
        result = session.rename_sgt(0, "Corp-Employees", "admin")
        
        assert result == True
        assert session.sgt_customizations[0].sgt_name == "Corp-Employees"
    
    def test_reassign_sgt_value(self, sample_taxonomy):
        """Test reassigning SGT value."""
        session = create_review_session(sample_taxonomy, "test-001")
        
        result = session.reassign_sgt_value(0, 150, "admin")
        
        assert result == True
        assert session.sgt_customizations[0].sgt_value == 150
    
    def test_reassign_reserved_value_fails(self, sample_taxonomy):
        """Test that reserved values can't be assigned."""
        session = create_review_session(sample_taxonomy, "test-001")
        
        result = session.reassign_sgt_value(0, 0, "admin")  # 0 is reserved
        
        assert result == False
        assert session.sgt_customizations[0].sgt_value == 100  # Unchanged
    
    def test_reassign_duplicate_value_fails(self, sample_taxonomy):
        """Test that duplicate values can't be assigned."""
        session = create_review_session(sample_taxonomy, "test-001")
        
        result = session.reassign_sgt_value(0, 200, "admin")  # 200 is already used
        
        assert result == False
    
    def test_merge_clusters(self, sample_taxonomy):
        """Test merging clusters."""
        session = create_review_session(sample_taxonomy, "test-001")
        
        result = session.merge_clusters(2, 1, "admin")  # Merge IoT into Servers
        
        assert result == True
        assert session.sgt_customizations[2].merged_into == 1
    
    def test_approve_sgt(self, sample_taxonomy):
        """Test approving an SGT."""
        session = create_review_session(sample_taxonomy, "test-001")
        
        result = session.approve_sgt(0, "admin", "Approved for production")
        
        assert result == True
        assert session.sgt_customizations[0].status == ApprovalStatus.APPROVED
    
    def test_reject_sgt(self, sample_taxonomy):
        """Test rejecting an SGT."""
        session = create_review_session(sample_taxonomy, "test-001")
        
        result = session.reject_sgt(0, "admin", "Too broad")
        
        assert result == True
        assert session.sgt_customizations[0].status == ApprovalStatus.REJECTED
    
    def test_approve_all_pending(self, sample_taxonomy):
        """Test approving all pending SGTs."""
        session = create_review_session(sample_taxonomy, "test-001")
        
        # Reject one first
        session.reject_sgt(2)
        
        count = session.approve_all_pending("admin")
        
        assert count == 2  # Two were pending
        assert session.sgt_customizations[0].status == ApprovalStatus.APPROVED
        assert session.sgt_customizations[1].status == ApprovalStatus.APPROVED
        assert session.sgt_customizations[2].status == ApprovalStatus.REJECTED  # Still rejected
    
    def test_add_permit_rule_via_session(self, sample_taxonomy):
        """Test adding a permit rule via session."""
        session = create_review_session(sample_taxonomy, "test-001")
        
        session.add_permit_rule(100, 200, "tcp", 8443, "Internal app")
        
        key = (100, 200)
        assert key in session.policy_customizations
        assert len(session.policy_customizations[key].rule_changes) == 1
    
    def test_summary(self, sample_taxonomy):
        """Test session summary."""
        session = create_review_session(sample_taxonomy, "test-001")
        session.approve_sgt(0)
        session.reject_sgt(1)
        
        summary = session.summary()
        
        assert summary["sgt_count"] == 3
        assert summary["sgt_status"]["approved"] == 1
        assert summary["sgt_status"]["rejected"] == 1
        assert summary["sgt_status"]["pending"] == 1


class TestSessionPersistence:
    """Tests for session save/load."""
    
    @pytest.fixture
    def sample_session(self) -> CustomizationSession:
        """Create a sample session with customizations."""
        session = CustomizationSession(
            session_id="test-persist",
            created_by="admin",
        )
        
        # Add SGT customization
        custom = SGTCustomization(
            original_cluster_id=0,
            original_sgt_value=100,
            original_sgt_name="Employees",
            sgt_value=150,
            sgt_name="Corp-Employees",
            status=ApprovalStatus.MODIFIED,
        )
        session.sgt_customizations[0] = custom
        
        # Add policy customization
        session.add_permit_rule(100, 200, "tcp", 8443, "Internal app", "admin")
        
        return session
    
    def test_save_and_load(self, sample_session):
        """Test saving and loading a session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "session.json")
            
            # Save
            sample_session.save(path)
            assert os.path.exists(path)
            
            # Load
            loaded = CustomizationSession.load(path)
            
            assert loaded.session_id == "test-persist"
            assert loaded.created_by == "admin"
            assert len(loaded.sgt_customizations) == 1
            assert loaded.sgt_customizations[0].sgt_name == "Corp-Employees"
            assert len(loaded.policy_customizations) == 1
    
    def test_to_dict(self, sample_session):
        """Test dictionary conversion."""
        d = sample_session.to_dict()
        
        assert "session_id" in d
        assert "sgt_customizations" in d
        assert "policy_customizations" in d


class TestPolicyCustomizer:
    """Tests for PolicyCustomizer."""
    
    @pytest.fixture
    def sample_taxonomy(self) -> SGTTaxonomy:
        """Create sample taxonomy."""
        return SGTTaxonomy(
            recommendations=[
                SGTRecommendation(
                    cluster_id=0,
                    sgt_value=100,
                    sgt_name="Employees",
                    cluster_label="Employees",
                    cluster_size=50,
                    confidence=0.9,
                    justification="Employee workstations",
                    endpoint_count=50,
                ),
                SGTRecommendation(
                    cluster_id=1,
                    sgt_value=200,
                    sgt_name="Servers",
                    cluster_label="Servers",
                    cluster_size=20,
                    confidence=0.95,
                    justification="Server infrastructure",
                    endpoint_count=20,
                ),
            ],
            total_endpoints=70,
        )
    
    @pytest.fixture
    def sample_policies(self) -> list:
        """Create sample policies."""
        policy = SGACLPolicy(
            name="SGACL_Employees_to_Servers",
            src_sgt=100,
            src_sgt_name="Employees",
            dst_sgt=200,
            dst_sgt_name="Servers",
        )
        policy.add_rule(SGACLRule(action="permit", protocol="tcp", port=443))
        policy.add_rule(SGACLRule(action="permit", protocol="tcp", port=80))
        policy.add_rule(SGACLRule(action="deny", protocol="ip"))
        return [policy]
    
    def test_apply_to_taxonomy_approved(self, sample_taxonomy):
        """Test applying customizations to taxonomy."""
        session = create_review_session(sample_taxonomy, "test")
        session.approve_all_pending()
        
        customizer = PolicyCustomizer(session)
        new_taxonomy = customizer.apply_to_taxonomy(sample_taxonomy)
        
        assert len(new_taxonomy.recommendations) == 2
    
    def test_apply_to_taxonomy_rejected(self, sample_taxonomy):
        """Test that rejected SGTs are excluded."""
        session = create_review_session(sample_taxonomy, "test")
        session.approve_sgt(0)
        session.reject_sgt(1, reason="Not needed")
        
        customizer = PolicyCustomizer(session)
        new_taxonomy = customizer.apply_to_taxonomy(sample_taxonomy)
        
        # Only approved SGT remains
        assert len(new_taxonomy.recommendations) == 1
        assert new_taxonomy.recommendations[0].sgt_name == "Employees"
    
    def test_apply_to_taxonomy_renamed(self, sample_taxonomy):
        """Test that renamed SGTs have new names."""
        session = create_review_session(sample_taxonomy, "test")
        session.rename_sgt(0, "Corp-Employees")
        session.approve_all_pending()
        
        customizer = PolicyCustomizer(session)
        new_taxonomy = customizer.apply_to_taxonomy(sample_taxonomy)
        
        emp = [r for r in new_taxonomy.recommendations if r.cluster_id == 0][0]
        assert emp.sgt_name == "Corp-Employees"
    
    def test_apply_to_policies_add_rule(self, sample_taxonomy, sample_policies):
        """Test adding a rule to a policy."""
        session = create_review_session(sample_taxonomy, "test")
        session.add_permit_rule(100, 200, "tcp", 8443, "Internal app")
        
        customizer = PolicyCustomizer(session)
        new_policies = customizer.apply_to_policies(sample_policies)
        
        # Should have one more permit rule
        permit_rules = [r for r in new_policies[0].rules if r.action == "permit"]
        assert len(permit_rules) == 3  # Original 2 + 1 new
    
    def test_apply_to_policies_remove_rule(self, sample_taxonomy, sample_policies):
        """Test removing a rule from a policy."""
        session = create_review_session(sample_taxonomy, "test")
        session.remove_permit_rule(100, 200, "tcp", 80, "Block HTTP")
        
        customizer = PolicyCustomizer(session)
        new_policies = customizer.apply_to_policies(sample_policies)
        
        # HTTP rule should be removed
        permit_rules = [r for r in new_policies[0].rules if r.action == "permit"]
        assert len(permit_rules) == 1  # Only 443 remains
        assert permit_rules[0].port == 443


class TestReviewReport:
    """Tests for review report generation."""
    
    def test_generate_report(self):
        """Test generating a review report."""
        session = CustomizationSession(
            session_id="test-report",
            created_by="admin",
        )
        
        # Add some customizations
        custom = SGTCustomization(
            original_cluster_id=0,
            original_sgt_value=100,
            original_sgt_name="Employees",
            sgt_value=150,
            sgt_name="Corp-Employees",
            status=ApprovalStatus.APPROVED,
        )
        session.sgt_customizations[0] = custom
        
        report = generate_review_report(session)
        
        assert "POLICY CUSTOMIZATION REVIEW REPORT" in report
        assert "test-report" in report
        assert "Corp-Employees" in report
        assert "✓" in report  # Approved indicator

