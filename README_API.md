# Clarion API & UI

## Running the API Server

Start the FastAPI backend:

```bash
# Using the script
python scripts/run_api.py

# Or directly with uvicorn
uvicorn clarion.api.app:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API Docs**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **Health Check**: http://localhost:8000/health

## Running the React Frontend

Start the production React UI:

```bash
cd frontend
npm install  # First time only
npm run dev
```

The UI will open in your browser at http://localhost:3000

For setup instructions, see [REACT_FRONTEND.md](REACT_FRONTEND.md).

## API Endpoints

### Health
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health with metrics

### Edge (Sketch Ingestion)
- `POST /api/edge/sketches` - Receive sketches from edge devices
- `POST /api/edge/sketches/binary` - Receive binary-encoded sketches
- `GET /api/edge/sketches` - List stored sketches
- `GET /api/edge/sketches/stats` - Get sketch statistics

### Clustering
- `POST /api/clustering/run` - Run clustering analysis
- `GET /api/clustering/results` - Get clustering results

### Policy
- `POST /api/policy/generate` - Generate SGACL policies
- `GET /api/policy/matrix` - Get policy matrix
- `GET /api/policy/sgacls` - List SGACL policies
- `GET /api/policy/impact` - Get impact analysis

### Visualization
- `POST /api/viz/clusters` - Generate cluster visualization data
- `GET /api/viz/matrix/heatmap` - Get policy matrix heatmap data
- `GET /api/viz/clusters/distribution` - Get cluster distribution
- `GET /api/viz/endpoints/timeline` - Get endpoint timeline

### Export
- `GET /api/export/cisco-cli` - Download Cisco CLI configuration
- `GET /api/export/ise-json` - Download ISE JSON export
- `GET /api/export/json` - Download complete JSON export

## Example: Testing Edge Sync

Send test sketches from an edge device:

```bash
curl -X POST http://localhost:8000/api/edge/sketches \
  -H "Content-Type: application/json" \
  -d '{
    "switch_id": "switch-001",
    "timestamp": 1704067200,
    "sketch_count": 2,
    "sketches": [
      {
        "endpoint_id": "aa:bb:cc:dd:ee:ff",
        "switch_id": "switch-001",
        "unique_peers": 10,
        "unique_ports": 5,
        "bytes_in": 1000000,
        "bytes_out": 2000000,
        "flow_count": 500,
        "first_seen": 1704060000,
        "last_seen": 1704067200,
        "active_hours": 255,
        "local_cluster_id": 0
      }
    ]
  }'
```

## Example: Running Clustering

```bash
curl -X POST http://localhost:8000/api/clustering/run \
  -H "Content-Type: application/json" \
  -d '{
    "min_cluster_size": 50,
    "min_samples": 10
  }'
```

