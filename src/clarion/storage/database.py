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
        
        # Topology tables (locations, address spaces, subnets, switches)
        self._init_topology_schema(conn)
        
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
        
        # Cluster assignments (endpoint -> cluster)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cluster_assignments (
                endpoint_id TEXT NOT NULL,
                cluster_id INTEGER NOT NULL,
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
                src_sgt INTEGER,  -- Source Security Group Tag (from NetFlow v9/IPFIX)
                dst_sgt INTEGER,  -- Destination Security Group Tag (from NetFlow v9/IPFIX)
                src_mac TEXT,     -- Source MAC address (from NetFlow v9/IPFIX)
                dst_mac TEXT,     -- Destination MAC address (from NetFlow v9/IPFIX)
                vlan_id INTEGER,  -- VLAN ID (from NetFlow v9/IPFIX)
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for netflow
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_netflow_src 
            ON netflow(src_ip, flow_start)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_netflow_dst 
            ON netflow(dst_ip, flow_start)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_netflow_sgt 
            ON netflow(src_sgt, dst_sgt, flow_start)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_netflow_mac 
            ON netflow(src_mac, dst_mac)
        """)
        
        conn.commit()
        logger.info(f"Database schema initialized: {self.db_path}")
    
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
                vlan_id INTEGER,
                switch_id TEXT,  -- Primary switch
                gateway_ip TEXT,
                dhcp_start TEXT,
                dhcp_end TEXT,
                purpose TEXT NOT NULL,  -- USER, SERVER, IOT, GUEST, etc.
                metadata TEXT,  -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (location_id) REFERENCES locations(location_id)
            )
        """)
        
        # Switches (with location)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS switches (
                switch_id TEXT PRIMARY KEY,
                hostname TEXT NOT NULL UNIQUE,
                model TEXT,
                location_id TEXT NOT NULL,
                management_ip TEXT NOT NULL,
                serial_number TEXT,
                software_version TEXT,
                capabilities TEXT,  -- JSON array
                edge_agent_enabled BOOLEAN DEFAULT 0,
                metadata TEXT,  -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (location_id) REFERENCES locations(location_id)
            )
        """)
        
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
    ) -> int:
        """Store or update a sketch."""
        with self.transaction() as conn:
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
            return cursor.lastrowid
    
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
    ):
        """Store cluster metadata."""
        with self.transaction() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO clusters (
                    cluster_id, cluster_label, sgt_value, sgt_name, endpoint_count,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (cluster_id, cluster_label, sgt_value, sgt_name, endpoint_count))
    
    def assign_endpoint_to_cluster(self, endpoint_id: str, cluster_id: int):
        """Assign an endpoint to a cluster."""
        with self.transaction() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cluster_assignments 
                (endpoint_id, cluster_id) VALUES (?, ?)
            """, (endpoint_id, cluster_id))
    
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

