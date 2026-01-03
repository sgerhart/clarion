# Clarion Data Strategy

## Overview

Clarion requires a comprehensive data strategy to handle diverse data types from multiple sources, support two distinct graph models, enable AI/LLM integration with RAG, and scale to enterprise deployments. This document defines the complete data architecture and storage strategy.

---

## Data Types & Sources

### 1. **Network Flow Data**
- **Sources**: NetFlow v5/v9/IPFIX, sFlow, Cloud Flow Logs (AWS, Azure, GCP)
- **Volume**: High (100M+ flows/hour at enterprise scale)
- **Characteristics**: Time-series, high write throughput, temporal queries
- **Storage**: TimescaleDB (PostgreSQL extension)

### 2. **Network Topology Data**
- **Sources**: SNMP, Device APIs (RESTCONF, NETCONF), Configuration parsing, LLDP/CDP
- **Volume**: Medium (thousands of devices, millions of connections)
- **Characteristics**: Graph structure, relatively static, relationship-heavy
- **Storage**: Neo4j (Topology Graph)

### 3. **Identity Data**
- **Sources**: ISE pxGrid, Active Directory, Cloud IAM
- **Volume**: Medium (millions of users, devices, sessions)
- **Characteristics**: Relational, frequent updates, correlation-heavy
- **Storage**: PostgreSQL (relational tables)

### 4. **Configuration Data**
- **Sources**: Device configurations (Cisco, Juniper, Palo Alto, Fortinet, etc.)
- **Volume**: Low-Medium (thousands of devices, periodic updates)
- **Characteristics**: Text-based, vendor-specific, versioned
- **Storage**: PostgreSQL (JSON/Text columns) + Vector Database (for RAG)

### 5. **Policy Data**
- **Sources**: Generated policies, ISE policies, Firewall rules, Cloud security groups
- **Volume**: Low (hundreds to thousands of policies)
- **Characteristics**: Structured, versioned, relationship-heavy
- **Storage**: PostgreSQL (relational) + Neo4j (Policy Graph)

### 6. **Behavioral Data**
- **Sources**: Edge sketches, clustering results, behavioral patterns
- **Volume**: Medium (millions of endpoints, periodic updates)
- **Characteristics**: Probabilistic data structures, aggregated
- **Storage**: PostgreSQL (TimescaleDB for time-series behavioral data)

### 7. **AI/LLM Context Data**
- **Sources**: Cluster descriptions, policy justifications, historical decisions, documentation
- **Volume**: Low-Medium (grows with usage)
- **Characteristics**: Text, embeddings, semantic search
- **Storage**: Vector Database (Chroma, Qdrant, or Pinecone)

---

## Dual Graph Architecture

Clarion requires **two distinct graph models** in Neo4j, each serving different purposes:

### Graph 1: Network Flow Graph (Behavioral Relationships)

**Purpose**: Model observed network behavior and communication patterns

**Nodes:**
- `Endpoint` (IP/MAC addresses)
- `User` (identity)
- `Service` (ports, protocols)
- `Cluster` (behavioral groups)
- `SGT` (Security Group Tags)

**Edges:**
- `FLOWS_TO` (endpoint → endpoint, with metadata: bytes, packets, ports, protocol, timestamp)
- `ASSIGNED_TO` (user → endpoint, with confidence score)
- `MEMBER_OF` (endpoint → cluster, with confidence score)
- `TAGGED_WITH` (endpoint → SGT, with assignment history)
- `COMMUNICATES_WITH` (SGT → SGT, aggregated flow patterns)

**Use Cases:**
- User → Device → App relationship visualization
- SGT-to-SGT communication pattern analysis
- Blast radius analysis (what can be reached from compromised SGT)
- Behavioral anomaly detection
- Policy impact analysis

**Update Frequency**: Real-time (as flows arrive)

**Example Query:**
```cypher
// Find all endpoints that communicate with a specific SGT
MATCH (sgt:SGT {value: 10})<-[:TAGGED_WITH]-(ep1:Endpoint)
MATCH (ep1)-[f:FLOWS_TO]->(ep2:Endpoint)
MATCH (ep2)-[:TAGGED_WITH]->(sgt2:SGT)
RETURN ep1, ep2, sgt2, sum(f.bytes) as total_bytes
ORDER BY total_bytes DESC
```

---

### Graph 2: Network Topology Graph (Infrastructure Relationships)

**Purpose**: Model physical and logical network infrastructure

**Nodes:**
- `Device` (switches, routers, firewalls, endpoints)
- `Interface` (device interfaces)
- `Subnet` (network segments)
- `VLAN` (virtual LANs)
- `Zone` (firewall security zones)
- `Location` (physical locations: campus, building, IDF)

