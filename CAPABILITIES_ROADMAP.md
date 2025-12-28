# Clarion Complete Capabilities Roadmap

## Overview

This document provides a comprehensive, cohesive roadmap of all Clarion capabilities - both completed and planned. It consolidates all features, enhancements, and infrastructure requirements discussed across all documentation to ensure nothing is missed during implementation.

---

## Current Status Summary

### ✅ Completed (MVP Phase)
- Core data structures (sketches, HyperLogLog, Count-Min Sketch)
- Clustering pipeline (HDBSCAN, feature extraction, semantic labeling)
- Policy generation (SGT matrix, SGACL generation, customization)
- Edge container (sketch building, lightweight clustering, backend sync)
- API & UI (FastAPI backend, React frontend, basic visualizations)
- Network topology management (locations, address spaces, subnets, switches)
- NetFlow collector (v5 complete, v9/IPFIX with template parsing)
- Basic database (SQLite with all core tables)

---

## Complete Capabilities Matrix

### 1. Backend & Categorization Engine

#### 1.1 Core Categorization
- [x] Batch HDBSCAN clustering
- [x] Feature extraction (18 behavioral features)
- [x] Semantic labeling (AD groups, ISE profiles, device types)
- [x] SGT mapping (cluster → SGT recommendations)
- [ ] **Incremental clustering** (fast path for new endpoints)
- [ ] **First-seen tracking** (detect new devices/users)
- [ ] **Identity-aware clustering** (handle late-arriving identity data)
- [ ] **SGT lifecycle management** (stable SGTs, dynamic membership)
- [ ] **Cluster stability tracking** (evolution over time)
- [ ] **Cluster centroid storage** (for fast incremental assignment)

**Status:** ⚠️ Core complete, enhancements in progress  
**Priority:** 🔴 High (Priority 1)  
**Timeline:** 4-6 weeks

#### 1.2 AI/LLM Integration (Optional)
- [ ] **AI categorization agent architecture**
- [ ] **LLM backend abstraction** (pluggable backends)
- [ ] **Local model support** (Llama, Mistral via Ollama)
- [ ] **Cloud model support** (OpenAI GPT-4, Anthropic Claude)
- [ ] **Optional RAG** (database context for categorization)
- [ ] **Fallback to rule-based labeling** (graceful degradation)
- [ ] **AI configuration management** (enable/disable, model selection)

**Status:** 📋 Planned  
**Priority:** 🔴 High (Priority 1.2)  
**Timeline:** 2 weeks (after architecture validation)  
**Dependencies:** Verify Ollama integration, validate optional architecture

#### 1.3 Streaming Data Processing
- [ ] **Real-time flow ingestion** (streaming vs batch)
- [ ] **Incremental sketch updates** (update existing sketches)
- [ ] **Streaming clustering triggers** (when to re-cluster)
- [ ] **Backpressure handling** (rate limiting, buffering)

**Status:** 📋 Planned  
**Priority:** 🟡 Medium (Priority 1.3)  
**Timeline:** 2-3 weeks

---

### 2. Data Layer & Scalability

#### 2.1 Database Migration
- [x] SQLite (development)
- [ ] **PostgreSQL migration** (production-ready database)
- [ ] **TimescaleDB integration** (time-series optimization)
- [ ] **Hypertable creation** (for flow data partitioning)
- [ ] **Data retention policies** (automated archival/compression)
- [ ] **Migration scripts** (SQLite → PostgreSQL)

**Status:** 📋 Planned  
**Priority:** 🔴 High  
**Timeline:** 4-6 weeks  
**Dependencies:** None

#### 2.2 Graph Database
- [ ] **Neo4j deployment** (for relationship storage)
- [ ] **Graph schema design** (nodes, edges, properties)
- [ ] **Edge agent graph merging** (merge local graphs into global)
- [ ] **Graph queries** (traversal, relationship queries)
- [ ] **Graph visualization** (in UI)

**Status:** 📋 Planned  
**Priority:** 🟡 Medium  
**Timeline:** 3-4 weeks  
**Dependencies:** PostgreSQL migration

