# Testing the Native Collector

This guide covers how to test the Clarion native NetFlow collector at various levels.

## Table of Contents

1. [Unit Tests](#unit-tests)
2. [Running the Collector](#running-the-collector)
3. [Manual Testing with Test Packets](#manual-testing-with-test-packets)
4. [Integration Testing](#integration-testing)
5. [Health and Metrics Testing](#health-and-metrics-testing)
6. [Docker Testing](#docker-testing)
7. [Performance Testing](#performance-testing)

---

## Unit Tests

### Running Unit Tests

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

### Test Coverage

Current test coverage includes:
- ✅ NetFlow v5 parser (header parsing, record parsing, error handling)
- ✅ NetFlow v9 template parsing (template storage, validation)

**Missing test coverage:**
- ⚠️ NetFlow v9 data record parsing (with templates)
- ⚠️ IPFIX parser tests
- ⚠️ End-to-end collector integration tests
- ⚠️ Retry logic tests
- ⚠️ Metrics/health endpoint tests

---

## Running the Collector

### Basic Setup

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

### Environment Variables

Alternatively, use environment variables:

```bash
export CLARION_COLLECTOR_BACKEND_URL=http://localhost:8000
export CLARION_COLLECTOR_NETFLOW_PORT=2055
export CLARION_COLLECTOR_IPFIX_PORT=4739
export CLARION_COLLECTOR_LOG_LEVEL=DEBUG

python -m clarion_collector.main --mode native
```

---

## Manual Testing with Test Packets

### Method 1: Using Python socket (Quick Test)

Create a simple test script to send NetFlow v5 packets:

```python
# test_send_netflow.py
import socket
import struct
import ipaddress
import time

# Create a minimal NetFlow v5 packet
def create_netflow_v5_packet():
    # Header (24 bytes)
    header = struct.pack("!HHIIIIII",
        5,              # version
        1,              # count (1 record)
        int(time.time() * 1000) % (2**32),  # sys_uptime (ms)
        int(time.time()),  # unix_secs
        int((time.time() % 1) * 1000000000),  # unix_nsecs
        1,              # flow_sequence
        0,              # engine_type
        0,              # engine_id
    )
    
    # Record (48 bytes)
    src_ip = int(ipaddress.IPv4Address("10.0.0.1"))
    dst_ip = int(ipaddress.IPv4Address("10.0.0.2"))
    
    record = struct.pack("!IIIIIIIIIIHHBBBBHHBBH",
        src_ip,         # src_addr
        dst_ip,         # dst_addr
        0,              # nexthop
        0,              # input
        0,              # output
        10,             # dPkts
        1500,           # dOctets
        1000,           # first
        2000,           # last
        12345,          # srcport
        80,             # dstport
        0,              # pad1
        0,              # tcp_flags
        6,              # prot (TCP)
        0,              # tos
        0,              # src_as
        0,              # dst_as
        24,             # src_mask
        24,             # dst_mask
        0,              # pad2
    )
    
    return header + record

# Send packet to collector
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
packet = create_netflow_v5_packet()
sock.sendto(packet, ('localhost', 2055))
print("Sent NetFlow v5 packet to collector")
sock.close()
```

Run it:
```bash
python test_send_netflow.py
```

### Method 2: Using nfdump/nfsend (Realistic Test)

If you have `nfdump` installed, you can use `nfsend` to send NetFlow packets:

```bash
# Send a single NetFlow v5 packet
echo "10.0.0.1,10.0.0.2,12345,80,6,10,1500" | \
  nfsend -S localhost:2055 -v 5
```

### Method 3: Using softflowd (Flow Generator)

Use `softflowd` to generate NetFlow from actual traffic:

```bash
# Install softflowd (Ubuntu/Debian)
sudo apt-get install softflowd

# Generate NetFlow from interface traffic
sudo softflowd -i eth0 -n 127.0.0.1:2055 -v 5

# Or read from a pcap file
sudo softflowd -r capture.pcap -n 127.0.0.1:2055 -v 5
```

### Method 4: Using Python scapy (Advanced)

For more complex testing, use `scapy` to craft custom packets:

```python
# test_scapy_netflow.py
from scapy.all import *
import socket

# Note: Scapy doesn't have built-in NetFlow support,
# so you'd need to construct raw packets similar to Method 1
```

---

## Integration Testing

### Full Integration Test

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

### Expected Behavior

When working correctly:
- Collector logs should show: "Parsed N NetFlow v5 records from 127.0.0.1"
- Collector logs should show: "Sent N NetFlow records from 127.0.0.1"
- Backend API should return NetFlow records with your test data
- Collector metrics should show `total_received` > 0

---

## Health and Metrics Testing

### Health Check

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

### Metrics Endpoint

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

### Continuous Monitoring

```bash
# Watch metrics update in real-time
watch -n 1 'curl -s http://localhost:8081/metrics | jq'
```

---

## Docker Testing

### Build and Run

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
python test_send_netflow.py  # Should send to container
```

### Docker Compose

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

---

## Performance Testing

### Load Testing with Multiple Packets

Create a script to send many packets:

```python
# test_load.py
import socket
import struct
import ipaddress
import time
import random

def create_netflow_v5_packet(flow_num):
    """Create a NetFlow v5 packet with flow_num records."""
    records = []
    
    for i in range(flow_num):
        src_ip = random.randint(1, 255)
        dst_ip = random.randint(1, 255)
        
        # ... construct record (similar to Method 1) ...
        record = b""  # Simplified - use full record structure
        records.append(record)
    
    # Construct packet with header and records
    # ...
    return packet

# Send 1000 packets with 10 flows each
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
for i in range(1000):
    packet = create_netflow_v5_packet(10)
    sock.sendto(packet, ('localhost', 2055))
    if i % 100 == 0:
        print(f"Sent {i} packets")
sock.close()
```

### Monitor Performance

```bash
# Monitor collector metrics while load testing
watch -n 1 'curl -s http://localhost:8081/metrics | jq ".total_received, .total_sent, .errors"'

# Monitor system resources
top -p $(pgrep -f clarion_collector)
```

### Expected Performance

- **Single instance:** ~1M flows/hour (typical)
- **Horizontal scaling:** Can run multiple instances with SO_REUSEPORT
- **Memory usage:** Minimal (batches are small, sent frequently)
- **CPU usage:** Low (primarily I/O bound)

---

## Testing NetFlow v9 and IPFIX

### NetFlow v9 Testing

NetFlow v9 requires template packets before data packets. Testing is more complex:

1. **Send template packet** (defines field structure)
2. **Send data packet** (uses template)

See `tests/test_netflow_v9.py` for example template packet construction.

### IPFIX Testing

Similar to NetFlow v9, IPFIX requires template sets before data sets.

For realistic testing, use actual network equipment or tools like:
- `softflowd` with IPFIX export
- `pmacct` (IPFIX exporter)
- Cisco/IOS device with IPFIX enabled

---

## Troubleshooting Tests

### Common Issues

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

---

## Automated Test Script

Create an end-to-end test script:

```bash
#!/bin/bash
# test_collector_e2e.sh

set -e

echo "Testing Clarion Native Collector"
echo "================================"

# Start backend (if not running)
# ...

# Start collector
echo "Starting collector..."
python -m clarion_collector.main --mode native &
COLLECTOR_PID=$!
sleep 2

# Check health
echo "Checking health..."
curl -f http://localhost:8081/health || exit 1

# Send test packet
echo "Sending test packet..."
python test_send_netflow.py

# Wait for batch processing
sleep 6

# Check metrics
echo "Checking metrics..."
METRICS=$(curl -s http://localhost:8081/metrics)
RECEIVED=$(echo $METRICS | jq .total_received)
if [ "$RECEIVED" -lt "1" ]; then
    echo "ERROR: No packets received"
    exit 1
fi

# Check backend received data
echo "Checking backend..."
curl -f http://localhost:8000/api/netflow/netflow?limit=1 || exit 1

echo "All tests passed!"

# Cleanup
kill $COLLECTOR_PID
```

Run it:
```bash
chmod +x test_collector_e2e.sh
./test_collector_e2e.sh
```

---

## Next Steps

- Add more unit tests for IPFIX parser
- Create integration tests for full pipeline
- Add performance benchmarks
- Create test fixtures with real NetFlow samples
- Add CI/CD pipeline with automated tests