**Edges:**
- `CONNECTED_TO` (device → device, physical links)
- `HAS_INTERFACE` (device → interface)
- `CONNECTED_VIA` (interface → interface, logical connections)
- `ROUTES_TO` (router → subnet, routing relationships)
- `LOCATED_AT` (device → location)
- `ENFORCES_POLICY` (device → policy, policy enforcement points)
- `MEMBER_OF` (subnet → VLAN, interface → zone)

**Use Cases:**
- Attack path mapping (trace paths through network infrastructure)
- Policy enforcement point identification
- Network path discovery (find all paths from source to destination)
- Policy gap detection (identify paths without policy enforcement)
- Critical device identification
- Multi-hop attack scenarios

**Update Frequency**: Periodic (as topology changes, via discovery)

**Example Query:**
```cypher
// Find all network paths from source device to destination device
MATCH path = (src:Device {hostname: 'switch-1'})-[:CONNECTED_TO*..10]->(dst:Device {hostname: 'server-1'})
RETURN path
ORDER BY length(path)
```

---

## Data Storage Architecture

### 1. PostgreSQL + TimescaleDB (Primary Database)

**Purpose**: Time-series data, relational data, metadata

**Tables:**
- **Time-Series (TimescaleDB Hypertables):**
  - `flows` - Network flow data (partitioned by time)
  - `sessions` - ISE pxGrid session data
  - `behavioral_sketches` - Edge sketch data over time
  
- **Relational:**
  - `users` - User identity data
  - `devices` - Device metadata
  - `clusters` - Cluster definitions
  - `sgt_registry` - SGT definitions
  - `policies` - Policy definitions
  - `connectors` - Connector configurations
  - `locations` - Location hierarchy
  - `subnets` - Subnet definitions
  - `switches` - Switch metadata
  - `routers` - Router metadata
  - `firewalls` - Firewall metadata

- **Configuration (JSON/Text):**
  - `device_configurations` - Device configs (vendor-specific)
  - `policy_configurations` - Policy configs (vendor-specific)

**Benefits:**
- ACID transactions
- SQL interface
- Time-series optimization (TimescaleDB)
- Complex joins
- JSON support for flexible schemas

---

### 2. Neo4j (Dual Graph Database)

**Purpose**: Relationship storage for both flow graph and topology graph

**Graph 1: Flow Graph**
- Nodes: Endpoint, User, Service, Cluster, SGT
- Edges: FLOWS_TO, ASSIGNED_TO, MEMBER_OF, TAGGED_WITH, COMMUNICATES_WITH

**Graph 2: Topology Graph**
- Nodes: Device, Interface, Subnet, VLAN, Zone, Location
- Edges: CONNECTED_TO, HAS_INTERFACE, CONNECTED_VIA, ROUTES_TO, LOCATED_AT, ENFORCES_POLICY

**Benefits:**
- Native graph operations (traversal, path finding)
- Separate graph models for different purposes
- Graph queries (Cypher)
- Relationship visualization

**Implementation:**
- Use Neo4j labels to separate graph types: `:FlowGraph` and `:TopologyGraph`
- Or use separate Neo4j databases/instances if needed for isolation
- Graph merging from edge agents (Flow Graph only)

---

### 3. Vector Database (RAG Context)

**Purpose**: Store embeddings for AI/LLM context retrieval

**Technology Options:**
- **Chroma** (open-source, embedded)
- **Qdrant** (open-source, high-performance)
- **Pinecone** (managed, cloud-native)
- **Weaviate** (open-source, graph + vector)

**Data Stored:**
- **Cluster descriptions** - Text descriptions of behavioral clusters
- **Policy justifications** - Human-readable policy explanations
- **Historical decisions** - Past clustering and policy decisions with context
- **Device configuration snippets** - Relevant config sections for context
- **Documentation** - System documentation, vendor docs
- **User feedback** - User corrections and explanations

**Embeddings:**
- Use embedding models (e.g., `sentence-transformers`, OpenAI `text-embedding-ada-002`)
- Store embeddings alongside metadata (cluster_id, policy_id, device_id, etc.)
- Enable semantic search for RAG context retrieval

**Use Cases:**
- **RAG for AI agents** - Provide context to LLMs for better responses
- **Similar cluster discovery** - Find similar clusters for recommendations
- **Policy pattern matching** - Find similar policies from history
- **Configuration analysis** - Find similar device configurations

