#!/usr/bin/env python3
"""
Populate SGTs from Existing Clusters

Simplified script that creates SGTs and assigns endpoints based on existing
cluster assignments. This is the recommended first step to populate MVP features.

Usage:
    python scripts/populate_sgts_from_clusters.py [--sgt-start 10]
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clarion.storage import get_database
from clarion.clustering.sgt_lifecycle import SGTLifecycleManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    
    if not clusters:
        logger.warning("No clusters found (excluding noise cluster)")
        return {}
    
    manager = SGTLifecycleManager(db=db)
    sgt_map = {}  # cluster_id -> sgt_value
    sgt_value = sgt_start
    
    for row in clusters:
        cluster_id = row['cluster_id']
        cluster_label = row['cluster_label'] or f"Cluster {cluster_id}"
        
        # Determine category based on cluster label
        category = "devices"
        label_lower = cluster_label.lower()
        if "printer" in label_lower:
            category = "devices"
        elif "mobile" in label_lower or "phone" in label_lower:
            category = "devices"
        elif "workstation" in label_lower or "laptop" in label_lower:
            category = "endpoints"
        elif "iot" in label_lower:
            category = "devices"
        elif "server" in label_lower:
            category = "servers"
        elif "user" in label_lower:
            category = "users"
        
        try:
            manager.create_sgt(
                sgt_value=sgt_value,
                sgt_name=cluster_label,
                category=category,
                description=f"Auto-generated from cluster {cluster_id}",
            )
            sgt_map[cluster_id] = sgt_value
            logger.info(f"  ✅ Created SGT {sgt_value}: {cluster_label} (cluster {cluster_id})")
            sgt_value += 1
        except ValueError as e:
            logger.warning(f"  ⚠️  Failed to create SGT for cluster {cluster_id}: {e}")
    
    logger.info(f"✅ Created {len(sgt_map)} SGTs")
    return sgt_map


def assign_endpoints_to_sgts(db, sgt_map):
    """Assign endpoints to SGTs based on cluster assignments."""
    logger.info("Assigning endpoints to SGTs...")
    
    if not sgt_map:
        logger.warning("No SGTs to assign endpoints to")
        return 0
    
    conn = db._get_connection()
    
    # Get cluster assignments with confidence
    cluster_ids_str = ','.join(map(str, sgt_map.keys()))
    cursor = conn.execute(f"""
        SELECT ca.endpoint_id, ca.cluster_id, ca.confidence, ca.assigned_by
        FROM cluster_assignments ca
        WHERE ca.cluster_id != -1  -- Skip noise cluster
        AND ca.cluster_id IN ({cluster_ids_str})
    """)
    
    assignments = cursor.fetchall()
    
    if not assignments:
        logger.warning("No cluster assignments found")
        return 0
    
    manager = SGTLifecycleManager(db=db)
    assigned_count = 0
    error_count = 0
    
    for row in assignments:
        endpoint_id = row['endpoint_id']
        cluster_id = row['cluster_id']
        confidence = row['confidence']
        assigned_by = row['assigned_by'] or 'migration'
        
        if cluster_id not in sgt_map:
            continue
        
        sgt_value = sgt_map[cluster_id]
        
        # Default confidence if None
        if confidence is None:
            confidence = 0.75
        
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
                logger.info(f"  Assigned {assigned_count:,} endpoints...")
        except Exception as e:
            error_count += 1
            if error_count <= 5:  # Only log first few errors
                logger.warning(f"  Failed to assign endpoint {endpoint_id}: {e}")
    
    if error_count > 5:
        logger.warning(f"  ... and {error_count - 5} more errors")
    
    logger.info(f"✅ Assigned {assigned_count:,} endpoints to SGTs")
    if error_count > 0:
        logger.warning(f"⚠️  {error_count} assignment errors occurred")
    
    return assigned_count


def main():
    parser = argparse.ArgumentParser(
        description="Create SGTs and assign endpoints from existing cluster assignments"
    )
    parser.add_argument(
        '--sgt-start',
        type=int,
        default=10,
        help='Starting SGT value (default: 10)'
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
    
    cursor = conn.execute("SELECT COUNT(*) FROM clusters WHERE cluster_id != -1")
    cluster_count = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(*) FROM cluster_assignments WHERE cluster_id != -1")
    assignment_count = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(*) FROM sgt_registry WHERE is_active = 1")
    existing_sgt_count = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(*) FROM sgt_membership")
    existing_membership_count = cursor.fetchone()[0]
    
    logger.info(f"\n📊 Current Database State:")
    logger.info(f"   Clusters (excluding noise): {cluster_count}")
    logger.info(f"   Cluster Assignments: {assignment_count:,}")
    logger.info(f"   Existing SGTs: {existing_sgt_count}")
    logger.info(f"   Existing SGT Memberships: {existing_membership_count:,}")
    logger.info("")
    
    if args.dry_run:
        logger.info("Would perform the following operations:")
        logger.info("  1. Create SGTs from cluster labels")
        logger.info("  2. Assign endpoints to SGTs based on cluster assignments")
        return
    
    if existing_sgt_count > 0:
        logger.warning(f"⚠️  Found {existing_sgt_count} existing SGTs")
        logger.warning("  This script will create additional SGTs (will not overwrite existing)")
    
    if existing_membership_count > 0:
        logger.warning(f"⚠️  Found {existing_membership_count:,} existing SGT memberships")
        logger.warning("  New assignments will be added (endpoints may have multiple SGT assignments)")
    
    # Step 1: Create SGTs
    logger.info("\n" + "="*60)
    logger.info("STEP 1: Creating SGTs from Clusters")
    logger.info("="*60)
    sgt_map = create_sgts_from_clusters(db, sgt_start=args.sgt_start)
    
    if not sgt_map:
        logger.error("❌ No SGTs were created. Exiting.")
        return
    
    # Step 2: Assign endpoints to SGTs
    logger.info("\n" + "="*60)
    logger.info("STEP 2: Assigning Endpoints to SGTs")
    logger.info("="*60)
    assigned_count = assign_endpoints_to_sgts(db, sgt_map)
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("✅ POPULATION COMPLETE")
    logger.info("="*60)
    
    cursor = conn.execute("SELECT COUNT(*) FROM sgt_registry WHERE is_active = 1")
    final_sgt_count = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(*) FROM sgt_membership")
    final_membership_count = cursor.fetchone()[0]
    
    logger.info(f"\n📈 Results:")
    logger.info(f"   SGTs Created: {len(sgt_map)}")
    logger.info(f"   Endpoints Assigned: {assigned_count:,}")
    logger.info(f"   Total SGTs in Registry: {final_sgt_count}")
    logger.info(f"   Total SGT Memberships: {final_membership_count:,}")
    logger.info("")
    logger.info("💡 Note: Centroids can be generated later when re-running clustering")
    logger.info("")


if __name__ == "__main__":
    main()

