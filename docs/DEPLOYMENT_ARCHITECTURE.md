# Clarion Deployment Architecture

## Overview

Clarion is designed as a containerized microservices architecture, allowing for:
- **Independent scaling** of services
- **Isolated certificate management** for pxGrid integration
- **Independent deployment** and updates
- **Clear separation of concerns**

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Frontend Service                                      │
│                    (clarion-frontend:3000)                                   │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  React Application (nginx)                                         │    │
│  │  • Serves static build files                                       │    │
│  │  • Proxies /api requests to backend                                │    │
│  │  • SPA routing support                                             │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │ HTTP/REST (via nginx proxy)
                             │
┌────────────────────────────▼────────────────────────────────────────────────┐
│                        Main API Service                                      │
│                    (clarion-api:8000)                                        │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  FastAPI Application                                                │    │
│  │  • REST API endpoints                                               │    │
│  │  • Device/Cluster/User management                                   │    │
│  │  • Policy recommendations                                           │    │
│  │  • ISE ERS API integration                                          │    │
│  │  • Database access (SQLite/PostgreSQL)                              │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                │ HTTP/REST               │ Message Queue (Future)
                │                         │
┌───────────────▼──────────┐  ┌──────────▼──────────────────────────────────┐
│    pxGrid Service        │  │   Database Service                          │
│  (clarion-pxgrid:9000)   │  │   (PostgreSQL - Future)                     │
│                          │  │   or Shared SQLite volume                   │
│  ┌────────────────────┐  │  └────────────────────────────────────────────┘
│  │ pxGrid Subscriber  │  │
│  │ • ISE Connection   │  │  ┌──────────────────────────────────────────┐
│  │ • Certificate Auth │  │  │   Shared Storage                         │
│  │ • Event Processing │  │  │   (Volumes/Secrets)                      │
│  │ • Database Updates │  │  │   • Database files                       │
│  └────────────────────┘  │  │   • pxGrid certificates                  │
│                          │  │   • Configuration files                   │
│  ┌────────────────────┐  │  └──────────────────────────────────────────┘
│  │ HTTP API           │  │
│  │ • Status endpoint  │  │
│  │ • Control endpoint │  │
│  └────────────────────┘  │
└──────────────────────────┘
```

## Service Architecture

### 1. Frontend Service (`clarion-frontend`)

**Purpose**: React frontend served via nginx

**Container**: `clarion-frontend:latest`

**Responsibilities**:
- Serve React application (static files)
- Proxy API requests to backend service
- Handle SPA routing (client-side routing)
- Serve static assets with caching

**Ports**:
- `3000` - HTTP (nginx)

**Dependencies**:
- Main API Service (for proxied API requests)

**Configuration**:
- `VITE_API_URL` - API URL for build-time configuration
- nginx configuration for API proxying

**Scaling**: Stateless (can scale horizontally behind load balancer)

**Production Build**:
- Multi-stage build (Node.js build + nginx serve)
- Optimized static assets
- Gzip compression enabled

**Development Mode**:
- Vite dev server with hot module replacement
- Source code mounted as volumes
- Fast refresh for development

---

### 2. Main API Service (`clarion-api`)

**Purpose**: Primary REST API for the Clarion application

**Container**: `clarion-api:latest`

**Responsibilities**:
- All REST API endpoints (devices, clusters, users, policies, etc.)
- Database access (read/write)
- ISE ERS API integration (policy deployment, config sync)
- Business logic (clustering, recommendations, etc.)
- Frontend serving (optional - can be separate)

**Ports**:
- `8000` - HTTP API

**Dependencies**:
- Database (SQLite file or PostgreSQL connection)
- Optional: Message queue for pxGrid events

**Configuration**:
- Database path/connection string
- CORS settings
- ISE ERS API credentials (environment variables or secrets)

**Scaling**: Stateless (can scale horizontally with shared database)

---

### 3. pxGrid Service (`clarion-pxgrid`)

**Purpose**: ISE pxGrid integration with certificate-based authentication

**Container**: `clarion-pxgrid:latest`

**Responsibilities**:
- Connect to ISE pxGrid using certificate authentication
- Subscribe to pxGrid topics (session, endpoint events)
- Process and parse ISE events
- Update shared database with session data
- Provide status/control API

**Ports**:
- `9000` - Status/Control HTTP API (optional)

**Dependencies**:
- Database (shared SQLite file or PostgreSQL connection)
- pxGrid certificates (mounted as secrets/volumes)
- ISE pxGrid connection details

**Configuration**:
- ISE hostname
- Client name
- Certificate paths
- Database path/connection string

**Scaling**: Single instance (pxGrid connection is stateful)

**Security**:
- Certificates stored as Docker secrets or mounted volumes
- No credentials in environment variables
- Isolated from main API service

---

### 4. Database Service (Future)

**Purpose**: Centralized database for all services

**Container**: `postgresql:latest` (or `timescaledb:latest`)

**Responsibilities**:
- Store all Clarion data
- Time-series optimization (TimescaleDB)
- Shared access for API and pxGrid services

**Ports**:
- `5432` - PostgreSQL

**Scaling**: Single instance (can be replicated for HA)

---

## Service Communication

### Current (Simple HTTP)

```
Frontend (nginx) ──HTTP (proxy)──> Main API Service
Main API Service ──HTTP──> pxGrid Service (control/status)
pxGrid Service ──Direct DB──> Database
Main API Service ──Direct DB──> Database
Frontend ──Direct HTTP──> Main API Service (via nginx proxy)
```

### Future (Message Queue)

```
Frontend (nginx) ──HTTP──> Main API Service
Main API Service ──HTTP/REST──> pxGrid Service (control)
pxGrid Service ──Messages──> Message Queue (Redis/RabbitMQ)
Main API Service ──Messages──> Message Queue (consumes events)
pxGrid Service ──Direct DB──> Database (writes)
Main API Service ──Direct DB──> Database (reads/writes)
```

**Message Queue Benefits**:
- Decoupled services
- Event replay capability
- Better scalability
- Async event processing

---

## Certificate Management Strategy

### pxGrid Certificates

pxGrid requires client certificates for authentication. Certificate management options:

#### Option 1: Docker Secrets (Recommended for Production)

```yaml
services:
  pxgrid:
    secrets:
      - pxgrid_client_cert
      - pxgrid_client_key
      - pxgrid_ca_cert
