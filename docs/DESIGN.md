# Clarion - TrustSec Policy Copilot

## Design Document v2.0

> **Status:** ✅ MVP Implementation Complete  
> All 5 core phases have been implemented and tested. The system is functional and ready for evaluation with synthetic data.

---

## 1. Executive Summary

**Clarion** is a scale-first network visibility and policy design platform that helps organizations adopt Cisco TrustSec. It uses **edge processing** on switches to compress network telemetry into lightweight behavioral sketches, then applies **unsupervised learning** to cluster endpoints and generate SGT (Security Group Tag) taxonomies and SGACL policies.

### Core Value Proposition

> *"Process at the edge, cluster intelligently, generate policy automatically — at any scale."*

### Key Differentiators

| Challenge | Traditional Approach | Clarion Approach |
|-----------|---------------------|------------------|
| **Data Volume** | Ship all flows centrally | Compress to sketches at edge |
| **Clustering** | Batch processing nightly | Incremental real-time updates |
| **Scale** | Central bottleneck | Horizontally distributed |
| **Memory** | O(flows) | O(endpoints) |

---

## 2. Problem Statement

### Customer Pain Points

1. **TrustSec adoption is hard**: Customers struggle to define SGT taxonomies and policies from scratch
2. **Data overload**: Flow collectors can't handle enterprise-scale traffic
3. **No intelligent grouping**: Manual SGT assignment doesn't scale
4. **Identity chaos**: IP addresses change; mapping flows to users/devices requires complex joins
5. **Fear of breaking things**: Enforcement without validation causes outages

### What Clarion Solves

| Problem | Clarion Solution |
|---------|------------------|
| Data overload | Edge sketches reduce data 10,000x before transmission |
| No SGTs defined | Unsupervised learning clusters endpoints into natural groups |
| Unknown traffic patterns | Behavioral profiles track who talks to whom |
| Can't map IPs to users | Join sketches with ISE sessions and AD groups |
| Fear of enforcement | Monitor-mode validation before enforcement |

---

## 3. System Architecture

### Design Principles

1. **Edge-Heavy Processing**: Compress at the source, don't ship raw flows
2. **Sketch-Based**: Probabilistic data structures for bounded memory
3. **Incremental ML**: Clustering that updates without reprocessing
4. **Hierarchical Clustering**: Local clusters → Global clusters → SGT mapping
5. **Stateless Edge**: Edge can restart without losing global state

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EDGE TIER (Per-Switch)                          │
│                         Memory: 256-512MB | CPU: Minimal                      │
│                         Endpoints: 48-500 per switch                          │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                    Clarion Edge (Lightweight)                            │ │
│  │                                                                          │ │
│  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                │ │
│  │  │ Flow Sampler │──▶│ Aggregator   │──▶│ Sketch       │                │ │
│  │  │ (1:N sample) │   │ (5-min bins) │   │ Builder      │                │ │
│  │  └──────────────┘   └──────────────┘   └──────┬───────┘                │ │
│  │                                               │                         │ │
│  │                                               ▼                         │ │
│  │  ┌────────────────────────────────────────────────────────────────┐    │ │
│  │  │               Per-Endpoint Behavioral Sketch                    │    │ │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │    │ │
│  │  │  │ Service     │  │ Port/Proto  │  │ Peer Count  │             │    │ │
│  │  │  │ Histogram   │  │ Distribution│  │ (HyperLogLog)│            │    │ │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘             │    │ │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │    │ │
│  │  │  │ Bytes In/Out│  │ Flow Count  │  │ Active Hours│             │    │ │
│  │  │  │ Ratio       │  │ (per dest)  │  │ Bitmap      │             │    │ │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘             │    │ │
│  │  └────────────────────────────────────────────────────────────────┘    │ │
│  │                                               │                         │ │
│  │                                               ▼                         │ │
│  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                │ │
│  │  │ Local Cluster│──▶│ Sketch Sync  │──▶│ gRPC Stream  │────────────────┼─┼──▶
│  │  │ (K-Means Lite)│  │ (Delta only)│   │ to Backend   │                │ │
│  │  └──────────────┘   └──────────────┘   └──────────────┘                │ │
│  │                                                                          │ │
│  └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
                                        │
                          Behavioral Sketches (KB, not GB)
                                        │
                                        ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND TIER (Scalable)                           │
