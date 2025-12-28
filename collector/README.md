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

See [TESTING.md](TESTING.md) for comprehensive testing guide including:
- Unit tests
- Integration testing
- Manual packet testing
- Health/metrics endpoint testing
- Docker testing
- Performance testing

See [COMPLETENESS_CHECK.md](COMPLETENESS_CHECK.md) for a detailed status report of all components, features, and known limitations.

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
├── README.md
├── TESTING.md               # Testing guide
├── SCALABILITY.md           # Scalability guide
├── MISSING_FEATURES.md      # Feature status
└── COMPLETENESS_CHECK.md    # Component status report
```

## Scalability

See [SCALABILITY.md](SCALABILITY.md) for detailed scalability guide.

**Quick Summary:**
- Single instance capacity: ~1M flows/hour (typical)
- Horizontal scaling: Supported via SO_REUSEPORT (Linux)
- Recommended deployment: Containers (Kubernetes/Docker Compose)
- Can scale to 10+ instances for high-volume deployments

**Scale Example:**
```bash
# Docker Compose - scale to 3 instances (OS load balances UDP)
docker-compose up -d --scale collector=3

# Kubernetes - scale deployment
kubectl scale deployment clarion-collector --replicas=3
```

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

