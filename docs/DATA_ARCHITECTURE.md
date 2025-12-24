# Data Architecture & Analytics Layer

## Overview

Clarion requires a high-performance, scalable data architecture to handle:
- **Edge graph merging** - Agents on switches use graphs that must merge with backend
- **Multi-source ingestion** - NetFlow, agent flows, ISE pxGrid, AD, IoT solutions
- **Time-series data** - Flow data is inherently temporal
- **Graph relationships** - Device-to-device, user-to-device, policy relationships
- **Correlation** - Cross-source data correlation for policy generation
- **Scale** - Enterprise-scale data volumes (millions of flows/day)

## Current State

**Database:** SQLite (development only)
- Relational tables for sketches, clusters, policies
- Not suitable for production scale
- No graph capabilities
- Limited time-series optimization

**Limitations:**
- No graph merging from edge agents
- Single data source (synthetic flows)
- No time-series optimization
- No multi-source correlation layer

---

## Required Data Sources & Fields

### 1. NetFlow Data (Legacy Switches)

**NetFlow Versions:**
- **v5** - IPv4 only, fixed format
- **v9** - Template-based, extensible
- **IPFIX** - IETF standard, most flexible

**Required Fields:**

| Field | NetFlow v5 | NetFlow v9 | IPFIX | Purpose |
|-------|------------|------------|-------|---------|
| Source IP | ✅ | ✅ | ✅ | Device identification |
| Destination IP | ✅ | ✅ | ✅ | Device identification |
| Source Port | ✅ | ✅ | ✅ | Service identification |
| Destination Port | ✅ | ✅ | ✅ | Service identification |
| Protocol | ✅ | ✅ | ✅ | Transport layer |
| Bytes | ✅ | ✅ | ✅ | Volume analysis |
| Packets | ✅ | ✅ | ✅ | Volume analysis |
| Flow Start | ✅ | ✅ | ✅ | Time-series correlation |
| Flow End | ✅ | ✅ | ✅ | Duration calculation |
| TCP Flags | ✅ | ✅ | ✅ | Connection state |
| ToS/DSCP | ✅ | ✅ | ✅ | QoS analysis |
| Input Interface | ✅ | ✅ | ✅ | Switch port mapping |
| Output Interface | ✅ | ✅ | ✅ | Switch port mapping |
| Next Hop IP | ❌ | ✅ | ✅ | Routing analysis |
| Source AS | ❌ | ✅ | ✅ | Network context |
| Destination AS | ❌ | ✅ | ✅ | Network context |
| BGP Next Hop | ❌ | ✅ | ✅ | Routing context |
| VLAN ID | ❌ | ✅ | ✅ | Network segmentation |
| Source MAC | ❌ | ✅ | ✅ | Device correlation |
| Destination MAC | ❌ | ✅ | ✅ | Device correlation |
| **Source SGT** | ❌ | ✅ | ✅ | **TrustSec source tag (IPFIX IE 411)** |
| **Destination SGT** | ❌ | ✅ | ✅ | **TrustSec destination tag (IPFIX IE 412)** |
| IPv6 fields | ❌ | ✅ | ✅ | IPv6 support |

**Storage Requirements:**
- Time-series optimized (flows are temporal)
- High write throughput (100K+ flows/hour per switch)
- Retention policies (90 days raw, 1 year aggregated)
- Compression for historical data

**⚠️ Important: SGT in NetFlow**
- **Source SGT** and **Destination SGT** are available in NetFlow v9 and IPFIX
- IPFIX Information Elements:
  - IE 411: `sourceSecurityGroupTag` (16-bit SGT value)
  - IE 412: `destinationSecurityGroupTag` (16-bit SGT value)
- NetFlow v9: Cisco enterprise-specific fields (requires Flexible NetFlow configuration)
- **SGT value of 0** means: untagged, not found, or from trusted interface
- This is **critical** for policy validation - actual SGTs in use vs. recommended SGTs

---

### 2. Agent Flow Data (Edge Containers)

**Source:** Catalyst 9K App Hosting containers

