"""
Unit tests for Clarion clustering module.
"""

import pytest
import numpy as np
from datetime import datetime

from clarion.sketches import EndpointSketch
from clarion.ingest.sketch_builder import SketchStore
from clarion.clustering.features import FeatureExtractor, FeatureVector
from clarion.clustering.clusterer import EndpointClusterer, ClusterResult, LightweightClusterer
from clarion.clustering.labeling import SemanticLabeler, ClusterLabel
from clarion.clustering.sgt_mapper import SGTMapper, SGTRecommendation, SGTTaxonomy


@pytest.fixture
def sample_sketches() -> SketchStore:
    """Create a sample sketch store for testing."""
    store = SketchStore()
    
    # Create different types of endpoints
    # Laptops (clients)
    for i in range(50):
        sketch = store.get_or_create(f"aa:bb:cc:00:00:{i:02x}")
        sketch.device_type = "laptop"
        sketch.username = f"user{i}"
        sketch.ad_groups = ["All-Employees", "Engineering-Users"]
        sketch.ise_profile = "CorporateLaptop"
        sketch.bytes_out = 10000
        sketch.bytes_in = 5000
        sketch.flow_count = 100
        # Add some peer diversity
        for j in range(10):
            sketch.unique_peers.add(f"10.0.{j}.1")
            sketch.unique_ports.add(f"tcp/{443 + j}")
    
    # Servers
    for i in range(20):
        sketch = store.get_or_create(f"bb:cc:dd:00:00:{i:02x}")
        sketch.device_type = "server"
        sketch.ise_profile = "Server"
        sketch.bytes_out = 5000
        sketch.bytes_in = 50000  # Servers receive more
        sketch.flow_count = 500
        for j in range(100):
            sketch.unique_peers.add(f"10.1.{j}.1")
    
    # Printers
    for i in range(15):
        sketch = store.get_or_create(f"cc:dd:ee:00:00:{i:02x}")
        sketch.device_type = "printer"
        sketch.ise_profile = "Printer"
        sketch.bytes_out = 1000
        sketch.bytes_in = 500
        sketch.flow_count = 10
    
    # IoT devices
    for i in range(15):
        sketch = store.get_or_create(f"dd:ee:ff:00:00:{i:02x}")
        sketch.device_type = "iot"
        sketch.ise_profile = "IoT-Sensor"
        sketch.bytes_out = 500
        sketch.bytes_in = 100
        sketch.flow_count = 50
    
    return store


class TestFeatureExtractor:
    """Tests for feature extraction."""
    
    def test_extract_single(self):
        """Test extracting features from a single sketch."""
        sketch = EndpointSketch(endpoint_id="aa:bb:cc:dd:ee:ff")
        sketch.bytes_out = 1000
        sketch.bytes_in = 5000
        sketch.flow_count = 10
        sketch.device_type = "laptop"
        sketch.username = "jsmith"
        
        extractor = FeatureExtractor()
        fv = extractor.extract(sketch)
        
        assert fv.endpoint_id == "aa:bb:cc:dd:ee:ff"
        assert fv.is_laptop == 1.0
        assert fv.has_user == 1.0
        assert fv.in_out_ratio > 0.5  # More in than out = server-like
    
    def test_extract_all(self, sample_sketches: SketchStore):
        """Test extracting features from all sketches."""
        extractor = FeatureExtractor()
        features = extractor.extract_all(sample_sketches)
        
        assert len(features) == len(sample_sketches)
        assert all(isinstance(fv, FeatureVector) for fv in features)
    
    def test_to_matrix(self, sample_sketches: SketchStore):
        """Test converting to matrix."""
        extractor = FeatureExtractor()
        features = extractor.extract_all(sample_sketches)
        X, endpoint_ids = extractor.to_matrix(features)
        
        assert X.shape[0] == len(sample_sketches)
        assert X.shape[1] == len(FeatureVector.feature_names())
        assert len(endpoint_ids) == len(sample_sketches)
    
    def test_normalization(self, sample_sketches: SketchStore):
        """Test that normalization centers the data."""
        extractor = FeatureExtractor(normalize=True)
        features = extractor.extract_all(sample_sketches)
        X, _ = extractor.to_matrix(features)
        
        # Normalized data should have mean ~0 and std ~1
        assert np.abs(np.mean(X)) < 0.1
        assert np.abs(np.std(X) - 1.0) < 0.5
    
    def test_feature_names(self):
        """Test feature names list."""
        names = FeatureVector.feature_names()
        assert "peer_diversity" in names
        assert "in_out_ratio" in names
        assert "is_laptop" in names


class TestEndpointClusterer:
    """Tests for HDBSCAN clustering."""
    
    def test_cluster_basic(self, sample_sketches: SketchStore):
        """Test basic clustering."""
        clusterer = EndpointClusterer(min_cluster_size=10, min_samples=5)
        result = clusterer.cluster(sample_sketches)
        
        assert isinstance(result, ClusterResult)
        assert len(result.labels) == len(sample_sketches)
        assert result.n_clusters >= 1  # Should find at least one cluster
    
    def test_cluster_finds_groups(self, sample_sketches: SketchStore):
        """Test that clustering finds distinct groups."""
        clusterer = EndpointClusterer(min_cluster_size=10, min_samples=5)
        result = clusterer.cluster(sample_sketches)
        
        # With 4 distinct types, should find multiple clusters
        assert result.n_clusters >= 2
    
    def test_cluster_result_methods(self, sample_sketches: SketchStore):
        """Test ClusterResult methods."""
        clusterer = EndpointClusterer(min_cluster_size=10, min_samples=5)
        result = clusterer.cluster(sample_sketches)
        
        # Test get_cluster_members
        if result.n_clusters > 0:
            members = result.get_cluster_members(0)
            assert len(members) > 0
        
        # Test get_endpoint_cluster
        eid = result.endpoint_ids[0]
        cluster = result.get_endpoint_cluster(eid)
        assert cluster == result.labels[0]
        
        # Test summary
        summary = result.summary()
        assert "n_clusters" in summary
        assert "n_noise" in summary
    
    def test_apply_to_store(self, sample_sketches: SketchStore):
        """Test applying results back to store."""
        clusterer = EndpointClusterer(min_cluster_size=10, min_samples=5)
        result = clusterer.cluster(sample_sketches)
        clusterer.apply_to_store(sample_sketches, result)
        
        # Check that sketches have cluster assignments
        assigned = sum(1 for s in sample_sketches if s.local_cluster_id != -1)
        assert assigned > 0


