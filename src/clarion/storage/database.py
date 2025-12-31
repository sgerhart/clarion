"""
Clarion Database - SQLite-based persistent storage.

Stores sketches, clusters, policies, and customization sessions.
"""

from __future__ import annotations

import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
import threading

logger = logging.getLogger(__name__)

# Thread-local storage for database connections
_local = threading.local()


class ClarionDatabase:
    """
    SQLite database for Clarion backend storage.
    
    Tables:
    - sketches: Edge sketches from switches
    - clusters: Cluster assignments and metadata
    - policies: Generated SGACL policies
    - sessions: Customization sessions
    - identity: IP to identity mappings
    """
    
    def __init__(self, db_path: str = "clarion.db"):
        """
        Initialize database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._init_schema()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(_local, 'connection') or _local.connection is None:
            _local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
            )
            _local.connection.row_factory = sqlite3.Row
            # Enable foreign keys (SQLite requires explicit enable)
            _local.connection.execute("PRAGMA foreign_keys = ON")
        return _local.connection
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def _init_schema(self):
        """Initialize database schema."""
        conn = self._get_connection()
        
        # Collectors table (collector registry)
        self._init_collectors_schema(conn)
        
        # Topology tables (locations, address spaces, subnets, switches)
        self._init_topology_schema(conn)
        
        # MVP Schema: Categorization Engine Enhancements
        self._init_mvp_schema(conn)
        
        # Sketches table (from edge devices)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sketches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint_id TEXT NOT NULL,
                switch_id TEXT NOT NULL,
                unique_peers INTEGER,
                unique_ports INTEGER,
                bytes_in INTEGER,
                bytes_out INTEGER,
                flow_count INTEGER,
                first_seen INTEGER,
                last_seen INTEGER,
                active_hours INTEGER,
                local_cluster_id INTEGER DEFAULT -1,
                sketch_data BLOB,  -- Serialized sketch for full reconstruction
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(endpoint_id, switch_id)
            )
        """)
        
        # Create index for lookups
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sketches_endpoint 
            ON sketches(endpoint_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sketches_switch 
            ON sketches(switch_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sketches_last_seen 
            ON sketches(last_seen)
        """)
        
        # Clusters table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clusters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cluster_id INTEGER NOT NULL,
                cluster_label TEXT,
                sgt_value INTEGER,
                sgt_name TEXT,
                endpoint_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(cluster_id)
            )
        """)
        
        # Add explanation columns if they don't exist (migration)
        for col in ["explanation", "primary_reason", "confidence"]:
            try:
                if col == "confidence":
                    conn.execute(f"ALTER TABLE clusters ADD COLUMN {col} REAL")
                else:
                    conn.execute(f"ALTER TABLE clusters ADD COLUMN {col} TEXT")
            except sqlite3.OperationalError:
                # Column already exists
                pass
        
        # Create indexes for clusters
        conn.execute("CREATE INDEX IF NOT EXISTS idx_clusters_cluster_id ON clusters(cluster_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_clusters_sgt ON clusters(sgt_value)")
        
        # Cluster assignments (endpoint -> cluster)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cluster_assignments (
                endpoint_id TEXT NOT NULL,
                cluster_id INTEGER NOT NULL,
                confidence REAL,
                assigned_by TEXT,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (endpoint_id, cluster_id)
            )
        """)
        
        # Policies table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                policy_name TEXT NOT NULL,
                src_sgt INTEGER NOT NULL,
                dst_sgt INTEGER NOT NULL,
                action TEXT NOT NULL,  -- 'permit' or 'deny'
                rules_json TEXT,  -- JSON array of SGACL rules
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(policy_name, src_sgt, dst_sgt)
            )
        """)
        
        # Customization sessions
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'draft',  -- 'draft', 'review', 'approved', 'rejected'
                session_data TEXT  -- JSON blob
            )
        """)
        
        # Identity mappings (IP -> User/Device/AD Group)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS identity (
                ip_address TEXT PRIMARY KEY,
                mac_address TEXT,
                user_name TEXT,
                device_name TEXT,
                ad_groups TEXT,  -- JSON array
                ise_profile TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # NetFlow records (raw flow data)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS netflow (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                src_ip TEXT NOT NULL,
                dst_ip TEXT NOT NULL,
                src_port INTEGER,
                dst_port INTEGER,
                protocol INTEGER,
                bytes INTEGER,
                packets INTEGER,
                flow_start INTEGER,
                flow_end INTEGER,
                switch_id TEXT,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add SGT/MAC columns to netflow if they don't exist (migration for old databases)
        try:
            conn.execute("ALTER TABLE netflow ADD COLUMN src_sgt INTEGER")
            conn.execute("ALTER TABLE netflow ADD COLUMN dst_sgt INTEGER")
            conn.execute("ALTER TABLE netflow ADD COLUMN src_mac TEXT")
            conn.execute("ALTER TABLE netflow ADD COLUMN dst_mac TEXT")
            conn.execute("ALTER TABLE netflow ADD COLUMN vlan_id INTEGER")
        except sqlite3.OperationalError:
            # Columns may already exist (if table was created with newer schema)
            pass
        
        # Create indexes for netflow (basic indexes first)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_netflow_src 
            ON netflow(src_ip, flow_start)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_netflow_dst 
            ON netflow(dst_ip, flow_start)
        """)
        
        # Create indexes for SGT/MAC columns (only if columns exist)
        try:
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_netflow_sgt 
                ON netflow(src_sgt, dst_sgt, flow_start)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_netflow_mac 
                ON netflow(src_mac, dst_mac)
            """)
        except sqlite3.OperationalError:
            # Index creation may fail if columns don't exist (very old databases)
            pass
        
        conn.commit()
        logger.info(f"Database schema initialized: {self.db_path}")
        self._run_migrations(conn)
    
    def _run_migrations(self, conn: sqlite3.Connection):
        """Run database migrations."""
        # Check if user tables migration has been run
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='users'
        """)
        
        if not cursor.fetchone():
            # Run user tables migration
            try:
                from clarion.storage.migrations.add_user_tables import migrate as migrate_user_tables
                migrate_user_tables(conn)
                logger.info("User database tables migration completed")
            except ImportError as e:
                logger.warning(f"Could not import user tables migration: {e}")
            except Exception as e:
                logger.error(f"Error running user tables migration: {e}")
        
        # Check if user SGT assignment tables migration has been run
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='user_sgt_membership'
        """)
        
        if not cursor.fetchone():
            # Run user SGT assignment tables migration
            try:
                from clarion.storage.migrations.add_user_sgt_assignments import migrate as migrate_user_sgt
                migrate_user_sgt(conn)
                logger.info("User SGT assignment tables migration completed")
            except ImportError as e:
                logger.warning(f"Could not import user SGT assignment migration: {e}")
            except Exception as e:
                logger.error(f"Error running user SGT assignment migration: {e}")
        
        # Check if ISE configuration cache tables migration has been run
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='ise_sgts'
        """)
        
        if not cursor.fetchone():
            # Run ISE configuration cache tables migration
            try:
                from clarion.storage.migrations.add_ise_configuration_cache import migrate as migrate_ise_config
                migrate_ise_config(conn)
                logger.info("ISE configuration cache tables migration completed")
            except ImportError as e:
                logger.warning(f"Could not import ISE configuration cache migration: {e}")
            except Exception as e:
                logger.error(f"Error running ISE configuration cache migration: {e}")
        
        # Check if ISE session assignment tracking table migration has been run
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='ise_current_sgt_assignments'
        """)
        
        if not cursor.fetchone():
            # Run ISE session assignment tracking migration
            try:
                from clarion.storage.migrations.add_ise_session_assignments import migrate as migrate_ise_session
                migrate_ise_session(conn)
                logger.info("ISE session assignment tracking migration completed")
            except ImportError as e:
                logger.warning(f"Could not import ISE session assignment migration: {e}")
            except Exception as e:
                logger.error(f"Error running ISE session assignment migration: {e}")
        
        # Check if connector management tables migration has been run
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='connectors'
        """)
        
        if not cursor.fetchone():
            # Run connector management migration
            try:
                from clarion.storage.migrations.add_connectors_tables import migrate as migrate_connectors
                migrate_connectors(conn)
                logger.info("Connector management tables migration completed")
            except ImportError as e:
                logger.warning(f"Could not import connector management migration: {e}")
            except Exception as e:
                logger.error(f"Error running connector management migration: {e}")
        
        # Check if global certificates table migration has been run
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='certificates'
        """)
        
        if not cursor.fetchone():
            # Run global certificates migration
            try:
                from clarion.storage.migrations.add_certificates_table import migrate as migrate_certificates
                migrate_certificates(conn)
                logger.info("Global certificates table migration completed")
            except ImportError as e:
                logger.warning(f"Could not import certificates migration: {e}")
            except Exception as e:
                logger.error(f"Error running certificates migration: {e}")
    
    def _init_collectors_schema(self, conn: sqlite3.Connection):
        """Initialize collectors table."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS collectors (
                collector_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,  -- 'native' or 'agent'
                host TEXT NOT NULL,
                http_port INTEGER NOT NULL,
                backend_url TEXT,
                netflow_port INTEGER,
                ipfix_port INTEGER,
                batch_size INTEGER,
                batch_interval_seconds REAL,
                enabled INTEGER DEFAULT 1,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_collectors_type ON collectors(type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_collectors_enabled ON collectors(enabled)")
    
    def _init_topology_schema(self, conn: sqlite3.Connection):
        """Initialize topology-related tables."""
        # Locations table (hierarchy: campus/branch/remote -> building -> IDF)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                location_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,  -- CAMPUS, BRANCH, REMOTE_SITE, BUILDING, IDF, ROOM
                parent_id TEXT,
                address TEXT,
                latitude REAL,
                longitude REAL,
                site_type TEXT,  -- Additional classification (e.g., "BRANCH_OFFICE", "WAREHOUSE")
                contact_name TEXT,
                contact_phone TEXT,
                contact_email TEXT,
                timezone TEXT,  -- e.g., "America/Chicago"
                metadata TEXT,  -- JSON for custom fields
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES locations(location_id)
            )
        """)
        
        # Address spaces (customer-defined IP ranges)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS address_spaces (
                space_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                cidr TEXT NOT NULL,  -- e.g., "10.0.0.0/8"
                type TEXT NOT NULL,  -- GLOBAL, REGIONAL, LOCATION, VLAN
                location_id TEXT,
                description TEXT,
                is_internal BOOLEAN DEFAULT 1,
                metadata TEXT,  -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (location_id) REFERENCES locations(location_id)
            )
        """)
        
        # Subnets (with location mapping)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subnets (
                subnet_id TEXT PRIMARY KEY,
                cidr TEXT NOT NULL UNIQUE,  -- e.g., "10.1.2.0/24"
                name TEXT NOT NULL,
                location_id TEXT NOT NULL,
                address_space_id TEXT,  -- Reference to address space
                vlan_id INTEGER,
                switch_id TEXT,  -- Primary switch
                gateway_ip TEXT,
                dhcp_start TEXT,
                dhcp_end TEXT,
                purpose TEXT NOT NULL,  -- USER, SERVER, IOT, GUEST, etc.
                description TEXT,
                metadata TEXT,  -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (location_id) REFERENCES locations(location_id),
                FOREIGN KEY (address_space_id) REFERENCES address_spaces(space_id)
            )
        """)
        
        # Migration: Add address_space_id and description columns if they don't exist
        try:
            conn.execute("ALTER TABLE subnets ADD COLUMN address_space_id TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            conn.execute("ALTER TABLE subnets ADD COLUMN description TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Switches (with location)
        # Note: For existing databases, management_ip may still be NOT NULL
        # The API code handles this by providing a default empty string
        conn.execute("""
            CREATE TABLE IF NOT EXISTS switches (
                switch_id TEXT PRIMARY KEY,
                hostname TEXT NOT NULL UNIQUE,
                name TEXT,  -- Display name (can be same as hostname)
                model TEXT,
                location_id TEXT NOT NULL,
                management_ip TEXT,  -- Nullable for new databases
                serial_number TEXT,
                description TEXT,
                software_version TEXT,
                capabilities TEXT,  -- JSON array
                edge_agent_enabled BOOLEAN DEFAULT 0,
                metadata TEXT,  -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (location_id) REFERENCES locations(location_id)
            )
        """)
        
        # Migration: Add name and description columns if they don't exist
        try:
            conn.execute("ALTER TABLE switches ADD COLUMN name TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            conn.execute("ALTER TABLE switches ADD COLUMN description TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Migration: Make management_ip nullable if it's currently NOT NULL
        # SQLite doesn't support ALTER COLUMN, so we'll handle this in the API code
        
        # Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_locations_parent ON locations(parent_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_locations_type ON locations(type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_address_spaces_cidr ON address_spaces(cidr)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_address_spaces_location ON address_spaces(location_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_subnets_location ON subnets(location_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_subnets_vlan ON subnets(vlan_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_subnets_switch ON subnets(switch_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_switches_location ON switches(location_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_switches_hostname ON switches(hostname)")
        
        # Add new columns to existing locations table if they don't exist (migration)
        for column in ['site_type', 'contact_name', 'contact_phone', 'contact_email', 'timezone']:
            try:
                conn.execute(f"ALTER TABLE locations ADD COLUMN {column} TEXT")
            except sqlite3.OperationalError:
                # Column may already exist
                pass
        
        # Add location fields to existing netflow table (if not exists)
        try:
            conn.execute("ALTER TABLE netflow ADD COLUMN src_location_id TEXT")
            conn.execute("ALTER TABLE netflow ADD COLUMN dst_location_id TEXT")
            conn.execute("ALTER TABLE netflow ADD COLUMN src_subnet_id TEXT")
            conn.execute("ALTER TABLE netflow ADD COLUMN dst_subnet_id TEXT")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_netflow_src_location ON netflow(src_location_id, flow_start)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_netflow_dst_location ON netflow(dst_location_id, flow_start)")
        except sqlite3.OperationalError:
            # Columns may already exist
            pass
    
    # ========== Sketch Operations ==========
    
    def store_sketch(
        self,
        endpoint_id: str,
        switch_id: str,
        unique_peers: int,
        unique_ports: int,
        bytes_in: int,
        bytes_out: int,
        flow_count: int,
        first_seen: int,
        last_seen: int,
        active_hours: int,
        local_cluster_id: int = -1,
        sketch_data: Optional[bytes] = None,
    ) -> tuple[int, bool]:
        """
        Store or update a sketch.
        
        Returns:
            Tuple of (sketch_id, is_new_endpoint) where is_new_endpoint is True
            if this endpoint was never seen before on this switch.
        """
        with self.transaction() as conn:
            # Check if this endpoint already exists for this switch
            cursor = conn.execute("""
                SELECT id, first_seen FROM sketches 
                WHERE endpoint_id = ? AND switch_id = ?
            """, (endpoint_id, switch_id))
            existing = cursor.fetchone()
            
            is_new = existing is None
            
            # If endpoint exists, preserve original first_seen unless new first_seen is earlier
            if existing and first_seen < existing[1]:
                # Update with earlier first_seen
                cursor = conn.execute("""
                    UPDATE sketches SET
                        unique_peers = ?,
                        unique_ports = ?,
                        bytes_in = ?,
                        bytes_out = ?,
                        flow_count = ?,
                        first_seen = ?,
                        last_seen = ?,
                        active_hours = ?,
                        local_cluster_id = ?,
                        sketch_data = ?
                    WHERE endpoint_id = ? AND switch_id = ?
                """, (
                    unique_peers, unique_ports,
                    bytes_in, bytes_out, flow_count,
                    first_seen, last_seen,
                    active_hours, local_cluster_id, sketch_data,
                    endpoint_id, switch_id
                ))
                return existing[0], False
            else:
                # Insert new or replace
                cursor = conn.execute("""
                    INSERT OR REPLACE INTO sketches (
                        endpoint_id, switch_id, unique_peers, unique_ports,
                        bytes_in, bytes_out, flow_count, first_seen, last_seen,
                        active_hours, local_cluster_id, sketch_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    endpoint_id, switch_id, unique_peers, unique_ports,
                    bytes_in, bytes_out, flow_count, first_seen, last_seen,
                    active_hours, local_cluster_id, sketch_data
                ))
                return cursor.lastrowid, is_new
    
    def is_endpoint_first_seen(self, endpoint_id: str, switch_id: Optional[str] = None) -> bool:
        """
        Check if an endpoint is being seen for the first time.
        
        Args:
            endpoint_id: Endpoint identifier (MAC address)
            switch_id: Optional switch ID. If None, checks across all switches.
            
        Returns:
            True if endpoint has never been seen before, False otherwise.
        """
        conn = self._get_connection()
        if switch_id:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM sketches 
                WHERE endpoint_id = ? AND switch_id = ?
            """, (endpoint_id, switch_id))
        else:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM sketches 
                WHERE endpoint_id = ?
            """, (endpoint_id,))
        
        count = cursor.fetchone()[0]
        return count == 0
    
    def get_endpoint_first_seen(self, endpoint_id: str, switch_id: Optional[str] = None) -> Optional[int]:
        """
        Get the first_seen timestamp for an endpoint.
        
        Args:
            endpoint_id: Endpoint identifier
            switch_id: Optional switch ID. If None, gets earliest across all switches.
            
        Returns:
            Unix timestamp of first_seen, or None if endpoint not found.
        """
        conn = self._get_connection()
        if switch_id:
            cursor = conn.execute("""
                SELECT MIN(first_seen) FROM sketches 
                WHERE endpoint_id = ? AND switch_id = ?
            """, (endpoint_id, switch_id))
        else:
            cursor = conn.execute("""
                SELECT MIN(first_seen) FROM sketches 
                WHERE endpoint_id = ?
            """, (endpoint_id,))
        
        result = cursor.fetchone()[0]
        return result if result is not None else None
    
    def list_first_seen_endpoints(
        self,
        since: Optional[int] = None,
        limit: int = 1000,
        switch_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        List endpoints that were first seen within a time range.
        
        This is a simplified version that uses the sketches table.
        For more accurate tracking, we'd want a separate endpoints table.
        
        Args:
            since: Unix timestamp. Only return endpoints first seen after this time.
            limit: Maximum number of results.
            switch_id: Optional switch ID filter.
            
        Returns:
            List of dicts with endpoint_id, switch_id, first_seen, last_seen.
        """
        conn = self._get_connection()
        query = """
            SELECT endpoint_id, switch_id, MIN(first_seen) as first_seen, MAX(last_seen) as last_seen
            FROM sketches
            WHERE 1=1
        """
        params = []
        
        if switch_id:
            query += " AND switch_id = ?"
            params.append(switch_id)
        
        if since:
            query += " AND first_seen >= ?"
            params.append(since)
        
        query += " GROUP BY endpoint_id, switch_id ORDER BY first_seen DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_sketch(self, endpoint_id: str, switch_id: Optional[str] = None) -> Optional[Dict]:
        """Get a sketch by endpoint ID."""
        conn = self._get_connection()
        if switch_id:
            cursor = conn.execute("""
                SELECT * FROM sketches 
                WHERE endpoint_id = ? AND switch_id = ?
            """, (endpoint_id, switch_id))
        else:
            cursor = conn.execute("""
                SELECT * FROM sketches 
                WHERE endpoint_id = ? 
                ORDER BY last_seen DESC
                LIMIT 1
            """, (endpoint_id,))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def list_sketches(
        self,
        switch_id: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[Dict]:
        """List sketches."""
        conn = self._get_connection()
        if switch_id:
            cursor = conn.execute("""
                SELECT * FROM sketches 
                WHERE switch_id = ?
                ORDER BY last_seen DESC
                LIMIT ? OFFSET ?
            """, (switch_id, limit, offset))
        else:
            cursor = conn.execute("""
                SELECT * FROM sketches 
                ORDER BY last_seen DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_sketch_stats(self) -> Dict[str, Any]:
        """Get statistics about stored sketches."""
        conn = self._get_connection()
        
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total_sketches,
                COUNT(DISTINCT switch_id) as total_switches,
                COUNT(DISTINCT endpoint_id) as unique_endpoints,
                SUM(flow_count) as total_flows,
                MIN(first_seen) as earliest_flow,
                MAX(last_seen) as latest_flow
            FROM sketches
        """)
        row = cursor.fetchone()
        
        return dict(row) if row else {}
    
    # ========== NetFlow Operations ==========
    
    def store_netflow(
        self,
        src_ip: str,
        dst_ip: str,
        src_port: int,
        dst_port: int,
        protocol: int,
        bytes: int,
        packets: int,
        flow_start: int,
        flow_end: int,
        switch_id: Optional[str] = None,
        src_sgt: Optional[int] = None,
        dst_sgt: Optional[int] = None,
        src_mac: Optional[str] = None,
        dst_mac: Optional[str] = None,
        vlan_id: Optional[int] = None,
    ) -> int:
        """Store a NetFlow record."""
        with self.transaction() as conn:
            cursor = conn.execute("""
                INSERT INTO netflow (
                    src_ip, dst_ip, src_port, dst_port, protocol,
                    bytes, packets, flow_start, flow_end, switch_id,
                    src_sgt, dst_sgt, src_mac, dst_mac, vlan_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                src_ip, dst_ip, src_port, dst_port, protocol,
                bytes, packets, flow_start, flow_end, switch_id,
                src_sgt, dst_sgt, src_mac, dst_mac, vlan_id
            ))
            return cursor.lastrowid
    
    def get_recent_netflow(
        self,
        limit: int = 1000,
        since: Optional[int] = None,
    ) -> List[Dict]:
        """Get recent NetFlow records."""
        conn = self._get_connection()
        if since:
            cursor = conn.execute("""
                SELECT * FROM netflow 
                WHERE flow_start >= ?
                ORDER BY flow_start DESC
                LIMIT ?
            """, (since, limit))
        else:
            cursor = conn.execute("""
                SELECT * FROM netflow 
                ORDER BY flow_start DESC
                LIMIT ?
            """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_device_to_device_flows(
        self,
        src_device: Optional[str] = None,
        dst_device: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict]:
        """Get flows between specific devices (by IP or MAC)."""
        conn = self._get_connection()
        
        query = "SELECT * FROM netflow WHERE 1=1"
        params = []
        
        if src_device:
            query += " AND (src_ip = ? OR src_ip LIKE ?)"
            params.extend([src_device, f"{src_device}%"])
        
        if dst_device:
            query += " AND (dst_ip = ? OR dst_ip LIKE ?)"
            params.extend([dst_device, f"{dst_device}%"])
        
        query += " ORDER BY flow_start DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== Cluster Operations ==========
    
    def store_cluster(
        self,
        cluster_id: int,
        cluster_label: Optional[str] = None,
        sgt_value: Optional[int] = None,
        sgt_name: Optional[str] = None,
        endpoint_count: int = 0,
        explanation: Optional[str] = None,
        primary_reason: Optional[str] = None,
        confidence: Optional[float] = None,
    ):
        """Store cluster metadata including explanation."""
        with self.transaction() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO clusters (
                    cluster_id, cluster_label, sgt_value, sgt_name, endpoint_count,
                    explanation, primary_reason, confidence,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (cluster_id, cluster_label, sgt_value, sgt_name, endpoint_count,
                  explanation, primary_reason, confidence))
    
    def assign_endpoint_to_cluster(
        self, 
        endpoint_id: str, 
        cluster_id: int,
        confidence: Optional[float] = None,
        assigned_by: Optional[str] = None,
    ):
        """Assign an endpoint to a cluster."""
        with self.transaction() as conn:
            # Check if columns exist (they were added in MVP schema migration)
            conn.execute("""
                INSERT OR REPLACE INTO cluster_assignments 
                (endpoint_id, cluster_id, confidence, assigned_by, assigned_at) 
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (endpoint_id, cluster_id, confidence, assigned_by))
    
    def get_clusters(self) -> List[Dict]:
        """Get all clusters."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT * FROM clusters ORDER BY cluster_id
        """)
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== Policy Operations ==========
    
    def store_policy(
        self,
        policy_name: str,
        src_sgt: int,
        dst_sgt: int,
        action: str,
        rules_json: str,
    ):
        """Store a policy."""
        with self.transaction() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO policies (
                    policy_name, src_sgt, dst_sgt, action, rules_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (policy_name, src_sgt, dst_sgt, action, rules_json))
    
    def get_policies(self) -> List[Dict]:
        """Get all policies."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT * FROM policies ORDER BY policy_name, src_sgt, dst_sgt
        """)
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== Session Operations ==========
    
    def store_session(self, session_id: str, session_data: Dict, created_by: Optional[str] = None):
        """Store a customization session."""
        with self.transaction() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sessions (
                    session_id, session_data, created_by, updated_at
                ) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (session_id, json.dumps(session_data), created_by))
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get a session."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT * FROM sessions WHERE session_id = ?
        """, (session_id,))
        row = cursor.fetchone()
        if row:
            data = dict(row)
            data['session_data'] = json.loads(data['session_data'])
            return data
        return None
    
    # ========== Identity Operations ==========
    
    def store_identity(
        self,
        ip_address: str,
        mac_address: Optional[str] = None,
        user_name: Optional[str] = None,
        device_name: Optional[str] = None,
        ad_groups: Optional[List[str]] = None,
        ise_profile: Optional[str] = None,
    ):
        """Store identity mapping."""
        with self.transaction() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO identity (
                    ip_address, mac_address, user_name, device_name,
                    ad_groups, ise_profile, last_seen
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                ip_address, mac_address, user_name, device_name,
                json.dumps(ad_groups) if ad_groups else None,
                ise_profile
            ))
    
    def get_identity(self, ip_address: str) -> Optional[Dict]:
        """Get identity for an IP address."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT * FROM identity WHERE ip_address = ?
        """, (ip_address,))
        row = cursor.fetchone()
        if row:
            data = dict(row)
            if data.get('ad_groups'):
                data['ad_groups'] = json.loads(data['ad_groups'])
            return data
        return None
    
    def cleanup_old_data(self, days: int = 30):
        """Clean up data older than specified days."""
        cutoff = int((datetime.now().timestamp() - (days * 86400)))
        
        with self.transaction() as conn:
            # Clean old sketches
            conn.execute("""
                DELETE FROM sketches WHERE last_seen < ?
            """, (cutoff,))
            
            # Clean old netflow
            conn.execute("""
                DELETE FROM netflow WHERE flow_start < ?
            """, (cutoff,))
            
            logger.info(f"Cleaned up data older than {days} days")
    
    # ========== MVP: SGT Registry Operations ==========
    
    def create_sgt(self, sgt_value: int, sgt_name: str, category: Optional[str] = None, 
                   description: Optional[str] = None) -> None:
        """Create a new SGT in the registry."""
        with self.transaction() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sgt_registry 
                (sgt_value, sgt_name, category, description, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (sgt_value, sgt_name, category, description))
    
    def get_sgt(self, sgt_value: int) -> Optional[Dict]:
        """Get an SGT from the registry."""
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM sgt_registry WHERE sgt_value = ?", (sgt_value,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def list_sgts(self, active_only: bool = True) -> List[Dict]:
        """List all SGTs in the registry."""
        conn = self._get_connection()
        if active_only:
            cursor = conn.execute("""
                SELECT * FROM sgt_registry WHERE is_active = 1 
                ORDER BY sgt_value
            """)
        else:
            cursor = conn.execute("SELECT * FROM sgt_registry ORDER BY sgt_value")
        return [dict(row) for row in cursor.fetchall()]
    
    def update_sgt(self, sgt_value: int, sgt_name: Optional[str] = None,
                   category: Optional[str] = None, description: Optional[str] = None,
                   is_active: Optional[bool] = None) -> None:
        """Update an SGT in the registry."""
        updates = []
        params = []
        if sgt_name is not None:
            updates.append("sgt_name = ?")
            params.append(sgt_name)
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if is_active else 0)
        
        if not updates:
            return
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(sgt_value)
        
        with self.transaction() as conn:
            conn.execute(f"""
                UPDATE sgt_registry SET {', '.join(updates)}
                WHERE sgt_value = ?
            """, params)
    
    # ========== MVP: SGT Membership Operations ==========
    
    def assign_sgt_to_endpoint(self, endpoint_id: str, sgt_value: int, 
                               assigned_by: str = "clustering", confidence: Optional[float] = None,
                               cluster_id: Optional[int] = None) -> None:
        """Assign an SGT to an endpoint."""
        # First, record previous assignment in history if exists
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT sgt_value FROM sgt_membership WHERE endpoint_id = ?
        """, (endpoint_id,))
        old_row = cursor.fetchone()
        
        with self.transaction() as conn:
            if old_row:
                # Mark old assignment as unassigned
                conn.execute("""
                    UPDATE sgt_assignment_history 
                    SET unassigned_at = CURRENT_TIMESTAMP
                    WHERE endpoint_id = ? AND sgt_value = ? AND unassigned_at IS NULL
                """, (endpoint_id, old_row[0]))
            
            # Insert/update membership
            conn.execute("""
                INSERT OR REPLACE INTO sgt_membership
                (endpoint_id, sgt_value, assigned_at, assigned_by, confidence, cluster_id)
                VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
            """, (endpoint_id, sgt_value, assigned_by, confidence, cluster_id))
            
            # Insert into history
            conn.execute("""
                INSERT INTO sgt_assignment_history
                (endpoint_id, sgt_value, assigned_at, assigned_by)
                VALUES (?, ?, CURRENT_TIMESTAMP, ?)
            """, (endpoint_id, sgt_value, assigned_by))
    
    def get_endpoint_sgt(self, endpoint_id: str) -> Optional[Dict]:
        """Get the current SGT assignment for an endpoint."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT * FROM sgt_membership WHERE endpoint_id = ?
        """, (endpoint_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def list_endpoints_by_sgt(self, sgt_value: int) -> List[Dict]:
        """List all endpoints assigned to a specific SGT."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT * FROM sgt_membership WHERE sgt_value = ?
            ORDER BY assigned_at DESC
        """, (sgt_value,))
        return [dict(row) for row in cursor.fetchall()]
    
    def unassign_sgt_from_endpoint(self, endpoint_id: str) -> None:
        """Unassign SGT from an endpoint."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT sgt_value FROM sgt_membership WHERE endpoint_id = ?
        """, (endpoint_id,))
        row = cursor.fetchone()
        
        if row:
            with self.transaction() as conn:
                # Update history
                conn.execute("""
                    UPDATE sgt_assignment_history 
                    SET unassigned_at = CURRENT_TIMESTAMP
                    WHERE endpoint_id = ? AND sgt_value = ? AND unassigned_at IS NULL
                """, (endpoint_id, row[0]))
                
                # Delete membership
                conn.execute("""
                    DELETE FROM sgt_membership WHERE endpoint_id = ?
                """, (endpoint_id,))
    
    def get_sgt_assignment_history(self, endpoint_id: str) -> List[Dict]:
        """Get assignment history for an endpoint."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT * FROM sgt_assignment_history 
            WHERE endpoint_id = ?
            ORDER BY assigned_at DESC
        """, (endpoint_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== MVP: Cluster Centroids Operations ==========
    
    def store_cluster_centroid(self, cluster_id: int, feature_vector: List[float],
                               sgt_value: Optional[int] = None, member_count: int = 0) -> None:
        """Store or update a cluster centroid."""
        with self.transaction() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cluster_centroids
                (cluster_id, sgt_value, feature_vector, member_count, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (cluster_id, sgt_value, json.dumps(feature_vector), member_count))
    
    def get_cluster_centroid(self, cluster_id: int) -> Optional[Dict]:
        """Get a cluster centroid."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT * FROM cluster_centroids WHERE cluster_id = ?
        """, (cluster_id,))
        row = cursor.fetchone()
        if row:
            data = dict(row)
            if data.get('feature_vector'):
                data['feature_vector'] = json.loads(data['feature_vector'])
            return data
        return None
    
    def list_all_centroids(self) -> List[Dict]:
        """List all cluster centroids."""
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM cluster_centroids ORDER BY cluster_id")
        results = []
        for row in cursor.fetchall():
            data = dict(row)
            if data.get('feature_vector'):
                data['feature_vector'] = json.loads(data['feature_vector'])
            results.append(data)
        return results
    
    def update_centroid_member_count(self, cluster_id: int, member_count: int) -> None:
        """Update the member count for a centroid."""
        with self.transaction() as conn:
            conn.execute("""
                UPDATE cluster_centroids 
                SET member_count = ?, updated_at = CURRENT_TIMESTAMP
                WHERE cluster_id = ?
            """, (member_count, cluster_id))
    
    def _init_mvp_schema(self, conn: sqlite3.Connection):
        """Initialize MVP categorization engine schema enhancements."""
        # SGT Registry (stable SGTs)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sgt_registry (
                sgt_value INTEGER PRIMARY KEY,
                sgt_name TEXT NOT NULL,
                category TEXT,  -- 'users', 'servers', 'devices', 'special'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                is_active INTEGER DEFAULT 1  -- SQLite uses INTEGER for BOOLEAN
            )
        """)
        
        # SGT Membership (dynamic assignments)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sgt_membership (
                endpoint_id TEXT NOT NULL PRIMARY KEY,
                sgt_value INTEGER NOT NULL,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assigned_by TEXT,  -- 'clustering', 'manual', 'ise', 'incremental'
                confidence REAL,
                cluster_id INTEGER,  -- Which cluster this came from
                FOREIGN KEY (sgt_value) REFERENCES sgt_registry(sgt_value)
            )
        """)
        
        # SGT Assignment History (audit trail)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sgt_assignment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint_id TEXT NOT NULL,
                sgt_value INTEGER NOT NULL,
                assigned_at TIMESTAMP NOT NULL,
                unassigned_at TIMESTAMP,
                assigned_by TEXT,
                FOREIGN KEY (sgt_value) REFERENCES sgt_registry(sgt_value)
            )
        """)
        
        # Cluster Centroids (for fast incremental assignment)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cluster_centroids (
                cluster_id INTEGER NOT NULL PRIMARY KEY,
                sgt_value INTEGER,
                feature_vector TEXT,  -- JSON array of centroid features
                member_count INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sgt_value) REFERENCES sgt_registry(sgt_value)
            )
        """)
        
        # Policy Recommendations
        conn.execute("""
            CREATE TABLE IF NOT EXISTS policy_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cluster_id INTEGER NOT NULL,
                recommended_sgt INTEGER NOT NULL,
                recommended_sgt_name TEXT,
                endpoint_id TEXT,  -- For device-specific recommendations
                old_cluster_id INTEGER,
                old_sgt INTEGER,
                policy_rule_name TEXT NOT NULL,
                policy_rule_conditions TEXT NOT NULL,  -- JSON array of conditions
                policy_rule_action TEXT NOT NULL,
                policy_rule_justification TEXT,
                devices_affected INTEGER DEFAULT 0,
                ad_groups_affected TEXT,  -- JSON array
                device_profiles_affected TEXT,  -- JSON array
                device_types_affected TEXT,  -- JSON array
                status TEXT DEFAULT 'pending',  -- 'pending', 'accepted', 'rejected', 'deployed'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recommended_sgt) REFERENCES sgt_registry(sgt_value)
            )
        """)
        
        # Migrations: Add first_seen/last_seen to sketches if not exists (already have them, but ensure TIMESTAMP)
        # Note: sketches already has first_seen/last_seen as INTEGER (Unix timestamp) - this is fine
        
        # Migrations: Add confidence and assigned_by to cluster_assignments if needed
        # (For existing databases that don't have these columns)
        try:
            conn.execute("ALTER TABLE cluster_assignments ADD COLUMN confidence REAL")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            conn.execute("ALTER TABLE cluster_assignments ADD COLUMN assigned_by TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Note: assigned_at is now in the CREATE TABLE statement, but this migration
        # ensures existing databases get it
        try:
            conn.execute("ALTER TABLE cluster_assignments ADD COLUMN assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sgt_membership_sgt ON sgt_membership(sgt_value)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sgt_membership_cluster ON sgt_membership(cluster_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sgt_history_endpoint ON sgt_assignment_history(endpoint_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sgt_history_sgt ON sgt_assignment_history(sgt_value)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sgt_history_assigned_at ON sgt_assignment_history(assigned_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cluster_centroids_sgt ON cluster_centroids(sgt_value)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_policy_recommendations_cluster ON policy_recommendations(cluster_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_policy_recommendations_status ON policy_recommendations(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_policy_recommendations_endpoint ON policy_recommendations(endpoint_id)")
        
        logger.info("MVP categorization engine schema initialized")
    
    # ========== Policy Recommendation Operations ==========
    
    def store_policy_recommendation(
        self,
        cluster_id: int,
        recommended_sgt: int,
        recommended_sgt_name: Optional[str],
        policy_rule_name: str,
        policy_rule_conditions: List[Dict],
        policy_rule_action: str,
        policy_rule_justification: Optional[str],
        devices_affected: int = 0,
        ad_groups_affected: Optional[List[str]] = None,
        device_profiles_affected: Optional[List[str]] = None,
        device_types_affected: Optional[List[str]] = None,
        endpoint_id: Optional[str] = None,
        old_cluster_id: Optional[int] = None,
        old_sgt: Optional[int] = None,
        status: str = "pending",
    ) -> int:
        """
        Store a policy recommendation.
        
        Returns:
            Recommendation ID
        """
        with self.transaction() as conn:
            cursor = conn.execute("""
                INSERT INTO policy_recommendations (
                    cluster_id, recommended_sgt, recommended_sgt_name,
                    endpoint_id, old_cluster_id, old_sgt,
                    policy_rule_name, policy_rule_conditions, policy_rule_action,
                    policy_rule_justification,
                    devices_affected, ad_groups_affected, device_profiles_affected,
                    device_types_affected, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cluster_id, recommended_sgt, recommended_sgt_name,
                endpoint_id, old_cluster_id, old_sgt,
                policy_rule_name, json.dumps(policy_rule_conditions), policy_rule_action,
                policy_rule_justification,
                devices_affected,
                json.dumps(ad_groups_affected) if ad_groups_affected else None,
                json.dumps(device_profiles_affected) if device_profiles_affected else None,
                json.dumps(device_types_affected) if device_types_affected else None,
                status,
            ))
            return cursor.lastrowid
    
    def get_policy_recommendation(self, recommendation_id: int) -> Optional[Dict]:
        """Get a policy recommendation by ID."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT * FROM policy_recommendations WHERE id = ?
        """, (recommendation_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        data = dict(row)
        # Parse JSON fields
        if data.get('policy_rule_conditions'):
            data['policy_rule_conditions'] = json.loads(data['policy_rule_conditions'])
        if data.get('ad_groups_affected'):
            data['ad_groups_affected'] = json.loads(data['ad_groups_affected'])
        if data.get('device_profiles_affected'):
            data['device_profiles_affected'] = json.loads(data['device_profiles_affected'])
        if data.get('device_types_affected'):
            data['device_types_affected'] = json.loads(data['device_types_affected'])
        return data
    
    def list_policy_recommendations(
        self,
        status: Optional[str] = None,
        cluster_id: Optional[int] = None,
        endpoint_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict]:
        """List policy recommendations with optional filters."""
        conn = self._get_connection()
        
        query = "SELECT * FROM policy_recommendations WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        if cluster_id is not None:
            query += " AND cluster_id = ?"
            params.append(cluster_id)
        if endpoint_id:
            query += " AND endpoint_id = ?"
            params.append(endpoint_id)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            data = dict(row)
            # Parse JSON fields
            if data.get('policy_rule_conditions'):
                data['policy_rule_conditions'] = json.loads(data['policy_rule_conditions'])
            if data.get('ad_groups_affected'):
                data['ad_groups_affected'] = json.loads(data['ad_groups_affected'])
            if data.get('device_profiles_affected'):
                data['device_profiles_affected'] = json.loads(data['device_profiles_affected'])
            if data.get('device_types_affected'):
                data['device_types_affected'] = json.loads(data['device_types_affected'])
            results.append(data)
        
        return results
    
    def update_policy_recommendation_status(
        self,
        recommendation_id: int,
        status: str,
    ) -> None:
        """Update the status of a policy recommendation."""
        with self.transaction() as conn:
            conn.execute("""
                UPDATE policy_recommendations
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, recommendation_id))
    
    def delete_policy_recommendation(self, recommendation_id: int) -> None:
        """Delete a policy recommendation."""
        with self.transaction() as conn:
            conn.execute("""
                DELETE FROM policy_recommendations WHERE id = ?
            """, (recommendation_id,))
    
    # User database methods
    
    def create_user(
        self,
        user_id: str,
        username: str,
        email: Optional[str] = None,
        display_name: Optional[str] = None,
        department: Optional[str] = None,
        title: Optional[str] = None,
        source: str = "manual"
    ) -> None:
        """Create or update a user record."""
        conn = self._get_connection()
        # Check if user exists
        cursor = conn.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone()
        
        if exists:
            # Update existing user
            conn.execute("""
                UPDATE users 
                SET username = ?, email = ?, display_name = ?, department = ?, 
                    title = ?, source = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (username, email, display_name, department, title, source, user_id))
        else:
            # Create new user
            conn.execute("""
                INSERT INTO users 
                (user_id, username, email, display_name, department, title, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, username, email, display_name, department, title, source))
        conn.commit()
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get a user by user_id."""
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def list_users(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """List all users."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT * FROM users 
            ORDER BY username 
            LIMIT ? OFFSET ?
        """, (limit, offset))
        return [dict(row) for row in cursor.fetchall()]
    
    def create_user_device_association(
        self,
        user_id: str,
        endpoint_id: str,
        ip_address: Optional[str] = None,
        association_type: str = "manual",
        session_id: Optional[str] = None
    ) -> None:
        """Create or update a user-device association."""
        conn = self._get_connection()
        # Note: SQLite doesn't support ON CONFLICT with multiple columns the same way,
        # so we'll use INSERT OR REPLACE or check first
        cursor = conn.execute("""
            SELECT association_id FROM user_device_associations
            WHERE user_id = ? AND endpoint_id = ? AND association_type = ?
        """, (user_id, endpoint_id, association_type))
        
        existing = cursor.fetchone()
        if existing:
            conn.execute("""
                UPDATE user_device_associations
                SET ip_address = ?, session_id = ?, last_associated = CURRENT_TIMESTAMP, is_active = 1
                WHERE user_id = ? AND endpoint_id = ? AND association_type = ?
            """, (ip_address, session_id, user_id, endpoint_id, association_type))
        else:
            conn.execute("""
                INSERT INTO user_device_associations
                (user_id, endpoint_id, ip_address, association_type, session_id, last_associated, is_active)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 1)
            """, (user_id, endpoint_id, ip_address, association_type, session_id))
        conn.commit()
    
    def get_users_for_device(self, endpoint_id: str) -> List[Dict]:
        """Get all users associated with a device."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT u.*, uda.association_type, uda.last_associated, uda.is_active, uda.session_id
            FROM users u
            JOIN user_device_associations uda ON u.user_id = uda.user_id
            WHERE uda.endpoint_id = ? AND uda.is_active = 1
            ORDER BY uda.last_associated DESC
        """, (endpoint_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_devices_for_user(self, user_id: str) -> List[Dict]:
        """Get all devices associated with a user."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT 
                uda.association_id,
                uda.user_id,
                uda.endpoint_id,
                uda.ip_address as uda_ip_address,
                uda.association_type,
                uda.session_id,
                uda.first_associated,
                uda.last_associated,
                uda.is_active,
                s.endpoint_id as sketch_endpoint_id,
                s.switch_id, 
                s.flow_count, 
                s.unique_peers,
                i.device_name,
                i.ip_address as identity_ip_address,
                i.user_name,
                i.ise_profile
            FROM user_device_associations uda
            LEFT JOIN sketches s ON uda.endpoint_id = s.endpoint_id
            LEFT JOIN identity i ON (uda.endpoint_id = i.mac_address) OR (uda.ip_address = i.ip_address AND uda.ip_address IS NOT NULL)
            WHERE uda.user_id = ? AND uda.is_active = 1
            ORDER BY uda.last_associated DESC
        """, (user_id,))
        rows = cursor.fetchall()
        # Convert to dict and handle potential duplicate column names
        results = []
        for row in rows:
            device_dict = dict(row)
            # Use identity_ip_address if available, otherwise use uda_ip_address
            if device_dict.get('identity_ip_address'):
                device_dict['ip_address'] = device_dict['identity_ip_address']
            elif device_dict.get('uda_ip_address'):
                device_dict['ip_address'] = device_dict['uda_ip_address']
            # Clean up duplicate keys
            if 'uda_ip_address' in device_dict:
                del device_dict['uda_ip_address']
            if 'identity_ip_address' in device_dict:
                del device_dict['identity_ip_address']
            if 'sketch_endpoint_id' in device_dict:
                del device_dict['sketch_endpoint_id']
            # Set device_type to None since identity table doesn't have this column yet
            device_dict['device_type'] = None
            results.append(device_dict)
        return results
    
    def create_ad_group_membership(
        self,
        user_id: str,
        group_id: str,
        group_name: Optional[str] = None
    ) -> None:
        """Create or update an AD group membership."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT membership_id FROM ad_group_memberships
            WHERE user_id = ? AND group_id = ?
        """, (user_id, group_id))
        
        existing = cursor.fetchone()
        if existing:
            conn.execute("""
                UPDATE ad_group_memberships
                SET group_name = ?, last_verified = CURRENT_TIMESTAMP
                WHERE user_id = ? AND group_id = ?
            """, (group_name, user_id, group_id))
        else:
            conn.execute("""
                INSERT INTO ad_group_memberships (user_id, group_id, group_name, last_verified)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, group_id, group_name))
        conn.commit()
    
    def get_user_groups(self, user_id: str) -> List[Dict]:
        """Get AD groups for a user."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT group_id, group_name, last_verified
            FROM ad_group_memberships
            WHERE user_id = ?
            ORDER BY group_name
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def update_user_last_seen(self, user_id: str) -> None:
        """Update user's last_seen timestamp."""
        conn = self._get_connection()
        conn.execute("""
            UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE user_id = ?
        """, (user_id,))
        conn.commit()
    
    # ========== User SGT Assignment Operations ==========
    
    def assign_sgt_to_user(
        self,
        user_id: str,
        sgt_value: int,
        assigned_by: str = "traffic_analysis",
        confidence: Optional[float] = None,
        user_cluster_id: Optional[int] = None,
    ) -> None:
        """Assign an SGT to a user."""
        # First, record previous assignment in history if exists
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT sgt_value FROM user_sgt_membership WHERE user_id = ?
        """, (user_id,))
        old_row = cursor.fetchone()
        
        with self.transaction() as conn:
            if old_row:
                # Mark old assignment as unassigned
                conn.execute("""
                    UPDATE user_sgt_assignment_history 
                    SET unassigned_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND sgt_value = ? AND unassigned_at IS NULL
                """, (user_id, old_row[0]))
            
            # Insert/update membership
            conn.execute("""
                INSERT OR REPLACE INTO user_sgt_membership
                (user_id, sgt_value, assigned_at, assigned_by, confidence, user_cluster_id)
                VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
            """, (user_id, sgt_value, assigned_by, confidence, user_cluster_id))
            
            # Insert into history
            conn.execute("""
                INSERT INTO user_sgt_assignment_history
                (user_id, sgt_value, assigned_at, assigned_by)
                VALUES (?, ?, CURRENT_TIMESTAMP, ?)
            """, (user_id, sgt_value, assigned_by))
    
    def get_user_sgt(self, user_id: str) -> Optional[Dict]:
        """Get the current SGT assignment for a user."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT usm.*, sr.sgt_name, sr.category
            FROM user_sgt_membership usm
            LEFT JOIN sgt_registry sr ON usm.sgt_value = sr.sgt_value
            WHERE usm.user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def list_users_by_sgt(self, sgt_value: int) -> List[Dict]:
        """List all users assigned to a specific SGT."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT usm.*, sr.sgt_name, u.username, u.email, u.display_name
            FROM user_sgt_membership usm
            LEFT JOIN sgt_registry sr ON usm.sgt_value = sr.sgt_value
            LEFT JOIN users u ON usm.user_id = u.user_id
            WHERE usm.sgt_value = ?
            ORDER BY usm.assigned_at DESC
        """, (sgt_value,))
        return [dict(row) for row in cursor.fetchall()]
    
    def unassign_sgt_from_user(self, user_id: str) -> None:
        """Unassign SGT from a user."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT sgt_value FROM user_sgt_membership WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        
        if row:
            with self.transaction() as conn:
                # Update history
                conn.execute("""
                    UPDATE user_sgt_assignment_history 
                    SET unassigned_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND sgt_value = ? AND unassigned_at IS NULL
                """, (user_id, row[0]))
                
                # Delete membership
                conn.execute("""
                    DELETE FROM user_sgt_membership WHERE user_id = ?
                """, (user_id,))
    
    def get_user_sgt_assignment_history(self, user_id: str) -> List[Dict]:
        """Get assignment history for a user."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT usah.*, sr.sgt_name
            FROM user_sgt_assignment_history usah
            LEFT JOIN sgt_registry sr ON usah.sgt_value = sr.sgt_value
            WHERE usah.user_id = ?
            ORDER BY usah.assigned_at DESC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== ISE Configuration Cache Operations ==========
    
    def store_ise_sgts(self, ise_server: str, sgts: List[Dict[str, Any]]) -> int:
        """
        Store ISE SGTs in cache.
        
        Args:
            ise_server: ISE server identifier (e.g., "https://192.168.10.31")
            sgts: List of SGT dictionaries from ISE API
            
        Returns:
            Number of SGTs stored
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Delete existing SGTs for this ISE server
        cursor.execute("DELETE FROM ise_sgts WHERE ise_server = ?", (ise_server,))
        
        # Insert new SGTs
        count = 0
        for sgt in sgts:
            cursor.execute("""
                INSERT OR REPLACE INTO ise_sgts (id, name, value, description, generation_id, ise_server, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                sgt.get('id'),
                sgt.get('name'),
                int(sgt.get('value', 0)),
                sgt.get('description'),
                sgt.get('generationId'),
                ise_server,
            ))
            count += 1
        
        conn.commit()
        logger.info(f"Stored {count} SGTs from ISE server {ise_server}")
        return count
    
    def get_ise_sgts(self, ise_server: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get cached ISE SGTs.
        
        Args:
            ise_server: Optional ISE server identifier to filter by
            
        Returns:
            List of SGT dictionaries
        """
        conn = self._get_connection()
        
        if ise_server:
            cursor = conn.execute("""
                SELECT * FROM ise_sgts WHERE ise_server = ? ORDER BY value
            """, (ise_server,))
        else:
            cursor = conn.execute("SELECT * FROM ise_sgts ORDER BY ise_server, value")
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_ise_sgt_by_value(self, sgt_value: int, ise_server: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get an ISE SGT by value."""
        conn = self._get_connection()
        
        if ise_server:
            cursor = conn.execute("""
                SELECT * FROM ise_sgts WHERE value = ? AND ise_server = ?
            """, (sgt_value, ise_server))
        else:
            cursor = conn.execute("SELECT * FROM ise_sgts WHERE value = ? LIMIT 1", (sgt_value,))
        
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def store_ise_auth_profiles(self, ise_server: str, profiles: List[Dict[str, Any]]) -> int:
        """
        Store ISE authorization profiles in cache.
        
        Args:
            ise_server: ISE server identifier
            profiles: List of authorization profile dictionaries from ISE API
            
        Returns:
            Number of profiles stored
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Delete existing profiles for this ISE server
        cursor.execute("DELETE FROM ise_auth_profiles WHERE ise_server = ?", (ise_server,))
        
        count = 0
        for profile in profiles:
            # Extract SGT value if present
            sgt_value = None
            if 'sgt' in profile and profile['sgt']:
                try:
                    sgt_value = int(profile['sgt'])
                except (ValueError, TypeError):
                    pass
            
            # Also check advancedAttributes for cisco-av-pair
            if sgt_value is None and 'advancedAttributes' in profile:
                for attr in profile.get('advancedAttributes', []):
                    right_hand = attr.get('rightHandSideAttribueValue', {})
                    value = right_hand.get('value', '') if isinstance(right_hand, dict) else str(right_hand)
                    if isinstance(value, str) and 'security-group-tag=' in value:
                        try:
                            sgt_str = value.split('security-group-tag=')[1].split()[0]
                            sgt_value = int(sgt_str)
                            break
                        except (ValueError, IndexError):
                            pass
            
            cursor.execute("""
                INSERT OR REPLACE INTO ise_auth_profiles 
                (id, name, description, sgt_value, access_type, authz_profile_type, ise_server, synced_at, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            """, (
                profile.get('id'),
                profile.get('name'),
                profile.get('description'),
                sgt_value,
                profile.get('accessType'),
                profile.get('authzProfileType'),
                ise_server,
                json.dumps(profile),  # Store full profile as JSON for reference
            ))
            count += 1
        
        conn.commit()
        logger.info(f"Stored {count} authorization profiles from ISE server {ise_server}")
        return count
    
    def get_ise_auth_profiles(self, ise_server: Optional[str] = None, sgt_value: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get cached ISE authorization profiles.
        
        Args:
            ise_server: Optional ISE server identifier to filter by
            sgt_value: Optional SGT value to filter by
            
        Returns:
            List of authorization profile dictionaries
        """
        conn = self._get_connection()
        
        query = "SELECT * FROM ise_auth_profiles WHERE 1=1"
        params = []
        
        if ise_server:
            query += " AND ise_server = ?"
            params.append(ise_server)
        
        if sgt_value is not None:
            query += " AND sgt_value = ?"
            params.append(sgt_value)
        
        query += " ORDER BY name"
        
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def store_ise_auth_policies(self, ise_server: str, policies: List[Dict[str, Any]]) -> int:
        """
        Store ISE authorization policies in cache.
        
        Args:
            ise_server: ISE server identifier
            policies: List of authorization policy dictionaries from ISE API
            
        Returns:
            Number of policies stored
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Delete existing policies for this ISE server
        cursor.execute("DELETE FROM ise_auth_policies WHERE ise_server = ?", (ise_server,))
        
        count = 0
        for policy in policies:
            # Extract profile ID and name
            profile_id = None
            profile_name = None
            
            # Profile can be a string (name) or dict with id/name
            profile_ref = policy.get('profile')
            if isinstance(profile_ref, str):
                profile_name = profile_ref
            elif isinstance(profile_ref, dict):
                profile_id = profile_ref.get('id')
                profile_name = profile_ref.get('name')
            
            # Generate condition summary (simplified)
            condition_summary = "Unknown condition"
            condition_data = policy.get('condition', {})
            if condition_data:
                # Try to extract a human-readable summary
                if 'children' in condition_data:
                    condition_summary = f"Policy with {len(condition_data['children'])} conditions"
            
            cursor.execute("""
                INSERT OR REPLACE INTO ise_auth_policies
                (id, name, description, profile_id, profile_name, rank, state, condition_summary, condition_data, ise_server, synced_at, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            """, (
                policy.get('id'),
                policy.get('name'),
                policy.get('description'),
                profile_id,
                profile_name,
                policy.get('rank', 0),
                policy.get('state', 'enabled'),
                condition_summary,
                json.dumps(condition_data),
                ise_server,
                json.dumps(policy),  # Store full policy as JSON for reference
            ))
            count += 1
        
        conn.commit()
        logger.info(f"Stored {count} authorization policies from ISE server {ise_server}")
        return count
    
    def get_ise_auth_policies(self, ise_server: Optional[str] = None, profile_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get cached ISE authorization policies.
        
        Args:
            ise_server: Optional ISE server identifier to filter by
            profile_name: Optional profile name to filter by
            
        Returns:
            List of authorization policy dictionaries
        """
        conn = self._get_connection()
        
        query = "SELECT * FROM ise_auth_policies WHERE 1=1"
        params = []
        
        if ise_server:
            query += " AND ise_server = ?"
            params.append(ise_server)
        
        if profile_name:
            query += " AND profile_name = ?"
            params.append(profile_name)
        
        query += " ORDER BY rank, name"
        
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_ise_sync_status(self, ise_server: str) -> Optional[Dict[str, Any]]:
        """Get last sync time for an ISE server."""
        conn = self._get_connection()
        
        # Get latest sync time from each table
        sgt_cursor = conn.execute("""
            SELECT MAX(synced_at) as last_sync, COUNT(*) as count
            FROM ise_sgts WHERE ise_server = ?
        """, (ise_server,))
        sgt_row = sgt_cursor.fetchone()
        
        profile_cursor = conn.execute("""
            SELECT MAX(synced_at) as last_sync, COUNT(*) as count
            FROM ise_auth_profiles WHERE ise_server = ?
        """, (ise_server,))
        profile_row = profile_cursor.fetchone()
        
        policy_cursor = conn.execute("""
            SELECT MAX(synced_at) as last_sync, COUNT(*) as count
            FROM ise_auth_policies WHERE ise_server = ?
        """, (ise_server,))
        policy_row = policy_cursor.fetchone()
        
        return {
            "ise_server": ise_server,
            "sgts": {
                "last_sync": sgt_row['last_sync'] if sgt_row and sgt_row['last_sync'] else None,
                "count": sgt_row['count'] if sgt_row else 0,
            },
            "auth_profiles": {
                "last_sync": profile_row['last_sync'] if profile_row and profile_row['last_sync'] else None,
                "count": profile_row['count'] if profile_row else 0,
            },
            "auth_policies": {
                "last_sync": policy_row['last_sync'] if policy_row and policy_row['last_sync'] else None,
                "count": policy_row['count'] if policy_row else 0,
            },
        }
    
    # ========== ISE Session SGT Assignment Operations ==========
    
    def store_ise_session_sgt_assignment(
        self,
        endpoint_id: str,
        user_id: Optional[str],
        session_id: str,
        user_sgt: Optional[int],
        device_sgt: Optional[int],
        current_sgt: Optional[int],
        ise_profile: Optional[str],
        policy_set: Optional[str],
        authz_profile: Optional[str],
        ip_address: Optional[str],
        switch_id: Optional[str],
    ) -> None:
        """
        Store current SGT assignment from an ISE session event (pxGrid).
        
        This tracks what SGT ISE has actually assigned to a device/user,
        allowing Clarion to compare its recommendations with actual ISE assignments.
        """
        conn = self._get_connection()
        
        # Use INSERT OR REPLACE to update existing assignments
        conn.execute("""
            INSERT OR REPLACE INTO ise_current_sgt_assignments
            (endpoint_id, user_id, session_id, user_sgt, device_sgt, current_sgt,
             ise_profile, policy_set, authz_profile, ip_address, switch_id,
             assigned_at, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            endpoint_id, user_id, session_id, user_sgt, device_sgt, current_sgt,
            ise_profile, policy_set, authz_profile, ip_address, switch_id
        ))
        conn.commit()
    
    def get_ise_current_sgt_assignment(self, endpoint_id: str) -> Optional[Dict[str, Any]]:
        """Get the current ISE SGT assignment for a device."""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT * FROM ise_current_sgt_assignments WHERE endpoint_id = ?
        """, (endpoint_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def clear_ise_session_assignment(self, session_id: str) -> None:
        """Clear ISE session assignment when session terminates."""
        conn = self._get_connection()
        conn.execute("""
            DELETE FROM ise_current_sgt_assignments WHERE session_id = ?
        """, (session_id,))
        conn.commit()


# Global database instance
_db_instance: Optional[ClarionDatabase] = None
_db_lock = threading.Lock()


def get_database(db_path: str = "clarion.db") -> ClarionDatabase:
    """Get or create the global database instance."""
    global _db_instance
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                _db_instance = ClarionDatabase(db_path)
    return _db_instance


def init_database(db_path: str = "clarion.db") -> ClarionDatabase:
    """Initialize the database (creates schema if needed)."""
    return get_database(db_path)

