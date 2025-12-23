"""
Integration tests for the complete Policy Pipeline.

Tests the end-to-end flow:
1. Load synthetic data
2. Build sketches
3. Cluster endpoints
4. Generate SGT taxonomy
5. Build policy matrix
6. Generate SGACLs
7. Analyze impact
8. Export for ISE
"""

import os
import pytest
import tempfile

from clarion.ingest.loader import load_dataset
from clarion.ingest.sketch_builder import SketchStore, build_sketches
from clarion.identity import enrich_sketches
from clarion.clustering.clusterer import EndpointClusterer
from clarion.clustering.labeling import SemanticLabeler
from clarion.clustering.sgt_mapper import SGTMapper, generate_sgt_taxonomy
from clarion.policy.matrix import PolicyMatrixBuilder, build_policy_matrix
from clarion.policy.sgacl import SGACLGenerator
from clarion.policy.impact import ImpactAnalyzer
from clarion.policy.exporter import ISEExporter


# Path to synthetic data
DATA_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "data", "raw", "trustsec_copilot_synth_campus"
)


@pytest.fixture(scope="module")
def dataset():
    """Load the synthetic dataset."""
    return load_dataset(DATA_PATH)


@pytest.fixture(scope="module")
def sketch_store(dataset):
    """Build sketches from dataset."""
    return build_sketches(dataset)


@pytest.fixture(scope="module")
def enriched_store(dataset, sketch_store):
    """Enrich sketches with identity context."""
    enrich_sketches(sketch_store, dataset)
    return sketch_store


@pytest.fixture(scope="module")
def cluster_result(enriched_store):
    """Cluster the endpoints."""
    clusterer = EndpointClusterer(min_cluster_size=3)
    return clusterer.cluster(enriched_store)


@pytest.fixture(scope="module")
def labeled_clusters(enriched_store, cluster_result, dataset):
    """Add semantic labels to clusters."""
    labeler = SemanticLabeler(dataset)
    return labeler.label_clusters(enriched_store, cluster_result)


@pytest.fixture(scope="module")
def sgt_taxonomy(enriched_store, cluster_result, labeled_clusters):
    """Generate SGT taxonomy."""
    mapper = SGTMapper()
    return mapper.generate_taxonomy(enriched_store, cluster_result, labeled_clusters)


class TestPolicyMatrixBuilding:
    """Tests for building the policy matrix."""
    
    def test_matrix_from_flows(self, dataset, enriched_store, cluster_result, sgt_taxonomy):
        """Test building a matrix from flow data."""
        matrix = build_policy_matrix(dataset, enriched_store, cluster_result, sgt_taxonomy)
        
        # Should have non-empty matrix
        assert matrix.n_cells > 0
        assert matrix.total_flows > 0
    
    def test_matrix_has_sgt_names(self, dataset, enriched_store, cluster_result, sgt_taxonomy):
        """Test that matrix cells have SGT names."""
        matrix = build_policy_matrix(dataset, enriched_store, cluster_result, sgt_taxonomy)
        
        # Check first cell
        for (src, dst), cell in matrix.cells.items():
            assert cell.src_sgt_name is not None
            assert cell.dst_sgt_name is not None
            break
    
    def test_matrix_summary(self, dataset, enriched_store, cluster_result, sgt_taxonomy):
        """Test matrix summary statistics."""
        matrix = build_policy_matrix(dataset, enriched_store, cluster_result, sgt_taxonomy)
        
        summary = matrix.summary()
        assert "n_sgts" in summary
        assert "n_cells" in summary
        assert summary["n_cells"] > 0


