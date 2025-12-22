# Clarion - TrustSec Policy Copilot

## Design Document v1.0

---

## 1. Executive Summary

**Clarion** is an intelligent network visibility and policy design platform that helps organizations adopt and refine Cisco TrustSec deployments. It observes real network behavior, resolves identities, and generates actionable security group (SGT) taxonomies and SGACL policies—enabling customers to move from "no segmentation" to a working TrustSec model without requiring deep expertise.

### Core Value Proposition

> *"Mine real network behavior into a TrustSec policy matrix, then give customers a safe path from today → desired state."*

---

## 2. Problem Statement

### Customer Pain Points

1. **TrustSec adoption is hard**: Customers struggle to define SGT taxonomies and policies from scratch
2. **No visibility into current state**: Unknown traffic patterns make policy design guesswork
3. **Identity chaos**: IP addresses change; mapping flows to users/devices requires complex joins
4. **Fear of breaking things**: Enforcement without validation causes outages
5. **Policy drift**: Observed behavior diverges from intended policy over time

### What Clarion Solves

| Problem | Clarion Solution |
|---------|------------------|
| No SGTs defined | Recommend initial taxonomy from observed behavior |
| Unknown traffic patterns | Build identity-labeled communication graph |
| Can't map IPs to users | Join flows → ISE sessions → AD groups |
| Fear of enforcement | Monitor-mode validation before enforcement |
| Policy drift | Continuous reconciliation engine |

---

## 3. System Architecture

### Design Principles

1. **Edge-First Processing**: Process data at the source when possible
2. **Central Analytics**: Aggregate and correlate for comprehensive insights
3. **Integration Ready**: Built to consume data from multiple identity sources
4. **Production Path**: Architecture designed to transition from synthetic → live data

### Deployment Tiers

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              EDGE TIER                                           │
│  ┌─────────────────────────┐  ┌─────────────────────────┐                       │
│  │   Catalyst 9K Switches  │  │   Non-Container Switches │                      │
│  │   (App Hosting)         │  │   (NetFlow Export)       │                      │
│  │  ┌───────────────────┐  │  │                          │                      │
│  │  │ Clarion Edge      │  │  │    NetFlow/IPFIX/sFlow   │                      │
│  │  │ Container         │  │  │         │                │                      │
│  │  │ ├─ Flow Capture   │  │  │         │                │                      │
│  │  │ ├─ Local Graph    │  │  │         │                │                      │
│  │  │ └─ Edge API       │  │  │         │                │                      │
│  │  └───────────────────┘  │  │         │                │                      │
│  └───────────┬─────────────┘  └─────────┼────────────────┘                      │
│              │                          │                                        │
└──────────────┼──────────────────────────┼────────────────────────────────────────┘
               │ gRPC/REST                │ NetFlow v9/IPFIX
               │ (graph summaries)        │
               ▼                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            COLLECTOR TIER                                        │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                     Clarion Flow Collector                               │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │   │
│  │  │ NetFlow/IPFIX │  │ sFlow       │  │ Packet       │                   │   │
│  │  │ Receiver     │  │ Receiver    │  │ Broker       │                   │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                   │   │
│  │         └─────────────────┴─────────────────┘                           │   │
│  │                           │                                              │   │
│  │                    ┌──────▼───────┐                                     │   │
│  │                    │ Flow Parser  │                                     │   │
│  │                    │ & Normalizer │                                     │   │
│  │                    └──────┬───────┘                                     │   │
│  │                           │                                              │   │
│  └───────────────────────────┼──────────────────────────────────────────────┘   │
│                              │                                                   │
└──────────────────────────────┼───────────────────────────────────────────────────┘
                               │ Normalized flows + edge graphs
                               ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            BACKEND TIER                                          │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         Clarion Backend                                  │   │
│  │                                                                          │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │   │
│  │  │ Ingest   │  │ Identity │  │ Analysis │  │ Policy   │  │ API/UI   │  │   │
│  │  │ Service  │  │ Resolver │  │ Engine   │  │ Engine   │  │ Service  │  │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │   │
│  │       │             │             │             │             │         │   │
│  │  ┌────▼─────────────▼─────────────▼─────────────▼─────────────▼────┐   │   │
│  │  │                        Data Layer                               │   │   │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │   │   │
│  │  │  │ Flow     │  │ Identity │  │ Policy   │  │ Config   │        │   │   │
│  │  │  │ Store    │  │ Graph    │  │ Store    │  │ Store    │        │   │   │
│  │  │  │(TimeSeries)│ │ (Graph) │  │ (Relational)│ (KV)     │        │   │   │
│  │  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │   │   │
│  │  └─────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
                               ▲
                               │ Identity Context (REST/LDAP/pxGrid)
                               │
