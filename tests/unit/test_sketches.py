"""
Unit tests for Clarion sketches module.
"""

import pytest
from datetime import datetime

from clarion.sketches import EndpointSketch, HyperLogLogSketch, CountMinSketch


class TestHyperLogLogSketch:
    """Tests for HyperLogLog cardinality estimation."""
    
    def test_create_empty(self):
        """Test creating an empty HLL."""
        hll = HyperLogLogSketch(name="test")
        assert hll.count() == 0
        assert hll.name == "test"
    
    def test_add_single_item(self):
        """Test adding a single item."""
        hll = HyperLogLogSketch(name="test")
        hll.add("item1")
        assert hll.count() >= 1
    
    def test_add_duplicates(self):
        """Test that duplicates are counted once."""
        hll = HyperLogLogSketch(name="test")
        for _ in range(100):
            hll.add("same_item")
        # Should be approximately 1 (with some error)
        assert hll.count() <= 3
    
    def test_cardinality_estimation(self):
        """Test cardinality estimation accuracy."""
        hll = HyperLogLogSketch(name="test", precision=14)
        
        # Add 1000 unique items
        for i in range(1000):
            hll.add(f"item_{i}")
        
        # Should be within ~5% of 1000
        count = hll.count()
        assert 900 <= count <= 1100
    
    def test_add_various_types(self):
        """Test adding different types."""
        hll = HyperLogLogSketch(name="test")
        hll.add("string")
        hll.add(12345)
        hll.add(b"bytes")
        assert hll.count() >= 1
    
    def test_merge(self):
        """Test merging two HLLs."""
        hll1 = HyperLogLogSketch(name="test1")
        hll2 = HyperLogLogSketch(name="test2")
        
        # Add different items to each
        for i in range(100):
            hll1.add(f"a_{i}")
        for i in range(100):
            hll2.add(f"b_{i}")
        
        # Merge
        hll1.merge(hll2)
        
        # Should have ~200 unique items
        assert 180 <= hll1.count() <= 220
    
    def test_memory_bytes(self):
        """Test memory estimation."""
        hll = HyperLogLogSketch(name="test", precision=14)
        # 2^14 = 16384 registers + overhead
        assert hll.memory_bytes() > 16000


class TestCountMinSketch:
    """Tests for Count-Min Sketch frequency estimation."""
    
    def test_create_empty(self):
        """Test creating an empty CMS."""
        cms = CountMinSketch(name="test")
        assert cms.total() == 0
        assert cms.name == "test"
    
    def test_add_and_get(self):
        """Test adding and retrieving counts."""
        cms = CountMinSketch(name="test")
        cms.add("item1", count=10)
        cms.add("item1", count=5)
        
        # Should be at least 15 (may overestimate due to collisions)
        assert cms.get("item1") >= 15
    
    def test_frequency_estimation(self):
        """Test frequency estimation."""
        cms = CountMinSketch(name="test", width=1000, depth=5)
        
        # Add items with known frequencies
        for _ in range(100):
            cms.add("frequent")
        for _ in range(10):
            cms.add("rare")
        
        # Frequent should have higher count
        assert cms.get("frequent") >= cms.get("rare")
        assert cms.get("frequent") >= 100
        assert cms.get("rare") >= 10
    
    def test_total(self):
        """Test total count tracking."""
        cms = CountMinSketch(name="test")
        cms.add("a", count=10)
        cms.add("b", count=20)
        cms.add("c", count=30)
        assert cms.total() == 60
    
    def test_top_k(self):
        """Test top-k functionality."""
        cms = CountMinSketch(name="test")
        cms.add("first", count=100)
        cms.add("second", count=50)
        cms.add("third", count=25)
        
        candidates = ["first", "second", "third", "fourth"]
        top = cms.top_k(candidates, k=2)
        
        assert len(top) == 2
        assert top[0][0] == "first"
        assert top[1][0] == "second"
    
    def test_merge(self):
        """Test merging two CMS."""
        cms1 = CountMinSketch(name="test1", width=1000, depth=5)
        cms2 = CountMinSketch(name="test2", width=1000, depth=5)
        
        cms1.add("item", count=10)
        cms2.add("item", count=20)
        
        cms1.merge(cms2)
        
        assert cms1.get("item") >= 30
        assert cms1.total() == 30
    
    def test_clear(self):
        """Test clearing the sketch."""
        cms = CountMinSketch(name="test")
        cms.add("item", count=100)
        cms.clear()
        assert cms.total() == 0
        assert cms.get("item") == 0


