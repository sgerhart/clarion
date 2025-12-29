# Cisco ISE SGT Assignment Architecture

## Overview

Cisco Identity Services Engine (ISE) assigns Security Group Tags (SGTs) to devices and users through **authorization policies**, not by directly editing device SGT values. Understanding this architecture is critical for Clarion to properly integrate with ISE.

## How ISE Assigns SGTs

### 1. Dynamic SGT Assignment (Primary Method)

SGTs are assigned **dynamically** during the authentication/authorization process based on authorization policies that evaluate conditions:

#### Authentication Methods:
- **802.1X** (EAP-TLS, PEAP, etc.)
- **MAC Authentication Bypass (MAB)**
- **Web Authentication**
- **VPN Authentication**

#### Policy Evaluation Flow:
```
1. Device/User authenticates
   ↓
2. ISE evaluates authorization policies
   ↓
3. Policy matches conditions (AD groups, device type, network attributes)
   ↓
4. ISE assigns SGT specified in policy result
   ↓
5. SGT propagated to network (inline tagging or SXP)
```

#### Policy Conditions Examples:
- **AD Group Membership**: If user is member of "All-Employees" → Assign SGT 2
- **Device Type/Profile**: If device profile is "CorporatePhone" → Assign SGT 11
- **Network Attributes**: If connected to VLAN 100 → Assign SGT 10
- **Identity Attributes**: If user name contains "contractor" → Assign SGT 5

### 2. Static SGT Assignment (Secondary Method)

For devices that don't authenticate, SGTs are assigned through **static mappings**:

#### Static Mapping Methods:
- **VLAN-to-SGT**: Map VLAN 100 → SGT 10
- **Subnet-to-SGT**: Map 10.1.0.0/16 → SGT 2
- **IP Address-to-SGT**: Map 10.1.1.100 → SGT 10
- **Port Profile-to-SGT**: Map port profile "Server-Ports" → SGT 10

### 3. Active Directory Integration

ISE can assign SGTs based on AD custom attributes:
- Create custom AD attribute (e.g., "SGT")
- Set attribute value for users/groups
- ISE reads attribute during authentication
- Policy assigns SGT based on attribute value

### 4. SGT Propagation

Once assigned, SGTs are propagated through the network:
- **Inline Tagging**: SGT embedded in packet (Cisco TrustSec)
- **SXP (Security Group Tag Exchange Protocol)**: IP-to-SGT mappings shared across devices

## Implications for Clarion

### ❌ What Clarion Should NOT Do

1. **Direct SGT Editing on Devices**
   - Cannot directly set `device.sgt_value = 10`
   - ISE will override this on next authentication
   - Not aligned with ISE architecture

2. **Manual SGT Assignment**
   - Users cannot simply "change SGT" for a device
   - Must change ISE authorization policy instead

### ✅ What Clarion Should Do

1. **Policy Recommendation Engine**
   - Recommend ISE authorization policy rules
   - Suggest policy conditions (AD groups, device types, etc.)
   - Propose policy actions (assign SGT X)
   - Provide justification for recommendations

2. **Display Current ISE Assignment**
   - Show what SGT ISE is currently assigning
   - Display policy that assigned the SGT
   - Show when SGT was last assigned/changed

3. **Policy Impact Analysis**
   - When recommending SGT change, analyze impact:
     - How many devices would be affected?
     - What policies need to change?
     - What's the current policy rule?

4. **ISE Policy Export**
   - Generate ISE authorization policy configurations
   - Export policy rules in ISE-compatible format
   - Support policy deployment workflow

5. **Condition-Based Recommendations**
   - Instead of "change device SGT", recommend:
     - "Create policy: If AD group = 'HR-Users' → Assign SGT 12"
     - "Update policy: If device profile = 'CorporatePhone' → Assign SGT 11"
     - "Add condition: If VLAN = 100 → Assign SGT 10"

## Clarion Architecture Alignment

### Current State (Needs Update)

Currently, Clarion allows:
- Direct SGT value editing on devices (`DeviceDetailModal`)
- Direct SGT value editing on groups (`GroupDetailModal`)
- SGT assignment via API (`/api/devices/{id}`, `PUT` with `sgt_value`)

