# Lab VM Architecture

## Overview

This document defines the VM architecture for the Clarion lab environment, designed to test all components of the system including Backend, UI, Native NetFlow Collector, Edge Agents, Active Directory, and Cisco ISE.

## VM Requirements

### Current Configuration: 5 VMs (ISE TBD)

| VM # | Name | Role | Components | IP Address | Notes |
|------|------|------|------------|------------|-------|
| 1 | `clarion-server` | Clarion Server | Backend + UI + Native NetFlow Collector | 192.168.110.11 | Main server running all Clarion services |
| 2 | `edge-agent-1` | Edge Agent + NetFlow Sim | Edge Agent + NetFlow Traffic Generator | 192.168.110.12 | Simulates switch with NetFlow v5/v9/IPFIX |
| 3 | `edge-agent-2` | Edge Agent + NetFlow Sim | Edge Agent + NetFlow Traffic Generator | 192.168.110.13 | Additional edge agent for load testing |
| 4 | `edge-agent-3` | Edge Agent + NetFlow Sim | Edge Agent + NetFlow Traffic Generator | 192.168.110.14 | Additional edge agent for load testing |
| 5 | `dc-server` | Active Directory | Windows Server 2019/2022 or Samba AD | 192.168.110.10 | Active Directory Domain Controller |
| 6 | `ise-server` | Cisco ISE | Cisco ISE 3.x (VMware) | TBD | **Not yet built** - Identity Services Engine (requires 16GB+ RAM, 32GB recommended) |

### Alternative: Consolidated Configuration (3 VMs)

For resource-constrained environments, you can consolidate:

| VM # | Name | Role | Components | IP Address |
|------|------|------|------------|------------|
| 1 | `clarion-server` | Clarion Server | Backend + UI + Native NetFlow Collector | 192.168.110.11 |
| 2 | `edge-agent-1` | Edge Agent + NetFlow Sim | Edge Agent + NetFlow Traffic Generator | 192.168.110.12 |
| 3 | `dc-server` | Active Directory | Windows Server or Samba AD | 192.168.110.10 |

**Note:** With consolidated config, you lose ability to test multi-edge-agent scenarios and load distribution.

## VM Specifications

### clarion-server (VM1)

**Purpose:** Central Clarion server running backend API, frontend UI, and native NetFlow collector.

**Components:**
- Backend API (FastAPI) on port 8000
- Frontend UI (React/Vite) on port 5173 (dev) or 80/443 (prod)
- Native NetFlow Collector on ports:
  - 2055/UDP (NetFlow v5/v9)
  - 4739/UDP (IPFIX)
  - 8081/TCP (Health/Metrics)

**Resources:**
- CPU: 4 vCPU (minimum 2)
- RAM: 8GB (minimum 4GB)
- Disk: 50GB (for database and logs)
- OS: Ubuntu 22.04 LTS or similar

**Services:**
- PostgreSQL + TimescaleDB (when migrated)
- SQLite (current, interim)
- Neo4j (when implemented)

**Network:**
- Interface: `eth0` or `ens33`
- IP: `192.168.110.11/24`
- Gateway: `192.168.110.1` (TBD - confirm gateway)
- DNS: `192.168.110.10` (DC server)

### edge-agent-* (VM2-VM4)

**Purpose:** Simulate edge switches with NetFlow generation and edge agent processing.

**Components:**
- Edge Agent (Clarion Edge) - processes flows and sends sketches
- NetFlow Traffic Generator - simulates NetFlow v5/v9/IPFIX packets
- Network namespaces (h1-h24) for traffic generation
- Softflowd/nfcapd (optional, for real NetFlow generation)

**Resources:**
- CPU: 4 vCPU (minimum 2)
- RAM: 4GB (minimum 2GB)
- Disk: 30GB
- OS: Ubuntu 22.04 LTS

**Network:**
- Interface: `eth0` or `ens33`
- IP: `192.168.110.12/13/14/24` (one per VM)
- Gateway: `192.168.110.1` (TBD - confirm gateway)
- Internal subnets: `10.10.0.0/24`, `10.10.1.0/24`, `10.10.2.0/24`
- DNS: `192.168.110.10` (DC server)

**NetFlow Simulation:**
- Simulates NetFlow v5, v9, and IPFIX packets
- Sends to `clarion-server:2055` (NetFlow) or `clarion-server:4739` (IPFIX)
- Can generate realistic traffic patterns matching IMIX

