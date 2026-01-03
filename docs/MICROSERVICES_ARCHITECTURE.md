# Clarion Microservices Architecture

## Overview

Clarion is designed as a **pure microservices architecture** with clear service boundaries, independent deployment, and modular design. Each service has a single responsibility and communicates via well-defined APIs.

## Architecture Principles

1. **Single Responsibility**: Each service has one clear purpose
2. **Independent Deployment**: Services can be deployed/updated independently
3. **Scalability**: Services scale independently based on load
4. **Resilience**: Service failures don't cascade
5. **API-First**: Services communicate via REST APIs and message queues
6. **Database per Service**: Each service owns its data (future: service-specific databases)

## Service Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                               │
│                      (clarion-frontend:3000)                           │
└────────────────────────────┬──────────────────────────────────────────┘
                              │ HTTP
                              │
┌────────────────────────────▼──────────────────────────────────────────┐
│                    API Gateway / Orchestrator                          │
│                    (clarion-gateway:8000)                              │
│                                                                         │
│  • Request routing                                                      │
│  • Authentication/Authorization                                         │
│  • Rate limiting                                                        │
│  • Request aggregation                                                  │
└──┬──────────┬──────────┬──────────┬──────────┬──────────┬─────────────┘
   │          │          │          │          │          │
   │ REST     │ REST     │ REST     │ REST     │ REST     │ REST
   │          │          │          │          │          │
┌──▼──┐  ┌───▼───┐  ┌───▼───┐  ┌───▼───┐  ┌───▼───┐  ┌───▼──────┐
│User │  │Policy │  │Cluster│  │Connect│  │ Data  │  │  pxGrid │
│Svc  │  │ Svc   │  │  Svc  │  │  Svc  │  │  Svc  │  │  Svc    │
└──┬──┘  └───┬───┘  └───┬───┘  └───┬───┘  └───┬───┘  └───┬──────┘
   │         │          │          │          │          │
   │         │          │          │          │          │
   └─────────┴──────────┴──────────┴──────────┴──────────┘
                              │
                    ┌─────────▼─────────┐
                    │   Message Queue   │
                    │   (Redis/RabbitMQ)│
                    └─────────┬─────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼──────┐      ┌───────▼──────┐      ┌───────▼──────┐