│                                                                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                         Sketch Aggregation Layer                         │  │
│  │                                                                          │  │
│  │   Switch-1 ──┐                                                          │  │
│  │   Switch-2 ──┼──▶ ┌──────────────────────────────────────────────────┐  │  │
│  │   Switch-3 ──┤    │         Global Endpoint Profile Store            │  │  │
│  │      ...   ──┤    │                                                  │  │  │
│  │   Switch-N ──┘    │  Endpoint-A: [merged sketch from all switches]  │  │  │
│  │                   │  Endpoint-B: [merged sketch from all switches]  │  │  │
│  │                   │  ...                                            │  │  │
│  │                   └──────────────────────────────────────────────────┘  │  │
│  │                                        │                                 │  │
│  └────────────────────────────────────────┼─────────────────────────────────┘  │
│                                           │                                    │
│  ┌────────────────────────────────────────▼─────────────────────────────────┐  │
│  │                        Unsupervised Learning Engine                       │  │
│  │                                                                           │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐          │  │
│  │  │ Feature         │  │ Incremental     │  │ Cluster         │          │  │
│  │  │ Engineering     │──▶ Clustering      │──▶ Refinement      │          │  │
│  │  │                 │  │ (Mini-Batch     │  │ (Merge/Split)   │          │  │
│  │  │ • Normalize     │  │  K-Means,       │  │                 │          │  │
│  │  │ • PCA/UMAP      │  │  HDBSCAN)       │  │                 │          │  │
│  │  └─────────────────┘  └─────────────────┘  └────────┬────────┘          │  │
│  │                                                      │                   │  │
│  │  ┌─────────────────┐  ┌─────────────────┐           │                   │  │
│  │  │ Cluster →       │◀─┤ Semantic        │◀──────────┘                   │  │
│  │  │ SGT Mapping     │  │ Labeling        │                               │  │
│  │  │                 │  │ (AD groups,     │                               │  │
│  │  │                 │  │  ISE profiles)  │                               │  │
│  │  └────────┬────────┘  └─────────────────┘                               │  │
│  │           │                                                              │  │
│  └───────────┼──────────────────────────────────────────────────────────────┘  │
│              │                                                                  │
│              ▼                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                           Policy Engine                                    │ │
│  │                                                                            │ │
│  │  Cluster-A (Corp-Users) ──┐     ┌─────────────────────────────────────┐  │ │
│  │  Cluster-B (Servers)    ──┼────▶│  SGT → SGT Policy Matrix            │  │ │
│  │  Cluster-C (IoT)        ──┤     │  + SGACL Generation                 │  │ │
│  │  Cluster-D (Printers)   ──┘     │  + Impact Simulation                │  │ │
│  │                                 └─────────────────────────────────────┘  │ │
│  │                                                                            │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
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
│  │ • Auth     │  │ • OUs      │  │ • Critical │  │ • Subnets  │  │            │ │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘  └────────────┘ │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Edge Processing Design

### Memory Budget (Catalyst 9K App Hosting)

| Resource | Limit | Clarion Usage |
|----------|-------|---------------|
| Memory | 256-512MB | ~50MB for sketches + 100MB runtime |
| Storage | 1-4GB | Flow buffer + sketch snapshots |
| CPU | Shared | Minimal (aggregation only) |

### Endpoint Capacity Per Switch

| Switch Type | Ports | With Wireless | Sketch Memory |
|-------------|-------|---------------|---------------|
| Access (Cat 9300) | 24-48 | 100-300 | 3MB |
| Distribution | 48 | 200-500 | 5MB |
| Conservative Max | - | 500 | 5MB |

### Behavioral Sketch Data Structure

Each endpoint gets a lightweight sketch (~10KB) that summarizes its behavior:

```python
@dataclass
class EndpointSketch:
    """
    Lightweight behavioral fingerprint per endpoint.
    Designed to fit in edge container memory constraints.
    
    Memory: ~10KB per endpoint
    500 endpoints = 5MB total
    """
    endpoint_id: str              # MAC address or device_id
    switch_id: str                # Source switch
    
    # Cardinality estimation (HyperLogLog)
    unique_peers: bytes           # ~1KB - unique IPs contacted
    unique_services: bytes        # ~1KB - unique services accessed
    
    # Frequency distribution (Count-Min Sketch)
    port_frequency: bytes         # ~4KB - port usage distribution
    service_frequency: bytes      # ~4KB - service access patterns
    
    # Simple aggregates
    bytes_in: int
    bytes_out: int
    packets_in: int
    packets_out: int
    flow_count: int
    
    # Temporal metadata
    first_seen: int               # Unix timestamp
    last_seen: int                # Unix timestamp
    active_hours: int             # 24-bit bitmap (1 bit per hour)
    
    # Local clustering (edge-computed)
    local_cluster_id: int         # K-means assignment (0-7)
    
    # Sync metadata
    last_sync: int                # Last backend sync timestamp
    sketch_version: int           # For delta sync
```

