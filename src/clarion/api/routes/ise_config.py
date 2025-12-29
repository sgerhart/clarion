"""
ISE Configuration API Routes

Endpoints for syncing and viewing existing ISE TrustSec configuration
for brownfield deployment support.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging

from clarion.integration.ise_client import ISEClient, ISEAuthenticationError, ISEAPIError
from clarion.storage import get_database

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== Request/Response Models ==========

class ISESyncRequest(BaseModel):
    """Request to sync ISE configuration."""
    ise_url: str = Field(..., description="ISE server URL (e.g., https://192.168.10.31:9060)")
    ise_username: str = Field(..., description="ISE admin username")
    ise_password: str = Field(..., description="ISE admin password")
    verify_ssl: bool = Field(False, description="Verify SSL certificates")


class ISESyncResponse(BaseModel):
    """Response from ISE sync operation."""
    status: str
    message: str
    ise_server: str
    sgts_synced: int
    profiles_synced: int
    policies_synced: int


class ISESyncStatusResponse(BaseModel):
    """ISE sync status response."""
    ise_server: str
    sgts: Dict[str, Any]
    auth_profiles: Dict[str, Any]
    auth_policies: Dict[str, Any]


# ========== ISE Configuration Endpoints ==========

@router.post("/ise/config/sync", response_model=ISESyncResponse)
async def sync_ise_configuration(request: ISESyncRequest):
    """
    Sync existing ISE TrustSec configuration from ISE server.
    
    This extracts all existing SGTs, authorization profiles, and authorization policies
    from ISE and stores them in the cache for brownfield deployment support.
    
    Use this endpoint to:
    - Discover existing SGTs before generating recommendations
    - Avoid creating duplicate SGTs
    - Recommend using existing SGTs when appropriate
    """
    try:
        # Initialize ISE client
        ise_client = ISEClient(
            base_url=request.ise_url,
            username=request.ise_username,
            password=request.ise_password,
            verify_ssl=request.verify_ssl,
        )
        
        db = get_database()
        ise_server = request.ise_url  # Use URL as server identifier
        
        # Extract and store SGTs
        logger.info(f"Syncing SGTs from ISE server {ise_server}")
        sgts = ise_client.get_all_sgts()
        sgts_count = db.store_ise_sgts(ise_server, sgts)
        
        # Extract and store authorization profiles
        logger.info(f"Syncing authorization profiles from ISE server {ise_server}")
        profiles = ise_client.get_all_authorization_profiles()
        profiles_count = db.store_ise_auth_profiles(ise_server, profiles)
        
        # Extract and store authorization policies
        logger.info(f"Syncing authorization policies from ISE server {ise_server}")
        policies = ise_client.get_all_authorization_policies()
        policies_count = db.store_ise_auth_policies(ise_server, policies)
        
        return ISESyncResponse(
            status="success",
            message=f"Successfully synced ISE configuration from {ise_server}",
            ise_server=ise_server,
            sgts_synced=sgts_count,
            profiles_synced=profiles_count,
            policies_synced=policies_count,
        )
        
    except ISEAuthenticationError as e:
        logger.error(f"ISE authentication failed: {e}")
        raise HTTPException(status_code=401, detail=f"ISE authentication failed: {e}")
    except ISEAPIError as e:
        logger.error(f"ISE API error during sync: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"ISE API error: {e}")
    except Exception as e:
        logger.error(f"Error syncing ISE configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ise/config/status", response_model=ISESyncStatusResponse)
async def get_ise_sync_status(
    ise_server: str = Query(..., description="ISE server URL to check status for")
):
    """
    Get sync status for an ISE server.
    
    Returns the last sync time and count of cached resources.
    """
    try:
        db = get_database()
        status = db.get_ise_sync_status(ise_server)
        
        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"No sync data found for ISE server: {ise_server}"
            )
        
        return ISESyncStatusResponse(**status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ISE sync status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ise/config/sgts")
async def get_ise_sgts(
    ise_server: Optional[str] = Query(None, description="Filter by ISE server")
):
    """
    Get cached ISE SGTs.
    
    Returns all cached SGTs, optionally filtered by ISE server.
    """
    try:
        db = get_database()
        sgts = db.get_ise_sgts(ise_server=ise_server)
        return {"sgts": sgts, "count": len(sgts)}
        
    except Exception as e:
        logger.error(f"Error getting ISE SGTs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ise/config/auth-profiles")
async def get_ise_auth_profiles(
    ise_server: Optional[str] = Query(None, description="Filter by ISE server"),
    sgt_value: Optional[int] = Query(None, description="Filter by SGT value")
):
    """
    Get cached ISE authorization profiles.
    
    Returns all cached authorization profiles, optionally filtered by ISE server or SGT value.
    """
    try:
        db = get_database()
        profiles = db.get_ise_auth_profiles(ise_server=ise_server, sgt_value=sgt_value)
        return {"profiles": profiles, "count": len(profiles)}
        
    except Exception as e:
        logger.error(f"Error getting ISE authorization profiles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ise/config/auth-policies")
async def get_ise_auth_policies(
    ise_server: Optional[str] = Query(None, description="Filter by ISE server"),
    profile_name: Optional[str] = Query(None, description="Filter by profile name")
):
    """
    Get cached ISE authorization policies.
    
    Returns all cached authorization policies, optionally filtered by ISE server or profile name.
    """
    try:
        db = get_database()
        policies = db.get_ise_auth_policies(ise_server=ise_server, profile_name=profile_name)
        return {"policies": policies, "count": len(policies)}
        
    except Exception as e:
        logger.error(f"Error getting ISE authorization policies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

