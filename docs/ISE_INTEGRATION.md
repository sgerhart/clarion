# Cisco ISE Integration Architecture

## Overview

This document explains how Clarion integrates with Cisco Identity Services Engine (ISE) for Security Group Tag (SGT) assignment recommendations.

**Clarion's Purpose**: Help users understand what SGTs should be assigned to users and devices. Clarion analyzes network behavior, provides recommendations, and can either push policies to ISE (automated) or export policy configurations for manual creation. Clarion doesn't handle authentication flows - that's ISE's job. Clarion helps users on their TrustSec journey, whether they're just starting (greenfield) or already down the path (brownfield).

**Greenfield vs Brownfield Deployments**:
- **Greenfield**: Starting TrustSec from scratch - no existing SGTs or policies in ISE
- **Brownfield**: Existing TrustSec deployment - SGTs, authorization profiles, and policies already configured in ISE
- Clarion supports both scenarios by syncing existing ISE configuration and recommending existing SGTs when appropriate

## ISE SGT Assignment Model

### Key Principle: Policy-Based Assignment

**Critical Understanding**: ISE assigns SGTs through **authorization policies**, not by directly setting SGT values on devices. This fundamental principle must guide all Clarion-ISE integration.

## User SGT vs Device SGT Precedence and Assignment Model

**Key Principle: User SGT Takes Precedence Over Device SGT**

When a user authenticates to a device (computer, laptop, etc.), the user's SGT takes precedence over the device's SGT. This is fundamental to ISE's authorization model:

1. **Device-Level SGT (Initial State)**: 
   - User devices (computers, laptops) start with device-level SGT assignments
   - These are based on device characteristics, ISE endpoint profiles, or MAB (MAC Authentication Bypass)

2. **User SGT Takes Over (On Authentication)**:
   - When a user logs into the device, ISE assigns the user's SGT
   - The user's SGT overrides the device SGT for the duration of the session
   - This ensures users get appropriate access based on their identity, not just their device

3. **User SGT Assignment Strategy:**
   - **Primary Approach (Lead with AD Groups)**: Users are assigned SGTs based on their AD group memberships - this is the baseline and starting point
   - **Security Enhancement via Traffic Analysis**: NetFlow data reveals actual network access patterns, enabling Clarion to suggest more secure SGT assignments when traffic patterns differ from AD group expectations
   - **Critical Understanding**: To recommend appropriate SGTs, we must understand what network resources each SGT will have access to - this requires analyzing NetFlow data to see actual communication patterns

### Clarion's Role in User SGT Recommendations

**Core Principle: Lead with AD Groups, Enhance with Traffic Analysis for Security**

Clarion uses NetFlow data to analyze actual user access patterns and recommend more secure SGT assignments:

1. **Baseline: AD Group-Based Assignments**
   - Users are initially assigned SGTs based on their AD group memberships
   - This is the organizational baseline and starting point
   - Example: User in "Engineering-Users" AD group → Assigned User SGT 10 (Engineering)

2. **Security Analysis: Compare AD Groups vs Actual Access Patterns**
   - NetFlow data reveals what network resources users actually access
   - Compare expected access (based on AD group) vs actual access (based on NetFlow)
   - Identify discrepancies that may indicate security concerns or misalignment

3. **Secure SGT Recommendations**
   - Suggest SGT assignments that better match actual access needs
   - Recommend more restrictive SGTs when actual access is narrower than AD group suggests
   - Flag users whose access patterns suggest they may need custom SGT policies

**Why NetFlow Data is Critical:**
- NetFlow shows actual communication patterns: which systems users connect to, which ports/services they use
- Understanding actual access patterns is essential for recommending appropriate SGTs
- SGT recommendations must consider what resources each SGT will have access to based on the TrustSec matrix
- Traffic analysis reveals if users are accessing resources outside their expected scope (security review)

**Example Security Scenario:**
- User is in "Engineering-Users" AD group → Currently assigned User SGT 10 (Engineering)
- NetFlow analysis reveals user primarily accesses:
  - Finance systems (SGT 20) - 60% of traffic
  - Marketing tools (SGT 30) - 30% of traffic  
  - Engineering resources (SGT 10) - 10% of traffic
- **Security Recommendation**: User's actual access pattern suggests they should have a different SGT or custom policy that better reflects their role. This may indicate:
  - User's AD group membership needs review (should they be in Finance-Users instead?)
  - User requires custom user SGT policy with appropriate access
  - Security review needed - why is an Engineering user accessing Finance systems?

