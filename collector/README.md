# Clarion Collector

Central collector for NetFlow/IPFIX data and edge agent sketches.

## Overview

The Clarion Collector supports two modes:

1. **Native NetFlow Collector** - Receives NetFlow v5/v9 and IPFIX directly from switches via UDP
2. **Agent Collector** - Receives sketches from edge agents via HTTP and forwards to backend

## Installation

```bash
cd collector
pip install -r requirements.txt
```

Or install in development mode:

```bash
pip install -e .
```

## Usage

### Native NetFlow Collector

Listens on UDP ports for NetFlow/IPFIX packets from switches:

```bash
python -m clarion_collector.main --mode native --backend-url http://localhost:8000
```

Configuration via environment variables:

```bash
export CLARION_COLLECTOR_BACKEND_URL=http://backend:8000
export CLARION_COLLECTOR_NETFLOW_PORT=2055
export CLARION_COLLECTOR_IPFIX_PORT=4739
export CLARION_COLLECTOR_BATCH_SIZE=1000
export CLARION_COLLECTOR_BATCH_INTERVAL=5.0

python -m clarion_collector.main --mode native
```

### Agent Collector

Provides HTTP endpoint for edge agents to send sketches:

```bash
python -m clarion_collector.main --mode agent --backend-url http://localhost:8000 --agent-port 8080
```

Edge agents can then connect to the collector instead of directly to the backend:

```bash
# In edge agent config
BACKEND_URL=http://collector:8080
```

### Both Collectors

Run both collectors simultaneously:

```bash
python -m clarion_collector.main --mode both --backend-url http://localhost:8000
```

## Configuration

### Environment Variables

- `CLARION_COLLECTOR_BACKEND_URL` - Backend API URL (default: `http://localhost:8000`)
- `CLARION_COLLECTOR_NETFLOW_PORT` - NetFlow UDP port (default: `2055`)
- `CLARION_COLLECTOR_IPFIX_PORT` - IPFIX UDP port (default: `4739`)
- `CLARION_COLLECTOR_SFLOW_PORT` - sFlow UDP port (default: `6343`, not yet implemented)
- `CLARION_COLLECTOR_BIND_HOST` - Host to bind to (default: `0.0.0.0`)
- `CLARION_COLLECTOR_BATCH_SIZE` - Batch size for NetFlow records (default: `1000`)
- `CLARION_COLLECTOR_BATCH_INTERVAL` - Batch interval in seconds (default: `5.0`)
- `CLARION_COLLECTOR_SWITCH_ID_FROM_IP` - Use source IP as switch_id (default: `true`)
- `CLARION_COLLECTOR_LOG_LEVEL` - Logging level (default: `INFO`)
- `CLARION_COLLECTOR_UDP_RCVBUF` - UDP receive buffer size in bytes (requires privileges, default: OS default)
- `CLARION_COLLECTOR_RETRY_ATTEMPTS` - Maximum retry attempts for backend requests (default: `3`)
- `CLARION_COLLECTOR_RETRY_BACKOFF` - Retry backoff factor (default: `1.5`)

### Command Line Arguments

```bash
python -m clarion_collector.main --help
```

Options:
- `--mode` - Collector mode: `native`, `agent`, or `both` (default: `both`)
- `--backend-url` - Backend API URL
- `--netflow-port` - NetFlow UDP port
- `--ipfix-port` - IPFIX UDP port
- `--agent-port` - Agent collector HTTP port (default: `8080`)
- `--log-level` - Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- `--batch-size` - Batch size for NetFlow records
- `--batch-interval` - Batch interval in seconds

## Docker

### Build

```bash
docker build -t clarion-collector:latest .
```

### Run

```bash
docker run -d \
  --name clarion-collector \
  -p 2055:2055/udp \
  -p 4739:4739/udp \
  -p 8080:8080/tcp \
  -p 8081:8081/tcp \
  -e CLARION_COLLECTOR_BACKEND_URL=http://backend:8000 \
  clarion-collector:latest \
  --mode both
```

### Docker Compose

```bash
docker-compose up -d
```

## Supported Formats

### NetFlow v5

✅ Fully supported - Fixed format, no templates required

Fields extracted:
- Source/Destination IP addresses
- Source/Destination ports
- Protocol
- Bytes and packets
- Flow timestamps
- Switch ID (from source IP)

### NetFlow v9

✅ Fully supported - Template-based format with full template parsing

