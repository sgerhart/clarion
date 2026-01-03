"""
HashiCorp Vault Client Wrapper

Provides a Python interface for interacting with HashiCorp Vault.
Handles authentication, secret storage/retrieval, and error handling.
Includes connection pooling, retry logic, and comprehensive error handling.
"""
import logging
import time
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
from functools import wraps
import threading

try:
    import hvac
    from hvac.exceptions import VaultError, InvalidRequest, InvalidPath
    HVAC_AVAILABLE = True
except ImportError:
    HVAC_AVAILABLE = False
    hvac = None
    VaultError = Exception
    InvalidRequest = Exception
    InvalidPath = Exception

from clarion.secrets.config import VaultConfig

logger = logging.getLogger(__name__)


def retry_on_failure(max_retries: int = 3, backoff_factor: float = 1.0, exceptions: tuple = (VaultError,)):
    """
    Decorator for retrying Vault operations on failure.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(self, *args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor * (2 ** attempt)
                        logger.warning(
                            f"Vault operation failed (attempt {attempt + 1}/{max_retries}): {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        time.sleep(wait_time)
                        # Re-authenticate if token might be expired
                        if hasattr(self, '_authenticate'):
                            try:
                                self._authenticate()
                            except Exception as auth_error:
                                logger.error(f"Re-authentication failed: {auth_error}")
                    else:
                        logger.error(f"Vault operation failed after {max_retries} attempts: {e}")
            raise last_exception
        return wrapper
    return decorator


class VaultClient:
    """
    HashiCorp Vault client wrapper.
    
    Provides methods for storing and retrieving secrets from Vault.
    Supports both token and AppRole authentication.
    Includes connection pooling, retry logic, and comprehensive error handling.
    """
    
    _lock = threading.Lock()  # Thread-safe client access
    
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
        self._client = None
        self._last_auth_time = 0
        self._auth_token_ttl = 3600  # Assume 1 hour TTL, will be updated from Vault
        
        # Initialize client
        self._initialize_client()
        
        logger.info(f"Vault client initialized: {self.config.address}")
    
    def _initialize_client(self):
        """Initialize and authenticate Vault client."""
        with self._lock:
            self._client = hvac.Client(
                url=self.config.address,
                timeout=self.config.timeout,
                verify=self.config.verify
            )
            
            # Set namespace if provided
            if self.config.namespace:
                self._client.adapter.namespace = self.config.namespace
            
            # Authenticate
            self._authenticate()
            
            # Verify connection
            if not self._client.is_authenticated():
                raise ConnectionError("Failed to authenticate with Vault")
    
    @property
    def client(self):
        """Get Vault client, re-authenticating if token expired."""
        # Check if token might be expired (simple heuristic)
        if time.time() - self._last_auth_time > (self._auth_token_ttl * 0.8):
            try:
                if not self._client.is_authenticated():
                    logger.info("Vault token expired, re-authenticating...")
                    self._authenticate()
            except Exception as e:
                logger.warning(f"Token check failed, re-authenticating: {e}")
                self._authenticate()
        
        return self._client
    
    def _authenticate(self):
        """Authenticate with Vault using token or AppRole."""
        with self._lock:
            if self.config.token:
                self._client.token = self.config.token
                logger.debug("Authenticated with Vault using token")
                self._last_auth_time = time.time()
            elif self.config.role_id and self.config.secret_id:
                try:
                    response = self._client.auth.approle.login(
                        role_id=self.config.role_id,
                        secret_id=self.config.secret_id
                    )
                    self._client.token = response['auth']['client_token']
                    self._last_auth_time = time.time()
                    
                    # Update token TTL from response
                    if 'lease_duration' in response.get('auth', {}):
                        self._auth_token_ttl = response['auth']['lease_duration']
                    
                    logger.debug(f"Authenticated with Vault using AppRole (TTL: {self._auth_token_ttl}s)")
                except VaultError as e:
                    raise ConnectionError(f"Failed to authenticate with Vault using AppRole: {e}")
            else:
                raise ValueError(
                    "Either VAULT_TOKEN or VAULT_ROLE_ID/VAULT_SECRET_ID must be provided"
                )
    
    @retry_on_failure(max_retries=2, backoff_factor=0.5)
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
                "server_time_utc": health.get("server_time_utc"),
                "version": health.get("version"),
            }
        except Exception as e:
            logger.error(f"Vault health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e)
            }
    
    @retry_on_failure(max_retries=3, backoff_factor=1.0)
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
        except InvalidRequest as e:
            # Don't retry on invalid requests (e.g., bad data format)
            logger.error(f"Invalid request writing secret to {mount}/{path}: {e}")
            raise
        except VaultError as e:
            logger.error(f"Failed to write secret to {mount}/{path}: {e}")
            raise
    
    @retry_on_failure(max_retries=3, backoff_factor=1.0)
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
        except InvalidPath as e:
            # Path doesn't exist - not an error, just return None
            logger.debug(f"Secret not found at {mount}/{path}")
            return None
        except VaultError as e:
            if 'not found' in str(e).lower() or '404' in str(e):
                logger.debug(f"Secret not found at {mount}/{path}")
                return None
            logger.error(f"Failed to read secret from {mount}/{path}: {e}")
            raise
    
    @retry_on_failure(max_retries=3, backoff_factor=1.0)
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
        except InvalidPath as e:
            # Path doesn't exist - consider it already deleted
            logger.debug(f"Secret not found at {mount}/{path} (already deleted)")
            return True
        except VaultError as e:
            if 'not found' in str(e).lower() or '404' in str(e):
                logger.debug(f"Secret not found at {mount}/{path} (already deleted)")
                return True
            logger.error(f"Failed to delete secret from {mount}/{path}: {e}")
            raise
    
    @retry_on_failure(max_retries=2, backoff_factor=0.5)
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
        except InvalidPath as e:
            # Path doesn't exist - return empty list
            return []
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

