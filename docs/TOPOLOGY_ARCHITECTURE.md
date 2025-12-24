# Network Topology & Location Architecture

## Overview

Clarion requires network topology awareness to:
- **Correlate flows with physical locations** (campus, building, IDF)
- **Map subnets to locations** for policy context
- **Track switches by location** for edge agent management
- **Support customer-defined address spaces** (RFC 1918 ranges)
- **Enable location-based policy recommendations**

---

## Location Hierarchy

### Structure

The topology supports multiple location types with flexible hierarchies:

```
Organization (optional top level)
├── Campus (e.g., "Main Campus")
│   └── Building (e.g., "Building 2")
│       └── IDF (Intermediate Distribution Frame, e.g., "IDF 1")
│           └── Switches
│           └── Subnets
├── Branch Office (e.g., "Branch - Austin")
│   └── IDF (e.g., "Main IDF")
│       └── Switches
│       └── Subnets
└── Remote Site (e.g., "Remote Site - Warehouse")
    └── Switch (may not have IDF, just switch)
    └── Subnets
```

### Location Model

```python
@dataclass
class Location:
    """Network location in hierarchy."""
    location_id: str  # Unique ID
    name: str  # Display name
    type: LocationType  # CAMPUS, BRANCH, REMOTE_SITE, BUILDING, IDF, ROOM
    parent_id: Optional[str]  # Parent location (None for top-level)
    address: Optional[str]  # Physical address
    coordinates: Optional[Tuple[float, float]]  # Lat/long
    site_type: Optional[str]  # Additional classification
    metadata: Dict[str, Any]  # Custom fields
```

### Location Types

**Top-Level Locations:**
- **CAMPUS** - Main campus location (e.g., "Main Campus", "HQ Campus")
- **BRANCH** - Branch office (e.g., "Branch - Austin", "Branch - Seattle")
- **REMOTE_SITE** - Remote/small site (e.g., "Remote Site - Warehouse", "Retail Store 1")

**Sub-Locations (for Campus):**
- **BUILDING** - Building within campus (e.g., "Building 2", "Data Center")
- **IDF** - Intermediate Distribution Frame (e.g., "IDF 1", "MDF")
- **ROOM** - Optional: Specific room/closet (e.g., "Server Room 101")

**Sub-Locations (for Branch/Remote):**
- **IDF** - Distribution frame (may be single IDF for branch)
- **ROOM** - Optional: Specific room/closet
- **SWITCH** - Direct switch (for very small remote sites)

### Location Attributes

All location types support:
- **Physical Address** - Street address
- **Coordinates** - Latitude/longitude for mapping
- **Contact Information** - Site contact details
- **Network Information** - Subnets, switches, VLANs
- **Custom Metadata** - Flexible JSON for vendor-specific data

---

## Address Space Management

### Customer-Defined Address Spaces

Customers define their internal IP address ranges:

| Address Space | Type | Description | Example |
|---------------|------|-------------|---------|
| **Global** | RFC 1918 | Organization-wide ranges | `10.0.0.0/8` |
| **Regional** | Subnet | Region-specific | `10.1.0.0/16` |
| **Location** | Subnet | Location-specific | `10.1.2.0/24` |
| **VLAN** | Subnet | VLAN-specific | `10.1.2.100/28` |

### Address Space Model

```python
@dataclass
class AddressSpace:
    """Customer-defined IP address space."""
    space_id: str
    name: str  # e.g., "Corporate Network"
    cidr: str  # e.g., "10.0.0.0/8"
    type: AddressSpaceType  # GLOBAL, REGIONAL, LOCATION, VLAN
    location_id: Optional[str]  # If location-specific
    description: str
    is_internal: bool  # True for RFC 1918, False for public
    metadata: Dict[str, Any]
```

### RFC 1918 Ranges

Default internal ranges (can be customized):
- `10.0.0.0/8` - Class A private
- `172.16.0.0/12` - Class B private
- `192.168.0.0/16` - Class C private

---

## Subnet-to-Location Mapping

### Subnet Model

