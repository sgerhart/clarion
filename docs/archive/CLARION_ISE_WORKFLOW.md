# Clarion-ISE Integration Workflows

## Overview

This document outlines the real-world scenarios and workflows for how Clarion integrates with Cisco ISE for SGT assignment and TrustSec matrix population. It addresses multiple deployment scenarios from greenfield to existing ISE deployments.

## Scenario 1: Greenfield Deployment (NetFlow → Clustering → SGT Recommendations → ISE Policies)

### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                   Phase 1: Data Collection                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. NetFlow Collection                                      │
│     • Collect NetFlow from native collector                 │
│     • Collect sketches from edge agents                     │
│     • Build endpoint behavioral profiles                    │
│                                                             │
│  2. Device Grouping (Categorization)                        │
│     • Run clustering on collected data                      │
│     • Group devices by behavioral patterns                  │
│     • Identify device types, roles, functions               │
│                                                             │
│  3. SGT Structure Recommendation                            │
│     • Analyze clusters                                      │
│     • Recommend SGT structure (SGT values and names)        │
│     • Map clusters → Recommended SGTs                       │
│                                                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ Recommended SGT Structure
                      ↓
┌─────────────────────────────────────────────────────────────┐
│              Phase 2: Policy Generation                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  4. ISE Authorization Policy Generation                     │
│     • Map clusters to policy conditions                     │
│     • Identify matching attributes:                         │
│       - AD group memberships                                │
│       - Device types/profiles                               │
│       - Network attributes (VLAN, subnet)                   │
│     • Generate ISE authorization policy rules               │
│                                                             │
│  5. TrustSec Matrix Population                              │
│     • Generate SGT-to-SGT communication matrix              │
│     • Generate SGACL policies for each SGT pair             │
│     • Create ISE TrustSec matrix configuration              │
│                                                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ ISE Policy Configurations
                      ↓
┌─────────────────────────────────────────────────────────────┐
│              Phase 3: ISE Deployment                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  6. Export & Deploy to ISE                                  │
│     • Export SGT definitions                                │
│     • Export authorization policies                         │
│     • Export TrustSec matrix (SGACLs and mappings)          │
│     • User reviews and deploys to ISE                       │
│                                                             │
│  7. ISE Applies Policies                                    │
│     • ISE evaluates authorization policies                  │
│     • Assigns SGTs based on policy conditions               │
│     • Propagates SGTs through network                       │
│                                                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ Current SGT Assignments (pxGrid)
                      ↓
┌─────────────────────────────────────────────────────────────┐
│              Phase 4: Verification & Sync                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  8. Clarion Syncs with ISE                                  │
│     • pxGrid subscriber receives session updates            │
│     • Stores current ISE SGT assignments                    │
│     • Compares with Clarion recommendations                 │
│     • Displays "Current ISE Assignment" vs "Recommended"    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Key Activities

1. **Data Collection & Analysis**
   - Collect NetFlow data (native collector + edge agents)
   - Build behavioral sketches
   - Run clustering to group devices

2. **SGT Structure Design**
   - Analyze clusters to understand device groupings
   - Recommend SGT values and names
   - Design SGT taxonomy (e.g., SGT 10: Servers, SGT 11: Corporate Users)

3. **Policy Generation**
   - Map each cluster to recommended SGT
   - Identify policy conditions (AD groups, device types, etc.)
   - Generate ISE authorization policy configurations

4. **ISE Deployment**
   - Export policy configurations
   - Deploy to ISE
   - ISE assigns SGTs based on policies

---

## Scenario 2: Enhanced with Identity Data (AD, IoT, etc.)

### Workflow

This scenario is the same as Scenario 1, but enriched with identity data:

```
NetFlow Data
    +
AD Integration (user/group data)
    +
IoT/Medical IoT Solutions
    +
Other Identity Sources
    ↓
Enhanced Categorization
    ↓
More Accurate Clustering (identity-aware)
    ↓
Better SGT Recommendations
    ↓
More Precise Policy Conditions
```

### Identity Data Sources

1. **Active Directory**
   - User group memberships
   - User attributes
   - Device attributes

2. **IoT/Medical IoT Solutions**
   - Device type information
   - Device profiles
   - Specialized device context

3. **Other Identity Sources**
   - LDAP directories
   - Custom identity systems
   - Third-party integrations

### Enhanced Policy Generation

With identity data, policy conditions are more precise:
- **Without identity**: "If device shows server-like behavior → SGT 10"
- **With identity**: "If AD group = 'IT-Servers' AND device profile = 'Server' → SGT 10"

---

## Scenario 3: Building Upon Existing ISE SGTs

### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│              Phase 1: Discover Existing ISE State           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. ISE pxGrid Integration                                  │
│     • Connect to ISE via pxGrid                             │
│     • Receive session updates                               │
│     • Store current SGT assignments                         │
│     • Import existing SGT definitions from ISE              │
│                                                             │
│  2. Analyze Existing SGT Structure                          │
│     • What SGTs already exist in ISE?                       │
     • What devices have SGTs assigned?                        │
     • What authorization policies exist?                      │
     • What's in the TrustSec matrix?                          │
│                                                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ Existing SGT Structure
                      ↓
┌─────────────────────────────────────────────────────────────┐
│        Phase 2: Analyze New Devices & Recommend             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  3. Collect New Device Data                                 │
│     • NetFlow from new devices                              │
│     • Sketches from edge agents                             │
│     • Identity data (AD, IoT, etc.)                         │
│                                                             │
│  4. Check SGT Assignment Status                             │
│     • For each new device:                                  │
│       - Does it have SGT assigned from ISE? (check pxGrid)  │
│       - If yes: Display current assignment                  │
│       - If no: Categorize and recommend                     │
│                                                             │
│  5. Categorization & Recommendation                         │
│     • Run clustering on new devices                         │
│     • Match to existing clusters or create new              │
│     • Recommend SGT (may be existing or new)                │
│     • Generate policy recommendations                       │
│                                                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ Recommendations
                      ↓
┌─────────────────────────────────────────────────────────────┐
│          Phase 3: Incremental Policy Updates                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  6. Policy Recommendations                                  │
│     • For devices without SGT:                              │
│       - Recommend assignment to existing SGT (if cluster    │
│         matches existing group)                             │
│       - OR recommend new SGT (if new device category)       │
│     • Generate incremental policy updates                   │
│     • Update TrustSec matrix (add new SGT pairs)            │
│                                                             │
│  7. Deploy Incremental Updates                              │
│     • Export incremental policy changes                     │
│     • Deploy to ISE                                         │
│     • ISE applies to new devices                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Key Activities

1. **Discover Existing State**
   - Import existing SGT definitions from ISE
   - Sync current SGT assignments via pxGrid
   - Understand existing authorization policies

2. **New Device Detection**
   - Track "first-seen" endpoints
   - Check if SGT already assigned (from ISE)
   - Categorize unassigned devices

3. **Incremental Recommendations**
   - Recommend assignment to existing SGTs when appropriate
   - Recommend new SGTs only when necessary
   - Generate incremental policy updates

4. **Building Upon Existing Matrix**
   - Extend existing TrustSec matrix
   - Add new SGT-to-SGT pairs
   - Update SGACL policies

---

## Scenario 4: Other Scenarios

### Potential Additional Scenarios

1. **Hybrid Approach**
   - Some devices get SGTs from existing ISE policies
   - Some devices get SGTs from Clarion recommendations
   - Clarion manages the gap/overlap

2. **Policy Refinement**
   - ISE policies exist but need refinement
   - Clarion analyzes actual behavior vs policy assignments
   - Recommends policy adjustments

3. **Multi-ISE Deployment**
   - Multiple ISE nodes
   - Different policies per location/domain
   - Clarion provides unified view and recommendations

4. **Migration/Consolidation**
   - Migrating from one SGT structure to another
   - Consolidating multiple SGT schemes
   - Clarion provides migration plan

---

## Clarion Architecture Requirements

### Core Capabilities Needed

#### 1. SGT Discovery & Import
- [ ] **Import existing SGT definitions from ISE**
  - Via ISE ERS API or manual import
  - Store in Clarion's SGT registry
  - Track "source" (ISE vs Clarion-recommended)

- [ ] **Sync current SGT assignments**
  - Via ISE pxGrid (session updates)
  - Store endpoint_id → current_sgt_value
  - Track assignment timestamp and policy source

#### 2. New Device Detection & Categorization
- [ ] **First-seen tracking**
  - Track when devices are first observed
  - Maintain "pending assignment" list

- [ ] **SGT assignment status check**
  - For each new device, check: Does ISE have SGT assigned?
  - Display status: "Assigned by ISE" vs "Pending Assignment"

- [ ] **Categorization for unassigned devices**
  - Run clustering on devices without SGT
  - Match to existing clusters or create new
  - Recommend appropriate SGT

#### 3. Policy Recommendation Engine
- [ ] **Map clusters to policy conditions**
  - Analyze cluster members to identify common attributes:
    - AD group memberships
    - Device types/profiles
    - Network attributes (VLAN, subnet)
  - Generate policy condition expressions

- [ ] **Recommend SGT assignment**
  - Map cluster to recommended SGT (existing or new)
  - Provide justification
  - Generate policy rule recommendation

- [ ] **Policy generation**
  - Generate ISE authorization policy configurations
  - Support both new policies and policy updates
  - Export in ISE-compatible formats

#### 4. TrustSec Matrix Management
- [ ] **Build/Extend TrustSec matrix**
  - Generate SGT-to-SGT communication matrix
  - Generate SGACL policies
  - Support incremental updates (add to existing matrix)

