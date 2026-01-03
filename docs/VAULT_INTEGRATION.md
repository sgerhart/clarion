# HashiCorp Vault Integration Guide

## Overview

Clarion uses HashiCorp Vault for secure secrets management. All sensitive data (passwords, API keys, certificates, tokens) are stored in Vault, not in the database. The database only contains non-sensitive configuration and metadata.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Clarion Services                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │   API    │  │  pxGrid  │  │   AD     │            │
│  │ Service  │  │ Service  │  │ Connector│            │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘            │
│       │             │              │                   │
│       └─────────────┼──────────────┘                   │
│                     │                                  │
│              ┌──────▼──────┐                          │
│              │ VaultClient │                          │
│              │   Wrapper   │                          │
│              └──────┬──────┘                          │
└─────────────────────┼─────────────────────────────────┘
                       │
              ┌────────▼────────┐
              │  HashiCorp      │
              │     Vault      │
              │                 │
              │  KV v2 Secrets  │
              │  - Connectors   │
              │  - Certificates │
              │  - API Keys     │
              └─────────────────┘
```

## Quick Start

### 1. Start Vault (Development)

```bash
# Using Docker Compose
docker-compose -f docker-compose.vault.yml up -d

# Or using Docker directly
docker run -d \
  --name clarion-vault \
  -p 8200:8200 \
  -e VAULT_DEV_ROOT_TOKEN_ID=clarion-dev-root-token \
  hashicorp/vault:latest \
  vault server -dev
```

**⚠️ Development Mode Warning:**
- Development mode is **NOT SECURE** for production
- Uses in-memory storage (data is lost on restart)
- Single unseal key = root token
- Only use for development/testing

### 2. Set Environment Variables

```bash
export VAULT_ADDR="http://localhost:8200"
export VAULT_TOKEN="clarion-dev-root-token"  # From dev mode
```

### 3. Verify Vault is Running

```bash
# Check Vault status
curl http://localhost:8200/v1/sys/health

# Or using vault CLI
vault status
```

### 4. Test Vault Client

```python
from clarion.secrets import VaultClient, VaultConfig

# Initialize client
config = VaultConfig.from_env()
vault = VaultClient(config)

# Health check
health = vault.health_check()
print(health)

# Store a test secret
vault.write_secret("test/path", {"key": "value"})

# Retrieve secret
secret = vault.read_secret("test/path")
print(secret)
```

## Production Setup

### 1. Deploy Vault

**Option A: Docker (Recommended for small deployments)**
```bash
docker run -d \
  --name clarion-vault \
  -p 8200:8200 \
  -v vault-data:/vault/data \
  -v vault-config:/vault/config \
  hashicorp/vault:latest \
  vault server -config /vault/config/vault.hcl
```

**Option B: Kubernetes**
- Use HashiCorp Vault Helm chart
- Configure auto-unsealing (e.g., AWS KMS, Azure Key Vault)
- Set up high availability

**Option C: Managed Service**
- HashiCorp Cloud Platform (HCP)
- AWS Secrets Manager (alternative)
- Azure Key Vault (alternative)

### 2. Initialize Vault

```bash
# Initialize Vault (first time only)
vault operator init -key-shares=5 -key-threshold=3

# Save unseal keys and root token securely!
# Unseal Vault
vault operator unseal <unseal-key-1>
vault operator unseal <unseal-key-2>
vault operator unseal <unseal-key-3>
```

### 3. Configure Secrets Engine

```bash
# Enable KV v2 secrets engine
vault secrets enable -version=2 -path=secret kv

# Create policy for Clarion services
vault policy write clarion-policy - <<EOF
path "secret/data/connectors/*" {
  capabilities = ["create", "read", "update", "delete"]
}

path "secret/data/certificates/*" {
  capabilities = ["create", "read", "update", "delete"]
}

path "secret/data/api_keys/*" {
  capabilities = ["create", "read", "update", "delete"]
}
EOF
```

### 4. Set Up AppRole Authentication (Recommended)

```bash
# Enable AppRole auth method
vault auth enable approle

# Create AppRole for Clarion API service
vault write auth/approle/role/clarion-api \
    token_policies=clarion-policy \
    token_ttl=1h \
    token_max_ttl=4h

# Get Role ID
vault read auth/approle/role/clarion-api/role-id

# Generate Secret ID
vault write -f auth/approle/role/clarion-api/secret-id
```

### 5. Configure Environment Variables

```bash
# For AppRole authentication
export VAULT_ADDR="http://vault:8200"
export VAULT_ROLE_ID="<role-id>"
export VAULT_SECRET_ID="<secret-id>"

