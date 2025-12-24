# Administrative Control & User Hierarchy

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
      - custom_ranges: [] (admin defined)
  
  - Policy Defaults:
      - default_action: deny (admin override)
      - require_approval: true (admin override)
      - auto_apply: false (admin override)
  
  - Data Retention:
      - flow_retention_days: 90 (admin override)
      - sketch_retention_days: 365 (admin override)
```

### Level 2: Device Groups (Clusters)

**Location:** Devices → Groups

**Admin Controls:**
- ✅ **Create manual groups** (bypass clustering)
- ✅ **Rename groups** (override AI labels)
- ✅ **Merge groups** (combine clusters)
- ✅ **Split groups** (divide clusters)
- ✅ **Delete groups** (remove clusters)
- ✅ **Assign devices** (manual assignment)
- ✅ **Remove devices** (manual removal)

**Example:**
```
Group: "Linux Servers"
├── Created: Manual (admin override)
├── Members: 25 devices
├── SGT: 15 - Linux-Servers
├── Override Reason: "Production Linux servers need separate SGT"
└── Devices:
    ├── 00:11:22:33:44:55 (web-server-01)
    ├── 00:11:22:33:44:56 (db-server-01)
    └── ... (23 more)
```

### Level 3: SGT Mappings

**Location:** Policy → SGT Mappings

**Admin Controls:**
- ✅ **Assign SGT values** (override AI recommendations)
- ✅ **Rename SGTs** (override AI names)
- ✅ **Reassign SGTs** (change group → SGT mapping)
- ✅ **Reserve SGT values** (prevent auto-assignment)
- ✅ **Create custom SGTs** (manual creation)

**Example:**
```
SGT Mapping Override:
├── Group: "Linux Servers"
├── Original: SGT 10 - Server-Like-Endpoints (AI)
├── Override: SGT 15 - Linux-Servers (Admin)
├── Override By: admin@company.com
├── Override Date: 2025-01-15
└── Reason: "Linux servers need dedicated SGT for compliance"
```

### Level 4: Policies (SGACLs)

**Location:** Policy → Access Rules

**Admin Controls:**
- ✅ **Create policies** (manual policy creation)
- ✅ **Modify policies** (add/remove rules)
- ✅ **Delete policies** (remove rules)
- ✅ **Override default action** (permit/deny)
- ✅ **Set policy priority** (rule ordering)
- ✅ **Enable/disable policies** (temporary disable)

**Example:**
```
Policy Override:
├── Policy: Linux-Servers → Corporate-Users
├── Original: Deny all (AI recommendation)
├── Override: Permit HTTPS, SSH (Admin)
├── Rules Added:
│   ├── permit tcp 443 (HTTPS)
│   ├── permit tcp 22 (SSH)
│   └── deny ip (default)
├── Override By: admin@company.com
└── Reason: "IT team needs SSH access to Linux servers"
```

### Level 5: Individual Devices

**Location:** Devices → [Device Details]

**Admin Controls:**
- ✅ **Manual group assignment** (override cluster assignment)
- ✅ **Manual SGT assignment** (override group SGT)
- ✅ **Override device type** (correct misclassification)
- ✅ **Add identity mapping** (link to user/device)
- ✅ **Override behavioral data** (correct errors)
- ✅ **Exclude from clustering** (manual exclusion)

**Example:**
```
Device: 00:11:22:33:44:55
├── Detected: Server-Like-Endpoints (Cluster 3)
├── Override: Linux-Servers (Manual Group)
├── SGT: 15 - Linux-Servers (Manual)
├── Device Type: linux-server (Admin override)
├── Identity: web-server-01.prod.company.com
└── Override Reason: "Production web server, needs dedicated SGT"
```

---

## User Interface Hierarchy

### Main Navigation Structure

```
Clarion Dashboard
│
├── 📊 Overview (Simple View)
│   ├── Total Devices: 1,234
│   ├── Active Groups: 12
│   ├── Policies: 45
│   └── Recent Activity
│
├── 🔍 Devices (Device Management)
│   ├── All Devices (list view)
│   ├── Groups (cluster view)
│   │   ├── AI-Generated Groups
│   │   ├── Manual Groups
│   │   └── Unassigned Devices
│   ├── Device Details
│   │   ├── Basic Info
│   │   ├── Behavior Analysis
│   │   ├── Group Assignment
│   │   └── Policy Impact
│   └── Search & Filter
│
├── 🏷️  Groups (Group Management)
│   ├── All Groups
│   │   ├── AI-Generated (12)
│   │   ├── Manual (3)
│   │   └── Merged (2)
│   ├── Group Details
│   │   ├── Members (devices)
│   │   ├── SGT Assignment
│   │   ├── Behavioral Profile
│   │   ├── Policy Rules
│   │   └── Override History
│   └── Create/Edit Group
│
├── 🎯 Policy (Policy Management)
│   ├── SGT Mappings
│   │   ├── All SGTs
│   │   ├── SGT Details
│   │   └── Override SGT
│   ├── Access Rules (SGACLs)
│   │   ├── All Policies
│   │   ├── Policy Matrix
│   │   ├── Policy Details
│   │   └── Create/Edit Policy
│   └── Policy Impact
│       ├── Blocked Traffic
│       ├── Allowed Traffic
│       └── Recommendations
│
├── ⚙️  Settings (Administrative)
│   ├── Global Settings
│   ├── Clustering Settings
│   ├── SGT Allocation
│   ├── Policy Defaults
│   └── Data Retention
│
└── 📈 Analytics (Advanced)
    ├── Clustering Analysis
    ├── Policy Effectiveness
    ├── Traffic Patterns
    └── Compliance Reports