Features:
- Template record handling and storage
- Dynamic field mapping based on templates
- Support for enterprise-specific fields (e.g., SGT via enterprise field IDs)
- Data flow set parsing with template-based field extraction

### IPFIX

✅ Fully supported - Template-based format with full IE mapping

Features:
- Information Element (IE) mapping (standard IANA IEs)
- Template record handling and storage
- Support for enterprise-specific IEs (SGT via IE 411/412)
- Data set parsing with template-based field extraction

### sFlow

❌ Not yet implemented

## Health Check

Both collectors provide health check endpoints:

**Agent Collector:**
```bash
curl http://localhost:8080/health
```

**Native Collector:**
```bash
curl http://localhost:8081/health
```

Response:
```json
{
  "status": "healthy",
  "service": "native-netflow-collector",
  "backend_url": "http://backend:8000"
}
```

## Metrics

Both collectors provide metrics endpoints:

**Agent Collector:**
```bash
curl http://localhost:8080/metrics
```

**Native Collector:**
```bash
curl http://localhost:8081/metrics
```

Response:
```json
{
  "total_received": 1000,
  "total_sent": 1000,
  "pending": 0,
  "errors": 0,
  "batch_size": 1000,
  "batch_interval_seconds": 5.0
}
```

## Architecture

```
Switches                    Collector                    Backend
  |                            |                           |
  | NetFlow v5/v9/IPFIX (UDP)  |                           |
  |--------------------------->|                           |
  |                            | HTTP POST /api/netflow/   |
  |                            |-------------------------->|
  |                            |                           |
  |                            |                           |
Edge Agents                    |                           |
  |                            |                           |
  | HTTP POST /api/edge/       |                           |
  |--------------------------->|                           |
  |                            | HTTP POST /api/edge/      |
  |                            |-------------------------->|
```

## Development

### Running Tests

```bash
# Unit tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=clarion_collector --cov-report=term-missing
```


### Code Structure

```
collector/
├── clarion_collector/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── config.py            # Configuration
│   ├── native_collector.py  # Native NetFlow/IPFIX collector
│   ├── agent_collector.py   # Agent collector
│   ├── netflow_parser.py    # NetFlow v5 parser
│   ├── netflow_v9.py        # NetFlow v9 parser (templates)
│   ├── ipfix_parser.py      # IPFIX parser (templates)
│   └── retry.py             # Retry logic with backoff
├── tests/                   # Unit tests
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Scalability

### Current Scale Limitations

**Single Instance Capacity:**
- Single asyncio event loop (single-threaded async)
- Single UDP socket per port (NetFlow/IPFIX)
- In-memory batching (no persistence)
- Default batch size: 1000 records
- Default batch interval: 5 seconds
- Maximum throughput per instance: ~200 records/second (theoretical)

**Estimated Capacity per Instance:**
- **Light load:** ~100K flows/hour (28 flows/sec)
- **Medium load:** ~500K flows/hour (140 flows/sec)  
- **Heavy load:** ~1M flows/hour (280 flows/sec) - may hit limits

**Bottlenecks:**
1. UDP packet processing (asyncio loop)
2. Batch processing overhead
3. HTTP POST to backend (network latency)
4. Memory usage (grows with batch size)

### Scaling Strategies

#### Option 1: Horizontal Scaling with SO_REUSEPORT (Recommended)

**How it works:**
- Multiple collector instances bind to the same UDP port using `SO_REUSEPORT`
- OS kernel load balances UDP packets across instances
- Each instance processes packets independently

**Pros:**
- True horizontal scaling
- OS-level load balancing (efficient)
- No single point of failure
- Linear scalability (2x instances ≈ 2x capacity)

**Cons:**
- Requires OS support (Linux 3.9+, modern kernels)
- Packet ordering not guaranteed (acceptable for NetFlow)
- Each switch IP must be hashed consistently (not an issue for NetFlow)

**Deployment:**
```bash
# Docker Compose - scale to 3 instances
docker-compose up -d --scale collector=3

