# Final Setup - See It All Working Together

## 🎯 Quick Answer

**Run this one command to see everything:**

```bash
python scripts/run_complete_system.py --mode demo
```

This will:
1. ✅ Start the backend API (port 8000)
2. ✅ Initialize the SQLite database
3. ✅ Load synthetic data (flows → sketches → clusters → policies)
4. ✅ Start the admin console (port 8502)
5. ✅ Open your browser automatically

**Then open:** `http://localhost:8502` to see the admin console with all your data!

---

## 📋 What You'll See

### In the Admin Console

1. **Dashboard Tab**
   - Total endpoints: ~13,300
   - Total sketches: matches endpoints
   - Active clusters: 8
   - Policies: 8 SGACL policies
   - System health: ✅ Healthy

2. **Sketches Tab**
   - All edge sketches from synthetic data
   - Flow counts, bytes, unique peers
   - Charts showing distribution

3. **Clusters Tab**
   - 8 discovered clusters
   - SGT assignments
   - Endpoint counts per cluster

4. **Policies Tab**
   - Generated SGACL policies
   - Permit/deny distribution
   - Policy matrix visualization

### In the API

Visit `http://localhost:8000/api/docs` to see:
- All 23+ endpoints
- Interactive API documentation
- Test endpoints directly

### In the Database

```bash
# Check database
ls -lh clarion.db

# Query directly
sqlite3 clarion.db "SELECT COUNT(*) FROM sketches;"
sqlite3 clarion.db "SELECT COUNT(*) FROM clusters;"
sqlite3 clarion.db "SELECT COUNT(*) FROM policies;"
```

---

## 🔄 Alternative Workflows

### Option 1: Manual Step-by-Step

```bash
# Terminal 1: Start API
python scripts/run_api.py --port 8000

# Terminal 2: Load data
python scripts/test_system.py

# Terminal 3: Start admin console
python scripts/run_admin_console.py
```

### Option 2: API Only (No UI)

```bash
python scripts/run_complete_system.py --mode api-only
```

Then visit: `http://localhost:8000/api/docs`

### Option 3: With Lab VMs

```bash
# On host: Start API (accessible from VMs)
python scripts/run_api.py --port 8000 --host 0.0.0.0

# On each VM:
sudo ./lab/setup_vm.sh --traffic imix
sudo ./lab/vm_agent_setup.sh --backend-url http://HOST_IP:8000
sudo ./lab/vm_netflow_sender.sh --backend-url http://HOST_IP:8000

# On host: Start admin console
python scripts/run_admin_console.py
```

---

## ✅ Verification Checklist

After running the system, verify:

- [ ] API is running: `curl http://localhost:8000/api/health`
- [ ] Database exists: `ls -lh clarion.db`
- [ ] Sketches in database: `sqlite3 clarion.db "SELECT COUNT(*) FROM sketches;"` (should be > 0)
- [ ] Admin console loads: `http://localhost:8502`
- [ ] Dashboard shows data: Endpoints > 0, Sketches > 0
- [ ] Clusters visible: Navigate to Clusters tab
- [ ] Policies visible: Navigate to Policies tab

---

## 🎓 What's Happening Behind the Scenes

1. **API Startup**
   - FastAPI server starts
   - SQLite database initializes (creates `clarion.db`)
   - All tables created (sketches, netflow, clusters, policies, etc.)

2. **Data Loading** (if using demo mode)
   - Loads synthetic CSV data (106K+ flows)
   - Builds behavioral sketches for each endpoint
   - Enriches with identity (IP → User → AD Groups)
   - Runs HDBSCAN clustering (finds 8 clusters)
   - Generates SGT taxonomy
   - Builds policy matrix
   - Generates SGACL policies
   - **All stored in database**

3. **Admin Console**
   - Connects to database
   - Queries all tables
   - Displays data in interactive UI
   - Real-time visualizations

---

## 🐛 Troubleshooting

### "Port already in use"

```bash
# Find what's using the port
lsof -i :8000
lsof -i :8502

# Kill the process or use different ports
python scripts/run_complete_system.py --api-port 8001 --admin-port 8503
```

### "Database locked"

SQLite is single-writer. If you see lock errors:
- Close any other database connections
- Restart the API
- Ensure only one process is writing

### "No data in admin console"

1. Check database exists: `ls -lh clarion.db`
2. Check data loaded: `sqlite3 clarion.db "SELECT COUNT(*) FROM sketches;"`
3. Refresh the admin console (data loads on page load)
4. Check API: `curl http://localhost:8000/api/edge/sketches/stats`

### "Admin console not loading"

```bash
# Check Streamlit is installed
pip list | grep streamlit

# Try running directly
streamlit run src/clarion/ui/admin_console.py --server.port 8502
```

---

## 📚 Next Steps

Once you see everything working:

1. **Explore the Admin Console**
   - Navigate through all tabs
   - Try filtering sketches by switch
   - View cluster visualizations
   - Check policy matrix

2. **Use the API**
   - Visit `/api/docs` for interactive docs
   - Try clustering endpoint: `POST /api/clustering/run`
   - Generate policies: `POST /api/policy/generate`

3. **Test with Lab Environment**
   - Set up VMs with edge agents
   - Watch real-time data flow
   - Generate fake ISE/AD logs

4. **Customize Policies**
   - Use the customization workflow
   - Rename SGTs
   - Modify SGACL rules
   - Export to ISE format

---

## 📖 Documentation

- **[QUICK_START.md](QUICK_START.md)** - Detailed quick start guide
- **[STORAGE_AND_LAB.md](STORAGE_AND_LAB.md)** - Storage and lab implementation
- **[lab/README.md](lab/README.md)** - Lab environment setup
- **[README_API.md](README_API.md)** - API documentation

---

## 🎉 You're Ready!

Run the command and watch the magic happen:

```bash
python scripts/run_complete_system.py --mode demo
```

Then open `http://localhost:8502` and explore your complete Clarion system! 🚀

