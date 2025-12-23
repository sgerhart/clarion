"""
Unit tests for the Clarion Policy module.

Tests:
- PolicyMatrix and MatrixCell
- SGACLGenerator and SGACL rules
- ImpactAnalyzer
- ISEExporter
"""

import pytest
from datetime import datetime
from typing import List

from clarion.policy.matrix import PolicyMatrix, MatrixCell
from clarion.policy.sgacl import SGACLGenerator, SGACLRule, SGACLPolicy
from clarion.policy.impact import ImpactAnalyzer, ImpactReport, BlockedTraffic
from clarion.policy.exporter import ISEExporter, PolicyExport
from clarion.clustering.sgt_mapper import SGTTaxonomy, SGTRecommendation


class TestMatrixCell:
    """Tests for MatrixCell."""
    
    def test_cell_creation(self):
        """Test creating a matrix cell."""
        cell = MatrixCell(
            src_sgt=100,
            src_sgt_name="Employees",
            dst_sgt=200,
            dst_sgt_name="Servers",
        )
        
        assert cell.src_sgt == 100
        assert cell.dst_sgt == 200
        assert cell.total_flows == 0
        assert cell.total_bytes == 0
    
    def test_add_flow(self):
        """Test adding flows to a cell."""
        cell = MatrixCell(
            src_sgt=100,
            src_sgt_name="Employees",
            dst_sgt=200,
            dst_sgt_name="Servers",
        )
        
        cell.add_flow(port=443, proto="tcp", bytes_count=1000)
        cell.add_flow(port=443, proto="tcp", bytes_count=2000)
        cell.add_flow(port=80, proto="tcp", bytes_count=500)
        
        assert cell.total_flows == 3
        assert cell.total_bytes == 3500
        assert cell.observed_ports["tcp/443"] == 2
        assert cell.observed_ports["tcp/80"] == 1
    
    def test_add_flow_with_service(self):
        """Test adding flows with service names."""
        cell = MatrixCell(
            src_sgt=100,
            src_sgt_name="Employees",
            dst_sgt=200,
            dst_sgt_name="Servers",
        )
        
        cell.add_flow(port=443, proto="tcp", bytes_count=1000, service_name="web-app")
        cell.add_flow(port=443, proto="tcp", bytes_count=1000, service_name="web-app")
        
        assert "web-app" in cell.services
        assert len(cell.services) == 1
    
    def test_top_ports(self):
        """Test getting top ports."""
        cell = MatrixCell(
            src_sgt=100,
            src_sgt_name="Employees",
            dst_sgt=200,
            dst_sgt_name="Servers",
        )
        
        for _ in range(100):
            cell.add_flow(port=443, proto="tcp", bytes_count=100)
        for _ in range(50):
            cell.add_flow(port=80, proto="tcp", bytes_count=100)
        for _ in range(10):
            cell.add_flow(port=22, proto="tcp", bytes_count=100)
        
        top = cell.top_ports(2)
        assert len(top) == 2
        assert top[0] == ("tcp/443", 100)
        assert top[1] == ("tcp/80", 50)
    
    def test_to_dict(self):
        """Test dictionary conversion."""
        cell = MatrixCell(
            src_sgt=100,
            src_sgt_name="Employees",
            dst_sgt=200,
            dst_sgt_name="Servers",
        )
        cell.add_flow(port=443, proto="tcp", bytes_count=1000)
        
        d = cell.to_dict()
        assert d["src_sgt"] == 100
        assert d["total_flows"] == 1


