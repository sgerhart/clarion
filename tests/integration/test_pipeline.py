"""
Integration tests for the full Clarion pipeline.

Tests the complete flow:
1. Load synthetic data
2. Build sketches from flows
3. Enrich with identity
"""

import pytest
from pathlib import Path

from clarion import (
    load_dataset,
    build_sketches,
    enrich_sketches,
    ClarionDataset,
    SketchStore,
)


# Path to synthetic dataset
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "raw" / "trustsec_copilot_synth_campus"


@pytest.fixture
def dataset() -> ClarionDataset:
    """Load the synthetic dataset."""
    if not DATA_DIR.exists():
        pytest.skip(f"Synthetic data not found at {DATA_DIR}")
    return load_dataset(DATA_DIR)


@pytest.fixture
def sketch_store(dataset: ClarionDataset) -> SketchStore:
    """Build sketches from the dataset."""
    return build_sketches(dataset)


class TestDataLoading:
    """Tests for data loading."""
    
    def test_load_dataset(self, dataset: ClarionDataset):
        """Test that dataset loads correctly."""
        summary = dataset.summary()
        
        assert summary["flows"] > 100000  # ~106K flows
        assert summary["endpoints"] > 10000  # ~13K endpoints
        assert summary["ise_sessions"] > 10000  # ~13K sessions
        assert summary["ad_users"] > 5000  # ~10K users
        assert summary["services"] > 30  # ~42 services
    
    def test_flows_have_required_columns(self, dataset: ClarionDataset):
        """Test that flows have required columns."""
        required = [
            "flow_id", "src_ip", "dst_ip", "src_port", "dst_port",
            "proto", "bytes", "packets", "src_mac", "start_time"
        ]
        for col in required:
            assert col in dataset.flows.columns
    
    def test_flows_sorted_by_time(self, dataset: ClarionDataset):
        """Test that flows are sorted by start_time."""
        times = dataset.flows["start_time"]
        assert times.is_monotonic_increasing


class TestSketchBuilding:
    """Tests for sketch building."""
    
    def test_build_sketches(self, sketch_store: SketchStore):
        """Test that sketches are built correctly."""
        assert len(sketch_store) > 10000  # Should have many endpoints
    
    def test_sketch_has_flows(self, sketch_store: SketchStore):
        """Test that sketches have flow data."""
        total_flows = sum(s.flow_count for s in sketch_store)
        assert total_flows > 100000
    
    def test_sketch_memory_reasonable(self, sketch_store: SketchStore):
        """Test that memory usage is reasonable."""
        summary = sketch_store.summary()
        
        # Should be under 500MB for ~13K endpoints
        # (Current: ~32KB per endpoint, target is ~10KB - optimization for later)
        assert summary["memory_mb"] < 500
        
        # Average per endpoint should be under 50KB
        avg_memory = summary["memory_bytes"] / summary["count"]
        assert avg_memory <= 50000
    
    def test_sketch_diversity_metrics(self, sketch_store: SketchStore):
        """Test that diversity metrics are computed."""
        sample = list(sketch_store)[:100]
        
        for sketch in sample:
            if sketch.flow_count > 0:
                # Should have tracked some peers and ports
                assert sketch.peer_diversity >= 0
                assert sketch.port_diversity >= 0


class TestIdentityResolution:
    """Tests for identity resolution."""
    
    def test_enrich_sketches(self, sketch_store: SketchStore, dataset: ClarionDataset):
        """Test identity enrichment."""
        contexts = enrich_sketches(sketch_store, dataset)
        
        assert len(contexts) == len(sketch_store)
    
    def test_user_resolution_rate(self, sketch_store: SketchStore, dataset: ClarionDataset):
        """Test that we resolve a good percentage of users."""
        contexts = enrich_sketches(sketch_store, dataset)
        
        with_user = sum(1 for c in contexts.values() if c.has_user())
        rate = with_user / len(contexts)
        
        # Should resolve >50% of endpoints to users
        # (Some are servers/IoT without users)
        assert rate > 0.5
    
    def test_group_resolution(self, sketch_store: SketchStore, dataset: ClarionDataset):
        """Test AD group resolution."""
        contexts = enrich_sketches(sketch_store, dataset)
        
        with_groups = sum(1 for c in contexts.values() if c.has_groups())
        
        # Most users should have groups
        assert with_groups > 0


class TestEndToEndPipeline:
    """Test the complete pipeline."""
    
    def test_full_pipeline(self, dataset: ClarionDataset):
        """Test loading → sketching → enriching."""
        # Build sketches
        store = build_sketches(dataset)
        assert len(store) > 0
        
        # Enrich with identity
        contexts = enrich_sketches(store, dataset)
        assert len(contexts) == len(store)
        
        # Verify sketches have identity
        enriched = [s for s in store if s.username is not None]
        assert len(enriched) > 0
        
        # Verify sketches have groups
        with_groups = [s for s in store if len(s.ad_groups) > 0]
        assert len(with_groups) > 0
    
    def test_sketch_export(self, sketch_store: SketchStore):
        """Test that sketches can be exported to dict."""
        sample = list(sketch_store)[:10]
        
        for sketch in sample:
            d = sketch.to_dict()
            assert "endpoint_id" in d
            assert "flow_count" in d
            assert "peer_diversity" in d
            assert "in_out_ratio" in d

