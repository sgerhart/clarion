# 🔔 Clarion

**TrustSec Policy Copilot** — Scale-first network segmentation using edge processing and unsupervised learning.

> [!NOTE]
> ## ✅ MVP Implementation Complete
> **All core phases are implemented and functional.** The system can:
> - Process flow data and build behavioral sketches
> - Cluster endpoints using HDBSCAN
> - Generate SGT taxonomies and SGACL policies
> - Customize recommendations via human-in-the-loop review
> - Run edge processing with simulator (no physical switch required)
> - Visualize clusters and policies via API and Streamlit UI
> 
> **Ready for testing and evaluation with synthetic data.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status](https://img.shields.io/badge/Status-MVP%20Complete-green.svg)]()

---

## 🎯 What is Clarion?

Clarion helps organizations adopt **Cisco TrustSec** by automatically discovering endpoint behavior patterns and generating SGT (Security Group Tag) policies. Unlike traditional approaches that require manual classification, Clarion uses **unsupervised learning** to cluster endpoints by behavior and recommend policy.

### Key Capabilities

1. **Edge Processing** — Compress flows to behavioral sketches on-switch (Catalyst 9K App Hosting)
2. **Behavioral Clustering** — Group endpoints by what they do, not what they are
3. **SGT Recommendation** — Auto-generate SGT taxonomy from discovered clusters
4. **Policy Generation** — Build SGACL rules from observed traffic patterns
5. **Scale-First** — Handle enterprise-scale traffic without central bottlenecks

---

## 🏗️ Architecture

Clarion uses a **distributed, scale-first architecture**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EDGE TIER (Per-Switch)                          │
│                         Catalyst 9K App Hosting Container                     │
│                                                                               │
│   Flows ──▶ Aggregate ──▶ Build Sketches ──▶ Local Cluster ──▶ Sync         │
│                              (5MB max)         (K-means k=8)     to Backend  │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                          Behavioral Sketches (KB, not GB)
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND TIER                                    │
│                                                                              │
│   Merge Sketches ──▶ HDBSCAN Clustering ──▶ Semantic Labels ──▶ SGT Mapping │
│                                                                              │
│                              Policy Matrix ──▶ SGACL Generation              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why This Architecture?

| Traditional Approach | Clarion Approach |
|---------------------|------------------|
| Ship all flows to central collector | Compress to sketches at edge |
| O(flows) memory growth | O(endpoints) memory — bounded |
| Central processing bottleneck | Horizontally distributed |
| Batch clustering overnight | Incremental real-time updates |

**Scale Example:**
- 1000 switches × 100K flows/hour = **10GB/hour** to process centrally
- With sketches: 1000 switches × 5KB updates = **5MB/hour** to aggregate

---

## 🧠 How It Works

### 1. Behavioral Sketches (Edge)

Each endpoint gets a lightweight ~10KB behavioral fingerprint:

```python
@dataclass
class EndpointSketch:
    endpoint_id: str              # MAC address
    
    # Cardinality (HyperLogLog)
    unique_peers: HyperLogLog     # How many IPs contacted
    unique_services: HyperLogLog  # How many services accessed
    
    # Frequency (Count-Min Sketch)
    port_frequency: CountMinSketch    # Port usage distribution
    service_frequency: CountMinSketch # Service access patterns
    
    # Aggregates
    bytes_in: int
    bytes_out: int
    in_out_ratio: float           # Client vs server
    active_hours: int             # 24-bit bitmap
```

### 2. Unsupervised Clustering (Backend)

HDBSCAN finds natural groupings based on behavior:

```
Cluster-0: [laptop-1, laptop-2, ...] → "Corporate Users"
Cluster-1: [server-1, server-2, ...] → "Servers"  
Cluster-2: [printer-1, printer-2, ...] → "Printers"
Cluster-3: [camera-1, sensor-1, ...] → "IoT Devices"
```

### 3. SGT Mapping

Clusters map to Security Group Tags:

```
"Corporate Users"  → SGT 2
"Servers"          → SGT 10
"Printers"         → SGT 20
"IoT Devices"      → SGT 21
```

### 4. Policy Generation

Observed traffic patterns become SGACL rules:

```
! SGT 2 (Corp-Users) → SGT 10 (Servers)
permit tcp dst eq 443
permit tcp dst eq 22
deny ip log
```

---

## 📊 Sample Dataset

Clarion includes a synthetic enterprise campus dataset for development:

| Data | Records | Description |
|------|---------|-------------|
| Switches | 100 | Campus switches across 10 sites |
| Users | 10,000 | Employees with AD groups |
| Endpoints | 13,650 | Laptops, servers, IoT, printers |
| Flows | 106,814 | Network traffic metadata |
| Services | 42 | AD, DNS, ERP, FileShare, etc. |
| ISE Sessions | 13,300 | Authentication context |

---

## 📁 Project Structure

```
clarion/
├── docs/
│   ├── DESIGN.md              # System architecture (v2.0)
│   └── PROJECT_PLAN.md        # Development roadmap
│
├── data/
│   ├── raw/                   # Synthetic datasets
│   │   └── trustsec_copilot_synth_campus/
│   └── processed/             # Transformed data
│
├── src/clarion/               # Backend library
│   ├── sketches/              # HyperLogLog, Count-Min Sketch
│   ├── clustering/            # HDBSCAN, feature extraction
│   ├── ingest/                # Data loading, sketch building
│   ├── identity/              # IP → User resolution
│   ├── policy/                # Matrix, SGACL generation
│   ├── connectors/            # ISE, AD, CMDB integrations
│   └── api/                   # FastAPI REST API
│
├── edge/                      # Edge container (Catalyst 9K)
│   ├── Dockerfile
│   ├── iox-app.yaml           # IOx descriptor
│   └── clarion_edge/          # Lightweight Python package
│
├── collector/                 # Flow collector (legacy switches)
├── tests/                     # Test suite
├── notebooks/                 # Jupyter exploration
└── deploy/                    # K8s, Ansible artifacts
```

---

## 🗺️ Roadmap

### Phase 1: Core Data Structures 🟡 Current
- [ ] EndpointSketch with HyperLogLog, Count-Min Sketch
- [ ] Load synthetic data into sketches
- [ ] Identity resolution (flow → user/device)

### Phase 2: Clustering Pipeline ⬜ Pending
- [ ] Feature extraction from sketches
- [ ] HDBSCAN clustering
- [ ] Semantic labeling (AD groups, ISE profiles)
- [ ] SGT recommendations

### Phase 3: Policy Generation ⬜ Pending
- [ ] SGT → SGT matrix builder
- [ ] SGACL generator
- [ ] Impact simulator

### Phase 4: Edge Container ⬜ Pending
- [ ] NetFlow/IPFIX receiver
- [ ] On-switch sketch builder
- [ ] gRPC sync to backend
- [ ] IOx packaging

### Phase 5: API & UI ⬜ Pending
- [ ] FastAPI backend
- [ ] Cluster visualization (UMAP)
- [ ] Policy matrix heatmap

---

## 🔧 Technology Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.11+ |
| **Sketches** | datasketch (HyperLogLog, CMS) |
| **Clustering** | scikit-learn, hdbscan |
| **API** | FastAPI |
| **Edge Container** | Alpine Linux + Python |
| **Serialization** | Protocol Buffers |

---

## 📖 Documentation

- **[Design Document](docs/DESIGN.md)** — System architecture, data model, algorithms
- **[Project Plan](docs/PROJECT_PLAN.md)** — Milestones, tasks, progress tracking

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- Cisco TrustSec documentation and pxGrid APIs
- Synthetic data generation inspired by enterprise campus patterns
- datasketch library for probabilistic data structures
