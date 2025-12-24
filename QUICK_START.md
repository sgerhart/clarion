# Quick Start Guide - Complete System

This guide walks you through running the complete Clarion system end-to-end, including the backend, admin console, and lab environment.

## Prerequisites

- Python 3.11+
- Virtual environment activated
- All dependencies installed (`pip install -r requirements.txt`)

## Option 1: Quick Demo (Synthetic Data)

This option uses the existing synthetic data to demonstrate the full system without VMs.

### Step 1: Start the Backend API

```bash
# Terminal 1
python scripts/run_api.py --port 8000
```

The API will:
- Initialize the SQLite database (`clarion.db`)
- Start on `http://localhost:8000`
- API docs at `http://localhost:8000/api/docs`

### Step 2: Load Synthetic Data

```bash
# Terminal 2
python scripts/test_system.py
```

This will:
- Load synthetic flow data
- Build sketches
- Run clustering
- Generate policies
- Store everything in the database

### Step 3: Start the Admin Console

```bash
# Terminal 3
python scripts/run_admin_console.py
```

Open your browser to `http://localhost:8502` to see:
- Dashboard with system metrics
- Sketches from the synthetic data
- Clusters and policies
- Visualizations

### Step 4: Verify Everything

```bash
# Check API health
curl http://localhost:8000/api/health

# Check sketch stats
curl http://localhost:8000/api/edge/sketches/stats

# Check database
ls -lh clarion.db
```

---

## Option 2: Full Lab Environment (VMs)

This option uses the lab environment with VMs, edge agents, and NetFlow.

### Step 1: Start the Backend API

```bash
# Terminal 1 (on your host machine)
python scripts/run_api.py --port 8000 --host 0.0.0.0
```

**Note:** Use `--host 0.0.0.0` so VMs can reach it.

### Step 2: Setup VMs

On each VM (VM1, VM2, VM3):

```bash
# Base setup with traffic
sudo ./lab/setup_vm.sh --traffic imix

# Setup edge agent
sudo ./lab/vm_agent_setup.sh --backend-url http://HOST_IP:8000

# Setup NetFlow sender
sudo ./lab/vm_netflow_sender.sh --backend-url http://HOST_IP:8000
```

Replace `HOST_IP` with your host machine's IP address.

### Step 3: Generate Fake Logs

On your host machine:

```bash
# Generate ISE logs
python3 lab/generate_fake_ise.py \
    -o lab/data/ise_sessions.json \
    -d 24 \
    -e 5

# Generate AD logs
python3 lab/generate_fake_ad.py \
    -o lab/data/ad_logs.json \
    -d 24 \
    -e 3
```

### Step 4: Start Admin Console

```bash
# Terminal 2 (on your host machine)
python scripts/run_admin_console.py
```

Open `http://localhost:8502` to monitor:
- Sketches coming from edge agents
- NetFlow records
- Real-time system metrics

### Step 5: Verify Data Flow

```bash
# Check edge agent status (on VMs)
sudo systemctl status clarion-edge
sudo journalctl -f -u clarion-edge

# Check NetFlow sender (on VMs)
sudo systemctl status clarion-netflow
sudo journalctl -f -u clarion-netflow

# Check backend (on host)
curl http://localhost:8000/api/edge/sketches/stats
curl http://localhost:8000/api/netflow/netflow?limit=10
```

---

## Option 3: Hybrid (Simulator + Real Backend)

This option uses the edge simulator locally but connects to a real backend.

### Step 1: Start Backend

```bash
# Terminal 1
python scripts/run_api.py --port 8000
```

### Step 2: Run Edge Simulator

```bash
# Terminal 2
cd edge
PYTHONPATH=.. python -m clarion_edge.main \
    --mode simulator \
    --backend-url http://localhost:8000 \
    --switch-id SW-SIM-001 \
    --duration 300
```

This will:
- Generate synthetic flows
- Build sketches
- Send to backend every 30 seconds

### Step 3: Start Admin Console

```bash
# Terminal 3
python scripts/run_admin_console.py
```

Watch the admin console update in real-time as sketches arrive.

---

## Complete Workflow Script

For convenience, use the orchestration script:

```bash
python scripts/run_complete_system.py --mode demo
```

This script will:
1. Start the backend API
2. Load synthetic data
3. Start the admin console
4. Open your browser

---

## What to Look For

### In the Admin Console

1. **Dashboard Tab**
   - Total endpoints should be > 0
   - Total sketches should match endpoints
   - System health should show "✅ Healthy"

2. **Sketches Tab**
   - Should see sketches from switches
   - Flow counts should be > 0
   - Charts should show data distribution

3. **NetFlow Tab** (if using lab environment)
   - Should see recent NetFlow records
   - Top talkers should be populated
   - Time-based filtering works

4. **Clusters Tab**
   - Should see clusters after running clustering
   - SGT assignments visible
   - Endpoint counts per cluster

5. **Policies Tab**
   - Should see generated policies
   - Permit/deny distribution
   - Policy matrix visualization

### In the API

```bash
# Health check
curl http://localhost:8000/api/health
# Should return: {"status": "healthy"}

# Sketch stats
curl http://localhost:8000/api/edge/sketches/stats
# Should show total_sketches > 0

# List sketches
curl http://localhost:8000/api/edge/sketches?limit=10
# Should return sketch data
```

### In the Database

```bash
# Check database exists
ls -lh clarion.db

# Check size (should grow as data is added)
du -h clarion.db

# Query directly (optional)
sqlite3 clarion.db "SELECT COUNT(*) FROM sketches;"
sqlite3 clarion.db "SELECT COUNT(*) FROM netflow;"
```

---

## Troubleshooting

### Backend Not Starting

```bash
# Check if port is in use
lsof -i :8000

# Check Python version
python --version  # Should be 3.11+

# Check dependencies
pip list | grep fastapi
```

### Admin Console Not Loading

```bash
# Check if port is in use
lsof -i :8502

# Check Streamlit
pip list | grep streamlit

# Try running directly
streamlit run src/clarion/ui/admin_console.py --server.port 8502
```

### No Data in Admin Console

1. **Check database exists**: `ls -lh clarion.db`
2. **Check API is receiving data**: `curl http://localhost:8000/api/edge/sketches/stats`
3. **Refresh admin console** (data loads on page load)
4. **Check database directly**: `sqlite3 clarion.db "SELECT COUNT(*) FROM sketches;"`

### Edge Agent Not Sending Data

1. **Check service status**: `sudo systemctl status clarion-edge`
2. **Check logs**: `sudo journalctl -f -u clarion-edge`
3. **Verify backend URL**: Check the service file for correct URL
4. **Test connectivity**: `curl http://BACKEND_IP:8000/api/health` from VM

### Database Locked

SQLite is single-writer. If you see lock errors:
- Ensure only one process is writing
- Close any database connections
- Restart the API

---

## Next Steps

Once everything is running:

1. **Explore the Admin Console** - Navigate through all tabs
2. **Run Clustering** - Use the API or Streamlit UI to cluster endpoints
3. **Generate Policies** - Create SGACL policies from clusters
4. **Customize Policies** - Use the customization workflow
5. **Export Policies** - Export to Cisco ISE format

For more details, see:
- [Storage & Lab Environment](STORAGE_AND_LAB.md)
- [Lab README](lab/README.md)
- [API Documentation](README_API.md)

