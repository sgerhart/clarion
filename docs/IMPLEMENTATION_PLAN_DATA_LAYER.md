# Implementation Plan: High-Performance Data & Analytics Layer

## Executive Summary

Current SQLite implementation is insufficient for production. We need:
1. **Graph database** for edge agent graph merging
2. **Time-series database** for NetFlow data (100M+ flows/hour)
3. **Multi-source ingestion** (NetFlow v5/v9/IPFIX, pxGrid, AD, IoT)
4. **Correlation engine** for cross-source data joins
5. **Scalable architecture** for enterprise deployments

---

## Phase 1: PostgreSQL + TimescaleDB Migration (Immediate)

### Current State
- SQLite database (`clarion.db`)
- Basic relational schema
- No time-series optimization
- Limited to single-node

### Target State
- PostgreSQL with TimescaleDB extension
- Time-series optimized tables (hypertables)
- Automatic data retention/compression
- High write throughput

### Implementation Steps

#### 1.1 Database Migration
```bash
# Install PostgreSQL + TimescaleDB
# Create migration script
python scripts/migrate_to_postgresql.py
```

**Schema Changes:**
```sql
-- Convert netflow table to TimescaleDB hypertable
CREATE TABLE flows (
    time TIMESTAMPTZ NOT NULL,
    src_ip INET NOT NULL,
    dst_ip INET NOT NULL,
    src_port INTEGER,
    dst_port INTEGER,
    protocol INTEGER,
    bytes BIGINT,
    packets INTEGER,
    src_mac MACADDR,
    dst_mac MACADDR,
    switch_id TEXT,
    input_interface INTEGER,
    output_interface INTEGER,
    vlan_id INTEGER,
    tos INTEGER,
    tcp_flags INTEGER,
    flow_duration INTEGER,
    -- NetFlow v9/IPFIX fields
    next_hop_ip INET,
    src_as INTEGER,
    dst_as INTEGER,
    bgp_next_hop INET,
    -- Metadata
    received_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create hypertable (partitioned by time)
SELECT create_hypertable('flows', 'time', 
    chunk_time_interval => INTERVAL '1 day');

-- Create indexes
CREATE INDEX idx_flows_src_time ON flows(src_ip, time DESC);
CREATE INDEX idx_flows_dst_time ON flows(dst_ip, time DESC);
CREATE INDEX idx_flows_switch_time ON flows(switch_id, time DESC);
CREATE INDEX idx_flows_mac ON flows(src_mac, dst_mac);
```

#### 1.2 Update Storage Layer
- Modify `src/clarion/storage/database.py`
- Add PostgreSQL connection pool
- Implement TimescaleDB-specific queries
- Add data retention policies

#### 1.3 Migration Script
```python
# scripts/migrate_to_postgresql.py
def migrate_sqlite_to_postgres():
    # 1. Export SQLite data
    # 2. Transform schema
    # 3. Import to PostgreSQL
    # 4. Create TimescaleDB hypertables
    # 5. Verify data integrity
```

**Timeline:** 2-3 weeks

---

## Phase 2: Graph Database Integration (Short-term)

### Current State
- No graph capabilities
- Edge agents send sketches (not graphs)
- No graph merging logic

### Target State
- Neo4j cluster for graph storage
- Graph schema for relationships
- Edge agent graph merging
- Graph queries for policy correlation

### Implementation Steps

#### 2.1 Deploy Neo4j
```bash
# Docker Compose or Kubernetes
# Neo4j cluster (3 nodes for HA)
```

#### 2.2 Graph Schema Design
```cypher
// Node types
(:Device {mac, ip, device_type, sgt})
(:User {username, user_id, email})
(:Switch {switch_id, location})
(:Service {port, protocol, name})
(:SGT {value, name, description})
(:Cluster {cluster_id, label})
(:ADGroup {name, sid, type})

// Relationship types
(:Device)-[:FLOWS_TO {bytes, packets, port, time}]->(:Device)
(:Device)-[:ASSIGNED_TO]->(:User)
(:User)-[:MEMBER_OF]->(:ADGroup)
(:Device)-[:HAS_SGT]->(:SGT)
(:Device)-[:IN_CLUSTER]->(:Cluster)
(:Device)-[:CONNECTED_TO]->(:Switch)
(:Device)-[:USES_SERVICE]->(:Service)
```

#### 2.3 Edge Agent Graph Format
```python
# Edge agent sends graph structure
{
    "nodes": [
        {"id": "mac1", "type": "Device", "properties": {...}},
        {"id": "mac2", "type": "Device", "properties": {...}}
    ],
    "edges": [
        {"source": "mac1", "target": "mac2", "type": "FLOWS_TO", "properties": {...}}
    ],
    "switch_id": "SW001",
    "timestamp": 1234567890
}
```

