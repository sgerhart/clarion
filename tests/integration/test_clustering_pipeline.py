"""
Integration tests for the clustering pipeline.

Tests the complete clustering flow:
1. Load data and build sketches
2. Enrich with identity
3. Cluster endpoints
4. Label clusters semantically
5. Generate SGT recommendations
"""

import pytest
from pathlib import Path

from clarion import (
    load_dataset,
    build_sketches,
    enrich_sketches,
    EndpointClusterer,
    SemanticLabeler,
    SGTMapper,
    FeatureExtractor,
    generate_sgt_taxonomy,
)


# Path to synthetic dataset
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "raw" / "trustsec_copilot_synth_campus"


@pytest.fixture(scope="module")
def enriched_store():
    """Load data, build sketches, and enrich with identity."""
    if not DATA_DIR.exists():
        pytest.skip(f"Synthetic data not found at {DATA_DIR}")
    
    dataset = load_dataset(DATA_DIR)
    store = build_sketches(dataset)
    enrich_sketches(store, dataset)
    
    return store


class TestClusteringPipeline:
    """Integration tests for clustering."""
    
    def test_feature_extraction(self, enriched_store):
        """Test feature extraction on real data."""
        extractor = FeatureExtractor()
        features = extractor.extract_all(enriched_store)
        
        assert len(features) == len(enriched_store)
        
        # Check that features have variation
        X, _ = extractor.to_matrix(features)
        variances = X.var(axis=0)
        assert variances.sum() > 0  # Not all zeros
    
    def test_clustering_real_data(self, enriched_store):
        """Test clustering on real synthetic data."""
        clusterer = EndpointClusterer(
            min_cluster_size=50,
            min_samples=10,
        )
        result = clusterer.cluster(enriched_store)
        
        # Should find multiple clusters in diverse data
        assert result.n_clusters >= 3
        
        # Noise should be reasonable
        noise_ratio = result.n_noise / len(result.endpoint_ids)
        assert noise_ratio < 0.3  # Less than 30% noise
        
        # Should have silhouette score
        assert result.silhouette is not None
        assert result.silhouette > 0  # Positive means clusters are somewhat separated
    
    def test_semantic_labeling_real_data(self, enriched_store):
        """Test semantic labeling on real data."""
        clusterer = EndpointClusterer(min_cluster_size=50, min_samples=10)
        result = clusterer.cluster(enriched_store)
        
        labeler = SemanticLabeler()
        labels = labeler.label_clusters(enriched_store, result)
        
        # Should label most clusters
        assert len(labels) >= result.n_clusters
        
        # Labels should have meaningful names
        for label in labels.values():
            if label.cluster_id != -1:
                assert label.name != ""
                assert label.confidence > 0
    
    def test_sgt_mapping_real_data(self, enriched_store):
        """Test SGT mapping on real data."""
        clusterer = EndpointClusterer(min_cluster_size=50, min_samples=10)
        result = clusterer.cluster(enriched_store)
        
        labeler = SemanticLabeler()
        labels = labeler.label_clusters(enriched_store, result)
        
        mapper = SGTMapper()
        taxonomy = mapper.generate_taxonomy(enriched_store, result, labels)
        
        # Should generate multiple SGTs
        assert taxonomy.n_sgts >= 3
        
        # Coverage should be reasonable
        assert taxonomy.coverage_ratio() > 0.5
        
        # SGT values should be in valid ranges
        for rec in taxonomy.recommendations:
            assert 2 <= rec.sgt_value <= 99
    
    def test_full_pipeline_convenience(self, enriched_store):
        """Test the convenience function for full pipeline."""
        clusterer = EndpointClusterer(min_cluster_size=50, min_samples=10)
        result = clusterer.cluster(enriched_store)
        
        taxonomy = generate_sgt_taxonomy(enriched_store, result)
        
        assert taxonomy.n_sgts >= 1
        assert taxonomy.total_endpoints == len(enriched_store)
    
    def test_cluster_quality_metrics(self, enriched_store):
        """Test that cluster quality metrics are reasonable."""
        clusterer = EndpointClusterer(min_cluster_size=50, min_samples=10)
        result = clusterer.cluster(enriched_store)
        
        summary = result.summary()
        
        # Check all expected fields are present
        assert "n_clusters" in summary
        assert "n_noise" in summary
        assert "silhouette" in summary
        assert "cluster_sizes" in summary
        
        # Cluster sizes should be non-empty
        assert len(summary["cluster_sizes"]) > 0
    
    def test_taxonomy_output_format(self, enriched_store):
        """Test that taxonomy output is in expected format."""
        clusterer = EndpointClusterer(min_cluster_size=50, min_samples=10)
        result = clusterer.cluster(enriched_store)
        
        taxonomy = generate_sgt_taxonomy(enriched_store, result)
        
        # Test to_dict serialization
        d = taxonomy.to_dict()
        assert "recommendations" in d
        assert "total_endpoints" in d
        assert "coverage_ratio" in d
        
        # Test summary string
        summary = taxonomy.summary()
        assert "SGT Taxonomy" in summary
        assert "SGT" in summary


class TestEndToEndClustering:
    """End-to-end tests for the complete workflow."""
    
    def test_complete_workflow(self, enriched_store):
        """Test complete workflow from sketches to SGT recommendations."""
        # Step 1: Extract features
        extractor = FeatureExtractor()
        features = extractor.extract_all(enriched_store)
        
        # Step 2: Cluster
        clusterer = EndpointClusterer(min_cluster_size=50, min_samples=10)
        result = clusterer.cluster(enriched_store, features)
        
        # Step 3: Apply to store
        clusterer.apply_to_store(enriched_store, result)
        
        # Step 4: Label clusters
        labeler = SemanticLabeler()
        labels = labeler.label_clusters(enriched_store, result)
        
        # Step 5: Generate SGT taxonomy
        mapper = SGTMapper()
        taxonomy = mapper.generate_taxonomy(enriched_store, result, labels)
        
        # Verify end state
        print(f"\n{taxonomy.summary()}")
        
        assert taxonomy.n_sgts >= 3
        assert taxonomy.coverage_ratio() > 0.5
        
        # Verify sketches have cluster assignments
        assigned = sum(1 for s in enriched_store if s.local_cluster_id >= 0)
        assert assigned > len(enriched_store) * 0.5