#### 2.3 Data Persistence & Buffering
- [ ] **Redis integration** (for buffering/caching)
- [ ] **Kafka integration** (optional, for high-volume streaming)
- [ ] **Data loss prevention** (persistent queues)
- [ ] **Retry mechanisms** (already in collector, extend to backend)

**Status:** 📋 Planned (High priority for collector)  
**Priority:** 🔴 High (collector), 🟡 Medium (backend)  
**Timeline:** 2-3 weeks

---

### 3. Multi-Source Data Ingestion

#### 3.1 NetFlow Collection
- [x] NetFlow v5 parser (complete)
- [x] NetFlow v9 template parsing (complete)
- [x] IPFIX template parsing (complete)
- [x] SGT extraction (IPFIX IE 411/412, NetFlow v9 enterprise fields)
- [x] Native UDP collector (with SO_REUSEPORT)
- [x] Health/metrics endpoints
- [x] Retry logic with exponential backoff
- [ ] **sFlow support** (not yet implemented)
- [ ] **Data persistence/buffering** (high priority for production)
- [ ] **Production hardening** (error recovery, monitoring)

**Status:** ✅ Mostly complete  
**Priority:** 🟡 Medium (remaining items)  
**Timeline:** 1-2 weeks for remaining features

#### 3.2 ISE pxGrid Integration
- [ ] **pxGrid subscriber client** (session events)
- [ ] **Identity data ingestion** (user, device, endpoint)
- [ ] **SGT assignment data** (from ISE)
- [ ] **Policy changes** (SGACL updates from ISE)
- [ ] **Real-time synchronization** (event-driven updates)

**Status:** 📋 Planned  
**Priority:** 🔴 High  
**Timeline:** 3-4 weeks  
**Dependencies:** Streaming data processing

#### 3.3 Active Directory Integration
- [ ] **LDAP connector** (user/group queries)
- [ ] **AD group membership** (for identity enrichment)
- [ ] **User-to-device mapping** (via AD)
- [ ] **Device attributes** (from AD)
- [ ] **Scheduled synchronization** (periodic AD queries)

**Status:** 📋 Planned  
**Priority:** 🔴 High  
**Timeline:** 2-3 weeks  
**Dependencies:** Identity-aware clustering

#### 3.4 DNS Resolution
- [ ] **Hostname resolution** (IP → hostname via DNS)
- [ ] **Reverse DNS lookup** (for device identification)
- [ ] **URL resolution** (domain name resolution)
- [ ] **DNS caching** (performance optimization)
- [ ] **DNS server configuration** (custom DNS servers)

**Status:** 📋 Planned  
**Priority:** 🟡 Medium  
**Timeline:** 1-2 weeks  
**Note:** Mentioned in roadmap as needed capability

#### 3.5 IoT/Third-Party Connectors
- [ ] **IoT connector framework** (pluggable adapters)
- [ ] **MediGate integration** (healthcare IoT)
- [ ] **ClearPass integration** (Aruba device context)
- [ ] **Generic IoT adapter** (REST API based)
- [ ] **Device type enrichment** (from IoT platforms)

**Status:** 📋 Planned  
**Priority:** 🟢 Low  
**Timeline:** 4-6 weeks (framework first, then specific connectors)

#### 3.6 Correlation Engine
- [ ] **Cross-source data joins** (NetFlow + ISE + AD)
- [ ] **Identity resolution service** (IP → MAC → Endpoint → User)
- [ ] **Temporal correlation** (time-based joins)
- [ ] **Confidence scoring** (for correlated data)
- [ ] **Conflict resolution** (when sources disagree)

**Status:** 📋 Planned  
**Priority:** 🔴 High  
**Timeline:** 4-6 weeks  
**Dependencies:** Multi-source ingestion (3.2, 3.3)

---

### 4. Network Topology

#### 4.1 Location Hierarchy
- [x] Location types (Campus, Branch, Remote Site, Building, IDF)
- [x] Location CRUD API endpoints
- [x] Location hierarchy management
- [ ] **Topology builder UI** (visual hierarchy creation)
- [ ] **Location visualization** (map view, tree view)

**Status:** ✅ Core complete, UI enhancements needed  
**Priority:** 🟡 Medium  
**Timeline:** 2-3 weeks for UI enhancements

