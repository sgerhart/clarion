"""
HashiCorp Vault Client Wrapper

Provides a Python interface for interacting with HashiCorp Vault.
Handles authentication, secret storage/retrieval, and error handling.
"""
import logging
import time
from typing import Optional, Dict, Any, List
from pathlib import Path

try:
    import hvac
    from hvac.exceptions import VaultError
    HVAC_AVAILABLE = True
except ImportError:
    HVAC_AVAILABLE = False
    hvac = None
    VaultError = Exception

from clarion.secrets.config import VaultConfig

logger = logging.getLogger(__name__)


class VaultClient:
    """
    HashiCorp Vault client wrapper.
    
    Provides methods for storing and retrieving secrets from Vault.
    Supports both token and AppRole authentication.
    """
    
    def __init__(self, config: Optional[VaultConfig] = None):
        """
        Initialize Vault client.
        
        Args:
            config: Vault configuration. If None, loads from environment.
        """
        if not HVAC_AVAILABLE:
            raise ImportError(
                "hvac library is required for Vault integration. "
                "Install it with: pip install hvac"
            )
        
        self.config = config or VaultConfig.from_env()
        self.client = hvac.Client(url=self.config.address)
        
        # Set namespace if provided
        if self.config.namespace:
            self.client.adapter.namespace = self.config.namespace
        
        # Authenticate
        self._authenticate()
        
        # Verify connection
        if not self.client.is_authenticated():
            raise ConnectionError("Failed to authenticate with Vault")
        
        logger.info(f"Vault client initialized: {self.config.address}")
    
    def _authenticate(self):
        """Authenticate with Vault using token or AppRole."""
        if self.config.token:
            self.client.token = self.config.token
            logger.debug("Authenticated with Vault using token")
        elif self.config.role_id and self.config.secret_id:
            try:
                response = self.client.auth.approle.login(
                    role_id=self.config.role_id,
                    secret_id=self.config.secret_id
                )
                self.client.token = response['auth']['client_token']
                logger.debug("Authenticated with Vault using AppRole")
            except VaultError as e:
                raise ConnectionError(f"Failed to authenticate with Vault using AppRole: {e}")
        else:
            raise ValueError(
                "Either VAULT_TOKEN or VAULT_ROLE_ID/VAULT_SECRET_ID must be provided"
            )
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check Vault health.
        
        Returns:
            Health status dictionary
        """
        try:
            health = self.client.sys.read_health_status(method='GET')
            return {
                "healthy": True,
                "initialized": health.get("initialized", False),
                "sealed": health.get("sealed", False),
                "standby": health.get("standby", False),
            }
        except Exception as e:
            logger.error(f"Vault health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e)
            }
    
    def write_secret(
        self,
        path: str,
        data: Dict[str, Any],
        mount_point: Optional[str] = None
    ) -> bool:
        """
        Write a secret to Vault.
        
        Args:
            path: Secret path (relative to mount point)
            data: Secret data dictionary
            mount_point: Secrets engine mount point (defaults to config)
            
        Returns:
            True if successful
        """
        mount = mount_point or self.config.mount_point
        
        try:
            # KV v2 requires 'data' wrapper
            self.client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret=data,
                mount_point=mount
            )
            logger.debug(f"Secret written to {mount}/{path}")
            return True
        except VaultError as e:
            logger.error(f"Failed to write secret to {mount}/{path}: {e}")
            raise
    
    def read_secret(
        self,
        path: str,
        mount_point: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Read a secret from Vault.
        
        Args:
            path: Secret path (relative to mount point)
            mount_point: Secrets engine mount point (defaults to config)
            
        Returns:
            Secret data dictionary or None if not found
        """
        mount = mount_point or self.config.mount_point
        
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=mount
            )
            return response.get('data', {}).get('data', {})
        except VaultError as e:
            if 'not found' in str(e).lower() or '404' in str(e):
                logger.debug(f"Secret not found at {mount}/{path}")
                return None
            logger.error(f"Failed to read secret from {mount}/{path}: {e}")
            raise
    
    def delete_secret(
        self,
        path: str,
        mount_point: Optional[str] = None
    ) -> bool:
        """
        Delete a secret from Vault.
        
        Args:
            path: Secret path (relative to mount point)
            mount_point: Secrets engine mount point (defaults to config)
            
        Returns:
            True if successful
        """
        mount = mount_point or self.config.mount_point
        
        try:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=path,
                mount_point=mount
            )
            logger.debug(f"Secret deleted from {mount}/{path}")
            return True
        except VaultError as e:
            if 'not found' in str(e).lower() or '404' in str(e):
                logger.debug(f"Secret not found at {mount}/{path} (already deleted)")
                return True
            logger.error(f"Failed to delete secret from {mount}/{path}: {e}")
            raise
    
    def list_secrets(
        self,
        path: str = "",
        mount_point: Optional[str] = None
    ) -> List[str]:
        """
        List secrets at a path.
        
        Args:
            path: Path to list (relative to mount point)
            mount_point: Secrets engine mount point (defaults to config)
            
        Returns:
            List of secret paths
        """
        mount = mount_point or self.config.mount_point
        
        try:
            response = self.client.secrets.kv.v2.list_secrets(
                path=path,
                mount_point=mount
            )
            return response.get('data', {}).get('keys', [])
        except VaultError as e:
            if 'not found' in str(e).lower() or '404' in str(e):
                return []
            logger.error(f"Failed to list secrets at {mount}/{path}: {e}")
            raise
    
    # Connector-specific methods
    
    def store_connector_credentials(
        self,
        connector_id: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Store connector credentials in Vault.
        
        Args:
            connector_id: Connector identifier (e.g., 'ise_pxgrid')
            username: Username (optional)
            password: Password (optional)
            **kwargs: Additional credential fields
            
        Returns:
            True if successful
        """
        path = self.config.get_connector_path(connector_id)
        
        data = {}
        if username:
            data['username'] = username
        if password:
            data['password'] = password
        data.update(kwargs)
        
        return self.write_secret(path, data)
    
    def get_connector_credentials(
        self,
        connector_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve connector credentials from Vault.
        
        Args:
            connector_id: Connector identifier
            
        Returns:
            Credentials dictionary or None if not found
        """
        path = self.config.get_connector_path(connector_id)
        return self.read_secret(path)
    
    # Certificate-specific methods
    
    def store_certificate(
        self,
        certificate_id: str,
        cert_data: bytes,
        key_data: Optional[bytes] = None,
        ca_cert_data: Optional[bytes] = None,
        cert_type: str = "client"
    ) -> bool:
        """
        Store certificate data in Vault.
        
        Args:
            certificate_id: Certificate identifier
            cert_data: Certificate data (bytes)
            key_data: Private key data (bytes, optional)
            ca_cert_data: CA certificate data (bytes, optional)
            cert_type: Certificate type (e.g., 'client', 'server')
            
        Returns:
            True if successful
        """
        path = self.config.get_certificate_path(certificate_id)
        
        data = {
            'cert_type': cert_type,
            'cert_data': cert_data.decode('utf-8') if isinstance(cert_data, bytes) else cert_data,
        }
        
        if key_data:
            data['key_data'] = key_data.decode('utf-8') if isinstance(key_data, bytes) else key_data
        if ca_cert_data:
            data['ca_cert_data'] = ca_cert_data.decode('utf-8') if isinstance(ca_cert_data, bytes) else ca_cert_data
        
        return self.write_secret(path, data)
    
    def get_certificate(
        self,
        certificate_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve certificate data from Vault.
        
        Args:
            certificate_id: Certificate identifier
            
        Returns:
            Certificate data dictionary or None if not found
        """
        path = self.config.get_certificate_path(certificate_id)
        secret = self.read_secret(path)
        
        if secret:
            # Convert string data back to bytes if needed
            if 'cert_data' in secret and isinstance(secret['cert_data'], str):
                secret['cert_data'] = secret['cert_data'].encode('utf-8')
            if 'key_data' in secret and isinstance(secret['key_data'], str):
                secret['key_data'] = secret['key_data'].encode('utf-8')
            if 'ca_cert_data' in secret and isinstance(secret['ca_cert_data'], str):
                secret['ca_cert_data'] = secret['ca_cert_data'].encode('utf-8')
        
        return secret
    
    # API key methods
    
    def store_api_key(
        self,
        service: str,
        api_key: str,
        **kwargs
    ) -> bool:
        """
        Store API key in Vault.
        
        Args:
            service: Service name (e.g., 'openai', 'anthropic')
            api_key: API key value
            **kwargs: Additional metadata
            
        Returns:
            True if successful
        """
        path = self.config.get_api_key_path(service)
        
        data = {
            'api_key': api_key,
            **kwargs
        }
        
        return self.write_secret(path, data)
    
    def get_api_key(
        self,
        service: str
    ) -> Optional[str]:
        """
        Retrieve API key from Vault.
        
        Args:
            service: Service name
            
        Returns:
            API key string or None if not found
        """
        path = self.config.get_api_key_path(service)
        secret = self.read_secret(path)
        
        if secret:
            return secret.get('api_key')
        return None

