"""
pxGrid Service Entry Point

Standalone service for pxGrid integration that can run in a container.
This service runs the pxGrid subscriber and provides a simple HTTP API
for status and control.
"""

import os
import sys
import json
import logging
import signal
import threading
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

from clarion.integration.pxgrid_client import PxGridConfig
from clarion.integration.pxgrid_subscriber import PxGridSubscriber
from clarion.storage import init_database, get_database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global subscriber instance
subscriber: PxGridSubscriber = None

# FastAPI app for status/control API
app = FastAPI(title="Clarion pxGrid Service", version="1.0.0")


@app.get("/health")
async def health():
    """Health check endpoint."""
    if subscriber and subscriber.is_running:
        return {"status": "healthy", "pxgrid_connected": subscriber.client.is_connected}
    return {"status": "starting", "pxgrid_connected": False}


@app.get("/status")
async def status():
    """Get pxGrid subscriber status."""
    if not subscriber:
        return JSONResponse(
            status_code=503,
            content={"status": "not_initialized", "message": "pxGrid subscriber not initialized"}
        )
    
    return {
        "is_running": subscriber.is_running,
        "is_connected": subscriber.client.is_connected if subscriber.client else False,
        "ise_hostname": subscriber.config.ise_hostname,
        "client_name": subscriber.config.client_name,
        "subscribed_topics": subscriber.client.subscribed_topics if subscriber.client else [],
    }


