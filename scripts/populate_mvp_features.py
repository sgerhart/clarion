#!/usr/bin/env python3
"""
Populate MVP Categorization Engine Features

This script populates the new MVP tables from existing database data:
1. Generates cluster centroids from existing cluster assignments
2. Creates SGTs based on existing cluster labels
3. Assigns endpoints to SGTs based on cluster assignments

Usage:
    python scripts/populate_mvp_features.py [--sgt-start 10] [--dry-run]
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clarion.storage import get_database
from clarion.clustering.features import FeatureExtractor
from clarion.clustering.sgt_lifecycle import SGTLifecycleManager
from clarion.sketches import EndpointSketch
from clarion.ingest.sketch_builder import SketchStore
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_sketches_from_db(db, limit=None):
    """Load sketches from database into a SketchStore."""
    store = SketchStore()
    conn = db._get_connection()
    
    # Get all sketches with cluster assignments
    query = """
        SELECT s.endpoint_id, s.switch_id, s.unique_peers, s.unique_ports,
               s.bytes_in, s.bytes_out, s.flow_count,
               s.first_seen, s.last_seen, ca.cluster_id, ca.confidence
        FROM sketches s
        JOIN cluster_assignments ca ON s.endpoint_id = ca.endpoint_id
    """
    if limit:
        query += f" LIMIT {limit}"
    
    cursor = conn.execute(query)
    rows = cursor.fetchall()
    
    logger.info(f"Loading {len(rows)} sketches from database...")
    
    for row in rows:
        # Create EndpointSketch from database row
        sketch = EndpointSketch(
            endpoint_id=row['endpoint_id'],
            switch_id=row['switch_id'] or 'unknown',
        )
        sketch.unique_peers_count = row['unique_peers'] or 0
        sketch.unique_ports_count = row['unique_ports'] or 0
        sketch.bytes_in = row['bytes_in'] or 0
        sketch.bytes_out = row['bytes_out'] or 0
        sketch.flow_count = row['flow_count'] or 0
        
        # Store cluster assignment
        sketch.cluster_id = row['cluster_id']
        
        store._sketches[sketch.endpoint_id] = sketch
    
    logger.info(f"Loaded {len(store)} sketches")
    return store


def generate_centroids_from_clusters(db, store):
    """Generate centroids from existing cluster assignments."""
    from clarion.clustering.incremental import IncrementalClusterer
    from clarion.clustering.features import FeatureExtractor
    
    logger.info("Generating centroids from existing clusters...")
    
    # Extract features
    extractor = FeatureExtractor()
    features = extractor.extract_all(store)
    
    # Create a mock ClusterResult from existing assignments
    cluster_ids = set()
    endpoint_to_cluster = {}
    
    for sketch in store:
        if hasattr(sketch, 'cluster_id') and sketch.cluster_id is not None:
            cluster_id = sketch.cluster_id
            cluster_ids.add(cluster_id)
            endpoint_to_cluster[sketch.endpoint_id] = cluster_id
    
    # Calculate centroids for each cluster
    incremental = IncrementalClusterer(db=db)
    centroids_stored = 0
    
    for cluster_id in cluster_ids:
        # Get all endpoints in this cluster
        cluster_endpoints = [
            ep_id for ep_id, cid in endpoint_to_cluster.items() 
            if cid == cluster_id
        ]
        
        if len(cluster_endpoints) < 5:  # Skip clusters with too few members
            continue
        
        # Get feature vectors for this cluster
        cluster_features = [
            features[ep_id] for ep_id in cluster_endpoints 
            if ep_id in features
        ]
        
        if not cluster_features:
            continue
        
        # Calculate centroid (mean of feature vectors)
        import numpy as np
        feature_matrix = np.array([fv.to_array() for fv in cluster_features])
        centroid = feature_matrix.mean(axis=0).tolist()
        
        # Store centroid
        db.store_cluster_centroid(
            cluster_id=cluster_id,
            centroid=centroid,
            member_count=len(cluster_endpoints),
        )
        centroids_stored += 1
    
    logger.info(f"✅ Stored {centroids_stored} cluster centroids")
    return centroids_stored


def create_sgts_from_clusters(db, sgt_start=10):
    """Create SGTs based on existing cluster labels."""
    logger.info(f"Creating SGTs from clusters (starting at SGT {sgt_start})...")
    
    conn = db._get_connection()
    cursor = conn.execute("""
        SELECT DISTINCT cluster_id, cluster_label
        FROM clusters
        WHERE cluster_id != -1  -- Skip noise cluster
        ORDER BY cluster_id
    """)
    
    clusters = cursor.fetchall()
    
    manager = SGTLifecycleManager(db=db)
    sgt_map = {}  # cluster_id -> sgt_value
    sgt_value = sgt_start
    
    for row in clusters:
        cluster_id = row['cluster_id']
        cluster_label = row['cluster_label'] or f"Cluster {cluster_id}"
        
        # Create SGT based on cluster label
        category = "devices"
        if "Printer" in cluster_label:
            category = "devices"
        elif "Mobile" in cluster_label or "Phone" in cluster_label:
            category = "devices"
        elif "Workstation" in cluster_label or "Laptop" in cluster_label:
            category = "endpoints"
        elif "IoT" in cluster_label:
            category = "devices"
        elif "Server" in cluster_label:
            category = "servers"
        
        try:
            manager.create_sgt(
                sgt_value=sgt_value,
                sgt_name=cluster_label,
                category=category,
                description=f"Auto-generated from cluster {cluster_id}",
            )
            sgt_map[cluster_id] = sgt_value
            logger.info(f"  Created SGT {sgt_value}: {cluster_label} (cluster {cluster_id})")
            sgt_value += 1
        except ValueError as e:
            logger.warning(f"  Failed to create SGT for cluster {cluster_id}: {e}")
    
    logger.info(f"✅ Created {len(sgt_map)} SGTs")
    return sgt_map


def assign_endpoints_to_sgts(db, sgt_map):
    """Assign endpoints to SGTs based on cluster assignments."""
    logger.info("Assigning endpoints to SGTs...")
    
    conn = db._get_connection()
    
    # Get cluster assignments with confidence
    cursor = conn.execute("""
        SELECT ca.endpoint_id, ca.cluster_id, ca.confidence, ca.assigned_by
        FROM cluster_assignments ca
        WHERE ca.cluster_id != -1  -- Skip noise cluster
        AND ca.cluster_id IN ({})
    """.format(','.join(map(str, sgt_map.keys()))))
    
    assignments = cursor.fetchall()
    
    manager = SGTLifecycleManager(db=db)
    assigned_count = 0
    
    for row in assignments:
        endpoint_id = row['endpoint_id']
        cluster_id = row['cluster_id']
        confidence = row['confidence'] or 0.75  # Default confidence
        assigned_by = row['assigned_by'] or 'migration'
        
        if cluster_id not in sgt_map:
            continue
        
        sgt_value = sgt_map[cluster_id]
        
        try:
            manager.assign_endpoint(
                endpoint_id=endpoint_id,
                sgt_value=sgt_value,
                assigned_by=assigned_by,
                confidence=confidence,
                cluster_id=cluster_id,
            )
            assigned_count += 1
            
            if assigned_count % 1000 == 0:
                logger.info(f"  Assigned {assigned_count} endpoints...")
        except Exception as e:
            logger.warning(f"  Failed to assign endpoint {endpoint_id}: {e}")
    
    logger.info(f"✅ Assigned {assigned_count} endpoints to SGTs")
    return assigned_count


def main():
    parser = argparse.ArgumentParser(
        description="Populate MVP categorization engine features from existing data"
    )
    parser.add_argument(
        '--sgt-start',
        type=int,
        default=10,
        help='Starting SGT value (default: 10)'
    )
    parser.add_argument(
        '--skip-centroids',
        action='store_true',
        help='Skip centroid generation'
    )
    parser.add_argument(
        '--skip-sgts',
        action='store_true',
        help='Skip SGT creation and assignment'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of sketches to process (for testing)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")
    
    db = get_database()
    
    # Check current state
    conn = db._get_connection()
    
    cursor = conn.execute("SELECT COUNT(*) FROM sketches")
    sketch_count = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(*) FROM cluster_assignments")
    assignment_count = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(*) FROM clusters WHERE cluster_id != -1")
    cluster_count = cursor.fetchone()[0]
    
    logger.info(f"\n📊 Current Database State:")
    logger.info(f"   Sketches: {sketch_count:,}")
    logger.info(f"   Cluster Assignments: {assignment_count:,}")
    logger.info(f"   Clusters (excluding noise): {cluster_count}")
    logger.info("")
    
    if args.dry_run:
        logger.info("Would perform the following operations:")
        logger.info("  1. Generate centroids from existing cluster assignments")
        logger.info("  2. Create SGTs based on cluster labels")
        logger.info("  3. Assign endpoints to SGTs based on cluster assignments")
        return
    
    # Step 1: Generate centroids
    if not args.skip_centroids:
        logger.info("\n" + "="*60)
        logger.info("STEP 1: Generating Cluster Centroids")
        logger.info("="*60)
        store = load_sketches_from_db(db, limit=args.limit)
        generate_centroids_from_clusters(db, store)
    else:
        logger.info("⏭️  Skipping centroid generation")
    
    # Step 2: Create SGTs
    if not args.skip_sgts:
        logger.info("\n" + "="*60)
        logger.info("STEP 2: Creating SGTs from Clusters")
        logger.info("="*60)
        sgt_map = create_sgts_from_clusters(db, sgt_start=args.sgt_start)
        
        # Step 3: Assign endpoints to SGTs
        logger.info("\n" + "="*60)
        logger.info("STEP 3: Assigning Endpoints to SGTs")
        logger.info("="*60)
        assign_endpoints_to_sgts(db, sgt_map)
    else:
        logger.info("⏭️  Skipping SGT creation and assignment")
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("✅ POPULATION COMPLETE")
    logger.info("="*60)
    
    cursor = conn.execute("SELECT COUNT(*) FROM cluster_centroids")
    centroid_count = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(*) FROM sgt_registry WHERE is_active = 1")
    sgt_count = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(*) FROM sgt_membership")
    membership_count = cursor.fetchone()[0]
    
    logger.info(f"\n📈 New MVP Features:")
    logger.info(f"   Cluster Centroids: {centroid_count}")
    logger.info(f"   SGTs in Registry: {sgt_count}")
    logger.info(f"   SGT Memberships: {membership_count:,}")
    logger.info("")


if __name__ == "__main__":
    main()

