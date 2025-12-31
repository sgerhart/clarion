# Cisco ISE Complete Configuration Guide

## Overview

This guide provides comprehensive configuration steps for Cisco ISE in the lab environment, including all components needed for Clarion integration.

## Prerequisites

- ISE 3.x installed and accessible
- AD domain controller configured and accessible
- ISE joined to AD domain (see CML_LAB_SETUP.md)

## Step 1: Initial ISE Setup

### 1.1 Access ISE Admin Portal

1. Open browser: `https://192.168.110.15`
2. Login with admin credentials
3. Accept self-signed certificate warning (for lab)

### 1.2 Verify Node Status

1. Navigate to **Administration → System → Deployment**
2. Verify node status is **Registered** and **Enabled**
3. For standalone: Node should show as **Primary Admin Node**

## Step 2: Active Directory Integration

### 2.1 Add AD as Identity Source

1. Navigate to **Administration → Identity Management → External Identity Sources**
2. Click **Add** → **Active Directory**
3. Configure:

   **General Settings:**
   - **Name**: `lab.clarion.local`
   - **Description**: `Lab Active Directory Domain`

   **Connection Settings:**
   - **Domain**: `lab.clarion.local`
   - **Username**: `Administrator`
   - **Password**: `C!sco#123` (or your domain admin password)
   - **Base DN**: `DC=lab,DC=clarion,DC=local`
   - **AD Forest**: `lab.clarion.local`

   **Advanced Settings:**
   - **Enable**: **Retrieve groups from this identity source**
   - **Enable**: **Enable this identity source**
   - **Group Attribute**: `memberOf` (default)
   - **User Attribute**: `sAMAccountName` (default)

4. Click **Test Connection** → Should show "Connection successful"
5. Click **Join Domain** → Wait for completion (may take a few minutes)
6. Click **Save**

### 2.2 Verify AD Integration

1. Navigate to **Administration → Identity Management → Groups**
2. Click **Add** → **Select Groups**
3. Search for AD groups (e.g., "Engineering-Users")
4. Verify groups are visible and can be selected
5. Add groups to ISE identity groups if needed

### 2.3 Configure Identity Source Sequence

1. Navigate to **Administration → Identity Management → Identity Source Sequences**
2. Edit default sequence or create new:
   - **Name**: `Lab-Identity-Source-Sequence`
   - **Identity Sources**: Add `lab.clarion.local` (AD)
   - **Order**: AD first, then Internal Users (if needed)
3. Click **Save**

## Step 3: pxGrid Configuration

### 3.1 Enable pxGrid Services

1. Navigate to **Administration → pxGrid Services → Settings**
2. Configure:

   **General Settings:**
   - **Enable pxGrid Services**: ✅ Enabled
   - **pxGrid Domain**: `xgrid.cisco.com` (default)
   - **Description**: `Lab pxGrid Services`

   **Certificate Settings:**
   - **Certificate**: Auto-generate (or upload existing)
   - **Certificate Validity**: 365 days (default)

   **REST API Settings:**
   - **Enable pxGrid REST API**: ✅ Enabled
   - **REST API Port**: `8910` (default)

3. Click **Save**
4. Wait for services to start (may take 1-2 minutes)

### 3.2 Verify pxGrid Status

1. Navigate to **Administration → pxGrid Services → Settings**
2. Verify status shows **Enabled** and **Running**
3. Check **Client Management** → Should show no clients initially (Clarion will appear after connection)

### 3.3 Configure pxGrid Client Approval

1. Navigate to **Administration → pxGrid Services → Client Management → Clients**
2. Set approval mode:
   - **Auto-approve**: For lab (optional, not recommended for production)
   - **Manual approval**: Recommended (requires manual approval in ISE GUI)

## Step 4: Security Group Tags (SGTs)

### 4.1 Create Department SGTs

1. Navigate to **Policy → Policy Elements → Results → Security Group Access → Security Groups**
2. Click **Add** for each SGT:

   **Engineering-Users:**
   - **Name**: `Engineering-Users`
   - **Value**: `10`
   - **Description**: `Engineering department users`

   **Finance-Users:**
   - **Name**: `Finance-Users`
   - **Value**: `20`
   - **Description**: `Finance department users`

   **HR-Users:**
   - **Name**: `HR-Users`
   - **Value**: `30`
   - **Description**: `HR department users`

   **Sales-Users:**
   - **Name**: `Sales-Users`
   - **Value**: `40`
   - **Description**: `Sales department users`

   **IT-Users:**
   - **Name**: `IT-Users`
   - **Value**: `50`
   - **Description**: `IT department users`