### dc-server (VM5)

**Purpose:** Active Directory Domain Controller for user/group management and identity resolution.

**Components:**
- Windows Server 2019/2022 AD DS, or
- Samba 4.x Active Directory (Linux alternative)
- DNS Server (integrated with AD)
- LDAP/389 Directory Server

**Resources:**
- CPU: 2 vCPU (minimum)
- RAM: 4GB (minimum, 8GB recommended for Windows)
- Disk: 40GB
- OS: Windows Server 2019/2022 or Ubuntu 22.04 (Samba)

**Network:**
- Interface: `eth0` or `ens33`
- IP: `192.168.110.10/24`
- Gateway: `192.168.110.1` (TBD - confirm gateway)
- DNS: Self (127.0.0.1) or forwarder

**Domain:**
- Domain: `lab.clarion.local`
- Domain NetBIOS: `LAB`
- Admin User: `Administrator` / `admin`
- Test Users: Various test users (see setup script)

**Services:**
- Active Directory Domain Services
- DNS Server
- LDAP (389/tcp)
- Kerberos (88/tcp, 88/udp)
- LDAP/GC (3268/tcp, 3269/tcp)

### ise-server (VM6) - **NOT YET BUILT**

**Purpose:** Cisco Identity Services Engine for network access control and TrustSec/SGT assignment.

**Components:**
- Cisco ISE 3.x (PAN or PSN node)
- pxGrid services
- RADIUS server
- TACACS+ server (optional)

**Resources:**
- CPU: 4 vCPU (minimum, 8 recommended)
- RAM: **16GB minimum (Cisco requirement), 32GB recommended for production workloads**
- Disk: 250GB (Cisco minimum requirement)
- OS: Cisco ISE (based on RHEL)

**Network:**
- Interface: `eth0` or `ens33`
- IP: `TBD` (suggest 192.168.110.15 or similar)
- Gateway: `192.168.110.1` (TBD - confirm gateway)
- DNS: `192.168.110.10` (DC server)

**Services:**
- RADIUS (1812/udp, 1813/udp)
- pxGrid (5222/tcp, 8910/tcp)
- Admin Portal (HTTPS 443/tcp)
- Monitoring Portal (HTTPS 443/tcp)

**Integration:**
- AD Integration: Joins to `lab.clarion.local` domain
- Device Registration: Switches and endpoints
- Policy: TrustSec/SGT assignment policies

**Note:** ISE requires significant resources. Cisco's minimum is 16GB RAM, but 32GB is recommended for optimal performance, especially with multiple nodes or high session volumes.

## Network Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Lab Network (192.168.110.0/24)          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐      ┌─────────────────┐                 │
│  │ clarion-server  │      │   dc-server     │                 │
│  │ 110.11          │      │   110.10        │                 │
│  │                 │      │                 │                 │
│  │ • Backend       │      │ • AD DS         │                 │
│  │ • UI            │      │ • DNS           │                 │
│  │ • Native        │      │ • LDAP          │                 │
│  │   Collector     │      │                 │                 │
│  └─────────────────┘      └─────────────────┘                 │
│         │                         │                            │
│         │                         │                            │
│  ┌──────┴─────────────────────────┴──────┐                    │
│  │         Network (192.168.110.0/24)    │                    │
│  └──────┬─────────────────────────┬──────┘                    │
│         │                         │                            │
│  ┌──────▼──────┐  ┌──────────────▼──────┐  ┌──────────────┐ │
│  │edge-agent-1 │  │   edge-agent-2      │  │ise-server    │ │
│  │  110.12     │  │     110.13          │  │   TBD        │ │
│  │             │  │                     │  │  (Not built)  │ │
│  │ • Agent     │  │ • Agent             │  │ • ISE        │ │
│  │ • NetFlow   │  │ • NetFlow           │  │ • pxGrid     │ │
│  │   Sim       │  │   Sim               │  │ • RADIUS     │ │
│  └─────────────┘  └─────────────────────┘  └──────────────┘ │
│                                                                 │
│  ┌─────────────────┐                                           │
│  │ edge-agent-3    │                                           │
│  │   110.14        │                                           │
│  │                 │                                           │
│  │ • Agent         │                                           │
│  │ • NetFlow Sim   │                                           │
│  └─────────────────┘                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Traffic Flow:
- Edge Agents → NetFlow → clarion-server:2055 (Native Collector)
- Edge Agents → Sketches → clarion-server:8000/api/edge/sketches
- ISE → pxGrid → clarion-server (future integration)
- AD → LDAP → clarion-server (future integration)
```

## Data Flow

### NetFlow Collection
```
Switches/Simulators
  ↓ (NetFlow v5/v9/IPFIX UDP)
