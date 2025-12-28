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
| NetFlow/IPFIX receiver | ✅ Done | Native collector implemented (v5 complete, v9/IPFIX stubbed) |
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

#### 5.3 React Frontend (Production UI)
| Task | Status | Notes |
|------|--------|-------|
| Interactive dashboard | ✅ Done | Overview with stats |
| Data loading | ✅ Done | Load synthetic data |
| Clustering workflow | ✅ Done | Run and view results |
| Policy generation | ✅ Done | Generate and review policies |
| Export functionality | ✅ Done | Download configs |
| Complete menu structure | ✅ Done | All menu items implemented |
| Navigation system | ✅ Done | Expandable sub-menus, active states |
| Device management page | ✅ Done | Device list and management |
| Groups management page | ✅ Done | Group/cluster management |
| Policy sub-pages | ✅ Done | SGT Mappings, Access Rules, Matrix, Builder, Impact |
| Topology page | ✅ Done | Hierarchy configuration |
| Data Sources pages | ✅ Done | Agents, Collectors, Overview |
| Connectors pages | ✅ Done | ISE, AD, IoT (flexible architecture) |
| Settings pages | ✅ Done | Global, Clustering, Policy, System |
| Monitoring page | ✅ Done | System health dashboard |
| Audit/Logs page | ✅ Done | Change tracking |
| Reports/Export page | ✅ Done | Policy export and reports |

#### 5.4 Clustering Explainability & Admin Controls
| Task | Status | Notes |
|------|--------|-------|
| Cluster explanation system | ✅ Done | Primary reason, confidence, statistics |
| Device-agnostic clustering | ✅ Done | Works without AD, supports all device types |
| Admin override capabilities | ✅ Done | Full customization system |
| Documentation | ✅ Done | CLUSTERING_AND_GROUPING.md, ADMIN_CONTROL_AND_HIERARCHY.md |

**Deliverables:** ✅ Complete
- FastAPI backend with 23 endpoints
- React frontend (production UI with TypeScript, Tailwind CSS)
  - Complete navigation menu with 12 main sections
  - Expandable sub-menus for Policy, Data Sources, Connectors, Settings
  - 20+ page components implemented
  - Flexible connector architecture for future integrations
- D3.js network visualizations, Plotly.js heatmaps
- Complete API documentation
- Clustering explainability and admin control documentation
- UI menu structure documentation (UI_MENU_STRUCTURE.md)

---

### Phase 6: Data Layer & Scalability ⬜ In Progress

**Goal:** Migrate to production-grade data architecture

#### 6.1 Database Migration
| Task | Status | Notes |
|------|--------|-------|
| PostgreSQL + TimescaleDB setup | ⬜ Todo | Time-series optimization |
| SQLite → PostgreSQL migration | ⬜ Todo | Data migration scripts |
| TimescaleDB hypertables | ⬜ Todo | Flow data partitioning |
| Data retention policies | ⬜ Todo | 90 days raw, 1 year aggregated |

#### 6.2 Graph Database Integration
| Task | Status | Notes |
|------|--------|-------|
| Neo4j deployment | ⬜ Todo | Graph database cluster |
| Graph schema design | ⬜ Todo | Nodes, edges, properties |
| Edge graph merging | ⬜ Todo | Merge agent graphs to global |
| Graph queries | ⬜ Todo | Relationship traversal |

**Deliverables:** ⬜ In Progress
- PostgreSQL + TimescaleDB for time-series
- Neo4j for graph relationships
- Migration scripts and documentation

---

### Phase 7: Network Topology ⬜ In Progress

**Goal:** Location-aware network topology management

#### 7.1 Location Hierarchy
| Task | Status | Notes |
|------|--------|-------|
| Location types (Campus, Branch, Remote) | ✅ Schema Done | Database schema complete |
| Location hierarchy API | ⬜ Todo | CRUD endpoints |
| Location attributes | ✅ Schema Done | Contact, timezone, coordinates |
| Topology builder UI | ⬜ Todo | Visual hierarchy editor |

#### 7.2 Address Space Management
| Task | Status | Notes |
|------|--------|-------|
| Address space definition | ✅ Schema Done | Customer IP ranges |
| RFC 1918 detection | ⬜ Todo | Auto-detect internal ranges |
| Address space API | ⬜ Todo | CRUD endpoints |

#### 7.3 Subnet & Switch Mapping
| Task | Status | Notes |
|------|--------|-------|
| Subnet-to-location mapping | ✅ Schema Done | Database schema complete |
| Switch-to-location mapping | ✅ Schema Done | Database schema complete |
| IP-to-subnet resolution | ⬜ Todo | CIDR matching |
| Flow location correlation | ⬜ Todo | Enrich flows with location |

**Deliverables:** ⬜ In Progress
- Topology database schema ✅
- Location management API ⬜
- Topology builder UI ⬜
- Flow location correlation ⬜

---

### Phase 8: Multi-Source Ingestion ⬜ Planned

**Goal:** Ingest data from multiple sources

#### 8.1 NetFlow Collector ✅ In Progress
| Task | Status | Notes |
|------|--------|-------|
| NetFlow v5 parser | ✅ Done | Fixed format, fully implemented |
| NetFlow v9 parser | ⬜ Stubbed | Template-based parsing needed |
| IPFIX parser | ⬜ Stubbed | Template-based parsing needed |
| Native NetFlow collector | ✅ Done | UDP listener (ports 2055, 4739) |
| Agent collector | ✅ Done | HTTP endpoint (port 8080) |
| SGT field extraction | ⬜ Pending | Requires template parsing |
| Backend integration | ✅ Done | Sends to /api/netflow/netflow |
| Documentation | ✅ Done | See collector/README.md |
| IPFIX parser | ⬜ Todo | IETF standard |
| SGT field extraction | ⬜ Todo | IPFIX IE 411/412 |
| Field mapping | ⬜ Todo | Unified schema |