```python
@dataclass
class Subnet:
    """Subnet with location mapping."""
    subnet_id: str
    cidr: str  # e.g., "10.1.2.0/24"
    name: str  # e.g., "Building 2 - Floor 1"
    location_id: str  # IDF location
    vlan_id: Optional[int]  # VLAN number
    switch_id: Optional[str]  # Primary switch
    gateway_ip: Optional[str]  # Default gateway
    dhcp_range: Optional[Tuple[str, str]]  # DHCP range
    purpose: SubnetPurpose  # USER, SERVER, IOT, GUEST, etc.
    metadata: Dict[str, Any]
```

### Subnet Purposes

- **USER** - User devices (laptops, desktops)
- **SERVER** - Server subnets
- **IOT** - IoT devices
- **GUEST** - Guest network
- **DMZ** - Demilitarized zone
- **MANAGEMENT** - Network management
- **STORAGE** - Storage networks
- **BACKUP** - Backup networks

---

## Switch-to-Location Mapping

### Switch Model

```python
@dataclass
class Switch:
    """Network switch with location."""
    switch_id: str  # Unique switch identifier
    hostname: str  # Switch hostname
    model: str  # e.g., "Catalyst 9300"
    location_id: str  # IDF location
    management_ip: str  # Management IP
    serial_number: Optional[str]
    software_version: Optional[str]
    capabilities: List[str]  # e.g., ["App Hosting", "TrustSec"]
    edge_agent_enabled: bool  # Has edge container?
    metadata: Dict[str, Any]
```

### Switch Ports

```python
@dataclass
class SwitchPort:
    """Switch port with VLAN/subnet mapping."""
    port_id: str  # e.g., "GigabitEthernet1/0/1"
    switch_id: str
    port_number: int
    port_type: PortType  # ACCESS, TRUNK, ROUTED
    vlan_id: Optional[int]  # For access ports
    allowed_vlans: Optional[List[int]]  # For trunk ports
    subnet_id: Optional[str]  # If routed port
    description: str
    status: PortStatus  # UP, DOWN, ADMIN_DOWN
```

---

## Topology Database Schema

### Locations Table

```sql
CREATE TABLE locations (
    location_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,  -- CAMPUS, BRANCH, REMOTE_SITE, BUILDING, IDF, ROOM
    parent_id TEXT,  -- Foreign key to locations.location_id
    address TEXT,
    latitude REAL,
    longitude REAL,
    site_type TEXT,  -- Additional classification (e.g., "BRANCH_OFFICE", "WAREHOUSE")
    contact_name TEXT,
    contact_phone TEXT,
    contact_email TEXT,
    timezone TEXT,  -- e.g., "America/Chicago"
    metadata JSON,  -- JSON for custom fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES locations(location_id)
);

CREATE INDEX idx_locations_parent ON locations(parent_id);
CREATE INDEX idx_locations_type ON locations(type);
```

### Address Spaces Table

```sql
CREATE TABLE address_spaces (
    space_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    cidr TEXT NOT NULL,  -- e.g., "10.0.0.0/8"
    type TEXT NOT NULL,  -- GLOBAL, REGIONAL, LOCATION, VLAN
    location_id TEXT,  -- If location-specific
    description TEXT,
    is_internal BOOLEAN DEFAULT TRUE,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (location_id) REFERENCES locations(location_id)
);

CREATE INDEX idx_address_spaces_cidr ON address_spaces(cidr);
CREATE INDEX idx_address_spaces_location ON address_spaces(location_id);
```

### Subnets Table

```sql
CREATE TABLE subnets (
    subnet_id TEXT PRIMARY KEY,
    cidr TEXT NOT NULL UNIQUE,  -- e.g., "10.1.2.0/24"
    name TEXT NOT NULL,
    location_id TEXT NOT NULL,
    vlan_id INTEGER,
    switch_id TEXT,  -- Primary switch
    gateway_ip TEXT,
    dhcp_start TEXT,
    dhcp_end TEXT,
    purpose TEXT NOT NULL,  -- USER, SERVER, IOT, etc.
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (location_id) REFERENCES locations(location_id),
    FOREIGN KEY (switch_id) REFERENCES switches(switch_id)
);

CREATE INDEX idx_subnets_location ON subnets(location_id);
CREATE INDEX idx_subnets_vlan ON subnets(vlan_id);
CREATE INDEX idx_subnets_switch ON subnets(switch_id);
```

### Switches Table