class TestSGACLGeneration:
    """Tests for SGACL generation."""
    
    def test_generate_policies(self, dataset, enriched_store, cluster_result, sgt_taxonomy):
        """Test generating SGACL policies."""
        matrix = build_policy_matrix(dataset, enriched_store, cluster_result, sgt_taxonomy)
        
        generator = SGACLGenerator(min_flow_count=5)
        policies = generator.generate(matrix)
        
        # Should generate policies for each matrix cell
        assert len(policies) == matrix.n_cells
    
    def test_policies_have_rules(self, dataset, enriched_store, cluster_result, sgt_taxonomy):
        """Test that policies contain rules."""
        matrix = build_policy_matrix(dataset, enriched_store, cluster_result, sgt_taxonomy)
        
        generator = SGACLGenerator(min_flow_count=5)
        policies = generator.generate(matrix)
        
        # Each policy should have at least a deny rule
        for policy in policies:
            assert len(policy.rules) >= 1
    
    def test_policies_have_permit_rules(self, dataset, enriched_store, cluster_result, sgt_taxonomy):
        """Test that policies have permit rules for observed traffic."""
        matrix = build_policy_matrix(dataset, enriched_store, cluster_result, sgt_taxonomy)
        
        generator = SGACLGenerator(min_flow_count=1)  # Low threshold
        policies = generator.generate(matrix)
        
        # At least some policies should have permit rules
        total_permit_rules = sum(
            len([r for r in p.rules if r.action == "permit"])
            for p in policies
        )
        assert total_permit_rules > 0


class TestImpactAnalysis:
    """Tests for impact analysis."""
    
    def test_analyze_all_policies(self, dataset, enriched_store, cluster_result, sgt_taxonomy):
        """Test impact analysis across all policies."""
        matrix = build_policy_matrix(dataset, enriched_store, cluster_result, sgt_taxonomy)
        
        generator = SGACLGenerator(min_flow_count=10)
        policies = generator.generate(matrix)
        
        analyzer = ImpactAnalyzer()
        report = analyzer.analyze(matrix, policies)
        
        assert report.total_flows_analyzed > 0
        assert report.permit_ratio() + report.block_ratio() == pytest.approx(1.0)
    
    def test_report_has_blocked_traffic(self, dataset, enriched_store, cluster_result, sgt_taxonomy):
        """Test that report identifies blocked traffic."""
        matrix = build_policy_matrix(dataset, enriched_store, cluster_result, sgt_taxonomy)
        
        # Use high threshold to ensure some traffic is blocked
        generator = SGACLGenerator(min_flow_count=100)
        policies = generator.generate(matrix)
        
        analyzer = ImpactAnalyzer()
        report = analyzer.analyze(matrix, policies)
        
        # With high threshold, some traffic should be blocked
        assert report.flows_blocked > 0
    
    def test_report_summary_format(self, dataset, enriched_store, cluster_result, sgt_taxonomy):
        """Test that report summary is well-formatted."""
        matrix = build_policy_matrix(dataset, enriched_store, cluster_result, sgt_taxonomy)
        
        generator = SGACLGenerator()
        policies = generator.generate(matrix)
        
        analyzer = ImpactAnalyzer()
        report = analyzer.analyze(matrix, policies)
        
        summary = report.summary()
        assert "Policy Impact Analysis" in summary


