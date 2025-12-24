#!/bin/bash
#
# VM NetFlow Sender Setup
#
# Sets up a VM to send NetFlow data to the Clarion backend.
# This simulates a NetFlow collector sending data to the API.
#
# Usage:
#   sudo ./vm_netflow_sender.sh [--backend-url http://backend:8000]
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m'

log()  { echo -e "${BLUE}[*]${NC} $1"; }
ok()   { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1" >&2; }

# Parse arguments
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
while [[ $# -gt 0 ]]; do
    case $1 in
        --backend-url)
            BACKEND_URL="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

if [[ $EUID -ne 0 ]]; then
    err "Run as root: sudo $0"
    exit 1
fi

echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║         Clarion NetFlow Sender - VM Setup                 ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Detect VM
UPLINK=$(ip route show default | awk '{print $5; exit}')
MGMT_IP=$(ip -4 addr show "$UPLINK" | awk '/inet / {print $2}' | cut -d/ -f1)

case "$MGMT_IP" in
    192.168.193.129) VM="VM1"; SWITCH_ID="SW-VM1"; ;;
    192.168.193.130) VM="VM2"; SWITCH_ID="SW-VM2"; ;;
    192.168.193.131) VM="VM3"; SWITCH_ID="SW-VM3"; ;;
    *) SWITCH_ID="SW-UNKNOWN"; ;;
esac

ok "VM: $VM | Switch ID: $SWITCH_ID | Backend: $BACKEND_URL"

# 1. Install Python and dependencies
log "Installing Python and dependencies..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip nfdump

# 2. Create virtual environment
log "Setting up Python virtual environment..."
VENV_DIR="/opt/clarion-netflow"
if [ -d "$VENV_DIR" ]; then
    warn "Virtual environment already exists, skipping..."
else
    python3 -m venv "$VENV_DIR"
    ok "Virtual environment created"
fi

# 3. Install dependencies
log "Installing Python packages..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
pip install -q requests pandas

# 4. Create NetFlow sender script
log "Creating NetFlow sender script..."
cat > "$VENV_DIR/netflow_sender.py" <<'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""
NetFlow Sender - Sends NetFlow data to Clarion backend.

Reads NetFlow files from nfdump and sends them to the API.
"""

import json
import sys
import time
import subprocess
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict

BACKEND_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
SWITCH_ID = sys.argv[2] if len(sys.argv) > 2 else "SW-UNKNOWN"
NETFLOW_DIR = sys.argv[3] if len(sys.argv) > 3 else "/var/log/netflow"

def parse_nfdump_output(output: str) -> List[Dict]:
    """Parse nfdump output into records."""
    records = []
    for line in output.strip().split('\n'):
        if not line or line.startswith('Date'):
            continue
        
        parts = line.split()
        if len(parts) < 9:
            continue
        
        try:
            # Parse nfdump format: Date flow start Duration Proto SrcIPAddr:Port DstIPAddr:Port Flags Tos Packets Bytes
            src_ip_port = parts[4].split(':')
            dst_ip_port = parts[5].split(':')
            
            record = {
                "src_ip": src_ip_port[0],
                "dst_ip": dst_ip_port[0],
                "src_port": int(src_ip_port[1]) if len(src_ip_port) > 1 else 0,
                "dst_port": int(dst_ip_port[1]) if len(dst_ip_port) > 1 else 0,
                "protocol": 6 if parts[2] == "TCP" else 17 if parts[2] == "UDP" else 1,
                "bytes": int(parts[8]),
                "packets": int(parts[7]),
                "flow_start": int(datetime.now().timestamp()),  # Approximate
                "flow_end": int(datetime.now().timestamp()),
                "switch_id": SWITCH_ID,
            }
            records.append(record)
        except (ValueError, IndexError):
            continue
    
    return records

def send_netflow(records: List[Dict]) -> bool:
    """Send NetFlow records to backend."""
    if not records:
        return True
    
    url = f"{BACKEND_URL}/api/netflow/netflow"
    payload = {
        "records": records,
        "switch_id": SWITCH_ID,
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error sending NetFlow: {e}", file=sys.stderr)
        return False

def main():
    """Main loop - read NetFlow files and send to backend."""
    print(f"NetFlow Sender started")
    print(f"  Backend: {BACKEND_URL}")
    print(f"  Switch ID: {SWITCH_ID}")
    print(f"  NetFlow Dir: {NETFLOW_DIR}")
    
    while True:
        try:
            # Find latest NetFlow file
            netflow_path = Path(NETFLOW_DIR)
            if not netflow_path.exists():
                time.sleep(60)
                continue
            
            # Get latest file
            nfcapd_files = sorted(netflow_path.glob("nfcapd.*"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not nfcapd_files:
                time.sleep(60)
                continue
            
            latest_file = nfcapd_files[0]
            
            # Read with nfdump
            try:
                result = subprocess.run(
                    ["nfdump", "-R", str(latest_file), "-o", "fmt:%ts %te %pr %sa:%sp %da:%dp %flg %tos %pkt %byt"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                
                if result.returncode == 0:
                    records = parse_nfdump_output(result.stdout)
                    if records:
                        print(f"Sending {len(records)} NetFlow records...")
                        if send_netflow(records):
                            print(f"✅ Sent {len(records)} records")
                        else:
                            print(f"❌ Failed to send records")
                else:
                    print(f"nfdump error: {result.stderr}", file=sys.stderr)
            except subprocess.TimeoutExpired:
                print("nfdump timeout", file=sys.stderr)
            except Exception as e:
                print(f"Error processing NetFlow: {e}", file=sys.stderr)
            
            # Wait before next check
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("\nShutting down...")
            break
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            time.sleep(60)

if __name__ == "__main__":
    main()
PYTHON_SCRIPT

chmod +x "$VENV_DIR/netflow_sender.py"
ok "NetFlow sender script created"

# 5. Create systemd service
log "Creating systemd service..."
cat > /etc/systemd/system/clarion-netflow.service <<EOF
[Unit]
Description=Clarion NetFlow Sender
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$VENV_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/python $VENV_DIR/netflow_sender.py $BACKEND_URL $SWITCH_ID /var/log/netflow
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
ok "Systemd service created"

# 6. Start the NetFlow sender
log "Starting NetFlow sender..."
systemctl enable clarion-netflow
systemctl start clarion-netflow
sleep 2

if systemctl is-active --quiet clarion-netflow; then
    ok "NetFlow sender started successfully"
else
    err "NetFlow sender failed to start"
    systemctl status clarion-netflow
    exit 1
fi

# 7. Summary
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Setup Complete!                        ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  VM:             $VM"
echo "  Switch ID:      $SWITCH_ID"
echo "  Backend URL:    $BACKEND_URL"
echo "  Service:        clarion-netflow"
echo ""
echo "Commands:"
echo "  sudo systemctl status clarion-netflow"
echo "  sudo journalctl -f -u clarion-netflow"
echo "  sudo systemctl restart clarion-netflow"
echo ""