class TestPolicyMatrix:
    """Tests for PolicyMatrix."""
    
    def test_matrix_creation(self):
        """Test creating a policy matrix."""
        matrix = PolicyMatrix()
        assert matrix.n_cells == 0
        assert len(matrix.sgt_values) == 0
    
    def test_get_or_create_cell(self):
        """Test creating cells in the matrix."""
        matrix = PolicyMatrix()
        matrix.add_sgt_name(100, "Employees")
        matrix.add_sgt_name(200, "Servers")
        
        cell = matrix.get_or_create_cell(100, 200)
        assert cell.src_sgt == 100
        assert cell.dst_sgt == 200
        assert matrix.n_cells == 1
        
        # Get same cell
        cell2 = matrix.get_or_create_cell(100, 200)
        assert cell is cell2
        assert matrix.n_cells == 1
    
    def test_sgt_values(self):
        """Test getting SGT values."""
        matrix = PolicyMatrix()
        matrix.get_or_create_cell(100, 200)
        matrix.get_or_create_cell(100, 300)
        matrix.get_or_create_cell(200, 300)
        
        sgts = matrix.sgt_values
        assert sgts == [100, 200, 300]
    
    def test_to_dataframe(self):
        """Test DataFrame conversion."""
        matrix = PolicyMatrix()
        matrix.add_sgt_name(100, "Employees")
        matrix.add_sgt_name(200, "Servers")
        
        cell = matrix.get_or_create_cell(100, 200)
        cell.add_flow(port=443, proto="tcp", bytes_count=1000)
        
        df = matrix.to_dataframe()
        assert len(df) == 1
        assert df.iloc[0]["src_sgt"] == 100
        assert df.iloc[0]["total_flows"] == 1
    
    def test_to_heatmap_data(self):
        """Test heatmap data generation."""
        matrix = PolicyMatrix()
        cell = matrix.get_or_create_cell(100, 200)
        for _ in range(10):
            cell.add_flow(port=443, proto="tcp", bytes_count=100)
        
        src, dst, data = matrix.to_heatmap_data()
        assert 100 in src
        assert 200 in dst
        # Find the cell value
        src_idx = src.index(100)
        dst_idx = dst.index(200)
        assert data[src_idx][dst_idx] == 10
    
    def test_summary(self):
        """Test summary generation."""
        matrix = PolicyMatrix()
        matrix.total_flows = 1000
        matrix.total_bytes = 1000000
        cell = matrix.get_or_create_cell(100, 200)
        
        summary = matrix.summary()
        assert summary["n_sgts"] == 2
        assert summary["n_cells"] == 1


class TestSGACLRule:
    """Tests for SGACLRule."""
    
    def test_rule_creation(self):
        """Test creating a rule."""
        rule = SGACLRule(
            action="permit",
            protocol="tcp",
            port=443,
        )
        
        assert rule.action == "permit"
        assert rule.protocol == "tcp"
        assert rule.port == 443
    
    def test_to_cisco_syntax(self):
        """Test Cisco syntax generation."""
        rule = SGACLRule(
            action="permit",
            protocol="tcp",
            port=443,
        )
        
        syntax = rule.to_cisco_syntax()
        assert syntax == "permit tcp dst eq 443"
    
    def test_to_cisco_syntax_with_log(self):
        """Test Cisco syntax with logging."""
        rule = SGACLRule(
            action="deny",
            protocol="ip",
            log=True,
        )
        
        syntax = rule.to_cisco_syntax()
        assert "deny ip log" == syntax


class TestSGACLPolicy:
    """Tests for SGACLPolicy."""
    
    def test_policy_creation(self):
        """Test creating a policy."""
        policy = SGACLPolicy(
            name="SGACL_Employees_to_Servers",
            src_sgt=100,
            src_sgt_name="Employees",
            dst_sgt=200,
            dst_sgt_name="Servers",
        )
        
        assert policy.name == "SGACL_Employees_to_Servers"
        assert len(policy.rules) == 0
    
    def test_add_rules(self):
        """Test adding rules to a policy."""
        policy = SGACLPolicy(
            name="test",
            src_sgt=100,
            src_sgt_name="Employees",
            dst_sgt=200,
            dst_sgt_name="Servers",
            total_observed_flows=100,
        )
        
        policy.add_rule(SGACLRule(
            action="permit",
            protocol="tcp",
            port=443,
            flow_count=80,
        ))
        policy.covered_flows = 80
        
        assert len(policy.rules) == 1
        assert policy.coverage_ratio() == 0.8
    
    def test_to_cisco_syntax(self):
        """Test complete Cisco config generation."""
        policy = SGACLPolicy(
            name="SGACL_test",
            src_sgt=100,
            src_sgt_name="Employees",
            dst_sgt=200,
            dst_sgt_name="Servers",
        )
        
        policy.add_rule(SGACLRule(action="permit", protocol="tcp", port=443))
        policy.add_rule(SGACLRule(action="permit", protocol="tcp", port=80))
        
        config = policy.to_cisco_syntax()
        
        assert "ip access-list role-based SGACL_test" in config
        assert "permit tcp dst eq 443" in config
        assert "permit tcp dst eq 80" in config


