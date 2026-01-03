# Clarion Complete Capabilities Roadmap

## Overview

This document provides a comprehensive, cohesive roadmap of all Clarion capabilities - both completed and planned. It consolidates all features, enhancements, and infrastructure requirements discussed across all documentation to ensure nothing is missed during implementation.

**🎯 Clarion's Vision:** Leverage network visibility and identity context to help users build, generate, and deploy policy across heterogeneous environments. Clarion's strength lies in gathering information from collectors, connectors, and other sources to correlate data and build policy that is both easy to understand and provides comprehensive understanding of what is happening across customer network infrastructures.

**🌐 Multi-Vendor, Multi-Environment Support:**
- **Network Vendors**: Cisco TrustSec, Aruba ClearPass, Juniper, Palo Alto, Fortinet, and others
- **Security Vendors**: Integration with various security platforms and SIEMs
- **Environments**: Campus, Branch, WAN, Cloud (AWS, Azure, GCP), Data Centers
- **Policy Enforcement Methods**: SGTs, ACLs, agents on servers, cloud security groups, firewall rules, and more

**⚠️ PRODUCTION READINESS:** Before deploying to production, review `docs/PRODUCTION_READINESS.md`. Critical infrastructure requirements (authentication, security, monitoring, high availability) must be completed first.

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
- **User database** (users, user_device_associations, ad_group_memberships tables)
- **User clustering** (user clusterer, traffic-based user clustering)
- **User SGT assignments and recommendations** (user SGT management, traffic analysis)
- **User traffic aggregation** (user traffic patterns, user-to-user traffic)
- **Containerization** (Docker, docker-compose for API, pxGrid, frontend services)
- **ISE brownfield support** (ISE configuration sync, cache, existing SGT recommendations)
- **ISE policy deployment** (automated deployment via ERS API, UI integration)

---

## Complete Capabilities Matrix

### 1. Backend & Categorization Engine

#### 1.1 Core Categorization
- [x] Batch HDBSCAN clustering
- [x] Feature extraction (18 behavioral features)
- [x] Semantic labeling (AD groups, ISE profiles, device types)
- [x] SGT mapping (cluster → SGT recommendations)
- [x] **Incremental clustering** (fast path for new endpoints) - ✅ Implemented: `IncrementalClusterer` class with centroid-based assignment
- [x] **First-seen tracking** (detect new devices/users) - ✅ Implemented: `first_seen` fields in database, `is_endpoint_first_seen()`, `get_endpoint_first_seen()`, `list_first_seen_endpoints()` methods
- [ ] **Identity-aware clustering** (handle late-arriving identity data)
- [x] **SGT lifecycle management** (stable SGTs, dynamic membership) - ✅ Implemented: `SGTLifecycleManager` class with registry, membership, and history tracking
- [ ] **Cluster stability tracking** (evolution over time)
  - [ ] **Stability scoring** (track cluster behavior changes over time)
  - [ ] **Behavior change detection** (flag clusters with wild behavior changes)
  - [ ] **SGT stability protection** (prevent automatic SGT updates for unstable clusters)
  - [ ] **Policy "flapping" prevention** (require manual review for unstable clusters)
  - [ ] **Stability metrics** (track cluster membership changes, behavior variance)
- [x] **Cluster centroid storage** (for fast incremental assignment) - ✅ Implemented: `cluster_centroids` table, `store_cluster_centroid()`, `get_cluster_centroid()`, `list_all_centroids()` methods
- [x] **Enhanced confidence scoring** (all decisions have confidence 0.0-1.0) - ✅ Implemented: `ConfidenceScorer` class with distance-based, probability-based, and combined confidence scoring
- [x] **Enhanced explainability** (clear "why" explanations for all decisions) - ✅ Implemented: `explanation.py` with `generate_cluster_explanation()` function
- [ ] **Quality assurance framework** (validation, quality monitoring)
- [ ] **Edge case handling** (ambiguous endpoints, outliers, low-confidence)
- [ ] **Override tracking & feedback loop** (learn from user overrides)

**Status:** ✅ Core complete, incremental clustering and SGT lifecycle implemented, quality enhancements in progress  
**Priority:** 🔴 High (Priority 1)  
**Timeline:** 2-4 weeks remaining (quality framework, edge cases, override tracking)  
**Quality Review:** See `docs/CATEGORIZATION_ENGINE_REVIEW.md` for detailed quality enhancements