```

**Benefits**:
- Encrypted at rest
- Only accessible to pxGrid service
- Managed by Docker/Kubernetes

#### Option 2: Mounted Volumes (Development/Testing)

```yaml
services:
  pxgrid:
    volumes:
      - ./certs/pxgrid:/etc/pxgrid/certs:ro
```

**Benefits**:
- Easy for development
- Direct file access
- Simple to update

#### Option 3: Kubernetes Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: pxgrid-certificates
type: Opaque
data:
  client.crt: <base64-encoded>
  client.key: <base64-encoded>
  ca.crt: <base64-encoded>
```

---

## Deployment Options

### Development (docker-compose)

- All services in single compose file
- Shared volumes for database
- Easy local development
- Certificate files mounted from host

### Production (Kubernetes)

- Separate deployments for each service
- Secrets for certificates
- ConfigMaps for configuration
- Persistent volumes for database
- Service mesh for inter-service communication (optional)

### Hybrid

- Main API: Containerized
- pxGrid: Separate container with certificates
- Database: Managed service (RDS, Cloud SQL, etc.)
- Frontend: CDN or separate container

---

## Container Images

### Frontend Service

**Base Image**: `node:20-alpine` (build) + `nginx:alpine` (production)

**Build Stages**:
1. **Builder**: Node.js environment, installs dependencies, builds React app
2. **Production**: nginx alpine image, serves static files

**Includes**:
- React application (built static files)
- nginx configuration
- API proxy configuration

**Build Context**: `frontend/` directory

**Entrypoint**: `nginx -g daemon off;` (production)
**Development**: `npm run dev` (Vite dev server with hot reload)

**Environment Variables**:
- `VITE_API_URL` - Backend API URL (build-time)

