"""
Secret Rotation Framework

Provides automated secret rotation capabilities for Vault-stored secrets.
Supports password rotation, certificate rotation, and secret versioning.
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum

from clarion.secrets import VaultClient, VaultConfig

logger = logging.getLogger(__name__)


class RotationStatus(Enum):
    """Secret rotation status."""
    ACTIVE = "active"
    PENDING = "pending"
    EXPIRED = "expired"
    ROTATING = "rotating"
    FAILED = "failed"


class SecretRotationManager:
    """
    Manages secret rotation for various secret types.
    
    Supports:
    - Password rotation (ISE, AD credentials)
    - Certificate rotation (pxGrid certificates, TLS certificates)
    - Secret versioning and rollback
    - Expiration tracking and renewal
    """
    
    def __init__(self, vault_client: Optional[VaultClient] = None):
        """
        Initialize rotation manager.
        
        Args:
            vault_client: Vault client instance. If None, creates new client.
        """
        self.vault = vault_client or VaultClient()
        self.rotation_metadata_path = "secret/data/rotation/metadata"
    
    def get_secret_metadata(self, secret_path: str) -> Optional[Dict[str, Any]]:
        """
        Get rotation metadata for a secret.
        
        Args:
            secret_path: Path to secret in Vault
            
        Returns:
            Metadata dictionary or None if not found
        """
        try:
            metadata = self.vault.read_secret(self.rotation_metadata_path)
            if metadata and secret_path in metadata:
                return metadata[secret_path]
        except Exception as e:
            logger.debug(f"Could not retrieve metadata for {secret_path}: {e}")
        return None
    
    def set_secret_metadata(
        self,
        secret_path: str,
        expires_at: Optional[datetime] = None,
        rotation_interval_days: int = 90,
        last_rotated: Optional[datetime] = None,
        status: RotationStatus = RotationStatus.ACTIVE
    ) -> bool:
        """
        Set rotation metadata for a secret.
        
        Args:
            secret_path: Path to secret in Vault
            expires_at: When the secret expires
            rotation_interval_days: Days between rotations
            last_rotated: When secret was last rotated
            status: Current rotation status
            
        Returns:
            True if successful
        """
        try:
            # Get existing metadata
            metadata = self.vault.read_secret(self.rotation_metadata_path) or {}
            
            # Update metadata for this secret
            metadata[secret_path] = {
                "expires_at": expires_at.isoformat() if expires_at else None,
                "rotation_interval_days": rotation_interval_days,
                "last_rotated": last_rotated.isoformat() if last_rotated else None,
                "status": status.value,
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            # Save metadata
            return self.vault.write_secret(self.rotation_metadata_path, metadata)
        except Exception as e:
            logger.error(f"Failed to set metadata for {secret_path}: {e}")
            return False
    
    def check_secret_expiration(self, secret_path: str) -> Optional[Dict[str, Any]]:
        """
        Check if a secret is expired or nearing expiration.
        
        Args:
            secret_path: Path to secret in Vault
            
        Returns:
            Dictionary with expiration info or None if not found
        """
        metadata = self.get_secret_metadata(secret_path)
        if not metadata:
            return None
        
        expires_at_str = metadata.get("expires_at")
        if not expires_at_str:
            return None
        
        expires_at = datetime.fromisoformat(expires_at_str)
        now = datetime.utcnow()
        
        days_until_expiry = (expires_at - now).days
        
        return {
            "expires_at": expires_at,
            "days_until_expiry": days_until_expiry,
            "is_expired": days_until_expiry < 0,
            "is_nearing_expiry": days_until_expiry <= 30,  # Warn 30 days before
            "status": metadata.get("status", RotationStatus.ACTIVE.value),
        }
    
    def rotate_connector_password(
        self,
        connector_id: str,
        new_password: Optional[str] = None,
        rotation_interval_days: int = 90
    ) -> bool:
        """
        Rotate password for a connector.
        
        Args:
            connector_id: Connector identifier (e.g., 'ise_pxgrid')
            new_password: New password (if None, generates one - future enhancement)
            rotation_interval_days: Days until next rotation
            
        Returns:
            True if successful
        """
        secret_path = f"connectors/{connector_id}"
        
        try:
            # Get current credentials
            current_creds = self.vault.get_connector_credentials(connector_id)
            if not current_creds:
                logger.error(f"No credentials found for {connector_id}")
                return False
            
            # For now, require new_password to be provided
            # Future: Generate secure password automatically
            if not new_password:
                logger.error("Password rotation requires new_password (auto-generation not yet implemented)")
                return False
            
            # Update metadata to mark as rotating
            self.set_secret_metadata(
                secret_path,
                status=RotationStatus.ROTATING,
                last_rotated=datetime.utcnow()
            )
            
            # Store new password
            updated_creds = current_creds.copy()
            updated_creds["password"] = new_password
            updated_creds["rotated_at"] = datetime.utcnow().isoformat()
            
            success = self.vault.store_connector_credentials(connector_id, **updated_creds)
            
            if success:
                # Update metadata with expiration
                expires_at = datetime.utcnow() + timedelta(days=rotation_interval_days)
                self.set_secret_metadata(
                    secret_path,
                    expires_at=expires_at,
                    rotation_interval_days=rotation_interval_days,
                    last_rotated=datetime.utcnow(),
                    status=RotationStatus.ACTIVE
                )
                logger.info(f"Successfully rotated password for {connector_id}")
            else:
                self.set_secret_metadata(secret_path, status=RotationStatus.FAILED)
                logger.error(f"Failed to rotate password for {connector_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error rotating password for {connector_id}: {e}")
            self.set_secret_metadata(secret_path, status=RotationStatus.FAILED)
            return False
    
    def rotate_certificate(
        self,
        certificate_id: str,
        new_cert_data: bytes,
        new_key_data: Optional[bytes] = None,
        new_ca_cert_data: Optional[bytes] = None,
        rotation_interval_days: int = 365
    ) -> bool:
        """
        Rotate certificate.
        
        Args:
            certificate_id: Certificate identifier
            new_cert_data: New certificate data
            new_key_data: New private key data (optional)
            new_ca_cert_data: New CA certificate data (optional)
            rotation_interval_days: Days until next rotation
            
        Returns:
            True if successful
        """
        secret_path = f"certificates/{certificate_id}"
        
        try:
            # Update metadata to mark as rotating
            self.set_secret_metadata(
                secret_path,
                status=RotationStatus.ROTATING,
                last_rotated=datetime.utcnow()
            )
            
            # Store new certificate
            success = self.vault.store_certificate(
                certificate_id=certificate_id,
                cert_data=new_cert_data,
                key_data=new_key_data,
                ca_cert_data=new_ca_cert_data,
                cert_type="client"
            )
            
            if success:
                # Update metadata with expiration
                expires_at = datetime.utcnow() + timedelta(days=rotation_interval_days)
                self.set_secret_metadata(
                    secret_path,
                    expires_at=expires_at,
                    rotation_interval_days=rotation_interval_days,
                    last_rotated=datetime.utcnow(),
                    status=RotationStatus.ACTIVE
                )
                logger.info(f"Successfully rotated certificate {certificate_id}")
            else:
                self.set_secret_metadata(secret_path, status=RotationStatus.FAILED)
                logger.error(f"Failed to rotate certificate {certificate_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error rotating certificate {certificate_id}: {e}")
            self.set_secret_metadata(secret_path, status=RotationStatus.FAILED)
            return False
    
    def list_secrets_needing_rotation(self) -> List[Dict[str, Any]]:
        """
        List all secrets that need rotation (expired or nearing expiration).
        
        Returns:
            List of secrets needing rotation with metadata
        """
        try:
            metadata = self.vault.read_secret(self.rotation_metadata_path) or {}
            secrets_needing_rotation = []
            
            for secret_path, secret_metadata in metadata.items():
                expiration_info = self.check_secret_expiration(secret_path)
                if expiration_info and (expiration_info["is_expired"] or expiration_info["is_nearing_expiry"]):
                    secrets_needing_rotation.append({
                        "secret_path": secret_path,
                        "expiration_info": expiration_info,
                        "metadata": secret_metadata,
                    })
            
            return secrets_needing_rotation
            
        except Exception as e:
            logger.error(f"Error listing secrets needing rotation: {e}")
            return []
    
    def get_rotation_history(self, secret_path: str) -> List[Dict[str, Any]]:
        """
        Get rotation history for a secret (using Vault versioning).
        
        Args:
            secret_path: Path to secret in Vault
            
        Returns:
            List of rotation history entries
        """
        # Note: This would require Vault's versioning API
        # For now, return metadata-based history
        metadata = self.get_secret_metadata(secret_path)
        if not metadata:
            return []
        
        history = []
        if metadata.get("last_rotated"):
            history.append({
                "rotated_at": metadata["last_rotated"],
                "status": metadata.get("status"),
            })
        
        return history
    
    def rollback_secret(self, secret_path: str, version: Optional[int] = None) -> bool:
        """
        Rollback secret to previous version.
        
        Args:
            secret_path: Path to secret in Vault
            version: Version number to rollback to (if None, rollback to previous)
            
        Returns:
            True if successful
        """
        # Note: This would require Vault's versioning API
        # For now, this is a placeholder for future implementation
        logger.warning(f"Secret rollback not yet fully implemented for {secret_path}")
        return False

