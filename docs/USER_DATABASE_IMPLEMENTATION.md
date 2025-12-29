# User Database Implementation Guide

This document outlines the steps needed to implement user database support in Clarion, including database schema updates, dataset updates, and UI changes.

---

## Overview

To support User SGT recommendations, Clarion needs:
1. **User database schema** - Store user details and user-device associations
2. **Dataset updates** - Enhance ground truth datasets with user data
3. **Database migration** - Update clarion.db schema to include user tables
4. **API updates** - Expose user information in device responses
5. **UI updates** - Display user information in device views

---

## 1. Database Schema Updates

### 1.1 New Tables to Add

#### `users` Table
```sql
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,  -- AD SID or ISE internal ID
    username TEXT NOT NULL,
    email TEXT,
    display_name TEXT,
    department TEXT,
    title TEXT,
    is_active BOOLEAN DEFAULT 1,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT,  -- 'ise', 'ad', 'ldap', 'manual'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
```

#### `user_device_associations` Table
```sql
CREATE TABLE IF NOT EXISTS user_device_associations (
    association_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    endpoint_id TEXT NOT NULL,  -- MAC address
    ip_address TEXT,
    association_type TEXT NOT NULL,  -- 'ise_session', 'ad_computer', 'manual'
    session_id TEXT,  -- ISE session ID if applicable
    first_associated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_associated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (endpoint_id) REFERENCES sketches(endpoint_id),
    UNIQUE(user_id, endpoint_id, association_type)
);

CREATE INDEX idx_uda_user ON user_device_associations(user_id);
CREATE INDEX idx_uda_endpoint ON user_device_associations(endpoint_id);
CREATE INDEX idx_uda_active ON user_device_associations(is_active, last_associated);
```

#### `ad_group_memberships` Table
```sql
CREATE TABLE IF NOT EXISTS ad_group_memberships (
    membership_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    group_id TEXT NOT NULL,  -- AD group SID or name
    group_name TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_verified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    UNIQUE(user_id, group_id)
);

CREATE INDEX idx_memberships_user ON ad_group_memberships(user_id);
CREATE INDEX idx_memberships_group ON ad_group_memberships(group_id);
```

### 1.2 Migration Script

Create `src/clarion/storage/migrations/add_user_tables.py`:

```python
"""
Migration: Add user database tables.

Adds users, user_device_associations, and ad_group_memberships tables.
"""
import sqlite3
import logging

logger = logging.getLogger(__name__)

def migrate(conn: sqlite3.Connection):
    """Add user database tables."""
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT,
            display_name TEXT,
            department TEXT,
            title TEXT,
            is_active BOOLEAN DEFAULT 1,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    
    # User-device associations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_device_associations (
            association_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            endpoint_id TEXT NOT NULL,
            ip_address TEXT,
            association_type TEXT NOT NULL,
            session_id TEXT,
            first_associated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_associated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(user_id, endpoint_id, association_type)
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_uda_user ON user_device_associations(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_uda_endpoint ON user_device_associations(endpoint_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_uda_active ON user_device_associations(is_active, last_associated)")
    
    # AD group memberships table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ad_group_memberships (
            membership_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            group_id TEXT NOT NULL,
            group_name TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_verified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(user_id, group_id)
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memberships_user ON ad_group_memberships(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memberships_group ON ad_group_memberships(group_id)")
    
    conn.commit()
    logger.info("User database tables created successfully")
```

### 1.3 Update `database.py`

Add the migration to `_init_schema()` method in `src/clarion/storage/database.py`:

```python
def _init_schema(self):
    """Initialize database schema."""
    conn = self._get_connection()
    
    # ... existing table creation ...
    
    # Run migrations
    self._run_migrations(conn)
    
def _run_migrations(self, conn: sqlite3.Connection):
    """Run database migrations."""
    from clarion.storage.migrations.add_user_tables import migrate as migrate_user_tables
    
    # Check if migration has been run
    cursor = conn.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='users'
    """)
    
    if not cursor.fetchone():
        migrate_user_tables(conn)
```

### 1.4 Add Database Methods

Add CRUD methods to `ClarionDatabase` class in `src/clarion/storage/database.py`:

```python
def create_user(
    self,
    user_id: str,
    username: str,
    email: Optional[str] = None,
    display_name: Optional[str] = None,
    department: Optional[str] = None,
    title: Optional[str] = None,
    source: str = "manual"
) -> None:
    """Create or update a user record."""
    conn = self._get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO users 
        (user_id, username, email, display_name, department, title, source, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (user_id, username, email, display_name, department, title, source))
    conn.commit()

def create_user_device_association(
    self,
    user_id: str,
    endpoint_id: str,
    ip_address: Optional[str] = None,
    association_type: str = "manual",
    session_id: Optional[str] = None
) -> None:
    """Create or update a user-device association."""
    conn = self._get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO user_device_associations
        (user_id, endpoint_id, ip_address, association_type, session_id, last_associated, is_active)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 1)
    """, (user_id, endpoint_id, ip_address, association_type, session_id))
    conn.commit()

def get_users_for_device(self, endpoint_id: str) -> List[Dict]:
    """Get all users associated with a device."""
    conn = self._get_connection()
    cursor = conn.execute("""
        SELECT u.*, uda.association_type, uda.last_associated, uda.is_active
        FROM users u
        JOIN user_device_associations uda ON u.user_id = uda.user_id
        WHERE uda.endpoint_id = ? AND uda.is_active = 1
        ORDER BY uda.last_associated DESC
    """, (endpoint_id,))
    return [dict(row) for row in cursor.fetchall()]

def get_user_groups(self, user_id: str) -> List[Dict]:
    """Get AD groups for a user."""
    conn = self._get_connection()
    cursor = conn.execute("""
        SELECT group_id, group_name, last_verified
        FROM ad_group_memberships
        WHERE user_id = ?
        ORDER BY group_name
    """, (user_id,))
    return [dict(row) for row in cursor.fetchall()]
```

