"""
Migration: Add user database tables.

Adds users, user_device_associations, and ad_group_memberships tables.
"""
import sqlite3
import logging

logger = logging.getLogger(__name__)

def migrate(conn: sqlite3.Connection):
    """Add user database tables."""
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT,
            display_name TEXT,
            department TEXT,
            title TEXT,
            is_active BOOLEAN DEFAULT 1,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    
    # User-device associations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_device_associations (
            association_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            endpoint_id TEXT NOT NULL,
            ip_address TEXT,
            association_type TEXT NOT NULL,
            session_id TEXT,
            first_associated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_associated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_uda_user ON user_device_associations(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_uda_endpoint ON user_device_associations(endpoint_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_uda_active ON user_device_associations(is_active, last_associated)")
    
    # AD group memberships table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ad_group_memberships (
            membership_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            group_id TEXT NOT NULL,
            group_name TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_verified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(user_id, group_id)
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memberships_user ON ad_group_memberships(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memberships_group ON ad_group_memberships(group_id)")
    
    conn.commit()
    logger.info("User database tables created successfully")

