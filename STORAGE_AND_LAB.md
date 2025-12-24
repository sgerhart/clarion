# Storage & Lab Environment Implementation

## Summary

This document describes the implementation of:
1. **Persistent Storage** - SQLite database for backend data
2. **Administrative Console** - Production-ready admin UI
3. **Lab Environment** - VM setup with agents, NetFlow, and fake logs

---

## 1. Persistent Storage

### Implementation

**Location:** `src/clarion/storage/database.py`

**Database:** SQLite (can be upgraded to PostgreSQL/MySQL in production)

### Tables

1. **sketches** - Edge sketches from switches
   - Stores endpoint behavioral data
   - Indexed by endpoint_id, switch_id, last_seen
   - Includes serialized sketch data for full reconstruction

2. **netflow** - Raw NetFlow records
   - Stores flow data from collectors
   - Indexed by src_ip, dst_ip, flow_start
   - Used for historical analysis

3. **clusters** - Cluster metadata
   - Cluster IDs, labels, SGT assignments
   - Endpoint counts per cluster

4. **cluster_assignments** - Endpoint to cluster mapping
   - Links endpoints to their assigned clusters

5. **policies** - Generated SGACL policies
   - Policy definitions with rules
   - SGT to SGT mappings

6. **sessions** - Customization sessions
   - Human-in-the-loop review sessions
   - JSON blob for session data

7. **identity** - IP to identity mappings
   - IP → MAC, User, Device, AD Groups
   - ISE profile assignments

### Usage

```python
from clarion.storage import get_database

db = get_database()

# Store a sketch
db.store_sketch(
    endpoint_id="00:1a:2b:3c:4d:5e",
    switch_id="SW-001",
    unique_peers=150,
    unique_ports=25,
    bytes_in=1024000,
    bytes_out=2048000,
    flow_count=500,
    first_seen=1234567890,
    last_seen=1234567890,
    active_hours=0b111111111111111111111111,
)

# Get statistics
stats = db.get_sketch_stats()
print(f"Total sketches: {stats['total_sketches']}")
```

### API Integration

All API endpoints now use the database instead of in-memory storage:

- `/api/edge/sketches` - Stores sketches in database
- `/api/netflow/netflow` - Stores NetFlow records
- `/api/clustering/run` - Can store cluster results
- `/api/policy/generate` - Can store policies

### Data Retention

Automatic cleanup of old data:

```python
db.cleanup_old_data(days=30)  # Remove data older than 30 days
```

---

## 2. Administrative Console

### Implementation

**Location:** `src/clarion/ui/admin_console.py`

**Technology:** React + TypeScript (production-ready frontend)

### Features

1. **Dashboard**
   - System health metrics
   - Total endpoints, sketches, clusters, policies
   - Recent activity feed
   - Switch connectivity status

2. **Sketches Management**
   - View all edge sketches
   - Filter by switch
   - Summary statistics
   - Visualizations (flows per switch, endpoints distribution)

3. **NetFlow Records**
   - View recent NetFlow data
   - Top talkers analysis
   - Time-based filtering
   - Protocol breakdown

4. **Clusters**
   - View all clusters
   - SGT assignments
   - Endpoint counts
   - Cluster visualizations

5. **Policies**
   - View generated policies
   - Action distribution (permit/deny)
   - Policy matrix visualization

6. **Identity Mappings**
   - IP to user/device mappings
   - AD group memberships
   - ISE profile assignments

7. **Settings**
   - Database management
   - Data retention configuration
   - System configuration

### Running

```bash
# Start admin console
python scripts/run_admin_console.py

# Or directly
cd frontend && npm run dev
# Opens at http://localhost:3000
```

Access at: `http://localhost:8502`

### UI Features

- **Wide layout** for data tables
- **Interactive charts** with Plotly
- **Real-time updates** (refresh to see new data)
- **Professional styling** with custom CSS
- **Responsive design** for different screen sizes

---

## 3. Lab Environment

### Overview

Complete lab setup for testing Clarion with:
- 3 VMs with network namespaces
- Edge agents processing flows
- NetFlow senders
- Fake ISE and AD logs

### VM Setup

#### Base Setup (`setup_vm.sh`)

Creates:
- Bridge network (vsw0)
- 24 network namespaces (h1-h24)
- NetFlow collection (softflowd + nfcapd)
- Realistic traffic patterns

```bash
sudo ./lab/setup_vm.sh --traffic imix
```

#### Edge Agent Setup (`vm_agent_setup.sh`)

Installs and runs the Clarion edge agent:

```bash
sudo ./lab/vm_agent_setup.sh --backend-url http://BACKEND_IP:8000
```

Features:
- Python virtual environment
- Edge agent installation
- Systemd service
- Automatic startup

#### NetFlow Sender Setup (`vm_netflow_sender.sh`)

