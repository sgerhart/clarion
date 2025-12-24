# Clarion Lab Environment

This directory contains scripts and tools for setting up a lab environment to test Clarion with VMs, edge agents, NetFlow collectors, and fake ISE/AD logs.

## Overview

The lab environment simulates a real network with:
- **3 VMs** (VM1, VM2, VM3) each with 24 network namespaces (h1-h24)
- **Edge Agents** running on VMs to process flows and send sketches
- **NetFlow Senders** to send NetFlow data to the backend
- **Fake ISE Logs** matching traffic patterns
- **Fake AD Logs** matching user activity

## Quick Start

### 1. Setup VMs

On each VM, run the base setup:

```bash
sudo ./setup_vm.sh --traffic imix
```

This creates:
- Bridge network (vsw0)
- 24 network namespaces (h1-h24)
- NetFlow collection (softflowd + nfcapd)
- Realistic traffic patterns

### 2. Setup Edge Agents

On VMs that will run edge agents:

```bash
sudo ./vm_agent_setup.sh --backend-url http://BACKEND_IP:8000
```

This:
- Installs Python and dependencies
- Sets up the Clarion edge agent
- Creates a systemd service
- Starts the agent

### 3. Setup NetFlow Senders

On VMs that will send NetFlow:

```bash
sudo ./vm_netflow_sender.sh --backend-url http://BACKEND_IP:8000
```

This:
- Installs nfdump
- Creates a NetFlow sender script
- Reads NetFlow files and sends to backend API
- Creates a systemd service

### 4. Generate Fake Logs

Generate ISE and AD logs that match the traffic:

```bash
# ISE logs
python3 generate_fake_ise.py -o lab/data/ise_sessions.json -d 24

# AD logs
python3 generate_fake_ad.py -o lab/data/ad_logs.json -d 24
```

## VM Configuration

### VM1 (192.168.193.129)
- Subnet: 10.10.0.0/24
- Hosts: h1-h8 (10.10.0.11-18)
- Gateway: 10.10.0.1

### VM2 (192.168.193.130)
- Subnet: 10.10.1.0/24
- Hosts: h9-h16 (10.10.1.11-18)
- Gateway: 10.10.1.1

### VM3 (192.168.193.131)
- Subnet: 10.10.2.0/24
- Hosts: h17-h24 (10.10.2.11-18)
- Gateway: 10.10.2.1

## Host Roles

| Hosts | Role | Description |
|-------|------|-------------|
| h1-h2 | Web/App Servers | HTTP/HTTPS (80, 443, 8080, 8443) |
| h3 | Database Server | MySQL (3306), PostgreSQL (5432) |
| h4 | File Server | SMB (445), NFS (2049) |
| h5 | DNS Server | DNS (53/UDP) |
| h6 | Print Server | IPP (631) |
| h7-h12 | Workstations | Web, files, printing |
| h13-h16 | IoT Cameras | Video streams |
| h17-h18 | Badge Readers | Auth bursts |
| h19-h20 | Sensors | Periodic telemetry |
| h21-h22 | IT Admins | SSH, DB management |
| h23-h24 | Guests | Web only |

## Services

### Edge Agent Service

```bash
# Status
sudo systemctl status clarion-edge

# Logs
sudo journalctl -f -u clarion-edge

# Restart
sudo systemctl restart clarion-edge
```

### NetFlow Sender Service

```bash
# Status
sudo systemctl status clarion-netflow

# Logs
sudo journalctl -f -u clarion-netflow

# Restart
sudo systemctl restart clarion-netflow
```

## Fake Log Generation

### ISE Logs

Generates ISE session logs with:
- Authentication events
- Authorization events
- Device profiles
- AD group memberships
- User assignments

```bash
python3 generate_fake_ise.py \
    -o lab/data/ise_sessions.json \
    -d 24 \
    -e 5
```

Options:
- `-o, --output`: Output file path
- `-d, --duration`: Hours of logs to generate
- `-e, --events-per-hour`: Events per host per hour

### AD Logs

Generates Active Directory logs with:
- User logon/logoff events
- Group membership changes
- Account events
- IP to user mappings

```bash
python3 generate_fake_ad.py \
    -o lab/data/ad_logs.json \
    -d 24 \
    -e 3
```

Options:
- `-o, --output`: Output file path
- `-d, --duration`: Hours of logs to generate
- `-e, --events-per-hour`: Events per user per hour

## Data Flow

```
VM (Traffic Generation)
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

## Verification

### Check Traffic

```bash
# On VM
sudo ./check_status.sh

# View NetFlow
sudo nfdump -R /var/log/netflow -c 10
```

### Check Backend

```bash
# Health check
curl http://BACKEND_IP:8000/api/health

# Sketch stats
curl http://BACKEND_IP:8000/api/edge/sketches/stats

# NetFlow stats
curl http://BACKEND_IP:8000/api/netflow/netflow?limit=10
```

### Check Admin Console

Open in browser:
```
http://BACKEND_IP:8502
```

## Troubleshooting

### Edge Agent Not Sending Data

1. Check service status: `sudo systemctl status clarion-edge`
2. Check logs: `sudo journalctl -f -u clarion-edge`
3. Verify backend URL is reachable: `curl http://BACKEND_IP:8000/api/health`
4. Check network connectivity

### NetFlow Not Being Collected

1. Check softflowd: `ps aux | grep softflowd`
2. Check nfcapd: `ps aux | grep nfcapd`
3. Check NetFlow files: `ls -lh /var/log/netflow/`
4. Restart services: `sudo systemctl restart softflowd nfcapd`

### Backend Not Receiving Data

1. Check API is running: `curl http://BACKEND_IP:8000/api/health`
2. Check database: `ls -lh clarion.db`
3. Check API logs
4. Verify CORS settings if using browser

## Files

- `setup_vm.sh` - Base VM setup (traffic, NetFlow)
- `vm_agent_setup.sh` - Edge agent installation
- `vm_netflow_sender.sh` - NetFlow sender installation
- `generate_fake_ise.py` - ISE log generator
- `generate_fake_ad.py` - AD log generator
- `check_status.sh` - Status checker
- `build_switch_graph.py` - Graph builder (legacy)

## Next Steps

1. **Load Fake Logs into Backend**: Create API endpoints to ingest ISE/AD logs
2. **Identity Resolution**: Map IPs to users/devices from logs
3. **Real-time Processing**: Stream logs instead of batch processing
4. **Multi-site**: Test with multiple backend instances

