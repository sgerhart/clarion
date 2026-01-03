"""
Vault Helper Functions

Helper functions for integrating Vault with application code.
"""
import logging
from typing import Optional, Dict, Any, Tuple
from clarion.secrets import VaultClient, VaultConfig

logger = logging.getLogger(__name__)

# Global Vault client instance (lazy initialization)
_vault_client: Optional[VaultClient] = None


def get_vault_client() -> Optional[VaultClient]:
    """
    Get or create Vault client instance.
    
    Returns:
        VaultClient instance or None if Vault is not configured
    """
    global _vault_client
    
    if _vault_client is not None:
        return _vault_client
    
    try:
        config = VaultConfig.from_env()
        # Only create client if Vault is configured
        if config.address and (config.token or (config.role_id and config.secret_id)):
            _vault_client = VaultClient(config)
            logger.info("Vault client initialized")
            return _vault_client
        else:
            logger.debug("Vault not configured (missing address or credentials)")
            return None
    except Exception as e:
        logger.warning(f"Failed to initialize Vault client: {e}")
        return None


def load_connector_credentials_from_vault(connector_id: str) -> Optional[Dict[str, Any]]:
    """
    Load connector credentials from Vault.
    
    Args:
        connector_id: Connector identifier (e.g., 'ise_pxgrid')
        
    Returns:
        Credentials dictionary or None if not found
    """
    vault = get_vault_client()
    if not vault:
        return None
    
    try:
        creds = vault.get_connector_credentials(connector_id)
        if creds:
            logger.debug(f"Loaded credentials for {connector_id} from Vault")
        return creds
    except Exception as e:
        logger.error(f"Failed to load credentials from Vault for {connector_id}: {e}")
        return None


def load_certificates_from_vault(connector_id: str) -> Optional[Tuple[Optional[bytes], Optional[bytes], Optional[bytes]]]:
    """
    Load certificates from Vault for a connector.
    
    Args:
        connector_id: Connector identifier (e.g., 'ise_pxgrid')
        
    Returns:
        Tuple of (client_cert_data, client_key_data, ca_cert_data) or None if not found
    """
    vault = get_vault_client()
    if not vault:
        return None
    
    try:
        cert_data = vault.get_certificate(connector_id)
        if not cert_data:
            return None
        
        client_cert = cert_data.get('cert_data')
        client_key = cert_data.get('key_data')
        ca_cert = cert_data.get('ca_cert_data')
        
        # Convert string to bytes if needed
        if isinstance(client_cert, str):
            client_cert = client_cert.encode('utf-8')
        if isinstance(client_key, str):
            client_key = client_key.encode('utf-8')
        if isinstance(ca_cert, str):
            ca_cert = ca_cert.encode('utf-8')
        
        logger.debug(f"Loaded certificates for {connector_id} from Vault")
        return (client_cert, client_key, ca_cert)
    except Exception as e:
        logger.error(f"Failed to load certificates from Vault for {connector_id}: {e}")
        return None


def store_connector_credentials_to_vault(
    connector_id: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs
) -> bool:
    """
    Store connector credentials in Vault.
    
    Args:
        connector_id: Connector identifier
        username: Username (optional)
        password: Password (optional)
        **kwargs: Additional credential fields
        
    Returns:
        True if successful, False otherwise
    """
    vault = get_vault_client()
    if not vault:
        logger.warning("Vault not available, cannot store credentials")
        return False
    
    try:
        vault.store_connector_credentials(
            connector_id=connector_id,
            username=username,
            password=password,
            **kwargs
        )
        logger.info(f"Stored credentials for {connector_id} in Vault")
        return True
    except Exception as e:
        logger.error(f"Failed to store credentials in Vault for {connector_id}: {e}")
        return False


def store_certificates_to_vault(
    connector_id: str,
    cert_data: Optional[bytes] = None,
    key_data: Optional[bytes] = None,
    ca_cert_data: Optional[bytes] = None
) -> bool:
    """
    Store certificates in Vault for a connector.
    
    Args:
        connector_id: Connector identifier
        cert_data: Client certificate data (bytes)
        key_data: Client private key data (bytes)
        ca_cert_data: CA certificate data (bytes)
        
    Returns:
        True if successful, False otherwise
    """
    vault = get_vault_client()
    if not vault:
        logger.warning("Vault not available, cannot store certificates")
        return False
    
    try:
        vault.store_certificate(
            certificate_id=connector_id,
            cert_data=cert_data,
            key_data=key_data,
            ca_cert_data=ca_cert_data,
            cert_type="client"
        )
        logger.info(f"Stored certificates for {connector_id} in Vault")
        return True
    except Exception as e:
        logger.error(f"Failed to store certificates in Vault for {connector_id}: {e}")
        return False

