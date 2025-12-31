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
from datetime import datetime

from clarion.storage import get_database

logger = logging.getLogger(__name__)

router = APIRouter()


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
                
                # Get certificate status
                cert_cursor = conn.execute("""
                    SELECT cert_type FROM connector_certificates WHERE connector_id = ?
                """, (connector_id,))
                cert_types = {row['cert_type'] for row in cert_cursor.fetchall()}
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
            
            # Get certificate status
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
            # Get certificate status (might have certificates even if not configured)
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
            # TODO: Check for required certificates (for pxGrid)
            # TODO: Start container via Docker API (for pxGrid)
            pass
        
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
        
        # TODO: Stop container via Docker API (for pxGrid)
        
        # Update connector status
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
            from clarion.integration.pxgrid_client import PxGridClient, PxGridConfig
            
            try:
                ise_hostname = config.get('ise_hostname')
                username = config.get('username')
                password = config.get('password')
                client_name = config.get('client_name', 'clarion-pxgrid-client')
                port = config.get('port', 8910)
                use_ssl = config.get('use_ssl', True)
                verify_ssl = config.get('verify_ssl', False)
                
                if not ise_hostname or not username or not password:
                    raise HTTPException(
                        status_code=400,
                        detail="Missing required pxGrid configuration: ise_hostname, username, and password are required"
                    )
                
                pxgrid_config = PxGridConfig(
                    ise_hostname=ise_hostname,
                    username=username,
                    password=password,
                    client_name=client_name,
                    port=port,
                    use_ssl=use_ssl,
                    verify_ssl=verify_ssl,
                )
                
                client = PxGridClient(pxgrid_config)
                try:
                    is_connected = client.connect()
                    
                    if is_connected:
                        client.disconnect()
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
                            "message": f"Successfully connected to pxGrid at {ise_hostname}:{port}",
                            "ise_hostname": ise_hostname,
                            "port": port,
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
                            "ise_hostname": ise_hostname,
                            "port": port,
                        }
                except Exception as connect_error:
                    # Handle connection errors (timeout, network, auth, etc.)
                    error_msg = str(connect_error)
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

