# ISE pxGrid Integration - Implementation Summary

## Overview

Clarion integrates with Cisco ISE pxGrid (pxGrid REST API) to receive real-time session and endpoint events from ISE. This enables:
- **Real-time user database population** from ISE authentication events
- **Current SGT assignment tracking** from ISE
- **User-device association mapping** based on active sessions
- **Live visibility** into network access patterns

## Architecture

### Microservices Design

The pxGrid integration runs as a **separate containerized service** (`clarion-pxgrid`) to:
- Isolate certificate management (pxGrid requires mutual TLS/client certificates)
- Enable independent scaling and deployment
- Maintain clear separation of concerns
- Allow certificate rotation without affecting the main API service

### Components

1. **pxGrid Client** (`src/clarion/integration/pxgrid_client.py`)
   - Handles pxGrid REST API authentication
   - Supports both username/password and certificate-based authentication
   - Manages pxGrid account creation and activation flow
   - Provides event subscription capabilities

2. **pxGrid Subscriber** (`src/clarion/integration/pxgrid_subscriber.py`)
   - Processes ISE session and endpoint events
   - Updates Clarion database with user/device information
   - Tracks current SGT assignments
   - Manages user-device associations

3. **pxGrid Service** (`services/pxgrid/pxgrid_service.py`)
   - Standalone FastAPI service running in container
   - Loads configuration from database (connectors table)
   - Provides HTTP API for status and control (`/status`, `/start`, `/stop`, `/reload`)
   - Runs the pxGrid subscriber in a background thread

4. **Connector Management UI** (`frontend/src/pages/connectors/ISE.tsx`)
   - Combined ISE connector page (ERS API + pxGrid tabs)
   - Configuration form for pxGrid (hostname, username, password, client name, port, SSL settings)
   - Authentication method toggle (Username/Password vs Certificate)
   - Test Connection button
   - Enable/Disable controls

## Key Features Implemented

### 1. Account Creation and Activation Flow

pxGrid uses a two-phase account setup:
1. **AccountCreate**: Create a new pxGrid client account (requires ISE admin credentials)
   - ISE generates and returns a bootstrap password
   - Account state: PENDING (requires approval in ISE GUI)
2. **AccountActivate**: Check account state and activate
   - Returns account state (PENDING, ENABLED)
   - After approval in ISE, state becomes ENABLED
3. **Authentication**: Authenticate and get access token (requires client credentials)

**Bootstrap Password Handling**:
- Bootstrap password is automatically captured and persisted in database
- Config username is updated to client_name after account creation
- Password is stored in connector config for future connections

### 2. Dual Authentication Support

**Username/Password Authentication**:
- Default authentication method
- Uses ISE admin credentials for AccountCreate
- Uses client credentials (client_name + bootstrap_password) for Auth
- Suitable for initial setup and testing

**Certificate-Based Authentication (Mutual TLS)**:
- Uses client certificate + private key for mutual TLS
- More secure for production deployments
- Requires certificates to be uploaded via Certificate Settings
- Certificates are stored in centralized certificate management system

### 3. PENDING Approval Handling

When a pxGrid client account is created, it enters PENDING state until approved in ISE:
- **Enable Endpoint**: Returns success response with `status='pending_approval'` instead of raising error
- **User-Friendly Messages**: Clear instructions to approve client in ISE GUI
- **Test Connection**: Checks account state and detects PENDING status
- **Status Updates**: Automatically updates to `connected` after approval when test connection succeeds

**UI Flow**:
1. User clicks "Save & Enable"
2. Account is created, status set to `pending_approval`
3. System shows: "pxGrid client account was created but is PENDING approval in ISE. Please approve it: Administration > pxGrid Services > Client Management > Clients."
4. Test Connection button remains enabled
5. User approves client in ISE
6. User clicks "Test Connection" → System verifies account is ENABLED and connects successfully

### 4. Configuration Management

**Database-Driven Configuration**:
- pxGrid configuration is stored in `connectors` table (`connector_id='ise_pxgrid'`)
- Configuration includes: hostname, username, password, client_name, port, use_ssl, verify_ssl, auth_method
- pxGrid service loads configuration from database on startup
- `/reload` endpoint allows reloading configuration without restart

**Centralized Certificate Management**:
- Certificates stored in global `certificates` table
- Certificates linked to connectors via `certificate_connector_references` table
- UI: Settings > Certificates for managing all certificates
- CSR generation support for certificate creation

### 5. Container Management

**Dynamic Container Control**:
- API service can trigger pxGrid service start/stop/reload via HTTP API
- `enable_connector` endpoint triggers pxGrid service `/reload` or `/start`
- `disable_connector` endpoint triggers pxGrid service `/stop`
- Container runs independently but controlled by main API

## File Structure

```
src/clarion/integration/
├── pxgrid_client.py          # pxGrid REST API client
└── pxgrid_subscriber.py      # Event subscriber and processor

services/pxgrid/
├── Dockerfile                # Container build file
└── pxgrid_service.py         # Standalone service entry point

src/clarion/api/routes/
├── connectors.py             # Connector management endpoints (includes pxGrid test/enable/disable)
└── certificates.py           # Certificate management endpoints

frontend/src/pages/connectors/
└── ISE.tsx                   # Combined ISE connector UI (ERS + pxGrid tabs)

docker-compose.yml            # Container definitions (pxgrid service)
```

## API Endpoints

### Connector Management (Main API)