#### 4.2 Address Space Management
- [x] Address space CRUD operations
- [x] CIDR-based address ranges
- [x] Internal/external classification
- [ ] **IP range visualization** (overlapping detection)
- [ ] **Address space validation** (conflict detection)

**Status:** ✅ Core complete  
**Priority:** 🟢 Low (enhancements)

#### 4.3 Subnet-to-Location Mapping
- [x] Subnet CRUD operations
- [x] Subnet-to-location assignment
- [x] IP-to-subnet resolution
- [x] Subnet purposes (USER, SERVER, IOT, etc.)
- [ ] **Automatic subnet discovery** (optional, from routers)

**Status:** ✅ Complete  
**Priority:** 🟢 Low (enhancements)

#### 4.4 Switch-to-Location Mapping
- [x] Switch registration
- [x] Switch-to-location assignment
- [x] Switch capabilities tracking
- [x] Edge agent enablement flags
- [ ] **Switch discovery** (optional, automated discovery)

**Status:** ✅ Complete  
**Priority:** 🟢 Low (enhancements)

#### 4.5 Flow Location Correlation
- [ ] **Automatic flow enrichment** (add location context to flows)
- [ ] **Location-based queries** (flows by location)
- [ ] **Inter-location vs intra-location** analysis
- [ ] **Location-aware policy recommendations**

**Status:** 📋 Planned  
**Priority:** 🟡 Medium  
**Timeline:** 2-3 weeks  
**Dependencies:** Topology complete (4.1-4.4)

---

### 5. Edge Agent

#### 5.1 Core Edge Agent
- [x] Edge sketch building (pure Python)
- [x] Lightweight K-means clustering (k=8)
- [x] Backend synchronization (HTTP JSON/binary)
- [x] Flow simulator (for testing)
- [x] Docker containerization
- [ ] **Production deployment guides** (IOx integration)
- [ ] **Error recovery** (resilience improvements)
- [ ] **Performance optimization** (memory/CPU tuning)

**Status:** ⚠️ Basic implementation complete  
**Priority:** 🟡 Medium (Priority 5)  
**Timeline:** 2-3 weeks

#### 5.2 Cisco IOx Integration
- [ ] **IOx deployment guides** (step-by-step)
- [ ] **IOx descriptor configuration** (iox-app.yaml)
- [ ] **Resource limits** (memory, CPU constraints)
- [ ] **Network configuration** (VLAN access)
- [ ] **Monitoring integration** (IOx health checks)

**Status:** 📋 Planned  
**Priority:** 🟡 Medium  
**Timeline:** 1-2 weeks

---

### 6. Testing & Validation

#### 6.1 Ground Truth Test Datasets
- [ ] **Enterprise Corporation dataset** (multiple departments, servers, IoT)
- [ ] **Healthcare Organization dataset** (medical devices, EMR, BYOD)
- [ ] **Manufacturing Company dataset** (Industrial IoT, PLC, SCADA)
- [ ] **Education Institution dataset** (students, faculty, labs)
- [ ] **Retail Chain dataset** (POS, inventory, stores)
- [ ] **Dataset generation scripts** (synthetic data with known groups)

**Status:** 📋 Planned  
**Priority:** 🔴 High (Priority 2)  
**Timeline:** 3-4 weeks

#### 6.2 Validation Framework
- [ ] **Clustering accuracy metrics** (precision, recall, F1-score)
- [ ] **SGT assignment validation** (correct SGT assignments)
- [ ] **Performance benchmarks** (throughput, latency)
- [ ] **Regression testing** (automated validation)
- [ ] **Accuracy targets** (>90% precision, >85% recall)

**Status:** 📋 Planned  
**Priority:** 🔴 High (Priority 2.2)  
**Timeline:** 2 weeks

---

### 7. User Interface

#### 7.1 Core UI Features
- [x] React frontend (TypeScript, Tailwind CSS)
- [x] Dashboard (system metrics, health)
- [x] Network flows visualization (D3.js)
- [x] Clusters page (cluster list, members)
- [x] SGT matrix (heatmap visualization)
- [x] Policy builder (SGACL generation, editing)
- [x] Topology management (locations, subnets, switches)

