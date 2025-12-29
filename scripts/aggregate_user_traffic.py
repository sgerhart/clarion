#!/usr/bin/env python3
"""
Aggregate User Traffic Patterns

This script aggregates network flows by user (across all their devices) to enable
user-based traffic pattern analysis and clustering. It populates the user_traffic_patterns
and user_user_traffic tables from NetFlow data.

Usage:
    python scripts/aggregate_user_traffic.py [--limit N] [--dry-run]
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clarion.storage import get_database
from clarion.analytics.user_traffic_aggregator import UserTrafficAggregator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate user traffic patterns from NetFlow data"
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of users to process (for testing)'
    )
    parser.add_argument(
        '--skip-user-to-user',
        action='store_true',
        help='Skip user-to-user traffic aggregation (faster)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")
        return
    
    db = get_database()
    
    # Check current state
    conn = db._get_connection()
    
    cursor = conn.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
    user_count = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(*) FROM user_device_associations WHERE is_active = 1")
    association_count = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(*) FROM netflow")
    flow_count = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(*) FROM user_traffic_patterns")
    existing_pattern_count = cursor.fetchone()[0]
    
    logger.info(f"\n📊 Current Database State:")
    logger.info(f"   Active Users: {user_count:,}")
    logger.info(f"   User-Device Associations: {association_count:,}")
    logger.info(f"   NetFlow Records: {flow_count:,}")
    logger.info(f"   Existing Traffic Patterns: {existing_pattern_count:,}")
    logger.info("")
    
    if flow_count == 0:
        logger.warning("⚠️  No NetFlow records found in database")
        logger.warning("   Please load NetFlow data first using load_flows_to_db.py or similar")
        return
    
    if association_count == 0:
        logger.warning("⚠️  No user-device associations found")
        logger.warning("   Please ensure users and associations are loaded")
        return
    
    aggregator = UserTrafficAggregator()
    
    # Step 1: Aggregate user traffic patterns
    logger.info("\n" + "="*60)
    logger.info("STEP 1: Aggregating User Traffic Patterns")
    logger.info("="*60)
    
    stats = aggregator.aggregate_user_traffic(limit=args.limit)
    
    logger.info(f"\n✅ User Traffic Aggregation Complete:")
    logger.info(f"   Users Processed: {stats['users_processed']:,}")
    logger.info(f"   Users with Traffic: {stats['users_with_traffic']:,}")
    logger.info(f"   Total Flows Aggregated: {stats['total_flows']:,}")
    
    # Step 2: Aggregate user-to-user traffic
    if not args.skip_user_to_user:
        logger.info("\n" + "="*60)
        logger.info("STEP 2: Aggregating User-to-User Traffic")
        logger.info("="*60)
        
        user_user_stats = aggregator.aggregate_user_to_user_traffic()
        
        logger.info(f"\n✅ User-to-User Traffic Aggregation Complete:")
        logger.info(f"   User Pairs: {user_user_stats['user_pairs']:,}")
        logger.info(f"   Total Flows: {user_user_stats['total_flows']:,}")
    else:
        logger.info("⏭️  Skipping user-to-user traffic aggregation")
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("✅ AGGREGATION COMPLETE")
    logger.info("="*60)
    
    cursor = conn.execute("SELECT COUNT(*) FROM user_traffic_patterns")
    final_pattern_count = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(*) FROM user_user_traffic")
    final_user_user_count = cursor.fetchone()[0]
    
    logger.info(f"\n📈 Final State:")
    logger.info(f"   User Traffic Patterns: {final_pattern_count:,}")
    if not args.skip_user_to_user:
        logger.info(f"   User-to-User Traffic Pairs: {final_user_user_count:,}")
    logger.info("")
    logger.info("Next steps:")
    logger.info("  - Run user clustering based on traffic patterns")
    logger.info("  - Generate user SGT recommendations")
    logger.info("")


if __name__ == "__main__":
    main()

