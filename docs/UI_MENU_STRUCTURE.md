# UI Menu Structure & Navigation

## Current Menu (Baseline)

```
- Dashboard
- Network Flows
- Clusters
- SGT Matrix
- Policy Builder
```

---

## Proposed Complete Menu Structure

### 1. Dashboard
**Purpose:** Overview and quick actions  
**Content:**
- System health summary
- Recent activity feed
- Quick statistics (devices, groups, policies)
- Alerts and notifications
- Quick actions (review recommendations, create policy)

---

### 2. Devices
**Purpose:** Device discovery and management  
**Content:**
- All devices list (with filters)
- Device details (behavior, identity, group assignment)
- Manual device assignment
- Device search and filtering
- Device type classification

---

### 3. Groups
**Purpose:** Group/cluster management  
**Content:**
- All groups (AI-generated + manual)
- Group details (members, SGT assignment, behavioral profile)
- Create/edit/delete groups
- Merge/split groups
- Group override history

---

### 4. Network Flows
**Purpose:** Traffic analysis and visualization  
**Content:**
- Flow visualization (device-to-device)
- Flow metadata (5/9-tuple)
- Flow filtering and search
- Traffic patterns
- Top talkers

---

### 5. Policy
**Purpose:** SGT and SGACL policy management  
**Sub-sections:**
- **SGT Mappings** - View/edit SGT assignments
- **Access Rules (SGACLs)** - Policy rules
- **Policy Matrix** - SGT x SGT communication matrix
- **Policy Builder** - Create/edit policies
- **Impact Analysis** - What traffic would be blocked/allowed

---

### 6. Topology (NEW)
**Purpose:** Network topology and location hierarchy  
**Content:**
- Location hierarchy tree (Campus → Building → IDF)
- Address space management
- Subnet mapping
- Switch registration
- Visual topology map

---

### 7. Data Sources (NEW)
**Purpose:** Monitor and configure data sources  
**Sub-sections:**
- **Edge Agents** - Monitor agents on switches
  - Agent status per switch
  - Agent health metrics
  - Last sync time
  - Sketch statistics
  - Enable/disable agents
- **NetFlow Collectors** - Monitor NetFlow collectors
  - Collector status
  - Flow ingestion rates
  - Collector health
  - Source device mapping
- **Data Source Overview** - Summary of all sources
  - Total flows/hour
  - Data freshness
  - Source status dashboard

---

### 8. Connectors (NEW)
**Purpose:** Configure external system connectors  
**Sub-sections:**
- **ISE pxGrid** - ISE connector configuration
  - Connection settings
  - Authentication/certificates
  - Topic subscriptions (sessions, endpoints)
  - Connection status
  - Test connection
- **Active Directory** - AD connector configuration
  - LDAP connection settings
  - Domain controllers
  - Sync schedule
  - User/group sync status
  - Test connection
- **IoT Connectors** - IoT system connectors
  - MediGate
  - ClearPass
  - Custom connectors

---

### 9. Settings/Configuration (NEW)
**Purpose:** System-wide configuration  
**Sub-sections:**
- **Global Settings**
  - Clustering parameters (min_cluster_size, min_samples)
  - SGT allocation ranges
  - Policy defaults (default action, approval required)
  - Data retention policies
- **Clustering Settings**
  - Algorithm selection
  - Feature weights
  - Labeling thresholds
  - Auto-clustering schedule
- **Policy Settings**
  - Default SGACL behavior
  - Approval workflow
  - Auto-apply settings
  - Impact analysis thresholds
- **System Settings**
  - Timezone
  - Date/time format
  - Logging levels
  - Backup/restore
- **User Management** (if multi-user)
  - Users
  - Roles/permissions
  - Authentication settings

---

### 10. Monitoring (NEW)
**Purpose:** System monitoring and health  
**Sub-sections:**
- **System Health**
  - API health
  - Database status
  - Storage usage
  - Performance metrics
- **Agent Status**
  - All edge agents status
  - Agent uptime
  - Last sync
  - Error logs
- **Data Ingestion**
  - Flow ingestion rates
  - Source status
  - Data quality metrics
- **Clustering Status**
  - Last clustering run
  - Cluster quality metrics
  - Processing time

---

### 11. Audit/Logs (NEW)
**Purpose:** Track changes and system activity  
**Content:**
- **Change Log**
  - All admin overrides (who, what, when)
  - Policy changes
  - Group modifications
  - SGT reassignments
- **System Logs**
  - API requests
  - Errors
  - Warnings
  - Debug information
- **Audit Trail**
  - User actions
  - Configuration changes
  - Policy deployments

---

