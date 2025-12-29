"""
Migration: Add user SGT assignment tables.

Adds user_sgt_membership and user_sgt_assignment_history tables for assigning
SGTs to users (separate from device SGT assignments).
"""
import sqlite3
import logging

logger = logging.getLogger(__name__)

def migrate(conn: sqlite3.Connection):
    """Add user SGT assignment tables."""
    cursor = conn.cursor()
    
    # User SGT Membership (dynamic assignments)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_sgt_membership (
            user_id TEXT NOT NULL PRIMARY KEY,
            sgt_value INTEGER NOT NULL,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            assigned_by TEXT,  -- 'clustering', 'manual', 'ise', 'traffic_analysis'
            confidence REAL,
            user_cluster_id INTEGER,  -- Which user cluster this came from
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (sgt_value) REFERENCES sgt_registry(sgt_value)
        )
    """)
    
    # User SGT Assignment History (audit trail)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_sgt_assignment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            sgt_value INTEGER NOT NULL,
            assigned_at TIMESTAMP NOT NULL,
            unassigned_at TIMESTAMP,
            assigned_by TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (sgt_value) REFERENCES sgt_registry(sgt_value)
        )
    """)
    
    # User Traffic Aggregation (aggregated traffic patterns per user)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_traffic_patterns (
            user_id TEXT NOT NULL PRIMARY KEY,
            total_bytes_in BIGINT DEFAULT 0,
            total_bytes_out BIGINT DEFAULT 0,
            total_flows INTEGER DEFAULT 0,
            unique_peers INTEGER DEFAULT 0,
            unique_services INTEGER DEFAULT 0,
            top_ports TEXT,  -- JSON array of top destination ports
            top_protocols TEXT,  -- JSON array of top protocols
            active_hours INTEGER DEFAULT 0,  -- Bitmap of active hours
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    # User-to-User Traffic Correlation
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_user_traffic (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            src_user_id TEXT NOT NULL,
            dst_user_id TEXT NOT NULL,
            total_bytes BIGINT DEFAULT 0,
            total_flows INTEGER DEFAULT 0,
            top_ports TEXT,  -- JSON array of top destination ports
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (src_user_id) REFERENCES users(user_id),
            FOREIGN KEY (dst_user_id) REFERENCES users(user_id),
            UNIQUE(src_user_id, dst_user_id)
        )
    """)
    
    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sgt_membership_sgt ON user_sgt_membership(sgt_value)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sgt_membership_cluster ON user_sgt_membership(user_cluster_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sgt_history_user ON user_sgt_assignment_history(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sgt_history_sgt ON user_sgt_assignment_history(sgt_value)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_traffic_patterns_updated ON user_traffic_patterns(last_updated)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_user_traffic_src ON user_user_traffic(src_user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_user_traffic_dst ON user_user_traffic(dst_user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_user_traffic_last_seen ON user_user_traffic(last_seen)")
    
    conn.commit()
    logger.info("User SGT assignment tables created successfully")

