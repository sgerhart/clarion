# Cluster Assignment Workflow & Policy Recommendations

## Overview

This document explains the relationship between cluster assignment changes and SGT policy recommendations. It clarifies why users should be able to manually assign devices to clusters, and how this triggers ISE policy recommendations.

## Key Distinction

### ❌ Direct SGT Editing (Not Allowed)
- User directly changes `device.sgt_value = 12`
- Bypasses categorization engine
- Doesn't work with ISE (will be overridden on next authentication)
- **Action**: Removed from UI/API

### ✅ Cluster Assignment Changes (Allowed)
- User moves device from Cluster A → Cluster B
- Represents user override of categorization
- Triggers policy recommendation: "Generate ISE policy to assign Cluster B's SGT"
- **Action**: Keep this functionality

## Workflow: Cluster Assignment → Policy Recommendation

```
┌─────────────────────────────────────────────────────────────┐
│              User Action: Move Device to New Cluster        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User manually assigns device to different cluster          │
│  Example: Move device from Cluster 5 (SGT 10)               │
│                       to Cluster 8 (SGT 12)                  │
│                                                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ Device moved to Cluster 8
                      ↓
┌─────────────────────────────────────────────────────────────┐
│            Clarion Detects Cluster Assignment Change         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Device now in Cluster 8                                 │
│  2. Cluster 8 has recommended SGT 12                        │
│  3. Device currently has SGT 10 (from previous cluster)     │
│  4. Change detected: SGT recommendation changed              │
│                                                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ Policy Recommendation Triggered
                      ↓
┌─────────────────────────────────────────────────────────────┐
│           Generate ISE Policy Recommendation                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Clarion analyzes device attributes:                        │
│  - User: john.doe@company.com                              │
│  - AD Groups: ["Engineering", "All-Employees"]             │
│  - Device Type: Corporate Laptop                           │
│  - ISE Profile: Windows-10-Pro                             │
│                                                             │
│  Generates policy recommendation:                           │
│  "Move user to AD group 'Engineering-Servers'               │
│   OR update device profile to 'Server-Profile'              │
│   → ISE will assign SGT 12"                                │
│                                                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ User Reviews Recommendation
                      ↓
┌─────────────────────────────────────────────────────────────┐
│              Policy Export & Deployment                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. User reviews policy recommendation                      │
│  2. User accepts/modifies recommendation                    │
│  3. Export ISE authorization policy configuration           │
│  4. Deploy to ISE (manually or via API)                    │
│                                                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ ISE Policy Applied
                      ↓
┌─────────────────────────────────────────────────────────────┐
│              ISE Assigns New SGT                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  On next authentication:                                    │
│  - User/device matches new policy conditions                │
│  - ISE assigns SGT 12 (from policy)                         │
│  - SGT propagated through network                           │
│                                                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ pxGrid Sync
                      ↓
┌─────────────────────────────────────────────────────────────┐
│            Clarion Updates Display                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  - pxGrid receives session update                           │
│  - Clarion stores: device → SGT 12 (from ISE)               │
│  - UI displays: "Current ISE Assignment: SGT 12"           │
│  - UI shows: "Aligned with recommendation"                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Why Allow Cluster Assignment Changes?

### 1. User Override of Categorization
- Categorization engine is not always perfect
- Users may have domain knowledge that engine lacks
- Manual cluster assignment = user correction/refinement

### 2. Triggers Policy Recommendations
- Cluster change → New SGT recommendation → Policy recommendation
- Provides clear path to implement the change in ISE
- Generates actionable ISE policy configurations

### 3. Flexible Workflow
- Users can:
  - Accept categorization engine's assignment
  - Manually override cluster assignment
  - Review policy recommendations
  - Deploy to ISE when ready

### 4. ISE Integration Alignment
- Cluster assignment = intent to change categorization
- SGT change = must happen via ISE policy
- Policy recommendation = bridge between intent and implementation

## Example Scenarios

### Scenario 1: User Corrects Categorization

**Initial State:**
- Device categorized as "Corporate Laptop" (Cluster 5, SGT 10)
- User knows device is actually a "Development Server"
- User moves device to "Servers" cluster (Cluster 8, SGT 12)

**Clarion Response:**
- Detects cluster assignment change
- Generates policy recommendation:
  - "Update device profile to 'Server-Profile' → ISE assigns SGT 12"
  - OR "Move device to AD group 'Servers' → ISE assigns SGT 12"

**User Action:**
- Reviews recommendation
- Exports ISE policy configuration
- Deploys to ISE

**Result:**
- Device gets new ISE profile/AD group
- ISE assigns SGT 12 on next authentication
- Device now properly categorized

### Scenario 2: Temporary Assignment

**Initial State:**
- Device normally in "Employee Devices" (Cluster 2, SGT 5)
- Temporary assignment to "Contractor Devices" (Cluster 7, SGT 8)

**Clarion Response:**
- Generates policy recommendation with temporary conditions
- Could include time-based conditions (if ISE supports)

**User Action:**
- Deploys temporary policy
- Sets expiration date
- ISE assigns SGT 8 for duration
- Automatically reverts after expiration

### Scenario 3: AD Group Movement

**Initial State:**
- User in "Engineering" AD group → SGT 10
- User moves device to "Management" cluster → Should have SGT 15

**Clarion Response:**
- Analyzes user's current AD groups
- Generates recommendation: "Move user to AD group 'Management' → ISE assigns SGT 15"

**User Action:**
- Moves user to "Management" AD group in AD
- ISE policy automatically assigns SGT 15 on next login
- Device properly categorized

## Implementation Requirements

### 1. Cluster Assignment Changes (Current - Keep)
- ✅ Allow manual cluster assignment in UI
- ✅ API endpoint: `PUT /api/devices/{id}` with `cluster_id`
- ✅ Update device's cluster assignment in database
- ✅ Track assignment changes (history)

### 2. Policy Recommendation Trigger (New)
- [ ] Detect when cluster assignment changes
- [ ] Compare old cluster SGT vs new cluster SGT
- [ ] If different, trigger policy recommendation generation
- [ ] Analyze device/user attributes (AD groups, device type, etc.)
- [ ] Generate policy conditions that would assign new SGT

### 3. Policy Recommendation Generation (New)
- [ ] Map cluster's recommended SGT to policy conditions
- [ ] Identify device/user attributes:
  - AD group memberships
  - Device types/profiles
  - Network attributes (VLAN, subnet)
- [ ] Generate ISE authorization policy rule
- [ ] Provide justification and impact analysis

### 4. Policy Recommendation UI (New)
- [ ] Display policy recommendations when cluster assignment changes
- [ ] Show "Pending Policy Recommendations" section
- [ ] Allow user to review, accept, modify, or reject
- [ ] Export ISE policy configurations
- [ ] Track recommendation status (pending, accepted, deployed)

## API Design

### Cluster Assignment Change (Current - Keep)

```python
PUT /api/devices/{endpoint_id}
{
  "cluster_id": 8  # ✅ Keep this - valid use case
}
```

### Policy Recommendation Generation (New)

```python
POST /api/devices/{endpoint_id}/policy-recommendation
# Triggered automatically when cluster assignment changes
# Or can be manually triggered