# Kubernetes - scale deployment
kubectl scale deployment clarion-collector --replicas=3
```

#### Option 2: Load Balancer in Front (For VMs/Containers)

**Architecture:**
```
Switches → Load Balancer (UDP) → Multiple Collector Instances → Backend
```

**Load Balancer Options:**
- **Linux IPVS** (kernel-level, high performance)
- **HAProxy** (UDP mode, stateless)
- **Nginx** (UDP stream module)
- **Cloud Load Balancers** (AWS ELB, GCP Load Balancer, Azure LB)

#### Option 3: Switch-Level Distribution

**How it works:**
- Configure different switches to send to different collector instances
- Use DNS round-robin or switch grouping

### Deployment Options

**Container Deployment (Recommended):**
- ✅ Easy scaling (Kubernetes/Docker Compose)
- ✅ Consistent environments
- ✅ Resource limits and isolation
- ✅ Easy updates and rollbacks
- ✅ Health checks and auto-restart
- ✅ SO_REUSEPORT works well in containers

**VM Deployment:**
- ✅ Full OS control
- ✅ Better for bare metal deployments
- ✅ Can optimize OS settings (kernel parameters)
- ✅ No container overhead
- ❌ Manual scaling (need to provision VMs)
- ❌ More complex updates

### Performance Optimization

1. **Increase Batch Size:**
   ```bash
   CLARION_COLLECTOR_BATCH_SIZE=5000  # Default: 1000
   ```

2. **Decrease Batch Interval:**
   ```bash
   CLARION_COLLECTOR_BATCH_INTERVAL=2.0  # Default: 5.0 seconds
   ```

3. **Socket Buffer Sizes:**
   ```python
   # Increase UDP receive buffer (requires root/privileges)
   sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4194304)  # 4MB
   ```

### Capacity Planning

**Formula:**
```
Instances = (Peak flows/sec) / (Instance capacity)
```

**Example:**
- Peak traffic: 10M flows/hour = 2,778 flows/sec
- Instance capacity: 250 flows/sec
- Required instances: 2,778 / 250 = **~12 instances**

**With Safety Margin (2x):**
```
Instances = (Peak flows/sec) / (Instance capacity) * 2
= 2,778 / 250 * 2 = ~22 instances
```

### Resource Requirements per Instance

| Load Level | CPU | Memory | Network | Notes |
|------------|-----|--------|---------|-------|
| Light (<100K/hr) | 0.1 cores | 128 MB | Low | Development/small networks |
| Medium (100K-1M/hr) | 0.25 cores | 256 MB | Moderate | Typical production |
| Heavy (1M-10M/hr) | 0.5 cores | 512 MB | High | Large enterprise |
| Very Heavy (>10M/hr) | 1+ cores | 1 GB+ | Very High | Scale horizontally instead |

### Recommended Deployment Architecture

**Small Scale (< 1M flows/hour):**
- **Instances:** 1-2 collectors
- **Deployment:** Docker Compose or single VM
- **Load Balancer:** Not needed (direct switch config)

**Medium Scale (1M - 10M flows/hour):**
- **Instances:** 3-10 collectors
- **Deployment:** Kubernetes with SO_REUSEPORT
- **Load Balancer:** Optional (OS handles with SO_REUSEPORT)
- **Auto-scaling:** Based on CPU/memory metrics

**Large Scale (> 10M flows/hour):**
- **Instances:** 10+ collectors
- **Deployment:** Kubernetes or VMs with load balancer
- **Load Balancer:** Required (HAProxy or cloud LB)
- **Auto-scaling:** Horizontal Pod Autoscaler (K8s) or VM auto-scaling
- **Regional Distribution:** Deploy collectors close to switches

## Testing

This section covers how to test the Clarion native NetFlow collector at various levels.

### Unit Tests

**Running Unit Tests:**

From the `collector/` directory:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_netflow_v5.py -v

# Run with coverage
pytest tests/ -v --cov=clarion_collector --cov-report=term-missing

# Run with detailed output
pytest tests/ -v -s
```

**Test Coverage:**

Current test coverage includes:
- ✅ NetFlow v5 parser (header parsing, record parsing, error handling)
- ✅ NetFlow v9 template parsing (template storage, validation)

**Missing test coverage:**
- ⚠️ NetFlow v9 data record parsing (with templates)
- ⚠️ IPFIX parser tests
- ⚠️ End-to-end collector integration tests
- ⚠️ Retry logic tests
- ⚠️ Metrics/health endpoint tests

### Running the Collector

**Basic Setup:**

1. **Install dependencies:**
```bash
cd collector
pip install -r requirements.txt
```

2. **Start the collector:**
```bash
# Native collector only
python -m clarion_collector.main --mode native \
  --backend-url http://localhost:8000 \
  --netflow-port 2055 \
  --ipfix-port 4739 \
  --log-level DEBUG

# Both native and agent collectors
python -m clarion_collector.main --mode both
```