```

### Progressive Disclosure

#### Simple View (Default)
```
Group: Engineering Users
├── Devices: 150
├── SGT: 10
└── Status: Active
```

#### Detailed View (Expand)
```
Group: Engineering Users
├── Devices: 150
│   ├── Windows: 120
│   ├── Mac: 25
│   ├── Linux: 5
│   └── Unknown: 0
├── SGT: 10 - Engineering-Users
├── Created: AI-Generated (2025-01-10)
├── Last Modified: Admin Override (2025-01-15)
├── Behavioral Profile:
│   ├── Avg Peers: 45
│   ├── Avg Services: 12
│   └── Traffic Pattern: Client
├── Policy Rules: 8 policies
└── Override History:
    └── Renamed from "Engineering Team" (admin, 2025-01-15)
```

#### Advanced View (Expert Mode)
```
Group: Engineering Users
├── [All detailed fields]
├── Clustering Details:
│   ├── Cluster ID: 0
│   ├── Algorithm: HDBSCAN
│   ├── Silhouette Score: 0.72
│   └── Feature Weights: [...]
├── ML Model Info:
│   ├── Training Date: 2025-01-10
│   ├── Model Version: v2.1
│   └── Confidence: 0.85
└── [Technical details...]
```

---

## Override Workflow

### 1. Override Group Assignment

**Simple Path:**
```
Devices → [Select Device] → Change Group → [Select New Group] → Save
```

**With Justification:**
```
Devices → [Select Device] → Change Group → [Select New Group] 
→ Reason: "Device is production server, needs dedicated group"
→ Save
```

### 2. Override SGT Mapping

**Simple Path:**
```
Groups → [Select Group] → Change SGT → [Enter SGT Value] → Save
```

**With Validation:**
```
Groups → [Select Group] → Change SGT → [Enter SGT Value]
→ System checks: SGT available? Reserved? In use?
→ Confirm Override → Save
```

### 3. Override Policy

**Simple Path:**
```
Policy → Access Rules → [Select Policy] → Edit Rules
→ Add/Remove Rules → Save
```

**With Impact Analysis:**
```
Policy → Access Rules → [Select Policy] → Edit Rules
→ System shows: "This will affect 45 devices, block 12 flows"
→ Confirm → Save
```

---

## Device Type Handling

### Non-AD Devices

**Clustering Strategy:**
1. **Primary:** Behavioral features (always available)
2. **Secondary:** Device type from ISE/NetFlow
3. **Tertiary:** MAC address OUI lookup
4. **Fallback:** Generic device classification

**Labeling Strategy:**
```python
if device_type == "linux":
    label = "Linux Servers"  # or "Linux Workstations"
elif device_type == "mac":
    label = "Mac Users"
elif device_type == "iot":
    label = "IoT Devices"
elif ise_profile:
    label = f"{ise_profile} Devices"
else:
    # Behavioral fallback
    if is_server_behavior:
        label = "Server-Like Endpoints"
    else:
        label = "Client Devices"
