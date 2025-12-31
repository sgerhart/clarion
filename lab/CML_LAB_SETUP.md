# Cisco CML Lab Setup Guide

## Overview

This guide provides step-by-step instructions for setting up a complete lab environment using Cisco Modeling Labs (CML) to test Clarion's ISE and AD integrations. The lab includes:

- **Cisco ISE** - Identity Services Engine for network access control and TrustSec/SGT assignment
- **Active Directory** - Windows Server for user/group management
- **Clarion Server** - Main Clarion application (can run on CML or external VM)
- **Network Devices** - Switches/routers for traffic generation and NetFlow export

## Prerequisites

### CML Requirements

- **Cisco CML 2.x** installed and running
- **CML License** with sufficient node count (minimum 4-6 nodes)
- **CML Resources**:
  - RAM: 64GB+ recommended (32GB minimum)
  - CPU: 16+ cores recommended
  - Disk: 500GB+ free space
  - Network: Bridge to host network for external access

### Software Images Required

1. **Cisco ISE 3.x** (OVA/ISO)
   - Minimum: 16GB RAM, 4 vCPU, 250GB disk
   - Recommended: 32GB RAM, 8 vCPU, 250GB disk
   - Download from Cisco Software Download (requires CCO account)

2. **Windows Server 2019/2022** (ISO)
   - For Active Directory Domain Controller
   - Minimum: 4GB RAM, 2 vCPU, 40GB disk
   - Evaluation license available from Microsoft

3. **Cisco IOS/IOS-XE** (for switches/routers)
   - Catalyst 9300/9500 images (if available)
   - Or use generic router images for basic connectivity

### External Requirements

- **Clarion Server** - Can run on CML or external VM/host
  - If external: Ensure network connectivity to CML lab network
  - IP: 192.168.110.11 (or configure as needed)

## CML Lab Topology

### Network Design

```
┌─────────────────────────────────────────────────────────────────┐
│                    CML Lab Network (192.168.110.0/24)          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐      ┌─────────────────┐               │
│  │   ISE Server    │      │   AD Server     │               │
│  │  (192.168.110.15)│      │  (192.168.110.10)│               │
│  │                 │      │                 │               │
│  │ • ISE 3.x       │      │ • Windows AD   │               │
│  │ • pxGrid        │      │ • DNS           │               │
│  │ • RADIUS        │      │ • LDAP         │               │
│  └─────────────────┘      └─────────────────┘               │
│         │                         │                            │
│         │                         │                            │
│  ┌──────┴─────────────────────────┴──────┐                    │
│  │         Lab Network (192.168.110.0/24) │                    │
│  └──────┬─────────────────────────┬──────┘                    │
│         │                         │                            │
│  ┌──────▼──────┐  ┌──────────────▼──────┐                    │
│  │   Switch-1  │  │   Switch-2          │                    │
│  │  (110.20)  │  │   (110.21)          │                    │
│  │            │  │                     │                    │
│  │ • NetFlow  │  │ • NetFlow           │                    │
│  │ • TrustSec │  │ • TrustSec         │                    │
│  └────────────┘  └─────────────────────┘                    │
│                                                                 │
│  ┌─────────────────┐                                           │
│  │ Clarion Server  │  (External or CML VM)                      │
│  │  (110.11)       │                                           │
│  │                 │                                           │
│  │ • Backend API   │                                           │
│  │ • UI            │                                           │
│  │ • pxGrid Client │                                           │
│  │ • AD Connector  │                                           │
│  └─────────────────┘                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Node Configuration

| Node | Type | Image | IP Address | Resources | Purpose |
|------|------|-------|------------|-----------|---------|
| ISE | ISE 3.x | ISE OVA | 192.168.110.15 | 32GB RAM, 8 vCPU, 250GB | ISE server with pxGrid |
| AD-DC | Windows Server 2022 | Windows ISO | 192.168.110.10 | 8GB RAM, 2 vCPU, 40GB | Active Directory DC |
| Switch-1 | IOS-XE | Catalyst 9300 | 192.168.110.20 | 4GB RAM, 2 vCPU | NetFlow export, TrustSec |
| Switch-2 | IOS-XE | Catalyst 9300 | 192.168.110.21 | 4GB RAM, 2 vCPU | NetFlow export, TrustSec |
| Clarion | External VM | Ubuntu 22.04 | 192.168.110.11 | 8GB RAM, 4 vCPU | Clarion application |

**Note:** Clarion can run on CML as a Linux VM or externally. External is recommended for easier access and development.

## Step 1: CML Topology Setup

### 1.1 Create New Lab in CML

1. Open CML web interface
2. Click **"New Lab"** or **"Create Lab"**
3. Name: `Clarion-ISE-AD-Lab`
4. Description: `Lab for testing Clarion ISE and AD integrations`

### 1.2 Add Nodes

Add the following nodes:

1. **ISE Server**
   - Type: `Unmanaged Server` or `External Connector` (if using OVA)
   - Image: Upload ISE OVA or use external connector
   - Name: `ISE-Server`
   - Resources: 32GB RAM, 8 vCPU, 250GB disk

2. **AD Domain Controller**
   - Type: `Unmanaged Server`
   - Image: Windows Server 2022 ISO
   - Name: `AD-DC`
   - Resources: 8GB RAM, 2 vCPU, 40GB disk

3. **Switches** (Optional, for NetFlow/TrustSec testing)
   - Type: `IOSv` or `IOS-XE`
   - Name: `Switch-1`, `Switch-2`
   - Resources: 4GB RAM, 2 vCPU each

### 1.3 Configure Network

1. Create a **Bridge Network** connected to your host network
   - Name: `Lab-Network`
   - Subnet: `192.168.110.0/24`
   - Gateway: `192.168.110.1` (or your host gateway)

2. Connect all nodes to the bridge network

3. Configure static IPs:
   - AD-DC: `192.168.110.10`
   - Clarion: `192.168.110.11` (if on CML)
   - ISE: `192.168.110.15`
   - Switch-1: `192.168.110.20`
   - Switch-2: `192.168.110.21`

### 1.4 Start Nodes

1. Start AD-DC first (DNS dependency)
2. Wait for AD-DC to fully boot
3. Start ISE server
4. Start switches (if using)
5. Start Clarion (if on CML)

## Step 2: Active Directory Setup

### 2.1 Install Windows Server

1. Boot AD-DC node
2. Install Windows Server 2022 (Evaluation or licensed)
3. Set hostname: `AD-DC`
4. Set static IP: `192.168.110.10/24`
5. Set DNS: `127.0.0.1` (self, since it will be DNS server)

### 2.2 Install Active Directory Domain Services

```powershell
# Run PowerShell as Administrator
Install-WindowsFeature -Name AD-Domain-Services -IncludeManagementTools