#### 7.2 UI Enhancements
- [ ] **Improved cluster visualization** (better charts, PCA/t-SNE plots)
- [ ] **Real-time updates** (WebSocket for live data)
- [ ] **SGT lifecycle visualization** (timeline, changes over time)
- [ ] **Enhanced policy matrix UI** (better filtering, details)
- [ ] **AI categorization feedback** (show AI recommendations, allow override)
- [ ] **Better error handling** (user-friendly error messages)
- [ ] **Performance optimization** (virtual scrolling, lazy loading)
- [ ] **Mobile responsiveness** (if needed)

**Status:** ✅ Good foundation, enhancements needed  
**Priority:** 🟡 Medium (Priority 3)  
**Timeline:** 4-6 weeks

---

### 8. Policy Management

#### 8.1 Policy Generation
- [x] SGT matrix builder (communication patterns)
- [x] SGACL generator (permit/deny rules)
- [x] Impact analysis (what would break)
- [x] Policy customization (human-in-the-loop review)
- [x] Export formats (Cisco CLI, ISE JSON, JSON)

#### 8.2 Policy Lifecycle
- [ ] **Policy versioning** (track policy changes over time)
- [ ] **Policy approval workflow** (multi-stage approval)
- [ ] **Policy deployment** (push to ISE, monitor enforcement)
- [ ] **Policy validation** (test before deployment)
- [ ] **Rollback capability** (revert to previous policy)

**Status:** ✅ Core complete, lifecycle management planned  
**Priority:** 🟡 Medium  
**Timeline:** 3-4 weeks

---

### 9. Administrative Control

#### 9.1 Override Capabilities
- [x] Manual cluster assignment
- [x] Manual SGT assignment
- [x] Policy customization
- [x] SGT renaming/reassignment
- [ ] **Audit trail** (track all admin actions)
- [ ] **Role-based access control** (RBAC, if needed)

**Status:** ✅ Core complete  
**Priority:** 🟡 Medium (audit trail), 🟢 Low (RBAC)

#### 9.2 Configuration Management
- [ ] **Global settings UI** (clustering parameters, SGT allocation)
- [ ] **System configuration** (data sources, integrations)
- [ ] **AI configuration** (model selection, enable/disable)
- [ ] **Retention policies** (data archival settings)

**Status:** 📋 Planned  
**Priority:** 🟡 Medium  
**Timeline:** 2-3 weeks

---

### 10. Production Infrastructure

#### 10.1 Deployment
- [ ] **Production deployment guides** (step-by-step)
- [ ] **Docker Compose production config** (with all services)
- [ ] **Kubernetes manifests** (for K8s deployments)
- [ ] **High availability setup** (multi-node, load balancing)
- [ ] **Backup/restore procedures** (database backups)

**Status:** 📋 Planned  
**Priority:** 🔴 High  
**Timeline:** 2-3 weeks

#### 10.2 Monitoring & Observability
- [x] Health check endpoints (basic)
- [x] Metrics endpoints (basic)
- [ ] **Prometheus metrics export** (standard format)
- [ ] **Grafana dashboards** (pre-built dashboards)
- [ ] **Logging infrastructure** (centralized logging)
- [ ] **Alerting** (critical issues notification)

**Status:** ⚠️ Basic monitoring exists  
**Priority:** 🟡 Medium  
**Timeline:** 2-3 weeks

#### 10.3 Performance & Scalability
- [ ] **Performance benchmarks** (throughput, latency targets)
- [ ] **Load testing** (stress testing at scale)
- [ ] **Optimization** (query optimization, caching)
- [ ] **Horizontal scaling** (multi-instance deployment)
- [ ] **Capacity planning** (resource requirements guide)

**Status:** 📋 Planned  
**Priority:** 🟡 Medium  
**Timeline:** 3-4 weeks

---

## Implementation Priority Order

Based on `PRIORITIZED_ROADMAP.md`, the recommended implementation order is:

### Phase 1: Backend & Categorization (Weeks 1-6)
1. **Incremental clustering & SGT lifecycle** (Weeks 1-4)
2. **AI integration** (Weeks 5-6, after architecture validation)

### Phase 2: Testing & Validation (Weeks 7-10)
3. **Ground truth datasets** (Weeks 7-10)
4. **Validation framework** (Week 10)