3. Click **Submit** for each SGT

### 4.2 Create Infrastructure SGTs

Create additional SGTs for infrastructure:

- **Servers**: Value `60`
- **Network-Devices**: Value `70`
- **IoT-Devices**: Value `80`
- **Guests**: Value `90`

### 4.3 Verify SGTs

1. Navigate to **Policy → Policy Elements → Results → Security Group Access → Security Groups**
2. Verify all SGTs are listed
3. Check values are unique and sequential

## Step 5: Authorization Profiles

### 5.1 Create Department Authorization Profiles

1. Navigate to **Policy → Policy Elements → Results → Authorization → Authorization Profiles**
2. Click **Add** for each department:

   **Profile-Engineering-Users:**
   - **Name**: `Profile-Engineering-Users`
   - **Description**: `Assigns Engineering-Users SGT`
   - **Security Group**: Select `Engineering-Users` (SGT 10)
   - **Access Type**: `ACCESS_ACCEPT`

   **Profile-Finance-Users:**
   - **Name**: `Profile-Finance-Users`
   - **Security Group**: Select `Finance-Users` (SGT 20)

   **Profile-HR-Users:**
   - **Name**: `Profile-HR-Users`
   - **Security Group**: Select `HR-Users` (SGT 30)

   **Profile-Sales-Users:**
   - **Name**: `Profile-Sales-Users`
   - **Security Group**: Select `Sales-Users` (SGT 40)

   **Profile-IT-Users:**
   - **Name**: `Profile-IT-Users`
   - **Security Group**: Select `IT-Users` (SGT 50)

3. Click **Submit** for each profile

## Step 6: Authorization Policies

### 6.1 Create Authorization Policy Rules

1. Navigate to **Policy → Authorization**
2. Create policy rules (order matters - more specific first):

   **Rule 1: Engineering-Users-Policy**
   - **Rule Name**: `Engineering-Users-Policy`
   - **Conditions**:
     - `User AD Groups EQUALS Engineering-Users`
   - **Result**: `Profile-Engineering-Users`
   - **Status**: Enabled

   **Rule 2: Finance-Users-Policy**
   - **Rule Name**: `Finance-Users-Policy`
   - **Conditions**:
     - `User AD Groups EQUALS Finance-Users`
   - **Result**: `Profile-Finance-Users`

   **Rule 3: HR-Users-Policy**
   - **Rule Name**: `HR-Users-Policy`
   - **Conditions**:
     - `User AD Groups EQUALS HR-Users`
   - **Result**: `Profile-HR-Users`

   **Rule 4: Sales-Users-Policy**
   - **Rule Name**: `Sales-Users-Policy`
   - **Conditions**:
     - `User AD Groups EQUALS Sales-Users`
   - **Result**: `Profile-Sales-Users`

   **Rule 5: IT-Users-Policy**
   - **Rule Name**: `IT-Users-Policy`
   - **Conditions**:
     - `User AD Groups EQUALS IT-Users`
   - **Result**: `Profile-IT-Users`

   **Default Rule:**
   - **Rule Name**: `Default`
   - **Result**: `DenyAccess` (or PermitAccess if testing)

3. Click **Save** after each rule

### 6.2 Verify Policy Order

1. Verify rules are in correct order (most specific first)
2. Default rule should be last
3. Policies are evaluated top-to-bottom

## Step 7: Network Devices (Optional)

### 7.1 Add Network Devices

If using switches/routers in CML:

1. Navigate to **Administration → Network Resources → Network Devices**
2. Click **Add** for each device:

   **Switch-1:**
   - **Name**: `Switch-1`
   - **IP Address**: `192.168.110.20`
   - **Device Type**: `Switch`
   - **RADIUS Authentication Settings**:
     - **Shared Secret**: `C!sco#123`
     - **Enable Key Wrap**: No (for lab)
   - **TrustSec Settings**:
     - **Enable TrustSec**: ✅ Enabled
     - **Device Authentication**: `Do Not Include Device ID`
   - **Model Name**: `Catalyst 9300` (or your model)

   **Switch-2:**
   - **Name**: `Switch-2`
   - **IP Address**: `192.168.110.21`
   - Same configuration as Switch-1