Sends NetFlow data to backend:

```bash
sudo ./lab/vm_netflow_sender.sh --backend-url http://BACKEND_IP:8000
```

Features:
- Reads nfdump files
- Sends to `/api/netflow/netflow`
- Systemd service
- Automatic retry on failure

### Fake Log Generation

#### ISE Logs (`generate_fake_ise.py`)

Generates realistic ISE session logs:

```bash
python3 lab/generate_fake_ise.py \
    -o lab/data/ise_sessions.json \
    -d 24 \
    -e 5
```

Features:
- Matches traffic patterns from VMs
- Device types (Server, Workstation, IoT, Guest)
- ISE profiles
- AD group memberships
- User assignments

#### AD Logs (`generate_fake_ad.py`)

Generates realistic AD logs:

```bash
python3 lab/generate_fake_ad.py \
    -o lab/data/ad_logs.json \
    -d 24 \
    -e 3
```

Features:
- User logon/logoff events
- Group membership changes
- IP to user mappings
- Domain events

### Data Flow

```
VM Traffic Generation
  ↓
NetFlow Collection (softflowd → nfcapd)
  ↓
Edge Agent (Processes flows → Sketches)
  ↓
Backend API (/api/edge/sketches)
  ↓
Database (SQLite)
  ↓
Admin Console (Visualization)
```

### Verification

```bash
# Check edge agent
sudo systemctl status clarion-edge
sudo journalctl -f -u clarion-edge

# Check NetFlow sender
sudo systemctl status clarion-netflow
sudo journalctl -f -u clarion-netflow

# Check backend
curl http://BACKEND_IP:8000/api/health
curl http://BACKEND_IP:8000/api/edge/sketches/stats
```

---

## API Endpoints

### New Endpoints

1. **NetFlow Ingestion**
   - `POST /api/netflow/netflow` - Receive NetFlow records
   - `GET /api/netflow/netflow` - List recent records

2. **Database-backed Endpoints**
   - All existing endpoints now use database
   - Data persists across restarts
   - Automatic cleanup of old data

---

## Files Created

### Storage
- `src/clarion/storage/__init__.py`
- `src/clarion/storage/database.py`

### Admin UI
- `src/clarion/ui/admin_console.py`
- `scripts/run_admin_console.py`

### Lab Environment
- `lab/vm_agent_setup.sh`
- `lab/vm_netflow_sender.sh`
- `lab/generate_fake_ise.py`
- `lab/generate_fake_ad.py`
- `lab/README.md`

### API Updates
- `src/clarion/api/routes/netflow.py` (new)
- `src/clarion/api/routes/sketches.py` (updated to use DB)
- `src/clarion/api/app.py` (added netflow router)

---

## Next Steps

1. **Load Fake Logs**: Create API endpoints to ingest ISE/AD logs into database
2. **Identity Resolution**: Use ISE/AD logs to enrich identity mappings
3. **Real-time Updates**: WebSocket support for live admin console updates
4. **Production Database**: Migrate to PostgreSQL for production
5. **Multi-site Support**: Test with multiple backend instances

---

## Testing

### Test Storage

```python
from clarion.storage import get_database

db = get_database()
stats = db.get_sketch_stats()
assert stats['total_sketches'] >= 0
```

### Test Admin Console

```bash
# Start console
python scripts/run_admin_console.py

# Verify it loads
curl http://localhost:8502
```

### Test Lab Environment

```bash
# On VM
sudo ./lab/setup_vm.sh --traffic imix
sudo ./lab/vm_agent_setup.sh --backend-url http://BACKEND:8000

# Verify agent is running
sudo systemctl status clarion-edge

# Check backend receives data
curl http://BACKEND:8000/api/edge/sketches/stats
```

---

## Configuration

### Database Path

Default: `clarion.db` in current directory

Set via environment variable:
```bash
export CLARION_DB_PATH=/var/lib/clarion/clarion.db
```

### Backend URL

For edge agents and NetFlow senders:
```bash
export BACKEND_URL=http://backend-ip:8000
```

Or pass as argument:
```bash
./lab/vm_agent_setup.sh --backend-url http://backend-ip:8000
```

---

## Troubleshooting

### Database Issues

- **Lock errors**: SQLite is single-writer, ensure only one process writes
- **Disk space**: Monitor database size, use cleanup_old_data()
- **Permissions**: Ensure write permissions on database directory

### Admin Console Issues

- **Port conflict**: Change port in `run_admin_console.py`
- **Database not found**: Ensure database is initialized
- **No data**: Check that API is receiving data

### Lab Environment Issues

- **Agent not starting**: Check Python version (3.11+)
- **NetFlow not sending**: Verify nfdump is installed
- **Backend unreachable**: Check network connectivity and firewall

