# Cisco ISE Integration Architecture

## Overview

This document outlines how Clarion integrates with Cisco Identity Services Engine (ISE) for Security Group Tag (SGT) assignment and policy management. It explains the architectural alignment with ISE's policy-based SGT assignment model.

**See also:** `docs/CLARION_ISE_WORKFLOW.md` for detailed workflow scenarios including greenfield deployments, identity-enhanced categorization, building upon existing ISE SGTs, and incremental updates.

## ISE SGT Assignment Model

### Key Principle: Policy-Based Assignment

**Critical Understanding**: ISE assigns SGTs through **authorization policies**, not by directly setting SGT values on devices. This fundamental principle must guide all Clarion-ISE integration.

### Assignment Methods

#### 1. Dynamic Assignment (Primary)
- Occurs during authentication/authorization
- Policy evaluates conditions:
  - AD group membership
  - Device type/profile
  - User identity attributes
  - Network attributes (VLAN, subnet, location)
- Policy result: Assign SGT X

#### 2. Static Assignment (Secondary)
- For non-authenticating devices
- Static mappings:
  - VLAN → SGT
  - Subnet → SGT
  - IP Address → SGT
  - Port Profile → SGT

## Clarion's Role

### What Clarion Does

1. **Categorization & Recommendation**
   - Analyze network traffic and device behavior
   - Categorize devices into logical groups
   - Recommend appropriate SGTs for each group
   - Generate policy recommendations

2. **Policy Generation**
   - Generate ISE authorization policy configurations
   - Suggest policy conditions (AD groups, device types, etc.)
   - Provide policy justification and impact analysis

3. **Current State Display**
   - Show what SGT ISE is currently assigning (via pxGrid)
   - Display policy that assigned the SGT
   - Compare recommendations vs current assignments

4. **Policy Export & Deployment**
   - Export ISE-compatible policy configurations
   - Generate deployment guides
   - (Future) Deploy policies via ISE ERS API

### What Clarion Does NOT Do

1. **Direct SGT Assignment**
   - ❌ Cannot directly set `device.sgt_value = 10`
   - ❌ ISE will override on next authentication
   - ❌ Not aligned with ISE architecture

2. **Bypass ISE Policy Engine**
   - ❌ Cannot assign SGTs independently of ISE
   - ❌ Must work through ISE authorization policies
   - ❌ Must respect ISE's policy-based model

## Integration Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Clarion System                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Categorization Engine                                   │
│     • Analyzes network traffic                              │
│     • Clusters devices by behavior                          │
│     • Recommends SGTs based on clusters                     │
│                                                             │
│  2. Policy Recommendation Engine                            │
│     • Cluster → Recommended SGT                             │
│     • Device attributes → Policy conditions                 │
│     • Generate policy rule recommendations                  │
│                                                             │
│  3. Policy Export                                           │
│     • Generate ISE authorization policy configs             │
│     • Export in ISE-compatible format                       │
│     • Provide deployment guide                              │
│                                                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ Policy Recommendations
                      │ (Export/Deploy)
                      ↓
┌─────────────────────────────────────────────────────────────┐
│                  Cisco ISE System                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Authorization Policies                                  │
│     • Evaluate conditions (AD groups, device types, etc.)  │
│     • Assign SGTs based on policy results                   │
│                                                             │
│  2. Policy Engine                                           │
│     • Processes authentication requests                     │
│     • Matches policies to devices/users                     │
│     • Assigns SGTs dynamically                              │
│                                                             │
│  3. SGT Propagation                                         │
│     • Inline tagging (TrustSec)                             │
│     • SXP (IP-to-SGT mappings)                              │
│                                                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ Session Updates (pxGrid)
                      │ Current SGT Assignments
                      ↓
┌─────────────────────────────────────────────────────────────┐
│              Clarion pxGrid Subscriber                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  • Receives session updates from ISE                        │
│  • Stores current SGT assignments                           │
│  • Updates UI with "Current ISE Assignment"                 │
│  • Compares with Clarion recommendations                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Policy Recommendation Workflow

```
1. Clarion Categorization
   ├─> Cluster devices by behavior
   ├─> Recommend SGT for cluster
   └─> Identify device attributes (AD groups, device types, etc.)

2. Policy Recommendation Generation
   ├─> Map cluster → Recommended SGT
   ├─> Identify policy conditions:
   │   ├─> AD group memberships
   │   ├─> Device profiles/types
   │   ├─> Network attributes
   │   └─> User attributes
   └─> Generate policy rule:
       ├─> Condition: AD group = "HR-Users" OR device profile = "CorporatePhone"
       ├─> Action: Assign SGT 12
       └─> Justification: "Cluster analysis shows these devices share HR-related behavior"

3. User Review
   ├─> Review recommendation
   ├─> View impact analysis (how many devices affected)
   └─> Accept or modify recommendation

4. Policy Export
   ├─> Generate ISE authorization policy configuration
   ├─> Export in ISE-compatible format
   └─> Generate deployment guide

5. Policy Deployment (Future)
   ├─> Deploy to ISE via ERS API
   ├─> Verify deployment
   └─> Monitor policy enforcement

6. ISE Policy Application
   ├─> ISE evaluates policy on next authentication
   ├─> Assigns SGT to matching devices
   └─> Propagates SGT through network

7. Clarion Sync (via pxGrid)
   ├─> Receive session updates from ISE
   ├─> Store current SGT assignments
   └─> Update UI to show "Current ISE Assignment"
```