```

### Unknown Devices

**Handling:**
- ✅ **Still clustered** based on behavior
- ✅ **Generic labels** ("Endpoint Group X")
- ✅ **Admin can assign** proper group/name
- ✅ **System learns** from admin corrections

**Example:**
```
Unknown Device: 00:11:22:33:44:55
├── Detected: Cluster 5 (behavioral)
├── Label: "Endpoint Group 5" (generic)
├── Admin Action: Assign to "IoT Devices"
├── System Learning: "Similar devices → IoT Devices"
└── Future: Auto-label similar devices as "IoT Devices"
```

---

## Simplified Views

### Dashboard (Simple)

```
┌─────────────────────────────────────────┐
│  Clarion - TrustSec Policy Copilot      │
├─────────────────────────────────────────┤
│                                          │
│  📊 Your Network                        │
│  ├── 1,234 Devices                      │
│  ├── 12 Groups                          │
│  └── 45 Policies                        │
│                                          │
│  🎯 Quick Actions                       │
│  ├── Review Recommendations (12 new)   │
│  ├── Create Policy                      │
│  └── Assign Device to Group             │
│                                          │
│  📈 Recent Activity                     │
│  ├── 5 devices added (today)           │
│  ├── 2 groups created (yesterday)      │
│  └── 1 policy updated (2 hours ago)    │
│                                          │
└─────────────────────────────────────────┘
```

### Group View (Simple)

```
┌─────────────────────────────────────────┐
│  Groups                                  │
├─────────────────────────────────────────┤
│                                          │
│  Engineering Users                      │
│  ├── 150 devices                        │
│  ├── SGT: 10                            │
│  └── [View Details] [Edit]              │
│                                          │
│  Linux Servers                          │
│  ├── 25 devices                         │
│  ├── SGT: 15                            │
│  └── [View Details] [Edit]              │
│                                          │
│  IoT Devices                            │
│  ├── 89 devices                         │
│  ├── SGT: 20                            │
│  └── [View Details] [Edit]              │
│                                          │
└─────────────────────────────────────────┘
```

### Policy View (Simple)

```
┌─────────────────────────────────────────┐
│  Access Rules                           │
├─────────────────────────────────────────┤
│                                          │
│  Engineering Users → Servers            │
│  ├── Allow: HTTPS (443), SSH (22)      │
│  ├── Block: Everything else            │
│  └── [Edit] [View Impact]              │
│                                          │
│  IoT Devices → Internet                │
│  ├── Allow: HTTPS (443), DNS (53)       │
│  ├── Block: Everything else            │
│  └── [Edit] [View Impact]              │
│                                          │
└─────────────────────────────────────────┘
```

---

## Admin Override API

### Endpoints

```python
# Override group assignment
POST /api/admin/groups/{group_id}/override
{
    "action": "rename",
    "new_name": "Linux Servers",
    "reason": "Production Linux servers"
}

# Override SGT mapping
POST /api/admin/sgts/{sgt_id}/override
{
    "action": "reassign",
    "new_value": 15,
    "reason": "Compliance requirement"
}

# Override policy
POST /api/admin/policies/{policy_id}/override
{
    "action": "add_rule",
    "rule": {
        "protocol": "tcp",
        "port": 443,
        "action": "permit"
    },
    "reason": "Allow HTTPS access"
}

# Manual device assignment
POST /api/admin/devices/{device_id}/assign
{
    "group_id": 5,
    "sgt_value": 15,
    "reason": "Production server"
}
```

---

## Implementation Plan

### Phase 1: Enhanced Admin Controls (2-3 weeks)
- [ ] Manual group creation UI
- [ ] Device assignment UI
- [ ] SGT override UI
- [ ] Policy override UI
- [ ] Override history tracking

### Phase 2: Device Type Support (2-3 weeks)
- [ ] Non-AD device detection
- [ ] Device type classification
- [ ] MAC OUI lookup
- [ ] Generic device handling
- [ ] Unknown device workflow

### Phase 3: Simplified UI (3-4 weeks)
- [ ] Dashboard redesign
- [ ] Progressive disclosure
- [ ] Simple/Advanced mode toggle
- [ ] Plain language explanations
- [ ] Contextual help

### Phase 4: Hierarchy Navigation (2-3 weeks)
- [ ] Tree view navigation
- [ ] Breadcrumb trails
- [ ] Quick actions
- [ ] Search and filter
- [ ] Visual hierarchy indicators

---

## Benefits

1. **Full Control** - Admins can override anything
2. **Device Agnostic** - Works with any device type
3. **Easy Adoption** - Simple views hide complexity
4. **Flexible** - Manual overrides for edge cases
5. **Auditable** - All overrides tracked
6. **Learnable** - System learns from admin corrections

---

## Example: Complete Override Workflow

```
1. System detects: 25 Linux servers clustered as "Server-Like Endpoints"
   ↓
2. Admin reviews: "These are production Linux servers, need separate group"
   ↓
3. Admin creates: Manual group "Linux Servers"
   ↓
4. Admin assigns: All 25 devices to new group
   ↓
5. Admin overrides: SGT from 10 to 15 (Linux-Servers)
   ↓
6. Admin creates: Policy "Linux-Servers → Corporate-Users"
   ↓
7. System learns: "Linux servers should be separate group"
   ↓
8. Future: Similar devices auto-grouped as "Linux Servers"
```

---

## Questions to Address

1. **Override Granularity**
   - Per-device overrides?
   - Per-group overrides?
   - Global overrides?

2. **Override Persistence**
   - Permanent overrides?
   - Temporary overrides (until next clustering)?
   - Override with expiration?

3. **Learning from Overrides**
   - Should system learn from overrides?
   - How to prevent override loops?
   - When to suggest removing overrides?

4. **UI Complexity**
   - How many levels of detail?
   - When to show advanced options?
   - How to guide users?

