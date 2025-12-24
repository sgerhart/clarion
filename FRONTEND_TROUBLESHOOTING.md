# Frontend Troubleshooting Guide

## No Data Showing in React Frontend

### Quick Checks

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

### Common Issues

#### Issue 1: API Not Running

**Symptoms:**
- Frontend shows "Loading..." forever
- Browser console shows network errors
- API calls return 404 or connection refused

**Solution:**
```bash
# Start the backend API
cd /path/to/clarion
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

### Expected API Responses

**Sketch Stats:**
```json
{
  "total_sketches": 13300,
  "total_flows": 106814,
  "switches": 80,
  "unique_endpoints": 13300
}
```

**Clusters:**
```json
[
  {
    "cluster_id": 0,
    "cluster_label": "Printers",
    "sgt_value": 20,
    "sgt_name": "Printers",
    "endpoint_count": 0
  },
  ...
]
```

**NetFlow:**
```json
{
  "count": 5,
  "records": [
    {
      "src_ip": "10.6.60.157",
      "dst_ip": "10.250.210.190",
      "src_port": 4854,
      "dst_port": 8080,
      "protocol": 6,
      "bytes": 8398,
      "packets": 32,
      "flow_start": 1766538576,
      "flow_end": 1766538636
    },
    ...
  ]
}
```

### Browser DevTools Checks

1. **Console Tab:**
   - Look for red error messages
   - Check for API call errors
   - Verify React Query is working

2. **Network Tab:**
   - Filter by "Fetch/XHR"
   - Check if API calls are being made
   - Verify response status (should be 200)
   - Check response body contains data

3. **Application Tab:**
   - Check if React Query cache has data
   - Verify no CORS issues

### Quick Fixes

**Restart Everything:**
```bash
# Stop all processes
pkill -f "run_api"
pkill -f "streamlit"
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

### Still Not Working?

1. Check backend logs: `tail -f /tmp/clarion_api.log`
2. Check frontend console for specific errors
3. Verify database has data: `sqlite3 clarion.db "SELECT COUNT(*) FROM sketches;"`
4. Test API directly: `curl http://localhost:8000/api/edge/sketches/stats`

