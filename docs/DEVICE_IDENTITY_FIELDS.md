# Device Identity Fields

This document describes the device identity fields used in Clarion, specifically for laptops and user-associated devices.

## Overview

Clarion tracks multiple identity attributes for devices to provide comprehensive device identification and user association:

1. **Machine Name** - The hostname/name of the device (applies to ALL device types)
2. **Username** - The authenticated user on the device (when applicable)
3. **Device Name** - An alternative identifier (e.g., from ISE profiles)
4. **Device Type** - Classification (laptop, server, desktop, IoT, printer, etc.)

**Important:** Machine names are universal - ALL devices can have names:
- **Laptops/Desktops**: Computer hostnames (e.g., "JOHN-LAPTOP", "WORKSTATION-001")
- **Servers**: Server hostnames (e.g., "WEB-SRV-01", "DB-PRIMARY")
- **IoT Devices**: Device names (e.g., "CAMERA-ENTRANCE", "SENSOR-BUILDING-A")
- **Printers**: Printer names (e.g., "PRINTER-IT-DEPT", "MFP-FLOOR-3")
- **Network Equipment**: Device hostnames (e.g., "SWITCH-IDF-01", "AP-LOBBY")

Names can be resolved from multiple sources: Active Directory (AD), DNS, ISE profiling, SNMP, DHCP, or manual entry.

## Current Implementation

### Database Schema

#### `identity` Table
The `identity` table stores IP-to-identity mappings:

```sql
CREATE TABLE identity (
    ip_address TEXT PRIMARY KEY,
    mac_address TEXT,
    user_name TEXT,              -- Username associated with the device
    device_name TEXT,            -- Device/machine name (hostname)
    ad_groups TEXT,              -- JSON array of AD groups
    ise_profile TEXT,            -- ISE device profile
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

#### `sketches` Table
The `sketches` table stores network behavior data for endpoints:

```sql
CREATE TABLE sketches (
    endpoint_id TEXT NOT NULL,   -- MAC address
    switch_id TEXT NOT NULL,
    -- ... network metrics ...
)
```

#### `user_device_associations` Table
Links users to devices:

```sql
CREATE TABLE user_device_associations (
    association_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    endpoint_id TEXT NOT NULL,   -- MAC address
    ip_address TEXT,
    association_type TEXT,       -- 'ise_session', 'ad_computer', 'manual'
    -- ... timestamps ...
)
```

### API Response Fields

#### Device List/Detail Endpoints
The `/api/devices` endpoints return:

```json
{
  "endpoint_id": "00:11:22:33:44:55",
  "ip_address": "192.168.1.100",
  "user_name": "john.doe",           // Username
  "device_name": "JOHN-LAPTOP",      // Machine name/hostname
  "device_type": "laptop",           // Device classification
  "ad_groups": ["Engineering", "VPN-Users"],
  "ise_profile": "Windows-Laptop",
  // ... network metrics ...
}
```

## Display Requirements

### Machine Names for All Devices
**ALL devices should display their machine name when available**, regardless of device type:
- **Laptops/Desktops**: Show machine name + username (e.g., "JOHN-LAPTOP (john.doe)")
- **Servers**: Show machine name (e.g., "WEB-SRV-01")
- **IoT Devices**: Show device name (e.g., "CAMERA-ENTRANCE")
- **Printers**: Show printer name (e.g., "PRINTER-IT-DEPT")
- **Network Equipment**: Show device hostname (e.g., "SWITCH-IDF-01")

### User-Associated Devices
When a device has an associated user (laptops, shared workstations), show both:
- **Machine Name** (`device_name`): The device hostname/name (e.g., "JOHN-LAPTOP", "CAMERA-ENTRANCE")
- **Username** (`user_name`): The authenticated user (e.g., "john.doe") - when applicable

### UI Display Format

**Example in Devices List (Laptop):**
```
Device: JOHN-LAPTOP (john.doe)
MAC: 00:11:22:33:44:55
IP: 192.168.1.100
Type: Laptop
```

**Example in Devices List (Server):**
```
Device: WEB-SRV-01
MAC: 00:11:22:33:44:AA
IP: 192.168.10.50
Type: Server
```

**Example in Devices List (IoT Device):**
```
Device: CAMERA-ENTRANCE
MAC: 00:11:22:33:44:BB
IP: 192.168.20.100
Type: IoT
```

**Example in Device Detail Modal (Laptop):**
```
Machine Name: JOHN-LAPTOP
Username: john.doe
Device Type: Laptop
```

**Example in Device Detail Modal (Server):**
```
Machine Name: WEB-SRV-01
Device Type: Server
Username: (not applicable)
```

**Example in User Detail Modal (Associated Devices):**
```
Device: JOHN-LAPTOP
MAC: 00:11:22:33:44:55
Username: john.doe
Association Type: ISE Session
```

## Data Sources

Machine names can be resolved from multiple sources, in priority order:

### 1. Active Directory (AD)
- **Machine Name**: From AD computer object name (CN attribute)
  - Works for: Domain-joined computers (laptops, desktops, servers)
  - Example: Query AD by MAC address or IP → get computer name
- **Username**: From AD user sessions or computer associations
- **Device Type**: Inferred from AD computer object attributes

### 2. DNS (Domain Name System)
- **Machine Name**: Reverse DNS lookup (PTR records)
  - Works for: Any device with DNS entry
  - Example: IP → PTR record → hostname
- **Device Type**: Inferred from hostname patterns or additional queries

### 3. ISE (Cisco Identity Services Engine)
- **Machine Name**: From ISE endpoint profiling (hostname detection)
  - Works for: Devices authenticated through ISE
  - ISE can detect hostnames from DHCP, CDP, authentication
- **Username**: From ISE authentication sessions (username field)
- **Device Type**: From ISE device profiles (e.g., "Windows-Laptop", "IoT-Camera")

### 4. SNMP (Simple Network Management Protocol)
- **Machine Name**: From SNMP sysName (1.3.6.1.2.1.1.5.0)
  - Works for: Network devices with SNMP enabled (switches, routers, IoT devices)
- **Device Type**: From SNMP sysDescr or device capabilities

### 5. DHCP
- **Machine Name**: From DHCP hostname option (option 12)
  - Works for: Devices that provide hostname in DHCP requests
- **Device Type**: May be inferred from hostname patterns

### 6. Manual Entry
- Administrators can manually set `device_name` and `user_name` fields
- Useful for: Devices that can't be automatically resolved, correction of incorrect names

### Resolution Priority
When multiple sources are available, Clarion should prioritize:
1. **Manual entry** (user override)
2. **AD computer object** (most reliable for domain-joined devices)
3. **ISE endpoint profiling** (comprehensive for authenticated devices)
4. **DNS PTR lookup** (quick but may be incomplete)
5. **SNMP sysName** (for network devices)
6. **DHCP hostname** (least reliable, may be generic)

## Implementation Notes

### Field Mapping

| Display Field | Database Field | Source |
|--------------|----------------|--------|
| Machine Name | `identity.device_name` | ISE profile, AD computer name, manual |
| Username | `identity.user_name` | ISE session, AD user, manual |
| Device Type | `identity.device_type` (if added) | ISE profile classification |

### Current Status

✅ **Implemented:**
- `identity` table has `device_name` and `user_name` fields
- API endpoints return both fields
- Frontend `Device` interface includes both fields

⏳ **To Be Enhanced:**
- **Machine Name Resolution**: Implement multi-source resolution (AD, DNS, ISE, SNMP, DHCP)
  - Priority: AD → ISE → DNS → SNMP → DHCP → Manual
  - Fallback logic when one source fails
- **Device Type Enhancement**: Add `device_type` field to `identity` table if not present
  - Classify all device types: laptop, desktop, server, IoT, printer, network, etc.
- **UI Display Updates**: Update all UI components to prominently display machine name for ALL devices
  - Devices list: Show machine name for all devices (not just laptops)
  - Device Detail Modal: Always show machine name section
  - User Detail Modal: Show machine name in associated devices section
  - Group Detail Modal: Show machine names for cluster members
- **Name Resolution Service**: Build a service/utility to resolve machine names from multiple sources
  - AD LDAP queries by MAC/IP
  - DNS reverse lookup (PTR records)
  - ISE endpoint profiling integration
  - SNMP queries for network devices
  - DHCP hostname extraction (if available)
  - Caching to reduce redundant lookups

## Related Documentation

- `docs/USER_DATABASE_IMPLEMENTATION.md` - User database schema and implementation
- `docs/ISE_INTEGRATION.md` - ISE integration details and data flow
- `docs/TESTING.md` - Testing guidelines for device identity