#### 2.4 Graph Merging Service
```python
# src/clarion/graph/merger.py
class GraphMerger:
    def merge_edge_graph(self, edge_graph: Dict, switch_id: str):
        """
        Merge edge agent graph into global graph.
        
        1. Deduplicate nodes (by MAC address)
        2. Merge node properties (update timestamps, aggregates)
        3. Merge edges (aggregate flow data)
        4. Update cluster assignments
        """
        # Neo4j merge query
        # MATCH/MERGE nodes
        # CREATE/MERGE relationships
        # Update properties
```

#### 2.5 Update Edge Agent
- Modify edge agent to build graph structure
- Send graph JSON to backend
- Include cluster assignments in graph

**Timeline:** 4-6 weeks

---

## Phase 3: Multi-Source Ingestion (Medium-term)

### 3.1 NetFlow Collector

**Support:**
- NetFlow v5 (fixed format)
- NetFlow v9 (template-based)
- IPFIX (IETF standard)

**Implementation:**
```python
# src/clarion/ingest/netflow_collector.py
class NetFlowCollector:
    def __init__(self):
        self.templates = {}  # For v9/IPFIX
        
    def parse_v5(self, data: bytes) -> List[FlowRecord]:
        """Parse NetFlow v5 packet."""
        
    def parse_v9(self, data: bytes) -> List[FlowRecord]:
        """Parse NetFlow v9 packet (template-based)."""
        # Handle template records
        # Parse data records using templates
        
    def parse_ipfix(self, data: bytes) -> List[FlowRecord]:
        """Parse IPFIX packet."""
```

**Fields Mapping:**
```python
FIELD_MAPPING = {
    # Common fields
    'src_ip': {v5: 0, v9: 8, ipfix: 8},
    'dst_ip': {v5: 4, v9: 12, ipfix: 12},
    'src_port': {v5: 8, v9: 7, ipfix: 7},
    'dst_port': {v5: 10, v9: 11, ipfix: 11},
    'protocol': {v5: 2, v9: 4, ipfix: 4},
    'bytes': {v5: 16, v9: 85, ipfix: 85},
    'packets': {v5: 12, v9: 86, ipfix: 86},
    # v9/IPFIX only
    'src_mac': {v9: 56, ipfix: 56},
    'dst_mac': {v9: 57, ipfix: 57},
    'vlan_id': {v9: 58, ipfix: 58},
    'next_hop': {v9: 15, ipfix: 15},
    # TrustSec SGT fields (CRITICAL for policy validation)
    'src_sgt': {v9: 'enterprise', ipfix: 411},  # IPFIX IE 411: sourceSecurityGroupTag
    'dst_sgt': {v9: 'enterprise', ipfix: 412},  # IPFIX IE 412: destinationSecurityGroupTag
}
```

**Timeline:** 3-4 weeks

### 3.2 ISE pxGrid Subscriber

**Implementation:**
```python
# src/clarion/ingest/pxgrid_subscriber.py
class PxGridSubscriber:
    def __init__(self, config: PxGridConfig):
        self.client = pxgrid.Client(config)
        
    async def subscribe(self):
        """Subscribe to pxGrid topics."""
        # com.cisco.ise.session
        # com.cisco.ise.endpoint
        # com.cisco.ise.anc
        
    async def on_session_update(self, message: Dict):
        """Handle session updates."""
        # Extract: MAC, IP, Username, SGT, Groups
        # Store in identity table
        # Update graph (User -> Device)
```

**Topics:**
- `com.cisco.ise.session` - Active sessions
- `com.cisco.ise.endpoint` - Endpoint info
- `com.cisco.ise.anc` - Adaptive Network Control

**Timeline:** 2-3 weeks

### 3.3 AD Connector

**Implementation:**
```python
# src/clarion/ingest/ad_connector.py
class ADConnector:
    def __init__(self, config: ADConfig):
        self.ldap = ldap3.Connection(...)
        
    def sync_users(self):
        """Sync user data from AD."""
        # Query: users, groups, memberships
        
    def sync_devices(self):
        """Sync computer objects from AD."""
        # Query: computer accounts
        
    def get_group_membership(self, username: str) -> List[str]:
        """Get AD groups for user."""
```

**Timeline:** 2 weeks

### 3.4 IoT Connector Framework

**Implementation:**
```python
# src/clarion/ingest/iot_connector.py
class IoTConnector(ABC):
    @abstractmethod
    def connect(self):
        """Connect to IoT platform."""
        
    @abstractmethod
    def fetch_devices(self) -> List[Device]:
        """Fetch device data."""
        
    @abstractmethod
    def map_fields(self, device: Dict) -> Device:
        """Map vendor fields to unified schema."""

# Vendor-specific implementations
class MediGateConnector(IoTConnector):
    """MediGate medical device connector."""
    
class ArubaClearPassConnector(IoTConnector):
    """Aruba ClearPass connector."""
```

**Timeline:** 3-4 weeks (per connector)

---

## Phase 4: Correlation Engine (Long-term)

### 4.1 Identity Resolution Service

**Purpose:** Correlate data across sources