clarion-server (192.168.110.11):2055 (Native Collector)
  ↓ (HTTP POST)
clarion-server:8000/api/netflow/netflow
  ↓
Database (SQLite → PostgreSQL + TimescaleDB)
```

### Edge Agent Collection
```
Edge Agents (edge-agent-*: 192.168.110.12-14)
  ↓ (HTTP POST sketches)
clarion-server:8000/api/edge/sketches
  ↓
Database
```

### Identity Resolution (Future)
```
DC Server (dc-server: 192.168.110.10)
  ↓ (LDAP queries)
clarion-server
  ↓
Identity Resolver
  ↓
Enriched Sketches
```

### TrustSec Integration (Future)
```
ISE Server (ise-server: TBD)
  ↓ (pxGrid)
clarion-server
  ↓
SGT Assignment
  ↓
Policy Matrix
```

## Setup Order

1. **dc-server** (192.168.110.10) - Setup AD first (DNS dependency)
2. **clarion-server** (192.168.110.11) - Setup Clarion services
3. **edge-agent-*** (192.168.110.12-14) - Setup edge agents and NetFlow simulators
4. **ise-server** (TBD) - Join ISE to AD domain (not yet built)

## DNS Configuration

All VMs should use `dc-server` (192.168.110.10) as their primary DNS server:
- Forward lookups: `clarion-server.lab.clarion.local` → 192.168.110.11
- Reverse lookups: 192.168.110.11 → `clarion-server.lab.clarion.local`
- AD domain: `lab.clarion.local`

## Testing Scenarios

### Scenario 1: Native NetFlow Collection
- **Source:** edge-agent-* (192.168.110.12-14) (NetFlow simulators)
- **Destination:** clarion-server (192.168.110.11):2055 (Native Collector)
- **Format:** NetFlow v5, v9, IPFIX
- **Validation:** Check `/api/netflow/netflow` endpoint

### Scenario 2: Edge Agent Collection
- **Source:** edge-agent-* (192.168.110.12-14) (Edge agents)
- **Destination:** clarion-server (192.168.110.11):8000/api/edge/sketches
- **Format:** JSON sketches
- **Validation:** Check `/api/edge/sketches/stats` endpoint

### Scenario 3: Identity Resolution
- **Source:** DC Server (192.168.110.10) (LDAP)
- **Integration:** clarion-server Identity Resolver
- **Test:** IP → User → AD Groups mapping
- **Validation:** Check enriched sketches with identity context

### Scenario 4: ISE Integration (Future - ISE not yet built)
- **Source:** ISE Server (TBD) (pxGrid)
- **Integration:** clarion-server pxGrid client
- **Test:** Session data, SGT assignments
- **Validation:** Check TrustSec policy matrix

### Scenario 5: Combined Workflow
- NetFlow flows → Native Collector
- Edge sketches → Agent Collector
- AD users → Identity Resolution
- ISE sessions → TrustSec SGTs (when ISE is built)
- All integrated → Policy recommendations

## Resource Planning

### Current Setup (5 VMs - ISE TBD)
- Total CPU: 16 vCPU
- Total RAM: 28GB (without ISE)
- Total Disk: 370GB (without ISE)
- Suitable for: Basic functionality testing, multi-agent testing

### With ISE (6 VMs - Recommended)
- Total CPU: 20-24 vCPU
- Total RAM: 44-60GB (16GB ISE minimum, 32GB recommended)
- Total Disk: 620GB (with ISE's 250GB requirement)
- Suitable for: Full integration testing, TrustSec testing

**ISE Memory Note:** Cisco ISE requires 16GB minimum, but 32GB is strongly recommended for optimal performance, especially with multiple nodes, high session volumes, or when running Policy Administration Node (PAN) and Policy Services Node (PSN) on the same VM.

## Next Steps

1. Create VM provisioning scripts (Vagrant, Ansible, or manual)
2. Setup AD server with test users/groups
3. Setup ISE server and join to AD
4. Configure NetFlow simulators on edge-agent VMs
5. Update lab setup scripts for new architecture
6. Create integration test suite