---

### Main API Service

**Base Image**: `python:3.11-slim`

**Includes**:
- Python 3.11+
- All Python dependencies
- Clarion application code
- uvicorn ASGI server

**Build Context**: Project root

**Entrypoint**: `uvicorn clarion.api.app:app --host 0.0.0.0 --port 8000`

### pxGrid Service

**Base Image**: `python:3.11-slim`

**Includes**:
- Python 3.11+
- pxGrid dependencies (websocket-client, requests, etc.)
- Clarion pxGrid subscriber code
- HTTP status API (optional)

**Build Context**: Project root (shared codebase)

**Entrypoint**: `python -m clarion.integration.pxgrid_service`

**Special Considerations**:
- Certificate files mounted at runtime
- Isolated from main API
- Single instance (pxGrid connection is stateful)

---

## Data Persistence

### SQLite (Current)

**Volume Mount**: Shared between API and pxGrid services

```yaml
volumes:
  clarion-db:
    driver: local

services:
  api:
    volumes:
      - clarion-db:/app/data
  
  pxgrid:
    volumes:
      - clarion-db:/app/data
```

**Pros**:
- Simple for development
- No additional service needed
- File-based (easy backup)

**Cons**:
- Single-writer limitation
- Not ideal for concurrent access
- Limited scalability

### PostgreSQL (Future)

**Separate Service**: PostgreSQL/TimescaleDB container

```yaml
services:
  postgres:
    image: timescale/timescaledb:latest-pg14
    volumes:
      - postgres-data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: clarion
      POSTGRES_USER: clarion
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
```

**Pros**:
- Multi-writer support
- Better concurrency
- Time-series optimization
- Better scalability

**Cons**:
- Additional service to manage
- More complex deployment

---

## Network Architecture

### Internal Network

All services communicate over an internal Docker network:

```yaml
networks:
  clarion-network:
    driver: bridge
```

**Services on network**:
- `clarion-frontend`
- `clarion-api`
- `clarion-pxgrid`
- `postgres` (if used)
- `redis` (if message queue used)

**External Access**:
- Frontend: Exposed on host port 3000 (nginx)
- Main API: Exposed on host port 8000 (optional, also accessible via frontend proxy)
- pxGrid Service: Optional status endpoint (internal only)

---

## Security Considerations

### Certificate Isolation

- pxGrid certificates only accessible to pxGrid service
- No credentials in environment variables (use secrets)
- Read-only certificate mounts where possible

### Network Isolation

- Services communicate over internal network
- Only necessary ports exposed to host
- pxGrid service not directly exposed (internal only)

### Database Security

- Database credentials via secrets
- Network isolation (internal network only)
- Encrypted connections (PostgreSQL SSL)

---

## Monitoring and Health Checks

### Health Endpoints

**Frontend**: `GET /health` (nginx health check)

**Main API**: `GET /api/health`

**pxGrid Service**: `GET /health` (optional internal endpoint)

### Docker Health Checks

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

---

## Deployment Sequence

1. **Database** (if PostgreSQL): Start first
2. **Main API Service**: Start after database
3. **pxGrid Service**: Start after database (optional - can start independently)

### Dependencies

```
Database ──> Main API Service
Database ──> pxGrid Service
Main API Service ──> Frontend (for API requests)
```

---

## Migration Path

### Phase 1: Current (Monolithic)
- Single process: API + pxGrid (if needed)
- SQLite database
- Development mode

### Phase 2: Containerized (This Architecture)
- Main API service containerized
- pxGrid service in separate container
- Shared SQLite volume
- docker-compose deployment

### Phase 3: Production Ready
- PostgreSQL database service
- Kubernetes deployment
- Secrets management
- Message queue for events
- Monitoring and logging

---

## Benefits of This Architecture

1. **Security**: Certificate isolation in pxGrid container
2. **Scalability**: Independent scaling of services
3. **Maintainability**: Clear separation of concerns
4. **Deployment**: Independent updates and rollbacks
5. **Development**: Easy local development with docker-compose
6. **Production**: Ready for Kubernetes deployment