# Promote to Domain Controller
Install-ADDSForest `
    -DomainName "lab.clarion.local" `
    -DomainNetbiosName "LAB" `
    -SafeModeAdministratorPassword (ConvertTo-SecureString "C!sco#123" -AsPlainText -Force) `
    -Force
```

### 2.3 Create Test Users and Groups

```powershell
# Create Organizational Units
New-ADOrganizationalUnit -Name "Users" -Path "DC=lab,DC=clarion,DC=local"
New-ADOrganizationalUnit -Name "Groups" -Path "DC=lab,DC=clarion,DC=local"

# Create Department Groups
New-ADGroup -Name "Engineering-Users" -GroupScope Global -Path "OU=Groups,DC=lab,DC=clarion,DC=local"
New-ADGroup -Name "Finance-Users" -GroupScope Global -Path "OU=Groups,DC=lab,DC=clarion,DC=local"
New-ADGroup -Name "HR-Users" -GroupScope Global -Path "OU=Groups,DC=lab,DC=clarion,DC=local"
New-ADGroup -Name "Sales-Users" -GroupScope Global -Path "OU=Groups,DC=lab,DC=clarion,DC=local"
New-ADGroup -Name "IT-Users" -GroupScope Global -Path "OU=Groups,DC=lab,DC=clarion,DC=local"

# Create Test Users
$password = ConvertTo-SecureString "Password123!" -AsPlainText -Force

New-ADUser -Name "John Engineer" -SamAccountName "jengineer" -UserPrincipalName "jengineer@lab.clarion.local" -Path "OU=Users,DC=lab,DC=clarion,DC=local" -AccountPassword $password -Enabled $true
Add-ADGroupMember -Identity "Engineering-Users" -Members "jengineer"

New-ADUser -Name "Jane Finance" -SamAccountName "jfinance" -UserPrincipalName "jfinance@lab.clarion.local" -Path "OU=Users,DC=lab,DC=clarion,DC=local" -AccountPassword $password -Enabled $true
Add-ADGroupMember -Identity "Finance-Users" -Members "jfinance"

New-ADUser -Name "Bob HR" -SamAccountName "bhr" -UserPrincipalName "bhr@lab.clarion.local" -Path "OU=Users,DC=lab,DC=clarion,DC=local" -AccountPassword $password -Enabled $true
Add-ADGroupMember -Identity "HR-Users" -Members "bhr"

New-ADUser -Name "Alice Sales" -SamAccountName "asales" -UserPrincipalName "asales@lab.clarion.local" -Path "OU=Users,DC=lab,DC=clarion,DC=local" -AccountPassword $password -Enabled $true
Add-ADGroupMember -Identity "Sales-Users" -Members "asales"

