# Clarion - Project Plan

## 📋 Overview

**Project:** Clarion - TrustSec Policy Copilot  
**Goal:** Mine network behavior to recommend SGT taxonomies and generate SGACL policies  
**Start Date:** December 2024  
**Status:** 🟡 In Progress - Architecture Complete, MVP 1 Starting

---

## 🎯 Project Phases

### Phase 0: Foundation ✅ Complete
- [x] Project vision and scope defined
- [x] Synthetic dataset acquired (291K records)
- [x] Architecture designed (edge/collector/backend)
- [x] Project structure created
- [x] Documentation framework (DESIGN.md)
- [x] NetFlow lab environment (VM simulation)

### Phase 1: MVP - Core Analytics (Current)

#### MVP 1.1: Data Ingestion ⬜ In Progress
| Task | Status | Owner | Notes |
|------|--------|-------|-------|
| Load all CSV files into DataFrames | ⬜ Todo | | `src/clarion/ingest/` |
| Validate data quality | ⬜ Todo | | Missing fields, duplicates |
| Create unified flow schema | ⬜ Todo | | Normalize across sources |
| Build test fixtures | ⬜ Todo | | Sample data for unit tests |

#### MVP 1.2: Identity Resolution ⬜ Pending
| Task | Status | Owner | Notes |
|------|--------|-------|-------|
| IP → Endpoint mapping | ⬜ Todo | | Time-bounded join |
| Endpoint → User mapping | ⬜ Todo | | Via ISE sessions |
| User → AD Groups mapping | ⬜ Todo | | Group membership |
| Destination → Service mapping | ⬜ Todo | | Service catalog lookup |
| Confidence scoring | ⬜ Todo | | Track join quality |

#### MVP 1.3: Graph Building ⬜ Pending
| Task | Status | Owner | Notes |
|------|--------|-------|-------|
| NetworkX graph creation | ⬜ Todo | | Nodes + edges |
| Edge enrichment | ⬜ Todo | | Add identity context |
| Graph serialization | ⬜ Todo | | JSON export |
| Basic queries | ⬜ Todo | | "Who talks to whom" |

#### MVP 1.4: CLI Tools ⬜ Pending
| Task | Status | Owner | Notes |
|------|--------|-------|-------|
| `clarion load` command | ⬜ Todo | | Load data |
| `clarion graph` command | ⬜ Todo | | Build/query graph |
| `clarion stats` command | ⬜ Todo | | Summary statistics |

### Phase 2: SGT Recommendation Engine ⬜ Pending

#### MVP 2.1: Behavior Analysis
| Task | Status | Owner | Notes |
|------|--------|-------|-------|
| Extract behavior features | ⬜ Todo | | Ports, protocols, destinations |
| Identify servers vs clients | ⬜ Todo | | Traffic direction analysis |
| Group by AD membership | ⬜ Todo | | Leverage existing groups |
| Group by ISE profile | ⬜ Todo | | Device type clustering |

#### MVP 2.2: SGT Recommendation
| Task | Status | Owner | Notes |
|------|--------|-------|-------|
| Propose initial taxonomy | ⬜ Todo | | 6-12 SGTs |
| Assign endpoints to SGTs | ⬜ Todo | | Confidence scores |
| Generate justifications | ⬜ Todo | | "Why this SGT?" |
| Coverage analysis | ⬜ Todo | | % traffic covered |

### Phase 3: Policy Matrix ⬜ Pending

#### MVP 3.1: Matrix Builder
| Task | Status | Owner | Notes |
|------|--------|-------|-------|
| Build SGT→SGT matrix | ⬜ Todo | | From enriched edges |
| Aggregate traffic stats | ⬜ Todo | | Ports, bytes, flows |
| Identify critical paths | ⬜ Todo | | High-volume flows |

#### MVP 3.2: SGACL Generator
| Task | Status | Owner | Notes |
|------|--------|-------|-------|
| Generate allow-list rules | ⬜ Todo | | From observed traffic |
| Generate deny rules | ⬜ Todo | | For unobserved |
| Impact simulation | ⬜ Todo | | "What would break?" |
| ISE export format | ⬜ Todo | | Ready for import |

### Phase 4: API & UI ⬜ Pending