### 12. Reports/Export (NEW)
**Purpose:** Generate reports and export configurations  
**Content:**
- **Policy Export**
  - ISE ERS format
  - Cisco CLI
  - JSON export
- **Reports**
  - Device inventory
  - Policy compliance
  - Traffic analysis
  - Clustering report
- **Scheduled Reports**
  - Configure automated reports
  - Email delivery

---

## Recommended Menu Organization

### Option 1: Flat Structure (All Top-Level)

```
Dashboard
Devices
Groups
Network Flows
Policy
  ├── SGT Mappings
  ├── Access Rules
  ├── Policy Matrix
  ├── Policy Builder
  └── Impact Analysis
Topology
Data Sources
  ├── Edge Agents
  ├── NetFlow Collectors
  └── Overview
Connectors
  ├── ISE pxGrid
  ├── Active Directory
  └── IoT Connectors
Settings
  ├── Global Settings
  ├── Clustering
  ├── Policy
  └── System
Monitoring
  ├── System Health
  ├── Agent Status
  ├── Data Ingestion
  └── Clustering Status
Audit/Logs
Reports/Export
```

### Option 2: Grouped Structure (With Sections)

```
📊 Overview
  ├── Dashboard
  └── Monitoring
      ├── System Health
      ├── Agent Status
      ├── Data Ingestion
      └── Clustering Status

🔍 Discovery
  ├── Devices
  ├── Groups
  └── Network Flows

🎯 Policy
  ├── SGT Mappings
  ├── Access Rules
  ├── Policy Matrix
  ├── Policy Builder
  └── Impact Analysis

🏗️ Infrastructure
  ├── Topology
  ├── Data Sources
  │   ├── Edge Agents
  │   ├── NetFlow Collectors
  │   └── Overview
  └── Connectors
      ├── ISE pxGrid
      ├── Active Directory
      └── IoT Connectors

⚙️ Configuration
  ├── Settings
  │   ├── Global
  │   ├── Clustering
  │   ├── Policy
  │   └── System
  ├── Audit/Logs
  └── Reports/Export
```

---

## Recommended Approach: Hybrid

**Main Navigation (Left Sidebar):**
```
Dashboard
Devices
Groups
Network Flows
Policy
Topology
Data Sources    (with sub-menu: Agents, Collectors, Overview)
Connectors      (with sub-menu: ISE, AD, IoT)
Settings        (with sub-menu: Global, Clustering, Policy, System)
Monitoring      (with sub-menu: Health, Agents, Ingestion, Clustering)
Audit/Logs
Reports/Export
```

**Settings Sub-menu:**
- Global Settings
- Clustering Settings
- Policy Settings
- System Settings
- User Management (if applicable)

**Data Sources Sub-menu:**
- Edge Agents
- NetFlow Collectors
- Overview

**Connectors Sub-menu:**
- ISE pxGrid
- Active Directory
- IoT Connectors

---

## Missing Items Summary

Based on your requirements and system architecture, here's what's needed:

### ✅ Already Mentioned
1. ✅ **Settings/Configuration** tab
2. ✅ **Agent monitoring** (edge agents on switches)
3. ✅ **NetFlow collector monitoring** (devices without agents)
4. ✅ **Connector configuration** (ISE, AD) - under Settings
5. ✅ **Hierarchy/Topology configuration** tab

### 🆕 Additional Recommendations

6. **Monitoring Dashboard** - System health, agent status, data ingestion
7. **Audit/Logs** - Track all changes and admin actions
8. **Reports/Export** - Generate reports and export configurations
9. **Devices** - Dedicated device management (currently only in Clusters)
10. **Groups** - Dedicated group management (separate from Clusters view)
11. **Data Sources Overview** - Unified view of all data sources

---

## Implementation Priority

### Phase 1: Core Navigation (Essential)
- [ ] Settings/Configuration
- [ ] Topology/Hierarchy
- [ ] Data Sources (Agents + Collectors)
- [ ] Connectors (ISE, AD)

### Phase 2: Monitoring & Management
- [ ] Monitoring dashboard
- [ ] Devices management page
- [ ] Groups management page (enhanced)

### Phase 3: Audit & Reporting
- [ ] Audit/Logs
- [ ] Reports/Export

---

## Menu Icons Suggestions

- Dashboard: 📊 or 🏠
- Devices: 💻
- Groups: 👥 or 📦
- Network Flows: 🌐 or 📡
- Policy: 🛡️
- Topology: 🗺️ or 🏗️
- Data Sources: 📥 or 📊
- Connectors: 🔌 or 🔗
- Settings: ⚙️
- Monitoring: 📈 or 🔍
- Audit/Logs: 📋 or 📝
- Reports/Export: 📄 or 📤