┌──────────────────────────────┴───────────────────────────────────────────────────┐
│                          INTEGRATION TIER                                         │
│                                                                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐ │
│  │    ISE     │  │    AD      │  │   CMDB     │  │  DHCP/DNS  │  │  Other     │ │
│  │  (pxGrid)  │  │  (LDAP)    │  │ (REST/SNOW)│  │ (Infoblox) │  │  Sources   │ │
│  │            │  │            │  │            │  │            │  │            │ │
│  │ • Sessions │  │ • Users    │  │ • Assets   │  │ • Leases   │  │ • Endpoints│ │
│  │ • Profiles │  │ • Groups   │  │ • Owners   │  │ • Names    │  │ • Inventory│ │
│  │ • Auth     │  │ • OUs      │  │ • Criticality│ │ • Subnets │  │            │ │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘  └────────────┘ │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
```

### Edge Container Architecture (Cisco App Hosting)

The Clarion Edge container runs on **Cisco Catalyst 9300/9400/9500** switches using Cisco IOx App Hosting:

```
┌─────────────────────────────────────────────────────────┐
│              Catalyst 9K Switch                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │                 Clarion Edge Container             │ │
│  │  ┌─────────────────────────────────────────────┐  │ │
│  │  │              Edge Services                   │  │ │
│  │  │  ┌─────────────┐  ┌─────────────────────┐   │  │ │
│  │  │  │ Flow        │  │ Local Graph        │   │  │ │
│  │  │  │ Listener    │  │ Builder            │   │  │ │
│  │  │  │ (UDP 2055)  │  │ (NetworkX)         │   │  │ │
│  │  │  └─────────────┘  └─────────────────────┘   │  │ │
│  │  │                                             │  │ │
│  │  │  ┌─────────────┐  ┌─────────────────────┐   │  │ │
│  │  │  │ SNMP/REST   │  │ Backend Sync        │   │  │ │
│  │  │  │ Poller      │  │ (gRPC client)       │   │  │ │
│  │  │  └─────────────┘  └─────────────────────┘   │  │ │
│  │  └─────────────────────────────────────────────┘  │ │
│  │                                                    │ │
│  │  ┌─────────────────────────────────────────────┐  │ │
│  │  │              Local Storage                   │  │ │
│  │  │  • Flow buffer (last N hours)               │  │ │
│  │  │  • Graph snapshot (switch-graph-1.0 JSON)   │  │ │
│  │  │  • Config cache                             │  │ │
│  │  └─────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │  Switch Data Plane                                │ │
│  │  • Flexible NetFlow → Container (UDP 2055)       │ │
│  │  • EPC samples → Container                       │ │
│  │  • SNMP MIBs → Container                         │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**Edge Container Responsibilities:**
- Collect NetFlow/IPFIX from local switch
- Build per-switch graph (nodes + edges)
- Buffer flows locally (survive backend outage)
- Sync graph summaries to backend
- Respond to on-demand queries from backend

**Container Constraints (App Hosting):**
- Memory: 256MB - 2GB (configurable)
- Storage: 1-4GB flash
- CPU: Shared with switch control plane
- Network: Management VRF or data plane

### Flow Collector Architecture (Non-Container Switches)

For switches that cannot host containers (older Catalyst, third-party):

