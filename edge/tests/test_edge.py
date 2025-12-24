"""
Tests for Clarion Edge module.

Tests:
- EdgeSketch and EdgeSketchStore
- FlowSimulator
- EdgeAgent
- LightweightKMeans
"""

import pytest
import tempfile
import os
import time

from clarion_edge.sketch import (
    EdgeHyperLogLog,
    EdgeCountMinSketch,
    EdgeSketch,
    EdgeSketchStore,
)
from clarion_edge.simulator import FlowSimulator, SimulatorConfig, create_test_csv
from clarion_edge.agent import EdgeAgent, EdgeConfig, LightweightKMeans


class TestEdgeHyperLogLog:
    """Tests for EdgeHyperLogLog."""
    
    def test_create_empty(self):
        """Test creating empty HLL."""
        hll = EdgeHyperLogLog()
        assert hll.count() == 0
    
    def test_add_single(self):
        """Test adding single item."""
        hll = EdgeHyperLogLog()
        hll.add("10.0.0.1")
        assert hll.count() >= 1
    
    def test_add_duplicates(self):
        """Test that duplicates don't increase count."""
        hll = EdgeHyperLogLog()
        for _ in range(100):
            hll.add("10.0.0.1")
        
        # Should be approximately 1
        assert hll.count() <= 2
    
    def test_cardinality_estimation(self):
        """Test cardinality estimation accuracy."""
        hll = EdgeHyperLogLog()
        
        n = 1000
        for i in range(n):
            hll.add(f"10.0.{i // 256}.{i % 256}")
        
        estimate = hll.count()
        # Should be within 10% error
        assert 900 <= estimate <= 1100
    
    def test_merge(self):
        """Test merging two HLLs."""
        hll1 = EdgeHyperLogLog()
        hll2 = EdgeHyperLogLog()
        
        for i in range(100):
            hll1.add(f"a{i}")
        for i in range(100):
            hll2.add(f"b{i}")
        
        hll1.merge(hll2)
        
        # Should be approximately 200
        assert 150 <= hll1.count() <= 250
    
    def test_serialization(self):
        """Test serialize/deserialize."""
        hll = EdgeHyperLogLog()
        for i in range(50):
            hll.add(f"item{i}")
        
        data = hll.to_bytes()
        restored = EdgeHyperLogLog.from_bytes(data)
        
        assert hll.count() == restored.count()
    
    def test_memory_bytes(self):
        """Test memory estimation."""
        hll = EdgeHyperLogLog(precision=10)
        assert hll.memory_bytes() == 1024  # 2^10 registers


class TestEdgeCountMinSketch:
    """Tests for EdgeCountMinSketch."""
    
    def test_create_empty(self):
        """Test creating empty CMS."""
        cms = EdgeCountMinSketch()
        assert cms.total() == 0
    
    def test_add_and_count(self):
        """Test adding and counting."""
        cms = EdgeCountMinSketch()
        
        cms.add("tcp/443", count=100)
        cms.add("tcp/80", count=50)
        
        assert cms.count("tcp/443") >= 100
        assert cms.count("tcp/80") >= 50
        assert cms.total() == 150
    
    def test_frequency_estimation(self):
        """Test frequency estimation."""
        cms = EdgeCountMinSketch()
        
        # Add with different frequencies
        for _ in range(1000):
            cms.add("frequent")
        for _ in range(10):
            cms.add("rare")
        
        # Frequent should be much higher
        assert cms.count("frequent") > cms.count("rare") * 10
    
    def test_merge(self):
        """Test merging two CMS."""
        cms1 = EdgeCountMinSketch()
        cms2 = EdgeCountMinSketch()
        
        cms1.add("a", 100)
        cms2.add("a", 50)
        
        cms1.merge(cms2)
        
        assert cms1.count("a") >= 150
    
    def test_serialization(self):
        """Test serialize/deserialize."""
        cms = EdgeCountMinSketch()
        cms.add("test", 42)
        
        data = cms.to_bytes()
        restored = EdgeCountMinSketch.from_bytes(data)
        
        assert cms.count("test") == restored.count("test")