3. Click **Submit** for each device

### 7.2 Configure Device Groups (Optional)

1. Navigate to **Administration → Network Resources → Device Groups**
2. Create groups:
   - **Switches**: Add Switch-1, Switch-2
   - **Routers**: Add routers if using

## Step 8: Endpoint Identity Groups (Optional)

### 8.1 Create Endpoint Groups

1. Navigate to **Policy → Policy Elements → Conditions → Endpoints → Endpoint Identity Groups**
2. Create groups for device types:
   - **Workstations**
   - **Servers**
   - **IoT-Devices**
   - **Network-Devices**

## Step 9: Verification and Testing

### 9.1 Test Authentication

1. Navigate to **Operations → Authentications**
2. Trigger a test authentication (from switch or test client)
3. Verify:
   - Authentication succeeds
   - User is authenticated against AD
   - SGT is assigned based on AD group
   - Authorization profile is applied

### 9.2 Test pxGrid Connection

1. From Clarion, configure pxGrid connector
2. Create pxGrid client account
3. In ISE, navigate to **Administration → pxGrid Services → Client Management → Clients**
4. Verify client appears (may show as PENDING)
5. Click **Approve** to approve the client
6. Return to Clarion and test connection → Should succeed

### 9.3 Monitor pxGrid Events

1. Navigate to **Operations → pxGrid → Subscriptions**
2. Verify Clarion client is subscribed to topics:
   - `com.cisco.ise.session`
   - `com.cisco.ise.endpoint`

### 9.4 Verify SGT Assignment

1. Navigate to **Operations → Authentications**
2. View recent authentications
3. Verify SGT is assigned in authentication details
4. Navigate to **Monitor → TrustSec → Security Group Tags**
5. Verify SGT assignments are visible

## Step 10: Advanced Configuration (Optional)

### 10.1 Configure Profiling

1. Navigate to **Policy → Profiling**
2. Enable profiling policies
3. Configure device profiling rules

### 10.2 Configure Posture

1. Navigate to **Policy → Posture**
2. Configure posture policies (if needed)

### 10.3 Configure Guest Access

1. Navigate to **Policy → Guest Access**
2. Configure guest portal (if needed)

## Troubleshooting

### AD Integration Issues

**Problem**: Cannot join domain
- Verify AD is accessible from ISE: `nslookup lab.clarion.local`
- Check AD credentials
- Verify firewall allows LDAP (389) and Kerberos (88) ports
- Check ISE logs: **Operations → Reports → Reports → System Reports → Admin Access**

**Problem**: Groups not visible
- Verify "Retrieve groups from this identity source" is enabled
- Check Base DN is correct
- Verify AD groups exist

### pxGrid Issues

**Problem**: pxGrid services not starting
- Check ISE services: **Administration → System → Deployment → Node → Services**
- Verify certificates are valid
- Check ISE logs

**Problem**: Client not appearing
- Verify pxGrid REST API is enabled
- Check network connectivity from Clarion to ISE port 8910
- Verify client name matches ISE configuration

### Policy Issues

**Problem**: SGT not assigned
- Verify authorization policy conditions match AD groups
- Check authorization profile has SGT configured
- Verify user is in correct AD group
- Check policy order (more specific rules first)

## Configuration Checklist

- [ ] ISE installed and accessible
- [ ] AD integrated and domain joined
- [ ] pxGrid services enabled
- [ ] SGTs created (Engineering, Finance, HR, Sales, IT)
- [ ] Authorization profiles created
- [ ] Authorization policies configured
- [ ] Network devices added (if using)
- [ ] Test authentication successful
- [ ] pxGrid client approved
- [ ] Clarion can connect to ISE ERS API
- [ ] Clarion can connect to ISE pxGrid

## Next Steps

1. Configure Clarion connectors (see CML_LAB_SETUP.md)
2. Test end-to-end integration
3. Generate test traffic
4. Monitor events in Clarion UI

