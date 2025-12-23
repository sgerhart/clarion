# Clarion - Project Plan

## 📋 Overview

**Project:** Clarion - TrustSec Policy Copilot  
**Goal:** Scale-first network segmentation using edge processing and unsupervised learning  
**Start Date:** December 2024  
**Status:** 🟡 In Progress - Architecture v2.0 Complete, Phase 1 Starting

---

## 🎯 Architecture Philosophy

### Scale-First Design

| Principle | Implementation |
|-----------|----------------|
| **Edge-Heavy** | Process flows on switches, send only sketches |
| **Sketch-Based** | Probabilistic structures for bounded memory |
| **Incremental ML** | Clustering updates without reprocessing |
| **Hierarchical** | Local clusters → Global clusters → SGTs |

### Realistic Capacity Planning

| Switch Type | Wired Ports | With Wireless | Sketch Memory |
|-------------|-------------|---------------|---------------|
| Access (Cat 9300) | 24-48 | 100-300 | 3MB |
| Distribution | 48 | 200-500 | 5MB |
| **Design Target** | - | **500 max** | **5MB** |

---

## 🚀 Project Phases

### Phase 0: Foundation ✅ Complete
- [x] Project vision and scope defined
- [x] Synthetic dataset acquired (291K records)
- [x] Architecture v1.0 designed
- [x] **Architecture v2.0 redesigned** (scale-first, edge ML)
- [x] Project structure created
- [x] Documentation framework

### Phase 1: Core Data Structures & Sketches 🟡 Current

**Goal:** Build the foundational data structures for behavioral sketching

#### 1.1 Endpoint Sketch Implementation
| Task | Status | Notes |
|------|--------|-------|
| `EndpointSketch` dataclass | ⬜ Todo | Core behavioral fingerprint |
| HyperLogLog wrapper | ⬜ Todo | Cardinality estimation (unique peers) |
| Count-Min Sketch wrapper | ⬜ Todo | Frequency distribution (ports/services) |
| Sketch serialization (protobuf) | ⬜ Todo | For edge→backend sync |
| Unit tests for sketches | ⬜ Todo | Accuracy validation |

#### 1.2 Synthetic Data → Sketches
| Task | Status | Notes |
|------|--------|-------|
| Load all CSV files | ⬜ Todo | flows, endpoints, ise_sessions, etc. |
| Simulate streaming ingestion | ⬜ Todo | Process flows in time order |
| Build sketches from flows | ⬜ Todo | Populate EndpointSketch per endpoint |
| Validate sketch accuracy | ⬜ Todo | Compare to ground truth |

#### 1.3 Identity Resolution
| Task | Status | Notes |
|------|--------|-------|
| IP → Endpoint mapping | ⬜ Todo | Via ip_assignments, time-bounded |
| Endpoint → User mapping | ⬜ Todo | Via ISE sessions |
| User → AD Groups mapping | ⬜ Todo | Via ad_group_membership |
| Enrich sketches with identity | ⬜ Todo | Add user/group context |

**Deliverables:**
- `src/clarion/sketches/` module with all data structures
- `src/clarion/ingest/` module to build sketches from synthetic data
- Unit tests with >90% coverage

---

### Phase 2: Clustering Pipeline ⬜ Pending

**Goal:** Implement unsupervised learning to group endpoints by behavior

#### 2.1 Feature Engineering
| Task | Status | Notes |
|------|--------|-------|
| Extract features from sketches | ⬜ Todo | peer_diversity, in_out_ratio, etc. |
| Normalize feature vectors | ⬜ Todo | Scaling, handling missing values |
| Dimensionality reduction | ⬜ Todo | PCA/UMAP for visualization |

#### 2.2 Clustering Algorithms
| Task | Status | Notes |
|------|--------|-------|
| Mini-batch K-means (edge) | ⬜ Todo | Lightweight, k=8 |
| HDBSCAN (backend) | ⬜ Todo | Density-based, finds natural clusters |
| Incremental update logic | ⬜ Todo | Assign new endpoints without re-clustering |
| Cluster refinement (merge/split) | ⬜ Todo | Periodic optimization |

#### 2.3 Semantic Labeling
| Task | Status | Notes |
|------|--------|-------|
| Join clusters with AD groups | ⬜ Todo | "80% are in Engineering" |
| Join clusters with ISE profiles | ⬜ Todo | "90% are Printers" |
| Auto-generate cluster labels | ⬜ Todo | Human-readable names |
| Confidence scoring | ⬜ Todo | How sure are we about the label? |