```sql
CREATE TABLE switches (
    switch_id TEXT PRIMARY KEY,
    hostname TEXT NOT NULL UNIQUE,
    model TEXT,
    location_id TEXT NOT NULL,
    management_ip TEXT NOT NULL,
    serial_number TEXT,
    software_version TEXT,
    capabilities TEXT,  -- JSON array
    edge_agent_enabled BOOLEAN DEFAULT FALSE,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (location_id) REFERENCES locations(location_id)
);

CREATE INDEX idx_switches_location ON switches(location_id);
CREATE INDEX idx_switches_hostname ON switches(hostname);
```

### Switch Ports Table

```sql
CREATE TABLE switch_ports (
    port_id TEXT PRIMARY KEY,  -- e.g., "SW001-Gi1/0/1"
    switch_id TEXT NOT NULL,
    port_number INTEGER NOT NULL,
    port_type TEXT NOT NULL,  -- ACCESS, TRUNK, ROUTED
    vlan_id INTEGER,  -- For access ports
    allowed_vlans TEXT,  -- JSON array for trunk ports
    subnet_id TEXT,  -- If routed port
    description TEXT,
    status TEXT NOT NULL,  -- UP, DOWN, ADMIN_DOWN
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (switch_id) REFERENCES switches(switch_id),
    FOREIGN KEY (subnet_id) REFERENCES subnets(subnet_id),
    UNIQUE(switch_id, port_number)
);

CREATE INDEX idx_switch_ports_switch ON switch_ports(switch_id);
CREATE INDEX idx_switch_ports_vlan ON switch_ports(vlan_id);
```

---

## Flow-to-Location Correlation

### Enhanced Flow Schema

```sql
-- Add location fields to flows table
ALTER TABLE flows ADD COLUMN src_location_id TEXT;
ALTER TABLE flows ADD COLUMN dst_location_id TEXT;
ALTER TABLE flows ADD COLUMN src_subnet_id TEXT;
ALTER TABLE flows ADD COLUMN dst_subnet_id TEXT;

CREATE INDEX idx_flows_src_location ON flows(src_location_id, time);
CREATE INDEX idx_flows_dst_location ON flows(dst_location_id, time);
```

### Location Resolution Logic

```python
def resolve_flow_location(flow: FlowRecord) -> Tuple[Location, Location]:
    """
    Resolve source and destination locations for a flow.
    
    1. Resolve IP to subnet (using CIDR matching)
    2. Subnet to location (via subnets table)
    3. Location hierarchy (campus -> building -> IDF)
    """
    # IP to subnet
    src_subnet = find_subnet_for_ip(flow.src_ip)
    dst_subnet = find_subnet_for_ip(flow.dst_ip)
    
    # Subnet to location
    src_location = get_location_for_subnet(src_subnet)
    dst_location = get_location_for_subnet(dst_subnet)
    
    return src_location, dst_location
```

---

## Topology Management API

### Location Management

```python
# POST /api/topology/locations
# Create location
{
    "location_id": "campus-main",
    "name": "Main Campus",
    "type": "CAMPUS",
    "parent_id": null,
    "address": "123 Main St",
    "coordinates": [40.7128, -74.0060]
}

# GET /api/topology/locations/{location_id}
# Get location with hierarchy

# GET /api/topology/locations/{location_id}/children
# Get child locations

# PUT /api/topology/locations/{location_id}
# Update location

# DELETE /api/topology/locations/{location_id}
# Delete location (if no children)
```

### Address Space Management

```python
# POST /api/topology/address-spaces
# Define address space
{
    "space_id": "corp-network",
    "name": "Corporate Network",
    "cidr": "10.0.0.0/8",
    "type": "GLOBAL",
    "is_internal": true
}

# GET /api/topology/address-spaces
# List all address spaces

# GET /api/topology/address-spaces/{space_id}
# Get address space details
```

### Subnet Management

```python
# POST /api/topology/subnets
# Create subnet
{
    "subnet_id": "bldg2-idf1-user",
    "cidr": "10.1.2.0/24",
    "name": "Building 2 - IDF 1 - User Network",
    "location_id": "bldg2-idf1",
    "vlan_id": 100,
    "switch_id": "SW001",
    "purpose": "USER",
    "gateway_ip": "10.1.2.1"
}

# GET /api/topology/subnets
# List subnets (with filters: location, purpose, etc.)

# GET /api/topology/subnets/{subnet_id}
# Get subnet details

# POST /api/topology/subnets/resolve
# Resolve IP to subnet
{
    "ip": "10.1.2.50"
}
# Returns: subnet_id, location_id, location_path
```