### Probabilistic Data Structures

| Structure | Size | Purpose | Error Rate |
|-----------|------|---------|------------|
| **HyperLogLog** | 1KB | Count unique peers/services | ~2% |
| **Count-Min Sketch** | 4KB | Port/service frequency | Configurable |
| **Bloom Filter** | 1KB | "Has talked to X?" | 1% false positive |

### Edge Processing Pipeline

```
NetFlow/IPFIX (UDP 2055)
         │
         ▼
┌─────────────────────┐
│   Flow Receiver     │  ← Receive raw flow records
│   (async UDP)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Flow Sampler      │  ← Optional 1:N sampling for high volume
│   (configurable)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Aggregator        │  ← 5-minute time buckets
│   (time windows)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Sketch Updater    │  ← Update per-endpoint sketches
│   (HLL, CMS)        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Local Clusterer   │  ← Lightweight K-means (k=8)
│   (mini-batch)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Backend Sync      │  ← gRPC stream, delta only
│   (periodic)        │
└─────────────────────┘
```

---

## 5. Unsupervised Learning Pipeline

### Clustering Strategy

| Layer | Algorithm | Purpose | Frequency |
|-------|-----------|---------|-----------|
| **Edge** | Mini-Batch K-Means (k=8) | Fast local grouping | Every 5 min |
| **Backend** | HDBSCAN | Find natural cluster shapes | Every hour |
| **Refinement** | Hierarchical Merging | Combine similar clusters | Daily |

### Feature Engineering

Features extracted from behavioral sketches for clustering:

```python
@dataclass
class ClusteringFeatures:
    """
    Normalized feature vector for clustering.
    Extracted from EndpointSketch.
    """
    # Communication patterns (from HyperLogLog)
    peer_diversity: float         # 0-1: few peers vs many peers
    service_diversity: float      # 0-1: few services vs many
    
    # Traffic profile (from aggregates)
    in_out_ratio: float          # 0-1: receiver vs sender
    traffic_volume: float        # Normalized bytes
    
    # Port usage (from Count-Min Sketch)
    common_ports_score: float    # Uses 80/443/22 vs exotic ports
    port_diversity: float        # Few ports vs many ports
    
    # Temporal patterns
    business_hours_ratio: float  # % traffic during 9-5
    weekend_activity: float      # % traffic on weekends
    
    # Identity context (from ISE/AD join)
    has_user: bool               # Authenticated user?
    user_group_vector: List[float]  # AD group membership (embedded)
    device_type_vector: List[float] # ISE profile (embedded)
```

### Clustering to SGT Mapping