**Example:**
```python
# Store cluster description with embedding
cluster_description = "Corporate laptops accessing web services and file servers"
embedding = embedding_model.encode(cluster_description)

vector_db.store(
    id=f"cluster_{cluster_id}",
    embedding=embedding,
    metadata={
        "cluster_id": cluster_id,
        "sgt": sgt_value,
        "endpoint_count": endpoint_count,
        "description": cluster_description
    }
)

# RAG retrieval for AI agent
similar_clusters = vector_db.search(
    query_embedding=query_embedding,
    top_k=5,
    filter={"sgt": sgt_value}  # Optional filtering
)
```

---

### 4. Redis (Caching & Buffering)

**Purpose**: High-speed caching and message buffering

**Use Cases:**
- **Flow data buffering** - Buffer flows before batch insert to TimescaleDB
- **Graph query caching** - Cache frequent graph traversal results
- **Identity correlation cache** - Cache IP → User mappings
- **Session data** - Temporary session storage
- **Rate limiting** - API rate limiting counters

---

### 5. Object Storage / Data Lake (Long-term Archive)

**Purpose**: Cost-effective long-term storage for analytics and ML training

**Technology**: S3, Azure Blob, GCP Cloud Storage + Parquet format

**Data Stored:**
- **Historical flows** - Compressed flow data beyond retention period
- **Configuration snapshots** - Versioned device configurations
- **Policy history** - Historical policy changes
- **Training data** - ML model training datasets

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA INGESTION LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  NetFlow ──┐                                                    │
│  sFlow ────┼──▶ Collector ──▶ Redis Buffer ──▶ TimescaleDB     │
│  Cloud ────┘                                                    │
│                                                                  │
│  ISE pxGrid ──▶ pxGrid Service ──▶ PostgreSQL (Identity)       │
│                                                                  │
│  AD ──▶ AD Connector ──▶ PostgreSQL (Identity)                  │
│                                                                  │
│  SNMP/API ──▶ Discovery Service ──▶ Neo4j (Topology Graph)      │
│                                                                  │
│  Configs ──▶ Config Parser ──▶ PostgreSQL + Vector DB          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PROCESSING LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Flow Processing ──▶ Behavioral Sketches ──▶ Clustering         │
│                                                                  │
│  Clustering Results ──▶ Neo4j (Flow Graph)                      │
│                                                                  │
│  Topology Discovery ──▶ Neo4j (Topology Graph)                  │
│                                                                  │
│  Identity Correlation ──▶ PostgreSQL + Neo4j (Flow Graph)      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AI/LLM LAYER (Optional)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Cluster Descriptions ──▶ Vector DB (Embeddings)                │
│                                                                  │
│  Policy Justifications ──▶ Vector DB (Embeddings)               │
│                                                                  │
│  RAG Context Retrieval ──▶ Vector DB ──▶ LLM Agent             │
│                                                                  │
│  AI Recommendations ──▶ PostgreSQL (Policies)                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Integration Points

### 1. Flow Graph Population

**Sources:**
- NetFlow/sFlow data → TimescaleDB → Processing → Neo4j Flow Graph
- Edge agent sketches → Processing → Neo4j Flow Graph
- ISE pxGrid sessions → PostgreSQL → Correlation → Neo4j Flow Graph

**Process:**
1. Flows ingested into TimescaleDB
2. Behavioral sketches built/updated
3. Clustering performed
4. Results written to Neo4j Flow Graph (endpoints, clusters, SGTs, relationships)

---

### 2. Topology Graph Population

**Sources:**
- SNMP discovery → Neo4j Topology Graph
- Device APIs (RESTCONF, NETCONF) → Neo4j Topology Graph
- Configuration parsing → Neo4j Topology Graph
- LLDP/CDP neighbor discovery → Neo4j Topology Graph

**Process:**
1. Device discovery via SNMP/API
2. Interface and connection discovery
3. Routing table discovery (for routers)
4. Results written to Neo4j Topology Graph (devices, interfaces, connections)

---

### 3. Vector Database Population

**Sources:**
- Cluster descriptions (from clustering)
- Policy justifications (from policy generation)
- Historical decisions (from user feedback)
- Device configurations (from config parsing)
- Documentation (from docs)

**Process:**
1. Text content generated (descriptions, justifications)
2. Embeddings generated using embedding model
3. Stored in Vector DB with metadata
4. Used for RAG context retrieval by AI agents

---

### 4. Cross-Graph Correlation

**Flow Graph ↔ Topology Graph:**
- Endpoint (Flow Graph) → Device (Topology Graph) via IP/MAC
- Flow paths (Flow Graph) → Network paths (Topology Graph) via device connections
- Policy enforcement points (Topology Graph) → Policy impact (Flow Graph)