New-ADUser -Name "Admin IT" -SamAccountName "ait" -UserPrincipalName "ait@lab.clarion.local" -Path "OU=Users,DC=lab,DC=clarion,DC=local" -AccountPassword $password -Enabled $true
Add-ADGroupMember -Identity "IT-Users" -Members "ait"
```

### 2.4 Configure DNS

1. Open **DNS Manager**
2. Create forward lookup zones if needed
3. Create reverse lookup zones for 192.168.110.0/24
4. Add A records:
   - `ise-server.lab.clarion.local` → 192.168.110.15
   - `clarion-server.lab.clarion.local` → 192.168.110.11

### 2.5 Verify AD Setup

```powershell
# Test LDAP connectivity
Test-NetConnection -ComputerName localhost -Port 389

# List users
Get-ADUser -Filter *

# List groups
Get-ADGroup -Filter *
```

## Step 3: Cisco ISE Setup

### 3.1 Install ISE

1. Boot ISE node in CML
2. If using OVA: Import and configure
3. If using ISO: Install ISE 3.x
4. Set hostname: `ise-server`
5. Set static IP: `192.168.110.15/24`
6. Set DNS: `192.168.110.10` (AD-DC)
7. Set NTP: Configure time synchronization

### 3.2 Initial ISE Configuration

1. Access ISE Admin Portal: `https://192.168.110.15`
2. Complete initial setup wizard:
   - Admin username: `admin`
   - Admin password: `C!sco#123` (or your choice)
   - Node role: **Policy Administration Node (PAN)** or **Standalone**
   - Time zone: Configure appropriately

### 3.3 Join ISE to AD Domain

1. Navigate to **Administration → Identity Management → External Identity Sources**
2. Click **Add** → **Active Directory**
3. Configure:
   - **Name**: `lab.clarion.local`
   - **Domain**: `lab.clarion.local`
   - **Username**: `Administrator` (or domain admin account)
   - **Password**: `C!sco#123` (or domain admin password)
   - **Base DN**: `DC=lab,DC=clarion,DC=local`
   - **Enable**: "Retrieve groups from this identity source"
4. Click **Test Connection** → Should succeed
5. Click **Join Domain** → Wait for completion
6. Click **Save**

### 3.4 Configure pxGrid

1. Navigate to **Administration → pxGrid Services → Settings**
2. Enable **pxGrid Services**
3. Configure:
   - **pxGrid Domain**: `xgrid.cisco.com` (default)
   - **Certificate**: Auto-generate or upload
   - **Enable pxGrid REST API**: Yes
4. Click **Save**

### 3.5 Create SGTs (Security Group Tags)

Use the automated script or create manually:

**Via Script:**
```bash
cd /path/to/clarion
python scripts/setup_ise_lab.py
```

**Via ISE GUI:**
1. Navigate to **Policy → Policy Elements → Results → Security Group Access → Security Groups**
2. Click **Add** for each SGT:
   - **Engineering-Users**: Value 10
   - **Finance-Users**: Value 20
   - **HR-Users**: Value 30
   - **Sales-Users**: Value 40
   - **IT-Users**: Value 50

### 3.6 Create Authorization Profiles

1. Navigate to **Policy → Policy Elements → Results → Authorization → Authorization Profiles**
2. Create profiles for each department:
   - **Profile-Engineering-Users**: Assign SGT 10
   - **Profile-Finance-Users**: Assign SGT 20
   - **Profile-HR-Users**: Assign SGT 30
   - **Profile-Sales-Users**: Assign SGT 40
   - **Profile-IT-Users**: Assign SGT 50

### 3.7 Create Authorization Policies

1. Navigate to **Policy → Authorization**
2. Create policy rules:
   - **Rule**: Engineering-Users-Policy
     - **Conditions**: `User AD Groups EQUALS Engineering-Users`
     - **Result**: `Profile-Engineering-Users`
   - Repeat for other departments

### 3.8 Add Network Devices (Optional)

If using switches in CML:

1. Navigate to **Administration → Network Resources → Network Devices**
2. Click **Add** for each switch:
   - **Name**: `Switch-1`
   - **IP Address**: `192.168.110.20`
   - **Device Type**: `Switch`
   - **RADIUS Shared Secret**: `C!sco#123`
   - **Enable TrustSec**: Yes
3. Repeat for Switch-2

### 3.9 Verify ISE Configuration

1. **Test Authentication**:
   - Navigate to **Operations → Authentications**
   - Trigger a test authentication
   - Verify authentication succeeds

2. **Test pxGrid**:
   - Navigate to **Administration → pxGrid Services → Client Management → Clients`
   - Verify pxGrid is running
   - Note: Clients will appear when Clarion connects

3. **Verify SGTs**:
   - Navigate to **Policy → Policy Elements → Results → Security Group Access → Security Groups`
   - Verify all SGTs are created

