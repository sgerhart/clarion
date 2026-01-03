"""
Vault Health and Status API Routes

Provides endpoints for checking Vault connectivity and health.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

from clarion.secrets.helpers import get_vault_client

logger = logging.getLogger(__name__)

router = APIRouter()


class VaultHealthResponse(BaseModel):
    """Vault health response."""
    healthy: bool
    initialized: Optional[bool] = None
    sealed: Optional[bool] = None
    standby: Optional[bool] = None
    version: Optional[str] = None
    error: Optional[str] = None


@router.get("/vault/health", response_model=VaultHealthResponse)
async def get_vault_health():
    """
    Check Vault health and connectivity.
    
    Returns:
        Vault health status
    """
    try:
        vault = get_vault_client()
        if not vault:
            return VaultHealthResponse(
                healthy=False,
                error="Vault not configured (missing VAULT_ADDR or credentials)"
            )
        
        health = vault.health_check()
        return VaultHealthResponse(**health)
    except Exception as e:
        logger.error(f"Vault health check failed: {e}")
        return VaultHealthResponse(
            healthy=False,
            error=str(e)
        )


@router.get("/vault/status")
async def get_vault_status():
    """
    Get detailed Vault status information.
    
    Returns:
        Detailed Vault status
    """
    try:
        vault = get_vault_client()
        if not vault:
            return {
                "configured": False,
                "error": "Vault not configured"
            }
        
        health = vault.health_check()
        
        # Try to list some secrets to verify access
        try:
            connectors = vault.list_secrets("connectors")
            certificates = vault.list_secrets("certificates")
            api_keys = vault.list_secrets("api_keys")
        except Exception as e:
            logger.warning(f"Failed to list secrets: {e}")
            connectors = []
            certificates = []
            api_keys = []
        
        return {
            "configured": True,
            "healthy": health.get("healthy", False),
            "initialized": health.get("initialized", False),
            "sealed": health.get("sealed", False),
            "standby": health.get("standby", False),
            "version": health.get("version"),
            "secrets": {
                "connectors": len(connectors),
                "certificates": len(certificates),
                "api_keys": len(api_keys)
            }
        }
    except Exception as e:
        logger.error(f"Vault status check failed: {e}")
        return {
            "configured": False,
            "error": str(e)
        }