class TestEdgeSketch:
    """Tests for EdgeSketch."""
    
    def test_create_empty(self):
        """Test creating empty sketch."""
        sketch = EdgeSketch(
            endpoint_id="aa:bb:cc:dd:ee:ff",
            switch_id="switch-1",
        )
        
        assert sketch.flow_count == 0
        assert sketch.bytes_in == 0
        assert sketch.bytes_out == 0
    
    def test_record_flow(self):
        """Test recording a flow."""
        sketch = EdgeSketch(
            endpoint_id="aa:bb:cc:dd:ee:ff",
            switch_id="switch-1",
        )
        
        sketch.record_flow(
            dst_ip="10.0.1.1",
            dst_port=443,
            proto="tcp",
            bytes_count=1000,
            is_outbound=True,
        )
        
        assert sketch.flow_count == 1
        assert sketch.bytes_out == 1000
        assert sketch.unique_peers.count() >= 1
        assert sketch.unique_ports.count() >= 1
    
    def test_record_multiple_flows(self):
        """Test recording multiple flows."""
        sketch = EdgeSketch(
            endpoint_id="aa:bb:cc:dd:ee:ff",
            switch_id="switch-1",
        )
        
        for i in range(100):
            sketch.record_flow(
                dst_ip=f"10.0.1.{i % 10}",
                dst_port=443 if i % 2 == 0 else 80,
                proto="tcp",
                bytes_count=1000,
                is_outbound=True,
            )
        
        assert sketch.flow_count == 100
        assert sketch.bytes_out == 100000
        assert 8 <= sketch.unique_peers.count() <= 12  # ~10 unique
        assert sketch.unique_ports.count() >= 2
    
    def test_get_feature_vector(self):
        """Test feature extraction."""
        sketch = EdgeSketch(
            endpoint_id="aa:bb:cc:dd:ee:ff",
            switch_id="switch-1",
        )
        
        for i in range(50):
            sketch.record_flow(
                dst_ip=f"10.0.1.{i}",
                dst_port=443,
                proto="tcp",
                bytes_count=1000,
                is_outbound=True,
            )
        
        features = sketch.get_feature_vector()
        
        assert len(features) == 7
        assert all(isinstance(f, float) for f in features)
    
    def test_serialization(self):
        """Test serialize/deserialize."""
        sketch = EdgeSketch(
            endpoint_id="aa:bb:cc:dd:ee:ff",
            switch_id="switch-1",
        )
        
        for i in range(10):
            sketch.record_flow(
                dst_ip=f"10.0.1.{i}",
                dst_port=443,
                proto="tcp",
                bytes_count=1000,
                is_outbound=True,
            )
        
        data = sketch.to_bytes()
        restored = EdgeSketch.from_bytes(data)
        
        assert restored.endpoint_id == sketch.endpoint_id
        assert restored.flow_count == sketch.flow_count
        assert restored.bytes_out == sketch.bytes_out
    
    def test_memory_bytes(self):
        """Test memory estimation."""
        sketch = EdgeSketch(
            endpoint_id="aa:bb:cc:dd:ee:ff",
            switch_id="switch-1",
        )
        
        # Memory includes HLL (2x ~1KB) + CMS (~16KB) + overhead
        # Should be around 18-20KB per endpoint
        memory = sketch.memory_bytes()
        assert 15000 <= memory <= 25000


class TestEdgeSketchStore:
    """Tests for EdgeSketchStore."""
    
    def test_create_empty(self):
        """Test creating empty store."""
        store = EdgeSketchStore(max_endpoints=100, switch_id="test")
        assert len(store) == 0
    
    def test_get_or_create(self):
        """Test getting/creating sketches."""
        store = EdgeSketchStore(max_endpoints=100, switch_id="test")
        
        sketch1 = store.get_or_create("aa:bb:cc:dd:ee:01")
        sketch2 = store.get_or_create("aa:bb:cc:dd:ee:01")  # Same
        sketch3 = store.get_or_create("aa:bb:cc:dd:ee:02")  # Different
        
        assert sketch1 is sketch2
        assert sketch1 is not sketch3
        assert len(store) == 2
    
    def test_eviction(self):
        """Test that old sketches are evicted."""
        store = EdgeSketchStore(max_endpoints=5, switch_id="test")
        
        # Add 5 endpoints
        for i in range(5):
            s = store.get_or_create(f"aa:bb:cc:dd:ee:{i:02x}")
            s.last_seen = i  # Older sketches have lower timestamps
        
        assert len(store) == 5
        
        # Add one more - should evict oldest
        store.get_or_create("aa:bb:cc:dd:ee:ff")
        
        assert len(store) == 5
        # Oldest (last_seen=0) should be evicted
        assert "aa:bb:cc:dd:ee:00" not in [s.endpoint_id for s in store]
    
    def test_get_feature_matrix(self):
        """Test feature matrix extraction."""
        store = EdgeSketchStore(max_endpoints=100, switch_id="test")
        
        for i in range(10):
            s = store.get_or_create(f"aa:bb:cc:dd:ee:{i:02x}")
            s.record_flow("10.0.1.1", 443, "tcp", 1000, True)
        
        features, ids = store.get_feature_matrix()
        
        assert len(features) == 10
        assert len(ids) == 10
        assert len(features[0]) == 7