## Step 4: Configure Clarion Connectors

### 4.1 Configure AD Connector

1. Access Clarion UI: `http://192.168.110.11:3000`
2. Navigate to **Connectors → Active Directory**
3. Configure:
   - **Domain Controller**: `192.168.110.10`
   - **Port**: `389` (LDAP) or `636` (LDAPS)
   - **Base DN**: `DC=lab,DC=clarion,DC=local`
   - **Bind DN**: `Administrator@lab.clarion.local`
   - **Bind Password**: `C!sco#123`
   - **Use SSL/TLS**: Yes (if using LDAPS)
4. Click **Test Connection** → Should succeed
5. Click **Save & Enable**

### 4.2 Configure ISE ERS API Connector

1. Navigate to **Connectors → ISE → ERS API Tab**
2. Configure:
   - **ISE URL**: `https://192.168.110.15`
   - **Username**: `admin`
   - **Password**: `C!sco#123`
   - **Verify SSL**: No (for lab with self-signed certs)
3. Click **Test Connection** → Should succeed
4. Click **Save & Enable**

### 4.3 Configure ISE pxGrid Connector

1. Navigate to **Connectors → ISE → pxGrid Tab**
2. Configure:
   - **ISE Hostname**: `192.168.110.15`
   - **Port**: `8910`
   - **Client Name**: `clarion`
   - **Username**: `admin` (for initial account creation)
   - **Password**: `C!sco#123`
   - **Use SSL**: Yes
   - **Verify SSL**: No (for lab)
   - **Authentication Method**: Username/Password (or Certificate if configured)
3. Click **Save & Enable**
4. **Approve Client in ISE**:
   - Navigate to ISE: **Administration → pxGrid Services → Client Management → Clients**
   - Find client `clarion` (or `clarion@xgrid.cisco.com`)
   - Click **Approve**
5. Return to Clarion and click **Test Connection** → Should succeed

## Step 5: Verification and Testing

### 5.1 Verify AD Integration

```bash
# Test LDAP connectivity from Clarion server
ldapsearch -H ldap://192.168.110.10 -x -D "Administrator@lab.clarion.local" -w "C!sco#123" -b "DC=lab,DC=clarion,DC=local" "(objectClass=user)"
```

### 5.2 Verify ISE Integration

```bash
# Test ISE ERS API
curl -k -u admin:C!sco#123 https://192.168.110.15/ers/config/sgt

# Test pxGrid (from Clarion)
curl http://192.168.110.11:8000/api/connectors/ise_pxgrid/status
```

### 5.3 Test End-to-End Flow

1. **User Authentication**:
   - Trigger authentication from a test endpoint
   - Verify ISE authenticates user against AD
   - Verify SGT is assigned based on AD group

2. **pxGrid Event Flow**:
   - Verify pxGrid events appear in Clarion
   - Check Clarion database for session data
   - Verify user-device associations

3. **AD User Sync**:
   - Verify AD users appear in Clarion user database
   - Verify group memberships are synced
   - Test user lookup by IP address

## Troubleshooting

### ISE Issues

**Problem**: ISE not accessible
- Check firewall rules
- Verify IP configuration
- Check ISE services: `show application status ise`

**Problem**: pxGrid not working
- Verify pxGrid services are enabled
- Check pxGrid certificates
- Verify client is approved in ISE

**Problem**: AD integration fails
- Verify ISE can reach AD (test from ISE: `nslookup lab.clarion.local`)
- Check AD credentials
- Verify domain join status in ISE

### AD Issues

**Problem**: LDAP queries fail
- Verify DNS resolution
- Check LDAP service is running
- Verify firewall allows port 389/636

**Problem**: Users not syncing
- Check AD connector configuration in Clarion
- Verify Base DN is correct
- Check bind credentials

### Network Issues

**Problem**: Nodes can't communicate
- Verify all nodes are on same network
- Check CML bridge configuration
- Verify static IPs are configured correctly
- Test connectivity: `ping` between nodes

## Next Steps

1. **Generate Test Traffic**: Use lab scripts to generate NetFlow traffic
2. **Test TrustSec Policies**: Configure and test SGT-based policies
3. **Monitor Events**: Use Clarion UI to monitor ISE and AD events
4. **Test Integration**: Verify end-to-end data flow from ISE/AD to Clarion

## Additional Resources

- [ISE Configuration Guide](ISE_CONFIGURATION.md)
- [AD Configuration Guide](AD_CONFIGURATION.md)
- [CML Documentation](https://developer.cisco.com/docs/modeling-labs/)
- [ISE pxGrid Documentation](https://www.cisco.com/c/en/us/support/security/identity-services-engine/products-installation-and-configuration-guides-list.html)