**Problem**: This doesn't work with ISE's policy-based model.

### Target State (Architecture Goal)

Clarion should provide:
- **Policy Recommendations**: Suggest ISE authorization policies
- **Policy Export**: Generate ISE policy configurations
- **Current Assignment Display**: Show what ISE assigned (from pxGrid sync)
- **Impact Analysis**: Analyze policy change impacts
- **Workflow Support**: Guide users through ISE policy creation

### UI/UX Changes Needed

#### Device Detail Modal
- **Remove**: Direct SGT value editing field
- **Add**: "Current ISE SGT Assignment" (read-only, from ISE)
- **Add**: "Recommended Policy Change" section with:
  - Suggested policy rule
  - Justification
  - Impact analysis
  - "Generate ISE Policy" button

#### Group Detail Modal
- **Change**: SGT editing → "Policy Recommendations"
- **Add**: "Recommended Policy for Cluster" section
- **Show**: Policy rule that would assign SGT to all cluster members

#### New Policy Recommendation Page
- List all policy recommendations
- Show current vs recommended policies
- Export ISE policy configurations
- Deploy to ISE (future integration)

## Integration with ISE pxGrid

### Data Flow (Target Architecture)

```
ISE Authorization Event
  ↓
pxGrid Session Update
  ↓
Clarion pxGrid Subscriber
  ↓
Store: endpoint_id → current_sgt_value (from ISE)
  ↓
Display in UI: "Current ISE Assignment: SGT 12"
```

### Policy Recommendation Flow

```
Clarion Categorization Engine
  ↓
Recommends: "Devices in cluster X should have SGT 12"
  ↓
Generate Policy Recommendation:
  - Condition: AD group = "HR-Users" OR device profile = "CorporatePhone"
  - Action: Assign SGT 12
  ↓
User Reviews Recommendation
  ↓
Export ISE Policy Configuration
  ↓
User Deploys to ISE (manually or via API)
  ↓
ISE Applies Policy
  ↓
pxGrid Sync: ISE assigns SGT 12 to matching devices
  ↓
Clarion Updates Display
```

## Implementation Roadmap

### Phase 1: Remove Direct SGT Editing (Immediate)
- [ ] Remove SGT value input fields from `DeviceDetailModal`
- [ ] Remove SGT value input fields from `GroupDetailModal`
- [ ] Update API endpoints to deprecate direct SGT editing
- [ ] Add warnings/notifications about ISE policy-based assignment

### Phase 2: Policy Recommendation Framework (Short-term)
- [ ] Create `PolicyRecommendation` data model
- [ ] Build recommendation engine:
  - Cluster → Recommended SGT → Policy conditions
  - Device attributes → Policy conditions
- [ ] Generate policy rule recommendations
- [ ] Create UI for displaying recommendations

### Phase 3: ISE Policy Export (Short-term)
- [ ] ISE authorization policy configuration generator
- [ ] Export in ISE-compatible format
- [ ] Policy impact analysis
- [ ] Policy deployment guide generation

### Phase 4: ISE pxGrid Integration (Medium-term)
- [ ] pxGrid subscriber for session updates
- [ ] Store current ISE SGT assignments
- [ ] Display "Current ISE Assignment" in UI
- [ ] Compare Clarion recommendations vs ISE assignments

### Phase 5: Policy Deployment Integration (Long-term)
- [ ] ISE ERS API integration for policy deployment
- [ ] Automated policy deployment workflow
- [ ] Policy change tracking
- [ ] Rollback capability

## References

- [Cisco ISE Group-Based Policy Fundamentals](https://community.cisco.com/t5/security-knowledge-base/group-based-policy-fundamentals/ta-p/3764433)
- [ISE Authorization Policies](https://www.cisco.com/c/en/us/td/docs/security/ise/2-7/admin_guide/b_ise_admin_guide_27/b_ise_admin_guide_27_chapter_010001.html)
- [ISE pxGrid Integration](https://www.cisco.com/c/en/us/td/docs/security/ise/2-7/admin_guide/b_ise_admin_guide_27/b_ise_admin_guide_27_chapter_011010.html)