**Example:**
```cypher
// Find attack path considering both flow behavior and topology
MATCH (ep:Endpoint {ip: '10.1.1.100'})-[:FLOWS_TO]->(ep2:Endpoint)
MATCH (d:Device {management_ip: ep.ip})
MATCH path = (d)-[:CONNECTED_TO*..10]->(d2:Device {management_ip: ep2.ip})
RETURN path, ep, ep2
```

---

## Configuration Data Strategy

### Vendor-Specific Configurations

**Storage:**
- **PostgreSQL**: Store raw configs in `device_configurations` table (JSON/Text)
- **Vector Database**: Store config snippets with embeddings for semantic search

**Structure:**
```sql
CREATE TABLE device_configurations (
    device_id TEXT PRIMARY KEY,
    vendor TEXT NOT NULL,  -- 'cisco', 'juniper', 'palo_alto', etc.
    config_type TEXT,  -- 'running-config', 'security-policy', etc.
    raw_config TEXT,  -- Full configuration text
    parsed_config JSONB,  -- Parsed/structured config (vendor-specific)
    version INTEGER,  -- Config version
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

**Vector DB Storage:**
- Store config snippets (e.g., interface configs, ACL rules, firewall policies)
- Generate embeddings for semantic search
- Enable RAG for AI agents analyzing configurations

**Use Cases:**
- Policy conflict detection across vendors
- Configuration pattern matching
- AI-powered configuration analysis
- Multi-vendor policy translation

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-5)
- ✅ PostgreSQL + TimescaleDB migration
- ✅ Basic Neo4j deployment
- ✅ Flow Graph implementation (Graph 1)
- ✅ Vector database setup (Chroma or Qdrant)

### Phase 2: Topology Integration (Weeks 6-10)
- Topology Graph implementation (Graph 2)
- Device discovery and topology population
- Cross-graph correlation

### Phase 3: AI Integration (Weeks 11-15)
- Vector database population (cluster descriptions, policy justifications)
- RAG context builder
- AI agent integration with vector DB

### Phase 4: Multi-Vendor (Weeks 16-20)
- Configuration storage and parsing
- Vector DB for config analysis
- Multi-vendor policy correlation

---

## Technology Recommendations

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Time-Series DB** | TimescaleDB | PostgreSQL-based, proven scale, SQL interface |
| **Graph DB** | Neo4j | Mature, dual graph support, good Python support |
| **Relational DB** | PostgreSQL | ACID, complex queries, JSON support |
| **Vector DB** | Chroma (dev) / Qdrant (prod) | Open-source, high-performance, good Python support |
| **Cache/Buffer** | Redis | High-speed, proven reliability |
| **Data Lake** | S3 + Parquet | Cost-effective, analytics-ready |

---

## Key Decisions

### 1. **Dual Graph Architecture**
- **Decision**: Use Neo4j with separate graph models (Flow Graph and Topology Graph)
- **Rationale**: Different use cases, different update frequencies, different query patterns
- **Implementation**: Use labels or separate databases for isolation

### 2. **Vector Database for RAG**
- **Decision**: Include vector database as core component, not optional
- **Rationale**: Essential for AI/LLM context, configuration analysis, pattern matching
- **Implementation**: Start with Chroma (embedded), scale to Qdrant or Pinecone

### 3. **Configuration Storage**
- **Decision**: Store in PostgreSQL (raw) + Vector DB (embeddings)
- **Rationale**: Need both structured storage and semantic search
- **Implementation**: Parse configs, store raw + parsed, generate embeddings for snippets

### 4. **Data Retention**
- **Decision**: TimescaleDB for time-series (90 days raw, 1 year aggregated), Data Lake for long-term
- **Rationale**: Balance performance and cost
- **Implementation**: Automated retention policies in TimescaleDB, archive to S3

---

## Next Steps

1. **Design Neo4j schema** for both Flow Graph and Topology Graph
2. **Select vector database** (Chroma for dev, Qdrant for prod)
3. **Implement configuration storage** strategy
4. **Design cross-graph correlation** queries
5. **Build RAG context builder** for AI agents
6. **Create data migration plan** from SQLite to new architecture

---

## References

- [Data Architecture](DATA_ARCHITECTURE.md) - Detailed data source requirements
- [AI Enhanced Architecture](AI_ENHANCED_ARCHITECTURE.md) - AI/LLM integration details
- [Topology Architecture](TOPOLOGY_ARCHITECTURE.md) - Network topology design
- [Capabilities Roadmap](../CAPABILITIES_ROADMAP.md) - Complete feature roadmap

