"""
Connector Management API Routes

Endpoints for managing external system connectors (ISE, pxGrid, AD).
Includes configuration storage, certificate management, and container deployment.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import logging
import json
import os
from datetime import datetime

from clarion.storage import get_database

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== Helper Functions ==========

def load_pxgrid_certificates(conn, connector_id: str = 'ise_pxgrid'):
    """
    Load certificate data from database for pxGrid connector.
    
    Returns:
        tuple: (client_cert_data, client_key_data, ca_cert_data) as bytes or None
    """
    client_cert_data = None
    client_key_data = None
    ca_cert_data = None
    
    try:
        cert_cursor = conn.execute("""
            SELECT 
                c.cert_type, c.cert_data, r.reference_type
            FROM certificates c
            INNER JOIN certificate_connector_references r ON c.id = r.certificate_id
            WHERE r.connector_id = ? AND r.reference_type IN ('client_cert', 'client_key', 'ca_cert')
        """, (connector_id,))
        
        cert_rows = cert_cursor.fetchall()
        for cert_row in cert_rows:
            ref_type = cert_row['reference_type']
            cert_data = cert_row['cert_data']
            
            if ref_type == 'client_cert':
                client_cert_data = cert_data
                logger.info(f"Loaded client certificate from database (size: {len(cert_data)} bytes)")
            elif ref_type == 'client_key':
                client_key_data = cert_data
                logger.info(f"Loaded client private key from database (size: {len(cert_data)} bytes)")
            elif ref_type == 'ca_cert':
                ca_cert_data = cert_data
                logger.info(f"Loaded CA certificate from database (size: {len(cert_data)} bytes)")
    except Exception as e:
        # Try old connector_certificates table for backward compatibility
        try:
            cert_cursor = conn.execute("""
                SELECT cert_type, cert_data FROM connector_certificates 
                WHERE connector_id = ? AND cert_type IN ('client_cert', 'client_key', 'ca_cert')
            """, (connector_id,))
            
            cert_rows = cert_cursor.fetchall()
            for cert_row in cert_rows:
                cert_type = cert_row['cert_type']
                cert_data = cert_row['cert_data']
                
                if cert_type == 'client_cert':
                    client_cert_data = cert_data
                elif cert_type == 'client_key':
                    client_key_data = cert_data
                elif cert_type == 'ca_cert':
                    ca_cert_data = cert_data
        except Exception:
            # Neither table exists or has certificates
            logger.debug(f"Could not load certificates: {e}")
            pass
    
    return client_cert_data, client_key_data, ca_cert_data


# ========== Request/Response Models ==========

class ConnectorConfigRequest(BaseModel):
    """Request to configure a connector."""
    config: Dict[str, Any] = Field(..., description="Connector-specific configuration (JSON)")
    enabled: Optional[bool] = Field(None, description="Enable/disable connector (triggers container deployment)")


class ConnectorResponse(BaseModel):
    """Connector response."""
    connector_id: str
    name: str
    type: str
    enabled: bool
    status: str  # 'enabled', 'disabled', 'error', 'connecting', 'connected'
    config: Optional[Dict[str, Any]]
    description: Optional[str]
    last_connected: Optional[str]
    last_error: Optional[str]
    error_count: int
    container_status: Optional[str]  # 'running', 'stopped', 'starting', 'error'
    certificates: Optional[Dict[str, bool]]  # {'has_client_cert': True, 'has_client_key': True, ...}


class ConnectorListResponse(BaseModel):
    """List of connectors."""
    connectors: List[ConnectorResponse]


class ConnectorStatusResponse(BaseModel):
    """Connector status response."""
    connector_id: str
    enabled: bool
    status: str
    container_status: Optional[str]
    is_connected: bool
    last_connected: Optional[str]
    last_error: Optional[str]
    error_count: int


# ========== Connector Management Endpoints ==========

@router.get("/connectors", response_model=ConnectorListResponse)
async def list_connectors():
    """
    List all available connectors with their status.
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Define available connector types
        connector_definitions = {
            'ise_ers': {
                'name': 'ISE ERS API',
                'type': 'ise_ers',
                'description': 'Cisco ISE ERS API connector for policy deployment and configuration sync'
            },
            'ise_pxgrid': {
                'name': 'ISE pxGrid',
                'type': 'ise_pxgrid',
                'description': 'Cisco ISE pxGrid connector for real-time session and endpoint events'
            },
            'ad': {
                'name': 'Active Directory',
                'type': 'ad',
                'description': 'LDAP connector for users, groups, and device information'
            },
        }
        
        connectors = []
        for connector_id, definition in connector_definitions.items():
            # Get connector from database
            cursor = conn.execute("""
                SELECT * FROM connectors WHERE connector_id = ?
            """, (connector_id,))
            row = cursor.fetchone()
            
            if row:
                # Parse config JSON
                config = json.loads(row['config']) if row['config'] else None
                
                # Get certificate status from new global certificates system
                try:
                    cert_cursor = conn.execute("""
                        SELECT reference_type FROM certificate_connector_references 
                        WHERE connector_id = ?
                    """, (connector_id,))
                    cert_types = {row['reference_type'] for row in cert_cursor.fetchall()}
                except Exception:
                    # Fallback: check old connector_certificates table for backward compatibility
                    try:
                        cert_cursor = conn.execute("""
                            SELECT cert_type FROM connector_certificates WHERE connector_id = ?
                        """, (connector_id,))
                        cert_types = {row['cert_type'] for row in cert_cursor.fetchall()}
                    except Exception:
                        cert_types = set()
                certificates = {
                    'has_client_cert': 'client_cert' in cert_types,
                    'has_client_key': 'client_key' in cert_types,
                    'has_ca_cert': 'ca_cert' in cert_types,
                }
                
                connectors.append(ConnectorResponse(
                    connector_id=row['connector_id'],
                    name=row['name'],
                    type=row['type'],
                    enabled=bool(row['enabled']),
                    status=row['status'],
                    config=config,
                    description=row['description'] if row['description'] else None,
                    last_connected=row['last_connected'],
                    last_error=row['last_error'],
                    error_count=row['error_count'],
                    container_status=None,  # TODO: Get from Docker API
                    certificates=certificates,
                ))
            else:
                # Return default (not configured) connector
                connectors.append(ConnectorResponse(
                    connector_id=connector_id,
                    name=definition['name'],
                    type=definition['type'],
                    enabled=False,
                    status='disabled',
                    config=None,
                    description=definition['description'],
                    last_connected=None,
                    last_error=None,
                    error_count=0,
                    container_status='stopped',
                    certificates={'has_client_cert': False, 'has_client_key': False, 'has_ca_cert': False},
                ))
        
        return ConnectorListResponse(connectors=connectors)
        
    except Exception as e:
        logger.error(f"Error listing connectors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connectors/{connector_id}", response_model=ConnectorResponse)