## Previous: User SGT vs Device SGT Precedence (Detailed Technical Notes)

**Critical Understanding**: ISE can assign SGTs to both **users** and **devices** in the same authorization policy result. When both are assigned, **User SGT takes precedence** over Device SGT for user-initiated traffic.

### Precedence Rules

1. **User SGT takes precedence** over Device SGT for user-initiated traffic
   - **User SGT** is applied to traffic initiated by the authenticated user
   - **Device SGT** applies only to device-initiated traffic (management, device services, unauthenticated devices)
   - For user traffic, the **User SGT is what gets enforced** in the TrustSec matrix

2. **Order of Operations**:
   ```
   User authenticates on Device
     ↓
   ISE evaluates authorization policies
     ↓
   Policy can assign:
     - User SGT (based on user identity, AD groups, user attributes)
     - Device SGT (based on device profile, device type, MAC)
     ↓
   Result:
     - User-initiated traffic → User SGT (if assigned) [HIGHEST PRECEDENCE]
     - Device-initiated traffic → Device SGT (if no user SGT or for device-only scenarios)
   ```

3. **When Each SGT Type Applies**:
   - **User SGT**: User authentication (802.1X, Web Auth, VPN), AD groups, user attributes
   - **Device SGT**: MAB, non-authenticating devices (printers, IoT), device management

4. **Implications for Clarion's Recommendations**:
   - For user-authenticated devices → Recommend **User SGT assignment** policies (based on AD groups)
   - For device-only scenarios (MAB, printers, IoT) → Recommend **Device SGT assignment** policies
   - Clarion's job is to recommend the **correct SGT type** - ISE handles the actual assignment and authentication flows


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

**Core Purpose**: Clarion helps users understand **what SGT should be assigned** to users and devices. Clarion analyzes network behavior, provides recommendations, and supports both automated policy deployment to ISE and manual policy export. Clarion doesn't handle authentication flows - that's ISE's job.

### What Clarion Does

1. **Categorization & Recommendation**
   - Analyze network traffic and device behavior
   - Categorize devices into logical groups
   - Recommend appropriate SGTs for each group (User SGT or Device SGT)
   - Generate ISE policy recommendations with appropriate conditions
   - Help users understand their TrustSec segmentation strategy

2. **Policy Generation**
   - Generate ISE authorization policy configurations
   - Suggest policy conditions (AD groups, device types, etc.)
   - Recommend User SGT policies for user-authenticated devices, Device SGT policies for device-only scenarios
   - Provide policy justification and impact analysis

3. **Current State Display** (Future: via pxGrid)
   - Show what SGT ISE is currently assigning
   - Display whether User SGT or Device SGT is assigned
   - Compare Clarion's recommendations vs current ISE assignments

4. **Policy Deployment** (Two Options)
   - **Option A: Automated Deployment** - Push policies directly to ISE via ISE ERS API (or pxGrid if supported)
   - **Option B: Manual Deployment** - Export policy configurations (JSON, XML, CLI) and deployment guides for manual creation in ISE
   - Support both workflows depending on user preference and ISE integration capabilities

### What Clarion Does NOT Do

1. **Direct SGT Assignment**
   - ❌ Cannot directly set `device.sgt_value = 10`
   - ❌ ISE will override on next authentication
   - ❌ Not aligned with ISE architecture

2. **Bypass ISE Policy Engine**
   - ❌ Cannot assign SGTs independently of ISE
   - ❌ Must work through ISE authorization policies
   - ❌ Must respect ISE's policy-based model

## User Database and User-Device Association

### Overview

Clarion needs to build and maintain a user database and associate users with devices to make proper User SGT recommendations. Users authenticate on devices, and understanding this relationship is critical for policy recommendations.

### Data Sources

**Primary Sources (Initial Implementation):**
1. **ISE (via pxGrid)** - Provides user authentication sessions and real-time user-to-device associations
2. **Active Directory (AD)** - Provides user details, AD group memberships, and organizational context

**Future Sources:**
- AD logs (for historical associations)
- LDAP queries (for user directory information)
- ISE ERS API (for user/endpoint data)

### User Database Schema

The user database should store:

**Users Table:**
- `user_id` (Primary Key) - Unique user identifier (AD SID or ISE internal ID)
- `username` - Username (e.g., "jdoe")
- `email` - User email address
- `display_name` - Full name
- `department` - Department/OU
- `title` - Job title
- `is_active` - Boolean (user account status)
- `first_seen` - First time user was observed
- `last_seen` - Last time user authenticated
- `source` - Data source ("ise", "ad", "ldap")

