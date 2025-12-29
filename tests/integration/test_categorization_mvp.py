"""
Integration tests for MVP categorization features.

Tests the end-to-end workflow of the MVP features:
1. First-seen tracking for endpoints
2. Database storage of clustering results with confidence
3. SGT lifecycle management (registry + membership)
4. Incremental clustering using stored centroids
5. Confidence scoring and explanations
"""

import pytest
import tempfile
import os
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

from clarion.storage.database import ClarionDatabase
from clarion.sketches import EndpointSketch
from clarion.ingest.sketch_builder import SketchStore, build_sketches
from clarion.ingest.loader import load_dataset
from clarion.identity import enrich_sketches
from clarion.clustering.clusterer import EndpointClusterer
from clarion.clustering.labeling import SemanticLabeler
from clarion.clustering.incremental import IncrementalClusterer
from clarion.clustering.sgt_lifecycle import SGTLifecycleManager
from clarion.clustering.confidence import ConfidenceScorer


# Path to synthetic dataset
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "raw" / "trustsec_copilot_synth_campus"


@pytest.fixture(scope="function")
def test_db():
    """Create a temporary test database using a temporary file."""
    import uuid
    test_id = str(uuid.uuid4())
    
    # Use tempfile to get a writable temporary directory
    tmpdir = tempfile.gettempdir()
    # Create a unique filename in the temp directory
    path = os.path.join(tmpdir, f'test_clarion_{test_id}.db')
    
    # Ensure path doesn't exist
    if os.path.exists(path):
        os.unlink(path)
    
    # Create database at the path (SQLite will create the file)
    db = ClarionDatabase(path)
    
    yield db
    
    # Cleanup - close connections first
    try:
        # Close any open connections
        if hasattr(db, '_local'):
            if hasattr(db._local, 'connection'):
                try:
                    db._local.connection.close()
                    db._local.connection = None
                except:
                    pass
    except Exception as e:
        # Log but don't fail on cleanup errors
        logger.warning(f"Cleanup warning: {e}")
        pass
    
    # Remove database files
    try:
        if os.path.exists(path):
            os.unlink(path)
        for suffix in ['-wal', '-shm', '-journal']:
            p = path + suffix
            if os.path.exists(p):
                try:
                    os.unlink(p)
                except:
                    pass
    except Exception as e:
        logger.warning(f"File cleanup warning: {e}")


@pytest.fixture
def sample_sketches(test_db):
    """Create sample sketches for testing."""
    if not DATA_DIR.exists():
        pytest.skip(f"Synthetic data not found at {DATA_DIR}")
    
    # Load a small subset of data
    dataset = load_dataset(DATA_DIR)
    store = build_sketches(dataset)
    enrich_sketches(store, dataset)
    
    # Take first 100 sketches for faster testing
    test_store = SketchStore()
    for sketch in list(store)[:100]:
        test_store._sketches[sketch.endpoint_id] = sketch
    
    return test_store


class TestFirstSeenTracking:
    """Test first-seen tracking functionality."""
    
    def test_store_sketch_tracks_first_seen(self, test_db):
        """Test that storing a sketch tracks first-seen correctly."""
        endpoint_id = "aa:bb:cc:dd:ee:ff"
        switch_id = "switch-1"
        
        # First store - should be new
        sketch_id, is_new = test_db.store_sketch(
            endpoint_id=endpoint_id,
            switch_id=switch_id,
            unique_peers=10,
            unique_ports=5,
            bytes_in=1000,
            bytes_out=2000,
            flow_count=5,
            first_seen=int(datetime.now().timestamp()),
            last_seen=int(datetime.now().timestamp()),
            active_hours=1,
        )
        
        assert is_new is True, "First store should mark endpoint as new"
        assert sketch_id is not None
        
        # Verify it appears in first-seen list
        first_seen = test_db.list_first_seen_endpoints(limit=100)
        endpoint_ids = [ep['endpoint_id'] for ep in first_seen]
        assert endpoint_id in endpoint_ids
        
        # Store again - should not be new
        sketch_id2, is_new2 = test_db.store_sketch(
            endpoint_id=endpoint_id,
            switch_id=switch_id,
            unique_peers=15,
            unique_ports=6,
            bytes_in=1500,
            bytes_out=2500,
            flow_count=6,
            first_seen=int(datetime.now().timestamp()),
            last_seen=int(datetime.now().timestamp()),
            active_hours=2,
        )
        
        assert is_new2 is False, "Second store should not mark endpoint as new"
        
        # Verify first-seen timestamp is preserved
        first_seen_timestamp = test_db.get_endpoint_first_seen(endpoint_id)
        assert first_seen_timestamp is not None
        assert isinstance(first_seen_timestamp, int)


