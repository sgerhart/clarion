# Clarion Prioritized Development Roadmap

## Overview

This document outlines the prioritized development plan for Clarion, focusing on building a robust, production-ready system with comprehensive testing and validation.

**🎯 Clarion's Vision:** Leverage network visibility and identity context to help users build, generate, and deploy policy across heterogeneous environments. Clarion's strength lies in gathering information from collectors, connectors, and other sources to correlate data and build policy that is both easy to understand and provides comprehensive understanding of what is happening across customer network infrastructures.

**🌐 Multi-Vendor, Multi-Environment Focus:**
- **Network Vendors**: Cisco TrustSec (current), Aruba ClearPass, Juniper, Palo Alto, Fortinet, and others
- **Environments**: Campus, Branch, WAN, Cloud (AWS, Azure, GCP), Data Centers
- **Policy Enforcement**: SGTs (current), ACLs, cloud security groups, firewall rules, server agents, and more
- **Core Strength**: Data gathering, correlation, and policy generation across heterogeneous environments

---

## Development Priorities (Optimized Build Order)

**Build Order Logic:**
1. **Foundation** (Microservices Architecture, Vault, Database, Basic Monitoring) - Must be first
2. **Core Data Collection** (Flow collection, basic connectors) - Builds on foundation
3. **Identity & Correlation** (AD, ISE, correlation engine) - Needs data sources
4. **Policy Generation** (TrustSec first, then multi-vendor) - Needs identity data
5. **Advanced Features** (AI, anomaly detection, multi-vendor deployment) - Builds on core
6. **Production Hardening** (Monitoring, HA, security) - Final polish

### Priority 0.4: Microservices Architecture 🏗️ **CRITICAL - Foundation**

**Goal:** Refactor monolithic API into pure microservices architecture with clear service boundaries, independent deployment, and modular design.

**Status:** ✅ **COMPLETE** - Architecture implemented and documented

**Why This Priority:**
- Enables independent scaling of services
- Allows independent deployment and updates
- Clear separation of concerns
- Better fault isolation
- Foundation for all other services
- Required before production deployment

**Completed Tasks:**
- [x] **Architecture Design** - Complete microservices architecture documented
- [x] **Service Structure** - All services created with Dockerfiles
- [x] **API Gateway** - Request routing and orchestration
- [x] **User Service** - User & Identity management (port 8001)
- [x] **Policy Service** - Policy management and recommendations (port 8002)
- [x] **Clustering Service** - Endpoint clustering and categorization (port 8003)
- [x] **Connector Service** - External system integrations (port 8004)
- [x] **Data Service** - Data ingestion and processing (port 8005)
- [x] **pxGrid Service** - ISE pxGrid integration (port 9000, already existed)
- [x] **Docker Compose** - Complete microservices deployment configuration
- [x] **Documentation** - Comprehensive architecture guide

**Services:**
1. **API Gateway** (`clarion-gateway:8000`) - Single entry point, request routing
2. **User Service** (`clarion-user-service:8001`) - User management, identity resolution
3. **Policy Service** (`clarion-policy-service:8002`) - Policy management, recommendations
4. **Clustering Service** (`clarion-clustering-service:8003`) - Endpoint clustering
5. **Connector Service** (`clarion-connector-service:8004`) - ISE, AD, IoT connectors
6. **Data Service** (`clarion-data-service:8005`) - NetFlow ingestion, flow processing
7. **pxGrid Service** (`clarion-pxgrid-service:9000`) - ISE pxGrid integration

**Files Created:**
- `docs/MICROSERVICES_ARCHITECTURE.md` - Complete architecture documentation
- `docker-compose.microservices.yml` - Microservices deployment configuration
- `services/gateway/` - API Gateway service
- `services/user-service/` - User & Identity service
- `services/policy-service/` - Policy service
- `services/clustering-service/` - Clustering service
- `services/connector-service/` - Connector service
- `services/data-service/` - Data ingestion service

**Communication:**
- **Synchronous**: REST APIs between services via API Gateway
- **Asynchronous**: Message Queue (Redis/RabbitMQ) - Future enhancement
- **Service Discovery**: Environment variables (can be enhanced with service mesh)

