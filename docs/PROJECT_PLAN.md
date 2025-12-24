# Clarion - Project Plan

## 📋 Overview

**Project:** Clarion - TrustSec Policy Copilot  
**Goal:** Scale-first network segmentation using edge processing and unsupervised learning  
**Start Date:** December 2024  
**Status:** ✅ MVP Complete - All 5 phases implemented and tested

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

### Phase 1: Core Data Structures & Sketches ✅ Complete

**Goal:** Build the foundational data structures for behavioral sketching

#### 1.1 Endpoint Sketch Implementation
| Task | Status | Notes |
|------|--------|-------|
| `EndpointSketch` dataclass | ✅ Done | Core behavioral fingerprint |
| HyperLogLog wrapper | ✅ Done | Cardinality estimation (unique peers) |
| Count-Min Sketch wrapper | ✅ Done | Frequency distribution (ports/services) |
| Sketch serialization | ✅ Done | JSON and binary formats |
| Unit tests for sketches | ✅ Done | 26 tests, all passing |

#### 1.2 Synthetic Data → Sketches
| Task | Status | Notes |
|------|--------|-------|
| Load all CSV files | ✅ Done | flows, endpoints, ise_sessions, etc. |
| Simulate streaming ingestion | ✅ Done | Process flows in time order |
| Build sketches from flows | ✅ Done | Populate EndpointSketch per endpoint |
| Validate sketch accuracy | ✅ Done | Tested against ground truth |

#### 1.3 Identity Resolution
| Task | Status | Notes |
|------|--------|-------|
| IP → Endpoint mapping | ✅ Done | Via ip_assignments, time-bounded |
| Endpoint → User mapping | ✅ Done | Via ISE sessions |
| User → AD Groups mapping | ✅ Done | Via ad_group_membership |
| Enrich sketches with identity | ✅ Done | Add user/group context |

**Deliverables:** ✅ Complete
- `src/clarion/sketches/` module with all data structures
- `src/clarion/ingest/` module to build sketches from synthetic data
- Unit tests with >90% coverage

---

### Phase 2: Clustering Pipeline ✅ Complete

**Goal:** Implement unsupervised learning to group endpoints by behavior

#### 2.1 Feature Engineering
| Task | Status | Notes |
|------|--------|-------|
| Extract features from sketches | ✅ Done | 18 features extracted |
| Normalize feature vectors | ✅ Done | Scaling, handling missing values |
| Dimensionality reduction | ✅ Done | PCA/t-SNE for visualization |

#### 2.2 Clustering Algorithms
| Task | Status | Notes |
|------|--------|-------|
| Mini-batch K-means (edge) | ✅ Done | Lightweight, k=8, pure Python |
| HDBSCAN (backend) | ✅ Done | Density-based, finds natural clusters |
| Incremental update logic | ✅ Done | Can assign new endpoints |
| Cluster refinement | ✅ Done | HDBSCAN handles merge/split naturally |

#### 2.3 Semantic Labeling
| Task | Status | Notes |
|------|--------|-------|
| Join clusters with AD groups | ✅ Done | Uses AD group membership patterns |
| Join clusters with ISE profiles | ✅ Done | Uses ISE endpoint profiles |
| Auto-generate cluster labels | ✅ Done | Human-readable names |
| Confidence scoring | ✅ Done | Confidence scores per label |

#### 2.4 SGT Mapping
| Task | Status | Notes |
|------|--------|-------|
| Cluster → SGT recommendation | ✅ Done | Propose SGT assignments |
| SGT taxonomy generation | ✅ Done | Generates 6-12 SGTs |
| Coverage analysis | ✅ Done | % endpoints with SGT assignment |

**Deliverables:** ✅ Complete
- `src/clarion/clustering/` module
- Clustering pipeline that produces labeled clusters
- SGT recommendations with confidence scores
- 17 unit tests + 8 integration tests

---

### Phase 3: Policy Matrix & SGACL ✅ Complete

**Goal:** Generate TrustSec policies from cluster communications

#### 3.1 Communication Matrix
| Task | Status | Notes |
|------|--------|-------|
| Build cluster→cluster matrix | ✅ Done | From enriched communications |
| Map to SGT→SGT matrix | ✅ Done | Using cluster→SGT mapping |
| Aggregate traffic stats | ✅ Done | Ports, bytes, flow counts |

#### 3.2 SGACL Generation
| Task | Status | Notes |
|------|--------|-------|
| Generate allow rules | ✅ Done | From observed traffic |
| Generate deny rules | ✅ Done | For unobserved (default deny) |
| Confidence-based filtering | ✅ Done | Min flow count threshold |
| ISE-ready format | ✅ Done | Cisco CLI + ISE JSON export |

#### 3.3 Impact Analysis
| Task | Status | Notes |
|------|--------|-------|
| "What would break?" simulator | ✅ Done | Test before enforcement |
| Critical path identification | ✅ Done | High-impact flows (DNS, LDAP, etc.) |
| User/endpoint impact counts | ✅ Done | Affected entities tracking |