**Implementation:**
```python
# src/clarion/correlation/identity_resolver.py
class IdentityResolver:
    def resolve_device(self, mac: str, ip: str, timestamp: int) -> DeviceIdentity:
        """
        Resolve device identity from multiple sources.
        
        1. MAC -> Device (from graph)
        2. IP -> MAC (from flows, time-bounded)
        3. MAC -> User (from pxGrid sessions)
        4. User -> AD Groups (from AD)
        5. AD Groups -> SGT (from ISE mapping)
        """
        
    def correlate_flow(self, flow: FlowRecord) -> CorrelatedFlow:
        """
        Correlate flow with identity data.
        
        Returns:
            - Source device identity
            - Destination device identity
            - User context
            - SGT assignments
            - Risk scores
        """
```

### 4.2 Temporal Correlation

**Time Windows:**
- Flow timestamp ± 5 minutes for session correlation
- Device discovery → Flow appearance
- SGT assignment changes → Policy impact

**Implementation:**
```python
# src/clarion/correlation/temporal.py
class TemporalCorrelator:
    def correlate_flow_with_session(
        self, 
        flow: FlowRecord,
        window_seconds: int = 300
    ) -> Optional[Session]:
        """Find ISE session active during flow."""
        
    def correlate_device_discovery(
        self,
        device_mac: str,
        discovery_time: int
    ) -> List[FlowRecord]:
        """Find flows from device after discovery."""
```

### 4.3 Policy Correlation

**Purpose:** Build SGT policies from correlated data

**Implementation:**
```python
# src/clarion/correlation/policy.py
class PolicyCorrelator:
    def build_policy_matrix(self) -> PolicyMatrix:
        """
        Build SGT policy matrix from correlated data.
        
        1. Query flows with identity
        2. Group by (src_sgt, dst_sgt)
        3. Aggregate: bytes, packets, ports
        4. Calculate confidence scores
        """
        
    def recommend_sgt(self, device: Device) -> SGTRecommendation:
        """
        Recommend SGT based on:
        - Behavioral clustering
        - AD group membership
        - ISE profile
        - IoT device type
        - Risk score
        """
```

**Timeline:** 6-8 weeks

---

## Technology Stack Updates

### Current → Target

| Component | Current | Target | Rationale |
|-----------|---------|--------|-----------|
| **Time-Series** | SQLite | TimescaleDB | Optimized for flows |
| **Graph** | None | Neo4j | Edge graph merging |
| **Relational** | SQLite | PostgreSQL | ACID, scale |
| **Message Queue** | None | Kafka/RabbitMQ | Real-time ingestion |
| **Data Lake** | None | S3 + Parquet | Long-term storage |

### New Dependencies

```python
# requirements.txt additions
timescaledb>=2.0.0  # PostgreSQL extension
neo4j>=5.0.0  # Graph database driver
kafka-python>=2.0.0  # Message queue
ldap3>=2.9.0  # AD connector
pxgrid-python>=1.0.0  # ISE pxGrid (or custom)
```

---

## Migration Strategy

### Step 1: PostgreSQL Migration (Week 1-3)
1. Set up PostgreSQL + TimescaleDB
2. Create new schema
3. Migrate existing data
4. Update storage layer
5. Test with synthetic data

### Step 2: Graph Integration (Week 4-9)
1. Deploy Neo4j
2. Design graph schema
3. Implement graph merging
4. Update edge agents to send graphs
5. Test graph operations

### Step 3: NetFlow Collector (Week 10-13)
1. Implement v5 parser
2. Implement v9 template handling
3. Implement IPFIX parser
4. Field mapping to unified schema
5. Integration testing

### Step 4: pxGrid Subscriber (Week 14-16)
1. Set up pxGrid client
2. Subscribe to topics
3. Parse session/endpoint data
4. Store in database
5. Update graph

### Step 5: AD Connector (Week 17-18)
1. LDAP connection
2. User/group sync
3. Device sync
4. Periodic updates

### Step 6: Correlation Engine (Week 19-26)
1. Identity resolution
2. Temporal correlation
3. Policy correlation
4. Performance optimization

---

## Performance Targets

### Write Throughput
- **NetFlow:** 100M flows/hour (sustained)
- **Agent Graphs:** 1M merges/hour
- **pxGrid:** 10K sessions/hour (bursts)

### Query Performance
- **Real-time Dashboard:** < 100ms
- **Flow Analysis (24h):** < 1s
- **Graph Traversal (3-hop):** < 500ms
- **Correlation:** < 2s

### Storage
- **Raw Flows:** 90 days = ~2.4TB (compressed)
- **Aggregated:** 1 year = ~500GB
- **Graph:** ~50GB
- **Identity:** ~10GB

---

## Next Steps

1. **Review and approve** data architecture document
2. **Set up development environment** (PostgreSQL + TimescaleDB)
3. **Create migration scripts** for SQLite → PostgreSQL
4. **Design graph schema** for Neo4j
5. **Start NetFlow collector** implementation
6. **Plan pxGrid integration** (get ISE access)