async def get_connector(connector_id: str):
    """
    Get connector configuration and status.
    
    Returns default connector info if not yet configured in database.
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Define available connector types (same as list_connectors)
        connector_definitions = {
            'ise_ers': {
                'name': 'ISE ERS API',
                'type': 'ise_ers',
                'description': 'Cisco ISE ERS API connector for policy deployment and configuration sync'
            },
            'ise_pxgrid': {
                'name': 'ISE pxGrid',
                'type': 'ise_pxgrid',
                'description': 'Cisco ISE pxGrid connector for real-time session and endpoint events'
            },
            'ad': {
                'name': 'Active Directory',
                'type': 'ad',
                'description': 'LDAP connector for users, groups, and device information'
            },
        }
        
        # Validate connector_id
        if connector_id not in connector_definitions:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown connector: {connector_id}"
            )
        
        definition = connector_definitions[connector_id]
        
        cursor = conn.execute("""
            SELECT * FROM connectors WHERE connector_id = ?
        """, (connector_id,))
        row = cursor.fetchone()
        
        if row:
            # Parse config JSON
            config = json.loads(row['config']) if row['config'] else None
            
            # Get certificate status from new global certificates system
            try:
                cert_cursor = conn.execute("""
                    SELECT reference_type FROM certificate_connector_references 
                    WHERE connector_id = ?
                """, (connector_id,))
                cert_types = {row['reference_type'] for row in cert_cursor.fetchall()}
            except Exception:
                # Fallback: check old connector_certificates table for backward compatibility
                try:
                    cert_cursor = conn.execute("""
                        SELECT cert_type FROM connector_certificates WHERE connector_id = ?
                    """, (connector_id,))
                    cert_types = {row['cert_type'] for row in cert_cursor.fetchall()}
                except Exception:
                    cert_types = set()
            certificates = {
                'has_client_cert': 'client_cert' in cert_types,
                'has_client_key': 'client_key' in cert_types,
                'has_ca_cert': 'ca_cert' in cert_types,
            }
            
            return ConnectorResponse(
                connector_id=row['connector_id'],
                name=row['name'],
                type=row['type'],
                enabled=bool(row['enabled']),
                status=row['status'],
                config=config,
                description=row['description'] if row['description'] else None,
                last_connected=row['last_connected'],
                last_error=row['last_error'],
                error_count=row['error_count'],
                container_status=None,  # TODO: Get from Docker API
                certificates=certificates,
            )
        else:
            # Return default (not configured) connector
            # Get certificate status from new global certificates system (might have certificates even if not configured)
            try:
                cert_cursor = conn.execute("""
                    SELECT reference_type FROM certificate_connector_references 
                    WHERE connector_id = ?
                """, (connector_id,))
                cert_types = {row['reference_type'] for row in cert_cursor.fetchall()}
            except Exception:
                # Fallback: check old connector_certificates table for backward compatibility
                try:
                    cert_cursor = conn.execute("""
                        SELECT cert_type FROM connector_certificates WHERE connector_id = ?
                    """, (connector_id,))
                    cert_types = {row['cert_type'] for row in cert_cursor.fetchall()}
                except Exception:
                    cert_types = set()
            certificates = {
                'has_client_cert': 'client_cert' in cert_types,
                'has_client_key': 'client_key' in cert_types,
                'has_ca_cert': 'ca_cert' in cert_types,
            }
            
            return ConnectorResponse(
                connector_id=connector_id,
                name=definition['name'],
                type=definition['type'],
                enabled=False,
                status='disabled',
                config=None,
                description=definition['description'],
                last_connected=None,
                last_error=None,
                error_count=0,
                container_status='stopped',
                certificates=certificates,
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting connector {connector_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connectors/{connector_id}/configure", response_model=ConnectorResponse)
async def configure_connector(connector_id: str, request: ConnectorConfigRequest):
    """
    Configure a connector (save configuration without enabling).
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Get connector definition
        connector_definitions = {
            'ise_ers': {'name': 'ISE ERS API', 'type': 'ise_ers', 'description': 'Cisco ISE ERS API connector'},
            'ise_pxgrid': {'name': 'ISE pxGrid', 'type': 'ise_pxgrid', 'description': 'Cisco ISE pxGrid connector'},
            'ad': {'name': 'Active Directory', 'type': 'ad', 'description': 'LDAP connector'},
        }
        
        if connector_id not in connector_definitions:
            raise HTTPException(status_code=404, detail=f"Unknown connector type: {connector_id}")
        
        definition = connector_definitions[connector_id]
        
        # Check if connector exists
        cursor = conn.execute("""
            SELECT connector_id FROM connectors WHERE connector_id = ?
        """, (connector_id,))
        exists = cursor.fetchone() is not None
        
        # For pxGrid, if username matches client_name, ensure we're using client credentials
        if connector_id == 'ise_pxgrid' and request.config:
            config = request.config
            username = config.get('username', '')
            client_name = config.get('client_name', '')
            password = config.get('password', '')
            
            # If username matches client_name, this is client credentials - ensure username is set correctly
            if username == client_name and password:
                logger.info(f"pxGrid configuration: username matches client_name - using client credentials")
                logger.info(f"  username: {username}, client_name: {client_name}, password_length: {len(password)}")
                # Ensure username is set to client_name (should already be, but double-check)
                config['username'] = client_name
            elif username != client_name and password:
                logger.info(f"pxGrid configuration: username != client_name - using ISE admin credentials for new client creation")
                logger.info(f"  username: {username}, client_name: {client_name}, password_length: {len(password)}")
        
        config_json = json.dumps(request.config) if request.config else None
        
        if exists:
            # Update existing connector
            conn.execute("""
                UPDATE connectors
                SET config = ?, updated_at = CURRENT_TIMESTAMP
                WHERE connector_id = ?
            """, (config_json, connector_id))
            if request.enabled is not None:
                conn.execute("""
                    UPDATE connectors
                    SET enabled = ?
                    WHERE connector_id = ?
                """, (1 if request.enabled else 0, connector_id))
        else:
            # Insert new connector
            conn.execute("""
                INSERT INTO connectors (
                    connector_id, name, type, enabled, status, config, description,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                connector_id,
                definition['name'],
                definition['type'],
                1 if request.enabled else 0,
                'disabled',
                config_json,
                definition['description'],
            ))
        
        # Clear last_error on successful configuration
        conn.execute("""
            UPDATE connectors
            SET last_error = NULL, status = 'disabled', updated_at = CURRENT_TIMESTAMP
            WHERE connector_id = ?
        """, (connector_id,))
        conn.commit()
        
        # Return updated connector
        return await get_connector(connector_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error configuring connector {connector_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connectors/{connector_id}/enable", response_model=ConnectorStatusResponse)
async def enable_connector(connector_id: str):
    """
    Enable a connector (deploy container if needed).
    
    This will:
    1. Validate connector configuration
    2. Check for required certificates (if needed)
    3. Start container (if connector requires one)
    4. Update connector status to 'enabled'
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Get connector
        cursor = conn.execute("""
            SELECT * FROM connectors WHERE connector_id = ?
        """, (connector_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Connector {connector_id} not configured. Please configure it first."
            )
        
        if not row['config']:
            raise HTTPException(
                status_code=400,
                detail=f"Connector {connector_id} has no configuration. Please configure it first."
            )
        
        # Validate configuration based on connector type
        config = json.loads(row['config']) if row['config'] else {}
        
        if connector_id == 'ise_ers':
            # For ISE ERS API, validate connection using saved credentials
            try:
                from clarion.integration.ise_client import ISEClient, ISEAuthenticationError
                
                ise_url = config.get('ise_url')
                ise_username = config.get('ise_username')
                ise_password = config.get('ise_password')
                verify_ssl = config.get('verify_ssl', False)
                
                if not ise_url or not ise_username or not ise_password:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Missing required ISE configuration: ise_url, ise_username, and ise_password are required"
                    )
                
                # Test connection using saved credentials
                logger.info(f"Validating ISE ERS API connection for enable: {ise_url} with username {ise_username}")
                try:
                    client = ISEClient(
                        base_url=ise_url,
                        username=ise_username,
                        password=ise_password,
                        verify_ssl=verify_ssl,
                    )
                    # ISEClient.__init__ will authenticate automatically
                    logger.info(f"Successfully validated ISE ERS API connection")
                except ISEAuthenticationError as e:
                    logger.error(f"ISE ERS API authentication failed during enable: {e}")
                    raise HTTPException(
                        status_code=401,
                        detail=f"Cannot enable connector: Authentication failed with saved credentials. Please check your ISE username and password. Error: {e}"
                    )
                except Exception as e:
                    logger.error(f"ISE ERS API connection error during enable: {e}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot enable connector: Connection failed. Please check your ISE configuration. Error: {e}"
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Unexpected error validating ISE ERS API connection: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Error validating connection: {e}"
                )
        elif connector_id == 'ise_pxgrid':
            # For pxGrid, first ensure the client account is created by testing the connection
            # This will create the account if it doesn't exist
            from clarion.integration.pxgrid_client import PxGridClient, PxGridConfig, PxGridAuthenticationError, PxGridPendingApprovalError
            
            try:
                # Reload config from database to ensure we have the latest (in case it was just saved)
                cursor = conn.execute("""
                    SELECT config FROM connectors WHERE connector_id = ?
                """, (connector_id,))
                config_row = cursor.fetchone()
                if config_row and config_row['config']:
                    config = json.loads(config_row['config'])
                    logger.info(f"Loaded pxGrid config from database for enable: hostname={config.get('ise_hostname')}, username={config.get('username')}, client_name={config.get('client_name')}")
                
                ise_hostname = config.get('ise_hostname')
                client_name = config.get('client_name', 'clarion-pxgrid-client')
                port = config.get('port', 8910)
                use_ssl = config.get('use_ssl', True)
                verify_ssl = config.get('verify_ssl', False)
                auth_method = config.get('auth_method', 'username_password')
                
                # For enable, determine which credentials to use:
                # - If stored_username == client_name: We have client credentials (client already exists)
                # - If stored_username != client_name: We have ISE admin credentials (use to create client)
                stored_username = config.get('username', '')
                stored_password = config.get('password', '')
                
                if stored_username == client_name and stored_password:
                    # We have client credentials stored - client already exists, use client credentials
                    username = client_name
                    password = stored_password
                    logger.info(f"Using stored client credentials for enable (client exists): username={client_name}, password_length={len(password)}")
                elif stored_username and stored_username != client_name and stored_password:
                    # We have ISE admin credentials stored - use them to create the client
                    username = stored_username
                    password = stored_password
                    logger.info(f"Using stored ISE admin credentials for enable (will create client): username={username}, password_length={len(password)}")
                elif stored_password:
                    # We have a password but unclear username - assume it's ISE admin credentials for new client
                    # This handles edge cases where username might not be set correctly
                    username = stored_username if stored_username else 'admin'  # Default to 'admin' if not set
                    password = stored_password
                    logger.info(f"Using stored credentials for enable (assuming ISE admin for new client): username={username}, password_length={len(password)}")
                else:
                    # No stored credentials - use empty (will fail validation)
                    username = stored_username
                    password = stored_password
                    logger.warning(f"No stored credentials found in database config")
                
                # Check if certificates are assigned (for certificate auth)
                has_client_cert = False
                try:
                    cert_cursor = conn.execute("""
                        SELECT certificate_id FROM certificate_connector_references 
                        WHERE connector_id = ? AND reference_type = 'client_cert'
                    """, ('ise_pxgrid',))
                    has_client_cert = cert_cursor.fetchone() is not None
                except Exception:
                    try:
                        cert_cursor = conn.execute("""
                            SELECT id FROM connector_certificates 
                            WHERE connector_id = ? AND cert_type = 'client_cert'
                        """, ('ise_pxgrid',))
                        has_client_cert = cert_cursor.fetchone() is not None
                    except Exception:
                        has_client_cert = False
                
                actual_auth_method = 'certificate' if has_client_cert else auth_method
                
                if not ise_hostname:
                    raise HTTPException(
                        status_code=400,
                        detail="Missing required pxGrid configuration: ise_hostname is required"
                    )
                
                if actual_auth_method == 'username_password' and (not username or not password):
                    raise HTTPException(
                        status_code=400,
                        detail="Missing required pxGrid configuration for username/password authentication: username and password are required"
                    )
                
                # Load certificate data if using certificate authentication
                client_cert_data = None
                client_key_data = None
                ca_cert_data = None
                if actual_auth_method == 'certificate':
                    client_cert_data, client_key_data, ca_cert_data = load_pxgrid_certificates(conn, 'ise_pxgrid')
                    if not client_cert_data or not client_key_data:
                        raise HTTPException(
                            status_code=400,
                            detail="Certificate authentication selected but client certificate or private key not found in database. Please assign certificates in the Certificates section."
                        )
                
                # Create pxGrid client and connect to ensure account is created
                pxgrid_config = PxGridConfig(
                    ise_hostname=ise_hostname,
                    username=username,
                    password=password,
                    client_name=client_name,
                    port=port,
                    use_ssl=use_ssl,
                    verify_ssl=verify_ssl,
                    client_cert_data=client_cert_data,
                    client_key_data=client_key_data,
                    ca_cert_data=ca_cert_data,
                )
                
                # Note: Certificates are loaded by the pxGrid service from the database
                # We just test the connection here to ensure the account is created
                logger.info(f"Attempting to connect to pxGrid to create/verify account: hostname={ise_hostname}, client_name={client_name}, username={username}")
                client = PxGridClient(pxgrid_config)
                try:
                    # This will create the account if it doesn't exist
                    logger.info(f"Calling client.connect() to create/verify pxGrid account...")
                    is_connected = client.connect()
                    logger.info(f"pxGrid client.connect() returned: {is_connected}")
                    
                    # CRITICAL: ALWAYS update config with bootstrap password if ISE returned one
                    # This is the client password that ISE generated - we MUST store it immediately for future use
                    # The bootstrap_password is set in _create_account() when AccountCreate succeeds
                    if client.bootstrap_password:
                        logger.info(f"✅ Bootstrap password received from ISE during enable, storing in database IMMEDIATELY (length: {len(client.bootstrap_password)})")
                        config['password'] = client.bootstrap_password
                        config['username'] = client_name  # Use client_name as username for client credentials
                        config_json = json.dumps(config)
                        conn.execute("""
                            UPDATE connectors
                            SET config = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE connector_id = ?
                        """, (config_json, connector_id))
                        conn.commit()
                        logger.info(f"✅ Bootstrap password stored in database - this is now the client password for '{client_name}'")
                    else:
                        logger.warning(f"⚠️  No bootstrap password received from ISE - client may already exist or account creation failed")
                    
                    client.disconnect()  # Disconnect, pxGrid service will reconnect
                    logger.info(f"pxGrid account verified/created successfully")
                    
                    # Clear last_error on successful enable
                    conn.execute("""
                        UPDATE connectors
                        SET last_error = NULL, updated_at = CURRENT_TIMESTAMP
                        WHERE connector_id = ?
                    """, (connector_id,))
                    conn.commit()
                except PxGridPendingApprovalError as e:
                    # Account was created but is pending approval - this is expected, not an error
                    error_msg = str(e)
                    logger.info(f"pxGrid account is pending approval: {error_msg}")
                    
                    # CRITICAL: ALWAYS update config with bootstrap password if ISE returned one (even if pending approval)
                    # This is the client password that ISE generated - we MUST store it for future use
                    logger.info(f"🔍 Checking for bootstrap password in client object...")
                    logger.info(f"   client.bootstrap_password exists: {hasattr(client, 'bootstrap_password')}")
                    logger.info(f"   client.bootstrap_password value: {getattr(client, 'bootstrap_password', None) is not None}")
                    if hasattr(client, 'bootstrap_password') and client.bootstrap_password:
                        logger.info(f"✅ Bootstrap password found in client object (length: {len(client.bootstrap_password)})")
                        logger.info(f"✅ Saving bootstrap password to database IMMEDIATELY...")
                        config['password'] = client.bootstrap_password
                        config['username'] = client_name  # Use client_name as username for client credentials
                        config_json = json.dumps(config)
                        conn.execute("""
                            UPDATE connectors
                            SET config = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE connector_id = ?
                        """, (config_json, connector_id))
                        conn.commit()
                        logger.info(f"✅✅✅ Bootstrap password successfully stored in database - this is now the client password for '{client_name}'")
                        logger.info(f"   Database updated: username='{client_name}', password_length={len(client.bootstrap_password)}")
                    else:
                        logger.error(f"❌❌❌ CRITICAL: No bootstrap password found in client object!")
                        logger.error(f"   This means the password was not received from ISE or was not stored in client.bootstrap_password")
                        logger.error(f"   Account may have been created but password was not in the response")
                    
                    # Mark as enabled with pending_approval status - this is a success state
                    conn.execute("""
                        UPDATE connectors
                        SET enabled = 1, status = 'pending_approval', 
                            last_error = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE connector_id = ?
                    """, (error_msg, connector_id))
                    conn.commit()
                    
                    # Return success response with pending_approval status
                    return ConnectorStatusResponse(
                        connector_id=connector_id,
                        enabled=True,
                        status='pending_approval',
                        container_status='stopped',  # Container won't start until approved
                        is_connected=False,
                        last_connected=row['last_connected'],
                        last_error=error_msg,
                        error_count=row['error_count'],
                    )
                except PxGridPendingApprovalError as e:
                    # Account was created but is pending approval - this is expected, not an error
                    error_msg = str(e)
                    logger.info(f"pxGrid account is pending approval: {error_msg}")
                    
                    # ALWAYS update config with bootstrap password if ISE returned one (even if pending approval)
                    # This is the client password that ISE generated - we must store it for future use
                    if client.bootstrap_password:
                        logger.info(f"✅ Bootstrap password received from ISE (pending approval), storing in database config (length: {len(client.bootstrap_password)})")
                        config['password'] = client.bootstrap_password
                        config['username'] = client_name  # Use client_name as username for client credentials
                        config_json = json.dumps(config)
                        conn.execute("""
                            UPDATE connectors
                            SET config = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE connector_id = ?
                        """, (config_json, connector_id))
                        conn.commit()
                        logger.info(f"✅ Bootstrap password stored in database - this is now the client password for '{client_name}'")
                    else:
                        logger.warning(f"⚠️  No bootstrap password received from ISE - account may not have been created")
                    
                    # Mark as enabled with pending_approval status - this is a success state
                    conn.execute("""
                        UPDATE connectors
                        SET enabled = 1, status = 'pending_approval', 
                            last_error = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE connector_id = ?
                    """, (error_msg, connector_id))
                    conn.commit()
                    
                    # Return success response with pending_approval status
                    return ConnectorStatusResponse(
                        connector_id=connector_id,
                        enabled=True,
                        status='pending_approval',
                        container_status='stopped',  # Container won't start until approved
                        is_connected=False,
                        last_connected=row['last_connected'],
                        last_error=error_msg,
                        error_count=row['error_count'],
                    )
                except PxGridAuthenticationError as e:
                    error_msg = str(e)
                    logger.error(f"pxGrid authentication failed during enable: {error_msg}")
                    raise HTTPException(
                        status_code=401,
                        detail=f"Cannot enable connector: {error_msg}"
                    )
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"pxGrid connection error during enable: {error_msg}")
                    
                    # CRITICAL: ALWAYS save bootstrap password if it was received, regardless of exception type
                    # When using username/password auth, client ALWAYS goes into PENDING approval
                    # So we MUST save the bootstrap password whenever it's available
                    if hasattr(client, 'bootstrap_password') and client.bootstrap_password:
                        logger.info(f"✅ Bootstrap password found in client object during exception (length: {len(client.bootstrap_password)})")
                        logger.info(f"✅ Saving bootstrap password to database IMMEDIATELY (even though exception occurred)...")
                        try:
                            config['password'] = client.bootstrap_password
                            config['username'] = client_name
                            config_json = json.dumps(config)
                            conn.execute("""
                                UPDATE connectors
                                SET config = ?, updated_at = CURRENT_TIMESTAMP
                                WHERE connector_id = ?
                            """, (config_json, connector_id))
                            conn.commit()
                            logger.info(f"✅✅✅ Bootstrap password saved to database despite exception")
                            logger.info(f"   Database updated: username='{client_name}', password_length={len(client.bootstrap_password)}")
                        except Exception as save_error:
                            logger.error(f"❌ Failed to save bootstrap password to database: {save_error}")
                    
                    # Check if this is a pending approval error (fallback check)
                    if "PENDING" in error_msg.upper() or "pending approval" in error_msg.lower():
                        logger.info(f"Detected pending approval in error message (fallback): {error_msg}")
                        
                        # Mark as enabled with pending_approval status
                        conn.execute("""
                            UPDATE connectors
                            SET enabled = 1, status = 'pending_approval', 
                                last_error = ?,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE connector_id = ?
                        """, (error_msg, connector_id))
                        conn.commit()
                        
                        # Return success response with pending_approval status
                        return ConnectorStatusResponse(
                            connector_id=connector_id,
                            enabled=True,
                            status='pending_approval',
                            container_status='stopped',
                            is_connected=False,
                            last_connected=row['last_connected'],
                            last_error=error_msg,
                            error_count=row['error_count'],
                        )
                    
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot enable connector: Connection failed. Error: {error_msg}"
                    )
                
                # Now trigger the pxGrid service to start
                try:
                    import httpx
                    pxgrid_service_url = os.environ.get("PXGRID_SERVICE_URL", "http://pxgrid:9000")
                    async with httpx.AsyncClient(timeout=10.0) as http_client:
                        try:
                            response = await http_client.post(f"{pxgrid_service_url}/reload")
                            if response.status_code == 200:
                                logger.info("pxGrid service reloaded configuration and started")
                            elif response.status_code == 503:
                                logger.info("pxGrid service not ready, attempting to start...")
                                response = await http_client.post(f"{pxgrid_service_url}/start")
                                if response.status_code != 200:
                                    logger.warning(f"pxGrid service /start returned {response.status_code}: {response.text}")
                        except httpx.ConnectError:
                            logger.warning(f"Could not connect to pxGrid service at {pxgrid_service_url}. Container may not be running.")
                except ImportError:
                    logger.warning("httpx not available, cannot communicate with pxGrid service")
                except Exception as e:
                    logger.warning(f"Error communicating with pxGrid service: {e}")
            except HTTPException:
                raise
            except PxGridPendingApprovalError as e:
                # Catch PxGridPendingApprovalError at outer level if it wasn't caught in inner try block
                error_msg = str(e)
                logger.info(f"pxGrid account is pending approval (outer catch): {error_msg}")
                
                # Get row for response
                cursor = conn.execute("""
                    SELECT * FROM connectors WHERE connector_id = ?
                """, (connector_id,))
                row = cursor.fetchone()
                
                # CRITICAL: ALWAYS save bootstrap password if it was received
                # The client object should have bootstrap_password set if AccountCreate succeeded
                if 'client' in locals() and hasattr(client, 'bootstrap_password') and client.bootstrap_password:
                    logger.info(f"✅ Bootstrap password found in client object (outer catch) (length: {len(client.bootstrap_password)})")
                    logger.info(f"✅ Saving bootstrap password to database IMMEDIATELY...")
                    try:
                        if 'config' not in locals() or not config:
                            # Load config from database
                            cursor = conn.execute("""
                                SELECT config FROM connectors WHERE connector_id = ?
                            """, (connector_id,))
                            config_row = cursor.fetchone()
                            if config_row and config_row['config']:
                                config = json.loads(config_row['config'])
                            else:
                                config = {}
                        config['password'] = client.bootstrap_password
                        config['username'] = client_name
                        config_json = json.dumps(config)
                        conn.execute("""
                            UPDATE connectors
                            SET config = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE connector_id = ?
                        """, (config_json, connector_id))
                        conn.commit()
                        logger.info(f"✅✅✅ Bootstrap password saved to database (outer catch)")
                    except Exception as save_error:
                        logger.error(f"❌ Failed to save bootstrap password to database: {save_error}")
                
                # Mark as enabled with pending_approval status
                conn.execute("""
                    UPDATE connectors
                    SET enabled = 1, status = 'pending_approval', 
                        last_error = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE connector_id = ?
                """, (error_msg, connector_id))
                conn.commit()
                
                # Return success response with pending_approval status
                return ConnectorStatusResponse(
                    connector_id=connector_id,
                    enabled=True,
                    status='pending_approval',
                    container_status='stopped',
                    is_connected=False,
                    last_connected=row['last_connected'] if row else None,
                    last_error=error_msg,
                    error_count=row['error_count'] if row else 0,
                )
            except Exception as e:
                logger.error(f"Unexpected error enabling pxGrid connector: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Error enabling connector: {e}"
                )
        
        # Update connector status
        conn.execute("""
            UPDATE connectors
            SET enabled = 1, status = 'enabled', updated_at = CURRENT_TIMESTAMP
            WHERE connector_id = ?
        """, (connector_id,))
        conn.commit()
        
        return ConnectorStatusResponse(
            connector_id=connector_id,
            enabled=True,
            status='enabled',
            container_status='running',  # TODO: Get actual status
            is_connected=False,  # TODO: Check actual connection
            last_connected=row['last_connected'],
            last_error=row['last_error'],
            error_count=row['error_count'],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling connector {connector_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connectors/{connector_id}/disable", response_model=ConnectorStatusResponse)
async def disable_connector(connector_id: str):
    """
    Disable a connector (stop container if running).
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Get connector
        cursor = conn.execute("""
            SELECT * FROM connectors WHERE connector_id = ?
        """, (connector_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Connector {connector_id} not found"
            )
        
        # For pxGrid, delete client from ISE and clear database config
        if connector_id == 'ise_pxgrid':
            # Parse config to get connection details
            config = json.loads(row['config']) if row['config'] else {}
            ise_hostname = config.get('ise_hostname')
            client_name = config.get('client_name', 'clarion-pxgrid-client')
            username = config.get('username', client_name)
            password = config.get('password', '')
            port = config.get('port', 8910)
            use_ssl = config.get('use_ssl', True)
            verify_ssl = config.get('verify_ssl', False)
            auth_method = config.get('auth_method', 'username_password')
            
            # Stop the pxGrid subscriber service
            try:
                import httpx
                pxgrid_service_url = os.environ.get("PXGRID_SERVICE_URL", "http://pxgrid:9000")
                async with httpx.AsyncClient(timeout=10.0) as client:
                    try:
                        response = await client.post(f"{pxgrid_service_url}/stop")
                        if response.status_code == 200:
                            logger.info("pxGrid subscriber stopped")
                    except Exception as e:
                        logger.warning(f"Error stopping pxGrid service: {e}")
            except ImportError:
                logger.warning("httpx not available, cannot communicate with pxGrid service")
            except Exception as e:
                logger.warning(f"Error stopping pxGrid service: {e}")
            
            # Delete client from ISE if we have credentials
            # Try to use ISE admin credentials if available (username != client_name)
            # Otherwise, try with stored credentials (which might be client credentials)
            if ise_hostname and username and password:
                try:
                    from clarion.integration.pxgrid_client import PxGridClient, PxGridConfig
                    
                    # Load certificates if using certificate auth
                    client_cert_data = None
                    client_key_data = None
                    ca_cert_data = None
                    if auth_method == 'certificate':
                        client_cert_data, client_key_data, ca_cert_data = load_pxgrid_certificates(conn, 'ise_pxgrid')
                    
                    # Determine if we have admin credentials (username != client_name means admin credentials)
                    is_admin_creds = username != client_name
                    admin_username = username if is_admin_creds else None
                    admin_password = password if is_admin_creds else None
                    
                    # For deletion, we'll try with current credentials first, then with admin if available
                    # Create config with current credentials for the client object
                    pxgrid_config = PxGridConfig(
                        ise_hostname=ise_hostname,
                        username=username,
                        password=password,
                        client_name=client_name,
                        port=port,
                        use_ssl=use_ssl,
                        verify_ssl=verify_ssl,
                        client_cert_data=client_cert_data,
                        client_key_data=client_key_data,
                        ca_cert_data=ca_cert_data,
                    )
                    
                    client = PxGridClient(pxgrid_config)
                    try:
                        # Try to delete - delete_account will try client credentials first, then admin if provided
                        # No need to connect first - delete_account makes its own HTTP request
                        deleted = client.delete_account(admin_username=admin_username, admin_password=admin_password)
                        if deleted:
                            logger.info(f"✅ pxGrid client '{client_name}' deleted from ISE")
                        else:
                            logger.warning(f"⚠️  Could not delete pxGrid client from ISE via API. You may need to delete it manually in ISE GUI.")
                    except Exception as e:
                        logger.warning(f"⚠️  Error deleting pxGrid client from ISE: {e}")
                        logger.warning(f"⚠️  Client may need to be deleted manually in ISE GUI: Administration > pxGrid Services > Client Management > Clients")
                except Exception as e:
                    logger.warning(f"⚠️  Error deleting pxGrid client from ISE: {e}")
                    logger.warning(f"⚠️  Client may need to be deleted manually in ISE GUI: Administration > pxGrid Services > Client Management > Clients")
            
            # Delete the connector from database entirely for a fresh start
            # This ensures no stale configuration remains when re-enabling
            logger.info(f"Deleting pxGrid connector from database for fresh start...")
            conn.execute("""
                DELETE FROM connectors
                WHERE connector_id = ?
            """, (connector_id,))
            conn.commit()
            logger.info(f"✅ pxGrid connector deleted from database")
            
            # Return response indicating connector was deleted
            return ConnectorStatusResponse(
                connector_id=connector_id,
                enabled=False,
                status='disabled',
                container_status='stopped',
                is_connected=False,
                last_connected=None,
                last_error=None,
                error_count=0,
            )
        else:
            # For other connectors, just disable
            conn.execute("""
                UPDATE connectors
                SET enabled = 0, status = 'disabled', updated_at = CURRENT_TIMESTAMP
                WHERE connector_id = ?
            """, (connector_id,))
            conn.commit()
            
            return ConnectorStatusResponse(
                connector_id=connector_id,
                enabled=False,
                status='disabled',
                container_status='stopped',
                is_connected=False,
                last_connected=row['last_connected'],
                last_error=row['last_error'],
                error_count=row['error_count'],
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling connector {connector_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connectors/{connector_id}/status", response_model=ConnectorStatusResponse)
async def get_connector_status(connector_id: str):
    """
    Get connector status (connection, container, errors).
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        cursor = conn.execute("""
            SELECT * FROM connectors WHERE connector_id = ?
        """, (connector_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Connector {connector_id} not found"
            )
        
        # TODO: Get actual container status from Docker API
        # TODO: Get actual connection status from connector service
        
        return ConnectorStatusResponse(
            connector_id=connector_id,
            enabled=bool(row['enabled']),
            status=row['status'],
            container_status='running' if row['enabled'] else 'stopped',
            is_connected=row['status'] == 'connected',
            last_connected=row['last_connected'],
            last_error=row['last_error'],
            error_count=row['error_count'],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting connector status {connector_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connectors/{connector_id}/test-connection")
async def test_connector_connection(connector_id: str):
    """
    Test connection for a connector using its saved configuration.
    
    For ISE ERS API: Tests connection and authentication
    For ISE pxGrid: Tests pxGrid connection and authentication
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Get connector configuration from database
        cursor = conn.execute("""
            SELECT * FROM connectors WHERE connector_id = ?
        """, (connector_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Connector {connector_id} not found. Please save configuration first."
            )
        
        if not row['config']:
            raise HTTPException(
                status_code=400,
                detail=f"Connector {connector_id} has no saved configuration. Please configure the connector first."
            )
        
        config = json.loads(row['config'])
        
        if connector_id == 'ise_ers':
            # Test ISE ERS API connection
            from clarion.integration.ise_client import ISEClient
            
            try:
                ise_url = config.get('ise_url')
                ise_username = config.get('ise_username')
                ise_password = config.get('ise_password')
                verify_ssl = config.get('verify_ssl', False)
                
                if not ise_url or not ise_username or not ise_password:
                    raise HTTPException(
                        status_code=400,
                        detail="Missing required ISE configuration: ise_url, ise_username, and ise_password are required"
                    )
                
                # Log what we're testing
                logger.info(f"Testing ISE ERS API connection to {ise_url} with username {ise_username}")
                
                try:
                    # ISEClient.__init__ will authenticate immediately
                    # If authentication fails, it will raise ISEAuthenticationError
                    from clarion.integration.ise_client import ISEAuthenticationError
                    client = ISEClient(
                        base_url=ise_url,
                        username=ise_username,
                        password=ise_password,
                        verify_ssl=verify_ssl,
                    )
                    
                    # If we get here, authentication succeeded (ISEClient.__init__ calls _authenticate)
                    # Now test the connection explicitly
                    is_connected = client.test_connection()
                    logger.info(f"ISE ERS API connection test result: {is_connected}")
                    
                    # Update last_connected timestamp
                    if is_connected:
                        conn.execute("""
                            UPDATE connectors
                            SET last_connected = CURRENT_TIMESTAMP,
                                status = 'connected',
                                last_error = NULL,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE connector_id = ?
                        """, (connector_id,))
                        conn.commit()
                        
                        return {
                            "status": "success",
                            "connected": True,
                            "message": f"Successfully connected to ISE at {ise_url}",
                            "ise_url": ise_url,
                        }
                    else:
                        error_msg = "Connection test failed"
                        conn.execute("""
                            UPDATE connectors
                            SET status = 'error',
                                last_error = ?,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE connector_id = ?
                        """, (error_msg, connector_id))
                        conn.commit()
                        
                        return {
                            "status": "failed",
                            "connected": False,
                            "message": "Connection test failed",
                            "ise_url": ise_url,
                        }
                        
                except ISEAuthenticationError as auth_error:
                    # Handle ISE authentication errors specifically
                    error_msg = str(auth_error)
                    logger.error(f"ISE ERS API authentication failed for {ise_url} with username {ise_username}: {error_msg}")
                    friendly_msg = f"Authentication failed: Please check your ISE username and password. Error details: {error_msg}"
                    
                    conn.execute("""
                        UPDATE connectors
                        SET status = 'error',
                            last_error = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE connector_id = ?
                    """, (error_msg[:500], connector_id))
                    conn.commit()
                    
                    return {
                        "status": "failed",
                        "connected": False,
                        "message": friendly_msg,
                        "ise_url": ise_url,
                        "error": error_msg,
                    }
                except Exception as connect_error:
                    # Handle connection errors (timeout, network, etc.)
                    error_msg = str(connect_error)
                    logger.error(f"ISE ERS API connection error for {ise_url}: {error_msg}")
                    # Provide more user-friendly error messages
                    if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                        friendly_msg = f"Connection timeout: Cannot reach {ise_url}. Please check network connectivity and firewall rules."
                    elif "authentication" in error_msg.lower() or "401" in error_msg or "403" in error_msg:
                        friendly_msg = f"Authentication failed: Please check your ISE username and password. Error: {error_msg}"
                    else:
                        friendly_msg = f"Connection failed: {error_msg}"
                    
                    conn.execute("""
                        UPDATE connectors
                        SET status = 'error',
                            last_error = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE connector_id = ?
                    """, (error_msg[:500], connector_id))  # Limit error message length
                    conn.commit()
                    
                    # Return error response instead of raising exception
                    return {
                        "status": "failed",
                        "connected": False,
                        "message": friendly_msg,
                        "ise_url": ise_url,
                        "error": error_msg,
                    }
                
            except Exception as e:
                error_msg = str(e)
                conn.execute("""
                    UPDATE connectors
                    SET status = 'error',
                        last_error = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE connector_id = ?
                """, (error_msg[:500], connector_id))
                conn.commit()
                
                return {
                    "status": "failed",
                    "connected": False,
                    "message": f"Connection test failed: {error_msg}",
                    "ise_url": ise_url,
                    "error": error_msg,
                }
        
        elif connector_id == 'ise_pxgrid':
            # Test pxGrid connection
            from clarion.integration.pxgrid_client import PxGridClient, PxGridConfig, PxGridAuthenticationError, PxGridPendingApprovalError
            
            try:
                ise_hostname = config.get('ise_hostname')
                client_name = config.get('client_name', 'clarion-pxgrid-client')
                port = config.get('port', 8910)
                use_ssl = config.get('use_ssl', True)
                verify_ssl = config.get('verify_ssl', False)
                auth_method = config.get('auth_method', 'username_password')  # Default to username/password for backward compatibility
                
                # For test connection, always use stored client credentials from database
                # When client is created, ISE returns a bootstrap password which becomes the client password
                # The config stores: username = client_name, password = bootstrap_password (client password)
                stored_username = config.get('username', '')
                stored_password = config.get('password', '')
                
                # For test connection, ALWAYS try to use client credentials first
                # If stored_username == client_name, we have client credentials stored - use them
                # If stored_username != client_name, we have ISE admin credentials - but client may exist, so try client credentials
                if not stored_password:
                    raise HTTPException(
                        status_code=400,
                        detail=f"No password stored in database for pxGrid connector. Please save configuration with credentials first."
                    )
                
                # Always use client_name as username for test connection (client credentials)
                # The password should be the client password if the client exists
                username = client_name
                password = stored_password
                
                if stored_username == client_name:
                    # We have client credentials stored - use them
                    logger.info(f"🔍 TEST CONNECTION - Using stored CLIENT credentials from database:")
                    logger.info(f"   - Username: {username} (matches client_name)")
                    logger.info(f"   - Client Name: {client_name}")
                    logger.info(f"   - Password length: {len(password)}")
                    logger.info(f"   - ✅ Using client credentials for existing client")
                else:
                    # We have ISE admin credentials stored, but trying client credentials
                    # This will work if the stored password is actually the client password
                    # If it fails, the error will indicate we need the client password
                    logger.info(f"🔍 TEST CONNECTION - Attempting with client credentials:")
                    logger.info(f"   - Username: {username} (client_name, overriding stored username '{stored_username}')")
                    logger.info(f"   - Client Name: {client_name}")
                    logger.info(f"   - Password length: {len(password)}")
                    logger.info(f"   - ⚠️  Stored username was '{stored_username}' (ISE admin), but using client_name as username")
                    logger.info(f"   - ⚠️  If this fails, the stored password may be ISE admin password, not client password")
                
                # Check if certificates are assigned (for certificate auth)
                # Use certificate_connector_references (new global certificates system)
                has_client_cert = False
                try:
                    cert_cursor = conn.execute("""
                        SELECT certificate_id FROM certificate_connector_references 
                        WHERE connector_id = ? AND reference_type = 'client_cert'
                    """, ('ise_pxgrid',))
                    has_client_cert = cert_cursor.fetchone() is not None
                except Exception as e:
                    # Table might not exist yet - check old connector_certificates table for backward compatibility
                    try:
                        cert_cursor = conn.execute("""
                            SELECT id FROM connector_certificates 
                            WHERE connector_id = ? AND cert_type = 'client_cert'
                        """, ('ise_pxgrid',))
                        has_client_cert = cert_cursor.fetchone() is not None
                    except Exception:
                        # Neither table exists or has certificates - default to False
                        has_client_cert = False
                
                # Determine actual auth method: if certificates are assigned, use certificate auth
                # Otherwise use the configured auth_method (defaults to username_password)
                actual_auth_method = 'certificate' if has_client_cert else auth_method
                
                if not ise_hostname:
                    raise HTTPException(
                        status_code=400,
                        detail="Missing required pxGrid configuration: ise_hostname is required"
                    )
                
                if actual_auth_method == 'username_password' and (not username or not password):
                    raise HTTPException(
                        status_code=400,
                        detail="Missing required pxGrid configuration for username/password authentication: username and password are required"
                    )
                elif actual_auth_method == 'certificate' and not has_client_cert:
                    raise HTTPException(
                        status_code=400,
                        detail="Missing required pxGrid configuration for certificate authentication: client certificate must be assigned. Please assign a certificate in the Certificates section."
                    )
                
                # Load certificate data if using certificate authentication
                client_cert_data = None
                client_key_data = None
                ca_cert_data = None
                if actual_auth_method == 'certificate':
                    client_cert_data, client_key_data, ca_cert_data = load_pxgrid_certificates(conn, 'ise_pxgrid')
                    if not client_cert_data or not client_key_data:
                        raise HTTPException(
                            status_code=400,
                            detail="Certificate authentication selected but client certificate or private key not found in database. Please assign certificates in the Certificates section."
                        )
                
                pxgrid_config = PxGridConfig(
                    ise_hostname=ise_hostname,
                    username=username,
                    password=password,
                    client_name=client_name,
                    port=port,
                    use_ssl=use_ssl,
                    verify_ssl=verify_ssl,
                    client_cert_data=client_cert_data,
                    client_key_data=client_key_data,
                    ca_cert_data=ca_cert_data,
                )
                
                client = PxGridClient(pxgrid_config)
                try:
                    # For test connection, only test AccountActivate (don't do full connect)
                    logger.info(f"Testing pxGrid AccountActivate for client '{client_name}'...")
                    test_result = client.test_account_activate()
                    
                    if test_result['success']:
                        account_state = test_result.get('account_state', 'UNKNOWN')
                        version = test_result.get('version', 'unknown')
                        message = test_result.get('message', 'AccountActivate successful')
                        
                        # Update status based on account state
                        if account_state == 'ENABLED':
                            status = 'connected'
                            conn.execute("""
                                UPDATE connectors
                                SET last_connected = CURRENT_TIMESTAMP,
                                    status = ?,
                                    last_error = NULL,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE connector_id = ?
                            """, (status, connector_id))
                            conn.commit()
                            
                            return {
                                "status": "success",
                                "connected": True,
                                "message": message,
                                "ise_hostname": ise_hostname,
                                "port": port,
                                "account_state": account_state,
                                "version": version,
                            }
                        elif account_state == 'PENDING':
                            status = 'pending_approval'
                            conn.execute("""
                                UPDATE connectors
                                SET status = ?,
                                    last_error = NULL,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE connector_id = ?
                            """, (status, connector_id))
                            conn.commit()
                            
                            return {
                                "status": "pending_approval",
                                "connected": False,
                                "message": f"Account is pending approval in ISE. Please approve it in ISE GUI: Administration > pxGrid Services > Client Management > Clients",
                                "ise_hostname": ise_hostname,
                                "port": port,
                                "account_state": account_state,
                                "version": version,
                            }
                        else:
                            status = 'error'
                            error_msg = f"Account state: {account_state}"
                            conn.execute("""
                                UPDATE connectors
                                SET status = ?,
                                    last_error = ?,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE connector_id = ?
                            """, (status, error_msg, connector_id))
                            conn.commit()
                            
                            return {
                                "status": "failed",
                                "connected": False,
                                "message": message,
                                "ise_hostname": ise_hostname,
                                "port": port,
                                "account_state": account_state,
                                "error": message,
                            }
                    else:
                        # AccountActivate failed
                        error_msg = test_result.get('message', 'AccountActivate failed')
                        conn.execute("""
                            UPDATE connectors
                            SET status = 'error',
                                last_error = ?,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE connector_id = ?
                        """, (error_msg[:500], connector_id))
                        conn.commit()
                        
                        return {
                            "status": "failed",
                            "connected": False,
                            "message": error_msg,
                            "ise_hostname": ise_hostname,
                            "port": port,
                            "error": error_msg,
                        }
                    
                except PxGridPendingApprovalError as e:
                    # Account is pending approval
                    status = 'pending_approval'
                    error_msg = str(e)
                    conn.execute("""
                        UPDATE connectors
                        SET status = ?,
                            last_error = NULL,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE connector_id = ?
                    """, (status, connector_id))
                    conn.commit()
                    
                    return {
                        "status": "pending_approval",
                        "connected": False,
                        "message": f"Account is pending approval in ISE. Please approve it in ISE GUI: Administration > pxGrid Services > Client Management > Clients",
                        "ise_hostname": ise_hostname,
                        "port": port,
                    }
                except PxGridAuthenticationError as e:
                    # Authentication failed
                    error_msg = str(e)
                    # Remove "already exists" messages - they're not helpful for test connection
                    if "already exists" in error_msg.lower():
                        error_msg = "Authentication failed. Please check your credentials."
                    
                    conn.execute("""
                        UPDATE connectors
                        SET status = 'error',
                            last_error = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE connector_id = ?
                    """, (error_msg[:500], connector_id))
                    conn.commit()
                    
                    return {
                        "status": "failed",
                        "connected": False,
                        "message": error_msg,
                        "ise_hostname": ise_hostname,
                        "port": port,
                        "error": error_msg,
                    }
                except Exception as e:
                    # Other errors
                    error_msg = str(e)
                    conn.execute("""
                        UPDATE connectors
                        SET status = 'error',
                            last_error = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE connector_id = ?
                    """, (error_msg[:500], connector_id))
                    conn.commit()
                    
                    return {
                        "status": "failed",
                        "connected": False,
                        "message": f"Connection test failed: {error_msg}",
                        "ise_hostname": ise_hostname,
                        "port": port,
                            "error": error_msg,
                        }
                except PxGridPendingApprovalError as pending_error:
                    # Account is pending approval - this is expected, not an error
                    error_msg = str(pending_error)
                    logger.info(f"pxGrid account is pending approval: {error_msg}")
                    
                    # Update config with bootstrap password if account was created
                    if client.bootstrap_password and client.bootstrap_password != password:
                        logger.info(f"Bootstrap password received (pending approval), storing in database config")
                        config['password'] = client.bootstrap_password
                        config['username'] = client_name
                        config_json = json.dumps(config)
                        conn.execute("""
                            UPDATE connectors
                            SET config = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE connector_id = ?
                        """, (config_json, connector_id))
                        conn.commit()
                    
                    conn.execute("""
                        UPDATE connectors
                        SET status = 'pending_approval',
                            last_error = ?,
                            updated_at = CURRENT_TIMESTAMP
                    WHERE connector_id = ?
                    """, (error_msg, connector_id))
                    conn.commit()
                    
                    return {
                        "status": "pending_approval",
                        "connected": False,
                        "message": error_msg,
                        "ise_hostname": ise_hostname,
                        "port": port,
                        "error": "Account pending approval",
                    }
                except PxGridAuthenticationError as auth_error:
                    # ALWAYS store bootstrap password if ISE returned one (even if connection failed)
                    # This is the client password that ISE generated - we must store it for future use
                    if client.bootstrap_password:
                        logger.info(f"✅ Bootstrap password received from ISE (before error), storing in database config (length: {len(client.bootstrap_password)})")
                        config['password'] = client.bootstrap_password
                        config['username'] = client_name  # Use client_name as username for client credentials
                        config_json = json.dumps(config)
                        conn.execute("""
                            UPDATE connectors
                            SET config = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE connector_id = ?
                        """, (config_json, connector_id))
                        conn.commit()
                        logger.info(f"✅ Bootstrap password stored in database - this is now the client password for '{client_name}'")
                    # Handle pxGrid authentication errors specifically
                    error_msg = str(auth_error)
                    logger.error(f"pxGrid authentication failed for {ise_hostname}:{port}: {error_msg}")
                    logger.error(f"   - Credentials used: username={username}, client_name={client_name}, password_length={len(password) if password else 0}")
                    logger.error(f"   - Username matches client_name: {username == client_name}")
                    logger.error(f"   - Stored username in config: {stored_username}")
                    
                    # Check if this is a PENDING approval issue - try to check account state
                    # If authentication fails, the account might be PENDING
                    try:
                        # Try AccountActivate to check account state
                        import requests
                        from requests.auth import HTTPBasicAuth
                        check_url = f"https://{ise_hostname}:{port}/pxgrid/control/AccountActivate"
                        check_payload = {"nodeName": client_name}
                        check_auth = HTTPBasicAuth(client_name, password) if password else None
                        check_response = requests.post(
                            check_url,
                            json=check_payload,
                            auth=check_auth,
                            timeout=10,
                            verify=verify_ssl
                        )
                        if check_response.status_code == 200:
                            check_result = check_response.json()
                            account_state = check_result.get("accountState")
                            if account_state == "PENDING":
                                conn.execute("""
                                    UPDATE connectors
                                    SET status = 'pending_approval',
                                        last_error = ?,
                                        updated_at = CURRENT_TIMESTAMP
                                    WHERE connector_id = ?
                                """, ("Account is PENDING approval in ISE. Please approve it.", connector_id))
                                conn.commit()
                                
                                return {
                                    "status": "pending_approval",
                                    "connected": False,
                                    "message": f"pxGrid client '{client_name}' is PENDING approval in ISE. Please approve it: Administration > pxGrid Services > Client Management > Clients. Then click 'Test Connection' again to verify.",
                                    "ise_hostname": ise_hostname,
                                    "port": port,
                                    "error": "Account pending approval",
                                }
                    except Exception as check_error:
                        # If we can't check account state, just return the original error
                        logger.debug(f"Could not check account state: {check_error}")
                        pass
                    
                    conn.execute("""
                        UPDATE connectors
                        SET status = 'error',
                            last_error = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE connector_id = ?
                    """, (error_msg[:500], connector_id))
                    conn.commit()
                    
                    return {
                        "status": "failed",
                        "connected": False,
                        "message": f"pxGrid connection failed: {error_msg}",
                        "ise_hostname": ise_hostname,
                        "port": port,
                        "error": error_msg,
                    }
                except Exception as connect_error:
                    # Handle connection errors (timeout, network, auth, etc.)
                    error_msg = str(connect_error)
                    logger.error(f"pxGrid connection error for {ise_hostname}:{port}: {error_msg}")
                    conn.execute("""
                        UPDATE connectors
                        SET status = 'error',
                            last_error = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE connector_id = ?
                    """, (error_msg[:500], connector_id))  # Limit error message length
                    conn.commit()

                    # Return error response instead of raising exception
                    return {
                        "status": "failed",
                        "connected": False,
                        "message": f"Connection test failed: {error_msg}",
                        "ise_hostname": ise_hostname,
                        "port": port,
                        "error": error_msg,
                    }
                
            except Exception as e:
                error_msg = str(e)
                conn.execute("""
                    UPDATE connectors
                    SET status = 'error',
                        last_error = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE connector_id = ?
                """, (error_msg[:500], connector_id))
                conn.commit()
                
                return {
                    "status": "failed",
                    "connected": False,
                    "message": f"Connection test failed: {error_msg}",
                    "ise_hostname": ise_hostname,
                    "port": port,
                    "error": error_msg,
                }
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Test connection not supported for connector type: {connector_id}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing connector connection {connector_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ========== Certificate Management Endpoints ==========

@router.post("/connectors/{connector_id}/certificates")
async def upload_certificate(
    connector_id: str,
    cert_type: str = Form(..., description="Certificate type: client_cert, client_key, or ca_cert"),
    cert_file: UploadFile = File(..., description="Certificate file"),
):
    """
    Upload a certificate for a connector.
    
    Supported certificate types:
    - client_cert: Client certificate
    - client_key: Client private key
    - ca_cert: CA certificate
    """
    if cert_type not in ['client_cert', 'client_key', 'ca_cert']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid certificate type: {cert_type}. Must be one of: client_cert, client_key, ca_cert"
        )
    
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Verify connector exists
        cursor = conn.execute("""
            SELECT connector_id FROM connectors WHERE connector_id = ?
        """, (connector_id,))
        if not cursor.fetchone():
            # Create connector if it doesn't exist (for certificate upload before configuration)
            connector_definitions = {
                'ise_ers': {'name': 'ISE ERS API', 'type': 'ise_ers', 'description': 'Cisco ISE ERS API connector'},
                'ise_pxgrid': {'name': 'ISE pxGrid', 'type': 'ise_pxgrid', 'description': 'Cisco ISE pxGrid connector'},
                'ad': {'name': 'Active Directory', 'type': 'ad', 'description': 'LDAP connector'},
            }
            
            if connector_id not in connector_definitions:
                raise HTTPException(status_code=404, detail=f"Unknown connector: {connector_id}")
            
            definition = connector_definitions[connector_id]
            conn.execute("""
                INSERT INTO connectors (
                    connector_id, name, type, enabled, status, description,
                    created_at, updated_at
                ) VALUES (?, ?, ?, 0, 'disabled', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (connector_id, definition['name'], definition['type'], definition['description']))
            conn.commit()
        
        # Read certificate file
        cert_data = await cert_file.read()
        
        # Delete existing certificate of this type (allow only one per type)
        conn.execute("""
            DELETE FROM connector_certificates
            WHERE connector_id = ? AND cert_type = ?
        """, (connector_id, cert_type))
        
        # Insert new certificate
        conn.execute("""
            INSERT INTO connector_certificates (
                connector_id, cert_type, cert_data, cert_filename, created_at
            ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (connector_id, cert_type, cert_data, cert_file.filename))
        conn.commit()
        
        return {
            "status": "success",
            "message": f"Certificate {cert_type} uploaded successfully",
            "connector_id": connector_id,
            "cert_type": cert_type,
            "filename": cert_file.filename,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading certificate for connector {connector_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connectors/{connector_id}/certificates")
async def list_certificates(connector_id: str):
    """
    List certificates for a connector.
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        cursor = conn.execute("""
            SELECT cert_type, cert_filename, created_at
            FROM connector_certificates
            WHERE connector_id = ?
            ORDER BY cert_type
        """, (connector_id,))
        
        certificates = []
        for row in cursor.fetchall():
            certificates.append({
                "cert_type": row['cert_type'],
                "filename": row['cert_filename'],
                "created_at": row['created_at'],
            })
        
        return {
            "connector_id": connector_id,
            "certificates": certificates,
        }
        
    except Exception as e:
        logger.error(f"Error listing certificates for connector {connector_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/connectors/{connector_id}/certificates/{cert_type}")
async def delete_certificate(connector_id: str, cert_type: str):
    """
    Delete a certificate for a connector.
    """
    if cert_type not in ['client_cert', 'client_key', 'ca_cert']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid certificate type: {cert_type}"
        )
    
    db = get_database()
    conn = db._get_connection()
    
    try:
        cursor = conn.execute("""
            DELETE FROM connector_certificates
            WHERE connector_id = ? AND cert_type = ?
        """, (connector_id, cert_type))
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Certificate {cert_type} not found for connector {connector_id}"
            )
        
        return {
            "status": "success",
            "message": f"Certificate {cert_type} deleted successfully",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting certificate for connector {connector_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

