# Clarion Prioritized Development Roadmap

## Overview

This document outlines the prioritized development plan for Clarion, focusing on building a robust, production-ready system with comprehensive testing and validation.

---

## Development Priorities

### Priority 1: Backend & Categorization Engine ⭐ **CURRENT FOCUS**

**Goal:** Build a sophisticated categorization engine with AI integration, incremental clustering, and comprehensive data processing.

#### 1.1 Categorization Engine Core

**Status:** ⚠️ In Progress

**Tasks:**
- [ ] Incremental clustering (fast path for new endpoints)
- [ ] First-seen tracking (detect new devices/users)
- [ ] Identity-aware clustering (handle late-arriving identity data)
- [ ] SGT lifecycle management (stable SGTs, dynamic membership)
- [ ] Cluster stability tracking
- [ ] Database schema updates (first_seen, SGT registry, centroids)
- [ ] **Enhanced confidence scoring system** (all decisions have confidence scores)
- [ ] **Enhanced explainability system** (clear "why" explanations for all decisions)
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

**Tasks:**
- [ ] AI categorization agent architecture
- [ ] LLM backend abstraction (Ollama, OpenAI, Anthropic)
- [ ] Local model support (Llama, Mistral via Ollama)
- [ ] Cloud model support (OpenAI, Anthropic)
- [ ] Optional RAG (database context)
- [ ] Fallback to rule-based labeling
- [ ] Configuration management
- [ ] **AI explainability** (show AI reasoning to users)
- [ ] **AI vs rule-based comparison** (show both options when they differ)
- [ ] **AI enhancement framework** (AI augments, doesn't replace rule-based)

**Files:**
- `src/clarion/clustering/ai_agent.py`
- `src/clarion/clustering/llm_backend.py`
- `src/clarion/clustering/rag_context.py` (optional)
- `src/clarion/clustering/ai_enhancer.py` (AI augmentation framework)

**Dependencies:**
- Verify architecture can support local models before implementation
- Ensure optional nature (can disable AI completely)
- AI must enhance, not replace rule-based logic

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
- [ ] Security Hardening (rate limiting, input validation, secrets management, SSL/TLS)
- [ ] PostgreSQL Migration (production database, migration scripts)
- [ ] Monitoring & Observability (Prometheus metrics, centralized logging, alerting, Grafana)
- [ ] High Availability (multi-instance deployment, load balancing, failover)
- [ ] CI/CD Pipeline (automated builds, deployment automation)
- [ ] Database Backup/Recovery (backup procedures, disaster recovery)

**Priority:** 🔴 CRITICAL  
**Timeline:** 10-14 weeks (Phase 1: 4-6 weeks, Phase 2: 4-6 weeks, Phase 3: 2-4 weeks)  
**Note:** See `docs/PRODUCTION_READINESS.md` for detailed requirements and prioritization.

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

### Q1 2025 (Weeks 1-12)

**Weeks 1-4: Backend Core**
- Incremental clustering
- First-seen tracking
- SGT lifecycle management
- Database schema updates
- Enhanced confidence scoring system
- Enhanced explainability system
- Quality assurance framework
- Edge case handling

**Weeks 5-6: AI Integration**
- Architecture validation
- LLM backend implementation
- Local model support (Ollama)
- Optional RAG
- AI explainability framework
- AI enhancement system (augments rule-based)
- Override tracking and feedback loop

**Weeks 7-10: Test Scenarios**
- Ground truth dataset creation
- Validation framework
- Testing across company types
- Accuracy metrics

**Weeks 11-12: UI Enhancement**
- Real-time updates
- Enhanced visualizations
- AI controls/feedback

### Q2 2025 (Weeks 13-24)

**Weeks 13-14: Collectors & Agents**
- NetFlow collector hardening
- Edge agent optimization
- Production deployment guides

**Weeks 15-18: Data Layer**
- PostgreSQL migration
- Neo4j integration

**Weeks 19-22: Multi-Source Ingestion & User Database**
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
- [ ] AD integration (user details, group memberships, user database enrichment)
- [ ] User-device association resolution engine

**Weeks 23-24: Integration & Testing**
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

- [ ] Incremental clustering works (<100ms per endpoint)
- [ ] AI integration optional and functional
- [ ] SGT lifecycle stable (>95% stability)
- [ ] First-seen tracking accurate
- [ ] All decisions have confidence scores (0.0-1.0)
- [ ] All decisions have clear explanations
- [ ] Quality framework operational (validation, monitoring)
- [ ] Edge cases handled gracefully
- [ ] Override tracking and feedback loop functional

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

