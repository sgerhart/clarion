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
│   ├── clustering/            # HDBSCAN, feature extraction, SGT mapping
│   ├── ingest/                # Data loading, sketch building
│   ├── identity/              # IP → User resolution
│   ├── policy/                # Matrix, SGACL generation, customization, export
│   ├── visualization/         # Cluster and policy visualization
│   ├── api/                   # FastAPI REST API
│   └── ui/                    # Streamlit UI
│
├── edge/                      # Edge container (Catalyst 9K)
│   ├── Dockerfile
│   ├── iox-app.yaml           # IOx descriptor
│   └── clarion_edge/          # Lightweight Python package
│       ├── sketch.py          # Edge sketches (pure Python)
│       ├── agent.py           # Edge agent with clustering
│       ├── simulator.py      # Flow simulator for testing
│       └── streaming.py       # Backend sync
│
├── collector/                 # Flow collector (legacy switches)
├── tests/                     # Test suite (137 tests)
│   ├── unit/                  # Unit tests
│   └── integration/           # Integration tests
├── scripts/                   # Utility scripts
│   ├── run_api.py            # Start API server
│   ├── run_streamlit.py      # Start Streamlit UI
│   ├── test_system.py        # Full system test
│   └── test_api.py           # API endpoint tests
├── notebooks/                 # Jupyter exploration
└── deploy/                    # K8s, Ansible artifacts
```

---

## 🗺️ Roadmap

### Phase 1: Core Data Structures ✅ Complete
- [x] EndpointSketch with HyperLogLog, Count-Min Sketch
- [x] Load synthetic data into sketches
- [x] Identity resolution (flow → user/device)

### Phase 2: Clustering Pipeline ✅ Complete
- [x] Feature extraction from sketches
- [x] HDBSCAN clustering
- [x] Semantic labeling (AD groups, ISE profiles)
- [x] SGT recommendations

### Phase 3: Policy Generation ✅ Complete
- [x] SGT → SGT matrix builder
- [x] SGACL generator
- [x] Impact analysis
- [x] Policy customization (human-in-the-loop)

### Phase 4: Edge Container ✅ Complete
- [x] Flow simulator (for testing without switch)
- [x] On-switch sketch builder
- [x] Lightweight K-means clustering
- [x] HTTP sync to backend
- [x] Docker/IOx packaging

### Phase 5: API & Visualization ✅ Complete
- [x] FastAPI backend with 23 endpoints
- [x] Cluster visualization (PCA/t-SNE)
- [x] Policy matrix heatmap
- [x] Streamlit UI for rapid prototyping

### Phase 6: Production Integration ⬜ Future
- [ ] NetFlow/IPFIX receiver (real switch integration)
- [ ] ISE pxGrid connector
- [ ] AD LDAP connector
- [ ] Production deployment guides

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
- **[API Documentation](README_API.md)** — FastAPI endpoints and usage
- **[Test Results](TEST_RESULTS.md)** — System test results and metrics

## 🚀 Quick Start

### Run Full System Test
```bash
python scripts/test_system.py
```

### Start API Server
```bash
python scripts/run_api.py --port 8000
# Visit http://localhost:8000/api/docs
```

### Start Streamlit UI
```bash
python scripts/run_streamlit.py
# Opens at http://localhost:8501
```

### Test Edge Simulator
```bash
cd edge && PYTHONPATH=. python -m clarion_edge.main --mode simulator --duration 60
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- Cisco TrustSec documentation and pxGrid APIs
- Synthetic data generation inspired by enterprise campus patterns
- datasketch library for probabilistic data structures
