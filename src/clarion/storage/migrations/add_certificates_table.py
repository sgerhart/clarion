"""
Migration: Add global certificates table.

Creates a centralized certificate management table that can be referenced by connectors.
Supports storing client certificates, private keys, CA certificates, and CSRs.
"""
import sqlite3
import logging

logger = logging.getLogger(__name__)

def migrate(conn: sqlite3.Connection):
    """Add global certificates table."""
    cursor = conn.cursor()
    
    # Certificates table - global certificate storage
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,  -- Human-readable name (e.g., "Clarion-pxGrid-Client")
            description TEXT,  -- Optional description
            cert_type TEXT NOT NULL,  -- 'client_cert', 'client_key', 'ca_cert', 'csr'
            
            -- Certificate data
            cert_data BLOB NOT NULL,  -- Certificate/key/CSR data (encrypted at rest in production)
            cert_filename TEXT,  -- Original filename if uploaded
            
            -- CSR-specific fields (only populated for CSR type)
            csr_subject TEXT,  -- Subject DN from CSR
            csr_key_size INTEGER,  -- Key size (2048, 4096, etc.)
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT  -- User/system that created the certificate
        )
    """)
    
    # Certificate references table - links certificates to connectors
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS certificate_connector_references (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            certificate_id INTEGER NOT NULL,
            connector_id TEXT NOT NULL,
            reference_type TEXT NOT NULL,  -- 'client_cert', 'client_key', 'ca_cert'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (certificate_id) REFERENCES certificates(id) ON DELETE CASCADE,
            FOREIGN KEY (connector_id) REFERENCES connectors(connector_id) ON DELETE CASCADE,
            UNIQUE(certificate_id, connector_id, reference_type)
        )
    """)
    
    # Indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_certificates_name ON certificates(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_certificates_type ON certificates(cert_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cert_conn_ref_cert ON certificate_connector_references(certificate_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cert_conn_ref_conn ON certificate_connector_references(connector_id)")
    
    logger.info("Global certificates table migration completed.")