- `POST /api/connectors/ise_pxgrid/configure` - Save pxGrid configuration
- `POST /api/connectors/ise_pxgrid/enable` - Enable pxGrid connector (creates account if needed, triggers service start)
- `POST /api/connectors/ise_pxgrid/disable` - Disable pxGrid connector (stops service)
- `POST /api/connectors/ise_pxgrid/test-connection` - Test pxGrid connection and check account status
- `GET /api/connectors/ise_pxgrid` - Get pxGrid connector configuration and status

### pxGrid Service API (Internal)

- `GET /health` - Health check
- `GET /status` - Get subscriber status and connection info
- `POST /start` - Start the pxGrid subscriber
- `POST /stop` - Stop the pxGrid subscriber
- `POST /reload` - Reload configuration from database and restart subscriber

## Configuration Flow

1. **Initial Setup**:
   - User navigates to Connectors > ISE > pxGrid tab
   - Fills in configuration form (ISE hostname, username, password, client name)
   - Selects authentication method (Username/Password or Certificate)
   - Clicks "Save & Enable"

2. **Account Creation**:
   - Backend calls `enable_connector` endpoint
   - pxGrid client attempts `AccountActivate` (if client exists)
   - If client doesn't exist, calls `AccountCreate` with ISE admin credentials
   - ISE returns bootstrap password
   - Bootstrap password is persisted in database config

3. **Account Approval**:
   - Account state is PENDING
   - User is prompted to approve in ISE GUI
   - Connector status set to `pending_approval`

4. **Connection**:
   - User approves client in ISE
   - User clicks "Test Connection"
   - System checks account state (should be ENABLED)
   - Authentication succeeds with client credentials
   - Connection verified, status updated to `connected`
   - pxGrid service is started/reloaded

5. **Ongoing Operation**:
   - pxGrid service subscribes to session and endpoint topics
   - Events are processed and database is updated
   - Real-time user/device information flows into Clarion

## Database Schema

### connectors Table
```sql
- connector_id: 'ise_pxgrid'
- config: JSON with {ise_hostname, username, password, client_name, port, use_ssl, verify_ssl, auth_method}
- enabled: 1 or 0
- status: 'disabled', 'pending_approval', 'connected', 'error'
- last_error: Error message if any
- last_connected: Timestamp of last successful connection
```

### certificates Table
- Stores client certificates, private keys, CA certificates
- Used by pxGrid when auth_method='certificate'

### certificate_connector_references Table
- Links certificates to connectors
- reference_type: 'client_cert' (for pxGrid)

## Current Status

### ✅ Completed
- pxGrid client implementation (REST API authentication)
- Account creation and activation flow
- Bootstrap password persistence
- Dual authentication support (username/password + certificates)
- PENDING approval handling with user-friendly messages
- Database-driven configuration
- Containerized service with HTTP control API
- UI integration (configuration form, test connection, enable/disable)
- Certificate management integration
- Event subscription framework (structure in place)

### 🚧 In Progress / Known Issues
- WebSocket/STOMP implementation for event subscription (currently REST-only)
- Full event processing pipeline (session/endpoint events)
- User database population from pxGrid events
- Current SGT assignment tracking

### 📝 Future Enhancements
- STOMP over WebSocket for pub/sub messaging (currently only REST API implemented)
- Complete event processing for session and endpoint events
- Real-time dashboard updates based on pxGrid events
- Certificate auto-rotation
- Multi-node ISE support (pxGrid cluster coordination)

## Testing Checklist

- [ ] Account creation with ISE admin credentials
- [ ] Bootstrap password capture and persistence
- [ ] Account approval flow (PENDING → ENABLED)
- [ ] Test connection after approval
- [ ] Certificate-based authentication
- [ ] Configuration save and reload
- [ ] Enable/disable connector
- [ ] Container start/stop/reload
- [ ] Error handling (invalid credentials, network errors)
- [ ] Status reporting (pending_approval, connected, error states)

## Troubleshooting

**Common Issues**:

1. **"Account is PENDING approval"**
   - Solution: Approve client in ISE: Administration > pxGrid Services > Client Management > Clients
   - Then click "Test Connection" again

2. **"Authentication failed with 401"**
   - Check: Are you using correct credentials?
   - For new clients: Use ISE admin credentials
   - For existing clients: Use client credentials (username=client_name, password=client_password)
   - Verify: pxGrid service is enabled on ISE
   - Check: Client has proper permissions (pxGrid Admin role)

3. **"Test Connection button is greyed out"**
   - Ensure configuration is saved first
   - Check that connector has a valid config in database

4. **"Container not starting"**
   - Check: `docker-compose logs pxgrid`
   - Verify: Configuration exists in database
   - Check: Network connectivity to ISE (port 8910)

## Configuration Parameters

**pxGrid Configuration**:
- `ise_hostname`: ISE hostname or IP address
- `client_name`: Unique pxGrid client name (e.g., "clarion")
- `username`: For username/password auth: ISE admin (for AccountCreate) or client_name (for Auth)
- `password`: ISE admin password (for AccountCreate) or bootstrap/client password (for Auth)
- `port`: pxGrid REST API port (default: 8910)
- `use_ssl`: Enable SSL/TLS (default: true)
- `verify_ssl`: Verify SSL certificates (default: false for self-signed)
- `auth_method`: 'username_password' or 'certificate'

**Environment Variables** (for pxGrid service):
- `CLARION_DB_PATH`: Database path (default: `/app/data/clarion.db`)
- `PXGRID_ISE_HOSTNAME`: ISE hostname (optional, uses DB config if available)
- `PORT`: pxGrid service HTTP API port (default: 9000)

## References

- Cisco ISE pxGrid REST API Documentation
- pxGrid SDK Sample Code
- Container deployment: `docs/DEPLOYMENT_ARCHITECTURE.md`
- Connector management: UI at `/connectors/ise` (pxGrid tab)