#### MVP 4.1: REST API
| Task | Status | Owner | Notes |
|------|--------|-------|-------|
| FastAPI skeleton | ⬜ Todo | | Basic structure |
| Graph endpoints | ⬜ Todo | | Nodes, edges, neighbors |
| Policy endpoints | ⬜ Todo | | Matrix, SGACLs |
| Export endpoints | ⬜ Todo | | ISE format |

#### MVP 4.2: Web Dashboard
| Task | Status | Owner | Notes |
|------|--------|-------|-------|
| Streamlit prototype | ⬜ Todo | | Rapid iteration |
| Graph visualization | ⬜ Todo | | D3.js or similar |
| Matrix heatmap | ⬜ Todo | | SGT interaction view |

### Phase 5: Edge & Collector ⬜ Future

#### Edge Container (App Hosting)
| Task | Status | Owner | Notes |
|------|--------|-------|-------|
| Flow listener (UDP 2055) | ⬜ Todo | | NetFlow receiver |
| Local graph builder | ⬜ Todo | | Per-switch graph |
| Backend sync | ⬜ Todo | | gRPC/REST client |
| IOx packaging | ⬜ Todo | | Cisco App Hosting |

#### Collector Service
| Task | Status | Owner | Notes |
|------|--------|-------|-------|
| NetFlow v5/v9 parser | ⬜ Todo | | For legacy switches |
| IPFIX parser | ⬜ Todo | | Modern standard |
| sFlow parser | ⬜ Todo | | Packet sampling |
| Multi-switch aggregation | ⬜ Todo | | Central collector |

### Phase 6: Integrations ⬜ Future

#### Identity Connectors
| Task | Status | Owner | Notes |
|------|--------|-------|-------|
| ISE pxGrid connector | ⬜ Todo | | Real-time sessions |
| AD LDAP connector | ⬜ Todo | | Users, groups |
| CMDB connector | ⬜ Todo | | ServiceNow REST |
| DHCP connector | ⬜ Todo | | Infoblox/MS DHCP |

#### Policy Export
| Task | Status | Owner | Notes |
|------|--------|-------|-------|
| ISE ERS API push | ⬜ Todo | | Direct policy update |
| DNA Center integration | ⬜ Todo | | Fabric deployment |
| Report generation | ⬜ Todo | | PDF/Excel export |

---

## 📊 Progress Summary

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 0: Foundation | ✅ Complete | 100% |
| Phase 1: MVP Core | 🟡 In Progress | 5% |
| Phase 2: SGT Recommender | ⬜ Pending | 0% |
| Phase 3: Policy Matrix | ⬜ Pending | 0% |
| Phase 4: API & UI | ⬜ Pending | 0% |
| Phase 5: Edge/Collector | ⬜ Future | 0% |
| Phase 6: Integrations | ⬜ Future | 0% |

---

## 🏃 Current Sprint

**Sprint 1: Data Ingestion & Identity Resolution**

**Goals:**
1. Load all synthetic CSV files
2. Implement identity resolution (flow → user/device)
3. Build initial communication graph
4. Create basic CLI

**Tasks:**
- [ ] Complete data loaders for all 13 CSV files
- [ ] Implement IP → endpoint → user join logic
- [ ] Build NetworkX graph with enriched edges
- [ ] Create `clarion load` CLI command
- [ ] Write unit tests for identity resolution

---

## 🗓️ Timeline (Estimated)

| Phase | Duration | Target |
|-------|----------|--------|
| MVP 1: Core Analytics | 2 weeks | Jan 2025 |
| MVP 2: SGT Recommender | 2 weeks | Jan 2025 |
| MVP 3: Policy Matrix | 2 weeks | Feb 2025 |
| MVP 4: API & UI | 2 weeks | Feb 2025 |
| Edge/Collector | 4 weeks | Mar 2025 |
| Integrations | 4 weeks | Apr 2025 |

---

## 📝 Notes

### Decisions Made
- Use synthetic data first, then transition to live data
- Start with NetworkX (in-memory), scale to Neo4j later
- Edge containers for Catalyst 9K, collector for legacy
- pxGrid 2.0 (WebSocket) for ISE integration

### Risks
- ISE pxGrid access may require lab setup
- AD LDAP connectivity requires proper credentials
- Edge container sizing for App Hosting limits

### Dependencies
- Synthetic dataset ✅ Available
- Lab VMs ✅ Working
- ISE for pxGrid testing ⬜ Needed
- AD for LDAP testing ⬜ Needed

---

*Last Updated: December 2024*

