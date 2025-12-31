# Connector Management System

## Overview

The Connector Management System provides a unified UI for configuring and managing all external system integrations (ISE, pxGrid, AD). When a connector is enabled, the corresponding service container is automatically deployed. This provides a seamless experience for setting up integrations.

---

## Architecture

### Connector Types

1. **ISE ERS API Connector**
   - Purpose: Sync existing ISE configuration (SGTs, policies, profiles)
   - Container: None (runs in main API service)
   - Configuration: ISE URL, credentials, SSL settings

2. **ISE pxGrid Connector**
   - Purpose: Real-time ISE session and endpoint events
   - Container: `clarion-pxgrid` (dedicated container)
   - Configuration: ISE hostname, credentials, client name, certificates
   - Deployment: pxGrid container deployed when enabled

3. **Active Directory Connector**
   - Purpose: User/group sync, device information
   - Container: None initially (runs in main API service), future: dedicated container
   - Configuration: Domain controller, credentials, base DN, sync schedule

4. **IoT Connectors** (Future)
   - Purpose: Device context from IoT platforms
   - Container: TBD
   - Configuration: Platform-specific

---

## Connector Configuration Flow

### 1. UI Configuration

**Connectors Page** (`/connectors`)
- List of available connectors with status
- Enable/disable toggle for each connector
- Navigate to connector-specific configuration page

**Connector Configuration Pages** (`/connectors/{connector_id}`)
- Connection settings (hostname, URL, ports)
- Authentication (username/password, certificates)
- Advanced settings (SSL verification, sync schedules)
- Test connection button
- Save configuration button
- Status/health display

### 2. API Endpoints

**Connector Management API** (`/api/connectors`)
- `GET /api/connectors` - List all connectors with status
- `GET /api/connectors/{connector_id}` - Get connector configuration
- `POST /api/connectors/{connector_id}/configure` - Save configuration
- `POST /api/connectors/{connector_id}/enable` - Enable connector (deploys container)
- `POST /api/connectors/{connector_id}/disable` - Disable connector (stops container)
- `GET /api/connectors/{connector_id}/status` - Get connector status/health
- `POST /api/connectors/{connector_id}/test` - Test connection

**Certificate Management API** (`/api/connectors/{connector_id}/certificates`)
- `POST /api/connectors/{connector_id}/certificates` - Upload certificate (client cert, key, CA cert)
- `GET /api/connectors/{connector_id}/certificates` - List certificates
- `DELETE /api/connectors/{connector_id}/certificates/{cert_id}` - Delete certificate

### 3. Container Deployment

**Dynamic Container Management**
- When connector enabled: Start corresponding container via Docker API
- When connector disabled: Stop container
- Certificate mounting: Mount certificates from database/storage to container
- Configuration injection: Inject connector config as environment variables

**Container Orchestration Options:**
1. **Docker Compose (Development)**: Use docker-compose to manage containers
2. **Docker API (Production)**: Direct Docker API calls to start/stop containers
3. **Kubernetes (Future)**: Kubernetes API for container orchestration

---

## Database Schema

### connectors Table