@app.post("/start")
async def start_service():
    """Start the pxGrid subscriber (if not already running)."""
    global subscriber
    
    if subscriber and subscriber.is_running:
        return {"status": "already_running", "message": "pxGrid subscriber is already running"}
    
    if not subscriber:
        return JSONResponse(
            status_code=503,
            content={"status": "not_initialized", "message": "pxGrid subscriber not initialized"}
        )
    
    try:
        success = subscriber.start()
        if success:
            return {"status": "started", "message": "pxGrid subscriber started successfully"}
        else:
            return JSONResponse(
                status_code=500,
                content={"status": "failed", "message": "Failed to start pxGrid subscriber"}
            )
    except Exception as e:
        logger.error(f"Error starting pxGrid subscriber: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


@app.post("/stop")
async def stop_service():
    """Stop the pxGrid subscriber."""
    global subscriber
    
    if not subscriber or not subscriber.is_running:
        return {"status": "not_running", "message": "pxGrid subscriber is not running"}
    
    try:
        subscriber.stop()
        return {"status": "stopped", "message": "pxGrid subscriber stopped successfully"}
    except Exception as e:
        logger.error(f"Error stopping pxGrid subscriber: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


@app.post("/reload")
async def reload_config():
    """Reload configuration from database and restart subscriber."""
    global subscriber
    
    try:
        # Stop existing subscriber if running
        if subscriber and subscriber.is_running:
            logger.info("Stopping existing pxGrid subscriber for reload...")
            subscriber.stop()
        
        # Reinitialize from database
        new_subscriber = initialize_subscriber_from_db()
        if new_subscriber:
            subscriber = new_subscriber
            # Auto-start if enabled and has credentials
            db = get_database()
            conn = db._get_connection()
            cursor = conn.execute("""
                SELECT enabled, config FROM connectors WHERE connector_id = 'ise_pxgrid'
            """)
            row = cursor.fetchone()
            
            if row and row['enabled']:
                config = json.loads(row['config']) if row['config'] else {}
                if config.get('username') and config.get('password'):
                    logger.info("Auto-starting pxGrid subscriber after reload...")
                    subscriber.start()
            
            return {"status": "reloaded", "message": "Configuration reloaded from database"}
        else:
            return JSONResponse(
                status_code=404,
                content={"status": "not_found", "message": "pxGrid connector not configured in database"}
            )
    except Exception as e:
        logger.error(f"Error reloading configuration: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    logger.info(f"\n🛑 Received signal {sig}, shutting down...")
    if subscriber:
        subscriber.stop()
    sys.exit(0)


def initialize_subscriber_from_db():
    """Initialize the pxGrid subscriber from database connector configuration."""
    # Initialize database
    db_path = os.environ.get("CLARION_DB_PATH", "/app/data/clarion.db")
    init_database(db_path)
    logger.info(f"Database initialized: {db_path}")
    
    # Get database instance
    db = get_database()
    conn = db._get_connection()
    
    # Read connector configuration from database
    cursor = conn.execute("""
        SELECT config FROM connectors WHERE connector_id = 'ise_pxgrid'
    """)
    row = cursor.fetchone()
    
    if not row or not row['config']:
        logger.warning("pxGrid connector not configured in database. Using environment variables as fallback.")
        return initialize_subscriber_from_env()
    
    try:
        config_json = json.loads(row['config'])
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in connector configuration: {e}")
        return initialize_subscriber_from_env()
    
    # Extract configuration
    ise_hostname = config_json.get('ise_hostname')
    username = config_json.get('username', '')
    password = config_json.get('password', '')
    client_name = config_json.get('client_name', 'clarion-pxgrid-client')
    use_ssl = config_json.get('use_ssl', True)
    verify_ssl = config_json.get('verify_ssl', False)
    port = int(config_json.get('port', 8910))
    
    if not ise_hostname:
        logger.warning("ise_hostname not found in connector configuration")
        return None
    
    logger.info(f"Loading pxGrid configuration from database: {ise_hostname}, client: {client_name}")
    
    # Load certificates from database (from global certificates table via connector references)
    client_cert_data = None
    client_key_data = None
    ca_cert_data = None
    
    try:
        cert_cursor = conn.execute("""
            SELECT 
                c.cert_type, c.cert_data, r.reference_type
            FROM certificates c
            INNER JOIN certificate_connector_references r ON c.id = r.certificate_id
            WHERE r.connector_id = 'ise_pxgrid'
            AND r.reference_type IN ('client_cert', 'client_key', 'ca_cert')
        """)
        
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
        
        # Determine authentication method (certificates take priority if available)
        if client_cert_data and client_key_data:
            logger.info("Certificate-based authentication will be used (mutual TLS)")
            # Certificates take priority - username/password optional for cert-based auth
        elif username and password:
            logger.info("Password-based authentication will be used (username/password)")
        else:
            logger.warning("Neither certificates nor credentials found. Authentication may fail.")
            logger.warning("Please configure either:")
            logger.warning("  1. Client certificate + private key (certificate-based auth), OR")
            logger.warning("  2. Username + password (password-based auth)")
    except Exception as e:
        logger.warning(f"Error loading certificates from database: {e}. Will continue without certificates.")
    
    # Create configuration
    config = PxGridConfig(
        ise_hostname=ise_hostname,
        username=username,
        password=password,
        client_name=client_name,
        use_ssl=use_ssl,
        verify_ssl=verify_ssl,
        port=port,
        client_cert_data=client_cert_data,
        client_key_data=client_key_data,
        ca_cert_data=ca_cert_data,
    )
    
    # Create subscriber
    subscriber_instance = PxGridSubscriber(config)
    logger.info(f"pxGrid subscriber initialized for {ise_hostname}")
    
    return subscriber_instance


def initialize_subscriber_from_env():
    """Initialize the pxGrid subscriber from environment variables (fallback)."""
    # Get configuration from environment
    ise_hostname = os.environ.get("PXGRID_ISE_HOSTNAME")
    username = os.environ.get("PXGRID_USERNAME", "")
    password = os.environ.get("PXGRID_PASSWORD", "")
    client_name = os.environ.get("PXGRID_CLIENT_NAME", "clarion-pxgrid-client")
    use_ssl = os.environ.get("PXGRID_USE_SSL", "true").lower() == "true"
    verify_ssl = os.environ.get("PXGRID_VERIFY_SSL", "false").lower() == "true"
    port = int(os.environ.get("PXGRID_PORT", "8910"))
    
    if not ise_hostname:
        logger.warning("PXGRID_ISE_HOSTNAME not set, pxGrid subscriber will not start")
        return None
    
    # Create configuration
    config = PxGridConfig(
        ise_hostname=ise_hostname,
        username=username,
        password=password,
        client_name=client_name,
        use_ssl=use_ssl,
        verify_ssl=verify_ssl,
        port=port,
    )
    
    # Create subscriber
    subscriber_instance = PxGridSubscriber(config)
    logger.info(f"pxGrid subscriber initialized from environment for {ise_hostname}")
    
    return subscriber_instance


def initialize_subscriber():
    """Initialize the pxGrid subscriber (tries database first, then environment)."""
    # Try to load from database first
    subscriber_instance = initialize_subscriber_from_db()
    
    if subscriber_instance:
        return subscriber_instance
    
    # Fall back to environment variables
    return initialize_subscriber_from_env()


def main():
    """Main entry point."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize subscriber
    initialize_subscriber()
    
    # Start HTTP API server
    port = int(os.environ.get("PORT", "9000"))
    logger.info(f"Starting pxGrid service HTTP API on port {port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()

