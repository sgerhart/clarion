#!/bin/bash
#
# VM Agent Setup Script
#
# Sets up the Clarion edge agent on a lab VM to:
# 1. Generate traffic (using existing setup_vm.sh)
# 2. Run the edge agent to process flows
# 3. Send sketches to the backend
#
# Usage:
#   sudo ./vm_agent_setup.sh [--backend-url http://backend:8000]
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
echo "║         Clarion Edge Agent - VM Setup                    ║"
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
apt-get install -y -qq python3 python3-pip python3-venv

# 2. Create virtual environment
log "Setting up Python virtual environment..."
VENV_DIR="/opt/clarion-edge"
if [ -d "$VENV_DIR" ]; then
    warn "Virtual environment already exists, skipping..."
else
    python3 -m venv "$VENV_DIR"
    ok "Virtual environment created"
fi

# 3. Install Clarion edge package
log "Installing Clarion edge agent..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
pip install -q requests  # For HTTP client

# Copy edge agent code (assuming it's in the repo)
if [ -d "/vagrant/edge" ]; then
    log "Copying edge agent code..."
    cp -r /vagrant/edge "$VENV_DIR/"
    ok "Edge agent code copied"
else
    warn "Edge agent code not found in /vagrant/edge"
    warn "You may need to copy it manually"
fi

# 4. Create systemd service
log "Creating systemd service..."
cat > /etc/systemd/system/clarion-edge.service <<EOF
[Unit]
Description=Clarion Edge Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$VENV_DIR
Environment="PATH=$VENV_DIR/bin"
Environment="BACKEND_URL=$BACKEND_URL"
Environment="SWITCH_ID=$SWITCH_ID"
ExecStart=$VENV_DIR/bin/python -m clarion_edge.main --mode simulator --backend-url $BACKEND_URL --switch-id $SWITCH_ID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
ok "Systemd service created"

# 5. Setup traffic generation (if not already done)
if [ ! -f "/var/log/netflow/nfcapd.current" ]; then
    log "Setting up traffic generation..."
    if [ -f "/vagrant/lab/setup_vm.sh" ]; then
        /vagrant/lab/setup_vm.sh --traffic imix
    else
        warn "setup_vm.sh not found, skipping traffic setup"
    fi
fi

# 6. Start the edge agent
log "Starting edge agent..."
systemctl enable clarion-edge
systemctl start clarion-edge
sleep 2

if systemctl is-active --quiet clarion-edge; then
    ok "Edge agent started successfully"
else
    err "Edge agent failed to start"
    systemctl status clarion-edge
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
echo "  Service:        clarion-edge"
echo ""
echo "Commands:"
echo "  sudo systemctl status clarion-edge"
echo "  sudo systemctl logs -f clarion-edge"
echo "  sudo systemctl restart clarion-edge"
echo ""