```
┌─────────────────────────────────────────────────────────┐
│                  Clarion Collector                       │
│  ┌───────────────────────────────────────────────────┐  │
│  │               Protocol Handlers                    │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐           │  │
│  │  │NetFlow v5│ │NetFlow v9│ │  IPFIX   │           │  │
│  │  │ Parser   │ │ Parser   │ │  Parser  │           │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘           │  │
│  │       └────────────┼────────────┘                  │  │
│  │                    ▼                               │  │
│  │            ┌──────────────┐                        │  │
│  │            │  Normalizer  │                        │  │
│  │            │  (Common     │                        │  │
│  │            │   Schema)    │                        │  │
│  │            └──────┬───────┘                        │  │
│  │                   ▼                                │  │
│  │            ┌──────────────┐                        │  │
│  │            │ Per-Switch   │                        │  │
│  │            │ Graph Builder│                        │  │
│  │            └──────┬───────┘                        │  │
│  │                   ▼                                │  │
│  │            ┌──────────────┐                        │  │
│  │            │ Backend Sync │                        │  │
│  │            └──────────────┘                        │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Integration Connectors

| Source | Protocol | Data Retrieved | Sync Frequency |
|--------|----------|----------------|----------------|
| **Cisco ISE** | pxGrid 2.0 (WebSocket) | Sessions, profiles, auth events | Real-time (pub/sub) |
| **Active Directory** | LDAP/LDAPS | Users, groups, OUs, memberships | Every 15 min (delta sync) |
| **CMDB (ServiceNow)** | REST API | Assets, owners, criticality, location | Every 1 hour |
| **Infoblox/DHCP** | REST API / DHCP snooping | IP leases, DNS names | Every 5 min |
| **IoT Inventory** | REST API (varies) | Device profiles, classifications | Every 1 hour |
| **Network Inventory** | DNA Center API | Switches, sites, fabric domains | Every 1 hour |

### Data Flow Summary

```
                        EDGE PROCESSING
                              │
     ┌────────────────────────┼────────────────────────┐
     │                        │                        │
     ▼                        ▼                        ▼
┌─────────┐            ┌─────────┐            ┌─────────┐
│ Cat 9K  │            │ Cat 9K  │            │ Legacy  │
│ + Edge  │            │ + Edge  │            │ Switch  │
│Container│            │Container│            │         │
└────┬────┘            └────┬────┘            └────┬────┘
     │                      │                      │
     │ Graph                │ Graph                │ NetFlow
     │ Summary              │ Summary              │
     │                      │                      │
     └──────────┬───────────┴───────────┬──────────┘
               │                        │
               ▼                        ▼
        ┌────────────┐          ┌────────────┐
        │  Backend   │◀─────────│  Collector │
        │  Ingest    │          │            │
        └─────┬──────┘          └────────────┘
              │
              ▼
        ┌─────────────────────────────────────────────┐
        │              CENTRAL PROCESSING              │
        │                                              │
        │  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
        │  │ Identity │◀─│ ISE      │  │ AD       │  │
        │  │ Resolver │  │ Connector│  │ Connector│  │
        │  └────┬─────┘  └──────────┘  └──────────┘  │
        │       │                                     │
        │       ▼                                     │
        │  ┌──────────┐  ┌──────────┐                │
        │  │ Behavior │──▶│ Policy   │                │
        │  │ Analyzer │  │ Engine   │                │
        │  └──────────┘  └──────────┘                │
        │                      │                      │
        │                      ▼                      │
        │               ┌──────────┐                  │
        │               │ ISE/DNAC │                  │
        │               │ Export   │                  │
        │               └──────────┘                  │
        │                                              │
        └──────────────────────────────────────────────┘