class TestFlowSimulator:
    """Tests for FlowSimulator."""
    
    def test_synthetic_generation(self):
        """Test synthetic flow generation."""
        config = SimulatorConfig(
            mode="synthetic",
            num_endpoints=10,
            flows_per_second=float('inf'),  # No delay
        )
        
        simulator = FlowSimulator(config)
        flows = list(simulator.generate(max_flows=100))
        
        assert len(flows) == 100
        
        # Check flow structure
        flow = flows[0]
        assert flow.src_mac
        assert flow.dst_ip
        assert flow.dst_port > 0
    
    def test_csv_creation_and_replay(self):
        """Test creating and replaying CSV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "test_flows.csv")
            
            # Create test CSV
            create_test_csv(csv_path, num_flows=50, num_endpoints=5)
            assert os.path.exists(csv_path)
            
            # Replay
            config = SimulatorConfig(
                mode="replay",
                csv_path=csv_path,
                replay_speed=0,  # No delay
            )
            
            simulator = FlowSimulator(config)
            flows = list(simulator.generate())
            
            assert len(flows) == 50


class TestLightweightKMeans:
    """Tests for LightweightKMeans."""
    
    def test_fit_basic(self):
        """Test basic fitting."""
        kmeans = LightweightKMeans(n_clusters=3)
        
        # 3 clear clusters
        X = [
            [0.0, 0.0], [0.1, 0.1], [0.2, 0.0],  # Cluster 0
            [5.0, 5.0], [5.1, 5.0], [5.0, 5.1],  # Cluster 1
            [10.0, 0.0], [10.1, 0.1], [10.0, 0.2],  # Cluster 2
        ]
        
        labels = kmeans.fit(X)
        
        assert len(labels) == 9
        assert len(set(labels)) == 3  # Should find 3 clusters
        
        # Points in same cluster should have same label
        assert labels[0] == labels[1] == labels[2]
        assert labels[3] == labels[4] == labels[5]
        assert labels[6] == labels[7] == labels[8]
    
    def test_predict(self):
        """Test prediction on new data."""
        kmeans = LightweightKMeans(n_clusters=2)
        
        X_train = [
            [0.0, 0.0], [0.1, 0.1],
            [10.0, 10.0], [10.1, 10.1],
        ]
        
        kmeans.fit(X_train)
        
        X_new = [[0.05, 0.05], [9.9, 9.9]]
        labels = kmeans.predict(X_new)
        
        assert len(labels) == 2
        assert labels[0] != labels[1]  # Different clusters


class TestEdgeAgent:
    """Tests for EdgeAgent."""
    
    def test_process_flow(self):
        """Test processing a single flow."""
        config = EdgeConfig(switch_id="test", enable_clustering=False)
        agent = EdgeAgent(config)
        
        from clarion_edge.simulator import SimulatedFlow
        
        flow = SimulatedFlow(
            src_mac="aa:bb:cc:dd:ee:ff",
            src_ip="192.168.1.100",
            dst_ip="10.0.1.1",
            dst_port=443,
            src_port=50000,
            proto="tcp",
            bytes=1000,
            packets=5,
            timestamp=int(time.time()),
        )
        
        agent.process_flow(flow)
        
        assert len(agent.store) == 1
        assert agent._flow_count == 1
    
    def test_run_with_simulator(self):
        """Test running with simulator."""
        config = EdgeConfig(
            switch_id="test",
            enable_clustering=True,
            n_clusters=4,
            cluster_interval_seconds=1,  # Cluster frequently for test
        )
        agent = EdgeAgent(config)
        
        sim_config = SimulatorConfig(
            mode="synthetic",
            num_endpoints=20,
            flows_per_second=float('inf'),
        )
        
        metrics = agent.run_with_simulator(sim_config, duration_seconds=2)
        
        assert metrics["flows_processed"] > 0
        assert metrics["endpoints_tracked"] > 0
    
    def test_get_metrics(self):
        """Test getting metrics."""
        config = EdgeConfig(switch_id="test")
        agent = EdgeAgent(config)
        
        metrics = agent.get_metrics()
        
        assert "switch_id" in metrics
        assert "uptime_seconds" in metrics
        assert "flows_processed" in metrics
    
    def test_save_state(self):
        """Test saving state to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = EdgeConfig(switch_id="test", data_dir=tmpdir)
            agent = EdgeAgent(config)
            
            # Add some data
            from clarion_edge.simulator import SimulatedFlow
            
            for i in range(5):
                flow = SimulatedFlow(
                    src_mac=f"aa:bb:cc:dd:ee:{i:02x}",
                    src_ip="192.168.1.100",
                    dst_ip="10.0.1.1",
                    dst_port=443,
                    src_port=50000,
                    proto="tcp",
                    bytes=1000,
                    packets=5,
                    timestamp=int(time.time()),
                )
                agent.process_flow(flow)
            
            # Save
            path = agent.save_state()
            
            assert os.path.exists(path)
            
            # Load and verify
            import json
            with open(path) as f:
                state = json.load(f)
            
            assert state["config"]["switch_id"] == "test"
            assert len(state["sketches"]) == 5