class TestISEExport:
    """Tests for ISE export functionality."""
    
    def test_export_complete(self, dataset, enriched_store, cluster_result, sgt_taxonomy):
        """Test creating a complete export."""
        matrix = build_policy_matrix(dataset, enriched_store, cluster_result, sgt_taxonomy)
        
        generator = SGACLGenerator()
        policies = generator.generate(matrix)
        
        exporter = ISEExporter()
        export = exporter.export(sgt_taxonomy, policies, matrix)
        
        assert len(export.sgt_definitions) > 0
        assert len(export.sgacl_definitions) > 0
        assert len(export.matrix_bindings) > 0
    
    def test_cli_config_valid(self, dataset, enriched_store, cluster_result, sgt_taxonomy):
        """Test that CLI config is valid."""
        matrix = build_policy_matrix(dataset, enriched_store, cluster_result, sgt_taxonomy)
        
        generator = SGACLGenerator()
        policies = generator.generate(matrix)
        
        exporter = ISEExporter()
        export = exporter.export(sgt_taxonomy, policies, matrix)
        
        config = export.cisco_cli_config
        assert "cts role-based" in config
        assert "ip access-list role-based" in config
    
    def test_save_export(self, dataset, enriched_store, cluster_result, sgt_taxonomy):
        """Test saving export to files."""
        matrix = build_policy_matrix(dataset, enriched_store, cluster_result, sgt_taxonomy)
        
        generator = SGACLGenerator()
        policies = generator.generate(matrix)
        
        exporter = ISEExporter()
        export = exporter.export(sgt_taxonomy, policies, matrix)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            files = export.save(tmpdir)
            
            assert len(files) > 0
            # Check that files exist
            for f in files:
                assert os.path.exists(f)
    
    def test_json_export_valid(self, dataset, enriched_store, cluster_result, sgt_taxonomy):
        """Test that JSON export is valid JSON."""
        import json
        
        matrix = build_policy_matrix(dataset, enriched_store, cluster_result, sgt_taxonomy)
        
        generator = SGACLGenerator()
        policies = generator.generate(matrix)
        
        exporter = ISEExporter()
        export = exporter.export(sgt_taxonomy, policies, matrix)
        
        # Should be valid JSON
        json_str = export.to_json()
        parsed = json.loads(json_str)
        
        assert "metadata" in parsed
        assert "sgt_definitions" in parsed


class TestEndToEndPipeline:
    """End-to-end pipeline tests."""
    
    def test_complete_pipeline(self, dataset, enriched_store, cluster_result, sgt_taxonomy):
        """Test the complete policy pipeline."""
        # Build matrix
        matrix = build_policy_matrix(dataset, enriched_store, cluster_result, sgt_taxonomy)
        
        # Generate policies
        generator = SGACLGenerator(min_flow_count=5)
        policies = generator.generate(matrix)
        
        # Analyze impact
        analyzer = ImpactAnalyzer()
        report = analyzer.analyze(matrix, policies)
        
        # Export
        exporter = ISEExporter()
        export = exporter.export(sgt_taxonomy, policies, matrix, report)
        
        # Verify end-to-end results
        print("\n" + "=" * 60)
        print("END-TO-END POLICY PIPELINE RESULTS")
        print("=" * 60)
        print(f"SGTs defined:       {len(export.sgt_definitions)}")
        print(f"SGACLs generated:   {len(export.sgacl_definitions)}")
        print(f"Matrix bindings:    {len(export.matrix_bindings)}")
        print(f"Traffic analyzed:   {report.total_flows_analyzed:,}")
        print(f"Traffic permitted:  {report.flows_permitted:,} ({report.permit_ratio()*100:.1f}%)")
        print(f"Traffic blocked:    {report.flows_blocked:,} ({report.block_ratio()*100:.1f}%)")
        print(f"Critical issues:    {report.critical_blocks}")
        print("=" * 60)
        
        # Assertions
        assert len(export.sgt_definitions) > 0
        assert len(policies) > 0
        assert report.total_flows_analyzed > 0
    
    def test_deployment_guide(self, dataset, enriched_store, cluster_result, sgt_taxonomy):
        """Test generating a deployment guide."""
        matrix = build_policy_matrix(dataset, enriched_store, cluster_result, sgt_taxonomy)
        
        generator = SGACLGenerator()
        policies = generator.generate(matrix)
        
        analyzer = ImpactAnalyzer()
        report = analyzer.analyze(matrix, policies)
        
        exporter = ISEExporter()
        export = exporter.export(sgt_taxonomy, policies, matrix, report)
        
        guide = exporter.generate_deployment_guide(export, report)
        
        assert "Deployment Guide" in guide
        assert "Impact Analysis" in guide
        assert "Deployment Steps" in guide

