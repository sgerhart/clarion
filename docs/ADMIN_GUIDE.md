# Administrative Control & User Guide

## Overview

Clarion provides **full administrative control** over all system components while **hiding complexity** from end users. The goal is to make SGT-based policy adoption easy, even for organizations with diverse device types (Windows, Linux, Mac, IoT, etc.) that may not be in Active Directory.

---

## Core Principles

### 1. Full Administrative Override
- ✅ **All AI recommendations can be overridden**
- ✅ **Manual grouping and SGT assignment**
- ✅ **Custom policy creation**
- ✅ **Complete control over all settings**

### 2. Device Type Agnostic
- ✅ **Works with any device type** (Windows, Linux, Mac, IoT, etc.)
- ✅ **Does not require AD membership**
- ✅ **Behavioral clustering works without identity**
- ✅ **Identity is enrichment, not requirement**

### 3. Clear Hierarchy
- ✅ **Intuitive navigation structure**
- ✅ **Progressive disclosure** (simple → detailed)
- ✅ **Visual hierarchy** (tree view, breadcrumbs)
- ✅ **Context-aware information**

### 4. Hide Complexity
- ✅ **Simple default views**
- ✅ **Advanced options hidden by default**
- ✅ **Plain language explanations**
- ✅ **Automated workflows**

---

## Device Type Support

### Supported Device Types

| Device Type | AD Required? | Identity Sources | Clustering Method |
|-------------|--------------|------------------|-------------------|
| **Windows** | Optional | AD, ISE, NetFlow | Behavioral + Identity |
| **Linux** | No | ISE, NetFlow, MAC | Behavioral + Device Type |
| **Mac** | Optional | ISE, NetFlow, MAC | Behavioral + Device Type |
| **IoT** | No | ISE, NetFlow, MAC | Behavioral + Device Type |
| **Printers** | No | ISE, NetFlow, MAC | Behavioral + Device Type |
| **Servers** | Optional | AD, ISE, NetFlow | Behavioral + Traffic Pattern |
| **Mobile** | No | ISE, NetFlow | Behavioral + Device Type |
| **Unknown** | No | NetFlow, MAC | Behavioral only |

### Clustering Without Identity

**Behavioral clustering works without any identity information:**

```python
# Clustering based purely on behavior
features = [
    peer_diversity,      # Who they talk to
    service_diversity,   # What services they use
    port_diversity,      # What ports they use
    in_out_ratio,        # Client vs server pattern
    traffic_volume,      # How much traffic
    active_hours,        # When they're active
]

# These features work for ANY device type
# No AD, no ISE, no identity required
```

### Identity as Enrichment

Identity information **enhances** clustering but is **not required**:

```python
# Priority order for labeling:
1. ISE Profile (if available)      # Works for all devices
2. Device Type (if available)      # Works for all devices
3. AD Group (if available)          # Windows only
4. Behavioral Pattern (always)      # Works for all devices
```

---

## Administrative Control Hierarchy

### Level 1: Global Settings (System-Wide)

**Location:** Settings → Global Configuration

```yaml
Global Settings:
  - Clustering Parameters:
      - min_cluster_size: 50 (admin override)
      - min_samples: 10 (admin override)
      - algorithm: HDBSCAN (admin override)
  
  - SGT Allocation:
      - base_sgt_value: 2 (admin override)
      - reserved_ranges: [0-1, 65535] (admin override)
      - category_ranges: users [2-9], servers [10-19], etc.
  
  - Policy Generation:
      - min_flow_count: 10 (admin override)
      - default_action: DENY (admin override)
      - enable_impact_analysis: true
```

### Level 2: Device Groups (Clusters)

**Location:** Clusters → Manage Groups

**Actions:**
- ✅ Rename clusters
- ✅ Merge clusters
- ✅ Split clusters (manual)
- ✅ Delete clusters
- ✅ Reassign devices to different clusters

**Override Example:**
```python
# AI recommends: Cluster 0 → "Corporate Laptops"
# Admin overrides: Cluster 0 → "Engineering Team"
# Result: Cluster renamed, all devices updated
```

### Level 3: SGT Mappings

**Location:** SGT Matrix → Manage SGTs

**Actions:**
- ✅ Create new SGTs
- ✅ Rename SGT names
- ✅ Reassign SGT values
- ✅ Map clusters to SGTs
- ✅ Assign individual devices to SGTs

**Override Example:**
```python
# AI recommends: Cluster 0 → SGT 2 "Corp-Users"
# Admin overrides: Cluster 0 → SGT 5 "Engineering"
# Result: All cluster members assigned to SGT 5
```

### Level 4: Policies (SGACLs)

**Location:** Policies → Manage Rules

**Actions:**
- ✅ Approve/reject generated policies
- ✅ Add custom rules
- ✅ Modify existing rules
- ✅ Delete rules
- ✅ Change rule order (priority)

**Override Example:**
```python
# AI generates: permit tcp dst eq 443
# Admin modifies: permit tcp dst eq 443,8443
# Result: Policy updated, impact analysis re-run
```

### Level 5: Individual Devices

**Location:** Devices → Device Details

**Actions:**
- ✅ Override device cluster assignment
- ✅ Override device SGT assignment
- ✅ Add manual tags/labels
- ✅ Exclude device from clustering
- ✅ Force device into specific cluster

---

## User Interface Hierarchy

### Main Navigation Structure

