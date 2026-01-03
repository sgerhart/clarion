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

## Development Priorities

### Priority 0.5: HashiCorp Vault Integration 🔐 **CRITICAL - Must Complete Before AI/AD**

**Goal:** Implement secure secrets management using HashiCorp Vault before implementing AI, AD, or other integrations that require credentials.

**Status:** ❌ Not Started - Critical Security Requirement

**Why This Priority:**
- All sensitive data (passwords, API keys, certificates, tokens) must be stored securely
- Current implementation stores secrets in SQLite database (not production-ready)
- AI integration will require API keys (OpenAI, Anthropic, etc.)
- AD integration will require LDAP credentials
- ISE pxGrid already stores passwords and certificates in database (needs migration)
- Must be completed before any production deployment

**Tasks:**

**Phase 1: Vault Infrastructure (Week 1)**
- [ ] Vault deployment (Docker container, Kubernetes, or standalone)
- [ ] Vault initialization and unsealing
- [ ] Vault authentication setup (AppRole for services, token for admin)
- [ ] Vault policies creation (read/write access for different services)
- [ ] Vault secrets engine configuration (KV v2 for secrets, PKI for certificates)

**Phase 2: Vault Client Integration (Week 2)**
- [ ] Python hvac library integration
- [ ] Vault client wrapper class (`src/clarion/secrets/vault_client.py`)
- [ ] Secret retrieval methods (get, list, create, update, delete)
- [ ] Certificate storage methods (store cert, key, CA cert)
- [ ] Connection pooling and retry logic
- [ ] Error handling and fallback mechanisms
- [ ] Configuration management (Vault address, auth method, paths)

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
**Timeline:** 5 weeks  
**Blocking:** AI integration, AD integration, production deployment  
**Note:** This must be completed before implementing AI (which needs API keys) or AD (which needs LDAP credentials). All existing secrets in the database must be migrated to Vault.

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
- Verify architecture can support local models before implementation
- Ensure optional nature (can disable AI completely)
- AI must enhance, not replace rule-based logic
- LangChain for orchestration
- LlamaIndex for RAG (optional)
- Vector database (Chroma/Qdrant) for RAG (optional)

**Architecture:** See `docs/AI_ENHANCED_ARCHITECTURE.md` for comprehensive design

**⚠️ BLOCKED:** Cannot start AI implementation until Vault integration is complete (Priority 0.5)

#### 1.3 Streaming Data Processing

**Status:** 📋 Planned

**Tasks:**
- [ ] Real-time flow ingestion
- [ ] Incremental sketch updates
- [ ] Streaming clustering triggers
- [ ] Backpressure handling

**Files:**
- `src/clarion/ingest/streaming.py`
- Update `src/clarion/ingest/sketch_builder.py`

**Timeline:** 4-6 weeks

#### 1.4 Behavioral Anomaly Detection (Zero Trust Continuous Verification)

**Status:** 📋 Planned

**Goal:** Detect behavioral anomalies and trigger security responses (SGT quarantining) for Zero Trust continuous verification.

**Tasks:**
- [ ] Baseline behavioral sketches (establish "normal" behavior for each SGT)
- [ ] Anomaly detection engine (detect deviations from normal behavior)
- [ ] Example: Detect if "Printer" SGT starts talking to "Database" SGT over SSH
- [ ] SGT Quarantining integration (trigger ISE quarantine events for anomalies)
- [ ] Continuous verification (ongoing monitoring of SGT behavior)
- [ ] Anomaly scoring (confidence scores for detected anomalies)
- [ ] False positive reduction (learn from user feedback on anomalies)
- [ ] Alerting and notification (notify security team of detected anomalies)

**Files:**
- `src/clarion/security/anomaly_detector.py`
- `src/clarion/security/baseline_builder.py`
- `src/clarion/integration/ise_quarantine.py`

**Priority:** 🔴 High (Critical for Zero Trust security)  
**Timeline:** 4-6 weeks  
**Dependencies:** Baseline behavioral sketches, ISE integration, anomaly detection algorithms

---

### Priority 2: Test Scenarios & Validation 🧪

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

---

### Priority 3: Robust UI Enhancement 🎨

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
- [ ] Performance optimization
- [ ] Mobile responsiveness (if needed)

**Timeline:** 4-6 weeks

---

### Priority 4: Native NetFlow Collectors 📡

**Status:** ✅ Mostly Complete