#### 3.4 Policy Customization
| Task | Status | Notes |
|------|--------|-------|
| Human-in-the-loop review | ✅ Done | Approve/reject/modify recommendations |
| SGT customization | ✅ Done | Rename, reassign values, merge clusters |
| SGACL rule customization | ✅ Done | Add/remove/modify rules |
| Persistence | ✅ Done | Save/load customization sessions |

**Deliverables:** ✅ Complete
- `src/clarion/policy/` module
- Policy matrix visualization
- SGACL export ready for ISE
- Policy customization workflow
- 35 unit tests + 15 integration tests

---

### Phase 4: Edge Container ✅ Complete

**Goal:** Build lightweight container for Catalyst 9K App Hosting

#### 4.1 Core Edge Services
| Task | Status | Notes |
|------|--------|-------|
| NetFlow/IPFIX receiver | ⬜ Future | Real switch integration pending |
| Flow simulator | ✅ Done | Synthetic + CSV replay for testing |
| Flow aggregator | ✅ Done | Time-bucket flows |
| Sketch builder | ✅ Done | Build EdgeSketch per MAC (pure Python) |
| Local K-means clustering | ✅ Done | Lightweight, k=8, pure Python |

#### 4.2 Backend Sync
| Task | Status | Notes |
|------|--------|-------|
| HTTP client | ✅ Done | JSON and binary transport |
| Binary sync logic | ✅ Done | Efficient sketch serialization |
| Retry logic | ✅ Done | Handle backend unavailable |
| State persistence | ✅ Done | Save/load state |

#### 4.3 Packaging
| Task | Status | Notes |
|------|--------|-------|
| Alpine-based Dockerfile | ✅ Done | Minimal footprint |
| IOx app descriptor | ✅ Done | iox-app.yaml |
| Memory optimization | ✅ Done | ~18KB per endpoint |
| Integration tests | ✅ Done | 30 tests, all passing |

**Deliverables:** ✅ Complete
- `edge/` container ready for App Hosting
- Flow simulator for testing without switch
- Sub-100MB container image (target)
- < 256MB runtime memory (validated)

---

### Phase 5: API & Visualization ✅ Complete

**Goal:** REST API and web dashboard

#### 5.1 FastAPI Backend
| Task | Status | Notes |
|------|--------|-------|
| Core endpoints (endpoints, clusters) | ✅ Done | 23 routes total |
| Health endpoints | ✅ Done | Basic + detailed health |
| Edge sketch ingestion | ✅ Done | JSON + binary formats |
| Clustering endpoints | ✅ Done | Run clustering via API |
| Policy endpoints (matrix, SGACL) | ✅ Done | Policy access |
| Export endpoints | ✅ Done | Cisco CLI, ISE JSON, JSON |

#### 5.2 Visualization
| Task | Status | Notes |
|------|--------|-------|
| Cluster visualization (PCA/t-SNE) | ✅ Done | 2D projection with Plotly |
| Policy matrix heatmap | ✅ Done | SGT×SGT interactive view |
| Cluster distribution charts | ✅ Done | Bar charts |
| SGACL coverage visualization | ✅ Done | Coverage metrics |

#### 5.3 Streamlit UI
| Task | Status | Notes |
|------|--------|-------|
| Interactive dashboard | ✅ Done | 5-tab interface |
| Data loading | ✅ Done | Load synthetic data |
| Clustering workflow | ✅ Done | Run and view results |
| Policy generation | ✅ Done | Generate and review policies |
| Export functionality | ✅ Done | Download configs |

**Deliverables:** ✅ Complete
- FastAPI backend with 23 endpoints
- Streamlit UI for rapid prototyping
- Plotly interactive visualizations
- Complete API documentation

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
| Phase 1: Sketches & Data | ✅ Complete | 100% |
| Phase 2: Clustering | ✅ Complete | 100% |
| Phase 3: Policy Matrix | ✅ Complete | 100% |
| Phase 4: Edge Container | ✅ Complete | 100% |
| Phase 5: API & UI | ✅ Complete | 100% |
| Phase 6: Integrations | ⬜ Future | 0% |

**MVP Status:** ✅ **All core phases complete and tested**

---

## ✅ MVP Implementation Complete

**All 5 core phases have been implemented and tested:**

1. ✅ **Core Data Structures** - Sketches, data loading, identity resolution
2. ✅ **Clustering Pipeline** - HDBSCAN, semantic labeling, SGT mapping
3. ✅ **Policy Generation** - Matrix, SGACL, impact analysis, customization
4. ✅ **Edge Container** - Simulator, lightweight sketches, clustering
5. ✅ **API & Visualization** - FastAPI backend, Streamlit UI, Plotly charts

**Test Results:**
- 137 unit/integration tests passing
- Full system test: All 10 components verified
- Edge simulator: 201K flows processed in 2s
- API server: 23 routes functional

**Next Steps:**
- Production integrations (ISE pxGrid, AD LDAP)
- Real NetFlow/IPFIX receiver (when switch available)
- Performance optimization
- Production deployment guides

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
*MVP Status: ✅ Complete - All 5 phases implemented and tested*