class TestEndpointSketch:
    """Tests for EndpointSketch behavioral fingerprinting."""
    
    def test_create_empty(self):
        """Test creating an empty sketch."""
        sketch = EndpointSketch(endpoint_id="aa:bb:cc:dd:ee:ff")
        assert sketch.endpoint_id == "aa:bb:cc:dd:ee:ff"
        assert sketch.flow_count == 0
        assert sketch.bytes_in == 0
        assert sketch.bytes_out == 0
    
    def test_record_flow(self):
        """Test recording a flow."""
        sketch = EndpointSketch(endpoint_id="aa:bb:cc:dd:ee:ff")
        
        sketch.record_flow(
            dst_ip="10.0.0.1",
            dst_port=443,
            proto="tcp",
            bytes_out=1000,
            bytes_in=5000,
            timestamp=datetime(2024, 1, 1, 10, 30),
        )
        
        assert sketch.flow_count == 1
        assert sketch.bytes_out == 1000
        assert sketch.bytes_in == 5000
        assert sketch.peer_diversity >= 1
        assert sketch.port_diversity >= 1
    
    def test_record_multiple_flows(self):
        """Test recording multiple flows."""
        sketch = EndpointSketch(endpoint_id="aa:bb:cc:dd:ee:ff")
        
        # Record flows to different destinations
        for i in range(10):
            sketch.record_flow(
                dst_ip=f"10.0.0.{i}",
                dst_port=443 if i % 2 == 0 else 80,
                proto="tcp",
                bytes_out=100,
                timestamp=datetime(2024, 1, 1, 10 + i, 0),
            )
        
        assert sketch.flow_count == 10
        assert sketch.bytes_out == 1000
        assert sketch.peer_diversity >= 8  # ~10 unique peers
        assert sketch.port_diversity >= 1  # 2 unique ports (tcp/443, tcp/80)
    
    def test_in_out_ratio_client(self):
        """Test in/out ratio for client behavior."""
        sketch = EndpointSketch(endpoint_id="aa:bb:cc:dd:ee:ff")
        
        # Client sends more than receives
        sketch.bytes_out = 10000
        sketch.bytes_in = 1000
        
        assert sketch.in_out_ratio < 0.2  # Mostly sender
    
    def test_in_out_ratio_server(self):
        """Test in/out ratio for server behavior."""
        sketch = EndpointSketch(endpoint_id="aa:bb:cc:dd:ee:ff")
        
        # Server receives more than sends
        sketch.bytes_out = 1000
        sketch.bytes_in = 10000
        
        assert sketch.in_out_ratio > 0.8  # Mostly receiver
    
    def test_active_hours_bitmap(self):
        """Test active hours tracking."""
        sketch = EndpointSketch(endpoint_id="aa:bb:cc:dd:ee:ff")
        
        # Record flows at hours 9, 10, 11 (business hours)
        for hour in [9, 10, 11]:
            sketch.record_flow(
                dst_ip="10.0.0.1",
                dst_port=443,
                proto="tcp",
                bytes_out=100,
                timestamp=datetime(2024, 1, 1, hour, 0),
            )
        
        assert sketch.active_hour_count == 3
        # Check specific bits
        assert sketch.active_hours & (1 << 9)  # Hour 9 set
        assert sketch.active_hours & (1 << 10)  # Hour 10 set
        assert sketch.active_hours & (1 << 11)  # Hour 11 set
        assert not (sketch.active_hours & (1 << 0))  # Hour 0 not set
    
    def test_service_tracking(self):
        """Test service name tracking."""
        sketch = EndpointSketch(endpoint_id="aa:bb:cc:dd:ee:ff")
        
        sketch.record_flow(
            dst_ip="10.0.0.1",
            dst_port=443,
            proto="tcp",
            bytes_out=100,
            service_name="HTTPS",
        )
        
        assert sketch.service_diversity >= 1
    
    def test_merge_sketches(self):
        """Test merging two sketches."""
        sketch1 = EndpointSketch(endpoint_id="aa:bb:cc:dd:ee:ff")
        sketch2 = EndpointSketch(endpoint_id="aa:bb:cc:dd:ee:ff")
        
        # Add different flows to each
        for i in range(5):
            sketch1.record_flow(
                dst_ip=f"10.0.0.{i}",
                dst_port=443,
                proto="tcp",
                bytes_out=100,
            )
        for i in range(5, 10):
            sketch2.record_flow(
                dst_ip=f"10.0.0.{i}",
                dst_port=80,
                proto="tcp",
                bytes_out=200,
            )
        
        # Merge
        sketch1.merge(sketch2)
        
        assert sketch1.flow_count == 10
        assert sketch1.bytes_out == 1500
        assert sketch1.peer_diversity >= 8  # ~10 unique peers
    
    def test_merge_different_endpoints_fails(self):
        """Test that merging different endpoints fails."""
        sketch1 = EndpointSketch(endpoint_id="aa:bb:cc:dd:ee:ff")
        sketch2 = EndpointSketch(endpoint_id="11:22:33:44:55:66")
        
        with pytest.raises(ValueError):
            sketch1.merge(sketch2)
    
    def test_memory_estimation(self):
        """Test memory usage estimation."""
        sketch = EndpointSketch(endpoint_id="aa:bb:cc:dd:ee:ff")
        
        # Should be roughly 10KB (as designed)
        memory = sketch.memory_bytes()
        assert 5000 <= memory <= 50000
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        sketch = EndpointSketch(endpoint_id="aa:bb:cc:dd:ee:ff")
        sketch.record_flow(
            dst_ip="10.0.0.1",
            dst_port=443,
            proto="tcp",
            bytes_out=100,
            timestamp=datetime(2024, 1, 1, 10, 0),
        )
        
        d = sketch.to_dict()
        
        assert d["endpoint_id"] == "aa:bb:cc:dd:ee:ff"
        assert d["flow_count"] == 1
        assert d["bytes_out"] == 100
        assert d["peer_diversity"] >= 1
        assert d["first_seen"] is not None
    
    def test_identity_enrichment(self):
        """Test identity context fields."""
        sketch = EndpointSketch(endpoint_id="aa:bb:cc:dd:ee:ff")
        
        # Enrich with identity
        sketch.user_id = "U00001"
        sketch.username = "jsmith"
        sketch.ad_groups = ["Engineering-Users", "All-Employees"]
        sketch.ise_profile = "CorporateLaptop"
        sketch.device_type = "laptop"
        
        d = sketch.to_dict()
        
        assert d["user_id"] == "U00001"
        assert d["username"] == "jsmith"
        assert len(d["ad_groups"]) == 2
        assert d["ise_profile"] == "CorporateLaptop"