### Phase 3: UI Enhancement (Weeks 11-12)
5. **UI improvements** (Weeks 11-12)

### Phase 4: Collectors & Agents (Weeks 13-14)
6. **Collector hardening** (Week 13)
7. **Edge agent optimization** (Week 14)

### Phase 5: Data Layer (Weeks 15-18)
8. **PostgreSQL migration** (Weeks 15-16)
9. **Neo4j integration** (Weeks 17-18)

### Phase 6: Multi-Source Ingestion (Weeks 19-24)
10. **ISE pxGrid** (Weeks 19-20)
11. **AD integration** (Week 21)
12. **DNS resolution** (Week 22)
13. **Correlation engine** (Weeks 23-24)

### Phase 7: Production Readiness (Weeks 25-28)
14. **Production deployment** (Week 25)
15. **Monitoring & observability** (Week 26)
16. **Performance optimization** (Weeks 27-28)

---

## Dependencies Matrix

```
Backend & Categorization
  ├─> AI Integration (requires architecture validation)
  ├─> Streaming Processing (enables real-time)
  └─> Data Layer (PostgreSQL/Neo4j)

Data Layer
  ├─> PostgreSQL Migration (foundation)
  ├─> Neo4j (requires PostgreSQL)
  └─> Data Persistence (Redis/Kafka)

Multi-Source Ingestion
  ├─> ISE pxGrid (requires streaming)
  ├─> AD Integration (requires identity-aware clustering)
  ├─> DNS Resolution (independent)
  └─> Correlation Engine (requires multi-source data)

Network Topology
  ├─> Location Hierarchy (foundation)
  ├─> Flow Location Correlation (requires topology)
  └─> Topology Builder UI (requires API)

Testing & Validation
  └─> Ground Truth Datasets (enables validation)

UI Enhancement
  ├─> Real-time Updates (requires WebSocket)
  └─> AI Feedback (requires AI integration)

Production Infrastructure
  └─> All core features (final phase)
```

---

## Success Criteria

### Categorization Engine
- [ ] Incremental clustering <100ms per endpoint
- [ ] AI integration optional and functional
- [ ] SGT lifecycle >95% stability
- [ ] First-seen tracking 100% accurate

### Data Layer
- [ ] PostgreSQL migration complete
- [ ] TimescaleDB hypertables operational
- [ ] Neo4j graph queries <500ms
- [ ] No data loss on collector crash

### Multi-Source Ingestion
- [ ] ISE pxGrid real-time sync operational
- [ ] AD integration complete
- [ ] DNS resolution <100ms
- [ ] Correlation engine >90% accuracy

### Testing
- [ ] 5+ ground truth datasets created
- [ ] Clustering accuracy >90% precision, >85% recall
- [ ] Validation framework operational
- [ ] Automated regression tests passing

### UI
- [ ] Real-time updates functional
- [ ] All features accessible via UI
- [ ] Performance <2s load times
- [ ] Mobile responsive (if needed)

### Production
- [ ] Production deployment guides complete
- [ ] High availability tested
- [ ] Monitoring/alerting operational
- [ ] Performance benchmarks met

---

## Notes

- **This roadmap consolidates all capabilities mentioned across:**
  - `PRIORITIZED_ROADMAP.md` (development priorities)
  - `README.md` (phase roadmap)
  - `docs/DESIGN.md` (architecture)
  - `docs/CATEGORIZATION_ENGINE.md` (categorization features)
  - `docs/DATA_ARCHITECTURE.md` (data layer requirements)
  - `docs/TOPOLOGY_ARCHITECTURE.md` (topology features)
  - `docs/AI_INTEGRATION.md` (AI capabilities)
  - `collector/README.md` (collector status)

- **Status Indicators:**
  - ✅ Complete
  - ⚠️ In Progress / Partial
  - 📋 Planned
  - ❌ Not Started

- **Priority Levels:**
  - 🔴 High (Critical path, blockers)
  - 🟡 Medium (Important, not blocking)
  - 🟢 Low (Nice to have, enhancements)

- **All capabilities are accounted for** - this roadmap ensures nothing is missed during implementation.

