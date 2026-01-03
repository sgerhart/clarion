"""
Vault Configuration

Configuration management for HashiCorp Vault integration.
"""
import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class VaultConfig:
    """Vault connection configuration."""
    
    address: str = "http://localhost:8200"
    token: Optional[str] = None
    role_id: Optional[str] = None  # For AppRole authentication
    secret_id: Optional[str] = None  # For AppRole authentication
    mount_point: str = "secret"  # KV v2 secrets engine mount point
    namespace: Optional[str] = None  # Vault namespace (for Vault Enterprise)
    
    # Paths for different secret types
    connector_secrets_path: str = "connectors"
    certificate_secrets_path: str = "certificates"
    api_key_secrets_path: str = "api_keys"
    
    # Connection settings
    timeout: int = 30
    verify: bool = True  # Verify SSL certificates
    
    @classmethod
    def from_env(cls) -> "VaultConfig":
        """Create VaultConfig from environment variables."""
        return cls(
            address=os.getenv("VAULT_ADDR", "http://localhost:8200"),
            token=os.getenv("VAULT_TOKEN"),
            role_id=os.getenv("VAULT_ROLE_ID"),
            secret_id=os.getenv("VAULT_SECRET_ID"),
            mount_point=os.getenv("VAULT_MOUNT_POINT", "secret"),
            namespace=os.getenv("VAULT_NAMESPACE"),
            connector_secrets_path=os.getenv("VAULT_CONNECTOR_PATH", "connectors"),
            certificate_secrets_path=os.getenv("VAULT_CERT_PATH", "certificates"),
            api_key_secrets_path=os.getenv("VAULT_API_KEY_PATH", "api_keys"),
            timeout=int(os.getenv("VAULT_TIMEOUT", "30")),
            verify=os.getenv("VAULT_VERIFY", "true").lower() == "true",
        )
    
    def get_connector_path(self, connector_id: str) -> str:
        """Get Vault path for connector secrets."""
        return f"{self.connector_secrets_path}/{connector_id}"
    
    def get_certificate_path(self, certificate_id: str) -> str:
        """Get Vault path for certificate secrets."""
        return f"{self.certificate_secrets_path}/{certificate_id}"
    
    def get_api_key_path(self, service: str) -> str:
        """Get Vault path for API key secrets."""
        return f"{self.api_key_secrets_path}/{service}"

