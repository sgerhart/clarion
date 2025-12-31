"""
pxGrid API Routes

Endpoints for configuring and managing pxGrid subscriptions to ISE.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging

from clarion.integration.pxgrid_client import (
    PxGridClient,
    PxGridConfig,
    PxGridError,
    PxGridAuthenticationError,
)
from clarion.integration.pxgrid_subscriber import PxGridSubscriber

logger = logging.getLogger(__name__)

router = APIRouter()

# Global pxGrid subscriber instance (singleton pattern)
_pxgrid_subscriber: Optional[PxGridSubscriber] = None


# ========== Request/Response Models ==========

class PxGridConfigRequest(BaseModel):
    """Request to configure pxGrid connection."""
    ise_hostname: str = Field(..., description="ISE hostname or IP (e.g., 192.168.10.31)")
    username: str = Field(..., description="pxGrid client username")
    password: str = Field(..., description="pxGrid client password")
    client_name: str = Field(..., description="Unique pxGrid client name (e.g., clarion-pxgrid-client)")
    use_ssl: bool = Field(True, description="Use SSL/TLS for connection")
    verify_ssl: bool = Field(False, description="Verify SSL certificates")
    port: int = Field(8910, description="pxGrid REST API port (default 8910)")


class PxGridConfigResponse(BaseModel):
    """Response from pxGrid configuration."""
    status: str
    message: str
    ise_hostname: str
    client_name: str
    connected: bool


class PxGridStatusResponse(BaseModel):
    """pxGrid subscriber status response."""
    is_running: bool
    is_connected: bool
    ise_hostname: Optional[str]
    client_name: Optional[str]
    subscribed_topics: list[str]
    error: Optional[str] = None


class PxGridTestConnectionRequest(BaseModel):
    """Request to test pxGrid connection."""
    ise_hostname: str = Field(..., description="ISE hostname or IP")
    username: str = Field(..., description="pxGrid client username")
    password: str = Field(..., description="pxGrid client password")
    client_name: str = Field(..., description="Unique pxGrid client name")
    use_ssl: bool = Field(True, description="Use SSL/TLS")
    verify_ssl: bool = Field(False, description="Verify SSL certificates")
    port: int = Field(8910, description="pxGrid REST API port")


class PxGridTestConnectionResponse(BaseModel):
    """Response from pxGrid connection test."""
    success: bool
    message: str
    ise_hostname: str


# ========== pxGrid Configuration Endpoints ==========

@router.post("/pxgrid/test-connection", response_model=PxGridTestConnectionResponse)
async def test_pxgrid_connection(request: PxGridTestConnectionRequest):
    """
    Test pxGrid connection to ISE without starting the subscriber.
    
    This endpoint allows you to verify:
    - pxGrid service is enabled on ISE
    - Credentials are correct
    - Network connectivity is working
    - Client name is available
    """
    try:
        config = PxGridConfig(
            ise_hostname=request.ise_hostname,
            username=request.username,
            password=request.password,
            client_name=request.client_name,
            use_ssl=request.use_ssl,
            verify_ssl=request.verify_ssl,
            port=request.port,
        )
        
        client = PxGridClient(config)
        success = client.connect()
        
        if success:
            client.disconnect()
            return PxGridTestConnectionResponse(
                success=True,
                message=f"Successfully connected to pxGrid at {request.ise_hostname}",
                ise_hostname=request.ise_hostname,
            )
        else:
            return PxGridTestConnectionResponse(
                success=False,
                message="Connection failed",
                ise_hostname=request.ise_hostname,
            )
            
    except PxGridAuthenticationError as e:
        logger.error(f"pxGrid authentication failed: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"pxGrid authentication failed: {e}. Please check your credentials and ensure pxGrid service is enabled on ISE."
        )
    except PxGridError as e:
        logger.error(f"pxGrid connection error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"pxGrid connection error: {e}"
        )
    except Exception as e:
        logger.error(f"Unexpected error testing pxGrid connection: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {e}"
        )


@router.post("/pxgrid/configure", response_model=PxGridConfigResponse)
async def configure_pxgrid(request: PxGridConfigRequest):
    """
    Configure and start the pxGrid subscriber.
    
    This will:
    1. Create a pxGrid client with the provided configuration
    2. Connect to ISE pxGrid service
    3. Start the subscriber service to receive real-time events
    4. Subscribe to session and endpoint topics
    
    Note: Only one pxGrid subscriber can run at a time. If one is already running,
    it will be stopped before starting the new one.
    """
    global _pxgrid_subscriber
    
    try:
        # Stop existing subscriber if running
        if _pxgrid_subscriber and _pxgrid_subscriber.is_running:
            logger.info("Stopping existing pxGrid subscriber...")
            _pxgrid_subscriber.stop()
        
        # Create new configuration
        config = PxGridConfig(
            ise_hostname=request.ise_hostname,
            username=request.username,
            password=request.password,
            client_name=request.client_name,
            use_ssl=request.use_ssl,
            verify_ssl=request.verify_ssl,
            port=request.port,
        )
        
        # Create and start subscriber
        _pxgrid_subscriber = PxGridSubscriber(config)
        success = _pxgrid_subscriber.start()
        
        if success:
            return PxGridConfigResponse(
                status="success",
                message=f"pxGrid subscriber started successfully for {request.ise_hostname}",
                ise_hostname=request.ise_hostname,
                client_name=request.client_name,
                connected=True,
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to start pxGrid subscriber"
            )
            
    except PxGridAuthenticationError as e:
        logger.error(f"pxGrid authentication failed: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"pxGrid authentication failed: {e}. Please check your credentials and ensure pxGrid service is enabled on ISE. You may also need to approve the client in ISE: Administration > pxGrid Services > Client Management > Clients"
        )
    except PxGridError as e:
        logger.error(f"pxGrid error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"pxGrid error: {e}"
        )
    except Exception as e:
        logger.error(f"Unexpected error configuring pxGrid: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {e}"
        )


@router.get("/pxgrid/status", response_model=PxGridStatusResponse)
async def get_pxgrid_status():
    """
    Get the current status of the pxGrid subscriber.
    
    Returns information about:
    - Whether the subscriber is running
    - Connection status
    - Subscribed topics
    - Any errors
    """
    global _pxgrid_subscriber
    
    if not _pxgrid_subscriber:
        return PxGridStatusResponse(
            is_running=False,
            is_connected=False,
            ise_hostname=None,
            client_name=None,
            subscribed_topics=[],
            error=None,
        )
    
    return PxGridStatusResponse(
        is_running=_pxgrid_subscriber.is_running,
        is_connected=_pxgrid_subscriber.client.is_connected if _pxgrid_subscriber.client else False,
        ise_hostname=_pxgrid_subscriber.config.ise_hostname,
        client_name=_pxgrid_subscriber.config.client_name,
        subscribed_topics=_pxgrid_subscriber.client.subscribed_topics if _pxgrid_subscriber.client else [],
        error=None,
    )


@router.post("/pxgrid/stop")
async def stop_pxgrid():
    """
    Stop the pxGrid subscriber.
    
    This will disconnect from ISE and stop receiving events.
    """
    global _pxgrid_subscriber
    
    if not _pxgrid_subscriber:
        raise HTTPException(
            status_code=404,
            detail="pxGrid subscriber is not configured"
        )
    
    if not _pxgrid_subscriber.is_running:
        raise HTTPException(
            status_code=400,
            detail="pxGrid subscriber is not running"
        )
    
    try:
        _pxgrid_subscriber.stop()
        return {
            "status": "success",
            "message": "pxGrid subscriber stopped successfully"
        }
    except Exception as e:
        logger.error(f"Error stopping pxGrid subscriber: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error stopping pxGrid subscriber: {e}"
        )