# Or for token authentication
export VAULT_ADDR="http://vault:8200"
export VAULT_TOKEN="<token>"
```

## Secret Paths

### Connector Secrets
- Path: `secret/data/connectors/{connector_id}`
- Example: `secret/data/connectors/ise_pxgrid`
- Data: `username`, `password`, `hostname`, etc.

### Certificates
- Path: `secret/data/certificates/{certificate_id}`
- Example: `secret/data/certificates/pxgrid-client-cert`
- Data: `cert_data`, `key_data`, `ca_cert_data`

### API Keys
- Path: `secret/data/api_keys/{service}`
- Example: `secret/data/api_keys/openai`
- Data: `api_key`, `organization_id`, etc.

## Migration from Database

See `scripts/migrate_secrets_to_vault.py` for automated migration script.

**Manual Migration Steps:**

1. **Export secrets from database:**
```python
# Connect to database
# Read connector configs
# Read certificates
```

2. **Import to Vault:**
```python
from clarion.secrets import VaultClient

vault = VaultClient()

# Migrate connector credentials
vault.store_connector_credentials(
    connector_id="ise_pxgrid",
    username="admin",
    password="password"
)

# Migrate certificates
vault.store_certificate(
    certificate_id="pxgrid-client",
    cert_data=cert_bytes,
    key_data=key_bytes,
    ca_cert_data=ca_bytes
)
```

3. **Update database:**
- Remove password fields from `connectors.config` JSON
- Remove certificate BLOB data
- Add `vault_path` reference

## Usage Examples

### Store Connector Credentials

```python
from clarion.secrets import VaultClient

vault = VaultClient()

# Store ISE pxGrid credentials
vault.store_connector_credentials(
    connector_id="ise_pxgrid",
    username="admin",
    password="secret-password",
    hostname="ise.example.com"
)
```

### Retrieve Connector Credentials

```python
from clarion.secrets import VaultClient

vault = VaultClient()

# Get credentials
creds = vault.get_connector_credentials("ise_pxgrid")
if creds:
    username = creds.get("username")
    password = creds.get("password")
```

### Store Certificates

```python
from clarion.secrets import VaultClient

vault = VaultClient()

# Read certificate files
with open("client.crt", "rb") as f:
    cert_data = f.read()
with open("client.key", "rb") as f:
    key_data = f.read()
with open("ca.crt", "rb") as f:
    ca_data = f.read()

# Store in Vault
vault.store_certificate(
    certificate_id="pxgrid-client",
    cert_data=cert_data,
    key_data=key_data,
    ca_cert_data=ca_data
)
```

### Retrieve Certificates

```python
from clarion.secrets import VaultClient

vault = VaultClient()

# Get certificate
cert = vault.get_certificate("pxgrid-client")
if cert:
    cert_data = cert["cert_data"]
    key_data = cert["key_data"]
    ca_cert_data = cert["ca_cert_data"]
```

### Store API Keys

```python
from clarion.secrets import VaultClient

vault = VaultClient()

# Store OpenAI API key
vault.store_api_key(
    service="openai",
    api_key="sk-...",
    organization_id="org-..."
)
```

## Integration with Application Code

### Update PxGridClient

```python
from clarion.secrets import VaultClient

class PxGridClient:
    def __init__(self, config: PxGridConfig):
        self.config = config
        self.vault = VaultClient()
        
        # Retrieve credentials from Vault
        if not config.password:
            creds = self.vault.get_connector_credentials("ise_pxgrid")
            if creds:
                config.password = creds.get("password")
                config.username = creds.get("username", config.client_name)
```

### Update Connector API Routes

```python
from clarion.secrets import VaultClient

@router.post("/connectors/{connector_id}/enable")
async def enable_connector(connector_id: str):
    vault = VaultClient()
    
    # Get credentials from Vault
    creds = vault.get_connector_credentials(connector_id)
    if not creds:
        raise HTTPException(400, "Credentials not found in Vault")
    
    # Use credentials for connection
    ...
```

## Security Best Practices

1. **Never store secrets in code or environment variables**
   - Use Vault for all secrets
   - Use AppRole authentication in production

2. **Rotate secrets regularly**
   - Implement secret rotation framework
   - Use Vault's secret versioning

3. **Limit access with policies**
   - Principle of least privilege
   - Separate policies for different services

4. **Enable audit logging**
   - Track all secret access
   - Monitor for suspicious activity

5. **Use namespaces (Vault Enterprise)**
   - Isolate secrets by environment
   - Separate dev/staging/prod

6. **Enable auto-unsealing**
   - Use cloud KMS (AWS, Azure, GCP)
   - Avoid manual unsealing

## Troubleshooting

### Connection Issues

```python
# Check Vault health
vault = VaultClient()
health = vault.health_check()
print(health)

# Verify authentication
if not vault.client.is_authenticated():
    print("Authentication failed")
```

### Secret Not Found

```python
# Check if secret exists
secrets = vault.list_secrets("connectors")
print(secrets)

# Verify path
path = vault.config.get_connector_path("ise_pxgrid")
print(f"Looking for secret at: {path}")
```

### Permission Denied

- Verify Vault policy grants required permissions
- Check AppRole/token has correct policy attached
- Verify mount point is correct

## References

- [HashiCorp Vault Documentation](https://www.vaultproject.io/docs)
- [Vault Python Client (hvac)](https://hvac.readthedocs.io/)
- [Vault Best Practices](https://learn.hashicorp.com/tutorials/vault/production-hardening)

