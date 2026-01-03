"""
Tests for Vault Client

Tests the Vault client wrapper functionality.
Requires a running Vault instance (use docker-compose.vault.yml for dev).
"""
import pytest
import os
from clarion.secrets import VaultClient, VaultConfig


@pytest.fixture
def vault_config():
    """Create Vault config for testing."""
    return VaultConfig(
        address=os.getenv("VAULT_ADDR", "http://localhost:8200"),
        token=os.getenv("VAULT_TOKEN", "clarion-dev-root-token"),
        mount_point="secret"
    )


@pytest.fixture
def vault_client(vault_config):
    """Create Vault client for testing."""
    try:
        client = VaultClient(vault_config)
        # Verify connection
        health = client.health_check()
        if not health.get("healthy"):
            pytest.skip("Vault is not available or not healthy")
        return client
    except Exception as e:
        pytest.skip(f"Failed to connect to Vault: {e}")


def test_health_check(vault_client):
    """Test Vault health check."""
    health = vault_client.health_check()
    assert health["healthy"] is True
    assert health["initialized"] is True
    assert health["sealed"] is False


def test_write_and_read_secret(vault_client):
    """Test writing and reading a secret."""
    test_path = "test/secret"
    test_data = {"key1": "value1", "key2": "value2", "number": 42}
    
    # Write secret
    result = vault_client.write_secret(test_path, test_data)
    assert result is True
    
    # Read secret
    secret = vault_client.read_secret(test_path)
    assert secret is not None
    assert secret["key1"] == "value1"
    assert secret["key2"] == "value2"
    assert secret["number"] == 42
    
    # Cleanup
    vault_client.delete_secret(test_path)


def test_read_nonexistent_secret(vault_client):
    """Test reading a non-existent secret."""
    secret = vault_client.read_secret("nonexistent/path")
    assert secret is None


def test_delete_secret(vault_client):
    """Test deleting a secret."""
    test_path = "test/delete"
    test_data = {"key": "value"}
    
    # Write secret
    vault_client.write_secret(test_path, test_data)
    
    # Delete secret
    result = vault_client.delete_secret(test_path)
    assert result is True
    
    # Verify deleted
    secret = vault_client.read_secret(test_path)
    assert secret is None


def test_list_secrets(vault_client):
    """Test listing secrets."""
    # Create some test secrets
    vault_client.write_secret("test/list/secret1", {"key": "value1"})
    vault_client.write_secret("test/list/secret2", {"key": "value2"})
    
    # List secrets
    secrets = vault_client.list_secrets("test/list")
    assert len(secrets) >= 2
    assert "secret1" in secrets or "secret1/" in str(secrets)
    assert "secret2" in secrets or "secret2/" in str(secrets)
    
    # Cleanup
    vault_client.delete_secret("test/list/secret1")
    vault_client.delete_secret("test/list/secret2")


def test_connector_credentials(vault_client):
    """Test connector credential storage and retrieval."""
    connector_id = "test_connector"
    username = "test_user"
    password = "test_password"
    
    # Store credentials
    result = vault_client.store_connector_credentials(
        connector_id=connector_id,
        username=username,
        password=password,
        hostname="test.example.com"
    )
    assert result is True
    
    # Retrieve credentials
    creds = vault_client.get_connector_credentials(connector_id)
    assert creds is not None
    assert creds["username"] == username
    assert creds["password"] == password
    assert creds["hostname"] == "test.example.com"
    
    # Cleanup
    path = vault_client.config.get_connector_path(connector_id)
    vault_client.delete_secret(path)


def test_certificate_storage(vault_client):
    """Test certificate storage and retrieval."""
    cert_id = "test_cert"
    cert_data = b"-----BEGIN CERTIFICATE-----\nTEST CERT DATA\n-----END CERTIFICATE-----"
    key_data = b"-----BEGIN PRIVATE KEY-----\nTEST KEY DATA\n-----END PRIVATE KEY-----"
    ca_data = b"-----BEGIN CERTIFICATE-----\nTEST CA DATA\n-----END CERTIFICATE-----"
    
    # Store certificate
    result = vault_client.store_certificate(
        certificate_id=cert_id,
        cert_data=cert_data,
        key_data=key_data,
        ca_cert_data=ca_data,
        cert_type="client"
    )
    assert result is True
    
    # Retrieve certificate
    cert = vault_client.get_certificate(cert_id)
    assert cert is not None
    assert cert["cert_type"] == "client"
    assert cert["cert_data"] == cert_data
    assert cert["key_data"] == key_data
    assert cert["ca_cert_data"] == ca_data
    
    # Cleanup
    path = vault_client.config.get_certificate_path(cert_id)
    vault_client.delete_secret(path)


def test_api_key_storage(vault_client):
    """Test API key storage and retrieval."""
    service = "test_service"
    api_key = "sk-test123456789"
    
    # Store API key
    result = vault_client.store_api_key(
        service=service,
        api_key=api_key,
        organization_id="org-123"
    )
    assert result is True
    
    # Retrieve API key
    retrieved_key = vault_client.get_api_key(service)
    assert retrieved_key == api_key
    
    # Cleanup
    path = vault_client.config.get_api_key_path(service)
    vault_client.delete_secret(path)


def test_config_from_env():
    """Test VaultConfig.from_env()."""
    os.environ["VAULT_ADDR"] = "http://test:8200"
    os.environ["VAULT_TOKEN"] = "test-token"
    
    config = VaultConfig.from_env()
    assert config.address == "http://test:8200"
    assert config.token == "test-token"
    
    # Cleanup
    del os.environ["VAULT_ADDR"]
    del os.environ["VAULT_TOKEN"]


def test_path_helpers(vault_config):
    """Test path helper methods."""
    assert vault_config.get_connector_path("ise_pxgrid") == "connectors/ise_pxgrid"
    assert vault_config.get_certificate_path("test-cert") == "certificates/test-cert"
    assert vault_config.get_api_key_path("openai") == "api_keys/openai"