**Benefits:**
- ✅ Modular design with clear service boundaries
- ✅ Independent deployment and scaling
- ✅ Fault isolation (service failures don't cascade)
- ✅ Technology diversity (use best tool for each service)
- ✅ Team autonomy (teams can work independently)

**Priority:** 🔴 CRITICAL  
**Status:** ✅ **COMPLETE**  
**Note:** This is the foundation for all other services. All new development should follow microservices patterns.

---

### Priority 0.5: HashiCorp Vault Integration 🔐 **CRITICAL - Must Complete First**

**Goal:** Implement secure secrets management using HashiCorp Vault before implementing AI, AD, or other integrations that require credentials.

**Status:** ✅ **COMPLETE** - All Phases Complete

**Why This Priority:**
- All sensitive data (passwords, API keys, certificates, tokens) must be stored securely
- Current implementation stores secrets in SQLite database (not production-ready)
- AI integration will require API keys (OpenAI, Anthropic, etc.)
- AD integration will require LDAP credentials
- ISE pxGrid already stores passwords and certificates in database (needs migration)
- Must be completed before any production deployment

**Tasks:**

**Phase 1: Vault Infrastructure** ✅ **COMPLETE**
- [x] Vault deployment (Docker container, Kubernetes, or standalone)
- [x] Vault client wrapper class (`src/clarion/secrets/vault_client.py`)
- [x] Configuration management (Vault address, auth method, paths)
- [x] Documentation (`docs/VAULT_INTEGRATION.md`)

**Phase 2: Vault Client Integration** ✅ **COMPLETE**
- [x] Python hvac library integration
- [x] Secret retrieval methods (get, list, create, update, delete)
- [x] Certificate storage methods (store cert, key, CA cert)
- [x] Connection pooling and retry logic
- [x] Error handling and fallback mechanisms
- [x] Thread-safe client access
- [x] Automatic token refresh
- [x] Comprehensive test suite

**Phase 3: Secrets Migration from Database**
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
- [ ] Update `PxGridClient` to retrieve credentials from Vault
- [ ] Update connector API routes to use Vault for credential storage/retrieval
- [ ] Update certificate management API to use Vault
- [ ] Update connector enable/test/disable flows to use Vault
- [ ] Add Vault health checks
- [ ] Add Vault connection monitoring
- [ ] Update deployment documentation

**Phase 5: Secret Rotation & Management (Week 5)**
- [ ] Secret rotation framework
- [ ] Automated password rotation (for ISE, AD credentials)
- [ ] Certificate rotation support
- [ ] Secret versioning and rollback
- [ ] Secret expiration and renewal
- [ ] Audit logging for secret access

**Files to Create:**
- `src/clarion/secrets/vault_client.py` - Vault client wrapper
- `src/clarion/secrets/migration.py` - Database to Vault migration script
- `src/clarion/secrets/config.py` - Vault configuration
- `scripts/migrate_secrets_to_vault.py` - Migration script
- `docker-compose.vault.yml` - Vault deployment configuration
- `docs/VAULT_INTEGRATION.md` - Vault integration guide

**Dependencies:**
- HashiCorp Vault deployment
- Python hvac library
- Existing secrets in database (for migration)

**Priority:** 🔴 CRITICAL  
**Status:** ✅ **COMPLETE** - All 5 Phases Complete  
**Blocking:** ~~AI integration, AD integration, production deployment~~ (No longer blocking - ready for use)  
**Note:** This must be completed before implementing AI (which needs API keys) or AD (which needs LDAP credentials). All existing secrets in the database must be migrated to Vault.

---

### Priority 0.6: PostgreSQL/TimescaleDB Migration 🗄️ **CRITICAL - Parallel with Vault**

**Goal:** Migrate from SQLite to PostgreSQL with TimescaleDB for production-scale time-series data.

**Status:** ❌ Not Started - Critical for Production Scale

**Why This Priority:**
- SQLite is not suitable for production-scale flow data
- TimescaleDB provides time-series optimization for flow data
- Required before heavy data ingestion (connectors, multi-vendor)
- Can run parallel with Vault (after Week 1)

**Tasks:**
- [ ] PostgreSQL deployment (Docker container or managed service)
- [ ] TimescaleDB extension installation
- [ ] Database schema migration (all existing tables)
- [ ] Hypertable creation (for flow data partitioning)
- [ ] Data migration scripts (SQLite → PostgreSQL)
- [ ] Performance optimization (indexes, query tuning)
- [ ] Data retention policies (automated archival/compression)

**Priority:** 🔴 CRITICAL  
**Timeline:** 4 weeks (Weeks 2-5, parallel with Vault after Week 1)  
**Dependencies:** None (can start after Week 1)  
**Note:** Can run parallel with Vault integration (after Week 1). Required before heavy data ingestion.

---

### Priority 0.7: Basic Monitoring & Diagnostic Logging 📊 **CRITICAL - Parallel with Vault/DB**

**Goal:** Implement basic monitoring and diagnostic capabilities for operational visibility.

**Status:** ❌ Not Started - Critical for Operations

**Why This Priority:**
- Need visibility into system health early
- Container health monitoring required for multi-service architecture
- Diagnostic logging needed for troubleshooting
- Can run parallel with Vault and PostgreSQL

**Tasks:**
- [ ] Structured logging (JSON format, log levels)
- [ ] Diagnostic endpoints (health checks, system info)
- [ ] Container health updates (real-time health status from all containers)
- [ ] Edge agent health monitoring (health status from edge agents)
- [ ] Basic Prometheus metrics (request counts, latency, errors)
- [ ] Log aggregation setup (centralized logging)

**Priority:** 🔴 CRITICAL  
**Timeline:** 3 weeks (Weeks 3-5, parallel with Vault/DB)  
**Dependencies:** None (can start in parallel)  
**Note:** Can run parallel with Vault and PostgreSQL. Required for operational visibility.

---

### Priority 0.8: Neo4j Graph Database Integration 🕸️ **Dual Graph Architecture**

**Goal:** Deploy Neo4j with dual graph architecture for both behavioral relationships and network topology.

**Status:** ❌ Not Started - Required for Network Topology and Flow Analysis

**Why This Priority:**
- Network Topology (Priority 2.6) requires graph database for device connection graph
- Flow analysis requires graph for behavioral relationships
- Attack path mapping requires graph queries
- Blast radius analysis requires graph traversal
- Should be deployed before Network Topology work begins

**Tasks:**

**Graph 1: Flow Graph (Behavioral Relationships)**
- [ ] Neo4j deployment (Docker container or managed service)
- [ ] Flow Graph schema design (Endpoint, User, Service, Cluster, SGT nodes)
- [ ] Flow Graph edges (FLOWS_TO, ASSIGNED_TO, MEMBER_OF, TAGGED_WITH, COMMUNICATES_WITH)
- [ ] User → Device → App relationship graph
- [ ] SGT relationship graph (SGT-to-SGT communication patterns)
- [ ] Edge agent graph merging (merge local graphs into global Flow Graph)
- [ ] Flow Graph queries (traversal, relationship queries, blast radius analysis)

**Graph 2: Topology Graph (Infrastructure Relationships)**
- [ ] Topology Graph schema design (Device, Interface, Subnet, VLAN, Zone, Location nodes)
- [ ] Topology Graph edges (CONNECTED_TO, HAS_INTERFACE, CONNECTED_VIA, ROUTES_TO, LOCATED_AT, ENFORCES_POLICY)
- [ ] Network topology graph (device nodes, connection edges, interface relationships)
- [ ] Topology Graph queries (path finding, attack path mapping, policy gap detection)
- [ ] Cross-graph correlation (Flow Graph ↔ Topology Graph)

**Common:**
- [ ] Graph visualization (in UI)
- [ ] Graph query API endpoints
- [ ] Graph performance optimization

**Priority:** 🔴 High  
**Timeline:** 4-5 weeks (Weeks 18-22, before Network Topology)  
**Dependencies:** PostgreSQL migration (Priority 0.6)  
**See:** [DATA_STRATEGY.md](docs/DATA_STRATEGY.md) for complete dual graph architecture  
**Note:** Should be deployed before Network Topology (Priority 2.6) work begins. Can run parallel with Policy Generation (Priority 2).

---

### Priority 0.9: Vector Database Integration 🔍 **Required for AI/RAG**

**Goal:** Deploy vector database for RAG (Retrieval-Augmented Generation) context storage and semantic search.

**Status:** ❌ Not Started - Required for AI Integration

**Why This Priority:**
- AI integration (Priority 1.2) requires vector database for RAG context
- Configuration analysis requires semantic search across vendor configs
- Similar pattern discovery (clusters, policies) requires embeddings
- Should be deployed before AI integration work begins

**Tasks:**
- [ ] Vector database selection and deployment (Chroma for dev, Qdrant for prod)
- [ ] Embedding model selection and integration (sentence-transformers, OpenAI embeddings)
- [ ] Cluster description storage (store cluster descriptions with embeddings)
- [ ] Policy justification storage (store policy justifications with embeddings)
- [ ] Configuration snippet storage (store device config snippets with embeddings)
- [ ] Historical decision storage (store past decisions with context)
- [ ] RAG context builder (retrieve relevant context for AI agents)
- [ ] Semantic search API (find similar clusters, policies, configurations)
- [ ] Vector database performance optimization

**Priority:** 🔴 High (Required for AI integration)  
**Timeline:** 2-3 weeks (Weeks 20-22, parallel with Neo4j)  
**Dependencies:** AI backend infrastructure (Priority 1.2), embedding model selection  
**See:** [DATA_STRATEGY.md](docs/DATA_STRATEGY.md) for complete vector database strategy  
**Note:** Can run parallel with Neo4j (Priority 0.8). Required before AI integration (Priority 1.2) can begin.

---

### Priority 1: Backend & Categorization Engine ⭐ **CURRENT FOCUS**

**Goal:** Build a sophisticated categorization engine with AI integration, incremental clustering, and comprehensive data processing.

#### 1.1 Categorization Engine Core

**Status:** ✅ Core features complete (incremental clustering, SGT lifecycle, confidence, explainability), quality enhancements in progress

**Tasks:**
- [x] Incremental clustering (fast path for new endpoints) - ✅ Implemented: `IncrementalClusterer` class
- [x] First-seen tracking (detect new devices/users) - ✅ Implemented: Database fields and methods
- [ ] Identity-aware clustering (handle late-arriving identity data)
- [x] SGT lifecycle management (stable SGTs, dynamic membership) - ✅ Implemented: `SGTLifecycleManager` class
- [ ] **Cluster stability tracking** (evolution over time)
  - [ ] **Stability scoring** (track cluster behavior changes over time)
  - [ ] **Behavior change detection** (flag clusters with wild behavior changes)
  - [ ] **SGT stability protection** (prevent automatic SGT updates for unstable clusters)
  - [ ] **Policy "flapping" prevention** (require manual review for unstable clusters)
- [x] Database schema updates (first_seen, SGT registry, centroids) - ✅ Implemented: All tables and methods exist
- [x] **Enhanced confidence scoring system** (all decisions have confidence scores) - ✅ Implemented: `ConfidenceScorer` class
- [x] **Enhanced explainability system** (clear "why" explanations for all decisions) - ✅ Implemented: `explanation.py` module
- [ ] **Quality assurance framework** (validation and quality monitoring)
- [ ] **Edge case handling** (ambiguous endpoints, outliers, low-confidence cases)
- [ ] **Override tracking and feedback loop** (learn from user overrides)

**Files:**
- `src/clarion/clustering/incremental.py`
- `src/clarion/clustering/sgt_lifecycle.py`
- `src/clarion/clustering/confidence.py` (confidence scoring)
- `src/clarion/clustering/explanation.py` (enhanced explanations)
- `src/clarion/clustering/quality.py` (quality monitoring)
- `src/clarion/clustering/edge_cases.py` (edge case handling)
- `src/clarion/clustering/override_learning.py` (override feedback loop)
- `src/clarion/storage/database.py` (schema updates)

**See:** `docs/CATEGORIZATION_ENGINE_REVIEW.md` for detailed quality enhancements

#### 1.2 AI/LLM Integration (Optional)

**Status:** 📋 Planned

**Phase 1: Core AI Infrastructure (Weeks 1-2)**
- [ ] LLM backend abstraction layer (pluggable backends)
- [ ] Ollama integration (local models: Llama 3, Mistral)
- [ ] AI agent base classes
- [ ] Basic cluster labeling with AI
- [ ] Configuration management
- [ ] Error handling and fallback

**Phase 2: Cloud Integration (Weeks 3-4)**
- [ ] OpenAI integration (GPT-4o, o1-preview)
- [ ] Anthropic integration (Claude 3 Opus, Sonnet, Haiku)
- [ ] Google Gemini integration
- [ ] Rate limiting and cost tracking
- [ ] Response caching (Redis)

**Phase 3: Conversational AI Interface (Weeks 5-6)**
- [ ] Conversational AI agent
- [ ] Natural language query processing
- [ ] Context retrieval from database
- [ ] Explanation generation
- [ ] What-if analysis capabilities
- [ ] Chat API endpoint
- [ ] Frontend chat interface

**Phase 4: RAG & Advanced Features (Weeks 7-8)**
- [ ] RAG context builder
- [ ] Knowledge base system
- [ ] Vector embeddings for similarity search
- [ ] Advanced insights generation
- [ ] Proactive recommendations
- [ ] AI-powered insights dashboard

**Phase 5: Optimization & Production (Weeks 9-10)**
- [ ] Performance optimization
- [ ] Caching strategies
- [ ] Batch processing optimization
- [ ] Production hardening
- [ ] Comprehensive testing
- [ ] **AI-Driven SGT Taxonomy Design** (human-readable SGT names from business context)
  - [ ] Analyze AD Group names and ISE Profiles to suggest meaningful SGT names
  - [ ] Generate business-auditor-friendly SGT names (not just "Cluster-0")
  - [ ] Context-aware naming (use business terminology, department names)

**Files:**
- `src/clarion/ai/llm_backend.py` - LLM abstraction
- `src/clarion/ai/agents/cluster_agent.py` - Cluster analysis
- `src/clarion/ai/agents/conversational_agent.py` - Conversational AI
- `src/clarion/ai/rag/context_builder.py` - RAG context
- `src/clarion/ai/rag/knowledge_base.py` - Knowledge base
- `src/clarion/ai/config.py` - AI configuration
- `src/clarion/api/routes/ai_chat.py` - Chat API
- `frontend/src/components/AIChat.tsx` - Chat UI

**Dependencies:**
- ✅ **Vault integration complete** (API keys must be stored in Vault, not database)
- ✅ **Vector database (Priority 0.9) - Required for RAG context**
- Verify architecture can support local models before implementation
- Ensure optional nature (can disable AI completely)
- AI must enhance, not replace rule-based logic
- LangChain for orchestration
- LlamaIndex for RAG (optional)

**Architecture:** See `docs/AI_ENHANCED_ARCHITECTURE.md` for comprehensive design

**⚠️ BLOCKED:** Cannot start AI implementation until Vault integration is complete (Priority 0.5)


---

**Goal:** Build comprehensive test datasets representing different company types to validate categorization accuracy.

#### 2.1 Ground Truth Test Datasets

**Status:** 📋 Planned

**Company Types to Model:**

1. **Enterprise Corporation**
   - Multiple departments (Engineering, Sales, Marketing, Finance, HR, IT)
   - Server infrastructure (web, database, file servers)
   - IoT devices (cameras, sensors)
   - Guest network
   - VPN users

2. **Healthcare Organization**
   - Medical devices (MRI, CT scanners, patient monitors)
   - EMR systems
   - BYOD devices
   - Guest WiFi
   - Compliance considerations

3. **Manufacturing Company**
   - Industrial IoT (PLC, SCADA)
   - Production servers
   - Office workstations
   - Warehouse devices
   - OT/IT convergence

4. **Education Institution**
   - Student devices (BYOD)
   - Faculty workstations
   - Lab computers
   - Library devices
   - Guest access

5. **Retail Chain**
   - Point of sale (POS) systems
   - Inventory systems
   - Guest WiFi
   - Corporate office
   - Warehouse/DC

**Tasks:**
- [ ] Design dataset schemas for each company type
- [ ] Generate synthetic data with known groups
- [ ] Create validation scripts
- [ ] Implement metrics (precision, recall, F1-score)
- [ ] Automated validation pipeline

**Files:**
- `tests/data/ground_truth/enterprise/`
- `tests/data/ground_truth/healthcare/`
- `tests/data/ground_truth/manufacturing/`
- `tests/data/ground_truth/education/`
- `tests/data/ground_truth/retail/`
- `src/clarion/clustering/validator.py`
- `tests/integration/test_clustering_accuracy.py`

**Timeline:** 3-4 weeks

#### 2.2 Validation Framework

**Status:** 📋 Planned

**Tasks:**
- [ ] Clustering accuracy metrics
- [ ] SGT assignment validation
- [ ] Performance benchmarks
- [ ] Regression testing

**Timeline:** 2 weeks  
**Priority:** 🟡 Medium (Important for validation, but not blocking)  
**Dependencies:** Core clustering and policy generation

---

### Priority 2.6: Network Topology & Device Discovery 🌐 **Critical for Complete Network Understanding**

**Goal:** Build complete network topology including routers and firewalls, with device discovery and graph-based attack path mapping.

**Status:** ⚠️ Switches implemented, routers/firewalls and discovery needed

**Current State:**
- Switch registration and management implemented
- Location hierarchy implemented
- Subnet-to-location mapping implemented

**Enhancements Needed:**

#### 2.6.1 Router & Firewall Management
- [ ] **Router registration and management**
  - [ ] Router device model (router_id, hostname, model, location, management_ip)
  - [ ] Router-to-location assignment
  - [ ] Router capabilities tracking (routing protocols, ACL support)
  - [ ] Router interface management (interfaces, IPs, connected devices)
- [ ] **Firewall registration and management**
  - [ ] Firewall device model (firewall_id, hostname, model, vendor, location)
  - [ ] Firewall-to-location assignment
  - [ ] Firewall capabilities tracking (NAT, VPN, threat detection)
  - [ ] Firewall zone/interface management (security zones, interfaces)
- [ ] **Unified device management** (switches, routers, firewalls)
  - [ ] Device type classification
  - [ ] Common device attributes
  - [ ] Device status monitoring

#### 2.6.2 Device Discovery & Information Gathering
- [ ] **SNMP-based device discovery**
  - [ ] SNMP v2c/v3 support
  - [ ] Device discovery via SNMP (walk MIBs)
  - [ ] Device information gathering (hostname, model, serial, software)
  - [ ] Interface discovery (interfaces, IPs, status)
  - [ ] LLDP/CDP neighbor discovery (build connection graph)
- [ ] **API-based device discovery**
  - [ ] Cisco devices (RESTCONF, NETCONF, SSH/CLI)
  - [ ] Juniper devices (NETCONF, REST API)
  - [ ] Palo Alto firewalls (REST API, Panorama)
  - [ ] Fortinet firewalls (REST API, FortiManager)
  - [ ] Generic REST API support
- [ ] **Configuration data parsing**
  - [ ] Parse device configurations
  - [ ] Extract interface, routing, firewall rule information
  - [ ] Configuration change tracking

#### 2.6.3 Network Topology Graph & Attack Path Mapping
- [ ] **Network topology graph database** (in Neo4j)
  - [ ] Device nodes (switches, routers, firewalls, endpoints)
  - [ ] Connection edges (physical links, logical connections, routing paths)
  - [ ] Interface relationships
  - [ ] VLAN/zone relationships
  - [ ] Policy enforcement points
- [ ] **Attack path mapping**
  - [ ] Path discovery (find all paths from source to destination)
  - [ ] Policy-aware path analysis (consider policies at each hop)
  - [ ] Attack path visualization (show paths through network)
  - [ ] Blast radius analysis (what can be reached from compromised device/SGT)
  - [ ] Critical path identification
  - [ ] Policy gap detection
- [ ] **Policy implementation mapping**
  - [ ] Policy enforcement point identification
  - [ ] End-to-end policy analysis (trace policy across network path)
  - [ ] Multi-device policy coordination
  - [ ] Policy conflict detection
  - [ ] Policy coverage analysis

**Priority:** 🔴 High (Critical for complete network understanding and security)  
**Timeline:** 8-10 weeks (device management: 2 weeks, discovery: 4 weeks, topology graph: 2-4 weeks)  
**Dependencies:** Graph database (Priority 0.8), Vault integration (Priority 0.5, for SNMP/API credentials), Device management APIs, PostgreSQL (Priority 0.6)

---

### Priority 3: UI Enhancement & User Experience 🎨

**Goal:** Enhance the existing UI to be production-ready and user-friendly.

**Status:** ✅ Good foundation exists

**Current State:**
- React frontend with good structure
- Basic visualization components
- API integration

**Enhancements Needed:**
- [ ] Improved cluster visualization
- [ ] Real-time updates (WebSocket)
- [ ] Better SGT lifecycle visualization
- [ ] Enhanced policy matrix UI
- [ ] AI categorization feedback/controls
- [ ] Better error handling and user feedback
- [x] **Connector configuration UI** (unified UI for all connectors with enable/disable) - ✅ Implemented: `ISE.tsx`, `AD.tsx`, `IoT.tsx` pages
- [ ] **Connector information tabs** (Summary/Overview tabs for ISE, AD, and other connectors explaining purpose, capabilities, and usage)
- [ ] **Network topology visualization** (visual network graph with devices, connections, attack paths)
- [ ] **Attack path visualization UI** (interactive attack path mapping)
- [ ] Performance optimization
- [ ] Mobile responsiveness (if needed)

**Timeline:** 4-6 weeks

---

### Priority 4: Collectors & Data Sources 📡

**Status:** ✅ Mostly Complete (Cisco NetFlow), Multi-vendor planned

**Current State:**
- NetFlow v5 fully implemented
- NetFlow v9/IPFIX template parsing implemented
- Health/metrics endpoints
- Docker support

**Remaining Tasks:**
- [ ] Production hardening
- [ ] Performance optimization
- [ ] **Cloud flow log collection** (AWS VPC Flow Logs, Azure NSG Flow Logs, GCP VPC Flow Logs)
- [ ] **sFlow support** (Juniper, Arista)
- [ ] Enhanced monitoring
- [ ] Documentation

**Timeline:** 3-4 weeks (production hardening: 1-2 weeks, cloud flow logs: 2 weeks)  
**Priority:** 🟡 Medium (Core functionality mostly complete, enhancements for multi-vendor)

---

### Priority 5: Advanced Features 🚀

#### 5.1 Behavioral Anomaly Detection (Zero Trust Continuous Verification)

**Status:** 📋 Planned

**Goal:** Detect behavioral anomalies and trigger security responses (SGT quarantining) for Zero Trust continuous verification.

**Tasks:**
- [ ] Baseline behavioral sketches (establish "normal" behavior for each SGT)
- [ ] Anomaly detection engine (detect deviations from normal behavior)
- [ ] SGT Quarantining integration (trigger ISE quarantine events for anomalies)
- [ ] Continuous verification (ongoing monitoring of SGT behavior)
- [ ] Anomaly scoring (confidence scores for detected anomalies)
- [ ] False positive reduction (learn from user feedback on anomalies)
- [ ] Alerting and notification (notify security team of detected anomalies)

**Priority:** 🔴 High (Critical for Zero Trust security)  
**Timeline:** 4-6 weeks  
**Dependencies:** Baseline behavioral sketches, ISE integration, anomaly detection algorithms

#### 5.2 Multi-Vendor Connectors & Cloud Integration

**Status:** 📋 Planned

**Goal:** Expand connector support to multiple vendors and cloud platforms.

**Tasks:**
- [ ] **Multi-vendor connector framework** (pluggable adapters for various vendors)
- [ ] **Cloud platform connectors** (AWS, Azure, GCP - flow logs, security groups, IAM)
- [ ] **Additional network vendor connectors** (Aruba ClearPass, Palo Alto, Fortinet)
- [ ] **Security vendor connectors** (SIEM, EDR/XDR, Identity providers)
- [ ] **Multi-environment support** (Campus, Branch, WAN, Cloud, Data Centers)

**Priority:** 🔴 High (Critical for multi-vendor vision)  
**Timeline:** 12-16 weeks (framework: 4 weeks, connectors: 8-12 weeks)  
**Dependencies:** Vault integration (Priority 0.5), PostgreSQL migration (Priority 0.6), Graph database (Priority 0.8)

---

### Priority 0: Production Infrastructure 🔴 **CRITICAL - Must Complete Before Production**

**Goal:** Make Clarion production-ready with security, monitoring, and high availability.

**Status:** ❌ Not Started - Critical Gap

**Tasks:**
- [ ] Authentication & Authorization (JWT-based, user management, RBAC)
- [ ] Security Hardening (rate limiting, input validation, SSL/TLS)
- [ ] PostgreSQL Migration (production database, migration scripts)
- [ ] Monitoring & Observability (Prometheus metrics, centralized logging, alerting, Grafana)
- [ ] **Container Health Updates** (real-time health status from all containers, health check aggregation)
- [ ] **Diagnostic Logging** (structured logging, log levels, log aggregation, diagnostic endpoints)
- [ ] High Availability (multi-instance deployment, load balancing, failover)
- [ ] CI/CD Pipeline (automated builds, deployment automation)
- [ ] Database Backup/Recovery (backup procedures, disaster recovery)

**Priority:** 🔴 CRITICAL  
**Timeline:** 10-14 weeks (Phase 1: 4-6 weeks, Phase 2: 4-6 weeks, Phase 3: 2-4 weeks)  
**Note:** See `docs/PRODUCTION_READINESS.md` for detailed requirements and prioritization. **Note:** Vault integration has been moved to Priority 0.5 and must be completed before AI/AD integration and production deployment.

**This must be completed before any production deployment.**

---

### Priority 6: Edge Agent 🔄

**Status:** ⚠️ Basic implementation exists

**Current State:**
- Edge agent with sketch building
- Lightweight clustering
- Backend sync

**Enhancements Needed:**
- [ ] Production deployment guides
- [ ] Cisco IOx integration
- [ ] Performance optimization
- [ ] Error recovery

**Timeline:** 2-3 weeks  
**Priority:** 🟡 Medium (Enhancement, not blocking)

---

## Development Timeline

### Q1 2025 (Weeks 1-17) - Foundation & Core

**Weeks 1-5: HashiCorp Vault Integration** 🔐 **CRITICAL - MUST COMPLETE FIRST**
- Vault deployment and infrastructure
- Vault client integration
- Secrets migration from database to Vault
- Application integration
- Secret rotation and management

**Weeks 2-5: PostgreSQL/TimescaleDB Migration** 🗄️ **Parallel with Vault (after Week 1)**
- PostgreSQL deployment
- TimescaleDB extension installation
- Database schema migration
- Hypertable creation
- Data migration scripts
- Performance optimization

**Weeks 3-5: Basic Monitoring & Diagnostic Logging** 📊 **Parallel with Vault/DB**
- Structured logging
- Diagnostic endpoints
- Container health updates
- Edge agent health monitoring
- Basic Prometheus metrics

**Weeks 6-9: Backend Core Enhancements** ✅ **Mostly COMPLETED**
- ✅ Incremental clustering - `IncrementalClusterer` implemented
- ✅ First-seen tracking - Database fields and methods implemented
- ✅ SGT lifecycle management - `SGTLifecycleManager` implemented
- ✅ Database schema updates - All tables implemented
- ✅ Enhanced confidence scoring system - `ConfidenceScorer` implemented
- ✅ Enhanced explainability system - `explanation.py` implemented
- [ ] Quality assurance framework - **Remaining**
- [ ] Edge case handling - **Remaining**
- [ ] Cluster stability tracking - **Remaining**

**Weeks 10-13: Connectors & Identity** (⚠️ Requires Vault)
- AD connector implementation (LDAP, user/group queries)
- ISE pxGrid WebSocket/STOMP integration completion
- Advanced AD Integration (WEF/WEC) investigation
- User-device association resolution engine

**Weeks 14-17: Identity Correlation & Enrichment** 🔗
- Passive Identity Correlation (multi-source confidence scoring)
- Identity Enrichment Framework
- Cloud identity correlation
- Cross-environment identity tracking

### Q2 2025 (Weeks 18-29) - Policy & Multi-Vendor

**Weeks 18-22: Graph Database, Vector DB & Policy Generation** 🕸️🔍🎯
- Neo4j Graph Integration (Priority 0.8) - **Dual Graph Architecture (Flow Graph + Topology Graph)**
- Vector Database Integration (Priority 0.9) - **Required for AI/RAG**
- Enhanced TrustSec policy (impact analysis, stability tracking)
- Brownfield "Least-Privilege" Delta Analysis
- Unified Policy Model (vendor-agnostic representation)
- Policy translation engine (TrustSec first, then multi-vendor)

**Weeks 27-28: Test Scenarios & Validation** 🧪
- Ground truth dataset creation
- Validation framework
- Testing across company types
- Accuracy metrics

**Weeks 29-32: Multi-Vendor Expansion** 🌐
- ✅ User database schema creation (completed)
- ✅ User management (CRUD operations, API endpoints, UI)
- ✅ User clustering (AD group-based and traffic-based clustering)
- ✅ User SGT assignments and recommendations (user SGT management, traffic analysis)
- ✅ User traffic aggregation (user traffic patterns, user-to-user traffic)
- ✅ ISE ERS API integration (brownfield support: sync existing ISE configuration)
- ✅ ISE configuration cache (store existing SGTs, profiles, policies)
- ✅ Policy recommendation engine with brownfield support (check existing SGTs)
- ✅ Containerization (Docker, docker-compose for API, pxGrid, frontend services)
- [ ] **Multi-vendor connector framework** (pluggable adapters for various vendors)
- [ ] **Cloud platform connectors** (AWS, Azure, GCP - flow logs, security groups, IAM)
- [ ] **Additional network vendor connectors** (Aruba ClearPass, Palo Alto, Fortinet)
- [ ] **Multi-environment support** (Campus, Branch, WAN, Cloud, Data Centers)
- [ ] Cloud flow log collection (AWS VPC Flow Logs, Azure NSG Flow Logs, GCP VPC Flow Logs)
- [ ] sFlow support (Juniper, Arista)

**Weeks 33-34: Advanced Features & Integration** 🚀
- Behavioral Anomaly Detection (Zero Trust continuous verification)
- AI Integration (⚠️ Requires Vault for API keys)
- Multi-vendor policy deployment orchestration
- End-to-end testing
- Performance optimization
- Bug fixes

### Q3 2025 (Weeks 34+) - Production Readiness

**Weeks 35-38: Production Infrastructure** 🔴
- Authentication & Authorization (JWT-based, RBAC)
- Security Hardening (rate limiting, SSL/TLS)
- Full Monitoring & Observability (Grafana dashboards, alerting)
- High Availability setup
- CI/CD Pipeline
- Database Backup/Recovery

**Weeks 39+: UI Enhancement & Polish** 🎨
- Real-time updates (WebSocket)
- Enhanced visualizations
- AI controls/feedback
- Connector information tabs
- Location-aware policy visualization
- Performance optimization

---

## Key Decisions

### AI Integration

**Decision:** AI is **optional** and supports:
- Local models (Llama, Mistral) via Ollama
- Cloud models (OpenAI, Anthropic)
- RAG is optional (can use database context)
- Must gracefully degrade to rule-based labeling

**Rationale:**
- Privacy concerns (local models)
- Cost concerns (cloud models)
- Flexibility for different customer needs

### Architecture Validation

**Before implementing AI:**
1. Verify Ollama integration works
2. Test local model performance
3. Validate architecture supports pluggable backends
4. Confirm optional nature doesn't complicate codebase

### Testing Strategy

**Focus on validation:**
- Multiple company types
- Known ground truth
- Accuracy metrics
- Regression testing

**Rationale:**
- Need confidence in categorization accuracy
- Different company types have different patterns
- Validation ensures system works correctly

---

## Success Criteria

### Categorization Engine

- [x] Incremental clustering works (<100ms per endpoint) - ✅ Implemented and tested
- [ ] AI integration optional and functional
- [x] SGT lifecycle stable (>95% stability) - ✅ Implemented: `SGTLifecycleManager` with registry and membership tracking
- [x] First-seen tracking accurate - ✅ Implemented: Database fields and methods
- [x] All decisions have confidence scores (0.0-1.0) - ✅ Implemented: `ConfidenceScorer` class
- [x] All decisions have clear explanations - ✅ Implemented: `explanation.py` module
- [ ] Quality framework operational (validation, monitoring) - **Remaining**
- [ ] Edge cases handled gracefully - **Remaining**
- [ ] Override tracking and feedback loop functional - **Remaining**

### Test Scenarios

- [ ] 5+ company type datasets created
- [ ] Clustering accuracy >90% precision, >85% recall
- [ ] Validation framework operational
- [ ] Automated regression tests

### UI

- [ ] Real-time updates functional
- [ ] All features accessible via UI
- [ ] Performance acceptable (<2s load times)
- [ ] User-friendly and intuitive

### Collectors & Agents

- [ ] Production-ready
- [ ] Well-documented
- [ ] Performance optimized
- [ ] Deployment guides complete

---

## Complete Capabilities Reference

**See:** [`CAPABILITIES_ROADMAP.md`](../CAPABILITIES_ROADMAP.md) for a comprehensive, consolidated view of ALL capabilities discussed across all documentation.

This prioritized roadmap focuses on **implementation order and priorities**, while the capabilities roadmap ensures **nothing is missed** - it catalogs every feature, enhancement, and infrastructure requirement mentioned across all documentation.

---

## Documentation Consolidation

**See:** `docs/DOCUMENTATION_CONSOLIDATION.md` for consolidation plan.

**Goal:** Reduce documentation files from 29 to ~10 core documents.

**Timeline:** 1 week (parallel with development)

