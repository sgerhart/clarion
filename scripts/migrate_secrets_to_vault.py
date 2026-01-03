#!/usr/bin/env python3
"""
Migration Script: Database to Vault

Migrates all secrets from the database to HashiCorp Vault.
Removes sensitive data from database and stores Vault path references.

Usage:
    python scripts/migrate_secrets_to_vault.py [--dry-run] [--connector-id CONNECTOR_ID]
"""
import argparse
import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clarion.storage import get_database
from clarion.secrets import VaultClient, VaultConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_connector_credentials(db, vault, connector_id: str, dry_run: bool = False):
    """Migrate connector credentials from database to Vault."""
    logger.info(f"Migrating credentials for connector: {connector_id}")
    
    # Get connector config from database
    conn = db.get_connection()
    cursor = conn.execute("""
        SELECT config, type
        FROM connectors
        WHERE connector_id = ?
    """, (connector_id,))
    
    row = cursor.fetchone()
    if not row:
        logger.warning(f"Connector {connector_id} not found in database")
        return False
    
    config_json = row['config']
    connector_type = row['type']
    
    if not config_json:
        logger.info(f"No configuration found for {connector_id}")
        return True
    
    try:
        config = json.loads(config_json)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON config for {connector_id}: {e}")
        return False
    
    # Extract credentials
    username = config.get('username')
    password = config.get('password')
    hostname = config.get('hostname')
    
    if not username and not password:
        logger.info(f"No credentials found in config for {connector_id}")
        return True
    
    # Prepare data for Vault
    vault_data = {}
    if username:
        vault_data['username'] = username
    if password:
        vault_data['password'] = password
    if hostname:
        vault_data['hostname'] = hostname
    
    # Copy other non-sensitive config
    for key, value in config.items():
        if key not in ['username', 'password'] and not key.startswith('_'):
            vault_data[key] = value
    
    if dry_run:
        logger.info(f"[DRY RUN] Would store credentials for {connector_id} in Vault")
        logger.info(f"[DRY RUN] Data: {list(vault_data.keys())}")
        return True
    
    # Store in Vault
    try:
        vault.store_connector_credentials(connector_id, **vault_data)
        logger.info(f"✅ Stored credentials for {connector_id} in Vault")
        
        # Update database: remove password, add vault_path
        config.pop('password', None)
        config['vault_path'] = vault.config.get_connector_path(connector_id)
        
        # Update database
        conn.execute("""
            UPDATE connectors
            SET config = ?, updated_at = CURRENT_TIMESTAMP
            WHERE connector_id = ?
        """, (json.dumps(config), connector_id))
        conn.commit()
        
        logger.info(f"✅ Updated database for {connector_id} (removed password, added vault_path)")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to migrate credentials for {connector_id}: {e}")
        return False


def migrate_certificates(db, vault, connector_id: str = None, dry_run: bool = False):
    """Migrate certificates from database to Vault."""
    logger.info("Migrating certificates to Vault")
    
    conn = db.get_connection()
    
    # Query certificates
    if connector_id:
        # Get certificates for specific connector
        cursor = conn.execute("""
            SELECT 
                c.id, c.cert_type, c.cert_data, c.cert_filename,
                r.connector_id, r.reference_type
            FROM certificates c
            INNER JOIN certificate_connector_references r ON c.id = r.certificate_id
            WHERE r.connector_id = ?
        """, (connector_id,))
    else:
        # Get all certificates
        cursor = conn.execute("""
            SELECT 
                c.id, c.cert_type, c.cert_data, c.cert_filename,
                r.connector_id, r.reference_type
            FROM certificates c
            LEFT JOIN certificate_connector_references r ON c.id = r.certificate_id
        """)
    
    rows = cursor.fetchall()
    
    if not rows:
        logger.info("No certificates found to migrate")
        return True
    
    migrated = 0
    for row in rows:
        cert_id = row['id']
        cert_type = row['cert_type']
        cert_data = row['cert_data']
        cert_filename = row['cert_filename']
        ref_connector_id = row['connector_id']
        ref_type = row['reference_type']
        
        # Create certificate ID
        if ref_connector_id and ref_type:
            certificate_id = f"{ref_connector_id}-{ref_type}"
        else:
            certificate_id = f"cert-{cert_id}"
        
        logger.info(f"Migrating certificate: {certificate_id} (type: {cert_type})")
        
        if dry_run:
            logger.info(f"[DRY RUN] Would store certificate {certificate_id} in Vault")
            continue
        
        # Store in Vault
        try:
            # For connector certificates, we need to get all related certs
            if ref_connector_id and ref_type in ['client_cert', 'client_key', 'ca_cert']:
                # Get all certs for this connector
                cert_cursor = conn.execute("""
                    SELECT c.cert_type, c.cert_data, r.reference_type
                    FROM certificates c
                    INNER JOIN certificate_connector_references r ON c.id = r.certificate_id
                    WHERE r.connector_id = ? AND r.reference_type IN ('client_cert', 'client_key', 'ca_cert')
                """, (ref_connector_id,))
                
                cert_rows = cert_cursor.fetchall()
                cert_data_dict = {}
                key_data = None
                ca_cert_data = None
                
                for cert_row in cert_rows:
                    ref_type = cert_row['reference_type']
                    data = cert_row['cert_data']
                    
                    if ref_type == 'client_cert':
                        cert_data_dict['cert_data'] = data
                    elif ref_type == 'client_key':
                        key_data = data
                    elif ref_type == 'ca_cert':
                        ca_cert_data = data
                
                if 'cert_data' in cert_data_dict:
                    vault.store_certificate(
                        certificate_id=ref_connector_id,
                        cert_data=cert_data_dict['cert_data'],
                        key_data=key_data,
                        ca_cert_data=ca_cert_data,
                        cert_type=cert_type
                    )
                    logger.info(f"✅ Stored certificate bundle for {ref_connector_id} in Vault")
                    migrated += 1
            else:
                # Store individual certificate
                vault.store_certificate(
                    certificate_id=certificate_id,
                    cert_data=cert_data,
                    cert_type=cert_type
                )
                logger.info(f"✅ Stored certificate {certificate_id} in Vault")
                migrated += 1
                
        except Exception as e:
            logger.error(f"❌ Failed to migrate certificate {certificate_id}: {e}")
    
    if not dry_run and migrated > 0:
        logger.info(f"✅ Migrated {migrated} certificate(s) to Vault")
        logger.info("⚠️  Note: Certificate BLOB data still in database. Run cleanup after verification.")
    
    return True


