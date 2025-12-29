"""
Migration: Add ISE configuration cache tables.

Adds tables to cache existing ISE TrustSec configuration (SGTs, authorization profiles, authorization policies)
for brownfield deployment support.
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)


def migrate(conn: sqlite3.Connection):
    """Add ISE configuration cache tables."""
    cursor = conn.cursor()
    
    # ISE SGTs cache
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ise_sgts (
            id TEXT PRIMARY KEY,  -- ISE SGT ID
            name TEXT NOT NULL,
            value INTEGER NOT NULL UNIQUE,
            description TEXT,
            generation_id TEXT,
            ise_server TEXT NOT NULL,  -- Which ISE server this came from
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ise_server, value)
        )
    """)
    
    # ISE Authorization Profiles cache
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ise_auth_profiles (
            id TEXT PRIMARY KEY,  -- ISE profile ID
            name TEXT NOT NULL,
            description TEXT,
            sgt_value INTEGER,  -- Extracted SGT value (NULL if no SGT assigned)
            access_type TEXT,
            authz_profile_type TEXT,
            ise_server TEXT NOT NULL,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            raw_data TEXT,  -- JSON string of full profile data for reference
            UNIQUE(ise_server, id)
        )
    """)
    
    # ISE Authorization Policies cache
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ise_auth_policies (
            id TEXT PRIMARY KEY,  -- ISE policy ID
            name TEXT NOT NULL,
            description TEXT,
            profile_id TEXT,  -- References ise_auth_profiles.id
            profile_name TEXT,  -- Profile name for quick lookup
            rank INTEGER,
            state TEXT,  -- enabled, disabled
            condition_summary TEXT,  -- Human-readable summary of policy conditions
            condition_data TEXT,  -- JSON string of full condition structure
            ise_server TEXT NOT NULL,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            raw_data TEXT,  -- JSON string of full policy data for reference
            UNIQUE(ise_server, id),
            FOREIGN KEY (profile_id) REFERENCES ise_auth_profiles(id)
        )
    """)
    
    # Indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ise_sgts_value ON ise_sgts(value)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ise_sgts_ise_server ON ise_sgts(ise_server)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ise_sgts_name ON ise_sgts(name)")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ise_auth_profiles_sgt ON ise_auth_profiles(sgt_value)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ise_auth_profiles_ise_server ON ise_auth_profiles(ise_server)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ise_auth_profiles_name ON ise_auth_profiles(name)")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ise_auth_policies_profile ON ise_auth_policies(profile_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ise_auth_policies_ise_server ON ise_auth_policies(ise_server)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ise_auth_policies_name ON ise_auth_policies(name)")
    
    logger.info("ISE configuration cache tables migration completed.")

