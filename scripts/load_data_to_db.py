#!/usr/bin/env python3
"""
Load Synthetic Data into Database

This script loads the synthetic data and stores it in the database
so it appears in the admin console.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from clarion.ingest.loader import load_dataset
from clarion.ingest.sketch_builder import build_sketches
from clarion.identity.resolver import enrich_sketches
from clarion.storage import get_database
from clarion.clustering.clusterer import EndpointClusterer
from clarion.clustering.labeling import SemanticLabeler
from clarion.clustering.sgt_mapper import generate_sgt_taxonomy
from clarion.policy.matrix import build_policy_matrix
from clarion.policy.sgacl import SGACLGenerator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Load data into database."""
    print("Loading synthetic data into database...")
    
    # Initialize database
    db = get_database()
    print("✅ Database initialized")
    
    # Load dataset
    print("\n1. Loading dataset...")
    data_path = Path(__file__).parent.parent / "data" / "raw" / "trustsec_copilot_synth_campus"
    if not data_path.exists():
        print(f"   ❌ Data path not found: {data_path}")
        sys.exit(1)
    dataset = load_dataset(str(data_path))
    print(f"   ✅ Loaded {len(dataset.flows)} flows")
    
    # Build sketches
    print("\n2. Building sketches...")
    store = build_sketches(dataset)
    print(f"   ✅ Built {len(store)} sketches")
    
    # Store sketches in database
    print("\n3. Storing sketches in database...")
    stored = 0
    for sketch in store:
        db.store_sketch(
            endpoint_id=sketch.endpoint_id,
            switch_id=sketch.switch_id or "SW-UNKNOWN",
            unique_peers=sketch.unique_peers.count(),
            unique_ports=sketch.unique_services.count(),
            bytes_in=sketch.bytes_in,
            bytes_out=sketch.bytes_out,
            flow_count=sketch.flow_count,
            first_seen=int(sketch.first_seen.timestamp()) if sketch.first_seen else 0,
            last_seen=int(sketch.last_seen.timestamp()) if sketch.last_seen else 0,
            active_hours=sketch.active_hours,
        )
        stored += 1
        if stored % 1000 == 0:
            print(f"   Stored {stored} sketches...")
    print(f"   ✅ Stored {stored} sketches in database")
    
    # Enrich with identity
    print("\n4. Enriching with identity...")
    enrich_sketches(store, dataset)
    
    # Store identity mappings
    print("\n5. Storing identity mappings...")
    identity_count = 0
    for sketch in store:
        if sketch.username or sketch.device_type or sketch.ad_groups:
            # Get IP from dataset if available
            ip_address = ""
            matching_flows = dataset.flows[dataset.flows['src_mac'] == sketch.endpoint_id]
            if len(matching_flows) > 0:
                ip_address = matching_flows.iloc[0]['src_ip']
            
            db.store_identity(
                ip_address=ip_address,
                mac_address=sketch.endpoint_id,
                user_name=sketch.username,
                device_name=sketch.device_type,
                ad_groups=sketch.ad_groups if sketch.ad_groups else None,
                ise_profile=sketch.ise_profile,
            )
            identity_count += 1
            if identity_count % 1000 == 0:
                print(f"   Stored {identity_count} identity mappings...")
    print(f"   ✅ Stored {identity_count} identity mappings")
    
    # Cluster
    print("\n6. Running clustering...")
    clusterer = EndpointClusterer(min_cluster_size=50, min_samples=10)
    result = clusterer.cluster(store)
    print(f"   ✅ Found {result.n_clusters} clusters")
    
    # Store clusters
    print("\n7. Storing clusters...")
    for cluster_id, size in result.cluster_sizes.items():
        db.store_cluster(
            cluster_id=cluster_id,
            endpoint_count=size,
        )
        # Store assignments
        for endpoint_id in result.get_cluster_members(cluster_id):
            db.assign_endpoint_to_cluster(endpoint_id, cluster_id)
    print(f"   ✅ Stored {result.n_clusters} clusters")
    
    # Label clusters
    print("\n8. Labeling clusters...")
    labeler = SemanticLabeler()
    labels = labeler.label_clusters(store, result)
    
    # Generate SGT taxonomy
    print("\n9. Generating SGT taxonomy...")
    taxonomy = generate_sgt_taxonomy(store, result)
    print(f"   ✅ Generated taxonomy with {len(taxonomy.recommendations)} SGTs")
    
    # Update cluster labels with SGT info and explanation
    from clarion.clustering.explanation import generate_cluster_explanation
    
    sgt_map = {rec.cluster_id: rec for rec in taxonomy.recommendations}
    for cluster_id, label in labels.items():
        sgt_rec = sgt_map.get(cluster_id)
        explanation = generate_cluster_explanation(label)
        db.store_cluster(
            cluster_id=cluster_id,
            cluster_label=label.name,
            sgt_value=sgt_rec.sgt_value if sgt_rec else None,
            sgt_name=sgt_rec.sgt_name if sgt_rec else None,
            explanation=explanation,
            primary_reason=label.primary_reason,
            confidence=label.confidence,
        )
    print(f"   ✅ Labeled {len(labels)} clusters with SGTs")
    
    # Build policy matrix
    print("\n10. Building policy matrix...")
    matrix = build_policy_matrix(dataset, store, result, taxonomy)
    print(f"   ✅ Built policy matrix with {matrix.n_cells} cells")
    
    # Generate policies
    print("\n11. Generating policies...")
    generator = SGACLGenerator()
    policies = generator.generate(matrix)
    print(f"   ✅ Generated {len(policies)} policies")
    
    # Store policies
    print("\n12. Storing policies...")
    import json
    for policy in policies:
        db.store_policy(
            policy_name=policy.name,
            src_sgt=policy.src_sgt,
            dst_sgt=policy.dst_sgt,
            action=policy.action,
            rules_json=json.dumps([r.to_dict() for r in policy.rules]),
        )
    print(f"   ✅ Stored {len(policies)} policies")
    
    # Summary
    print("\n" + "="*70)
    print("✅ DATA LOADED SUCCESSFULLY")
    print("="*70)
    stats = db.get_sketch_stats()
    print(f"Sketches: {stats.get('total_sketches', 0)}")
    print(f"Clusters: {len(db.get_clusters())}")
    print(f"Policies: {len(db.get_policies())}")
    print("\nNow start the admin console:")
    print("  python scripts/run_admin_console.py")
    print("="*70)

if __name__ == "__main__":
    main()