Response:
{
  "device_id": "12:7a:05:f0:7f:02",
  "old_cluster": 5,
  "old_sgt": 10,
  "new_cluster": 8,
  "recommended_sgt": 12,
  "policy_recommendation": {
    "name": "Move-Device-To-Server-Cluster",
    "condition": "Device:Profile EQUALS 'Server-Profile' OR AD:Group EQUALS 'Engineering-Servers'",
    "action": "Assign SGT 12",
    "justification": "Device manually moved to Server cluster. Generate policy to assign appropriate SGT."
  },
  "impact": {
    "devices_affected": 1,
    "ad_group_changes": ["Engineering-Servers"],
    "device_profile_changes": ["Server-Profile"]
  }
}
```

### List Pending Recommendations

```python
GET /api/policy/recommendations/pending
# Returns all pending policy recommendations

Response:
{
  "recommendations": [
    {
      "id": 1,
      "device_id": "12:7a:05:f0:7f:02",
      "recommended_sgt": 12,
      "policy_recommendation": {...},
      "status": "pending",
      "created_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

## UI/UX Design

### Device Detail Modal - After Cluster Assignment Change

**Show:**
- ✅ Current cluster assignment (editable)
- ✅ Recommended SGT for current cluster (read-only)
- ✅ **NEW**: "Policy Recommendation" section (if cluster changed)
  - Old SGT vs New SGT
  - Recommended policy rule
  - Justification
  - Impact analysis
  - "Generate ISE Policy" button
  - "View Recommendation Details" link

### Group/Cluster Detail Modal

**Show:**
- ✅ Current SGT recommendation for cluster (read-only)
- ✅ Policy recommendation for cluster members
- ✅ Devices in cluster with pending policy recommendations
- ✅ "Generate ISE Policy for Cluster" button

### New "Policy Recommendations" Page

**Show:**
- List of all pending policy recommendations
- Grouped by cluster assignment changes
- Status: pending, accepted, deployed
- Export functionality
- Deployment tracking

## Summary

✅ **Keep**: Cluster assignment changes (user can move devices between clusters)
❌ **Remove**: Direct SGT editing (cannot bypass cluster categorization)

**Workflow:**
1. User changes cluster assignment
2. Clarion detects change → New SGT recommendation
3. Clarion generates ISE policy recommendation
4. User reviews and exports policy
5. ISE assigns new SGT via policy

This maintains the integrity of the categorization engine while providing users with flexibility to override when needed, and ensures all SGT changes go through ISE's policy-based model.

