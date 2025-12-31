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
    ise_url: Optional[str] = Field(None, description="ISE server URL (e.g., https://192.168.10.31). Port is optional (defaults to 443). If not provided, uses saved connector configuration.")
    ise_username: Optional[str] = Field(None, description="ISE admin username. If not provided, uses saved connector configuration.")
    ise_password: Optional[str] = Field(None, description="ISE admin password. If not provided, uses saved connector configuration.")
    verify_ssl: Optional[bool] = Field(None, description="Verify SSL certificates. If not provided, uses saved connector configuration.")
    use_saved_config: bool = Field(True, description="Use saved connector configuration if credentials are not provided")


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
    import json
    
    try:
        # If credentials not provided, try to use saved connector configuration
        if request.use_saved_config and (not request.ise_url or not request.ise_username or not request.ise_password):
            db = get_database()
            conn = db._get_connection()
            cursor = conn.execute("""
                SELECT config FROM connectors WHERE connector_id = 'ise_ers'
            """)
            row = cursor.fetchone()
            
            if row and row['config']:
                saved_config = json.loads(row['config'])
                ise_url = request.ise_url or saved_config.get('ise_url')
                ise_username = request.ise_username or saved_config.get('ise_username')
                ise_password = request.ise_password or saved_config.get('ise_password')
                verify_ssl = request.verify_ssl if request.verify_ssl is not None else saved_config.get('verify_ssl', False)
                
                if not ise_url or not ise_username or not ise_password:
                    raise HTTPException(
                        status_code=400,
                        detail="Missing ISE configuration. Please provide credentials or configure the ISE ERS API connector first."
                    )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Missing ISE configuration. Please provide credentials or configure the ISE ERS API connector first."
                )
        else:
            ise_url = request.ise_url
            ise_username = request.ise_username
            ise_password = request.ise_password
            verify_ssl = request.verify_ssl if request.verify_ssl is not None else False
            
            if not ise_url or not ise_username or not ise_password:
                raise HTTPException(
                    status_code=400,
                    detail="Missing required ISE configuration: ise_url, ise_username, and ise_password are required"
                )
        
        # Log the sync operation start with ISE prefix for troubleshooting
        logger.info(f"ISE Sync: Starting configuration sync from ISE server {ise_url} (username: {ise_username}, verify_ssl: {verify_ssl})")
        
        # Initialize ISE client
        ise_client = ISEClient(
            base_url=ise_url,
            username=ise_username,
            password=ise_password,
            verify_ssl=verify_ssl,
        )
        
        db = get_database()
        ise_server = ise_url  # Use URL as server identifier
        
        # Extract and store SGTs
        logger.info(f"ISE Sync: Extracting SGTs from ISE server {ise_server}")
        sgts = ise_client.get_all_sgts()
        sgts_count = db.store_ise_sgts(ise_server, sgts)
        
        # Log SGT details
        sgt_names = [sgt.get('name', 'Unknown') for sgt in sgts[:10]]  # Log first 10 names
        logger.info(f"ISE Sync: Synced {sgts_count} SGTs from {ise_server}. Sample SGTs: {', '.join(sgt_names)}")
        if sgts_count > 10:
            logger.info(f"ISE Sync: ... and {sgts_count - 10} more SGTs")
        
        # Extract and store authorization profiles
        logger.info(f"ISE Sync: Extracting authorization profiles from ISE server {ise_server}")
        profiles = ise_client.get_all_authorization_profiles()
        profiles_count = db.store_ise_auth_profiles(ise_server, profiles)
        
        # Log profile details
        profile_names = [prof.get('name', 'Unknown') for prof in profiles[:10]]  # Log first 10 names
        logger.info(f"ISE Sync: Synced {profiles_count} authorization profiles from {ise_server}. Sample profiles: {', '.join(profile_names)}")
        if profiles_count > 10:
            logger.info(f"ISE Sync: ... and {profiles_count - 10} more authorization profiles")
        
        # Extract and store authorization policies (may fail on some ISE versions/configurations)
        policies_count = 0
        try:
            logger.info(f"ISE Sync: Extracting authorization policies from ISE server {ise_server}")
            policies = ise_client.get_all_authorization_policies()
            policies_count = db.store_ise_auth_policies(ise_server, policies)
            
            # Log policy details
            policy_names = [pol.get('name', 'Unknown') for pol in policies[:10]]  # Log first 10 names
            logger.info(f"ISE Sync: Synced {policies_count} authorization policies from {ise_server}. Sample policies: {', '.join(policy_names)}")
            if policies_count > 10:
                logger.info(f"ISE Sync: ... and {policies_count - 10} more authorization policies")
        except Exception as e:
            # Authorization policies endpoint may not be available or return 404 on some ISE versions
            if "404" in str(e):
                logger.warning(f"ISE Sync: Authorization policies endpoint not available or returned 404 (this is OK): {e}")
            else:
                logger.warning(f"ISE Sync: Failed to sync authorization policies (continuing anyway): {e}")
            # Continue with sync even if policies fail
        
        # Log successful sync completion with summary
        logger.info(
            f"ISE Sync: Successfully completed sync from {ise_server}. "
            f"Summary - SGTs: {sgts_count}, Authorization Profiles: {profiles_count}, "
            f"Authorization Policies: {policies_count}"
        )
        
        return ISESyncResponse(
            status="success",
            message=f"Successfully synced ISE configuration from {ise_server}",
            ise_server=ise_server,
            sgts_synced=sgts_count,
            profiles_synced=profiles_count,
            policies_synced=policies_count,
        )
        
    except ISEAuthenticationError as e:
        logger.error(f"ISE Sync: Authentication failed for {ise_url}: {e}")
        raise HTTPException(status_code=401, detail=f"ISE authentication failed: {e}")
    except ISEAPIError as e:
        logger.error(f"ISE Sync: API error during sync from {ise_url}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"ISE API error: {e}")
    except Exception as e:
        logger.error(f"ISE Sync: Unexpected error syncing configuration from {ise_url}: {e}", exc_info=True)
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