```

### Component Overview

| Tier | Component | Responsibility |
|------|-----------|----------------|
| **Edge** | Clarion Edge Container | Collect flows, build local graph, sync to backend |
| **Collector** | Flow Collector | Receive NetFlow/IPFIX from non-container switches |
| **Backend** | Ingest Service | Aggregate flows and graphs from all sources |
| **Backend** | Identity Resolver | Join flows → ISE sessions → AD users → endpoints |
| **Backend** | Analysis Engine | Behavior clustering, pattern detection, anomalies |
| **Backend** | Policy Engine | SGT recommendation, SGACL generation, matrix |
| **Backend** | API/UI Service | REST API, web dashboard, reports |
| **Integration** | ISE Connector | pxGrid subscription for real-time sessions |
| **Integration** | AD Connector | LDAP sync for users and groups |
| **Integration** | CMDB Connector | Asset context and ownership |

---

## 4. Data Model

### 4.1 Entity Types (Graph Nodes)

| Entity | Key Attributes | Source |
|--------|----------------|--------|
| **User** | user_id, username, email, department, title | AD |
| **Group** | group_id, name, type (department/role) | AD |
| **Endpoint** | device_id, mac, hostname, device_type, os | ISE/Endpoint DB |
| **Switch** | switch_id, site, role, model | Network Inventory |
| **Interface** | switch_id, interface, role (access/uplink), vlan | Switch Config |
| **Service** | service_id, name, type, ip, ports, proto | Service Catalog |
| **IP** | ip_address, vlan, assignment_type, lease_time | DHCP/Static |
| **SGT** | sgt_value, sgt_name, status (seed/proposed/active) | TrustSec Config |

### 4.2 Relationship Types (Graph Edges)

| Relationship | From → To | Attributes |
|--------------|-----------|------------|
| `MEMBER_OF` | User → Group | - |
| `OWNS` | User → Endpoint | ownership_type |
| `ASSIGNED_IP` | Endpoint → IP | lease_start, lease_end |
| `ATTACHED_TO` | Endpoint → Interface | vlan, auth_method |
| `ON_SWITCH` | Interface → Switch | - |
| `TALKS_TO` | Endpoint → Endpoint/Service | proto, ports, bytes, packets, first_seen, last_seen |
| `TAGGED_AS` | Endpoint → SGT | source (manual/inferred/ise) |
| `ALLOWED_TO` | SGT → SGT | sgacl_name, action, ports |

### 4.3 Flow Record Schema

```python
@dataclass
class FlowRecord:
    flow_id: str
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    proto: str              # tcp, udp, icmp
    bytes: int
    packets: int
    vlan: int
    exporter_switch_id: str
    ingress_interface: str
    start_time: datetime
    end_time: datetime
    src_mac: Optional[str]
    src_sgt: Optional[int]  # Often 0/unknown initially
    dst_sgt: Optional[int]
```

### 4.4 Enriched Edge Schema

```python
@dataclass
class EnrichedEdge:
    # Source identity
    src_user: Optional[str]
    src_user_groups: List[str]
    src_device: str
    src_device_type: str
    src_location: str       # site/switch/port
    
    # Destination identity  
    dst_service: Optional[str]
    dst_service_type: Optional[str]
    dst_device: Optional[str]
    
    # Communication metadata
    proto: str
    dst_ports: List[int]
    total_bytes: int
    total_packets: int
    flow_count: int
    first_seen: datetime
    last_seen: datetime
    confidence: float       # 0.0-1.0
    
    # TrustSec context
    src_sgt: Optional[int]
    dst_sgt: Optional[int]
    recommended_src_sgt: Optional[int]
    recommended_dst_sgt: Optional[int]
```

---

## 5. Processing Pipeline

### Phase 1: Observe Reality (No SGTs Required)

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Ingest    │───▶│   Normalize │───▶│   Store     │
│   Flows     │    │   & Dedupe  │    │   Raw       │
└─────────────┘    └─────────────┘    └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │  Aggregate  │
                   │  Time Buckets│
                   └─────────────┘
```

**Outputs:**
- Raw flow store (time-partitioned)
- Aggregated edges (5-min/hourly/daily buckets)
- Top talkers / top services

### Phase 2: Resolve Identity

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Flow      │───▶│   Join IP   │───▶│   Join      │
│   Record    │    │   Bindings  │    │   Endpoint  │
└─────────────┘    └─────────────┘    └─────────────┘
                                            │
        ┌───────────────────────────────────┤
        ▼                                   ▼
 ┌─────────────┐                     ┌─────────────┐
 │   Join      │                     │   Join      │
 │   User/AD   │                     │   Service   │
 └─────────────┘                     └─────────────┘
        │                                   │
        └───────────────┬───────────────────┘
                        ▼
                 ┌─────────────┐
                 │  Enriched   │
                 │    Edge     │
                 └─────────────┘
```

**Join Priority (Conflict Resolution):**
1. ISE session identity (authenticated) > inferred
2. Most recent session within TTL wins
3. Flag collisions (IP reuse, MAC randomization)

### Phase 3: Recommend SGT Taxonomy

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Enriched   │───▶│   Cluster   │───▶│  Propose    │
│   Edges     │    │   Behavior  │    │   SGTs      │
└─────────────┘    └─────────────┘    └─────────────┘
```

**Clustering Signals:**
- AD group membership
- ISE endpoint profile
- VLAN/subnet membership
- Behavioral patterns (who they talk to)
- Switch/port location (access edge vs. datacenter)