### Switch Management

```python
# POST /api/topology/switches
# Register switch
{
    "switch_id": "SW001",
    "hostname": "switch-bldg2-idf1",
    "model": "Catalyst 9300",
    "location_id": "bldg2-idf1",
    "management_ip": "10.1.2.1",
    "capabilities": ["App Hosting", "TrustSec"],
    "edge_agent_enabled": true
}

# GET /api/topology/switches
# List switches (with filters: location, model, etc.)

# GET /api/topology/switches/{switch_id}
# Get switch with location hierarchy

# GET /api/topology/switches/{switch_id}/ports
# Get switch ports
```

---

## Topology Builder UI

### Features

1. **Location Hierarchy Builder**
   - Drag-and-drop interface
   - Create campus → building → IDF structure
   - Visual hierarchy tree

2. **Address Space Configuration**
   - Define global ranges (10.0.0.0/8)
   - Mark as internal/external
   - Visual IP range display

3. **Subnet Mapping**
   - Create subnets
   - Assign to locations
   - Map VLANs
   - Set purpose (USER, SERVER, IOT, etc.)

4. **Switch Registration**
   - Add switches to locations
   - Configure ports
   - Enable edge agents
   - Import from discovery

5. **Topology Visualization**
   - Network map showing:
     - Locations (campus, buildings, IDFs)
     - Switches at each location
     - Subnets per location
     - Flow paths between locations

---

## Flow Enrichment with Location

### Enhanced Flow Record

```python
@dataclass
class EnrichedFlow:
    """Flow record with location context."""
    # Original flow fields
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: int
    bytes: int
    packets: int
    flow_start: int
    flow_end: int
    
    # Location context
    src_location_path: str  # "Campus: Main > Building: 2 > IDF: 1"
    dst_location_path: str
    src_subnet: str  # "10.1.2.0/24"
    dst_subnet: str
    src_subnet_purpose: str  # "USER", "SERVER", etc.
    dst_subnet_purpose: str
    
    # Switch context
    src_switch_id: str
    dst_switch_id: str
    src_switch_location: str
    dst_switch_location: str
```

### Location-Based Queries

```sql
-- Flows between locations
SELECT 
    src_loc.name as src_location,
    dst_loc.name as dst_location,
    SUM(bytes) as total_bytes,
    COUNT(*) as flow_count
FROM flows f
JOIN subnets src_sub ON f.src_subnet_id = src_sub.subnet_id
JOIN subnets dst_sub ON f.dst_subnet_id = dst_sub.subnet_id
JOIN locations src_loc ON src_sub.location_id = src_loc.location_id
JOIN locations dst_loc ON dst_sub.location_id = dst_loc.location_id
WHERE f.time >= NOW() - INTERVAL '24 hours'
GROUP BY src_loc.name, dst_loc.name;

-- Flows within a building
SELECT COUNT(*) as internal_flows
FROM flows f
JOIN subnets src_sub ON f.src_subnet_id = src_sub.subnet_id
JOIN subnets dst_sub ON f.dst_subnet_id = dst_sub.subnet_id
WHERE src_sub.location_id IN (
    SELECT location_id FROM locations 
    WHERE parent_id = 'bldg2' OR location_id = 'bldg2'
)
AND dst_sub.location_id IN (
    SELECT location_id FROM locations 
    WHERE parent_id = 'bldg2' OR location_id = 'bldg2'
);
```

---

## Implementation Priority

### Phase 1: Core Topology (Immediate)
1. Location hierarchy (campus → building → IDF)
2. Address space definition
3. Subnet-to-location mapping
4. Switch-to-location mapping
5. Basic API endpoints

### Phase 2: Flow Enrichment (Short-term)
1. IP-to-subnet resolution
2. Flow location correlation
3. Location-based queries
4. Enhanced flow schema

### Phase 3: Topology Builder UI (Medium-term)
1. Visual location hierarchy
2. Subnet mapping interface
3. Switch registration
4. Topology visualization