```sql
CREATE TABLE IF NOT EXISTS connectors (
    connector_id TEXT PRIMARY KEY,  -- 'ise_ers', 'ise_pxgrid', 'ad', 'iot_medigate', etc.
    name TEXT NOT NULL,
    type TEXT NOT NULL,  -- 'ise_ers', 'ise_pxgrid', 'ad', 'iot'
    enabled BOOLEAN DEFAULT 0,
    status TEXT DEFAULT 'disabled',  -- 'disabled', 'pending_approval', 'connected', 'error', 'connecting'
    
    -- Connection configuration (JSON)
    config TEXT,  -- JSON string with connector-specific settings
    
    -- Status tracking
    last_connected TIMESTAMP,
    last_error TEXT,
    error_count INTEGER DEFAULT 0,
    
    -- Metadata
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### connector_certificates Table

```sql
CREATE TABLE IF NOT EXISTS connector_certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    connector_id TEXT NOT NULL,
    cert_type TEXT NOT NULL,  -- 'client_cert', 'client_key', 'ca_cert'
    cert_data BLOB NOT NULL,  -- Certificate data (encrypted at rest in production)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (connector_id) REFERENCES connectors(connector_id)
);
```

---

## Implementation Plan

### Phase 1: Database & API Foundation
1. Create `connectors` and `connector_certificates` tables
2. Create connector management API endpoints
3. Create certificate upload/download API endpoints
4. Store connector configurations in database

### Phase 2: UI Components
1. Update Connectors.tsx to fetch connector status from API
2. Create connector configuration form components
3. Add certificate upload UI (file upload, paste text)
4. Add enable/disable toggle UI
5. Add connector status/health display

### Phase 3: ISE ERS API Connector
1. ISE connector configuration UI
2. Test connection functionality
3. Store configuration in database
4. Use stored config for ISE operations (policy deployment, sync)

### Phase 4: ISE pxGrid Connector
1. pxGrid connector configuration UI
2. Certificate upload UI (client cert, key, CA cert)
3. Enable/disable container deployment
4. Connect pxGrid API endpoints to connector management

### Phase 5: AD Connector
1. AD connector configuration UI
2. LDAP connection settings
3. Sync schedule configuration
4. Test connection functionality

### Phase 6: Container Deployment
1. Docker API integration for container management
2. Certificate mounting to containers
3. Configuration injection to containers
4. Container health monitoring

---

## Connector Configuration Details

### ISE ERS API Connector

**Configuration Fields:**
- ISE URL (e.g., `https://192.168.10.31`, port optional, defaults to 443)
- Username
- Password
- Verify SSL (boolean)
- Description

**Operations:**
- Test connection
- Sync ISE configuration (SGTs, profiles, policies)
- View synced configuration
- Use for policy deployment

**Container:** None (runs in main API service)

---

### ISE pxGrid Connector

**Configuration Fields:**
- ISE hostname (e.g., `192.168.10.31`)
- Username
- Password
- Client name (e.g., `clarion-pxgrid-client`)
- Port (default: 8910)
- Use SSL (boolean)
- Verify SSL (boolean)

**Certificates:**
- Client certificate (client.crt)
- Client private key (client.key)
- CA certificate (ca.crt)

**Operations:**
- Test connection (REST API authentication)
- Upload certificates
- Enable connector (starts pxGrid container)
- Disable connector (stops pxGrid container)
- View connection status
- View subscribed topics

**Container:** `clarion-pxgrid` (dedicated container)

**Container Deployment:**
- When enabled: Start `clarion-pxgrid` container with certificates mounted
- Mount certificates from database/storage to `/app/certs` in container
- Inject connection config as environment variables
- Connect to shared database volume

---

### AD Connector

**Configuration Fields:**
- Domain controller hostname/IP
- Port (default: 389 for LDAP, 636 for LDAPS)
- Base DN (e.g., `DC=example,DC=com`)
- Bind DN (service account)
- Bind password
- Use SSL/TLS (boolean)
- Verify SSL (boolean)
- Sync schedule (cron expression)
- Sync user details (boolean)
- Sync AD groups (boolean)
- Sync computer objects (boolean)

**Operations:**
- Test connection
- Manual sync trigger
- View sync status
- View last sync time
- View sync statistics

**Container:** None initially (runs in main API service)

---

## Certificate Management

### Certificate Storage

**Development:**
- Store certificates in database as BLOB
- Mount from database to container filesystem
- Or store in file system, reference from database

**Production:**
- Encrypt certificates at rest
- Use Docker secrets or Kubernetes secrets
- Store encrypted in database or secret manager

### Certificate Upload UI

**Options:**
1. File upload (drag & drop or file picker)
2. Text paste (paste certificate content)
3. Path input (reference to existing file)

**Validation:**
- Validate certificate format
- Check certificate expiration
- Validate certificate chain (if CA cert provided)