class TestLightweightClusterer:
    """Tests for Mini-Batch K-Means clustering."""
    
    def test_fit_predict(self, sample_sketches: SketchStore):
        """Test lightweight clustering."""
        extractor = FeatureExtractor()
        features = extractor.extract_all(sample_sketches)
        X, _ = extractor.to_matrix(features)
        
        clusterer = LightweightClusterer(n_clusters=4)
        labels = clusterer.fit_predict(X)
        
        assert len(labels) == len(sample_sketches)
        assert set(labels) <= set(range(4))  # Labels 0-3
    
    def test_predict(self, sample_sketches: SketchStore):
        """Test predicting on new data."""
        extractor = FeatureExtractor()
        features = extractor.extract_all(sample_sketches)
        X, _ = extractor.to_matrix(features)
        
        clusterer = LightweightClusterer(n_clusters=4)
        clusterer.fit_predict(X)
        
        # Predict on same data
        new_labels = clusterer.predict(X[:10])
        assert len(new_labels) == 10


class TestSemanticLabeler:
    """Tests for semantic labeling."""
    
    def test_label_clusters(self, sample_sketches: SketchStore):
        """Test labeling clusters."""
        # First cluster
        clusterer = EndpointClusterer(min_cluster_size=10, min_samples=5)
        result = clusterer.cluster(sample_sketches)
        
        # Then label
        labeler = SemanticLabeler()
        labels = labeler.label_clusters(sample_sketches, result)
        
        assert len(labels) >= result.n_clusters
        for cluster_id, label in labels.items():
            assert isinstance(label, ClusterLabel)
            assert label.name is not None
            assert label.member_count > 0
    
    def test_label_uses_device_type(self, sample_sketches: SketchStore):
        """Test that labeling uses device type information."""
        clusterer = EndpointClusterer(min_cluster_size=10, min_samples=5)
        result = clusterer.cluster(sample_sketches)
        
        labeler = SemanticLabeler()
        labels = labeler.label_clusters(sample_sketches, result)
        
        # At least one label should reference device types
        label_names = [l.name for l in labels.values()]
        device_related = [
            n for n in label_names 
            if any(d in n.lower() for d in ["laptop", "server", "printer", "iot"])
        ]
        assert len(device_related) > 0


class TestSGTMapper:
    """Tests for SGT mapping."""
    
    def test_generate_taxonomy(self, sample_sketches: SketchStore):
        """Test generating SGT taxonomy."""
        # Cluster
        clusterer = EndpointClusterer(min_cluster_size=10, min_samples=5)
        result = clusterer.cluster(sample_sketches)
        
        # Label
        labeler = SemanticLabeler()
        labels = labeler.label_clusters(sample_sketches, result)
        
        # Map to SGTs
        mapper = SGTMapper()
        taxonomy = mapper.generate_taxonomy(sample_sketches, result, labels)
        
        assert isinstance(taxonomy, SGTTaxonomy)
        assert taxonomy.n_sgts >= 1
        assert taxonomy.total_endpoints == len(sample_sketches)
    
    def test_sgt_values_unique(self, sample_sketches: SketchStore):
        """Test that SGT values are unique."""
        clusterer = EndpointClusterer(min_cluster_size=10, min_samples=5)
        result = clusterer.cluster(sample_sketches)
        
        labeler = SemanticLabeler()
        labels = labeler.label_clusters(sample_sketches, result)
        
        mapper = SGTMapper()
        taxonomy = mapper.generate_taxonomy(sample_sketches, result, labels)
        
        sgt_values = [rec.sgt_value for rec in taxonomy.recommendations]
        assert len(sgt_values) == len(set(sgt_values))  # All unique
    
    def test_taxonomy_summary(self, sample_sketches: SketchStore):
        """Test taxonomy summary output."""
        clusterer = EndpointClusterer(min_cluster_size=10, min_samples=5)
        result = clusterer.cluster(sample_sketches)
        
        labeler = SemanticLabeler()
        labels = labeler.label_clusters(sample_sketches, result)
        
        mapper = SGTMapper()
        taxonomy = mapper.generate_taxonomy(sample_sketches, result, labels)
        
        summary = taxonomy.summary()
        assert "SGT Taxonomy" in summary
        assert "Coverage" in summary
    
    def test_coverage_calculation(self, sample_sketches: SketchStore):
        """Test coverage ratio calculation."""
        clusterer = EndpointClusterer(min_cluster_size=10, min_samples=5)
        result = clusterer.cluster(sample_sketches)
        
        labeler = SemanticLabeler()
        labels = labeler.label_clusters(sample_sketches, result)
        
        mapper = SGTMapper()
        taxonomy = mapper.generate_taxonomy(sample_sketches, result, labels)
        
        coverage = taxonomy.coverage_ratio()
        assert 0 <= coverage <= 1.0
        
        # With our test data, should have reasonable coverage
        assert coverage > 0.5