**Environment Variables:**

Alternatively, use environment variables:

```bash
export CLARION_COLLECTOR_BACKEND_URL=http://localhost:8000
export CLARION_COLLECTOR_NETFLOW_PORT=2055
export CLARION_COLLECTOR_IPFIX_PORT=4739
export CLARION_COLLECTOR_LOG_LEVEL=DEBUG

python -m clarion_collector.main --mode native
```

### Manual Testing with Test Packets

**Method 1: Using Python socket (Quick Test)**

A simple test script (`tests/test_send_packet.py`) is provided to send NetFlow v5 packets:

```bash
python tests/test_send_packet.py
```

**Method 2: Using nfdump/nfsend (Realistic Test)**

If you have `nfdump` installed, you can use `nfsend` to send NetFlow packets:

```bash
# Send a single NetFlow v5 packet
echo "10.0.0.1,10.0.0.2,12345,80,6,10,1500" | \
  nfsend -S localhost:2055 -v 5
```

**Method 3: Using softflowd (Flow Generator)**

Use `softflowd` to generate NetFlow from actual traffic:

```bash
# Install softflowd (Ubuntu/Debian)
sudo apt-get install softflowd

# Generate NetFlow from interface traffic
sudo softflowd -i eth0 -n 127.0.0.1:2055 -v 5

# Or read from a pcap file
sudo softflowd -r capture.pcap -n 127.0.0.1:2055 -v 5
```

### Integration Testing

**Full Integration Test:**

1. **Start the backend API:**
```bash
# In another terminal
cd /path/to/clarion
python scripts/run_api.py --port 8000
```

2. **Start the collector:**
```bash
cd collector
python -m clarion_collector.main --mode native \
  --backend-url http://localhost:8000 \
  --log-level DEBUG
```

3. **Send test packets** (using one of the methods above)

4. **Verify data in backend:**
```bash
# Check health
curl http://localhost:8000/api/health

# Check NetFlow records (should see your test packets)
curl http://localhost:8000/api/netflow/netflow?limit=10
```

**Expected Behavior:**

When working correctly:
- Collector logs should show: "Parsed N NetFlow v5 records from 127.0.0.1"
- Collector logs should show: "Sent N NetFlow records from 127.0.0.1"
- Backend API should return NetFlow records with your test data
- Collector metrics should show `total_received` > 0

### Health and Metrics Testing

**Health Check:**

```bash
# Check collector health
curl http://localhost:8081/health

# Expected response:
# {
#   "status": "healthy",
#   "service": "native-netflow-collector",
#   "backend_url": "http://localhost:8000"
# }
```

**Metrics Endpoint:**

```bash
# Get collector metrics
curl http://localhost:8081/metrics

# Expected response:
# {
#   "total_received": 100,
#   "total_sent": 100,
#   "pending": 0,
#   "errors": 0,
#   "batch_size": 1000,
#   "batch_interval_seconds": 5.0
# }
```

**Continuous Monitoring:**

```bash
# Watch metrics update in real-time
watch -n 1 'curl -s http://localhost:8081/metrics | jq'
```

### Docker Testing

**Build and Run:**

```bash
# Build image
cd collector
docker build -t clarion-collector:latest .

# Run container
docker run -d \
  --name clarion-collector-test \
  -p 2055:2055/udp \
  -p 4739:4739/udp \
  -p 8081:8081/tcp \
  -e CLARION_COLLECTOR_BACKEND_URL=http://host.docker.internal:8000 \
  -e CLARION_COLLECTOR_LOG_LEVEL=DEBUG \
  clarion-collector:latest \
  --mode native

# Check logs
docker logs -f clarion-collector-test

# Check health
curl http://localhost:8081/health

# Send test packet (from host)
python tests/test_send_packet.py  # Should send to container
```

**Docker Compose:**

```bash
# Start collector with docker-compose
cd collector
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f collector

# Test health endpoint
curl http://localhost:8081/health

# Stop
docker-compose down
```

### Performance Testing

**Load Testing with Multiple Packets:**

Create a script to send many packets (see `tests/test_send_packet.py` for reference).

**Monitor Performance:**

```bash
# Monitor collector metrics while load testing
watch -n 1 'curl -s http://localhost:8081/metrics | jq ".total_received, .total_sent, .errors"'

# Monitor system resources
top -p $(pgrep -f clarion_collector)
```

**Expected Performance:**

