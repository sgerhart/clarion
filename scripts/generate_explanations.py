#!/usr/bin/env python3
"""
Generate Explanations for Existing Clusters

This script generates explanations for clusters that were created before
the explanation feature was added. It doesn't require reloading all data.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from clarion.storage import get_database
from clarion.clustering.explanation import generate_cluster_explanation
from clarion.clustering.labeling import ClusterLabel
from clarion.ingest.loader import load_dataset
from clarion.ingest.sketch_builder import build_sketches
from clarion.identity.resolver import enrich_sketches
from clarion.clustering.clusterer import EndpointClusterer
from clarion.clustering.labeling import SemanticLabeler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_explanations_for_existing_clusters():
    """Generate explanations for clusters that don't have them yet."""
    print("Generating explanations for existing clusters...")
    
    db = get_database()
    conn = db._get_connection()
    
    # Get all clusters (force regeneration, especially for cluster -1)
    # We want to regenerate explanations to fix the noise cluster explanation
    cursor = conn.execute("""
        SELECT cluster_id, cluster_label, endpoint_count
        FROM clusters
        ORDER BY cluster_id
    """)
    clusters_to_update = cursor.fetchall()
    
    if not clusters_to_update:
        print("⚠️  No clusters found in database!")
        return
    
    print(f"Found {len(clusters_to_update)} clusters to process (regenerating all explanations)")
    
    print(f"Found {len(clusters_to_update)} clusters without explanations")
    
    # We need to rebuild the cluster labels to get the explanation data
    # Load the dataset to get identity information
    print("\n1. Loading dataset for identity context...")
    data_path = Path(__file__).parent.parent / "data" / "raw" / "trustsec_copilot_synth_campus"
    if not data_path.exists():
        print(f"   ❌ Data path not found: {data_path}")
        print("   Skipping explanation generation (will be generated for new clusters)")
        return
    
    dataset = load_dataset(str(data_path))
    print(f"   ✅ Loaded dataset")
    
    # Build sketches
    print("\n2. Building sketches...")
    store = build_sketches(dataset)
    print(f"   ✅ Built {len(store)} sketches")
    
    # Enrich with identity
    print("\n3. Enriching with identity...")
    enrich_sketches(store, dataset)
    print(f"   ✅ Enriched sketches")
    
    # Get cluster assignments from database
    print("\n4. Getting cluster assignments from database...")
    cluster_assignments = {}
    cursor = conn.execute("SELECT endpoint_id, cluster_id FROM cluster_assignments")
    for row in cursor.fetchall():
        endpoint_id = row[0]
        cluster_id = row[1]
        if cluster_id not in cluster_assignments:
            cluster_assignments[cluster_id] = []
        cluster_assignments[cluster_id].append(endpoint_id)
    
    print(f"   ✅ Found assignments for {len(cluster_assignments)} clusters")
    
    # Generate labels for clusters
    print("\n5. Generating cluster labels...")
    labeler = SemanticLabeler()
    
    # Build endpoint lookup
    endpoint_lookup = {s.endpoint_id: s for s in store}
    
    updated_count = 0
    for cluster_row in clusters_to_update:
        cluster_id = cluster_row[0]
        cluster_label_name = cluster_row[1]
        
        # Get cluster members
        member_ids = cluster_assignments.get(cluster_id, [])
        if not member_ids:
            print(f"   ⚠️  Cluster {cluster_id} has no members, skipping")
            continue
        
        members = [
            endpoint_lookup[eid]
            for eid in member_ids
            if eid in endpoint_lookup
        ]
        
        if not members:
            print(f"   ⚠️  Cluster {cluster_id} has no matching sketches, skipping")
            continue
        
        # Special handling for noise cluster (-1)
        if cluster_id == -1:
            # Create noise cluster label with proper metadata
            from clarion.clustering.labeling import ClusterLabel
            from collections import Counter
            
            # Calculate statistics for noise cluster
            ad_groups_list = []
            ise_profiles_list = []
            device_types_list = []
            for m in members:
                ad_groups_list.extend(m.ad_groups or [])
                if m.ise_profile:
                    ise_profiles_list.append(m.ise_profile)
                if m.device_type:
                    device_types_list.append(m.device_type)
            
            from collections import Counter
            ad_counter = Counter(ad_groups_list)
            ise_counter = Counter(ise_profiles_list)
            device_counter = Counter(device_types_list)
            
            n_members = len(members)
            avg_peer_diversity = sum(m.peer_diversity for m in members) / n_members if n_members > 0 else 0
            avg_in_out_ratio = sum(m.in_out_ratio for m in members) / n_members if n_members > 0 else 0
            
            label = ClusterLabel(
                cluster_id=-1,
                name="Unclustered (Noise)",
                primary_reason="Did not fit any cluster pattern - outlier behavior",
                confidence=0.0,
                member_count=n_members,
                top_ad_groups=[(g, c/n_members) for g, c in ad_counter.most_common(5)],
                top_ise_profiles=[(p, c/n_members) for p, c in ise_counter.most_common(5)],
                top_device_types=[(d, c/n_members) for d, c in device_counter.most_common(5)],
                avg_peer_diversity=avg_peer_diversity,
                avg_in_out_ratio=avg_in_out_ratio,
                is_server_cluster=False,
            )
        else:
            # Generate label for regular cluster
            label = labeler._label_cluster(cluster_id, members)
        
        # Generate explanation (handles noise cluster -1 specially)
        explanation = generate_cluster_explanation(label)
        
        # Update database
        db.store_cluster(
            cluster_id=cluster_id,
            cluster_label=label.name if not cluster_label_name else cluster_label_name,
            explanation=explanation,
            primary_reason=label.primary_reason,
            confidence=label.confidence,
        )
        
        updated_count += 1
        print(f"   ✅ Generated explanation for Cluster {cluster_id}: {label.name}")
    
    print(f"\n✅ Generated explanations for {updated_count} clusters!")
    print("\nYou can now view explanations in the Groups page.")


if __name__ == "__main__":
    generate_explanations_for_existing_clusters()