**Fields Available:**
- All NetFlow fields (from switch)
- **Edge cluster assignments** - Local K-means cluster IDs
- **Behavioral sketches** - HyperLogLog, Count-Min Sketch
- **Switch context** - Switch ID, port, VLAN
- **Timestamp** - When processed at edge

**Required Fields:**

| Field | Purpose |
|-------|---------|
| Source IP | Device identification |
| Destination IP | Device identification |
| Source Port | Service identification |
| Destination Port | Service identification |
| Protocol | Transport layer |
| Bytes | Volume |
| Packets | Volume |
| Flow Start | Time correlation |
| Flow End | Duration |
| Switch ID | Edge location |
| Input Interface | Port mapping |
| Output Interface | Port mapping |
| Source MAC | Device correlation |
| Destination MAC | Device correlation |
| Edge Cluster ID | Local clustering result |
| Sketch Data | Behavioral fingerprint (binary) |
| Sketch Timestamp | When sketch was built |

**Graph Structure:**
- Nodes: Endpoints (IP/MAC), Switches, Services
- Edges: Flows (with metadata: bytes, packets, ports, protocol)
- Edge properties: Timestamp, duration, direction

**Merging Requirements:**
- Merge edge graphs into global graph
- Resolve endpoint identity across switches
- Aggregate behavioral sketches
- Update global clusters from edge clusters

---

### 3. ISE pxGrid Data (Identity & SGT)

**pxGrid Topics:**
- `com.cisco.ise.session` - Active sessions
- `com.cisco.ise.endpoint` - Endpoint information
- `com.cisco.ise.anc` - Adaptive Network Control

**Required Fields:**

| Field | pxGrid Topic | Purpose |
|-------|--------------|---------|
| MAC Address | session, endpoint | Device correlation |
| IP Address | session, endpoint | Device identification |
| Username | session | User identity |
| User ID | session | User identity |
| AD Groups | session | Group membership |
| SGT Value | session, endpoint | Current SGT assignment |
| SGT Name | session, endpoint | SGT label |
| ISE Profile | endpoint | Device profile |
| Device Type | endpoint | Device classification |
| Posture Status | session | Compliance state |
| Authentication Method | session | Auth context |
| Session Start | session | Time correlation |
| Session End | session | Time correlation |
| Switch ID | session | Location context |
| Switch Port | session | Port mapping |
| VLAN | session | Network context |
| Policy Set | session | Applied policy |

**Storage Requirements:**
- Real-time updates (pxGrid is pub/sub)
- Historical session data (for correlation)
- SGT assignment history
- User-to-device mapping

---

### 4. Active Directory Data

**Sources:**
- LDAP queries
- AD logs (Security Event Log)
- Group membership queries

**Required Fields:**

| Field | Source | Purpose |
|-------|--------|---------|
| Username | LDAP | User identity |
| User ID (SID) | LDAP | Unique user ID |
| Email | LDAP | User contact |
| Display Name | LDAP | User label |
| Department | LDAP | Organizational context |
| AD Groups | LDAP | Group membership |
| Group SID | LDAP | Group identity |
| Group Name | LDAP | Group label |
| Group Type | LDAP | Security/Distribution |
| Member Of | LDAP | Nested groups |
| Last Login | AD Logs | Activity correlation |
| Computer Name | LDAP | Device correlation |
| Computer SID | LDAP | Device identity |
| OU (Organizational Unit) | LDAP | Organizational context |

**Storage Requirements:**
- Periodic sync (not real-time)
- Group membership hierarchy
- User-to-device mapping
- Historical membership changes

---

### 5. Third-Party IoT/MIoT Solutions

**Examples:**
- MediGate (medical device management)
- Aruba ClearPass (device profiling)
- Forescout (device visibility)
- Custom IoT platforms

**Required Flexible Schema:**

| Field Type | Examples | Purpose |
|------------|----------|---------|
| Device ID | MAC, Serial, UUID | Device identification |
| Device Type | "Medical Device", "Printer" | Classification |
| Vendor | "Philips", "HP" | Context |
| Model | "Ventilator X1" | Context |
| Risk Score | 0-100 | Security context |
| Compliance Status | "Compliant", "Non-compliant" | Policy context |
| Location | Building, Floor, Room | Physical context |
| Owner | Department, User | Organizational context |
| Custom Attributes | JSON | Flexible extension |