**Initial SGT Recommendations (6-12 groups):**
| SGT | Name | Detection Method |
|-----|------|------------------|
| 2 | Corp-Users | AD group: All-Employees, device_type=laptop |
| 3 | Privileged-IT | AD group: Privileged-IT or Network-Admins |
| 10 | Domain-Services | Service type: directory/name_service |
| 11 | Shared-Services | Service type: file/proxy |
| 12 | ERP | Service type: business_app (ERP) |
| 13 | HR-Apps | Service type: business_app (HRIS) |
| 20 | Printers | Endpoint profile: Printer |
| 21 | IoT | Endpoint profile: IoT-* |

### Phase 4: Generate Policy Matrix

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  SGT-Tagged │───▶│   Build     │───▶│  Generate   │
│   Edges     │    │   Matrix    │    │   SGACLs    │
└─────────────┘    └─────────────┘    └─────────────┘
```

**Matrix Cell Structure:**
```python
@dataclass
class MatrixCell:
    src_sgt: int
    dst_sgt: int
    observed_ports: Dict[str, int]  # port/proto → flow_count
    observed_bytes: int
    first_seen: datetime
    last_seen: datetime
    flow_confidence: float
    recommended_action: str         # PERMIT, DENY, MONITOR
    recommended_sgacl: List[str]    # ACE lines
    affected_users: int
    affected_endpoints: int
```

### Phase 5: Safe Rollout

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Proposed   │───▶│   Deploy    │───▶│   Collect   │
│   Policy    │    │   Monitor   │    │   Hits      │
└─────────────┘    └─────────────┘    └─────────────┘
                                            │
                                            ▼
                                     ┌─────────────┐
                                     │  Validate   │
                                     │  & Promote  │
                                     └─────────────┘
```

**Workflow:**
1. Stage policy changes
2. Deploy in SGACL Monitor Mode
3. Collect "would-have-dropped" stats
4. Review impact
5. Promote to enforce (or refine)

---

## 6. Technology Stack

### Production Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Language** | Python 3.11+ | Data processing, ML, ecosystem |
| **Edge Container** | Alpine Linux + Python | Minimal footprint for switch hosting |
| **Backend** | FastAPI + Celery | Async API + background jobs |
| **Flow Ingest** | Apache Kafka | Scalable streaming, replay capability |
| **Time-Series** | ClickHouse | Fast aggregation queries at scale |
| **Graph Store** | Neo4j | Identity relationships, path queries |
| **Relational** | PostgreSQL | Policy storage, configuration |
| **Cache** | Redis | Session cache, pub/sub |
| **Message Queue** | Redis Streams / Kafka | Edge → Backend sync |
| **Frontend** | React + D3.js | Interactive visualization |
| **Containerization** | Docker + Kubernetes | Production deployment |

### Edge Container Stack

| Component | Technology | Constraint |
|-----------|------------|------------|
| **Base Image** | Alpine Linux 3.18 | < 100MB image size |
| **Runtime** | Python 3.11-slim | Standard library + minimal deps |
| **Flow Parser** | Custom (struct.unpack) | No heavy dependencies |
| **Graph** | NetworkX | In-memory, serialize to JSON |
| **Storage** | SQLite | Local flow buffer |
| **Sync** | gRPC / REST | Backend communication |
| **Memory** | 256MB - 512MB | App Hosting limits |
| **Storage** | 1GB flash | Flow buffer + graph snapshots |

### Collector Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| **Base Image** | python:3.11-slim | Standard container |
| **NetFlow Parser** | Custom Python | v5, v9, IPFIX support |
| **sFlow Parser** | python-sflow | Packet sampling |
| **Output** | Kafka / gRPC | Stream to backend |
| **Scaling** | Horizontal | Multiple collectors per region |

### MVP Stack (Development)

| Layer | Technology |
|-------|------------|
| **Language** | Python 3.11 |
| **Data Store** | DuckDB (analytical queries) |
| **Graph** | NetworkX (in-memory) |
| **API** | FastAPI |
| **Frontend** | Streamlit (rapid prototyping) |
| **Container** | Docker Compose |

---

## 7. Project Structure