#### 2.4 SGT Mapping
| Task | Status | Notes |
|------|--------|-------|
| Cluster → SGT recommendation | ⬜ Todo | Propose SGT assignments |
| SGT taxonomy generation | ⬜ Todo | 6-12 initial SGTs |
| Coverage analysis | ⬜ Todo | % endpoints with SGT assignment |

**Deliverables:**
- `src/clarion/clustering/` module
- Clustering pipeline that produces labeled clusters
- SGT recommendations with confidence scores

---

### Phase 3: Policy Matrix & SGACL ⬜ Pending

**Goal:** Generate TrustSec policies from cluster communications

#### 3.1 Communication Matrix
| Task | Status | Notes |
|------|--------|-------|
| Build cluster→cluster matrix | ⬜ Todo | From enriched communications |
| Map to SGT→SGT matrix | ⬜ Todo | Using cluster→SGT mapping |
| Aggregate traffic stats | ⬜ Todo | Ports, bytes, flow counts |

#### 3.2 SGACL Generation
| Task | Status | Notes |
|------|--------|-------|
| Generate allow rules | ⬜ Todo | From observed traffic |
| Generate deny rules | ⬜ Todo | For unobserved |
| Confidence-based filtering | ⬜ Todo | Only stable patterns |
| ISE-ready format | ⬜ Todo | Export syntax |

#### 3.3 Impact Analysis
| Task | Status | Notes |
|------|--------|-------|
| "What would break?" simulator | ⬜ Todo | Test before enforcement |
| Critical path identification | ⬜ Todo | High-impact flows |
| User/endpoint impact counts | ⬜ Todo | Affected entities |

**Deliverables:**
- `src/clarion/policy/` module
- Policy matrix visualization
- SGACL export ready for ISE

---

### Phase 4: Edge Container ⬜ Pending

**Goal:** Build lightweight container for Catalyst 9K App Hosting

#### 4.1 Core Edge Services
| Task | Status | Notes |
|------|--------|-------|
| NetFlow/IPFIX receiver (UDP 2055) | ⬜ Todo | Async UDP listener |
| Flow aggregator (5-min windows) | ⬜ Todo | Time-bucket flows |
| Sketch builder | ⬜ Todo | Build EndpointSketch per MAC |
| Local K-means clustering | ⬜ Todo | Lightweight, k=8 |

#### 4.2 Backend Sync
| Task | Status | Notes |
|------|--------|-------|
| gRPC client | ⬜ Todo | Streaming sketch sync |
| Delta sync logic | ⬜ Todo | Only send changed sketches |
| Backpressure handling | ⬜ Todo | Handle backend unavailable |
| Local buffer (SQLite) | ⬜ Todo | Survive backend outage |

#### 4.3 Packaging
| Task | Status | Notes |
|------|--------|-------|
| Alpine-based Dockerfile | ⬜ Todo | < 100MB image |
| IOx app descriptor | ⬜ Todo | iox-app.yaml |
| Memory optimization | ⬜ Todo | Target 256MB |
| Integration tests | ⬜ Todo | Simulated switch environment |

**Deliverables:**
- `edge/` container ready for App Hosting
- Sub-100MB container image
- < 256MB runtime memory

---

### Phase 5: API & Visualization ⬜ Pending

**Goal:** REST API and web dashboard

#### 5.1 FastAPI Backend
| Task | Status | Notes |
|------|--------|-------|
| Core endpoints (endpoints, clusters) | ⬜ Todo | CRUD operations |
| Streaming endpoints (WebSocket) | ⬜ Todo | Real-time updates |
| Policy endpoints (matrix, SGACL) | ⬜ Todo | Policy access |
| Export endpoints | ⬜ Todo | ISE format |

#### 5.2 Web Dashboard
| Task | Status | Notes |
|------|--------|-------|
| Cluster visualization (UMAP) | ⬜ Todo | 2D projection of clusters |
| Policy matrix heatmap | ⬜ Todo | SGT×SGT view |
| Endpoint explorer | ⬜ Todo | Search and drill-down |
| Recommendation review | ⬜ Todo | Approve/reject SGT assignments |