**Storage Requirements:**
- Flexible schema (JSON for custom fields)
- Vendor-specific field mapping
- Periodic sync or API polling
- Correlation with network flows

---

## Data Correlation Requirements

### Correlation Keys

1. **Device Identity:**
   - Primary: MAC Address
   - Secondary: IP Address (time-bounded)
   - Tertiary: Device serial/UUID

2. **User Identity:**
   - Primary: Username
   - Secondary: User SID
   - Correlation: AD Groups → ISE Profiles → SGTs

3. **Temporal Correlation:**
   - Flow timestamps → Session timestamps
   - Device discovery → Flow appearance
   - SGT assignment changes → Policy impact

4. **Network Context:**
   - Switch ID → Location
   - VLAN → Network segment
   - IP subnet → Organizational unit

### Correlation Queries

```sql
-- Example: Correlate flow with identity
SELECT 
    f.src_ip, f.dst_ip, f.bytes,
    i.username, i.ad_groups, i.sgt_value,
    a.device_type, a.risk_score
FROM flows f
JOIN identity i ON f.src_mac = i.mac_address
LEFT JOIN iot_devices a ON f.src_mac = a.device_id
WHERE f.flow_start BETWEEN ? AND ?
```

---

## Network Topology & Location Awareness

**See [TOPOLOGY_ARCHITECTURE.md](TOPOLOGY_ARCHITECTURE.md) for complete design.**

### Key Requirements

- **Location Hierarchy:** Campus → Building → IDF
- **Address Space Management:** Customer-defined IP ranges (e.g., 10.0.0.0/8)
- **Subnet-to-Location Mapping:** Know which subnets are at which locations
- **Switch-to-Location Mapping:** Track switches by physical location
- **Flow Location Correlation:** Enrich flows with location context

### Location Context in Flows

Flows will be enriched with:
- Source location path: "Campus: Main > Building: 2 > IDF: 1"
- Destination location path
- Source/destination subnets
- Subnet purposes (USER, SERVER, IOT, etc.)

This enables:
- Location-aware policy recommendations
- Inter-building vs. intra-building traffic analysis
- Compliance tracking by location

---

## Recommended Architecture

### Hybrid Approach: Time-Series + Graph + Relational

**1. Time-Series Database (Primary)**
- **Technology:** TimescaleDB (PostgreSQL extension) or InfluxDB
- **Purpose:** NetFlow and flow data
- **Benefits:**
  - Optimized for time-series queries
  - Automatic data retention/compression
  - High write throughput
  - Time-based partitioning

**2. Graph Database (Relationships)**
- **Technology:** Neo4j or Amazon Neptune
- **Purpose:** Device relationships, user-device mappings, policy graphs
- **Benefits:**
  - Native graph operations (merge, traverse)
  - Edge agent graph merging
  - Relationship queries
  - Policy dependency graphs

**3. Relational Database (Metadata)**
- **Technology:** PostgreSQL
- **Purpose:** Identity data, SGT mappings, policies, configuration
- **Benefits:**
  - ACID transactions
  - Complex joins
  - Structured data

**4. Data Lake (Long-term Storage)**
- **Technology:** S3 + Parquet or Delta Lake
- **Purpose:** Historical data, analytics, ML training
- **Benefits:**
  - Cost-effective long-term storage
  - Analytics workloads
  - Data versioning

---

## Implementation Strategy

### Phase 1: Foundation (Current → Next)

**Current:** SQLite
**Next:** PostgreSQL + TimescaleDB

**Changes:**
1. Migrate to PostgreSQL
2. Add TimescaleDB extension for time-series
3. Create hypertables for flow data
4. Implement data retention policies

**Schema:**
```sql
-- TimescaleDB hypertable for flows
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
    -- ... other fields
);

SELECT create_hypertable('flows', 'time');
```

### Phase 2: Graph Integration

**Add:** Neo4j or graph layer

**Changes:**
1. Deploy Neo4j cluster
2. Create graph schema:
   - Nodes: Device, User, Switch, Service, SGT
   - Edges: FLOWS_TO, ASSIGNED_TO, MEMBER_OF, CONNECTED_TO