```
clarion/
├── docs/
│   ├── DESIGN.md              # This document
│   ├── API.md                 # API reference
│   └── DEPLOYMENT.md          # Deployment guide
│
├── data/
│   ├── raw/                   # Original data files
│   │   └── trustsec_copilot_synth_campus/
│   └── processed/             # Transformed data
│
├── src/
│   ├── clarion/               # Backend library
│   │   ├── __init__.py
│   │   ├── config.py          # Configuration management
│   │   │
│   │   ├── ingest/            # Data ingestion
│   │   │   ├── __init__.py
│   │   │   ├── flows.py       # Flow data loader
│   │   │   ├── ise.py         # ISE session loader
│   │   │   └── ad.py          # AD data loader
│   │   │
│   │   ├── identity/          # Identity resolution
│   │   │   ├── __init__.py
│   │   │   ├── resolver.py    # IP → User/Device mapping
│   │   │   └── graph.py       # Identity graph builder
│   │   │
│   │   ├── analysis/          # Traffic analysis
│   │   │   ├── __init__.py
│   │   │   ├── clustering.py  # Behavior clustering
│   │   │   ├── patterns.py    # Pattern detection
│   │   │   └── anomalies.py   # Anomaly detection
│   │   │
│   │   ├── policy/            # Policy generation
│   │   │   ├── __init__.py
│   │   │   ├── sgt.py         # SGT recommendation
│   │   │   ├── matrix.py      # Policy matrix builder
│   │   │   └── sgacl.py       # SGACL generator
│   │   │
│   │   ├── connectors/        # External integrations
│   │   │   ├── __init__.py
│   │   │   ├── ise.py         # ISE pxGrid connector
│   │   │   ├── ad.py          # Active Directory LDAP
│   │   │   ├── cmdb.py        # CMDB (ServiceNow, etc.)
│   │   │   └── dhcp.py        # DHCP/DNS (Infoblox, etc.)
│   │   │
│   │   ├── export/            # Export & integration
│   │   │   ├── __init__.py
│   │   │   ├── ise.py         # ISE policy push
│   │   │   └── reports.py     # Report generation
│   │   │
│   │   └── api/               # REST API
│   │       ├── __init__.py
│   │       ├── main.py        # FastAPI app
│   │       └── routes/        # API endpoints
│   │
│   └── scripts/               # CLI utilities
│       ├── load_data.py       # Load synthetic data
│       ├── analyze.py         # Run analysis
│       └── recommend.py       # Generate recommendations
│
├── edge/                      # Edge container (Cisco App Hosting)
│   ├── Dockerfile             # Container image
│   ├── iox-app.yaml           # IOx app descriptor
│   ├── package.yaml           # Package metadata
│   │
│   ├── clarion_edge/          # Edge Python package
│   │   ├── __init__.py
│   │   ├── config.py          # Edge configuration
│   │   ├── collector.py       # Flow listener (UDP 2055)
│   │   ├── graph.py           # Local graph builder
│   │   ├── buffer.py          # Flow buffer (local storage)
│   │   ├── sync.py            # Backend sync (gRPC client)
│   │   └── api.py             # Edge REST API
│   │
│   ├── scripts/
│   │   └── entrypoint.sh      # Container entrypoint
│   │
│   └── tests/
│       └── test_edge.py
│
├── collector/                 # Flow collector (non-container switches)
│   ├── Dockerfile
│   ├── docker-compose.yml
│   │
│   ├── clarion_collector/     # Collector Python package
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── netflow.py         # NetFlow v5/v9 parser
│   │   ├── ipfix.py           # IPFIX parser
│   │   ├── sflow.py           # sFlow parser
│   │   ├── normalizer.py      # Common schema normalizer
│   │   └── exporter.py        # Backend export
│   │
│   └── tests/
│       └── test_collector.py
│
├── lab/                       # NetFlow lab (VM simulation)
│   ├── setup_vm.sh
│   ├── cleanup_vm.sh
│   ├── check_status.sh
│   └── build_switch_graph.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── notebooks/                 # Jupyter exploration
│   └── exploration.ipynb
│
├── deploy/                    # Deployment artifacts
│   ├── docker-compose.yml     # Full stack local
│   ├── k8s/                   # Kubernetes manifests
│   └── ansible/               # Switch deployment playbooks
│
├── pyproject.toml
├── requirements.txt
├── Makefile
└── README.md
```

---

## 8. MVP Milestones