class TestSGACLGenerator:
    """Tests for SGACLGenerator."""
    
    @pytest.fixture
    def sample_matrix(self) -> PolicyMatrix:
        """Create a sample matrix for testing."""
        matrix = PolicyMatrix()
        matrix.add_sgt_name(100, "Employees")
        matrix.add_sgt_name(200, "Servers")
        
        cell = matrix.get_or_create_cell(100, 200)
        
        # Add significant traffic
        for _ in range(50):
            cell.add_flow(port=443, proto="tcp", bytes_count=1000)
        for _ in range(30):
            cell.add_flow(port=80, proto="tcp", bytes_count=500)
        for _ in range(5):  # Below threshold
            cell.add_flow(port=22, proto="tcp", bytes_count=100)
        
        return matrix
    
    def test_generate_policies(self, sample_matrix):
        """Test policy generation."""
        generator = SGACLGenerator(min_flow_count=10)
        policies = generator.generate(sample_matrix)
        
        assert len(policies) == 1
        policy = policies[0]
        
        # Should have permit rules for 443 and 80, but not 22 (below threshold)
        permit_rules = [r for r in policy.rules if r.action == "permit"]
        assert len(permit_rules) == 2
        
        ports = {r.port for r in permit_rules}
        assert 443 in ports
        assert 80 in ports
        assert 22 not in ports
    
    def test_generate_with_default_deny(self, sample_matrix):
        """Test that policies end with deny."""
        generator = SGACLGenerator()
        policies = generator.generate(sample_matrix)
        
        policy = policies[0]
        last_rule = policy.rules[-1]
        
        assert last_rule.action == "deny"
        assert last_rule.protocol == "ip"
    
    def test_generate_summary(self, sample_matrix):
        """Test summary generation."""
        generator = SGACLGenerator(min_flow_count=10)
        policies = generator.generate(sample_matrix)
        
        summary = generator.generate_summary(policies)
        assert "SGACL Policy Summary" in summary
        assert "Employees" in summary


class TestImpactAnalyzer:
    """Tests for ImpactAnalyzer."""
    
    @pytest.fixture
    def matrix_and_policies(self):
        """Create a matrix with policies for testing."""
        matrix = PolicyMatrix()
        matrix.add_sgt_name(100, "Employees")
        matrix.add_sgt_name(200, "Servers")
        
        cell = matrix.get_or_create_cell(100, 200)
        
        # Add traffic on various ports
        for _ in range(100):
            cell.add_flow(port=443, proto="tcp", bytes_count=1000)
        for _ in range(50):
            cell.add_flow(port=53, proto="udp", bytes_count=100)  # DNS - critical
        for _ in range(20):
            cell.add_flow(port=8080, proto="tcp", bytes_count=500)
        
        # Policy only permits 443
        policy = SGACLPolicy(
            name="test_policy",
            src_sgt=100,
            src_sgt_name="Employees",
            dst_sgt=200,
            dst_sgt_name="Servers",
        )
        policy.add_rule(SGACLRule(action="permit", protocol="tcp", port=443))
        policy.add_rule(SGACLRule(action="deny", protocol="ip"))
        
        return matrix, [policy]
    
    def test_analyze_impact(self, matrix_and_policies):
        """Test impact analysis."""
        matrix, policies = matrix_and_policies
        
        analyzer = ImpactAnalyzer()
        report = analyzer.analyze(matrix, policies)
        
        assert report.total_flows_analyzed == 170
        assert report.flows_permitted == 100
        assert report.flows_blocked == 70
    
    def test_critical_detection(self, matrix_and_policies):
        """Test detection of critical blocked traffic."""
        matrix, policies = matrix_and_policies
        
        analyzer = ImpactAnalyzer()
        report = analyzer.analyze(matrix, policies)
        
        # DNS (port 53) should be flagged as critical
        assert report.has_critical_issues()
        assert report.critical_blocks > 0
        
        # Check blocked traffic includes DNS
        dns_blocked = [b for b in report.blocked_traffic if "53" in b.port]
        assert len(dns_blocked) > 0
        assert dns_blocked[0].risk_level == "critical"
    
    def test_report_summary(self, matrix_and_policies):
        """Test report summary generation."""
        matrix, policies = matrix_and_policies
        
        analyzer = ImpactAnalyzer()
        report = analyzer.analyze(matrix, policies)
        
        summary = report.summary()
        assert "Policy Impact Analysis" in summary
        assert "flows permitted" in summary.lower()