---

## 2. Dataset Updates

### 2.1 Update Ground Truth Dataset Schema

Update `tests/data/ground_truth/SCHEMA.md` to include user details:

**ad_users.csv** - Enhanced schema:
```csv
user_id,username,email,display_name,department,title,is_privileged
S-1-5-21-1234567890-123456789-123456789-1001,jdoe,jdoe@example.com,John Doe,Engineering,Software Engineer,false
```

**ise_sessions.csv** - Ensure it includes required fields:
```csv
session_id,endpoint_id,username,profile_name,policy_set,auth_time
```

### 2.2 Update Dataset Generator

Update `tests/data/ground_truth/generator.py` to:
- Generate more complete user data (email, display_name, department)
- Create user-device associations in ISE sessions
- Ensure users are linked to devices via endpoint_id

### 2.3 Update Data Loader

Update `src/clarion/ingest/loader.py` to handle enhanced user data:
- Load user details from ad_users.csv
- Create user records when loading datasets
- Create user-device associations from ise_sessions.csv

---

## 3. API Updates

### 3.1 Update DeviceResponse Model

Update `src/clarion/api/routes/devices.py` to include user information:

```python
class DeviceResponse(BaseModel):
    # ... existing fields ...
    
    # User information
    users: List[Dict] = []  # List of users associated with this device
    primary_user: Optional[Dict] = None  # Most recently associated user
    
    # User details (backward compatibility)
    user_name: Optional[str] = None  # Primary user's username
    user_email: Optional[str] = None  # Primary user's email
    user_department: Optional[str] = None  # Primary user's department
    user_ad_groups: List[str] = []  # All AD groups from all users
```

### 3.2 Update Device List/Get Endpoints

Modify queries in `list_devices` and `get_device` to join user tables:

```python
query = """
    SELECT 
        s.endpoint_id,
        -- ... existing fields ...
        u.username as primary_user_name,
        u.email as primary_user_email,
        u.department as primary_user_department
    FROM sketches s
    LEFT JOIN identity i ON s.endpoint_id = i.mac_address
    LEFT JOIN user_device_associations uda ON s.endpoint_id = uda.endpoint_id AND uda.is_active = 1
    LEFT JOIN users u ON uda.user_id = u.user_id
    -- ... rest of query ...
"""
```

Then populate user lists:
```python
# Get all users for this device
users = db.get_users_for_device(endpoint_id)
user_ad_groups = []
for user in users:
    groups = db.get_user_groups(user['user_id'])
    user_ad_groups.extend([g['group_name'] for g in groups])

device_dict['users'] = users
device_dict['primary_user'] = users[0] if users else None
device_dict['user_name'] = users[0]['username'] if users else None
device_dict['user_email'] = users[0]['email'] if users else None
device_dict['user_department'] = users[0]['department'] if users else None
device_dict['user_ad_groups'] = list(set(user_ad_groups))  # Deduplicate
```

### 3.3 Add User Endpoints (Optional)

Add new endpoints for user management:

```python
@router.get("/users", response_model=List[Dict])
async def list_users():
    """List all users."""
    db = get_database()
    conn = db._get_connection()
    cursor = conn.execute("SELECT * FROM users ORDER BY username")
    return [dict(row) for row in cursor.fetchall()]

@router.get("/users/{user_id}", response_model=Dict)
async def get_user(user_id: str):
    """Get user details including devices and groups."""
    db = get_database()
    user = db.get_user(user_id)
    devices = db.get_devices_for_user(user_id)
    groups = db.get_user_groups(user_id)
    return {
        **user,
        'devices': devices,
        'ad_groups': groups
    }
```

---

## 4. UI Updates

### 4.1 Update DeviceDetailModal

Update `frontend/src/components/DeviceDetailModal.tsx`:

```typescript
interface Device {
  // ... existing fields ...
  users?: Array<{
    user_id: string
    username: string
    email?: string
    display_name?: string
    department?: string
    association_type: string
    last_associated: string
  }>
  primary_user?: {
    username: string
    email?: string
    department?: string
  }
  user_ad_groups?: string[]
}
```

