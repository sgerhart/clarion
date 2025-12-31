"""
Migration: Add ISE session SGT assignment tracking table.

Adds a table to track current SGT assignments from ISE sessions (via pxGrid).
This allows Clarion to compare its recommendations with actual ISE assignments.
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)


def migrate(conn: sqlite3.Connection):
    """Add ISE session SGT assignment tracking table."""
    cursor = conn.cursor()
    
    # ISE Current SGT Assignments (from pxGrid sessions)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ise_current_sgt_assignments (
            endpoint_id TEXT NOT NULL PRIMARY KEY,  -- MAC address
            user_id TEXT,  -- User ID if user-authenticated session
            session_id TEXT,  -- ISE session ID
            user_sgt INTEGER,  -- User SGT (if assigned)
            device_sgt INTEGER,  -- Device SGT (if assigned)
            current_sgt INTEGER,  -- Current SGT (user takes precedence over device)
            ise_profile TEXT,  -- ISE endpoint profile
            policy_set TEXT,  -- Policy set that matched
            authz_profile TEXT,  -- Authorization profile that was applied
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- When this assignment was recorded
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Last time this assignment was seen
            ip_address TEXT,  -- Current IP address
            switch_id TEXT,  -- Network device (switch/router)
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    # Indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ise_sgt_assignments_user ON ise_current_sgt_assignments(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ise_sgt_assignments_sgt ON ise_current_sgt_assignments(current_sgt)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ise_sgt_assignments_session ON ise_current_sgt_assignments(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ise_sgt_assignments_seen ON ise_current_sgt_assignments(last_seen)")
    
    logger.info("ISE session SGT assignment tracking table migration completed.")

