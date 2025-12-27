<div align="center">
  <img src="frontend/public/clarion.jpg" alt="Clarion Logo" width="400"/>
  <img src="frontend/public/clarionicon.jpg" alt="Clarion Icon" width="100"/>
</div>

**TrustSec Policy Copilot** — Scale-first network segmentation using edge processing and unsupervised learning.



> [!NOTE]
> ## ✅ MVP Implementation Complete
> **All core phases are implemented and functional.** The system can:
> - Process flow data and build behavioral sketches
> - Cluster endpoints using HDBSCAN
> - Generate SGT taxonomies and SGACL policies
> - Customize recommendations via human-in-the-loop review
> - Run edge processing with simulator (no physical switch required)
> - Visualize clusters and policies via API and React frontend
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
6. **Device-Agnostic** — Works with Windows, Linux, Mac, IoT, and non-AD devices
7. **Full Admin Control** — Override any AI recommendation (groups, SGTs, policies)
8. **Network Topology** — Location-aware policy recommendations (Campus, Branch, Remote Sites)
9. **Multi-Source Correlation** — Integrate NetFlow, ISE pxGrid, AD, and IoT data
10. **Graph Database** — Merge edge agent graphs for global policy view

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
│   └── ui/                    # Legacy Streamlit UI (deprecated)
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
├── frontend/                  # React frontend (production UI)
│   ├── src/                  # React components and pages
│   ├── public/               # Static assets
│   └── package.json          # Frontend dependencies
├── scripts/                   # Utility scripts
│   ├── run_api.py            # Start API server
│   ├── setup_frontend.sh     # Setup React frontend
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
- [x] **React frontend (production-ready UI)**
- [x] **Persistent storage (SQLite database)**
- [x] **NetFlow ingestion endpoints**

### Phase 6: Data Layer & Scalability ⬜ In Progress
- [ ] PostgreSQL + TimescaleDB migration (time-series optimization)
- [ ] Neo4j graph database integration (edge graph merging)
- [ ] Multi-source data ingestion architecture
- [ ] Correlation engine for cross-source data joins

### Phase 7: Network Topology ⬜ In Progress
- [ ] Location hierarchy (Campus, Branch, Remote Site)
- [ ] Address space management (customer-defined IP ranges)
- [ ] Subnet-to-location mapping
- [ ] Switch-to-location mapping
- [ ] Flow location correlation
- [ ] Topology builder UI

### Phase 8: Multi-Source Ingestion ⬜ Planned
- [ ] NetFlow collector (v5, v9, IPFIX with SGT support)
- [ ] ISE pxGrid subscriber (identity & SGT data)
- [ ] AD LDAP connector (users, groups, devices)
- [ ] IoT connector framework (MediGate, ClearPass, etc.)

### Phase 9: Production Integration ⬜ Future
- [ ] Production deployment guides
- [ ] High availability setup
- [ ] Performance optimization
- [ ] Monitoring and alerting

---

## 🔧 Technology Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.11+ |
| **Sketches** | datasketch (HyperLogLog, CMS) |
| **Clustering** | scikit-learn, hdbscan |
| **API** | FastAPI |
| **Database** | SQLite (dev) → PostgreSQL + TimescaleDB (prod) |
| **Graph DB** | Neo4j (for relationships & edge graph merging) |
| **Frontend** | React + TypeScript + Tailwind CSS |
| **Edge Container** | Alpine Linux + Python |
| **Serialization** | Protocol Buffers |
| **NetFlow** | v5, v9, IPFIX (with SGT support) |
| **Identity** | ISE pxGrid, AD LDAP, IoT connectors |

---

## 📖 Documentation

### Core Documentation
- **[Design Document](docs/DESIGN.md)** — System architecture, data model, algorithms
- **[Project Plan](docs/PROJECT_PLAN.md)** — Milestones, tasks, progress tracking
- **[Project Roadmap](PROJECT_ROADMAP.md)** — 6-month roadmap, priorities, task tracking
- **[API Documentation](README_API.md)** — FastAPI endpoints and usage

### Frontend
- **[React Frontend Guide](REACT_FRONTEND.md)** — Frontend setup and development
- **[Frontend Troubleshooting](FRONTEND_TROUBLESHOOTING.md)** — Common issues and solutions

### Data & Topology
- **[Data Architecture](docs/DATA_ARCHITECTURE.md)** — Data sources, storage, correlation requirements
- **[Topology Architecture](docs/TOPOLOGY_ARCHITECTURE.md)** — Location hierarchy, address spaces, subnet mapping
- **[Topology Examples](docs/TOPOLOGY_EXAMPLES.md)** — Real-world topology examples
- **[Data Layer Implementation](docs/IMPLEMENTATION_PLAN_DATA_LAYER.md)** — Migration plan for scalable data layer

### Clustering & Administration
- **[Clustering & Grouping](docs/CLUSTERING_AND_GROUPING.md)** — How clusters are created, modified, and explained
- **[Admin Control & Hierarchy](docs/ADMIN_CONTROL_AND_HIERARCHY.md)** — Full administrative override, device-agnostic support, simplified UI

### Testing & Setup
- **[Test Results](TEST_RESULTS.md)** — System test results and metrics
- **[Storage & Lab Environment](STORAGE_AND_LAB.md)** — Database, lab setup
- **[Lab README](lab/README.md)** — VM setup, edge agents, fake logs

## 🚀 Quick Start

### Complete System Demo (Recommended)

Start the backend and frontend:

```bash
# Terminal 1: Start backend API
python scripts/run_api.py --port 8000

# Terminal 2: Start React frontend
cd frontend
npm install  # First time only
npm run dev
```

Then open http://localhost:3000 in your browser.

**See [QUICK_START.md](QUICK_START.md) for detailed instructions.**

### Individual Components

#### Run Full System Test
```bash
python scripts/test_system.py
```

#### Start API Server
```bash
python scripts/run_api.py --port 8000
# Visit http://localhost:8000/api/docs
```

#### Start React Frontend (Production UI)
```bash
cd frontend
npm install  # First time only
npm run dev
# Opens at http://localhost:3000
```

#### Setup Frontend (First Time)
```bash
./scripts/setup_frontend.sh
```

#### Test Edge Simulator
```bash
cd edge && PYTHONPATH=. python -m clarion_edge.main --mode simulator --duration 60
```

### Lab Environment Setup

For full lab environment with VMs:

```bash
# On each VM
sudo ./lab/setup_vm.sh --traffic imix
sudo ./lab/vm_agent_setup.sh --backend-url http://BACKEND_IP:8000
sudo ./lab/vm_netflow_sender.sh --backend-url http://BACKEND_IP:8000

# Generate fake logs
python3 lab/generate_fake_ise.py -o lab/data/ise_sessions.json
python3 lab/generate_fake_ad.py -o lab/data/ad_logs.json
```

**See [lab/README.md](lab/README.md) for detailed lab setup.**

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- Cisco TrustSec documentation and pxGrid APIs
- Synthetic data generation inspired by enterprise campus patterns
- datasketch library for probabilistic data structures
