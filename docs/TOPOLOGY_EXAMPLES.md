# Topology Examples

## Example 1: Enterprise with Multiple Campuses

```
Organization: Global Corp
│
├── Main Campus (campus-hq)
│   ├── Building 1 (bldg1)
│   │   ├── IDF 1 (bldg1-idf1)
│   │   │   ├── Switch SW001
│   │   │   └── Subnet: 10.1.1.0/24 (USER)
│   │   └── IDF 2 (bldg1-idf2)
│   │       ├── Switch SW002
│   │       └── Subnet: 10.1.2.0/24 (SERVER)
│   └── Building 2 (bldg2)
│       └── Data Center (bldg2-dc)
│           ├── Switch SW003
│           └── Subnet: 10.1.3.0/24 (SERVER)
│
├── Secondary Campus (campus-secondary)
│   └── Building 1 (bldg1-sec)
│       └── IDF 1 (bldg1-sec-idf1)
│           ├── Switch SW101
│           └── Subnet: 10.2.1.0/24 (USER)
│
├── Branch - New York (branch-ny)
│   └── Main IDF (branch-ny-idf1)
│       ├── Switch SW201
│       ├── Subnet: 10.3.1.0/24 (USER)
│       └── Subnet: 10.3.2.0/24 (SERVER)
│
├── Branch - Los Angeles (branch-la)
│   └── Main IDF (branch-la-idf1)
│       ├── Switch SW301
│       └── Subnet: 10.4.1.0/24 (USER)
│
└── Remote Site - Warehouse (remote-warehouse)
    └── Switch SW401 (direct connection)
        └── Subnet: 10.5.1.0/24 (IOT)
```

**Address Spaces:**
- `10.1.0.0/16` - Main Campus
- `10.2.0.0/16` - Secondary Campus
- `10.3.0.0/16` - Branch Offices (NY)
- `10.4.0.0/16` - Branch Offices (LA)
- `10.5.0.0/16` - Remote Sites

---

## Example 2: Healthcare Organization

```
Organization: Regional Hospital
│
├── Main Hospital Campus (campus-main)
│   ├── Building A - Patient Care (bldg-a)
│   │   ├── IDF 1 - Floor 1 (bldg-a-idf1)
│   │   │   ├── Switch SW001
│   │   │   └── Subnet: 10.1.1.0/24 (USER - Medical Devices)
│   │   └── IDF 2 - Floor 2 (bldg-a-idf2)
│   │       ├── Switch SW002
│   │       └── Subnet: 10.1.2.0/24 (IOT - Patient Monitors)
│   └── Building B - Administration (bldg-b)
│       └── IDF 1 (bldg-b-idf1)
│           ├── Switch SW003
│           └── Subnet: 10.1.3.0/24 (USER - Office)
│
├── Branch - Clinic Downtown (branch-clinic-dt)
│   └── Main IDF (branch-clinic-dt-idf1)
│       ├── Switch SW101
│       └── Subnet: 10.2.1.0/24 (USER)
│
└── Remote Site - Pharmacy (remote-pharmacy)
    └── Switch SW201
        └── Subnet: 10.3.1.0/24 (IOT - Pharmacy Systems)
```

**Special Considerations:**
- Medical devices (IOT purpose)
- HIPAA compliance tracking by location
- Patient data flows between locations

---

## Example 3: Retail Chain

```
Organization: Retail Chain
│
├── HQ Campus (campus-hq)
│   └── Data Center (bldg-dc)
│       └── MDF (mdf)
│           ├── Switch SW001
│           └── Subnet: 10.1.1.0/24 (SERVER)
│
├── Distribution Center (branch-dc)
│   └── Main IDF (branch-dc-idf1)
│       ├── Switch SW101
│       └── Subnet: 10.2.1.0/24 (IOT - Warehouse Systems)
│
└── Store Locations (multiple remote sites)
    ├── Store 001 (remote-store-001)
    │   └── Switch SW201
    │       └── Subnet: 10.3.1.0/24 (IOT - POS, Inventory)
    ├── Store 002 (remote-store-002)
    │   └── Switch SW202
    │       └── Subnet: 10.3.2.0/24 (IOT - POS, Inventory)
    └── Store 003 (remote-store-003)
        └── Switch SW203
            └── Subnet: 10.3.3.0/24 (IOT - POS, Inventory)
```

**Address Spaces:**
- `10.1.0.0/16` - HQ/Data Center
- `10.2.0.0/16` - Distribution Centers
- `10.3.0.0/16` - Retail Stores (one /24 per store)

---

## Location Type Attributes

### Campus Attributes
```json
{
  "location_id": "campus-main",
  "name": "Main Campus",
  "type": "CAMPUS",
  "parent_id": null,
  "address": "123 Corporate Blvd, City, State 12345",
  "coordinates": [40.7128, -74.0060],
  "site_type": "HEADQUARTERS",
  "contact_name": "IT Manager",
  "contact_phone": "555-0100",
  "contact_email": "it@company.com",
  "timezone": "America/New_York",
  "metadata": {
    "employee_count": 1000,
    "building_count": 5,
    "square_footage": 500000
  }
}
```