---

## Container Deployment Flow

### Enable Connector

1. User enables connector in UI
2. UI calls `POST /api/connectors/{connector_id}/enable`
3. Backend:
   - Validates configuration
   - Stores/updates connector config in database
   - If certificates needed: Validates certificates are uploaded
   - Calls Docker API to start container
   - Mounts certificates to container
   - Injects configuration as environment variables
   - Monitors container health
4. UI polls status endpoint to show connection status

### Disable Connector

1. User disables connector in UI
2. UI calls `POST /api/connectors/{connector_id}/disable`
3. Backend:
   - Calls Docker API to stop container
   - Updates connector status to 'disabled'
   - Optionally: Cleans up temporary files
4. UI updates to show disconnected status

---

## API Design

### Connector List

```typescript
GET /api/connectors

Response:
{
  "connectors": [
    {
      "connector_id": "ise_ers",
      "name": "ISE ERS API",
      "type": "ise_ers",
      "enabled": true,
      "status": "connected",
      "description": "Cisco ISE ERS API connector",
      "last_connected": "2025-12-30T22:00:00Z",
      "has_config": true
    },
    {
      "connector_id": "ise_pxgrid",
      "name": "ISE pxGrid",
      "type": "ise_pxgrid",
      "enabled": false,
      "status": "disabled",
      "description": "Cisco ISE pxGrid connector",
      "last_connected": null,
      "has_config": false,
      "container_status": "stopped"
    }
  ]
}
```

### Connector Configuration

```typescript
GET /api/connectors/ise_pxgrid

Response:
{
  "connector_id": "ise_pxgrid",
  "name": "ISE pxGrid",
  "type": "ise_pxgrid",
  "enabled": false,
  "status": "disabled",
  "config": {
    "ise_hostname": "192.168.10.31",
    "username": "admin",
    "client_name": "clarion-pxgrid-client",
    "port": 8910,
    "use_ssl": true,
    "verify_ssl": false
  },
  "certificates": {
    "has_client_cert": true,
    "has_client_key": true,
    "has_ca_cert": false
  },
  "container_status": "stopped",
  "last_connected": null,
  "last_error": null
}
```

### Enable Connector

```typescript
POST /api/connectors/ise_pxgrid/enable

Request:
{
  "config": {
    "ise_hostname": "192.168.10.31",
    "username": "admin",
    "password": "password",
    "client_name": "clarion-pxgrid-client",
    "port": 8910,
    "use_ssl": true,
    "verify_ssl": false
  }
}

Response:
{
  "status": "success",
  "message": "Connector enabled, container starting...",
  "connector_id": "ise_pxgrid",
  "container_status": "starting"
}
```

### Upload Certificate

```typescript
POST /api/connectors/ise_pxgrid/certificates

Request (multipart/form-data):
  cert_type: "client_cert"
  cert_file: <file>
  
  OR
  
Request (JSON):
{
  "cert_type": "client_cert",
  "cert_data": "-----BEGIN CERTIFICATE-----\n..."
}

Response:
{
  "status": "success",
  "cert_id": 123,
  "cert_type": "client_cert",
  "message": "Certificate uploaded successfully"
}
```

---

## Future Enhancements

1. **Container Orchestration**: Kubernetes support for container deployment
2. **Certificate Rotation**: Automated certificate renewal
3. **Multi-instance**: Support multiple ISE servers, multiple AD domains
4. **Connection Pooling**: Reuse connections across operations
5. **Event Logging**: Audit log for connector enable/disable, configuration changes
6. **Health Monitoring**: Proactive health checks and alerting
7. **Configuration Templates**: Pre-defined configurations for common setups

---

## References

- `docs/ISE_INTEGRATION.md` - ISE integration details
- `docs/DEPLOYMENT_ARCHITECTURE.md` - Container architecture
- `src/clarion/api/routes/pxgrid.py` - pxGrid API endpoints
- `src/clarion/api/routes/ise_config.py` - ISE config API endpoints

