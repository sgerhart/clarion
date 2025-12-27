# Clarion Project Roadmap

## Current Status: MVP Complete ✅

**Completed Phases:** 1-5 (Core MVP)  
**In Progress:** Phase 6 (Data Layer), Phase 7 (Topology)  
**Planned:** Phase 8 (Multi-Source), Phase 9 (Correlation)

---

## 🎯 Immediate Priorities (Next 3 Months)

### Priority 1: Data Layer Migration (Phase 6)
**Timeline:** 4-6 weeks

**Tasks:**
- [ ] Set up PostgreSQL + TimescaleDB development environment
- [ ] Create migration scripts (SQLite → PostgreSQL)
- [ ] Implement TimescaleDB hypertables for flow data
- [ ] Deploy Neo4j for graph database
- [ ] Design graph schema (nodes, edges, properties)
- [ ] Implement edge graph merging logic
- [ ] Update storage layer code
- [ ] Test with synthetic data

**Dependencies:** None  
**Blockers:** None

---

### Priority 2: Topology Management (Phase 7)
**Timeline:** 3-4 weeks

**Tasks:**
- [ ] Create topology management API endpoints
  - [ ] Locations CRUD (Campus, Branch, Remote Site)
  - [ ] Address spaces CRUD
  - [ ] Subnets CRUD
  - [ ] Switches CRUD
- [ ] Implement IP-to-subnet resolution
- [ ] Build topology builder UI (React)
  - [ ] Location hierarchy tree
  - [ ] Address space configuration
  - [ ] Subnet mapping interface
  - [ ] Switch registration
- [ ] Implement flow location correlation
- [ ] Add location context to flow queries

**Dependencies:** Phase 6 (database migration)  
**Blockers:** None

---

### Priority 3: NetFlow Collector (Phase 8.1) ✅ In Progress
**Timeline:** 3-4 weeks
**Status:** Core implementation complete, v9/IPFIX template parsing pending

**Tasks:**
- [x] Implement NetFlow v5 parser ✅
- [ ] Implement NetFlow v9 template handling (stubbed, needs template parsing)
- [ ] Implement IPFIX parser (stubbed, needs template parsing)
- [ ] Extract SGT fields (IPFIX IE 411/412) (pending template parsing)
- [x] Field mapping to unified schema ✅
- [x] Native NetFlow collector (UDP listener) ✅
- [x] Agent collector (HTTP endpoint) ✅
- [x] Basic integration with backend API ✅
- [ ] Integration with TimescaleDB (pending Phase 6)
- [ ] Testing with sample NetFlow data

**Dependencies:** Phase 6 (TimescaleDB) for production integration  
**Blockers:** None
**Notes:** See `collector/README.md` for usage instructions

---

## 📅 6-Month Roadmap

### Q1 2025: Foundation & Topology

**Month 1-2: Data Layer**
- PostgreSQL + TimescaleDB migration
- Neo4j graph database integration
- Edge graph merging

**Month 2-3: Topology**
- Topology management API
- Topology builder UI
- Flow location correlation

**Month 3: NetFlow Collector**
- Multi-version NetFlow support
- SGT field extraction
- Integration testing

---

### Q2 2025: Multi-Source Ingestion

**Month 4: ISE pxGrid**
- pxGrid client setup
- Session/endpoint subscribers
- SGT assignment tracking

**Month 5: AD Connector**
- LDAP integration
- User/group sync
- Device mapping

**Month 6: IoT Connectors**
- Connector framework
- MediGate connector
- ClearPass connector

---

### Q3 2025: Correlation & Production

**Month 7-8: Correlation Engine**
- Identity resolution
- Graph merging
- Policy correlation

**Month 9: Production Readiness**
- Kubernetes deployment
- Monitoring & alerting
- Documentation

---

## 🎯 Success Criteria

### Phase 6: Data Layer
- [ ] PostgreSQL handles 100M+ flows/hour
- [ ] Neo4j merges edge graphs successfully
- [ ] Query performance < 1s for 24h window

### Phase 7: Topology
- [ ] Customer can build complete topology
- [ ] All flows enriched with location
- [ ] Location-based queries work

### Phase 8: Multi-Source
- [ ] NetFlow v5/v9/IPFIX all supported
- [ ] SGT fields extracted correctly
- [ ] pxGrid real-time updates working
- [ ] AD sync completes in < 5 minutes

### Phase 9: Correlation
- [ ] Identity resolution accuracy > 95%
- [ ] Graph merging handles conflicts
- [ ] Policy correlation produces valid recommendations

---

## 📋 Task Tracking

### Active Tasks
- [ ] PostgreSQL migration script
- [ ] Neo4j graph schema design
- [ ] Topology API endpoints
- [ ] NetFlow v9/IPFIX template parsing

### Blocked Tasks
- None currently

### Completed This Week
- ✅ Topology database schema
- ✅ SGT fields in NetFlow schema
- ✅ Data architecture documentation
- ✅ Topology architecture documentation
- ✅ NetFlow Collector implementation (v5 parser, native collector, agent collector)

---

## 🔄 Weekly Review Process

**Every Monday:**
1. Review previous week's progress
2. Update task status
3. Identify blockers
4. Prioritize next week's tasks

**Every Friday:**
1. Update progress in PROJECT_PLAN.md
2. Commit documentation updates
3. Review and adjust roadmap

---

## 📊 Metrics to Track

- **Data Volume:** Flows/hour, sketches/hour
- **Query Performance:** Average query time
- **Correlation Accuracy:** Identity resolution success rate
- **Topology Coverage:** % of flows with location data
- **API Performance:** Response times, error rates

---

## 🚨 Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| PostgreSQL migration complexity | High | Start with small dataset, test thoroughly |
| Neo4j performance at scale | Medium | Benchmark early, optimize queries |
| NetFlow version compatibility | Medium | Test with multiple versions, handle edge cases |
| pxGrid integration complexity | Medium | Use existing libraries, follow Cisco docs |
| Timeline delays | Medium | Buffer time in estimates, prioritize MVP features |

---

## 📝 Notes

- All new features should maintain backward compatibility
- Database migrations must be reversible
- API changes require versioning
- UI changes should be incremental (don't break existing workflows)