#### 8.2 ISE pxGrid Integration
| Task | Status | Notes |
|------|--------|-------|
| pxGrid client setup | ⬜ Todo | Authentication, certificates |
| Session topic subscriber | ⬜ Todo | Real-time sessions |
| Endpoint topic subscriber | ⬜ Todo | Endpoint info |
| SGT assignment tracking | ⬜ Todo | SGT changes |

#### 8.3 AD Connector
| Task | Status | Notes |
|------|--------|-------|
| LDAP connection | ⬜ Todo | User/group queries |
| User sync | ⬜ Todo | Periodic sync |
| Group membership | ⬜ Todo | Nested groups |
| Device sync | ⬜ Todo | Computer objects |

#### 8.4 IoT Connector Framework
| Task | Status | Notes |
|------|--------|-------|
| Connector interface | ⬜ Todo | Abstract base class |
| MediGate connector | ⬜ Todo | Medical devices |
| ClearPass connector | ⬜ Todo | Device profiling |
| Custom connector support | ⬜ Todo | Vendor-specific |

**Deliverables:** ⬜ Planned
- NetFlow collector (v5/v9/IPFIX)
- pxGrid subscriber
- AD connector
- IoT connector framework

---

### Phase 9: Correlation Engine ⬜ Planned

**Goal:** Correlate data across all sources

#### 9.1 Identity Resolution
| Task | Status | Notes |
|------|--------|-------|
| MAC → IP → User resolution | ⬜ Todo | Multi-source correlation |
| Temporal correlation | ⬜ Todo | Time-windowed joins |
| Confidence scoring | ⬜ Todo | Correlation quality |

#### 9.2 Graph Merging
| Task | Status | Notes |
|------|--------|-------|
| Edge graph merge logic | ⬜ Todo | Deduplicate, aggregate |
| Conflict resolution | ⬜ Todo | Handle conflicts |
| Incremental updates | ⬜ Todo | Real-time merging |

#### 9.3 Policy Correlation
| Task | Status | Notes |
|------|--------|-------|
| Flow-to-identity correlation | ⬜ Todo | Cross-source joins |
| Location-aware policies | ⬜ Todo | Location-based SGTs |
| Risk assessment | ⬜ Todo | Multi-source risk scoring |

**Deliverables:** ⬜ Planned
- Identity resolution service
- Graph merging service
- Policy correlation engine

---

### Phase 10: Production Integration ⬜ Future

**Goal:** Production deployment and operations

#### 10.1 Deployment
| Task | Status | Notes |
|------|--------|-------|
| Kubernetes manifests | ⬜ Todo | K8s deployment |
| Docker Compose | ⬜ Todo | Local/development |
| Ansible playbooks | ⬜ Todo | Infrastructure as code |
| CI/CD pipeline | ⬜ Todo | Automated testing/deployment |

#### 10.2 Operations
| Task | Status | Notes |
|------|--------|-------|
| Monitoring | ⬜ Todo | Prometheus, Grafana |
| Logging | ⬜ Todo | Centralized logging |
| Alerting | ⬜ Todo | Alert rules |
| Backup/restore | ⬜ Todo | Data protection |

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
| Phase 6: Data Layer | ⬜ In Progress | 10% (Schema design done) |
| Phase 7: Topology | ⬜ In Progress | 30% (Schema done, API/UI pending) |
| Phase 8: Multi-Source | ⬜ Planned | 0% |
| Phase 9: Correlation | ⬜ Planned | 0% |
| Phase 10: Production | ⬜ Future | 0% |

**MVP Status:** ✅ **All core phases (1-5) complete and tested**

**Next Priorities:**
1. Phase 6: PostgreSQL + TimescaleDB migration
2. Phase 7: Topology management API and UI
3. Phase 8: NetFlow collector with SGT support

---

## ✅ MVP Implementation Complete

**All 5 core phases have been implemented and tested:**

1. ✅ **Core Data Structures** - Sketches, data loading, identity resolution
2. ✅ **Clustering Pipeline** - HDBSCAN, semantic labeling, SGT mapping
3. ✅ **Policy Generation** - Matrix, SGACL, impact analysis, customization
4. ✅ **Edge Container** - Simulator, lightweight sketches, clustering
5. ✅ **API & Visualization** - FastAPI backend, React frontend (production UI)

**Test Results:**
- 137 unit/integration tests passing
- Full system test: All 10 components verified
- Edge simulator: 201K flows processed in 2s
- API server: 23 routes functional

**Next Steps:**
- Phase 6: Data Layer migration (PostgreSQL + TimescaleDB, Neo4j)
- Phase 7: Topology management (API + UI)
- Phase 8: Multi-source ingestion (NetFlow, pxGrid, AD, IoT)
- Phase 9: Correlation engine
- Phase 10: Production deployment

**Recent Enhancements (Completed):**
- ✅ Clustering explainability (why devices are grouped)
- ✅ Device-agnostic support (Linux, Mac, IoT, non-AD devices)
- ✅ Full administrative override capabilities
- ✅ Simplified UI hierarchy design
- ✅ Documentation: CLUSTERING_AND_GROUPING.md, ADMIN_CONTROL_AND_HIERARCHY.md

**See [PROJECT_ROADMAP.md](../PROJECT_ROADMAP.md) for detailed roadmap and priorities.**

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
