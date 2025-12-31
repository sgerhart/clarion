"""
Migration: Add connector management tables.

Adds tables for storing connector configurations and certificates.
"""
import sqlite3
import logging

logger = logging.getLogger(__name__)

def migrate(conn: sqlite3.Connection):
    """Add connector management tables."""
    cursor = conn.cursor()
    
    # Connectors table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS connectors (
            connector_id TEXT PRIMARY KEY,  -- 'ise_ers', 'ise_pxgrid', 'ad', 'iot_medigate', etc.
            name TEXT NOT NULL,
            type TEXT NOT NULL,  -- 'ise_ers', 'ise_pxgrid', 'ad', 'iot'
            enabled BOOLEAN DEFAULT 0,
            status TEXT DEFAULT 'disabled',  -- 'enabled', 'disabled', 'error', 'connecting', 'connected'
            
            -- Connection configuration (JSON string)
            config TEXT,  -- JSON string with connector-specific settings
            
            -- Status tracking
            last_connected TIMESTAMP,
            last_error TEXT,
            error_count INTEGER DEFAULT 0,
            
            -- Metadata
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Connector certificates table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS connector_certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            connector_id TEXT NOT NULL,
            cert_type TEXT NOT NULL,  -- 'client_cert', 'client_key', 'ca_cert'
            cert_data BLOB NOT NULL,  -- Certificate data (encrypted at rest in production)
            cert_filename TEXT,  -- Original filename
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (connector_id) REFERENCES connectors(connector_id)
        )
    """)
    
    # Indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_connectors_type ON connectors(type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_connectors_enabled ON connectors(enabled)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_connectors_status ON connectors(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_connector_certificates_connector ON connector_certificates(connector_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_connector_certificates_type ON connector_certificates(connector_id, cert_type)")
    
    logger.info("Connector management tables migration completed.")