- [ ] **Matrix gap analysis**
  - Identify missing SGT pairs in existing matrix
  - Recommend SGACL policies for missing pairs
  - Highlight inconsistencies

#### 5. Incremental Updates
- [ ] **Track changes over time**
  - New devices added
  - SGT assignments changed
  - Policy recommendations updated

- [ ] **Generate incremental policy updates**
  - Only export changed/new policies
  - Support policy updates vs full replacement
  - Provide change summary

#### 6. Comparison & Verification
- [ ] **Compare Clarion vs ISE**
  - Clarion recommendations vs current ISE assignments
  - Highlight differences
  - Identify conflicts

- [ ] **Verification workflow**
  - After ISE deployment, verify assignments
  - Compare expected vs actual SGT assignments
  - Identify misconfigurations

---

## API Design Implications

### SGT Status Checking

```python
GET /api/devices/{endpoint_id}/sgt-status
{
  "endpoint_id": "12:7a:05:f0:7f:02",
  "current_ise_assignment": {
    "sgt_value": 12,
    "sgt_name": "Mobile Devices",
    "assigned_by": "ISE Authorization Policy",
    "policy_name": "Mobile-Devices-Policy",
    "assigned_at": "2025-01-15T10:30:00Z"
  },
  "clarion_recommendation": {
    "sgt_value": 12,
    "sgt_name": "Mobile Devices",
    "confidence": 0.95,
    "justification": "Cluster analysis shows mobile device behavior patterns"
  },
  "status": "aligned" | "conflict" | "pending"
}
```

### Policy Recommendations

```python
GET /api/clusters/{cluster_id}/policy-recommendation
{
  "cluster_id": 2,
  "recommended_sgt": 12,
  "policy_conditions": {
    "ad_groups": ["All-Employees"],
    "device_profiles": ["CorporatePhone", "MobileDevice"],
    "network_attributes": null
  },
  "policy_rule": {
    "name": "Mobile-Devices-Cluster-2",
    "condition": "AD:Group EQUALS 'All-Employees' AND Device:Profile EQUALS 'CorporatePhone'",
    "action": "Assign SGT 12"
  },
  "impact": {
    "devices_affected": 1679,
    "new_devices": 150
  }
}
```

### ISE State Import

```python
POST /api/ise/import-sgts
{
  "source": "ise_ers_api" | "manual" | "pxgrid",
  "sgts": [
    {
      "sgt_value": 10,
      "sgt_name": "Servers",
      "description": "Production servers"
    }
  ]
}

POST /api/ise/sync-assignments
{
  "source": "pxgrid",
  "assignments": [
    {
      "endpoint_id": "12:7a:05:f0:7f:02",
      "sgt_value": 12,
      "assigned_at": "2025-01-15T10:30:00Z",
      "policy_name": "Mobile-Devices-Policy"
    }
  ]
}
```

---

## UI/UX Implications

### Device Detail View

**Show:**
- ✅ Current ISE Assignment (read-only, from pxGrid)
- ✅ Clarion Recommendation (with justification)
- ✅ Status: "Aligned", "Conflict", or "Pending"
- ✅ Policy Recommendation (if different from current)

**Don't Show:**
- ❌ Direct SGT value input field

### Cluster/Group Detail View

**Show:**
- ✅ Recommended SGT for cluster
- ✅ Policy conditions (AD groups, device types, etc.)
- ✅ Policy recommendation
- ✅ Devices with SGT assigned vs pending
- ✅ "Generate ISE Policy" button

### New "ISE Integration" Page

**Show:**
- Current ISE SGT structure (imported from ISE)
- Current SGT assignments (synced from pxGrid)
- Clarion recommendations vs ISE assignments
- Pending assignments (devices without SGT)
- Policy recommendations ready for export

---

## Implementation Priorities

### Phase 1: Core Discovery & Status (High Priority)
- [ ] Import existing SGT definitions from ISE
- [ ] Sync current SGT assignments via pxGrid
- [ ] Display "Current ISE Assignment" in UI
- [ ] Track devices without SGT (pending list)

### Phase 2: Policy Recommendations (High Priority)
- [ ] Policy recommendation engine
- [ ] Map clusters → policy conditions
- [ ] Generate ISE policy configurations
- [ ] Policy export functionality

### Phase 3: Incremental Updates (Medium Priority)
- [ ] New device detection and categorization
- [ ] Incremental policy generation
- [ ] TrustSec matrix extension
- [ ] Change tracking and summaries

### Phase 4: Advanced Features (Lower Priority)
- [ ] Policy refinement recommendations
- [ ] Multi-ISE support
- [ ] Migration planning
- [ ] Automated policy deployment

---

## References

- `docs/ISE_SGT_ASSIGNMENT.md` - Detailed ISE SGT assignment architecture
- `docs/ISE_INTEGRATION.md` - Integration architecture overview