### MVP 1: Identity-Labeled Flow Graph (Week 1-2)

**Goal:** Load synthetic data, resolve identities, build communication graph

**Deliverables:**
- [ ] Data loaders for all CSV files
- [ ] Identity resolver (flow → user/device/service)
- [ ] NetworkX graph with enriched edges
- [ ] CLI: `clarion load` and `clarion graph`
- [ ] Basic stats output

**Success Criteria:**
- Load 100K+ flows in < 30 seconds
- Resolve 90%+ of flows to endpoint/user
- Graph query: "Show all communications for user X"

### MVP 2: SGT Taxonomy Recommender (Week 3-4)

**Goal:** Cluster endpoints and recommend initial SGT assignments

**Deliverables:**
- [ ] Behavior clustering algorithm
- [ ] SGT recommendation engine
- [ ] Coverage analysis ("% of traffic with SGT")
- [ ] CLI: `clarion recommend-sgts`
- [ ] Tagging report (CSV/JSON export)

**Success Criteria:**
- Recommend 6-12 meaningful SGTs
- 80%+ endpoint coverage
- Human-readable justification per SGT

### MVP 3: Policy Matrix Generator (Week 5-6)

**Goal:** Build SGT→SGT matrix with SGACL recommendations

**Deliverables:**
- [ ] Matrix builder from enriched edges
- [ ] SGACL generator (allow-list per cell)
- [ ] "What breaks if we enforce?" simulator
- [ ] CLI: `clarion policy-matrix`
- [ ] Matrix visualization (heatmap)

**Success Criteria:**
- Generate matrix for all observed SGT pairs
- SGACL rules match observed traffic patterns
- Impact analysis identifies critical dependencies

### MVP 4: API & Basic UI (Week 7-8)

**Goal:** REST API and simple web interface

**Deliverables:**
- [ ] FastAPI backend with key endpoints
- [ ] Streamlit dashboard
- [ ] Graph visualization (D3.js or similar)
- [ ] Export to ISE-ready format

**Success Criteria:**
- API response < 500ms for common queries
- Interactive exploration of identity graph
- One-click policy export

---

## 9. Key Algorithms

### 9.1 Identity Resolution

```python
def resolve_identity(flow: FlowRecord, 
                     ip_bindings: DataFrame,
                     ise_sessions: DataFrame,
                     endpoints: DataFrame,
                     users: DataFrame) -> EnrichedEdge:
    """
    Join flow to identity context with confidence scoring.
    
    Priority:
    1. ISE session (authenticated) - confidence 1.0
    2. IP binding (DHCP/static) - confidence 0.8
    3. Endpoint match (MAC) - confidence 0.7
    4. Unknown - confidence 0.0
    """
    # Time-bounded join to IP bindings
    binding = ip_bindings.query(
        f"ip == '{flow.src_ip}' and "
        f"lease_start <= '{flow.start_time}' and "
        f"lease_end >= '{flow.start_time}'"
    )
    
    # Join to ISE session for user context
    session = ise_sessions.query(
        f"ip == '{flow.src_ip}' and "
        f"session_start <= '{flow.start_time}' and "
        f"session_end >= '{flow.start_time}'"
    )
    
    # Build enriched edge...
```

### 9.2 Behavior Clustering

```python
def cluster_endpoints(edges: List[EnrichedEdge],
                      endpoints: DataFrame,
                      users: DataFrame) -> Dict[str, List[str]]:
    """
    Cluster endpoints by behavior patterns.
    
    Features:
    - Destination services accessed
    - Port/protocol distribution
    - Time-of-day patterns
    - AD group membership
    - ISE endpoint profile
    - VLAN/site location
    """
    # Build feature matrix
    features = build_behavior_features(edges, endpoints, users)
    
    # Cluster with hybrid approach:
    # 1. Rule-based for known patterns (servers, printers, IoT)
    # 2. ML clustering for ambiguous endpoints
    
    clusters = {}
    
    # Rule-based: servers (receive > send)
    servers = identify_servers(edges)
    clusters['servers'] = servers
    
    # Rule-based: IoT (limited service access)
    iot = identify_iot(edges, endpoints)
    clusters['iot'] = iot
    
    # ML: cluster remaining by behavior
    remaining = [e for e in endpoints if e not in servers + iot]
    ml_clusters = kmeans_cluster(features[remaining])
    
    return clusters
```