3. Implement edge graph merging:
   - Receive graph from edge agent
   - Merge nodes (deduplicate by MAC/IP)
   - Merge edges (aggregate flows)
   - Update global clusters

**Graph Schema:**
```cypher
// Device node
CREATE (d:Device {
    mac: 'aa:bb:cc:dd:ee:ff',
    ip: '10.0.0.1',
    device_type: 'Laptop',
    sgt: 2
})

// Flow relationship
CREATE (d1:Device)-[f:FLOWS_TO {
    bytes: 1000000,
    packets: 5000,
    port: 443,
    protocol: 'TCP',
    timestamp: datetime()
}]->(d2:Device)

// User assignment
CREATE (u:User)-[:ASSIGNED_TO]->(d:Device)
```

### Phase 3: Multi-Source Ingestion

**Add:** Ingestion pipelines

**Changes:**
1. **NetFlow Collector:**
   - Support v5, v9, IPFIX
   - Template handling for v9/IPFIX
   - Field mapping to unified schema

2. **pxGrid Subscriber:**
   - Subscribe to ISE topics
   - Real-time session updates
   - SGT assignment tracking

3. **AD Connector:**
   - LDAP queries (periodic)
   - Group membership sync
   - User-device mapping

4. **IoT Connector:**
   - Flexible API adapter
   - Vendor-specific parsers
   - Custom field mapping

### Phase 4: Correlation Engine

**Add:** Correlation service

**Changes:**
1. **Identity Resolution:**
   - MAC → IP → User → Groups → SGT
   - Temporal correlation (time windows)
   - Confidence scoring

2. **Graph Merging:**
   - Edge agent graphs → Global graph
   - Conflict resolution
   - Incremental updates

3. **Policy Correlation:**
   - Flow patterns → SGT assignments
   - User behavior → Policy recommendations
   - Device context → Risk assessment

---

## Performance Requirements

### Write Throughput
- **NetFlow:** 100K flows/hour per switch × 1000 switches = 100M flows/hour
- **Agent Data:** 1K sketches/hour per switch × 1000 switches = 1M sketches/hour
- **pxGrid:** 10K sessions/hour (bursts during login storms)

### Query Performance
- **Real-time Dashboard:** < 100ms for current state
- **Flow Analysis:** < 1s for 24-hour window
- **Graph Traversal:** < 500ms for 3-hop queries
- **Correlation:** < 2s for cross-source joins

### Storage
- **Raw Flows:** 90 days retention = ~2.4TB (compressed)
- **Aggregated:** 1 year retention = ~500GB
- **Graph:** ~50GB (relationships only)
- **Identity:** ~10GB (users, devices, mappings)

---

## Migration Path

### Step 1: PostgreSQL Migration (Immediate)
- Migrate SQLite → PostgreSQL
- Add TimescaleDB extension
- Update storage layer code

### Step 2: Graph Layer (Short-term)
- Deploy Neo4j
- Implement graph schema
- Add graph merging from edge agents

### Step 3: Multi-Source Ingestion (Medium-term)
- Build NetFlow collector (v5/v9/IPFIX)
- Implement pxGrid subscriber
- Add AD connector
- Create IoT adapter framework

### Step 4: Correlation Engine (Long-term)
- Build identity resolution service
- Implement graph merging logic
- Add policy correlation

---

## Technology Stack Recommendations

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Time-Series DB** | TimescaleDB | PostgreSQL-based, SQL interface, proven scale |
| **Graph DB** | Neo4j | Mature, good Python support, ACID transactions |
| **Relational DB** | PostgreSQL | Already using, ACID, complex queries |
| **Data Lake** | S3 + Parquet | Cost-effective, analytics-ready |
| **Message Queue** | Kafka/RabbitMQ | For real-time ingestion (pxGrid, flows) |
| **Stream Processing** | Apache Flink | For real-time correlation |

---

## Next Steps

1. **Design unified data schema** for all sources
2. **Implement PostgreSQL + TimescaleDB** migration
3. **Design graph schema** for relationships
4. **Build NetFlow collector** with multi-version support
5. **Create pxGrid subscriber** for ISE integration
6. **Design correlation engine** architecture