```
Dashboard (/)              # Overview, metrics, health
│
├── Network Flows          # Flow visualization, queries
│   ├── Flow Graph         # D3.js network visualization
│   ├── Flow Table         # Filterable flow records
│   └── Flow Analytics     # Statistics, top talkers
│
├── Devices                # Device management
│   ├── Device List        # All devices with filters
│   ├── Device Details     # Individual device view
│   └── Device Search      # Search by IP, MAC, hostname
│
├── Clusters               # Cluster management
│   ├── Cluster List       # All clusters with SGTs
│   ├── Cluster Details    # Cluster members, explanation
│   ├── Cluster Visualization  # PCA/t-SNE plot
│   └── Manual Grouping    # Admin: create custom groups
│
├── SGT Matrix             # SGT communication matrix
│   ├── Heatmap            # Interactive Plotly heatmap
│   ├── Matrix Details     # Cell-by-cell breakdown
│   └── SGT Management     # Admin: manage SGT registry
│
├── Policies               # Policy management
│   ├── Policy List        # All SGACL policies
│   ├── Policy Builder     # Generate new policies
│   ├── Policy Editor      # Edit existing policies
│   ├── Impact Analysis    # What would break?
│   └── Export             # Cisco CLI, ISE JSON
│
├── Topology               # Network topology
│   ├── Locations          # Campus, Branch, Remote Site
│   ├── Address Spaces     # IP address ranges
│   ├── Subnets            # Subnet mapping
│   └── Switches           # Switch registration
│
└── Settings               # System configuration
    ├── Global Settings    # Clustering, SGT allocation
    ├── Data Sources       # NetFlow collectors, connectors
    ├── Integrations       # AD, ISE, DNS
    └── AI Configuration   # LLM settings (if enabled)
```

### Progressive Disclosure

#### Simple View (Default)
- Shows only essential information
- High-level summaries
- Recommended actions clearly marked
- No technical jargon

#### Detailed View (Expand)
- Click to expand for more details
- Technical metrics shown
- Raw data access
- Configuration options

#### Advanced View (Expert Mode)
- All technical details visible
- Direct database queries
- Advanced configuration
- Debugging information

---

## Override Workflow

### 1. Override Group Assignment

**Scenario:** AI clusters devices together, but admin knows they should be separate.

**Steps:**
1. Navigate to Clusters → Cluster Details
2. Select devices to move
3. Click "Move to Different Cluster"
4. Choose target cluster or create new cluster
5. Confirm override
6. System updates cluster assignments and SGT mappings

**Result:**
- Devices reassigned to new cluster
- SGT assignment updated (if cluster has SGT)
- Audit trail recorded

### 2. Override SGT Mapping

**Scenario:** AI recommends SGT 2 "Corp-Users", but admin wants SGT 5 "Engineering".

**Steps:**
1. Navigate to SGT Matrix → SGT Management
2. Select cluster
3. Click "Reassign SGT"
4. Choose new SGT (or create new)
5. Confirm override
6. System updates all cluster members

**Result:**
- All cluster members assigned to new SGT
- Policy matrix updated
- Export files reflect new SGT

### 3. Override Policy

**Scenario:** AI generates policy, but admin needs to add exception.

**Steps:**
1. Navigate to Policies → Policy List
2. Select policy to modify
3. Click "Edit Policy"
4. Add/modify/delete rules
5. Run impact analysis
6. Save changes

**Result:**
- Policy updated
- Impact analysis shows what changes
- Export files reflect modifications

---

## Device Type Handling

### Non-AD Devices

**Clarion handles devices that are not in Active Directory:**

1. **Behavioral Clustering** - Devices grouped by communication patterns
2. **Device Type Detection** - MAC OUI, ISE profiling, manual assignment
3. **ISE Integration** - ISE profiles work for all device types
4. **Manual Assignment** - Admin can manually assign devices to groups/SGTs

**Example:**
```python
# Linux server (not in AD)
- Device Type: "server" (from MAC OUI or ISE)
- Behavioral Pattern: High inbound traffic, ports 22, 443
- Cluster: "Servers" (behavioral match)
- SGT: 10 "Servers"
# No AD group needed!
```

### Unknown Devices

**Devices with no identity information:**

1. **Pure Behavioral Clustering** - Grouped by what they do
2. **Anomaly Detection** - Flagged if behavior is unusual
3. **Manual Review** - Admin can assign labels/SGTs
4. **Gradual Enrichment** - Identity added later when available

**Example:**
```python
# Unknown IoT device
- No AD group
- No ISE profile
- Behavioral Pattern: Periodic small packets, port 443
- Cluster: "IoT Devices" (behavioral inference)
- SGT: 21 "IoT"
# Works entirely from behavior!
```

---

## Administrative Best Practices

### 1. Start with AI Recommendations

- Let the system generate initial clusters and SGTs
- Review recommendations before overriding
- Use AI as starting point, not final answer

### 2. Override Strategically

- Document why overrides were made
- Use overrides to encode domain knowledge
- Review overrides periodically

### 3. Test Before Enforcement

- Always run impact analysis before deploying policies
- Test in monitor mode first
- Gradual rollout recommended

### 4. Maintain Audit Trail

- System logs all admin actions
- Review audit logs periodically
- Track changes to clusters, SGTs, policies

### 5. Iterate and Refine

- Start with broad groupings
- Refine based on real traffic patterns
- Adjust policies based on enforcement feedback

---

## Related Documentation

- **System Design:** See `docs/DESIGN.md` for architecture overview
- **Categorization Engine:** See `docs/CATEGORIZATION_ENGINE.md` for clustering details
- **Policy Generation:** See `docs/DESIGN.md` for policy workflow
- **Topology Management:** See `docs/TOPOLOGY_ARCHITECTURE.md` for location hierarchy