class TestISEExporter:
    """Tests for ISEExporter."""
    
    @pytest.fixture
    def sample_export_data(self):
        """Create sample data for export testing."""
        taxonomy = SGTTaxonomy(
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
            ]
        )
        
        policies = [
            SGACLPolicy(
                name="SGACL_Employees_to_Servers",
                src_sgt=100,
                src_sgt_name="Employees",
                dst_sgt=200,
                dst_sgt_name="Servers",
            ),
        ]
        policies[0].add_rule(SGACLRule(action="permit", protocol="tcp", port=443))
        policies[0].add_rule(SGACLRule(action="deny", protocol="ip"))
        
        return taxonomy, policies
    
    def test_export_sgts(self, sample_export_data):
        """Test SGT export."""
        taxonomy, policies = sample_export_data
        
        exporter = ISEExporter()
        export = exporter.export(taxonomy, policies)
        
        assert len(export.sgt_definitions) == 2
        assert export.sgt_definitions[0]["name"] == "Employees"
        assert export.sgt_definitions[0]["value"] == 100
    
    def test_export_sgacls(self, sample_export_data):
        """Test SGACL export."""
        taxonomy, policies = sample_export_data
        
        exporter = ISEExporter()
        export = exporter.export(taxonomy, policies)
        
        assert len(export.sgacl_definitions) == 1
        assert "permit tcp dst eq 443" in export.sgacl_definitions[0]["aclcontent"]
    
    def test_cli_config(self, sample_export_data):
        """Test Cisco CLI config generation."""
        taxonomy, policies = sample_export_data
        
        exporter = ISEExporter()
        export = exporter.export(taxonomy, policies)
        
        config = export.cisco_cli_config
        assert "cts role-based sgt-map 100" in config
        assert "ip access-list role-based" in config
        assert "permit tcp dst eq 443" in config
    
    def test_api_payloads(self, sample_export_data):
        """Test ISE API payload generation."""
        taxonomy, policies = sample_export_data
        
        exporter = ISEExporter()
        export = exporter.export(taxonomy, policies)
        
        assert "sgt" in export.ise_api_payloads
        assert "sgacl" in export.ise_api_payloads
        assert "egressmatrixcell" in export.ise_api_payloads
        
        assert len(export.ise_api_payloads["sgt"]) == 2
        assert len(export.ise_api_payloads["sgacl"]) == 1
    
    def test_to_json(self, sample_export_data):
        """Test JSON export."""
        taxonomy, policies = sample_export_data
        
        exporter = ISEExporter()
        export = exporter.export(taxonomy, policies)
        
        json_str = export.to_json()
        assert "sgt_definitions" in json_str
        assert "sgacl_definitions" in json_str
    
    def test_deployment_guide(self, sample_export_data):
        """Test deployment guide generation."""
        taxonomy, policies = sample_export_data
        
        exporter = ISEExporter()
        export = exporter.export(taxonomy, policies)
        
        guide = exporter.generate_deployment_guide(export)
        assert "Deployment Guide" in guide
        assert "Deployment Steps" in guide


class TestPolicyExport:
    """Tests for PolicyExport dataclass."""
    
    def test_export_to_dict(self):
        """Test export to dictionary."""
        export = PolicyExport()
        export.sgt_definitions = [{"name": "Test", "value": 100}]
        
        d = export.to_dict()
        assert "metadata" in d
        assert "sgt_definitions" in d
        assert len(d["sgt_definitions"]) == 1