### Phase 4: Advanced Features (Long-term)
1. Automatic topology discovery
2. Switch port mapping
3. VLAN-to-subnet correlation
4. Location-based policy recommendations

---

## Database Migration

### Add Topology Tables

```sql
-- Run migration script
-- Creates: locations, address_spaces, subnets, switches, switch_ports
-- Adds indexes and foreign keys
```

### Update Existing Tables

```sql
-- Add location fields to flows
ALTER TABLE netflow ADD COLUMN src_location_id TEXT;
ALTER TABLE netflow ADD COLUMN dst_location_id TEXT;
ALTER TABLE netflow ADD COLUMN src_subnet_id TEXT;
ALTER TABLE netflow ADD COLUMN dst_subnet_id TEXT;

-- Add location to sketches
ALTER TABLE sketches ADD COLUMN location_id TEXT;
```

---

## Example: Customer Topology

### Complete Organization Structure

```
Organization: Acme Corp
├── Main Campus (campus-main)
│   ├── Building 1 (bldg1)
│   │   ├── IDF 1 (bldg1-idf1)
│   │   │   ├── Switch SW001
│   │   │   └── Subnet: 10.1.1.0/24 (USER)
│   │   └── IDF 2 (bldg1-idf2)
│   │       ├── Switch SW002
│   │       └── Subnet: 10.1.2.0/24 (SERVER)
│   └── Building 2 (bldg2)
│       ├── IDF 1 (bldg2-idf1)
│       │   ├── Switch SW003
│       │   └── Subnet: 10.1.3.0/24 (USER)
│       └── Data Center (bldg2-dc)
│           ├── Switch SW004
│           └── Subnet: 10.1.4.0/24 (SERVER)
│
├── Branch - Austin (branch-austin)
│   └── Main IDF (branch-austin-idf1)
│       ├── Switch SW101
│       ├── Switch SW102
│       ├── Subnet: 10.2.1.0/24 (USER)
│       └── Subnet: 10.2.2.0/24 (SERVER)
│
├── Branch - Seattle (branch-seattle)
│   └── Main IDF (branch-seattle-idf1)
│       ├── Switch SW201
│       └── Subnet: 10.3.1.0/24 (USER)
│
└── Remote Site - Warehouse (remote-warehouse)
    └── Switch SW301 (direct, no IDF)
        └── Subnet: 10.4.1.0/24 (IOT)
```

### Address Spaces by Location Type

```
Global: 10.0.0.0/8 (Corporate Network)
├── Campus: 10.1.0.0/16 (Main Campus)
│   ├── Building 1 - IDF 1: 10.1.1.0/24 (USER)
│   ├── Building 1 - IDF 2: 10.1.2.0/24 (SERVER)
│   ├── Building 2 - IDF 1: 10.1.3.0/24 (USER)
│   └── Building 2 - Data Center: 10.1.4.0/24 (SERVER)
│
├── Branch: 10.2.0.0/16 (Branch Offices)
│   ├── Austin - IDF 1: 10.2.1.0/24 (USER)
│   ├── Austin - IDF 1: 10.2.2.0/24 (SERVER)
│   └── Seattle - IDF 1: 10.3.1.0/24 (USER)
│
└── Remote: 10.4.0.0/16 (Remote Sites)
    └── Warehouse: 10.4.1.0/24 (IOT)
```

### Location Attributes Example

```json
{
  "location_id": "branch-austin",
  "name": "Branch - Austin",
  "type": "BRANCH",
  "parent_id": null,
  "address": "123 Austin St, Austin, TX 78701",
  "coordinates": [30.2672, -97.7431],
  "site_type": "BRANCH_OFFICE",
  "metadata": {
    "contact": "John Doe",
    "phone": "512-555-1234",
    "timezone": "America/Chicago",
    "business_hours": "8am-5pm",
    "employee_count": 50
  }
}
```

---

## Benefits

1. **Location-Aware Policies** - Recommend SGTs based on location
2. **Traffic Analysis** - Understand inter-building vs. intra-building traffic
3. **Policy Validation** - Verify policies match location requirements
4. **Edge Agent Management** - Know which switches are at which locations
5. **Compliance** - Track which locations have which device types
6. **Visualization** - Show network topology in UI