**User-Device Associations Table:**
- `association_id` (Primary Key)
- `user_id` - Foreign key to users table
- `endpoint_id` - MAC address (Foreign key to endpoints)
- `ip_address` - IP address at time of association
- `association_type` - "ise_session", "ad_computer", "manual"
- `session_id` - ISE session ID (if from ISE)
- `first_associated` - First time this user-device association was seen
- `last_associated` - Most recent association timestamp
- `is_active` - Boolean (current active association)

**AD Group Memberships Table:**
- `membership_id` (Primary Key)
- `user_id` - Foreign key to users table
- `group_id` - AD group SID or name
- `group_name` - AD group display name
- `added_at` - When membership was added
- `last_verified` - Last time membership was verified

### User-Device Association Resolution

**Resolution Chain:**
```
1. ISE Session Data (via pxGrid)
   MAC Address → ISE Session → Username → User ID
   
2. AD Integration
   Username → AD User Lookup → User Details (email, department, groups)
   
3. Association Storage
   User ID + MAC Address → User-Device Association
```

**Resolution Logic:**
1. **From ISE Sessions** (Real-time, via pxGrid):
   - ISE session contains: `mac_address`, `username`, `ip_address`, `session_id`
   - Create/update user record from session username
   - Create user-device association linking user_id to endpoint_id (MAC)
   - Update `last_seen` timestamp

2. **From Active Directory** (Periodic sync):
   - Query AD for user details (email, department, title, groups)
   - Update user records with AD information
   - Store AD group memberships
   - Link AD computer objects to devices (if computer_name matches device hostname)

3. **Association Confidence**:
   - **High confidence**: ISE session with authenticated user
   - **Medium confidence**: AD computer object matches device
   - **Low confidence**: Historical association or manual mapping

### Implementation Approach

**Phase 1: Database Schema (Current/Future)**
- ✅ `identity` table exists with basic user_name field
- ⚠️ Need dedicated `users` table for user details
- ⚠️ Need `user_device_associations` table for tracking relationships
- ⚠️ Need `ad_group_memberships` table for group tracking

**Phase 2: Data Ingestion**
1. **ISE pxGrid Integration**:
   - Subscribe to `com.cisco.ise.session` topic
   - Extract: username, mac_address, ip_address, session_id
   - Create/update user records
   - Create user-device associations

2. **AD Integration**:
   - Periodic LDAP queries for user details
   - Query AD group memberships
   - Update user records with AD data
   - Sync AD group memberships

**Phase 3: Association Logic**
- Build resolution engine that combines ISE session data + AD data
- Track association confidence levels
- Handle multiple users on same device (time-based associations)
- Handle device reassignments (user leaves, new user authenticates)

### Policy Recommendation Impact

**User SGT Recommendations:**
- **Primary Approach**: Lead with AD group memberships to recommend User SGT policies
- **Security Enhancement**: Use NetFlow data to analyze actual access patterns and suggest more secure SGT assignments
- **Critical Analysis**: Compare expected access (based on AD group) vs actual access (based on NetFlow) to identify:
  - Users whose actual access is more restricted than their AD group suggests (may need more restrictive SGT)
  - Users whose actual access is broader than their AD group suggests (security review needed)
  - Discrepancies that indicate potential misalignment or security concerns
- **Access Pattern Understanding**: NetFlow data is essential to understand what resources each SGT will have access to, enabling informed recommendations that consider the TrustSec matrix context
- Example: User in "Engineering-Users" AD group → Baseline: Recommend User SGT 10 (Engineering). If NetFlow shows user primarily accesses Finance systems, suggest reviewing AD group membership or recommending a different/custom SGT policy

**Device SGT Recommendations:**
- For devices without user associations (MAB, printers, IoT) → Recommend Device SGT policies
- For device-only scenarios where users don't authenticate

### Current State vs Target State

**Current State:**
- Basic `identity` table with `user_name` field
- Data loaded from CSV files for testing
- Identity resolution via `IdentityResolver` class (works with in-memory DataFrames)

**Target State:**
- Dedicated `users` table in database
- `user_device_associations` table for tracking relationships
- Real-time updates from ISE pxGrid
- Periodic sync from AD
- Persistent user database that survives data reloads

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
│  3. Policy Deployment                                       │
│     • Option A: Push policies to ISE (ERS API/pxGrid)      │
│     • Option B: Export policy configs for manual creation  │
│     • Support both automated and manual workflows          │
│                                                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ Policy Recommendations
                      │ (Automated Push OR Manual Export)
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