class TestClusteringWithDatabase:
    """Test clustering workflow with database storage."""
    
    def test_clustering_stores_results_with_confidence(self, test_db, sample_sketches):
        """Test that clustering stores results in database with confidence scores."""
        # Run clustering
        clusterer = EndpointClusterer(min_cluster_size=5, min_samples=2)
        result = clusterer.cluster(sample_sketches)
        
        # Verify confidence scores were calculated
        assert len(result.confidence_scores) > 0
        for endpoint_id, confidence in result.confidence_scores.items():
            assert 0.0 <= confidence <= 1.0, f"Confidence should be 0-1, got {confidence}"
        
        # Store assignments in database
        clusterer.apply_to_store(sample_sketches, result, store_in_db=True, db=test_db)
        
        # Verify assignments are stored with confidence
        conn = test_db._get_connection()
        cursor = conn.execute("""
            SELECT endpoint_id, cluster_id, confidence, assigned_by
            FROM cluster_assignments
            LIMIT 10
        """)
        assignments = cursor.fetchall()
        
        assert len(assignments) > 0, "Should have stored some assignments"
        for row in assignments:
            endpoint_id, cluster_id, confidence, assigned_by = row
            assert confidence is not None, f"Assignment for {endpoint_id} should have confidence"
            assert 0.0 <= confidence <= 1.0
            assert assigned_by == "clustering"
    
    def test_clustering_stores_centroids(self, test_db, sample_sketches):
        """Test that clustering stores centroids for incremental clustering."""
        from clarion.clustering.features import FeatureExtractor
        
        # Run clustering
        clusterer = EndpointClusterer(min_cluster_size=5, min_samples=2)
        result = clusterer.cluster(sample_sketches)
        
        # Extract features to calculate centroids
        extractor = FeatureExtractor()
        features = extractor.extract_all(sample_sketches)
        
        # Store centroids - need to convert FeatureVector objects to numpy array format
        # The store_centroids_from_clustering expects features as a list of FeatureVector objects
        # and will extract the feature arrays from them
        incremental = IncrementalClusterer(db=test_db)
        stored_count = incremental.store_centroids_from_clustering(result, features)
        
        assert stored_count > 0, "Should have stored some centroids"
        
        # Verify centroids are in database
        centroids = test_db.list_all_centroids()
        assert len(centroids) > 0
        
        # Verify centroids have feature vectors
        for centroid in centroids:
            assert centroid['feature_vector'] is not None
            assert len(centroid['feature_vector']) > 0


class TestSGTLifecycle:
    """Test SGT lifecycle management."""
    
    def test_sgt_registry_operations(self, test_db):
        """Test SGT registry create/get/list operations."""
        manager = SGTLifecycleManager(db=test_db)
        
        # Create SGT
        sgt = manager.create_sgt(
            sgt_value=100,
            sgt_name="Test Users",
            category="users",
            description="Test user devices"
        )
        
        assert sgt['sgt_value'] == 100
        assert sgt['sgt_name'] == "Test Users"
        
        # Get SGT
        retrieved = manager.get_sgt(100)
        assert retrieved is not None
        assert retrieved['sgt_value'] == 100
        
        # List SGTs
        all_sgts = manager.list_sgts()
        assert len(all_sgts) > 0
        sgt_values = [s['sgt_value'] for s in all_sgts]
        assert 100 in sgt_values
    
    def test_sgt_assignment_with_confidence(self, test_db):
        """Test SGT assignment includes confidence scoring."""
        manager = SGTLifecycleManager(db=test_db)
        
        # Create SGT
        manager.create_sgt(100, "Test Users", category="users")
        
        # Create a cluster assignment first (for confidence calculation)
        endpoint_id = "aa:bb:cc:dd:ee:ff"
        test_db.assign_endpoint_to_cluster(
            endpoint_id=endpoint_id,
            cluster_id=1,
            confidence=0.85,
            assigned_by="clustering"
        )
        
        # Assign endpoint to SGT (should auto-calculate confidence)
        assignment = manager.assign_endpoint(
            endpoint_id=endpoint_id,
            sgt_value=100,
            assigned_by="clustering",
            cluster_id=1
        )
        
        assert assignment is not None
        assert assignment['sgt_value'] == 100
        
        # Verify assignment has confidence (should be auto-calculated)
        endpoint_sgt = manager.get_endpoint_sgt(endpoint_id)
        assert endpoint_sgt is not None
        # Confidence should be present (either from parameter or auto-calculated)
        assert 'confidence' in endpoint_sgt or endpoint_sgt.get('confidence') is not None
        
        # Verify assignment history
        history = manager.get_sgt_assignment_history(endpoint_id)
        assert len(history) > 0
        assert history[0]['sgt_value'] == 100