│  PostgreSQL  │      │    Vault      │      │    Neo4j      │
│ +TimescaleDB │      │  (Secrets)    │      │  (Graph DB)   │
└──────────────┘      └───────────────┘      └──────────────┘
```

## Service Definitions

### 1. API Gateway / Orchestrator Service (`clarion-gateway`)

**Purpose**: Single entry point for all client requests

**Port**: `8000`

**Responsibilities**:
- Request routing to appropriate microservices
- Authentication and authorization (JWT tokens)
- Rate limiting and throttling
- Request/response aggregation
- API versioning
- CORS handling
- Request logging and monitoring

**Dependencies**:
- All backend microservices
- Authentication service (future)

**Scaling**: Stateless, horizontal scaling

**Technology**: FastAPI with gateway pattern

---

### 2. User & Identity Service (`clarion-user-service`)

**Purpose**: User and identity management

**Port**: `8001`

**Responsibilities**:
- User CRUD operations
- User-device associations
- AD group memberships
- User SGT assignments
- Identity resolution (IP → User mapping)
- User traffic aggregation

**API Endpoints**:
- `GET /users` - List users
- `GET /users/{user_id}` - Get user details
- `POST /users` - Create user
- `PUT /users/{user_id}` - Update user
- `DELETE /users/{user_id}` - Delete user
- `GET /users/{user_id}/devices` - Get user devices
- `GET /users/{user_id}/sgt` - Get user SGT assignments
- `POST /identity/resolve` - Resolve identity from IP/MAC

**Dependencies**:
- PostgreSQL (user data)
- Message Queue (identity events)

**Scaling**: Stateless, horizontal scaling

---

### 3. Policy Service (`clarion-policy-service`)

**Purpose**: Policy management and recommendations

**Port**: `8002`

**Responsibilities**:
- Policy recommendation generation
- Policy impact analysis
- SGT lifecycle management
- Policy matrix management
- Policy export to ISE
- Policy customization

**API Endpoints**:
- `GET /policies` - List policies
- `GET /policies/{policy_id}` - Get policy details
- `POST /policies/recommend` - Generate recommendations
- `POST /policies/{policy_id}/analyze` - Analyze policy impact
- `POST /policies/{policy_id}/export` - Export to ISE
- `GET /sgt` - List SGTs
- `POST /sgt` - Create SGT
- `PUT /sgt/{sgt_id}` - Update SGT

**Dependencies**:
- PostgreSQL (policy data)
- Clustering Service (for recommendations)
- Connector Service (for ISE export)

**Scaling**: Stateless, horizontal scaling

---

### 4. Clustering Service (`clarion-clustering-service`)

**Purpose**: Endpoint clustering and categorization

**Port**: `8003`

**Responsibilities**:
- HDBSCAN clustering operations
- Feature extraction from flow data
- Incremental clustering
- Cluster labeling and semantic naming
- Confidence scoring
- Cluster explanations
- SGT mapping to clusters

**API Endpoints**:
- `POST /clustering/run` - Run clustering job
- `POST /clustering/incremental` - Incremental cluster assignment
- `GET /clustering/{cluster_id}` - Get cluster details
- `GET /clustering/{cluster_id}/explain` - Get cluster explanation
- `POST /clustering/{cluster_id}/label` - Label cluster
- `POST /clustering/{cluster_id}/sgt` - Map cluster to SGT

**Dependencies**:
- PostgreSQL (flow data, cluster data)
- Message Queue (clustering jobs)

**Scaling**: Can scale horizontally for parallel clustering jobs

**Technology**: FastAPI + scikit-learn + HDBSCAN

---

### 5. Connector Service (`clarion-connector-service`)

**Purpose**: External system integrations (ISE, AD, IoT)

**Port**: `8004`

**Responsibilities**:
- ISE ERS API integration
- AD connector (future)
- IoT connector (future)
- Connector configuration management
- Certificate management
- Connector health monitoring

**API Endpoints**:
- `GET /connectors` - List connectors
- `GET /connectors/{connector_id}` - Get connector details
- `POST /connectors/{connector_id}/configure` - Configure connector
- `POST /connectors/{connector_id}/enable` - Enable connector
- `POST /connectors/{connector_id}/disable` - Disable connector
- `POST /connectors/{connector_id}/test` - Test connection
- `GET /connectors/{connector_id}/status` - Get connector status
- `POST /ise/deploy` - Deploy policies to ISE
- `GET /ise/sync` - Sync ISE configuration

**Dependencies**:
- PostgreSQL (connector config)
- Vault (credentials, certificates)
- ISE ERS API (external)
- AD (future, external)

**Scaling**: Stateless, horizontal scaling

---

### 6. Data Ingestion Service (`clarion-data-service`)

**Purpose**: Data ingestion and processing

**Port**: `8005`

**Responsibilities**:
- NetFlow data ingestion
- Flow data processing
- Sketch building (Count-Min, HyperLogLog)
- Data aggregation
- Data quality checks
- Data archiving

**API Endpoints**:
- `POST /data/netflow` - Ingest NetFlow data
- `POST /data/flows` - Ingest flow data
- `GET /data/quality` - Get data quality metrics
- `POST /data/aggregate` - Aggregate data
- `GET /data/sketches` - Get data sketches

**Dependencies**:
- PostgreSQL + TimescaleDB (flow data)
- Message Queue (data events)

**Scaling**: Stateless, horizontal scaling

---

### 7. pxGrid Service (`clarion-pxgrid-service`)

**Purpose**: ISE pxGrid integration (already exists)

**Port**: `9000`

**Responsibilities**:
- ISE pxGrid connection
- Real-time event subscription
- Event processing
- Publishing events to message queue

**API Endpoints**:
- `GET /health` - Health check
- `GET /status` - Service status
- `POST /start` - Start pxGrid subscriber
- `POST /stop` - Stop pxGrid subscriber
- `POST /reload` - Reload configuration

**Dependencies**:
- PostgreSQL (session data)
- Vault (credentials, certificates)
- Message Queue (publish events)
- ISE pxGrid (external)

**Scaling**: Single instance (stateful connection)

---

## Service Communication

### Synchronous Communication (REST)

Services communicate via REST APIs for request/response patterns:

```
Gateway → Service (REST)
Service → Service (REST)
```

**Example**:
```python
# Gateway calls Policy Service
response = requests.get("http://policy-service:8002/policies")
```

### Asynchronous Communication (Message Queue)

Services publish/subscribe to events via message queue:

```
pxGrid Service → Queue → User Service (user events)
pxGrid Service → Queue → Data Service (session events)
Clustering Service → Queue → Policy Service (cluster updates)
```

**Message Queue Topics**:
- `user.events` - User login/logout events
- `session.events` - ISE session events
- `endpoint.events` - Endpoint events
- `cluster.updates` - Cluster updates
- `policy.changes` - Policy changes
- `data.flows` - Flow data events

---

## Database Strategy

### Current (Shared Database)
- All services share PostgreSQL database
- Service-specific schemas/tables
- Allows for ACID transactions across services

### Future (Database per Service)
- Each service has its own database
- Services own their data
- Better isolation and scalability
- Eventual consistency between services

---

## Deployment

### Docker Compose (Development)
```yaml
services:
  gateway:
    # API Gateway
  user-service:
    # User Service
  policy-service:
    # Policy Service
  clustering-service:
    # Clustering Service
  connector-service:
    # Connector Service
  data-service:
    # Data Service
  pxgrid-service:
    # pxGrid Service
  postgres:
    # Database
  redis:
    # Message Queue
  vault:
    # Secrets Management
```

### Kubernetes (Production)
- Each service as a Deployment
- Service discovery via Kubernetes Services
- ConfigMaps for configuration
- Secrets for sensitive data
- Horizontal Pod Autoscaling

---

## Benefits of This Architecture

1. **Modularity**: Clear service boundaries
2. **Scalability**: Scale services independently
3. **Resilience**: Service failures are isolated
4. **Technology Diversity**: Use best tool for each service
5. **Team Autonomy**: Teams can work on services independently
6. **Deployment Flexibility**: Deploy services independently
7. **Testing**: Easier to test services in isolation

---

## Migration Path

1. **Phase 1**: Extract services one by one
2. **Phase 2**: Implement API Gateway
3. **Phase 3**: Add message queue for async communication
4. **Phase 4**: Move to database per service
5. **Phase 5**: Add service mesh (Istio/Linkerd) for advanced routing

---

## Service Dependencies

```
Gateway → All Services
Policy Service → Clustering Service
Policy Service → Connector Service
User Service → Data Service (for identity resolution)
Data Service → Clustering Service (for clustering jobs)
pxGrid Service → User Service (via message queue)
pxGrid Service → Data Service (via message queue)
All Services → PostgreSQL
All Services → Vault (for secrets)
```

---

## Next Steps

1. Create service structure and Dockerfiles
2. Extract services from monolithic API
3. Implement API Gateway
4. Add message queue (Redis/RabbitMQ)
5. Update docker-compose.yml
6. Add service discovery
7. Implement health checks and monitoring