4. Policy Deployment (User Choice)
   
   **Option A: Automated Deployment**
   ├─> Push policy directly to ISE via ISE ERS API (or pxGrid if supported)
   ├─> Verify deployment
   └─> Monitor policy enforcement
   
   **Option B: Manual Deployment**
   ├─> Generate ISE authorization policy configuration
   ├─> Export in ISE-compatible format (JSON, XML, CLI)
   ├─> Generate deployment guide
   └─> User manually creates policy in ISE GUI

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

# ✅ Recommended: Policy export (for manual deployment)
GET /api/policy/recommendations/{id}/ise-config?format=json|xml|cli
# Returns ISE authorization policy configuration for manual creation

# ✅ Recommended: Automated policy deployment
POST /api/policy/recommendations/{id}/deploy
{
  "deployment_method": "ers_api",  # or "pxgrid" if supported
  "ise_server": "ise.example.com",
  "verify": true
}
# Pushes policy directly to ISE

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
  - **"Deploy to ISE" button** (automated deployment)
  - **"Export Policy Config" button** (manual deployment - shows JSON/XML/CLI)
- ✅ "Policy Recommendation" section (shown when cluster assignment changes)
  - Old SGT vs New SGT
  - Recommended policy rule
  - Impact analysis
  - **"Deploy to ISE" button** (automated deployment)
  - **"Export Policy Config" button** (manual deployment - shows JSON/XML/CLI)

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
  - **"Deploy to ISE" button** (automated deployment)
  - **"Export Policy Config" button** (manual deployment - shows JSON/XML/CLI)

### New Policy Recommendations Page

**Create:**
- List all policy recommendations
- Current vs recommended comparison
- **Policy deployment options**: Automated (push to ISE) or Manual (export config)
- Deployment status tracking
- Policy configuration export (JSON, XML, CLI formats)

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

### Phase 3: ISE Policy Export & Deployment (Short-term)
- [ ] ISE authorization policy configuration generator
- [ ] Export in ISE-compatible format (JSON, XML, CLI)
- [ ] Policy impact analysis
- [ ] Deployment guide generation (for manual deployment)
- [ ] ISE ERS API integration (for automated deployment)
- [ ] Support both automated and manual deployment workflows

**Timeline**: 3-4 weeks

### Phase 4: User Database and ISE pxGrid Integration (Medium-term)
- [ ] Create `users` table in database schema
- [ ] Create `user_device_associations` table for tracking user-device relationships
- [ ] Create `ad_group_memberships` table for group tracking
- [ ] ISE pxGrid subscriber for session updates
- [ ] Extract user information from ISE sessions (username, mac_address, ip_address)
- [ ] Store user records and user-device associations from ISE sessions
- [ ] AD integration (LDAP queries) for user details and group memberships
- [ ] User-device association resolution engine
- [ ] Store current ISE SGT assignments
- [ ] Display "Current ISE Assignment" in UI
- [ ] Compare recommendations vs ISE assignments

**Timeline**: 6-8 weeks

### Phase 5: Policy Deployment Enhancement (Long-term)
- [ ] Enhanced automated policy deployment (pxGrid support if applicable)
- [ ] Policy change tracking and audit logging
- [ ] Rollback capability
- [ ] Deployment verification and health checks
- [ ] Bulk policy deployment workflows

**Timeline**: 4-6 weeks

## References

- See `docs/ISE_SGT_ASSIGNMENT.md` for detailed ISE SGT assignment architecture
- See `docs/CLARION_ISE_WORKFLOW.md` for workflow scenarios (greenfield, existing ISE, incremental)
- See `docs/CLUSTER_ASSIGNMENT_WORKFLOW.md` for how cluster assignment changes trigger policy recommendations
- [Cisco ISE Authorization Policies](https://www.cisco.com/c/en/us/td/docs/security/ise/2-7/admin_guide/b_ise_admin_guide_27/b_ise_admin_guide_27_chapter_010001.html)
- [ISE pxGrid Integration](https://www.cisco.com/c/en/us/td/docs/security/ise/2-7/admin_guide/b_ise_admin_guide_27/b_ise_admin_guide_27_chapter_011010.html)
- [ISE ERS API](https://www.cisco.com/c/en/us/td/docs/security/ise/3-0/api_ref_guide/api_ref_book.html)