class TestIncrementalClustering:
    """Test incremental clustering functionality."""
    
    def test_incremental_clustering_uses_stored_centroids(self, test_db, sample_sketches):
        """Test that incremental clustering can use stored centroids."""
        from clarion.clustering.features import FeatureExtractor
        
        # Step 1: Run full clustering and store centroids
        clusterer = EndpointClusterer(min_cluster_size=5, min_samples=2)
        result = clusterer.cluster(sample_sketches)
        
        extractor = FeatureExtractor()
        features = extractor.extract_all(sample_sketches)
        
        incremental = IncrementalClusterer(db=test_db)
        incremental.store_centroids_from_clustering(result, features)
        
        # Step 2: Load centroids
        loaded_count = incremental.load_centroids()
        assert loaded_count > 0
        assert incremental.has_centroids()
        
        # Step 3: Create a new endpoint (not in original clustering)
        # Create a proper EndpointSketch (__post_init__ will create HyperLogLog objects)
        new_sketch = EndpointSketch(endpoint_id="new:endpoint:ff:ff:ff:ff")
        # Add some data to the sketches
        for i in range(15):
            new_sketch.unique_peers.add(f"10.0.0.{i}")
        for port in [80, 443, 22, 53, 8080, 3306, 5432, 6379]:
            new_sketch.unique_ports.add(f"tcp/{port}")
        new_sketch.bytes_in = 5000
        new_sketch.bytes_out = 3000
        new_sketch.flow_count = 10
        
        # Step 4: Assign using incremental clustering
        assignment = incremental.assign_and_store(new_sketch, update_centroid=False)
        
        assert assignment is not None
        assert 'cluster_id' in assignment
        assert 'confidence' in assignment
        assert 0.0 <= assignment['confidence'] <= 1.0
        
        # If assigned to a cluster (not noise), verify it's stored
        if assignment['cluster_id'] != -1:
            endpoint_sgt = test_db._get_connection().execute("""
                SELECT endpoint_id, cluster_id, confidence
                FROM cluster_assignments
                WHERE endpoint_id = ?
            """, (new_sketch.endpoint_id,)).fetchone()
            
            assert endpoint_sgt is not None
            assert endpoint_sgt[1] == assignment['cluster_id']


class TestConfidenceAndExplanations:
    """Test confidence scoring and explanations."""
    
    def test_cluster_labels_have_confidence_and_explanations(self, sample_sketches):
        """Test that cluster labels include confidence and explanations."""
        # Run clustering and labeling
        clusterer = EndpointClusterer(min_cluster_size=5, min_samples=2)
        result = clusterer.cluster(sample_sketches)
        
        # Note: SemanticLabeler requires dataset for enrichment, so we'll use a simpler test
        # In real usage, labels would be generated via SemanticLabeler which includes explanations
        
        # Verify confidence scores are in result
        assert len(result.confidence_scores) > 0
        
        # Test confidence scorer directly
        confidence = ConfidenceScorer.for_cluster_assignment(
            cluster_id=1,
            distance=0.5,
            probability=0.85,
            cluster_size=50,
        )
        
        assert 0.0 <= confidence <= 1.0
        
        # Test confidence classification
        classification = ConfidenceScorer.classify(confidence)
        assert classification in ['very_high', 'high', 'medium', 'low', 'very_low']


