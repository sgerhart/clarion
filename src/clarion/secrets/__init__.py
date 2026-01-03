"""
Clarion Secrets Management

Provides secure secrets management using HashiCorp Vault.
"""

from clarion.secrets.vault_client import VaultClient
from clarion.secrets.config import VaultConfig
from clarion.secrets.helpers import (
    get_vault_client,
    load_connector_credentials_from_vault,
    load_certificates_from_vault,
    store_connector_credentials_to_vault,
    store_certificates_to_vault,
)

__all__ = [
    'VaultClient',
    'VaultConfig',
    'get_vault_client',
    'load_connector_credentials_from_vault',
    'load_certificates_from_vault',
    'store_connector_credentials_to_vault',
    'store_certificates_to_vault',
]