```
┌─────────────────────────────────────────────────────────────────┐
│                  CLUSTER → SGT MAPPING PROCESS                   │
│                                                                  │
│  Step 1: Unsupervised Clustering                                │
│  ────────────────────────────────                               │
│  HDBSCAN identifies natural groupings based on behavior:        │
│                                                                  │
│  Cluster-0: [laptop-1, laptop-2, ..., laptop-500]               │
│  Cluster-1: [server-1, server-2, ..., server-20]                │
│  Cluster-2: [printer-1, printer-2, ..., printer-15]             │
│  Cluster-3: [iot-cam-1, iot-sensor-1, ..., iot-50]              │
│                                                                  │
│  Step 2: Semantic Labeling                                      │
│  ─────────────────────────                                      │
│  Join with identity sources to name clusters:                   │
│                                                                  │
│  Cluster-0 → 80% have users in "All-Employees" AD group         │
│           → Label: "Corporate Users"                            │
│                                                                  │
│  Cluster-1 → 90% receive traffic, ISE profile "Server"          │
│           → Label: "Servers"                                    │
│                                                                  │
│  Cluster-2 → ISE profile "Printer", limited port usage          │
│           → Label: "Printers"                                   │
│                                                                  │
│  Cluster-3 → ISE profile "IoT-*", single service access         │
│           → Label: "IoT Devices"                                │
│                                                                  │
│  Step 3: SGT Assignment                                         │
│  ──────────────────────                                         │
│                                                                  │
│  "Corporate Users"  → SGT 2 (Corp-Users)                        │
│  "Servers"          → SGT 10 (Servers)                          │
│  "Printers"         → SGT 20 (Printers)                         │
│  "IoT Devices"      → SGT 21 (IoT)                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Incremental Clustering

```python
class IncrementalClusterer:
    """
    Updates clusters without reprocessing all data.
    
    Design for streaming:
    - New endpoints → assign to nearest existing cluster
    - Changed behavior → may trigger reassignment
    - Periodic refinement → merge/split clusters
    """
    
    def __init__(self):
        self.cluster_centroids: Dict[int, np.ndarray] = {}
        self.assignments: Dict[str, int] = {}
        self.confidence: Dict[str, float] = {}
    
    def assign_new_endpoint(self, sketch: EndpointSketch) -> int:
        """Fast path: assign to nearest existing cluster."""
        features = self.extract_features(sketch)
        distances = {
            cid: np.linalg.norm(features - centroid)
            for cid, centroid in self.cluster_centroids.items()
        }
        cluster_id = min(distances, key=distances.get)
        confidence = 1.0 / (1.0 + distances[cluster_id])
        
        self.assignments[sketch.endpoint_id] = cluster_id
        self.confidence[sketch.endpoint_id] = confidence
        return cluster_id
    
    def refine_clusters(self, all_sketches: List[EndpointSketch]):
        """Slow path: re-cluster with HDBSCAN, merge with existing."""
        features = np.array([self.extract_features(s) for s in all_sketches])
        
        clusterer = hdbscan.HDBSCAN(min_cluster_size=10)
        labels = clusterer.fit_predict(features)
        
        # Merge new clusters with existing taxonomy
        self._merge_with_existing(labels, all_sketches)
```

---

## 6. Data Model

### Entity Types (Graph Nodes)

| Entity | Key Attributes | Source |
|--------|----------------|--------|
| **Endpoint** | endpoint_id, mac, device_type, sketch | Edge Sketches |
| **User** | user_id, username, department | AD |
| **Group** | group_id, name, type | AD |
| **Service** | service_id, name, ports | Service Catalog |
| **Cluster** | cluster_id, label, sgt_mapping | ML Engine |
| **SGT** | sgt_value, sgt_name | TrustSec |

### Relationship Types (Graph Edges)

| Relationship | From → To | Attributes |
|--------------|-----------|------------|
| `MEMBER_OF` | User → Group | - |
| `OWNS` | User → Endpoint | ownership_type |
| `TALKS_TO` | Endpoint → Endpoint/Service | flow_count, bytes, ports |
| `BELONGS_TO` | Endpoint → Cluster | confidence |
| `MAPS_TO` | Cluster → SGT | confidence |
| `ALLOWED` | SGT → SGT | sgacl, ports |

### Flow Record Schema (Raw Input)

```python
@dataclass
class FlowRecord:
    """Raw flow from NetFlow/IPFIX - processed at edge, not stored."""
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    proto: str              # tcp, udp, icmp
    bytes: int
    packets: int
    src_mac: Optional[str]
    exporter_switch: str
    timestamp: datetime
```

### Enriched Communication (Backend Output)

```python
@dataclass
class EnrichedCommunication:
    """Aggregated, identity-resolved communication pattern."""
    src_endpoint: str
    src_cluster: int
    src_sgt: int
    src_user: Optional[str]
    
    dst_endpoint: Optional[str]
    dst_service: Optional[str]
    dst_cluster: int
    dst_sgt: int
    
    proto: str
    ports: List[int]
    total_bytes: int
    flow_count: int
    first_seen: datetime
    last_seen: datetime
    confidence: float
```

---

## 7. Policy Generation

### SGT → SGT Matrix

```python
@dataclass
class PolicyMatrixCell:
    """One cell in the SGT × SGT policy matrix."""
    src_sgt: int
    src_sgt_name: str
    dst_sgt: int
    dst_sgt_name: str
    
    # Observed traffic
    observed_ports: Dict[str, int]  # "tcp/443" → flow_count
    total_bytes: int
    endpoint_pairs: int
    first_seen: datetime
    last_seen: datetime
    
    # Policy recommendation
    recommended_action: str         # PERMIT, DENY, MONITOR
    recommended_sgacl: List[str]    # ACE lines
    confidence: float
    
    # Impact analysis
    affected_endpoints: int
    affected_users: int
    critical_services: List[str]