**Deliverables:**
- FastAPI backend with full API
- React dashboard with D3.js visualizations

---

### Phase 6: Integrations ⬜ Future

**Goal:** Connect to production identity sources

#### 6.1 Identity Connectors
| Task | Status | Notes |
|------|--------|-------|
| ISE pxGrid connector | ⬜ Todo | Real-time sessions |
| AD LDAP connector | ⬜ Todo | Users, groups |
| CMDB connector | ⬜ Todo | ServiceNow REST |

#### 6.2 Policy Export
| Task | Status | Notes |
|------|--------|-------|
| ISE ERS API push | ⬜ Todo | Direct policy update |
| DNA Center integration | ⬜ Todo | Fabric deployment |

---

## 📊 Progress Summary

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 0: Foundation | ✅ Complete | 100% |
| Phase 1: Sketches & Data | 🟡 Starting | 0% |
| Phase 2: Clustering | ⬜ Pending | 0% |
| Phase 3: Policy Matrix | ⬜ Pending | 0% |
| Phase 4: Edge Container | ⬜ Pending | 0% |
| Phase 5: API & UI | ⬜ Pending | 0% |
| Phase 6: Integrations | ⬜ Future | 0% |

---

## 🏃 Current Sprint

**Sprint 1: Core Data Structures**

**Goals:**
1. Implement EndpointSketch with HyperLogLog and Count-Min Sketch
2. Load synthetic CSV data and build sketches
3. Implement identity resolution (flow → user/device)
4. Validate sketch accuracy against ground truth

**Tasks:**
- [ ] Create `src/clarion/sketches/endpoint_sketch.py`
- [ ] Create `src/clarion/sketches/hyperloglog.py` (wrapper around datasketch)
- [ ] Create `src/clarion/sketches/countmin.py` (wrapper around datasketch)
- [ ] Create `src/clarion/ingest/loader.py` for CSV loading
- [ ] Create `src/clarion/ingest/sketch_builder.py`
- [ ] Create `src/clarion/identity/resolver.py`
- [ ] Write unit tests for all modules
- [ ] Validate sketches produce reasonable cardinality estimates

---

## 🗓️ Timeline (Estimated)

| Phase | Duration | Target |
|-------|----------|--------|
| Phase 1: Sketches & Data | 2 weeks | Jan 2025 |
| Phase 2: Clustering | 2 weeks | Jan 2025 |
| Phase 3: Policy Matrix | 2 weeks | Feb 2025 |
| Phase 4: Edge Container | 3 weeks | Feb-Mar 2025 |
| Phase 5: API & UI | 2 weeks | Mar 2025 |
| Phase 6: Integrations | 4 weeks | Apr 2025 |

---

## 📝 Technical Decisions

### Made
- **Edge sketches**: HyperLogLog + Count-Min Sketch for bounded memory
- **Edge clustering**: Mini-batch K-means (k=8) for lightweight local grouping
- **Backend clustering**: HDBSCAN for finding natural cluster shapes
- **Sketch library**: Use `datasketch` Python library
- **Sync protocol**: gRPC for efficient streaming
- **Backend API**: FastAPI with async support

### Pending
- Exact k value for edge clustering (8 vs 16?)
- Sketch sync frequency (5 min vs 1 min?)
- HDBSCAN min_cluster_size parameter
- Feature weights for clustering

---

## 🚨 Risks

| Risk | Mitigation |
|------|------------|
| Edge memory too constrained | Tune sketch sizes, reduce endpoint count |
| Clustering quality poor | Iterate on features, try different algorithms |
| ISE pxGrid access blocked | Use synthetic data, defer integration |
| AD LDAP complex | Start with synthetic, add real AD later |

---

## 📦 Dependencies

### Required
- Python 3.11+
- datasketch (HyperLogLog, Count-Min Sketch)
- scikit-learn (clustering)
- hdbscan (density-based clustering)
- FastAPI (API)
- NetworkX (graph operations)

### Synthetic Data ✅ Available
- flows.csv (106K records)
- endpoints.csv (13.6K records)
- ise_sessions.csv (13.3K records)
- ad_users.csv, ad_groups.csv, ad_group_membership.csv
- switches.csv, interfaces.csv
- services.csv, trustsec_sgts.csv

---

*Last Updated: December 2024*
*Architecture Version: 2.0 (Scale-First with Edge ML)*