def cleanup_database(db, connector_id: str = None, dry_run: bool = False):
    """Remove sensitive data from database after migration."""
    logger.info("Cleaning up database (removing sensitive data)")
    
    conn = db.get_connection()
    
    if connector_id:
        # Cleanup specific connector
        cursor = conn.execute("""
            SELECT connector_id, config
            FROM connectors
            WHERE connector_id = ?
        """, (connector_id,))
    else:
        # Cleanup all connectors
        cursor = conn.execute("""
            SELECT connector_id, config
            FROM connectors
            WHERE config IS NOT NULL
        """)
    
    rows = cursor.fetchall()
    
    for row in rows:
        cid = row['connector_id']
        config_json = row['config']
        
        if not config_json:
            continue
        
        try:
            config = json.loads(config_json)
        except json.JSONDecodeError:
            continue
        
        # Check if vault_path exists (migration completed)
        if 'vault_path' not in config:
            logger.warning(f"Skipping {cid}: vault_path not found (migration may not be complete)")
            continue
        
        # Remove password if still present
        if 'password' in config:
            if dry_run:
                logger.info(f"[DRY RUN] Would remove password from {cid}")
            else:
                config.pop('password')
                conn.execute("""
                    UPDATE connectors
                    SET config = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE connector_id = ?
                """, (json.dumps(config), cid))
                logger.info(f"✅ Removed password from {cid}")
    
    if not dry_run:
        conn.commit()
        logger.info("✅ Database cleanup complete")
    
    # Note: Certificate BLOB cleanup should be done separately after verification
    logger.info("⚠️  Certificate BLOB cleanup: Run after verifying Vault migration")


def main():
    parser = argparse.ArgumentParser(description="Migrate secrets from database to Vault")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes"
    )
    parser.add_argument(
        "--connector-id",
        type=str,
        help="Migrate specific connector only"
    )
    parser.add_argument(
        "--skip-certificates",
        action="store_true",
        help="Skip certificate migration"
    )
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="Only cleanup database (assumes migration already done)"
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")
    
    # Initialize database
    try:
        db = get_database()
        logger.info("✅ Connected to database")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        return 1
    
    # Initialize Vault
    if not args.cleanup_only:
        try:
            vault_config = VaultConfig.from_env()
            vault = VaultClient(vault_config)
            
            # Health check
            health = vault.health_check()
            if not health.get("healthy"):
                logger.error("❌ Vault is not healthy")
                return 1
            
            logger.info("✅ Connected to Vault")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Vault: {e}")
            logger.error("Make sure Vault is running and VAULT_ADDR/VAULT_TOKEN are set")
            return 1
    
    # Run migration
    success = True
    
    if args.cleanup_only:
        cleanup_database(db, args.connector_id, args.dry_run)
    else:
        # Migrate connector credentials
        if args.connector_id:
            success = migrate_connector_credentials(db, vault, args.connector_id, args.dry_run)
        else:
            # Migrate all connectors
            conn = db.get_connection()
            cursor = conn.execute("SELECT connector_id FROM connectors")
            connectors = [row['connector_id'] for row in cursor.fetchall()]
            
            for connector_id in connectors:
                if not migrate_connector_credentials(db, vault, connector_id, args.dry_run):
                    success = False
        
        # Migrate certificates
        if not args.skip_certificates:
            if not migrate_certificates(db, vault, args.connector_id, args.dry_run):
                success = False
        
        # Cleanup database
        cleanup_database(db, args.connector_id, args.dry_run)
    
    if success:
        logger.info("✅ Migration completed successfully")
        if args.dry_run:
            logger.info("🔍 This was a dry run. Run without --dry-run to perform actual migration.")
        return 0
    else:
        logger.error("❌ Migration completed with errors")
        return 1


if __name__ == "__main__":
    sys.exit(main())