- **Single instance:** ~1M flows/hour (typical)
- **Horizontal scaling:** Can run multiple instances with SO_REUSEPORT
- **Memory usage:** Minimal (batches are small, sent frequently)
- **CPU usage:** Low (primarily I/O bound)

### Testing NetFlow v9 and IPFIX

**NetFlow v9 Testing:**

NetFlow v9 requires template packets before data packets. Testing is more complex:
1. **Send template packet** (defines field structure)
2. **Send data packet** (uses template)

See `tests/test_netflow_v9.py` for example template packet construction.

**IPFIX Testing:**

Similar to NetFlow v9, IPFIX requires template sets before data sets.

For realistic testing, use actual network equipment or tools like:
- `softflowd` with IPFIX export
- `pmacct` (IPFIX exporter)
- Cisco/IOS device with IPFIX enabled

### Troubleshooting Tests

**Common Issues:**

**1. Collector not receiving packets:**
```bash
# Check if collector is listening
netstat -ulnp | grep 2055

# Check firewall
sudo ufw status
sudo iptables -L -n | grep 2055
```

**2. Backend not receiving data:**
```bash
# Check collector logs for errors
tail -f /var/log/clarion-collector.log  # or docker logs

# Test backend connectivity
curl http://localhost:8000/api/health

# Check collector metrics for errors
curl http://localhost:8081/metrics | jq .errors
```

**3. Parsing errors:**
```bash
# Enable DEBUG logging
export CLARION_COLLECTOR_LOG_LEVEL=DEBUG

# Check logs for parsing errors
# Look for "Error parsing NetFlow" messages
```

**4. Template-related errors (v9/IPFIX):**
- Ensure template packets are sent before data packets
- Templates expire after 30 minutes by default
- Check that template IDs match between template and data packets

## Implementation Status

### ✅ Completed Features

- ✅ **NetFlow v5 parser** - Fully implemented
- ✅ **NetFlow v9 template parsing** - Fully implemented with template management
- ✅ **IPFIX template parsing** - Fully implemented with IE mapping
- ✅ **SGT field extraction** - Implemented for IPFIX (IE 411/412) and NetFlow v9 (enterprise fields)
- ✅ **Health check & metrics HTTP endpoints** - Both collectors have HTTP endpoints
- ✅ **Retry logic with exponential backoff** - Backend communication resilience
- ✅ **Socket buffer size configuration** - Configurable UDP receive buffers
- ✅ **SO_REUSEPORT support** - Horizontal scaling capability

### ⚠️ Remaining Features

See [MISSING_FEATURES.md](MISSING_FEATURES.md) for detailed list.

**High Priority:**
- ⚠️ **Data persistence/buffering** - Currently in-memory only (data loss on crash)

**Medium Priority:**
- ⚠️ **Unit tests** - Basic test suite exists, needs expansion for full coverage

**Medium Priority:**
- ❌ **sFlow support** - Not implemented
- ⚠️ **SGT extraction for NetFlow v9** - Heuristic-based (device-specific field IDs needed)

**Low Priority:**
- ⚠️ **Kubernetes manifests** - Docker Compose exists, K8s manifests pending
- ⚠️ **Prometheus metrics export** - Basic metrics exist, Prometheus format pending

## Future Enhancements

**Completed:**
- [x] NetFlow v9 template parsing ✅
- [x] IPFIX template parsing with IE mapping ✅
- [x] SGT field extraction (IPFIX IE 411/412, NetFlow v9 enterprise fields) ✅
- [x] Health check & metrics HTTP endpoint for native collector ✅
- [x] SO_REUSEPORT support for horizontal scaling ✅
- [x] Retry logic with exponential backoff ✅
- [x] Socket buffer size configuration ✅

**Remaining:**
- [ ] Data persistence/buffering (Redis/Kafka) ⚠️ **High Priority**
- [ ] sFlow support ⚠️ **Medium Priority**
- [ ] Kubernetes manifests ⚠️ **Medium Priority**
- [ ] Prometheus metrics export format ⚠️ **Low Priority**
- [ ] Enhanced SGT extraction for NetFlow v9 (device-specific mappings) ⚠️ **Medium Priority**
- [ ] Options template sets (metadata) ⚠️ **Medium Priority**
- [ ] Circuit breaker pattern ⚠️ **Low Priority**
- [ ] Rate limiting and backpressure handling ⚠️ **Low Priority**
- [ ] Flow aggregation and deduplication ⚠️ **Low Priority**

