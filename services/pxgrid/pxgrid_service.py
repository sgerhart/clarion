"""
pxGrid Service Entry Point

Standalone service for pxGrid integration that can run in a container.
This service runs the pxGrid subscriber and provides a simple HTTP API
for status and control.
"""

import os
import sys
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
from clarion.storage import init_database

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


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    logger.info(f"\n🛑 Received signal {sig}, shutting down...")
    if subscriber:
        subscriber.stop()
    sys.exit(0)


def initialize_subscriber():
    """Initialize the pxGrid subscriber from environment variables."""
    global subscriber
    
    # Get configuration from environment
    ise_hostname = os.environ.get("PXGRID_ISE_HOSTNAME")
    username = os.environ.get("PXGRID_USERNAME")
    password = os.environ.get("PXGRID_PASSWORD")
    client_name = os.environ.get("PXGRID_CLIENT_NAME", "clarion-pxgrid-client")
    use_ssl = os.environ.get("PXGRID_USE_SSL", "true").lower() == "true"
    verify_ssl = os.environ.get("PXGRID_VERIFY_SSL", "false").lower() == "true"
    port = int(os.environ.get("PXGRID_PORT", "8910"))
    
    # Certificate paths (for certificate-based auth)
    cert_dir = os.environ.get("PXGRID_CERT_DIR", "/app/certs")
    
    if not ise_hostname:
        logger.warning("PXGRID_ISE_HOSTNAME not set, pxGrid subscriber will not start")
        return None
    
    # Initialize database
    db_path = os.environ.get("CLARION_DB_PATH", "/app/data/clarion.db")
    init_database(db_path)
    logger.info(f"Database initialized: {db_path}")
    
    # Create configuration
    # Note: For certificate auth, we'll need to update PxGridConfig
    # to support certificate files instead of username/password
    config = PxGridConfig(
        ise_hostname=ise_hostname,
        username=username or "",  # May be empty for cert auth
        password=password or "",  # May be empty for cert auth
        client_name=client_name,
        use_ssl=use_ssl,
        verify_ssl=verify_ssl,
        port=port,
    )
    
    # Create subscriber
    subscriber = PxGridSubscriber(config)
    logger.info(f"pxGrid subscriber initialized for {ise_hostname}")
    
    # Auto-start if credentials are provided
    if username and password:
        logger.info("Starting pxGrid subscriber automatically...")
        try:
            subscriber.start()
        except Exception as e:
            logger.error(f"Failed to start pxGrid subscriber: {e}")
            logger.info("Subscriber will remain stopped. Use /start endpoint to retry.")
    
    return subscriber


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