Add a "Users" section:
```tsx
{/* Users Section */}
{device.users && device.users.length > 0 && (
  <div>
    <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
      <Users className="h-5 w-5 mr-2" />
      Associated Users
    </h3>
    <div className="bg-gray-50 rounded-lg p-4 space-y-3">
      {device.users.map((user, idx) => (
        <div key={user.user_id} className="border-b border-gray-200 pb-3 last:border-0">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-gray-900 font-medium">{user.display_name || user.username}</p>
              {user.email && (
                <p className="text-sm text-gray-500">{user.email}</p>
              )}
              {user.department && (
                <p className="text-sm text-gray-500">{user.department}</p>
              )}
            </div>
            <div className="text-right">
              <span className="text-xs text-gray-400 capitalize">{user.association_type.replace('_', ' ')}</span>
              <p className="text-xs text-gray-400">
                {new Date(user.last_associated).toLocaleDateString()}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  </div>
)}

{/* AD Groups Section */}
{device.user_ad_groups && device.user_ad_groups.length > 0 && (
  <div>
    <h3 className="text-lg font-semibold text-gray-900 mb-4">AD Groups</h3>
    <div className="flex flex-wrap gap-2">
      {device.user_ad_groups.map((group) => (
        <span key={group} className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
          {group}
        </span>
      ))}
    </div>
  </div>
)}
```

### 4.2 Update Devices List Page

Update `frontend/src/pages/Devices.tsx` to show user information in the table:

```tsx
{/* Identity Column */}
<td className="px-6 py-4">
  <div className="text-sm text-gray-900">
    {device.primary_user?.display_name || device.user_name || '—'}
  </div>
  {device.primary_user?.email && (
    <div className="text-sm text-gray-500">{device.primary_user.email}</div>
  )}
  {device.user_ad_groups && device.user_ad_groups.length > 0 && (
    <div className="text-xs text-gray-400 mt-1">
      {device.user_ad_groups.slice(0, 2).join(', ')}
      {device.user_ad_groups.length > 2 && ` +${device.user_ad_groups.length - 2}`}
    </div>
  )}
</td>
```

---

## 5. Implementation Steps

### Phase 1: Database Schema
1. ✅ Create migration script for user tables
2. ✅ Add migration to `database.py`
3. ✅ Test migration on fresh database
4. ✅ Add database CRUD methods

### Phase 2: Dataset Updates
1. ✅ Update dataset schema documentation
2. ✅ Update dataset generator to create user data
3. ✅ Test dataset loading with user data
4. ✅ Update data loader to populate user tables

### Phase 3: API Updates
1. ✅ Update DeviceResponse model
2. ✅ Update device list/get queries to join user tables
3. ✅ Test API endpoints return user data
4. ✅ (Optional) Add user management endpoints

### Phase 4: UI Updates
1. ✅ Update Device interface in TypeScript
2. ✅ Update DeviceDetailModal to show users
3. ✅ Update Devices list page to show user info
4. ✅ Test UI displays user information correctly

---

## 6. Testing

### Test Database Migration
```python
from clarion.storage import get_database

db = get_database()
# Migration should run automatically on first access
```

### Test User Data Loading
```python
from clarion.ingest.loader import DataLoader

loader = DataLoader()
dataset = loader.load_synthetic("tests/data/ground_truth/enterprise")
# Verify users are loaded and associations created
```

### Test API
```bash
curl http://localhost:8000/api/devices/{endpoint_id}
# Verify response includes users, primary_user, user_ad_groups
```

### Test UI
- Open device detail modal
- Verify users section displays
- Verify AD groups display
- Check devices list shows user info

---

## 7. Notes

- The existing `identity` table with `user_name` field is kept for backward compatibility
- User data can come from multiple sources (ISE, AD, manual)
- Multiple users can be associated with the same device (time-based)
- The `primary_user` is the most recently associated active user
- AD groups are aggregated from all users on a device

---

## Device Identity Fields

Clarion tracks machine names and usernames for all devices:

- **Machine Name** (`device_name`): The device hostname/name - applies to ALL device types
  - Laptops/Desktops: "JOHN-LAPTOP", "WORKSTATION-001"
  - Servers: "WEB-SRV-01", "DB-PRIMARY"
  - IoT Devices: "CAMERA-ENTRANCE", "SENSOR-BUILDING-A"
  - Printers: "PRINTER-IT-DEPT", "MFP-FLOOR-3"
  - Network Equipment: "SWITCH-IDF-01", "AP-LOBBY"
- **Username** (`user_name`): The authenticated user (when applicable, primarily for laptops/desktops)

Machine names can be resolved from multiple sources: Active Directory (AD), DNS, ISE, SNMP, DHCP, or manual entry. See `docs/DEVICE_IDENTITY_FIELDS.md` for detailed information on device identity fields, resolution sources, and display requirements.

## References

- [Device Identity Fields](docs/DEVICE_IDENTITY_FIELDS.md) - Device identity fields (machine name, username) requirements and display guidelines
- [ISE Integration](docs/ISE_INTEGRATION.md) - User Database and User-Device Association architecture
- [Testing Guide](docs/TESTING.md) - Testing guidelines
- [Dataset Schema](tests/data/ground_truth/SCHEMA.md) - Dataset schema
- [Database Implementation](src/clarion/storage/database.py) - Database implementation

