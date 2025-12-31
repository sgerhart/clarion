# Clarion Deployment Guide

## Overview

Clarion can be deployed as a containerized microservices architecture, with separate containers for the main API and pxGrid integration service.

## Architecture

See [docs/DEPLOYMENT_ARCHITECTURE.md](docs/DEPLOYMENT_ARCHITECTURE.md) for detailed architecture documentation.

**Services**:
- **api**: Main FastAPI backend (port 8000)
- **pxgrid**: ISE pxGrid integration service (port 9000 - status API)
- **postgres**: PostgreSQL database (optional - can use SQLite)
- **redis**: Redis for message queue (optional - future)

## Quick Start

### Prerequisites

- Docker and Docker Compose
- pxGrid certificates (if using certificate authentication)

### Basic Deployment (SQLite)

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

This will:
- Start the main API service on port 8000
- Start the pxGrid service (if configured)
- Use SQLite database (shared volume)

### With PostgreSQL

```bash
# Start with PostgreSQL profile
docker-compose --profile postgres up -d
```

### Development Mode

```bash
# Start with development overrides (hot reload, source mounts)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## Configuration

### Environment Variables

#### Main API Service

| Variable | Default | Description |
|----------|---------|-------------|
| `CLARION_DB_PATH` | `/app/data/clarion.db` | Path to SQLite database |
| `PYTHONPATH` | `/app/src` | Python path |

#### pxGrid Service

| Variable | Default | Description |
|----------|---------|-------------|
| `PXGRID_ISE_HOSTNAME` | `192.168.10.31` | ISE server hostname |
| `PXGRID_CLIENT_NAME` | `clarion-pxgrid-client` | pxGrid client name |
| `PXGRID_USERNAME` | - | pxGrid username (if password auth) |
| `PXGRID_PASSWORD` | - | pxGrid password (if password auth) |
| `PXGRID_USE_SSL` | `true` | Use SSL/TLS |
| `PXGRID_VERIFY_SSL` | `false` | Verify SSL certificates |
| `PXGRID_PORT` | `8910` | pxGrid REST API port |
| `PXGRID_CERT_DIR` | `/app/certs` | Certificate directory |

### Certificate Setup (pxGrid)

1. Generate or obtain pxGrid client certificates
2. Place certificates in `certs/pxgrid/`:
   ```
   certs/pxgrid/
   ├── client.crt    # Client certificate
   ├── client.key    # Client private key
   └── ca.crt        # CA certificate (optional)
   ```
3. Certificates will be mounted into the pxGrid container at `/app/certs`

**Note**: Certificate-based authentication is required for pxGrid in production ISE deployments.

### Using Environment File

Create a `.env` file:

```bash
# ISE Configuration
PXGRID_ISE_HOSTNAME=192.168.10.31
PXGRID_CLIENT_NAME=clarion-pxgrid-client
PXGRID_USERNAME=admin
PXGRID_PASSWORD=your_password

# Database
POSTGRES_PASSWORD=secure_password
```

Then run:
```bash
docker-compose --env-file .env up -d
```

## Building Images

### Build All Services

```bash
docker-compose build
```

### Build Specific Service

```bash
docker-compose build api
docker-compose build pxgrid
```

## Database

### SQLite (Default)

- Database stored in Docker volume: `clarion-db`
- Shared between API and pxGrid services
- Simple for development

### PostgreSQL (Production)

To use PostgreSQL:

```bash
docker-compose --profile postgres up -d
```

**Note**: You'll need to update the application code to use PostgreSQL connection strings instead of SQLite paths.

## Service Communication

- **Frontend → API**: HTTP on port 8000
- **API → pxGrid**: HTTP on port 9000 (status/control endpoints)
- **pxGrid → Database**: Direct file access (SQLite) or PostgreSQL connection
- **API → Database**: Direct file access (SQLite) or PostgreSQL connection

## Health Checks

### API Service

```bash
curl http://localhost:8000/api/health
```

### pxGrid Service

```bash
curl http://localhost:9000/health
```

## Monitoring

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f pxgrid
```

### Service Status

```bash
# List running containers
docker-compose ps

# Service health
docker-compose ps --format json | jq '.[] | {name: .Name, status: .State}'
```

## Troubleshooting

### pxGrid Connection Issues

1. **Check certificates are mounted**:
   ```bash
   docker-compose exec pxgrid ls -la /app/certs
   ```

2. **Check pxGrid service logs**:
   ```bash
   docker-compose logs pxgrid
   ```

3. **Test pxGrid status**:
   ```bash
   curl http://localhost:9000/status
   ```

### Database Issues

1. **Check database volume**:
   ```bash
   docker volume inspect clarion-db
   ```

2. **Check database file**:
   ```bash
   docker-compose exec api ls -la /app/data/
   ```

### Port Conflicts

If ports 8000 or 9000 are already in use, modify `docker-compose.yml`:

```yaml
services:
  api:
    ports:
      - "8001:8000"  # Change host port
  
  pxgrid:
    ports:
      - "9001:9000"  # Change host port
```

## Production Deployment

### Using Docker Secrets (Recommended)

1. Create secrets:
   ```bash
   docker secret create pxgrid_client_cert certs/pxgrid/client.crt
   docker secret create pxgrid_client_key certs/pxgrid/client.key
   docker secret create pxgrid_ca_cert certs/pxgrid/ca.crt
   ```

2. Update `docker-compose.yml` to use secrets (see commented section)

3. Deploy with secrets:
   ```bash
   docker stack deploy -c docker-compose.yml clarion
   ```

### Kubernetes Deployment

See `deploy/k8s/` directory for Kubernetes manifests (to be created).

### Security Best Practices

1. **Certificates**: Use Docker secrets or Kubernetes secrets
2. **Passwords**: Use environment files or secrets management
3. **Network**: Use internal networks, limit exposed ports
4. **Database**: Use managed database service (RDS, Cloud SQL)
5. **TLS**: Use TLS for all external-facing services

## Scaling

### API Service (Stateless)

The API service is stateless and can be scaled horizontally:

```bash
docker-compose up -d --scale api=3
```

### pxGrid Service (Stateful)

The pxGrid service is stateful (maintains pxGrid connection) and should run as a single instance.

## Backup and Recovery

### SQLite Database

```bash
# Backup
docker-compose exec api cp /app/data/clarion.db /app/data/clarion.db.backup

# Copy from container
docker cp clarion-api:/app/data/clarion.db ./backup/
```

### PostgreSQL

```bash
# Backup
docker-compose exec postgres pg_dump -U clarion clarion > backup.sql

# Restore
docker-compose exec -T postgres psql -U clarion clarion < backup.sql
```

## Next Steps

- See [docs/DEPLOYMENT_ARCHITECTURE.md](docs/DEPLOYMENT_ARCHITECTURE.md) for detailed architecture
- See [docs/ISE_INTEGRATION.md](docs/ISE_INTEGRATION.md) for ISE integration details
- See [README.md](README.md) for general project information