**Current State:**
- NetFlow v5 fully implemented
- NetFlow v9/IPFIX template parsing implemented
- Health/metrics endpoints
- Docker support

**Remaining Tasks:**
- [ ] Production hardening
- [ ] Performance optimization
- [ ] Enhanced monitoring
- [ ] Documentation

**Timeline:** 1-2 weeks

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

### Priority 5: Edge Agent 🔄

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

---

## Development Timeline

### Q1 2025 (Weeks 1-17)

**Weeks 1-5: HashiCorp Vault Integration** 🔐 **CRITICAL - MUST COMPLETE FIRST**
- Vault deployment and infrastructure
- Vault client integration
- Secrets migration from database to Vault
- Application integration
- Secret rotation and management

**Weeks 6-9: Backend Core** ✅ **COMPLETED**
- ✅ Incremental clustering - `IncrementalClusterer` implemented
- ✅ First-seen tracking - Database fields and methods implemented
- ✅ SGT lifecycle management - `SGTLifecycleManager` implemented
- ✅ Database schema updates - All tables (sgt_registry, sgt_membership, cluster_centroids, etc.) implemented
- ✅ Enhanced confidence scoring system - `ConfidenceScorer` implemented
- ✅ Enhanced explainability system - `explanation.py` implemented
- [ ] Quality assurance framework - **Remaining**
- [ ] Edge case handling - **Remaining**

**Weeks 10-11: AI Integration** (⚠️ Requires Vault for API keys)
- Architecture validation
- LLM backend implementation
- Local model support (Ollama)
- Optional RAG
- AI explainability framework
- AI enhancement system (augments rule-based)
- Override tracking and feedback loop

**Weeks 12-15: Test Scenarios**
- Ground truth dataset creation
- Validation framework
- Testing across company types
- Accuracy metrics

**Weeks 16-17: UI Enhancement**
- Real-time updates
- Enhanced visualizations
- AI controls/feedback

### Q2 2025 (Weeks 18-29)

**Weeks 18-19: Collectors & Agents**
- NetFlow collector hardening
- Edge agent optimization
- Production deployment guides

**Weeks 20-23: Data Layer**
- PostgreSQL migration
- Neo4j integration

**Weeks 24-27: Multi-Source Ingestion & User Database** (⚠️ AD integration requires Vault for credentials)
- ✅ User database schema creation (completed)
- ✅ User management (CRUD operations, API endpoints, UI)
- ✅ User clustering (AD group-based and traffic-based clustering)
- ✅ User SGT assignments and recommendations (user SGT management, traffic analysis)
- ✅ User traffic aggregation (user traffic patterns, user-to-user traffic)
- ✅ ISE ERS API integration (brownfield support: sync existing ISE configuration)
- ✅ ISE configuration cache (store existing SGTs, profiles, policies)
- ✅ Policy recommendation engine with brownfield support (check existing SGTs)
- ✅ Containerization (Docker, docker-compose for API, pxGrid, frontend services)
- [ ] ISE pxGrid WebSocket/STOMP integration (full real-time event reception - architecture in place)
- [x] pxGrid certificate-based authentication (infrastructure implemented)
- [ ] pxGrid certificate-based authentication testing (end-to-end validation needed)
- [ ] **AD connector implementation** (LDAP connector, user/group queries, user database enrichment, AD group memberships storage, scheduled synchronization)
- [ ] **🔍 Advanced AD Integration Architecture Investigation** (LDAP/LDAPS + DirSync for near-real-time AD mirror, WEF→WEC for Security log streaming, event correlation using stable identifiers)
- [ ] **Connector information tabs** (Summary/Overview tabs for ISE, AD, and other connectors explaining purpose, capabilities, and usage)
- [ ] User-device association resolution engine
- [ ] **Multi-vendor connector framework** (pluggable adapters for various vendors)
- [ ] **Cloud platform connectors** (AWS, Azure, GCP - flow logs, security groups, IAM)
- [ ] **Additional network vendor connectors** (Aruba ClearPass, Palo Alto, Fortinet)
- [ ] **Multi-environment support** (Campus, Branch, WAN, Cloud, Data Centers)
- [ ] **Policy abstraction layer** (vendor-agnostic policy representation)
- [ ] **Policy translation engine** (convert unified policy to vendor-specific formats)

**Weeks 28-29: Integration & Testing**
- End-to-end testing
- Performance optimization
- Bug fixes

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

