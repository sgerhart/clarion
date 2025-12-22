# 🔔 Clarion

**TrustSec Policy Copilot** — Clear visibility into your network for intelligent policy design.

> [!CAUTION]
> ## 🚧 Design & Concept Phase Only
> **This project is currently in the design and concept phase.** Nothing is functional yet. The code structure, documentation, and data samples exist to explore the architecture and validate the approach. No features are implemented or working at this time.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status](https://img.shields.io/badge/Status-Concept%20Only-red.svg)]()

---

## 🎯 What is Clarion?

Clarion helps organizations adopt and refine **Cisco TrustSec** deployments by:

1. **Observing** real network traffic patterns
2. **Resolving** IP flows to user/device identities  
3. **Recommending** SGT (Security Group Tag) taxonomies
4. **Generating** SGACL policies from observed behavior
5. **Validating** policies before enforcement

> *"Mine real network behavior into a TrustSec policy matrix, then give customers a safe path from today → desired state."*

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- pip or uv

### Installation

```bash
# Clone the repository
git clone https://github.com/sgerhart/clarion.git
cd clarion

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import clarion; print('Clarion ready!')"
```

### Load Sample Data

```bash
# Load the synthetic campus dataset
python -m src.scripts.load_data

# Run analysis
python -m src.scripts.analyze
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

## 🏗️ Architecture

Clarion uses a **distributed architecture** designed for production deployments:

```
┌─────────────────────────────────────────────────────────────────────┐
│                           EDGE TIER                                  │
│  ┌─────────────────────┐     ┌─────────────────────┐               │
│  │   Catalyst 9K       │     │   Legacy Switches   │               │
│  │   ┌─────────────┐   │     │                     │               │
│  │   │Clarion Edge │   │     │   NetFlow Export    │               │
│  │   │ Container   │   │     │         │           │               │
│  │   └──────┬──────┘   │     └─────────┼───────────┘               │
│  └──────────┼──────────┘               │                            │
│             │ gRPC                     │ NetFlow                    │
└─────────────┼──────────────────────────┼────────────────────────────┘
              │                          │
              ▼                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         BACKEND TIER                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ Ingest   │  │ Identity │  │ Analysis │  │ Policy   │            │
│  │ Service  │  │ Resolver │  │ Engine   │  │ Engine   │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
└─────────────────────────────────────────────────────────────────────┘
              ▲                          ▲
              │                          │
     ┌────────┴────────┐        ┌────────┴────────┐
     │   ISE (pxGrid)  │        │   AD (LDAP)     │
     │   CMDB (REST)   │        │   DHCP/DNS      │
     └─────────────────┘        └─────────────────┘
```

### Deployment Options

| Component | Description |
|-----------|-------------|
| **Clarion Edge** | Lightweight container for Cisco App Hosting (Catalyst 9K) |
| **Clarion Collector** | Central collector for non-container switches |
| **Clarion Backend** | Analytics, policy engine, API/UI |

---

## 📁 Project Structure

```
clarion/
├── docs/                      # Documentation
│   └── DESIGN.md             # System design document
│
├── data/
│   ├── raw/                  # Original datasets
│   │   └── trustsec_copilot_synth_campus/
│   └── processed/            # Transformed data
│
├── src/clarion/              # Backend library
│   ├── ingest/               # Data ingestion
│   ├── identity/             # Identity resolution
│   ├── analysis/             # Traffic analysis
│   ├── policy/               # Policy generation
│   ├── connectors/           # ISE, AD, CMDB integrations
│   ├── export/               # Policy export
│   └── api/                  # REST API
│
├── edge/                      # Edge container (App Hosting)
│   ├── Dockerfile
│   ├── iox-app.yaml          # IOx descriptor
│   └── clarion_edge/         # Edge Python package
│
├── collector/                 # Central flow collector
│   ├── Dockerfile
│   └── clarion_collector/    # Collector Python package
│
├── lab/                       # NetFlow lab (VM simulation)
├── deploy/                    # Deployment artifacts
│   ├── k8s/                  # Kubernetes manifests
│   └── ansible/              # Switch deployment playbooks
│
├── tests/                     # Test suite
├── notebooks/                 # Jupyter exploration
└── pyproject.toml            # Project config
```

---

## 🔧 Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format
black src/ tests/
ruff check src/ tests/

# Type check
mypy src/
```

### Local API Server

```bash
uvicorn src.clarion.api.main:app --reload
```

---

## 📖 Documentation

- **[Design Document](docs/DESIGN.md)** — System architecture, data model, algorithms
- **[Project Plan](docs/PROJECT_PLAN.md)** — Milestones, tasks, progress tracking
- **[Lab Setup](lab/README.md)** — NetFlow lab environment

---

## 🗺️ Roadmap

### MVP 1: Identity-Labeled Flow Graph ⬜
- [ ] Data loaders for synthetic dataset
- [ ] Identity resolver (flow → user/device)
- [ ] NetworkX graph builder
- [ ] CLI tools

### MVP 2: SGT Taxonomy Recommender ⬜
- [ ] Behavior clustering
- [ ] SGT recommendation engine
- [ ] Coverage analysis

### MVP 3: Policy Matrix Generator ⬜
- [ ] SGT→SGT matrix builder
- [ ] SGACL generator
- [ ] Impact simulator

### MVP 4: API & UI ⬜
- [ ] FastAPI backend
- [ ] Streamlit dashboard
- [ ] Graph visualization

---

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- Cisco TrustSec documentation and pxGrid APIs
- Synthetic data generation inspired by enterprise campus patterns
