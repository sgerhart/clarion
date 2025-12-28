# Quick Start Guide - Complete System

This guide walks you through running the complete Clarion system end-to-end, including the backend, frontend UI, and lab environment.

## Prerequisites

- Python 3.11+
- Virtual environment activated (recommended: `pyenv`)
- All dependencies installed (`pip install -r requirements.txt`)
- Node.js 18+ (for React frontend)

## 🎯 Quickest Start (One Command)

**Run this one command to see everything:**

```bash
python scripts/run_complete_system.py --mode demo
```

This will:
1. ✅ Start the backend API (port 8000)
2. ✅ Initialize the SQLite database
3. ✅ Load synthetic data (flows → sketches → clusters → policies)
4. ✅ Start the React frontend (port 3000)

**Then open:** `http://localhost:3000` to see the UI with all your data!

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

### Step 3: Start the React Frontend

```bash
# Terminal 3
cd frontend
npm install  # First time only
npm run dev
```

Open your browser to `http://localhost:3000` to see:
- Dashboard with system metrics
- Network flows visualization
- Clusters and device memberships
- SGT matrix heatmap
- Policy builder
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

# Verify data loaded
sqlite3 clarion.db "SELECT COUNT(*) FROM sketches;"
```

---

## Troubleshooting

### Frontend Issues

#### No Data Showing in React Frontend

**Quick Checks:**
1. **Is the backend API running?**
   ```bash
   curl http://localhost:8000/health
   ```
   Should return: `{"status":"healthy",...}`

2. **Is data in the database?**
   ```bash
   sqlite3 clarion.db "SELECT COUNT(*) FROM sketches;"
   ```
   Should show: `13300` (or similar)

3. **Check browser console**
   - Open DevTools (F12)
   - Check Console tab for errors
   - Check Network tab for failed API calls

#### Issue 1: API Not Running

**Symptoms:**
- Frontend shows "Loading..." forever
- Browser console shows network errors
- API calls return 404 or connection refused

**Solution:**
```bash
# Start the backend API
python scripts/run_api.py --port 8000
```

#### Issue 2: CORS Errors

**Symptoms:**
- Browser console shows CORS errors
- Network tab shows preflight failures

**Solution:**
- CORS is already configured in `src/clarion/api/app.py`
- Make sure backend is running on port 8000
- Frontend should be on port 3000

#### Issue 3: No Data in Database

**Symptoms:**
- API returns empty arrays
- Dashboard shows zeros

**Solution:**
```bash
# Load data into database
python scripts/load_data_to_db.py
python scripts/load_flows_to_db.py
```

#### Issue 4: API Returns Data But Frontend Doesn't Show It

**Symptoms:**
- API calls succeed (check Network tab)
- But UI shows empty/loading

**Solution:**
- Check browser console for JavaScript errors
- Verify data structure matches what frontend expects
- Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)

### Common Issues

#### "Port already in use"

```bash
# Find what's using the port
lsof -i :8000
lsof -i :3000

# Kill the process or use different ports
python scripts/run_api.py --port 8001
# Update frontend/.env to point to port 8001
```

#### "Database locked"

SQLite is single-writer. If you see lock errors:
- Close any other database connections
- Restart the API
- Ensure only one process is writing

#### "Admin console not loading" / Frontend Issues

```bash
# Check if Node.js is installed
node --version

# Reinstall dependencies
cd frontend
rm -rf node_modules package-lock.json
npm install

# Try running directly
npm run dev
# Opens at http://localhost:3000
```

### Testing API Endpoints Manually

```bash
# Health check
curl http://localhost:8000/health

# Sketch stats
curl http://localhost:8000/api/edge/sketches/stats

# Clusters
curl http://localhost:8000/api/clustering/clusters

# NetFlow (first 5 records)
curl 'http://localhost:8000/api/netflow/netflow?limit=5'

# Cluster members (cluster 0)
curl http://localhost:8000/api/clustering/clusters/0/members
```

### Quick Fixes

**Restart Everything:**
```bash
# Stop all processes
pkill -f "run_api"
pkill -f "vite"

# Start backend
python scripts/run_api.py --port 8000 &

# Start frontend (in another terminal)
cd frontend
npm run dev
```

**Clear Browser Cache:**
- Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
- Or open in incognito/private window

**Reload Data:**
```bash
# Reload all data
python scripts/load_data_to_db.py
python scripts/load_flows_to_db.py
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

Open `http://localhost:3000` to monitor:
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

### Frontend Not Loading

```bash
# Check if port is in use
lsof -i :3000

# Check Node.js
node --version
npm --version

# Try running directly
cd frontend && npm run dev
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
2. **Run Clustering** - Use the API or React frontend to cluster endpoints
3. **Generate Policies** - Create SGACL policies from clusters
4. **Customize Policies** - Use the customization workflow
5. **Export Policies** - Export to Cisco ISE format

For more details, see:
- [Lab README](lab/README.md) - Complete lab setup guide
- [VM Architecture](lab/VM_ARCHITECTURE.md) - VM specifications
- [API Documentation](http://localhost:8000/api/docs) - Interactive API docs (when API is running)

