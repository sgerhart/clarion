"""
Secret Rotation API Routes

Provides endpoints for managing secret rotation.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from clarion.secrets import VaultClient
from clarion.secrets.rotation import SecretRotationManager, RotationStatus

logger = logging.getLogger(__name__)

router = APIRouter()


class RotatePasswordRequest(BaseModel):
    """Request to rotate a password."""
    connector_id: str
    new_password: Optional[str] = None
    rotation_interval_days: int = 90


class RotateCertificateRequest(BaseModel):
    """Request to rotate a certificate."""
    certificate_id: str
    new_cert_data: str  # Base64 encoded
    new_key_data: Optional[str] = None  # Base64 encoded
    new_ca_cert_data: Optional[str] = None  # Base64 encoded
    rotation_interval_days: int = 365


@router.get("/rotation/secrets")
async def list_secrets_needing_rotation():
    """
    List all secrets that need rotation (expired or nearing expiration).
    
    Returns:
        List of secrets needing rotation
    """
    try:
        vault = VaultClient()
        rotation_manager = SecretRotationManager(vault)
        
        secrets = rotation_manager.list_secrets_needing_rotation()
        return {
            "count": len(secrets),
            "secrets": secrets
        }
    except Exception as e:
        logger.error(f"Error listing secrets needing rotation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rotation/secrets/{secret_path:path}/status")
async def get_secret_rotation_status(secret_path: str):
    """
    Get rotation status for a secret.
    
    Args:
        secret_path: Path to secret (e.g., 'connectors/ise_pxgrid')
        
    Returns:
        Rotation status and expiration info
    """
    try:
        vault = VaultClient()
        rotation_manager = SecretRotationManager(vault)
        
        metadata = rotation_manager.get_secret_metadata(secret_path)
        expiration_info = rotation_manager.check_secret_expiration(secret_path)
        
        return {
            "secret_path": secret_path,
            "metadata": metadata,
            "expiration_info": expiration_info,
        }
    except Exception as e:
        logger.error(f"Error getting rotation status for {secret_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rotation/password")
async def rotate_password(request: RotatePasswordRequest):
    """
    Rotate password for a connector.
    
    Args:
        request: Rotation request with connector_id and new_password
        
    Returns:
        Rotation result
    """
    try:
        vault = VaultClient()
        rotation_manager = SecretRotationManager(vault)
        
        success = rotation_manager.rotate_connector_password(
            connector_id=request.connector_id,
            new_password=request.new_password,
            rotation_interval_days=request.rotation_interval_days
        )
        
        if success:
            return {
                "status": "success",
                "message": f"Password rotated for {request.connector_id}",
                "connector_id": request.connector_id,
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to rotate password for {request.connector_id}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rotating password: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rotation/certificate")
async def rotate_certificate(request: RotateCertificateRequest):
    """
    Rotate certificate.
    
    Args:
        request: Rotation request with certificate data
        
    Returns:
        Rotation result
    """
    try:
        import base64
        
        vault = VaultClient()
        rotation_manager = SecretRotationManager(vault)
        
        # Decode base64 certificate data
        cert_data = base64.b64decode(request.new_cert_data)
        key_data = base64.b64decode(request.new_key_data) if request.new_key_data else None
        ca_cert_data = base64.b64decode(request.new_ca_cert_data) if request.new_ca_cert_data else None
        
        success = rotation_manager.rotate_certificate(
            certificate_id=request.certificate_id,
            new_cert_data=cert_data,
            new_key_data=key_data,
            new_ca_cert_data=ca_cert_data,
            rotation_interval_days=request.rotation_interval_days
        )
        
        if success:
            return {
                "status": "success",
                "message": f"Certificate rotated for {request.certificate_id}",
                "certificate_id": request.certificate_id,
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to rotate certificate {request.certificate_id}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rotating certificate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rotation/secrets/{secret_path:path}/history")
async def get_rotation_history(secret_path: str):
    """
    Get rotation history for a secret.
    
    Args:
        secret_path: Path to secret
        
    Returns:
        Rotation history
    """
    try:
        vault = VaultClient()
        rotation_manager = SecretRotationManager(vault)
        
        history = rotation_manager.get_rotation_history(secret_path)
        
        return {
            "secret_path": secret_path,
            "history": history,
        }
    except Exception as e:
        logger.error(f"Error getting rotation history for {secret_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