```

### SGACL Generation Algorithm

```python
def generate_sgacl(src_sgt: int, dst_sgt: int,
                   observed_traffic: List[EnrichedCommunication],
                   min_confidence: float = 0.8) -> List[str]:
    """
    Generate SGACL rules from observed traffic patterns.
    
    Strategy:
    1. Allow stable, high-volume flows
    2. Flag rare/one-off flows for review
    3. Default deny for unobserved
    """
    rules = []
    
    # Aggregate by port/proto
    port_stats = aggregate_by_port(observed_traffic)
    
    for (proto, port), stats in sorted(port_stats.items(), 
                                        key=lambda x: -x[1]['flow_count']):
        if stats['confidence'] >= min_confidence:
            if proto == 'tcp':
                rules.append(f"permit tcp dst eq {port}")
            elif proto == 'udp':
                rules.append(f"permit udp dst eq {port}")
    
    # Always deny at the end
    rules.append("deny ip log")
    
    return rules
```

---

## 8. Technology Stack

### Production Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Language** | Python 3.11+ | ML ecosystem, async support |
| **Edge Container** | Alpine Linux + Python | Minimal footprint |
| **Sketches** | datasketch library | HLL, CMS, MinHash |
| **Clustering** | scikit-learn, hdbscan | Incremental K-means, HDBSCAN |
| **Backend API** | FastAPI + asyncio | High-performance async |
| **Message Queue** | Redis Streams | Edge → Backend sync |
| **Graph Store** | NetworkX → Neo4j | Start simple, scale later |
| **Time-Series** | DuckDB → ClickHouse | Analytical queries |
| **Frontend** | React + D3.js | Interactive visualization |
| **Serialization** | Protocol Buffers | Efficient sketch sync |

### Edge Container Stack

| Component | Technology | Constraint |
|-----------|------------|------------|
| **Base Image** | python:3.11-alpine | < 100MB image |
| **Sketches** | datasketch | HLL, CMS implementations |
| **Clustering** | Custom mini-batch K-means | No sklearn dependency |
| **Storage** | SQLite | Local sketch buffer |
| **Sync** | gRPC | Efficient streaming |
| **Memory** | 256MB target | 500 endpoints × 10KB + overhead |

---

## 9. Scale Analysis

### Data Reduction at Edge

| Metric | Raw Flows | With Sketches | Reduction |
|--------|-----------|---------------|-----------|
| Per switch/hour | 100K flows × 100B = 10MB | 500 endpoints × 10KB = 5MB | 2x |
| 1000 switches/hour | 10GB | 5MB | 2000x |
| Central storage/day | 240GB | 120MB | 2000x |

### Processing Capacity

| Component | Capacity | Bottleneck |
|-----------|----------|------------|
| Edge (per switch) | 10K flows/sec | UDP receive buffer |
| Backend (single node) | 10K sketch updates/sec | CPU |
| Backend (clustered) | 100K+ sketch updates/sec | Horizontal scaling |

### Memory Requirements

| Deployment | Endpoints | Sketch Storage | Backend RAM |
|------------|-----------|----------------|-------------|
| Small (10 switches) | 5,000 | 50MB | 4GB |
| Medium (100 switches) | 50,000 | 500MB | 16GB |
| Large (1000 switches) | 500,000 | 5GB | 64GB |

---

## 10. Project Structure

```
clarion/
├── docs/
│   ├── DESIGN.md              # This document
│   ├── PROJECT_PLAN.md        # Development roadmap
│   └── API.md                 # API reference
│
├── data/
│   ├── raw/                   # Synthetic datasets
│   │   └── trustsec_copilot_synth_campus/
│   └── processed/             # Transformed data
│
├── src/clarion/               # Backend library
│   ├── __init__.py
│   ├── config.py
│   │
│   ├── sketches/              # Probabilistic data structures
│   │   ├── __init__.py
│   │   ├── endpoint_sketch.py # EndpointSketch dataclass
│   │   ├── hyperloglog.py     # Cardinality estimation
│   │   └── countmin.py        # Frequency estimation
│   │
│   ├── clustering/            # Unsupervised learning
│   │   ├── __init__.py
│   │   ├── features.py        # Feature extraction
│   │   ├── clusterer.py       # HDBSCAN clustering
│   │   ├── labeling.py        # Semantic cluster labeling
│   │   └── sgt_mapper.py      # Cluster → SGT assignment
│   │
│   ├── ingest/                # Data ingestion
│   │   ├── __init__.py
│   │   ├── loader.py          # CSV/synthetic data loader
│   │   └── sketch_builder.py  # Build sketches from flows
│   │
│   ├── identity/              # Identity resolution
│   │   ├── __init__.py
│   │   └── resolver.py        # IP → User/Device mapping
│   │
│   ├── policy/                # Policy generation
│   │   ├── __init__.py
│   │   ├── matrix.py          # SGT → SGT matrix
│   │   ├── sgacl.py           # SGACL generation
│   │   ├── impact.py          # Impact analysis
│   │   ├── exporter.py        # ISE export
│   │   └── customization.py   # Human-in-the-loop review
│   │
│   ├── visualization/        # Visualization tools
│   │   ├── __init__.py
│   │   ├── clusters.py        # Cluster visualization
│   │   └── policy.py          # Policy visualization
│   │
│   ├── api/                   # REST API
│   │   ├── __init__.py
│   │   ├── app.py             # FastAPI application
│   │   └── routes/            # API route handlers
│   │
│   └── ui/                     # User interfaces
│       ├── __init__.py
│       └── admin_console.py   # Legacy Streamlit UI (deprecated)
│
├── edge/                      # Edge container
│   ├── Dockerfile
│   ├── iox-app.yaml           # IOx descriptor
│   ├── clarion_edge/
│   │   ├── __init__.py
│   │   ├── sketch.py          # Edge sketches (pure Python)
│   │   ├── agent.py           # Edge agent with clustering
│   │   ├── simulator.py       # Flow simulator for testing
│   │   ├── streaming.py       # Backend sync (HTTP)
│   │   └── main.py            # CLI entry point
│   └── tests/                 # Edge module tests
│
├── collector/                 # Flow collector (legacy switches)
│   ├── Dockerfile
│   └── clarion_collector/
│
├── tests/
│   ├── unit/                  # Unit tests (102 tests)
│   ├── integration/           # Integration tests (35 tests)
│   └── fixtures/
├── scripts/                   # Utility scripts
│   ├── run_api.py            # Start API server
│   ├── setup_frontend.sh     # Setup React frontend
│   ├── test_system.py        # Full system test
│   └── test_api.py           # API endpoint tests
│
├── notebooks/                 # Jupyter exploration
├── deploy/                    # Deployment artifacts
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 11. API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/endpoints` | List all endpoints with sketches |
| GET | `/api/v1/endpoints/{id}` | Get endpoint details + behavior |
| GET | `/api/v1/clusters` | List all clusters |
| GET | `/api/v1/clusters/{id}` | Get cluster details + members |
| GET | `/api/v1/clusters/{id}/features` | Get cluster feature profile |
| GET | `/api/v1/sgts` | List SGT taxonomy |
| GET | `/api/v1/sgts/recommendations` | Get SGT recommendations |
| GET | `/api/v1/matrix` | Get policy matrix |
| GET | `/api/v1/matrix/{src}/{dst}` | Get matrix cell details |
| POST | `/api/v1/export/ise` | Export to ISE format |

### Streaming Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| WS | `/api/v1/stream/sketches` | Real-time sketch updates |
| WS | `/api/v1/stream/clusters` | Cluster assignment changes |

---

## 12. Success Metrics

### Technical Metrics

| Metric | Target |
|--------|--------|
| Edge memory usage | < 100MB for 500 endpoints |
| Sketch sync latency | < 1 second |
| Clustering update | < 10 seconds for 50K endpoints |
| API response (p95) | < 200ms |

### Business Metrics

| Metric | Target |
|--------|--------|
| Endpoint coverage | > 95% with cluster assignment |
| Cluster coherence | > 0.7 silhouette score |
| SGT accuracy | > 85% match expert labeling |
| Time to first policy | < 1 hour from data load |

---

## 13. Open Questions

### Architecture
1. **Edge clustering k value**: k=8 sufficient for local grouping?
2. **Sketch sync frequency**: Every 5 min vs event-driven?
3. **Backend clustering trigger**: Time-based vs sketch-count based?

### ML/Clustering
4. **Feature selection**: Which behavioral features matter most?
5. **Cluster count**: Let HDBSCAN decide vs. target 6-12 SGTs?
6. **Confidence thresholds**: When is assignment "good enough"?

### Integration
7. **ISE push**: Auto-push SGT assignments or manual approval?
8. **Multi-site**: Per-site clusters or global?

---

*Document Version: 2.0*  
*Last Updated: December 2024*  
*Architecture: Scale-First with Edge ML*  
*MVP Status: ✅ Complete - All 5 phases implemented and tested*
