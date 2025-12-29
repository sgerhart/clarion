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
    
    # Load users from ad_users.csv
    print("\n5. Loading users from AD data...")
    user_count = 0
    if len(dataset.ad_users) > 0:
        # Create a mapping of username to user_id for later use
        username_to_user_id = {}
        for _, ad_user in dataset.ad_users.iterrows():
            user_id = ad_user.get('user_id', '')
            username = ad_user.get('samaccountname', '')
            if not user_id or not username:
                continue
            
            # Extract user details
            email = ad_user.get('email', '')
            first_name = ad_user.get('first_name', '')
            last_name = ad_user.get('last_name', '')
            display_name = f"{first_name} {last_name}".strip() if first_name or last_name else username
            department = ad_user.get('department', '')
            title = ad_user.get('title', '')
            
            # Create or update user
            db.create_user(
                user_id=user_id,
                username=username,
                email=email if email else None,
                display_name=display_name if display_name else None,
                department=department if department else None,
                title=title if title else None,
                source="ad"
            )
            username_to_user_id[username] = user_id
            user_count += 1
            if user_count % 100 == 0:
                print(f"   Loaded {user_count} users...")
        print(f"   ✅ Loaded {user_count} users into database")
    else:
        print("   ⚠️  No AD users found in dataset")
    
    # Create user-device associations from ISE sessions
    print("\n6. Creating user-device associations from ISE sessions...")
    association_count = 0
    username_to_user_id = {}
    if len(dataset.ad_users) > 0:
        # Build username to user_id mapping
        for _, ad_user in dataset.ad_users.iterrows():
            user_id = ad_user.get('user_id', '')
            username = ad_user.get('samaccountname', '')
            if user_id and username:
                username_to_user_id[username] = user_id
    
    if len(dataset.ise_sessions) > 0 and len(username_to_user_id) > 0:
        for _, session in dataset.ise_sessions.iterrows():
            username = session.get('username')
            mac_address = session.get('mac', '')
            ip_address = session.get('ip', '')
            session_id = session.get('session_id', '')
            
            if not username or not mac_address or username not in username_to_user_id:
                continue
            
            user_id = username_to_user_id[username]
            
            # Create user-device association
            db.create_user_device_association(
                user_id=user_id,
                endpoint_id=mac_address,
                ip_address=ip_address if ip_address else None,
                association_type="ise_session",
                session_id=session_id if session_id else None
            )
            association_count += 1
            if association_count % 100 == 0:
                print(f"   Created {association_count} associations...")
        print(f"   ✅ Created {association_count} user-device associations")
    else:
        print("   ⚠️  No ISE sessions found or users not loaded")
    
    # Load AD group memberships
    print("\n7. Loading AD group memberships...")
    membership_count = 0
    if len(dataset.ad_group_membership) > 0 and len(dataset.ad_groups) > 0:
        # Create a mapping of group_id to group_name
        group_id_to_name = {}
        for _, group in dataset.ad_groups.iterrows():
            group_id = group.get('group_id', '')
            group_name = group.get('group_name', '')
            if group_id and group_name:
                group_id_to_name[group_id] = group_name
        
        for _, membership in dataset.ad_group_membership.iterrows():
            user_id = membership.get('user_id', '')
            group_id = membership.get('group_id', '')
            
            if not user_id or not group_id:
                continue
            
            group_name = group_id_to_name.get(group_id, group_id)
            
            # Create AD group membership
            db.create_ad_group_membership(
                user_id=user_id,
                group_id=group_id,
                group_name=group_name
            )
            membership_count += 1
            if membership_count % 100 == 0:
                print(f"   Loaded {membership_count} group memberships...")
        print(f"   ✅ Loaded {membership_count} AD group memberships")
    else:
        print("   ⚠️  No AD group memberships found")
    
    # Store identity mappings
    print("\n8. Storing identity mappings...")
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
    print("\n9. Running clustering...")
    clusterer = EndpointClusterer(min_cluster_size=50, min_samples=10)
    result = clusterer.cluster(store)
    print(f"   ✅ Found {result.n_clusters} clusters")
    
    # Store clusters
    print("\n10. Storing clusters...")
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
    print("\n11. Labeling clusters...")
    labeler = SemanticLabeler()
    labels = labeler.label_clusters(store, result)
    
    # Generate SGT taxonomy
    print("\n12. Generating SGT taxonomy...")
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
    print("\n13. Building policy matrix...")
    matrix = build_policy_matrix(dataset, store, result, taxonomy)
    print(f"   ✅ Built policy matrix with {matrix.n_cells} cells")
    
    # Generate policies
    print("\n14. Generating policies...")
    generator = SGACLGenerator()
    policies = generator.generate(matrix)
    print(f"   ✅ Generated {len(policies)} policies")
    
    # Store policies
    print("\n15. Storing policies...")
    import json
    for policy in policies:
        db.store_policy(
            policy_name=policy.name,
            src_sgt=policy.src_sgt,
            dst_sgt=policy.dst_sgt,
            action=policy.default_action,
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
    # Get user count for summary
    all_users = db.list_users(limit=10000)
    print(f"Users: {len(all_users)}")
    print("\nNow start the admin console:")
    print("  python scripts/run_admin_console.py")
    print("="*70)

if __name__ == "__main__":
    main()