## API Changes Needed

### Current API (Needs Update)

```python
# ❌ Current: Direct SGT editing
PUT /api/devices/{endpoint_id}
{
  "sgt_value": 12  # This doesn't work with ISE
}
```

### Target API (Recommended)

```python
# ✅ Recommended: Policy recommendation
POST /api/policy/recommendations
{
  "cluster_id": 2,
  "recommended_sgt": 12,
  "conditions": {
    "ad_groups": ["HR-Users"],
    "device_profiles": ["CorporatePhone"]
  }
}

# ✅ Recommended: Policy export
GET /api/policy/recommendations/{id}/ise-config
# Returns ISE authorization policy configuration

# ✅ Recommended: Current ISE assignment (from pxGrid)
GET /api/devices/{endpoint_id}/ise-assignment
{
  "current_sgt": 12,
  "assigned_by": "ISE Authorization Policy",
  "policy_name": "HR-Devices-Policy",
  "assigned_at": "2025-01-15T10:30:00Z"
}
```

## UI Changes Needed

### Device Detail Modal

**Remove:**
- ❌ Direct SGT value input field
- ❌ "Save SGT" button

**Keep:**
- ✅ Cluster assignment editing (user can move device to different cluster)
  - Moving device to new cluster → triggers policy recommendation for new SGT

**Add:**
- ✅ "Current ISE Assignment" section (read-only, from pxGrid)
  - Current SGT value
  - Policy that assigned it
  - When it was assigned
- ✅ "Clarion Recommendation" section
  - Recommended SGT (based on current cluster)
  - Justification
  - Recommended policy rule
  - "Generate ISE Policy" button
- ✅ "Policy Recommendation" section (shown when cluster assignment changes)
  - Old SGT vs New SGT
  - Recommended policy rule
  - Impact analysis
  - "Generate ISE Policy" button

**Note:** See `docs/CLUSTER_ASSIGNMENT_WORKFLOW.md` for details on how cluster assignment changes trigger policy recommendations.

### Group Detail Modal

**Change:**
- ❌ "SGT Value" input field
- ❌ "SGT Name" input field

**To:**
- ✅ "Policy Recommendation" section
  - Recommended SGT for cluster
  - Policy conditions (AD groups, device types, etc.)
  - Impact analysis (how many devices affected)
  - "Generate ISE Policy" button

### New Policy Recommendations Page

**Create:**
- List all policy recommendations
- Current vs recommended comparison
- Policy export functionality
- Deployment status tracking

## Implementation Phases

### Phase 1: Remove Direct SGT Editing (Immediate - Critical)
- [ ] Remove SGT editing from `DeviceDetailModal`
- [ ] Remove SGT editing from `GroupDetailModal`
- [ ] Deprecate `PUT /api/devices/{id}` with `sgt_value`
- [ ] Add documentation/warnings about ISE policy model

**Status**: 🔴 Critical - Must be done before production

### Phase 2: Policy Recommendation Framework (Short-term)
- [ ] Create `PolicyRecommendation` data model
- [ ] Build recommendation engine (cluster → SGT → policy conditions)
- [ ] Generate policy rule recommendations
- [ ] Create UI for displaying recommendations

**Timeline**: 2-3 weeks

### Phase 3: ISE Policy Export (Short-term)
- [ ] ISE authorization policy configuration generator
- [ ] Export in ISE-compatible format
- [ ] Policy impact analysis
- [ ] Deployment guide generation

**Timeline**: 2-3 weeks

### Phase 4: ISE pxGrid Integration (Medium-term)
- [ ] pxGrid subscriber for session updates
- [ ] Store current ISE SGT assignments
- [ ] Display "Current ISE Assignment" in UI
- [ ] Compare recommendations vs ISE assignments

**Timeline**: 4-6 weeks

### Phase 5: Policy Deployment Integration (Long-term)
- [ ] ISE ERS API integration
- [ ] Automated policy deployment
- [ ] Policy change tracking
- [ ] Rollback capability

**Timeline**: 6-8 weeks

## References

- See `docs/ISE_SGT_ASSIGNMENT.md` for detailed ISE SGT assignment architecture
- See `docs/CLARION_ISE_WORKFLOW.md` for workflow scenarios (greenfield, existing ISE, incremental)
- See `docs/CLUSTER_ASSIGNMENT_WORKFLOW.md` for how cluster assignment changes trigger policy recommendations
- [Cisco ISE Authorization Policies](https://www.cisco.com/c/en/us/td/docs/security/ise/2-7/admin_guide/b_ise_admin_guide_27/b_ise_admin_guide_27_chapter_010001.html)
- [ISE pxGrid Integration](https://www.cisco.com/c/en/us/td/docs/security/ise/2-7/admin_guide/b_ise_admin_guide_27/b_ise_admin_guide_27_chapter_011010.html)
- [ISE ERS API](https://www.cisco.com/c/en/us/td/docs/security/ise/3-0/api_ref_guide/api_ref_book.html)