### 9.3 SGACL Generation

```python
def generate_sgacl(src_sgt: int, dst_sgt: int,
                   observed_traffic: List[EnrichedEdge]) -> List[str]:
    """
    Generate SGACL rules from observed traffic patterns.
    
    Strategy:
    - Allow stable, high-volume flows
    - Flag rare/one-off flows for review
    - Default deny for unobserved
    """
    # Aggregate by port/proto
    port_stats = aggregate_by_port(observed_traffic)
    
    rules = []
    for (proto, port), stats in port_stats.items():
        if stats['flow_count'] > STABILITY_THRESHOLD:
            if proto == 'tcp':
                rules.append(f"permit tcp dst eq {port}")
            elif proto == 'udp':
                rules.append(f"permit udp dst eq {port}")
    
    # Always deny at the end
    rules.append("deny ip")
    
    return rules
```

---

## 10. API Endpoints (Draft)

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/graph/nodes` | List all nodes (filtered) |
| GET | `/api/v1/graph/edges` | List all edges (filtered) |
| GET | `/api/v1/graph/node/{id}` | Get node details |
| GET | `/api/v1/graph/neighbors/{id}` | Get node neighbors |
| GET | `/api/v1/users/{id}/communications` | User's traffic |
| GET | `/api/v1/endpoints/{id}/communications` | Endpoint's traffic |
| GET | `/api/v1/services` | List known services |
| GET | `/api/v1/sgts` | List SGT taxonomy |
| GET | `/api/v1/sgts/recommendations` | Get SGT recommendations |
| GET | `/api/v1/matrix` | Get policy matrix |
| GET | `/api/v1/matrix/{src_sgt}/{dst_sgt}` | Get matrix cell details |
| GET | `/api/v1/sgacls/{src_sgt}/{dst_sgt}` | Get SGACL for cell |
| POST | `/api/v1/export/ise` | Export to ISE format |

---

## 11. Success Metrics

### Technical Metrics

| Metric | Target |
|--------|--------|
| Flow ingestion rate | > 10,000 flows/sec |
| Identity resolution rate | > 95% of flows |
| Query latency (p95) | < 500ms |
| Graph traversal | < 100ms for 2-hop |

### Business Metrics

| Metric | Target |
|--------|--------|
| SGT coverage | > 90% of endpoints |
| Policy accuracy | > 85% match observed traffic |
| Time to first policy | < 1 hour from data load |
| False positive rate (would-deny) | < 5% |

---

## 12. Open Questions

### Architecture
1. **Edge container sizing**: 256MB vs 512MB memory for App Hosting?
2. **Sync protocol**: gRPC (efficient) vs REST (simpler)?
3. **Edge buffering**: How many hours of flows to buffer locally?
4. **Collector placement**: Per-site or centralized?

### Data & Scale
5. **Graph database**: When to move from NetworkX to Neo4j?
6. **Real-time vs. batch**: Start batch, add streaming later?
7. **Historical analysis**: How far back to look? (7 days? 30 days?)
8. **Flow sampling**: Accept sampled flows or require full capture?

### Integration
9. **ISE integration**: Push policies directly or export for manual import?
10. **pxGrid version**: pxGrid 2.0 (WebSocket) vs 1.0 (REST)?
11. **AD sync**: Full sync vs delta? How often?
12. **Multi-domain**: Support multiple AD forests?

### Business
13. **Multi-tenancy**: Single customer focus for MVP?
14. **Deployment model**: On-prem only or SaaS option?
15. **Licensing**: Per-switch, per-endpoint, or flat?

---

## 13. References

- [Cisco TrustSec Overview](https://www.cisco.com/c/en/us/td/docs/switches/lan/trustsec/configuration/guide/trustsec.html)
- [Cisco pxGrid Session Directory](https://developer.cisco.com/docs/pxgrid/)
- [Catalyst 9300 Flexible NetFlow](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-9/configuration_guide/fnf/b_179_fnf_9300_cg.html)
- [SGACL Configuration Guide](https://www.cisco.com/c/en/us/td/docs/switches/lan/trustsec/configuration/guide/trustsec/sgacl_config.html)

---

*Document Version: 1.0*  
*Last Updated: December 2024*  
*Author: Clarion Development Team*