### Branch Attributes
```json
{
  "location_id": "branch-austin",
  "name": "Branch - Austin",
  "type": "BRANCH",
  "parent_id": null,
  "address": "456 Austin St, Austin, TX 78701",
  "coordinates": [30.2672, -97.7431],
  "site_type": "BRANCH_OFFICE",
  "contact_name": "Branch Manager",
  "contact_phone": "512-555-1234",
  "contact_email": "austin@company.com",
  "timezone": "America/Chicago",
  "metadata": {
    "employee_count": 50,
    "business_hours": "8am-5pm",
    "services": ["Sales", "Support"]
  }
}
```

### Remote Site Attributes
```json
{
  "location_id": "remote-warehouse",
  "name": "Remote Site - Warehouse",
  "type": "REMOTE_SITE",
  "parent_id": null,
  "address": "789 Industrial Way, City, State 12345",
  "coordinates": [40.7580, -73.9855],
  "site_type": "WAREHOUSE",
  "contact_name": "Site Supervisor",
  "contact_phone": "555-0200",
  "contact_email": "warehouse@company.com",
  "timezone": "America/New_York",
  "metadata": {
    "employee_count": 10,
    "business_hours": "24/7",
    "facility_type": "WAREHOUSE",
    "automation_level": "HIGH"
  }
}
```

---

## Location Hierarchy Rules

### Valid Hierarchies

**Campus:**
- CAMPUS → BUILDING → IDF → (Switches, Subnets)
- CAMPUS → BUILDING → ROOM → (Switches, Subnets)
- CAMPUS → BUILDING → IDF → ROOM → (Switches, Subnets)

**Branch:**
- BRANCH → IDF → (Switches, Subnets)
- BRANCH → ROOM → (Switches, Subnets)
- BRANCH → (Switches, Subnets) - Direct, no IDF

**Remote Site:**
- REMOTE_SITE → (Switches, Subnets) - Usually direct
- REMOTE_SITE → ROOM → (Switches, Subnets) - If has multiple rooms

### Invalid Hierarchies

- ❌ BRANCH → BUILDING (branches don't have buildings)
- ❌ REMOTE_SITE → IDF (remote sites usually too small)
- ❌ CAMPUS → BRANCH (branches are peer to campus, not children)

---

## Query Examples

### Get All Locations by Type
```sql
SELECT * FROM locations WHERE type = 'BRANCH';
SELECT * FROM locations WHERE type = 'REMOTE_SITE';
```

### Get Location Hierarchy
```sql
-- Get campus with all children
WITH RECURSIVE location_tree AS (
    SELECT * FROM locations WHERE location_id = 'campus-main'
    UNION ALL
    SELECT l.* FROM locations l
    JOIN location_tree lt ON l.parent_id = lt.location_id
)
SELECT * FROM location_tree;
```

### Get All Subnets for a Location Type
```sql
SELECT s.*, l.name as location_name, l.type as location_type
FROM subnets s
JOIN locations l ON s.location_id = l.location_id
WHERE l.type = 'BRANCH';
```

### Get Switches by Location Type
```sql
SELECT sw.*, l.name as location_name, l.type as location_type
FROM switches sw
JOIN locations l ON sw.location_id = l.location_id
WHERE l.type IN ('BRANCH', 'REMOTE_SITE');
```

### Flows Between Location Types
```sql
SELECT 
    src_loc.type as src_type,
    dst_loc.type as dst_type,
    COUNT(*) as flow_count,
    SUM(f.bytes) as total_bytes
FROM netflow f
JOIN subnets src_sub ON f.src_subnet_id = src_sub.subnet_id
JOIN subnets dst_sub ON f.dst_subnet_id = dst_sub.subnet_id
JOIN locations src_loc ON src_sub.location_id = src_loc.location_id
JOIN locations dst_loc ON dst_sub.location_id = dst_loc.location_id
WHERE f.flow_start >= UNIX_TIMESTAMP(NOW() - INTERVAL 24 HOUR)
GROUP BY src_loc.type, dst_loc.type;
```

---

## UI Considerations

### Topology Builder

1. **Location Type Selector**
   - Radio buttons: Campus / Branch / Remote Site
   - Different forms based on type

2. **Hierarchy Tree**
   - Show all location types
   - Color coding: Campus (blue), Branch (green), Remote (orange)
   - Expandable tree view

3. **Location Form**
   - Common fields: Name, Address, Coordinates
   - Type-specific fields:
     - Campus: Building count, square footage
     - Branch: Employee count, business hours
     - Remote: Facility type, automation level

4. **Map View**
   - Plot all locations on map
   - Filter by type
   - Show connections between locations