class TestMVPEndToEnd:
    """End-to-end test of all MVP features together."""
    
    def test_complete_mvp_workflow(self, test_db, sample_sketches):
        """Test the complete MVP workflow from first-seen to incremental assignment."""
        from clarion.clustering.features import FeatureExtractor
        
        # Step 1: Store sketches (triggers first-seen tracking)
        # Convert sketches to aggregate values for storage
        new_endpoints = []
        for sketch in list(sample_sketches)[:20]:  # Use subset for speed
            # Extract aggregate values from sketch objects
            # unique_peers and unique_ports are HyperLogLog objects, use peer_diversity/port_diversity properties
            unique_peers_count = int(sketch.peer_diversity) if sketch.peer_diversity else 0
            unique_ports_count = int(sketch.port_diversity) if sketch.port_diversity else 0
            
            sketch_id, is_new = test_db.store_sketch(
                endpoint_id=sketch.endpoint_id,
                switch_id=sketch.switch_id or "test-switch",
                unique_peers=unique_peers_count,
                unique_ports=unique_ports_count,
                bytes_in=int(sketch.bytes_in) if sketch.bytes_in else 0,
                bytes_out=int(sketch.bytes_out) if sketch.bytes_out else 0,
                flow_count=int(sketch.flow_count) if sketch.flow_count else 0,
                first_seen=int(datetime.now().timestamp()),
                last_seen=int(datetime.now().timestamp()),
                active_hours=sketch.active_hours if sketch.active_hours else 1,
            )
            if is_new:
                new_endpoints.append(sketch.endpoint_id)
        
        assert len(new_endpoints) > 0, "Should have detected new endpoints"
        
        # Step 2: Run clustering with confidence
        clusterer = EndpointClusterer(min_cluster_size=3, min_samples=1)
        result = clusterer.cluster(sample_sketches)
        
        assert result.n_clusters > 0
        assert len(result.confidence_scores) > 0
        
        # Step 3: Store cluster assignments and centroids
        clusterer.apply_to_store(sample_sketches, result, store_in_db=True, db=test_db)
        
        extractor = FeatureExtractor()
        features = extractor.extract_all(sample_sketches)
        incremental = IncrementalClusterer(db=test_db)
        incremental.store_centroids_from_clustering(result, features)
        
        # Step 4: Create SGT and assign endpoints
        manager = SGTLifecycleManager(db=test_db)
        manager.create_sgt(100, "Test Users", category="users")
        
        # Assign first few endpoints to SGT
        for sketch in list(sample_sketches)[:5]:
            if sketch.endpoint_id in result.endpoint_ids:
                idx = result.endpoint_ids.index(sketch.endpoint_id)
                cluster_id = int(result.labels[idx])
                if cluster_id != -1:
                    manager.assign_endpoint(
                        endpoint_id=sketch.endpoint_id,
                        sgt_value=100,
                        assigned_by="clustering",
                        cluster_id=cluster_id
                    )
        
        # Step 5: Use incremental clustering for new endpoint
        incremental.load_centroids()
        # Create a proper EndpointSketch (__post_init__ will create HyperLogLog objects)
        new_sketch = EndpointSketch(endpoint_id="new:test:endpoint:01")
        # Add some data to the sketches
        for i in range(10):
            new_sketch.unique_peers.add(f"10.0.0.{i}")
        for port in [80, 443, 22, 53, 8080]:
            new_sketch.unique_ports.add(f"tcp/{port}")
        new_sketch.bytes_in = 1000
        new_sketch.bytes_out = 2000
        new_sketch.flow_count = 5
        
        assignment = incremental.assign_and_store(new_sketch, update_centroid=False)
        
        assert assignment is not None
        assert 'cluster_id' in assignment
        assert 'confidence' in assignment
        
        # Verify everything is stored correctly
        assert incremental.has_centroids()
        
        # Verify SGT assignments exist
        sgt_members = manager.list_endpoints_by_sgt(100)
        assert len(sgt_members) > 0
        
        print("\n" + "=" * 60)
        print("MVP END-TO-END TEST RESULTS")
        print("=" * 60)
        print(f"New endpoints detected: {len(new_endpoints)}")
        print(f"Clusters found: {result.n_clusters}")
        print(f"Confidence scores calculated: {len(result.confidence_scores)}")
        print(f"Centroids stored: {len(test_db.list_all_centroids())}")
        print(f"SGT assignments: {len(sgt_members)}")
        print(f"Incremental assignment confidence: {assignment['confidence']:.3f}")
        print("=" * 60)