#### 1.2 AI/LLM Integration (Optional) ⚠️ **BLOCKED: Requires Vault Integration**
- [ ] **AI categorization agent architecture**
- [ ] **LLM backend abstraction** (pluggable backends: Ollama, OpenAI, Anthropic, Google)
- [ ] **Local model support** (Llama 3, Mistral via Ollama/Transformers)
- [ ] **Cloud model support** (OpenAI GPT-4o, o1-preview, Anthropic Claude 3, Google Gemini)
- [ ] **Optional RAG** (database context for categorization, vector embeddings)
- [ ] **Fallback to rule-based labeling** (graceful degradation)
- [ ] **AI configuration management** (enable/disable, model selection, cost tracking)
- [ ] **AI explainability** (show AI reasoning to users)
- [ ] **AI vs rule-based comparison** (show both options when they differ)
- [ ] **AI enhancement framework** (AI augments, doesn't replace rule-based)
- [ ] **Conversational AI interface** (natural language queries, discussions, explanations)
- [ ] **AI-powered insights dashboard** (proactive insights, trend analysis, anomaly detection)
- [ ] **Intelligent recommendation engine** (AI-powered SGT/policy recommendations with reasoning)
- [ ] **What-if analysis** (explore scenarios and implications)
- [ ] **Data quality analysis** (AI analyzes data quality and suggests improvements)
- [ ] **Pattern detection** (early detection of traffic patterns and anomalies)
- [ ] **Security insights** (security-focused observations and recommendations)
- [ ] **Performance insights** (network performance observations)
- [ ] **Response caching** (cache AI responses for similar queries)
- [ ] **Batch processing optimization** (process multiple clusters in one request)
- [ ] **Cost optimization** (track and optimize AI API costs)
- [ ] **AI-Driven SGT Taxonomy Design** (human-readable SGT names from business context)
  - [ ] Analyze AD Group names and ISE Profiles to suggest meaningful SGT names
  - [ ] Generate business-auditor-friendly SGT names (not just "Cluster-0")
  - [ ] Context-aware naming (use business terminology, department names)
  - [ ] SGT name validation (ensure names make sense to non-technical stakeholders)

**Status:** 📋 Planned - **BLOCKED until Vault integration complete**  
**Priority:** 🔴 High (Priority 1.2) - **Cannot start until Priority 0.5 (Vault) complete**  
**Timeline:** 10 weeks (phased implementation) - **Starts after Vault integration**  
**Dependencies:** ✅ **Vault integration (Priority 0.5) - API keys must be stored in Vault**, Verify Ollama integration, validate optional architecture  
**Architecture:** See `docs/AI_ENHANCED_ARCHITECTURE.md` for comprehensive AI architecture  
**⚠️ BLOCKING:** AI integration requires API keys (OpenAI, Anthropic, Google) which must be stored in Vault, not database

#### 1.3 Streaming Data Processing
- [ ] **Real-time flow ingestion** (streaming vs batch)
- [ ] **Incremental sketch updates** (update existing sketches)
- [ ] **Streaming clustering triggers** (when to re-cluster)
- [ ] **Backpressure handling** (rate limiting, buffering)

**Status:** 📋 Planned  
**Priority:** 🟡 Medium (Priority 1.3)  
**Timeline:** 2-3 weeks

#### 1.4 Behavioral Anomaly Detection (Zero Trust Continuous Verification)
- [ ] **Baseline behavioral sketches** (establish "normal" behavior for each SGT)
- [ ] **Anomaly detection engine** (detect deviations from normal behavior)
- [ ] **Example:** Detect if "Printer" SGT starts talking to "Database" SGT over SSH
- [ ] **SGT Quarantining integration** (trigger ISE quarantine events for anomalies)
- [ ] **Continuous verification** (ongoing monitoring of SGT behavior)
- [ ] **Anomaly scoring** (confidence scores for detected anomalies)
- [ ] **False positive reduction** (learn from user feedback on anomalies)
- [ ] **Alerting and notification** (notify security team of detected anomalies)

**Status:** 📋 Planned  
**Priority:** 🔴 High (Critical for Zero Trust security)  
**Timeline:** 4-6 weeks  
**Dependencies:** Baseline behavioral sketches, ISE integration, anomaly detection algorithms

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

#### 2.2 Graph Database (Neo4j)
- [ ] **Neo4j deployment** (for relationship storage)
- [ ] **Graph schema design** (nodes, edges, properties)
  - [ ] **User → Device → App relationships** (visualize identity-to-application paths)
  - [ ] **SGT relationship graph** (show SGT-to-SGT communication patterns)
- [ ] **Edge agent graph merging** (merge local graphs into global)
- [ ] **Graph queries** (traversal, relationship queries)
- [ ] **Graph visualization** (in UI)
- [ ] **Blast Radius Analysis** (show exactly what an attacker could reach if SGT compromised)
  - [ ] **Attack path visualization** (show potential attack paths from compromised SGT)
  - [ ] **Reachability analysis** (what resources are accessible from given SGT)
  - [ ] **Risk assessment** (identify high-risk SGTs based on reachability)
  - [ ] **Graph-based policy analysis** (analyze policy effectiveness using graph)

**Status:** 📋 Planned  
**Priority:** 🟡 Medium (Enhanced with Blast Radius Analysis for security)  
**Timeline:** 4-5 weeks (enhanced with security analysis features)  
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

#### 3.1 Multi-Vendor Flow Collection
- [x] NetFlow v5 parser (complete)
- [x] NetFlow v9 template parsing (complete)
- [x] IPFIX template parsing (complete)
- [x] SGT extraction (IPFIX IE 411/412, NetFlow v9 enterprise fields)
- [x] Native UDP collector (with SO_REUSEPORT)
- [x] Health/metrics endpoints
- [x] Retry logic with exponential backoff
- [ ] **sFlow support** (Juniper, Arista, and other vendors)
- [ ] **Cloud flow log collection**
  - [ ] **AWS VPC Flow Logs** (collect from S3, CloudWatch Logs)
  - [ ] **Azure NSG Flow Logs** (collect from storage accounts)
  - [ ] **GCP VPC Flow Logs** (collect from Cloud Logging)
- [ ] **Multi-vendor flow correlation** (normalize flows from different sources)
- [ ] **Data persistence/buffering** (high priority for production)
- [ ] **Production hardening** (error recovery, monitoring)

**Status:** ✅ Mostly complete (Cisco NetFlow/IPFIX), cloud flow logs planned  
**Priority:** 🔴 High (Critical for multi-vendor visibility)  
**Timeline:** 3-4 weeks for cloud flow logs and sFlow support

#### 3.2 ISE pxGrid Integration
- [x] **User database schema** (users, user_device_associations, ad_group_memberships tables)
- [x] **pxGrid client architecture** (pxgrid_client.py, pxgrid_subscriber.py structure)
- [x] **pxGrid API endpoints** (configuration, status, test connection)
- [x] **Database schema for pxGrid data** (ise_current_sgt_assignments table)
- [x] **Connector management infrastructure** (database tables, API endpoints, certificate storage)
- [x] **Connector configuration UI** (unified UI for all connectors with enable/disable) - ✅ Implemented: `ISE.tsx`, `AD.tsx`, `IoT.tsx` connector pages with enable/disable functionality
- [ ] **Connector information tabs** (Summary/Overview tabs explaining connector purpose, capabilities, and usage - for ISE, AD, and other connectors)
- [ ] **Certificate upload UI** (upload certificates via UI for pxGrid authentication)
- [ ] **Dynamic container deployment** (automatically deploy containers when connectors enabled)
- [ ] **pxGrid WebSocket/STOMP subscription** (full real-time event reception)
- [x] **Certificate-based authentication infrastructure** (pxGrid client supports mutual TLS - implemented)
- [ ] **Certificate-based authentication testing** (test certificate auth flow end-to-end - needs validation)
- [ ] **User data ingestion from ISE** (username, mac_address, ip_address from pxGrid sessions)
- [ ] **User-device association tracking** (link users to devices from ISE sessions)
- [ ] **Identity data ingestion** (user, device, endpoint)
- [ ] **SGT assignment data** (from ISE - current ISE assignments)
- [ ] **Policy changes** (SGACL updates from ISE)
- [ ] **Real-time synchronization** (event-driven updates via WebSocket)
- [ ] **Current ISE assignment display** (show what ISE assigned in UI)
- [x] **ISE SGT import** (import existing SGT definitions from ISE via ERS API)
- [x] **ISE configuration sync** (sync existing SGTs, authorization profiles, and policies)
- [x] **ISE configuration cache** (store synced ISE configuration for brownfield support)
- [ ] **SGT assignment status check** (check if device has SGT from ISE)

**Status:** ⚠️ User database complete, brownfield sync implemented, pxGrid architecture in place, connector management infrastructure complete, certificate authentication infrastructure implemented (WebSocket/STOMP, certificate testing, and UI pending)  
**Priority:** 🔴 High (Critical for ISE alignment and User SGT recommendations)  
**Timeline:** 4-6 weeks remaining (UI implementation, WebSocket/STOMP implementation, certificate auth testing, real-time sync)  
**Dependencies:** Certificate management (infrastructure complete, UI pending), WebSocket/STOMP library integration, certificate authentication testing  
**Architecture Note:** See `docs/ISE_INTEGRATION.md` and `docs/CONNECTOR_MANAGEMENT.md` - Connector management infrastructure is complete (database, API endpoints, certificate storage). Certificate-based authentication infrastructure is implemented in pxGrid client (mutual TLS support). UI for connector configuration and certificate upload is pending. pxGrid client and subscriber architecture is implemented; WebSocket/STOMP subscription and certificate authentication testing are pending. See `docs/DEPLOYMENT_ARCHITECTURE.md` for containerized deployment architecture.

#### 3.2.1 ISE Policy Recommendation & Export
- [x] **Policy recommendation engine** (cluster → SGT → policy conditions)
- [x] **ISE authorization policy generator** (generate ISE-compatible configs)
- [x] **Policy condition mapping** (AD groups, device types, network attributes → policy rules)
- [x] **Policy impact analysis** (analyze policy change impacts)
- [x] **Policy export formats** (ISE ERS API, CLI config, JSON)
- [x] **Policy deployment workflow** (review → export → deploy)
- [x] **Automated ISE deployment** (push policies to ISE via ERS API)
- [ ] **Remove direct SGT editing** (replace with policy recommendations)
- [ ] **UI updates** (remove SGT input fields, add policy recommendations)
- [x] **Brownfield ISE support** (sync existing ISE configuration)
- [x] **ISE configuration cache** (store existing SGTs, profiles, policies)
- [x] **Recommend existing SGTs** (check ISE cache before creating new SGTs)
- [x] **ISE configuration sync API** (extract existing configuration from ISE)
- [ ] **Incremental policy updates** (generate updates vs full replacement)
- [ ] **TrustSec matrix extension** (build upon existing ISE matrix)

**Status:** ✅ Core complete, brownfield support implemented  
**Priority:** 🔴 High (Critical for ISE alignment)  
**Timeline:** ✅ Completed (Policy recommendations and brownfield support)  
**Dependencies:** None  
**Architecture Note:** See `docs/ISE_INTEGRATION.md` - Clarion supports multiple scenarios: (1) Greenfield: NetFlow → clustering → SGT recommendations → ISE policies, (2) Identity-enhanced: Same with AD/IoT data, (3) Brownfield: Sync existing ISE configuration, recommend existing SGTs when appropriate, avoid creating duplicates. Brownfield support includes ISE configuration sync, cache, and recommendation engine updates to check existing SGTs.

#### 3.3 Active Directory Integration ⚠️ **BLOCKED: Requires Vault Integration**
- [ ] **AD connector implementation** (LDAP connector for user/group queries)
- [ ] **User database enrichment** (update user records with AD data: email, department, title, display_name)
- [ ] **AD group membership queries** (user groups, nested groups)
- [ ] **AD group memberships storage** (store group memberships in ad_group_memberships table)
- [ ] **User-to-device mapping** (via AD computer objects, if computer_name matches device hostname)
- [ ] **Device attributes** (from AD)
- [ ] **Scheduled synchronization** (periodic AD queries to update user database)
- [ ] **User-device association confidence** (enhance associations from AD computer objects)
- [ ] **AD connector UI** (configuration, test connection, enable/disable, status display)
- [ ] **AD connector information tab** (Summary/Overview explaining AD connector purpose, capabilities, and usage)
- [ ] **🔍 Advanced AD Integration Architecture Investigation** (evaluate LDAP/LDAPS + DirSync for near-real-time AD mirror, WEF→WEC for Security log streaming, event correlation using stable identifiers (SID, username, computer account))
  - [ ] **LDAP/LDAPS + DirSync** (near-real-time mirror of users/groups/membership from AD)
  - [ ] **Windows Event Forwarding (WEF) → Windows Event Collector (WEC)** (stream DC and endpoint Security logs to collector)
    - [ ] Near-real-time login/logout event streaming (reduces risk of mapping flow to "previous" user)
    - [ ] Security log ingestion (authentication events, group changes)
    - [ ] Event correlation using stable identifiers (SID, username, computer account)
    - [ ] Minimal event set design (avoid unnecessary noise and DC overhead)
  - [ ] **Event correlation engine** (correlate events using stable identifiers: SID, username, computer account)
  - [ ] **Target outcomes to support:**
    - [ ] User login/logout timeline (near-real-time visibility)
    - [ ] Map user→device→IP for NetFlow correlation (reduce identity lag)
    - [ ] Detect risky auth + group changes (security insights)
  - [ ] **Architecture design** (minimal event set, avoid unnecessary noise and DC overhead)

**Status:** 📋 Planned (Basic LDAP connector) + 🔍 Investigation (Advanced architecture) - **BLOCKED until Vault integration complete**  
**Priority:** 🔴 High (Critical for User SGT recommendations) - **Cannot start until Priority 0.5 (Vault) complete**  
**Timeline:** 3-4 weeks (basic LDAP), +2-3 weeks (advanced architecture investigation and implementation) - **Starts after Vault integration**  
**Dependencies:** ✅ **Vault integration (Priority 0.5) - LDAP credentials must be stored in Vault**, Identity-aware clustering, User database schema, Connector management infrastructure  
**Note:** Advanced architecture (DirSync + WEF/WEC) provides near-real-time AD synchronization and Security event streaming, enabling better correlation than periodic LDAP queries. Investigation needed to determine optimal event set and architecture for target outcomes.  
**⚠️ BLOCKING:** AD integration requires LDAP credentials (username/password) which must be stored in Vault, not database

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

#### 3.5 IoT/Third-Party Connectors & OT Fingerprinting
- [ ] **IoT connector framework** (pluggable adapters)
- [ ] **MediGate integration** (healthcare IoT)
- [ ] **ClearPass integration** (Aruba device context)
- [ ] **Generic IoT adapter** (REST API based)
- [ ] **Device type enrichment** (from IoT platforms)
- [ ] **IoT/OT Fingerprinting** (deep protocol analysis for accurate classification)
  - [ ] **Deep Packet Inspection (DPI)** integration (identify protocols, applications)
  - [ ] **Specialized platform integration** (Medigate for medical devices, other OT platforms)
  - [ ] **Protocol-based classification** (distinguish "Medical Imaging" SGT from "Building Management" SGT)
  - [ ] **Behavioral protocol analysis** (identify devices by communication patterns)
  - [ ] **OT device fingerprinting** (SCADA, PLC, medical devices, building automation)

**Status:** 📋 Planned  
**Priority:** 🟡 Medium (Enhanced with OT fingerprinting for accurate SGT classification)  
**Timeline:** 6-8 weeks (framework + DPI/fingerprinting capabilities)

#### 3.6 Correlation Engine & Identity Enrichment
- [ ] **Cross-source data joins** (NetFlow + ISE + AD)
- [ ] **Identity resolution service** (IP → MAC → Endpoint → User)
- [ ] **Temporal correlation** (time-based joins)
- [ ] **Confidence scoring** (for correlated data)
- [ ] **Conflict resolution** (when sources disagree)
- [ ] **Passive Identity Correlation** (multi-source confidence scoring engine)
  - [ ] Correlate NetFlow + ISE pxGrid + AD for late-binding identity
  - [ ] Handle flows that start before user authentication completes
  - [ ] Confidence scoring for identity assignments (0.0-1.0)
  - [ ] Temporal correlation window (handle identity arriving after flow)
  - [ ] Multi-source identity aggregation (combine signals from all sources)
- [ ] **Identity Enrichment Framework** (high-fidelity identity context)
  - [ ] User-to-device confidence scoring
  - [ ] Device-to-IP confidence scoring
  - [ ] Historical identity patterns (learn typical user-device mappings)
  - [ ] Identity context caching (reduce correlation overhead)

**Status:** 📋 Planned  
**Priority:** 🔴 High (Critical for accurate SGT assignments)  
**Timeline:** 6-8 weeks (enhanced with identity enrichment)  
**Dependencies:** Multi-source ingestion (3.2, 3.3), Vault integration (for credentials)

---

### 3.7 User Management & User Clustering

#### 3.7.1 User Database
- [x] **User database schema** (users, user_device_associations, ad_group_memberships tables)
- [x] **User CRUD operations** (create, read, update user records)
- [x] **User-device associations** (track which users use which devices)
- [x] **AD group memberships storage** (store user AD group memberships)
- [x] **User API endpoints** (GET /users, GET /users/{user_id})
- [x] **Users UI page** (list users, view user details)
- [ ] **User search and filtering** (advanced search by department, AD group, etc.)

**Status:** ✅ Core complete  
**Priority:** ✅ Completed  
**Timeline:** ✅ Completed

#### 3.7.2 User Clustering
- [x] **User clusterer** (cluster users by AD groups and departments)
- [x] **Traffic-based user clustering** (cluster users by traffic patterns using HDBSCAN)
- [x] **User cluster storage** (user_clusters, user_cluster_assignments tables)
- [x] **User cluster API endpoints** (GET /users/clusters, GET /users/clusters/{id}/users)
- [x] **User cluster UI** (view user clusters in Clusters page)
- [x] **Mixed clustering support** (combine AD group-based and traffic-based clustering)

**Status:** ✅ Complete  
**Priority:** ✅ Completed  
**Timeline:** ✅ Completed

#### 3.7.3 User SGT Management
- [x] **User SGT assignments** (assign SGTs directly to users, separate from device SGTs)
- [x] **User SGT assignment history** (audit trail for user SGT changes)
- [x] **User SGT API endpoints** (GET/PUT/DELETE /users/{user_id}/sgt)
- [x] **User SGT UI** (view and assign SGTs in User Detail Modal)
- [x] **User SGT recommendations** (recommend SGTs based on AD groups and traffic patterns)
- [x] **User SGT recommendation engine** (compare AD group expectations vs actual traffic)
- [x] **Security-focused recommendations** (identify users with out-of-scope access)
- [x] **User cluster SGT recommendations** (recommend SGTs for entire user clusters)

**Status:** ✅ Complete  
**Priority:** ✅ Completed  
**Timeline:** ✅ Completed

#### 3.7.4 User Traffic Analysis
- [x] **User traffic aggregation** (aggregate traffic patterns per user across all devices)
- [x] **User traffic patterns** (total bytes, flows, unique peers, top ports, protocols)
- [x] **User-to-user traffic** (correlate user-to-user communication patterns)
- [x] **User traffic API endpoints** (GET /users/{user_id}/traffic)
- [x] **User traffic UI** (display traffic patterns in User Detail Modal)

**Status:** ✅ Complete  
**Priority:** ✅ Completed  
**Timeline:** ✅ Completed

**Note:** User management features are complete and integrated into the UI. Users can be managed, clustered, assigned SGTs, and have their traffic patterns analyzed for security-focused SGT recommendations.

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
- [ ] **Location-aware policy recommendations** (Geo-Segmentation)
  - [ ] **Location-based policy differentiation** (different policies for Branch vs Headquarters)
  - [ ] **Example:** Finance User in branch has more restricted access than at HQ
  - [ ] **Topology-aware policy generation** (use location hierarchy in policy conditions)
  - [ ] **Location risk scoring** (higher risk locations get stricter policies)
  - [ ] **Cross-location policy rules** (inter-location vs intra-location policies)

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
- [x] Clusters page (cluster list, members, user clusters)
- [x] SGT matrix (heatmap visualization)
- [x] Policy builder (SGACL generation, editing)
- [x] Topology management (locations, subnets, switches)
- [x] Users page (user list, user details, user SGT assignments)
- [x] User Detail Modal (user info, AD groups, devices, SGT assignments, traffic patterns)
- [x] ISE deployment UI (ISE deployment modal, policy deployment workflow)
- [x] FlowGraph navigation fixes (zoom, pan, node click locking)
- [x] Machine name display (prominent display of device names)
- [x] Connector configuration UI (ISE, AD, IoT connector pages with enable/disable, test connection, status display) - ✅ Implemented: `ISE.tsx`, `AD.tsx`, `IoT.tsx` pages
- [ ] **Connector information tabs** (Summary/Overview tabs for ISE, AD, and other connectors explaining purpose, capabilities, and usage)

#### 7.2 AI-Enhanced UI Features
- [ ] **Conversational AI chat interface** (natural language queries, discussions)
- [ ] **AI insights dashboard** (proactive insights, trend analysis, anomaly detection)
- [ ] **AI-powered explanations** (detailed explanations for any decision or recommendation)
- [ ] **What-if analysis UI** (explore scenarios and their implications)
- [ ] **AI vs rule-based comparison** (show both options when they differ)
- [ ] **AI recommendation discussions** (discuss SGT and policy recommendations with AI)
- [ ] **Data quality insights** (AI analyzes data quality and suggests improvements)
- [ ] **Pattern detection alerts** (early detection of traffic patterns and anomalies)
- [ ] **Security insights panel** (security-focused observations and recommendations)
- [ ] **Performance insights panel** (network performance observations)

**Status:** 📋 Planned  
**Priority:** 🔴 High (Priority 1.2 - AI Integration)  
**Timeline:** 6-8 weeks (phased with AI backend)  
**Dependencies:** AI backend infrastructure (Phase 3-4)

#### 7.3 UI Enhancements
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
- [ ] **Automated Policy Impact Analysis** (enhanced impact analysis for monitor mode)
  - [ ] **User/device denial preview** (show exactly which users/devices would be denied if "Permit" changed to "Deny")
  - [ ] **Traffic impact visualization** (show affected flows, connections, applications)
  - [ ] **Business impact assessment** (identify critical services that would be affected)
  - [ ] **Rollback preview** (show impact of reverting policy changes)
  - [ ] **What-if analysis** (test policy changes before deployment)
- [x] Policy customization (human-in-the-loop review)
- [x] Export formats (Cisco CLI, ISE JSON, JSON)

#### 8.3 Policy Generation (Multi-Vendor)
- [ ] **ACL generation** (traditional router/switch ACLs)
  - [ ] Standard ACLs (source-based)
  - [ ] Extended ACLs (source, destination, port, protocol)
  - [ ] Named ACLs (for modern platforms)
  - [ ] IPv6 ACLs
  - [ ] ACL optimization (minimize rules, combine overlapping rules)
- [ ] **Cloud security group generation**
  - [ ] AWS Security Groups (ingress/egress rules)
  - [ ] Azure Network Security Groups (NSG rules)
  - [ ] GCP Firewall Rules (VPC firewall rules)
  - [ ] Cloud-native policy formats (Terraform, CloudFormation, ARM templates)
- [ ] **Firewall rule generation**
  - [ ] Palo Alto firewall rules (security policies)
  - [ ] Fortinet firewall rules (security policies)
  - [ ] Check Point firewall rules
  - [ ] Generic firewall rule format (for other vendors)
- [ ] **Kubernetes Network Policy generation**
  - [ ] NetworkPolicy resource generation
  - [ ] Pod selector-based policies
  - [ ] Namespace-based policies
- [ ] **Server agent policy generation**
  - [ ] Host-based firewall rules (iptables, firewalld, Windows Firewall)
  - [ ] Agent configuration files
  - [ ] Endpoint security policies

#### 8.4 Policy Lifecycle
- [ ] **Policy versioning** (track policy changes over time)
- [ ] **Policy approval workflow** (multi-stage approval)
- [x] **ISE authorization policy recommendations** (generate policy rules from clusters)
- [x] **Policy condition mapping** (map clusters → AD groups/device types → policy conditions)
- [x] **Policy export** (ISE ERS API format, CLI config, JSON)
- [x] **Policy deployment** (push to ISE via ERS API, monitor enforcement)
- [ ] **Policy validation** (test before deployment)
- [ ] **Rollback capability** (revert to previous policy)
- [x] **Current ISE policy display** (sync and cache existing ISE policies)
- [x] **Brownfield ISE support** (sync existing ISE configuration, recommend existing SGTs)
- [ ] **Brownfield "Least-Privilege" Delta Analysis** (identify over-privileged SGTs)
  - [ ] **Over-privilege detection** (identify SGTs with "Permit All" but limited observed traffic)
  - [ ] **Policy tightening recommendations** (recommend narrowing policies based on observed behavior)
  - [ ] **Example:** If SGT has "Permit All" but only 443/TCP observed, recommend "Tighten Policy" action
  - [ ] **Privilege reduction suggestions** (show what can be safely restricted)
  - [ ] **Risk-based prioritization** (prioritize high-risk over-privileged SGTs)
- [ ] **Incremental policy updates** (generate updates vs full replacement)
- [x] **Policy comparison** (Clarion recommendations check existing ISE SGTs)
- [x] **New device policy assignment** (categorize new devices, recommend policies)

**Status:** ✅ Core complete, policy recommendations and brownfield support implemented  
**Priority:** 🔴 High (policy recommendations are critical for ISE alignment)  
**Timeline:** ✅ Completed (policy recommendations and deployment, brownfield support)  
**Architecture Note:** See `docs/ISE_INTEGRATION.md` - Policies must align with ISE authorization policy model. Supports multiple scenarios: greenfield (new deployments), brownfield (existing ISE deployments with configuration sync), identity-enhanced, and incremental updates. Brownfield support includes ISE configuration sync, cache, and recommendation engine updates.

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
- [ ] **Container health updates** (real-time health status from all containers, health check aggregation API)
- [ ] **Diagnostic logging** (structured logging, log levels, diagnostic endpoints, log aggregation)
  - [ ] **Structured logging** (JSON format, log levels, correlation IDs)
  - [ ] **Diagnostic endpoints** (detailed system state, troubleshooting info)
  - [ ] **Log aggregation** (centralized log collection and analysis)
- [ ] **Edge Agent Health Monitoring** (trust that edge agents are reporting correctly)
  - [ ] **Edge agent health status** (verify agents on switches are operational)
  - [ ] **Data reporting validation** (ensure edge agents are sending data)
  - [ ] **Agent connectivity monitoring** (detect agent disconnections)
  - [ ] **Agent performance metrics** (CPU, memory, network usage on switches)
- [ ] **Prometheus metrics export** (standard format)
- [ ] **Grafana dashboards** (pre-built dashboards)
- [ ] **Logging infrastructure** (centralized logging)
- [ ] **Alerting** (critical issues notification)

**Status:** ⚠️ Basic monitoring exists  
**Priority:** 🔴 High (container health, diagnostic logging, edge agent monitoring)  
**Timeline:** 3-4 weeks (enhanced with edge agent monitoring)

#### 10.3 Security & Secrets Management (HashiCorp Vault)

**Status:** 📋 Planned - **CRITICAL PRIORITY - Must complete before AI/AD integration**  
**Priority:** 🔴 CRITICAL (Blocks AI integration, AD integration, production deployment)  
**Timeline:** 5 weeks  
**Dependencies:** Vault deployment, authentication setup  
**Blocking:** AI integration (needs API keys), AD integration (needs LDAP credentials), production deployment

**Why This is Critical:**
- Current implementation stores secrets in SQLite database (not production-ready)
- AI integration requires API keys (OpenAI, Anthropic, Google) - must be in Vault
- AD integration requires LDAP credentials - must be in Vault
- ISE pxGrid already stores passwords and certificates in database - needs migration
- All sensitive data must be secured before production deployment

**Phase 1: Vault Infrastructure (Week 1)**
- [ ] **Vault deployment** (Docker container, Kubernetes, or standalone)
- [ ] **Vault initialization and unsealing** (key management, unseal keys)
- [ ] **Vault authentication setup** (AppRole for services, token for admin)
- [ ] **Vault policies creation** (read/write access for different services)
- [ ] **Vault secrets engine configuration** (KV v2 for secrets, PKI for certificates)
- [ ] **Vault audit logging** (track all secret access and modifications)

**Phase 2: Vault Client Integration (Week 2)**
- [ ] **Python hvac library integration** (Vault client library)
- [ ] **Vault client wrapper class** (`src/clarion/secrets/vault_client.py`)
  - [ ] Secret retrieval methods (get, list, create, update, delete)
  - [ ] Certificate storage methods (store cert, key, CA cert)
  - [ ] Connection pooling and retry logic
  - [ ] Error handling and fallback mechanisms
- [ ] **Configuration management** (Vault address, auth method, paths)
- [ ] **Health checks** (Vault connection monitoring)

**Phase 3: Secrets Migration from Database (Week 3)**
- [ ] **ISE pxGrid credentials migration**
  - [ ] Migrate ISE admin username/password from `connectors.config` JSON
  - [ ] Migrate pxGrid client credentials (username, bootstrap password)
  - [ ] Migrate pxGrid certificates (client cert, client key, CA cert) from `connector_certificates` table
- [ ] **ISE ERS API credentials migration**
  - [ ] Migrate ISE ERS API username/password from `connectors.config` JSON
- [ ] **Certificate storage migration**
  - [ ] Migrate all certificates from `certificates` table to Vault
  - [ ] Migrate all certificates from `connector_certificates` table to Vault
- [ ] **Database cleanup**
  - [ ] Remove password fields from `connectors.config` JSON
  - [ ] Remove certificate BLOB data from database tables
  - [ ] Keep only metadata and references in database
  - [ ] Add Vault path references to database (e.g., `vault_path: "secret/data/connectors/ise_pxgrid"`)

**Phase 4: Application Integration (Week 4)**
- [ ] **Update PxGridClient** to retrieve credentials from Vault
- [ ] **Update connector API routes** to use Vault for credential storage/retrieval
- [ ] **Update certificate management API** to use Vault
- [ ] **Update connector enable/test/disable flows** to use Vault
- [ ] **Add Vault health checks** to monitoring
- [ ] **Update deployment documentation** with Vault setup

**Phase 5: Secret Rotation & Management (Week 5)**
- [ ] **Secret rotation framework** (automated rotation support)
- [ ] **Automated password rotation** (for ISE, AD credentials)
- [ ] **Certificate rotation support** (pxGrid certificates, TLS certificates)
- [ ] **Secret versioning and rollback** (maintain history, rollback capability)
- [ ] **Secret expiration and renewal** (track expiration, auto-renewal)
- [ ] **Audit logging** (track secret access, modifications, rotations)

**Files to Create:**
- `src/clarion/secrets/vault_client.py` - Vault client wrapper
- `src/clarion/secrets/migration.py` - Database to Vault migration script
- `src/clarion/secrets/config.py` - Vault configuration
- `scripts/migrate_secrets_to_vault.py` - Migration script
- `docker-compose.vault.yml` - Vault deployment configuration
- `docs/VAULT_INTEGRATION.md` - Vault integration guide

**Note:** All sensitive data (passwords, API keys, certificates, tokens) must be stored in Vault, not in the database. Database should only contain non-sensitive configuration and metadata. This is a **blocking requirement** for AI integration (API keys), AD integration (LDAP credentials), and production deployment.

#### 10.4 Performance & Scalability
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

### Phase 0.5: HashiCorp Vault Integration (Weeks 1-5) 🔐 **CRITICAL - MUST COMPLETE FIRST**
1. **Vault Infrastructure** (Week 1)
   - Vault deployment and initialization
   - Authentication and policies setup
2. **Vault Client Integration** (Week 2)
   - Python hvac library integration
   - Vault client wrapper class
3. **Secrets Migration** (Week 3)
   - Migrate ISE pxGrid credentials from database
   - Migrate ISE ERS API credentials from database
   - Migrate all certificates from database
   - Database cleanup
4. **Application Integration** (Week 4)
   - Update PxGridClient to use Vault
   - Update connector API routes
   - Update certificate management
5. **Secret Rotation** (Week 5)
   - Rotation framework
   - Automated rotation
   - Versioning and rollback

### Phase 1: Backend & Categorization (Weeks 6-10)
1. **Incremental clustering & SGT lifecycle** (Weeks 6-9)
   - Enhanced confidence scoring system
   - Enhanced explainability system
   - Quality assurance framework
   - Edge case handling
2. **AI integration** (Week 10, after Vault complete) ⚠️ **Requires Vault for API keys**
   - AI explainability framework
   - AI enhancement system (augments rule-based)
   - Override tracking and feedback loop

### Phase 2: Testing & Validation (Weeks 11-14)
3. **Ground truth datasets** (Weeks 7-10)
4. **Validation framework** (Week 10)

### Phase 3: UI Enhancement (Weeks 15-16)
5. **UI improvements** (Weeks 11-12)

### Phase 4: Collectors & Agents (Weeks 17-18)
6. **Collector hardening** (Week 13)
7. **Edge agent optimization** (Week 14)

### Phase 5: Data Layer (Weeks 19-22)
8. **PostgreSQL migration** (Weeks 15-16)
9. **Neo4j integration** (Weeks 17-18)

### Phase 6: Multi-Source Ingestion (Weeks 23-28) ⚠️ **AD integration requires Vault**
10. **ISE pxGrid & User Database** (Weeks 23-25)
    - User database schema (users, user_device_associations, ad_group_memberships tables)
    - ISE pxGrid subscriber for session events
    - User-device association tracking from ISE sessions
    - Real-time user data ingestion
    - Current ISE SGT assignment tracking
11. **AD integration** (Week 26) ⚠️ **Requires Vault for LDAP credentials**
    - LDAP connector for user details
    - AD group membership queries
    - User database enrichment with AD data
    - AD group memberships storage
12. **DNS resolution** (Week 27)
13. **Correlation engine** (Week 28)

### Phase 7: Production Readiness (Weeks 29-32)
14. **Production deployment** (Week 29)
15. **Monitoring & observability** (Week 30)
16. **Performance optimization** (Weeks 31-32)

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
  ├─> User Database Schema (foundation for user-device associations)
  ├─> ISE pxGrid (requires streaming, populates user database)
  ├─> AD Integration (requires identity-aware clustering, enriches user database)
  ├─> User-Device Association Engine (requires ISE + AD data)
  ├─> DNS Resolution (independent)
  └─> Correlation Engine (requires multi-source data including user database)

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
- [ ] All decisions have confidence scores (0.0-1.0)
- [ ] All decisions have clear explanations
- [ ] Quality framework operational (validation, monitoring)
- [ ] Edge cases handled gracefully
- [ ] Override tracking and feedback loop functional
- [ ] Clustering accuracy >90% precision, >85% recall (with ground truth)

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
- [ ] HashiCorp Vault integration complete (all secrets migrated from database)
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
  - `docs/CATEGORIZATION_ENGINE_REVIEW.md` (quality enhancements and best practices)
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

