#!/bin/bash
#
# setup_vm.sh - Complete VM setup for NetFlow lab
#
# Usage:
#   sudo ./setup_vm.sh              # Infrastructure + IMIX traffic (default)
#   sudo ./setup_vm.sh --traffic basic   # Infrastructure + basic HTTP traffic
#   sudo ./setup_vm.sh --traffic imix    # Infrastructure + IMIX traffic
#   sudo ./setup_vm.sh --traffic none    # Infrastructure only, no traffic
#
# Host Role Assignments (for IMIX mode):
#   h1-h2:   Web/App Servers
#   h3:      Database Server
#   h4:      File Server  
#   h5:      DNS Server
#   h6:      Print Server
#   h7-h12:  Corporate Workstations
#   h13-h16: IoT Cameras
#   h17-h18: Badge Readers
#   h19-h20: Environmental Sensors
#   h21-h22: IT Admin Workstations
#   h23-h24: Guest Devices
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
TRAFFIC_MODE="imix"  # default
while [[ $# -gt 0 ]]; do
    case $1 in
        --traffic)
            TRAFFIC_MODE="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

if [[ ! "$TRAFFIC_MODE" =~ ^(none|basic|imix)$ ]]; then
    err "Invalid traffic mode: $TRAFFIC_MODE (use: none, basic, imix)"
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
    err "Run as root: sudo $0"
    exit 1
fi

echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║         NetFlow Lab - VM Setup                            ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

#=============================================================================
# 1. Detect VM and configure subnet
#=============================================================================
log "Detecting VM configuration..."

UPLINK=$(ip route show default | awk '{print $5; exit}')
MGMT_IP=$(ip -4 addr show "$UPLINK" | awk '/inet / {print $2}' | cut -d/ -f1)

case "$MGMT_IP" in
    192.168.193.129) VM="VM1"; SUBNET="10.10.0"; ;;
    192.168.193.130) VM="VM2"; SUBNET="10.10.1"; ;;
    192.168.193.131) VM="VM3"; SUBNET="10.10.2"; ;;
    *) err "Unknown IP: $MGMT_IP"; exit 1; ;;
esac

GATEWAY="${SUBNET}.1"
ok "VM: $VM | Subnet: ${SUBNET}.0/24 | Traffic: $TRAFFIC_MODE"

#=============================================================================
# 2. Install packages
#=============================================================================
log "Checking packages..."
for pkg in softflowd nfdump bridge-utils curl netcat-openbsd; do
    if ! dpkg -l "$pkg" &>/dev/null; then
        log "Installing $pkg..."
        apt-get update -qq && apt-get install -y -qq "$pkg"
    fi
done
ok "Packages ready"

#=============================================================================
# 3. Create bridge
#=============================================================================
log "Creating bridge vsw0..."

ip link del vsw0 2>/dev/null || true
ip link add vsw0 type bridge
ip addr add "${GATEWAY}/24" dev vsw0
ip link set vsw0 up
sysctl -w net.ipv4.ip_forward=1 >/dev/null

ok "Bridge vsw0 created with $GATEWAY/24"

#=============================================================================
# 4. Add routes to other subnets
#=============================================================================
log "Adding routes..."

case "$VM" in
    VM1)
        ip route replace 10.10.1.0/24 via 192.168.193.130 dev "$UPLINK"
        ip route replace 10.10.2.0/24 via 192.168.193.131 dev "$UPLINK"
        ;;
    VM2)
        ip route replace 10.10.0.0/24 via 192.168.193.129 dev "$UPLINK"
        ip route replace 10.10.2.0/24 via 192.168.193.131 dev "$UPLINK"
        ;;
    VM3)
        ip route replace 10.10.0.0/24 via 192.168.193.129 dev "$UPLINK"
        ip route replace 10.10.1.0/24 via 192.168.193.130 dev "$UPLINK"
        ;;
esac

ok "Routes configured"

#=============================================================================
# 5. Create namespaces h1-h24
#=============================================================================
log "Creating 24 namespaces..."

for i in $(seq 1 24); do
    ns="h$i"
    veth_br="vb_$ns"
    veth_ns="v_$ns"
    host_ip="${SUBNET}.$((10 + i))"
    
    ip netns del "$ns" 2>/dev/null || true
    ip link del "$veth_br" 2>/dev/null || true
    
    ip netns add "$ns"
    ip link add "$veth_br" type veth peer name "$veth_ns"
    ip link set "$veth_br" master vsw0
    ip link set "$veth_br" up
    ip link set "$veth_ns" netns "$ns"
    ip netns exec "$ns" ip link set lo up
    ip netns exec "$ns" ip link set "$veth_ns" up
    ip netns exec "$ns" ip addr add "${host_ip}/24" dev "$veth_ns"
    ip netns exec "$ns" ip route add default via "$GATEWAY"
done

ok "Created h1-h24 (${SUBNET}.11 - ${SUBNET}.34)"

#=============================================================================
# 6. Start NetFlow
#=============================================================================
log "Starting NetFlow collection..."

mkdir -p /var/log/netflow
pkill -9 nfcapd 2>/dev/null || true
pkill -9 softflowd 2>/dev/null || true
sleep 2

nfcapd -D -l /var/log/netflow -p 9995 -t 60
sleep 1
nohup softflowd -i vsw0 -v 9 -n 127.0.0.1:9995 -t maxlife=30 >/dev/null 2>&1 &
disown

sleep 2
if pgrep nfcapd >/dev/null && pgrep softflowd >/dev/null; then
    ok "NetFlow running (nfcapd + softflowd)"
else
    err "NetFlow failed to start"
fi

#=============================================================================
# 7. Start Traffic (based on mode)
#=============================================================================

# Kill any existing traffic first
pkill -f "traffic_" 2>/dev/null || true
pkill -f "http.server" 2>/dev/null || true
pkill -f "nc -l" 2>/dev/null || true
sleep 1

if [[ "$TRAFFIC_MODE" == "none" ]]; then
    warn "Traffic mode: none - no traffic will be generated"

elif [[ "$TRAFFIC_MODE" == "basic" ]]; then
    #-------------------------------------------------------------------------
    # Basic mode: HTTP servers on h1-h2, clients on h7-h12
    #-------------------------------------------------------------------------
    log "Starting basic traffic (HTTP only)..."
    
    # HTTP servers
    for i in 1 2; do
        ip="${SUBNET}.$((10 + i))"
        ip netns exec "h$i" python3 -m http.server 8080 --bind "$ip" &>/dev/null &
    done
    sleep 1
    
    # Traffic loops
    for i in 7 8 9 10 11 12; do
        ip netns exec "h$i" nohup bash -c "
            exec -a traffic_basic_h$i bash -c '
                while true; do
                    curl -s --max-time 2 http://${SUBNET}.11:8080/ >/dev/null 2>&1 || true
                    curl -s --max-time 2 http://${SUBNET}.12:8080/ >/dev/null 2>&1 || true
                    sleep \$((RANDOM % 3 + 1))
                done
            '
        " >/dev/null 2>&1 &
        disown
    done
    
    ok "Basic traffic: 2 HTTP servers, 6 clients"

elif [[ "$TRAFFIC_MODE" == "imix" ]]; then
    #-------------------------------------------------------------------------
    # IMIX mode: Realistic enterprise traffic patterns
    #-------------------------------------------------------------------------
    log "Starting IMIX traffic (realistic enterprise patterns)..."
    
    # --- Servers ---
    # h1: Web Server (HTTP 80, HTTPS 443)
    ip netns exec h1 python3 -m http.server 80 --bind ${SUBNET}.11 &>/dev/null &
    ip netns exec h1 python3 -m http.server 443 --bind ${SUBNET}.11 &>/dev/null &
    
    # h2: App Server (HTTP 8080, 8443)
    ip netns exec h2 python3 -m http.server 8080 --bind ${SUBNET}.12 &>/dev/null &
    ip netns exec h2 python3 -m http.server 8443 --bind ${SUBNET}.12 &>/dev/null &
    
    # h3: Database Server (MySQL 3306, Postgres 5432)
    ip netns exec h3 nc -l -k ${SUBNET}.13 3306 &>/dev/null &
    ip netns exec h3 nc -l -k ${SUBNET}.13 5432 &>/dev/null &
    
    # h4: File Server (SMB 445, NFS 2049)
    ip netns exec h4 nc -l -k ${SUBNET}.14 445 &>/dev/null &
    ip netns exec h4 nc -l -k ${SUBNET}.14 2049 &>/dev/null &
    
    # h5: DNS Server (simulated)
    ip netns exec h5 nc -l -u -k ${SUBNET}.15 53 &>/dev/null &
    
    # h6: Print Server (IPP 631)
    ip netns exec h6 nc -l -k ${SUBNET}.16 631 &>/dev/null &
    
    sleep 1
    ok "Servers started (h1-h6)"
    
    # --- Workstations (h7-h12): Web, DNS, files, printing ---
    log "Starting workstation traffic (h7-h12)..."
    for i in 7 8 9 10 11 12; do
        ip netns exec "h$i" nohup bash -c "
            exec -a traffic_workstation_h$i bash -c '
                while true; do
                    curl -s --max-time 2 http://${SUBNET}.11:80/ >/dev/null 2>&1
                    curl -s --max-time 2 http://${SUBNET}.12:8080/ >/dev/null 2>&1
                    nc -z -w1 ${SUBNET}.11 443 2>/dev/null
                    nc -z -u -w1 ${SUBNET}.15 53 2>/dev/null
                    if (( RANDOM % 5 == 0 )); then nc -z -w1 ${SUBNET}.14 445 2>/dev/null; fi
                    if (( RANDOM % 20 == 0 )); then nc -z -w1 ${SUBNET}.16 631 2>/dev/null; fi
                    sleep \$((RANDOM % 3 + 1))
                done
            '
        " >/dev/null 2>&1 &
        disown
    done
    ok "Workstations active (h7-h12)"
    
    # --- IoT Cameras (h13-h16): Video streams ---
    log "Starting IoT camera traffic (h13-h16)..."
    for i in 13 14 15 16; do
        ip netns exec "h$i" nohup bash -c "
            exec -a traffic_camera_h$i bash -c '
                while true; do
                    for j in {1..10}; do nc -z -w1 ${SUBNET}.12 8080 2>/dev/null; sleep 0.5; done
                    if (( RANDOM % 10 == 0 )); then nc -z -w1 ${SUBNET}.11 443 2>/dev/null; fi
                    sleep 2
                done
            '
        " >/dev/null 2>&1 &
        disown
    done
    ok "IoT cameras active (h13-h16)"
    
    # --- Badge Readers (h17-h18): Auth bursts ---
    log "Starting badge reader traffic (h17-h18)..."
    for i in 17 18; do
        ip netns exec "h$i" nohup bash -c "
            exec -a traffic_badge_h$i bash -c '
                while true; do
                    nc -z -w1 ${SUBNET}.12 8443 2>/dev/null
                    if (( RANDOM % 5 == 0 )); then nc -z -w1 ${SUBNET}.13 3306 2>/dev/null; fi
                    sleep \$((RANDOM % 10 + 5))
                done
            '
        " >/dev/null 2>&1 &
        disown
    done
    ok "Badge readers active (h17-h18)"
    
    # --- Sensors (h19-h20): Periodic telemetry ---
    log "Starting sensor traffic (h19-h20)..."
    for i in 19 20; do
        ip netns exec "h$i" nohup bash -c "
            exec -a traffic_sensor_h$i bash -c '
                while true; do
                    nc -z -w1 ${SUBNET}.12 8080 2>/dev/null
                    sleep 30
                done
            '
        " >/dev/null 2>&1 &
        disown
    done
    ok "Sensors active (h19-h20)"
    
    # --- IT Admins (h21-h22): SSH, DB, management ---
    log "Starting admin traffic (h21-h22)..."
    for i in 21 22; do
        ip netns exec "h$i" nohup bash -c "
            exec -a traffic_admin_h$i bash -c '
                while true; do
                    nc -z -w1 ${SUBNET}.11 22 2>/dev/null
                    nc -z -w1 ${SUBNET}.12 22 2>/dev/null
                    nc -z -w1 ${SUBNET}.13 22 2>/dev/null
                    curl -s --max-time 2 http://${SUBNET}.11:80/ >/dev/null 2>&1
                    nc -z -w1 ${SUBNET}.13 3306 2>/dev/null
                    nc -z -w1 ${SUBNET}.13 5432 2>/dev/null
                    nc -z -w1 ${SUBNET}.14 445 2>/dev/null
                    sleep \$((RANDOM % 5 + 2))
                done
            '
        " >/dev/null 2>&1 &
        disown
    done
    ok "IT admins active (h21-h22)"
    
    # --- Guests (h23-h24): Web/DNS only ---
    log "Starting guest traffic (h23-h24)..."
    for i in 23 24; do
        ip netns exec "h$i" nohup bash -c "
            exec -a traffic_guest_h$i bash -c '
                while true; do
                    curl -s --max-time 2 http://${SUBNET}.11:80/ >/dev/null 2>&1
                    nc -z -w1 ${SUBNET}.11 443 2>/dev/null
                    nc -z -u -w1 ${SUBNET}.15 53 2>/dev/null
                    sleep \$((RANDOM % 5 + 2))
                done
            '
        " >/dev/null 2>&1 &
        disown
    done
    ok "Guests active (h23-h24)"
fi

#=============================================================================
# 8. Summary
#=============================================================================
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Setup Complete!                        ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  VM:             $VM"
echo "  Subnet:         ${SUBNET}.0/24"
echo "  Gateway:        $GATEWAY"
echo "  Namespaces:     h1-h24"
echo "  Traffic Mode:   $TRAFFIC_MODE"
echo "  NetFlow:        /var/log/netflow"
echo ""

if [[ "$TRAFFIC_MODE" == "imix" ]]; then
    echo "  Device Roles:"
    echo "    h1-h2:   Web/App Servers     (HTTP/HTTPS)"
    echo "    h3:      Database Server     (MySQL/PostgreSQL)"
    echo "    h4:      File Server         (SMB/NFS)"
    echo "    h5:      DNS Server"
    echo "    h6:      Print Server"
    echo "    h7-h12:  Workstations        (web, files, print)"
    echo "    h13-h16: IoT Cameras         (video streams)"
    echo "    h17-h18: Badge Readers       (auth bursts)"
    echo "    h19-h20: Sensors             (periodic telemetry)"
    echo "    h21-h22: IT Admins           (SSH, DB mgmt)"
    echo "    h23-h24: Guests              (web only)"
    echo ""
    echo "  Ports in use:"
    echo "    TCP: 22, 80, 443, 445, 631, 2049, 3306, 5432, 8080, 8443"
    echo "    UDP: 53"
    echo ""
fi

echo "Verify:"
echo "  sudo ./check_status.sh"
echo ""
echo "Build graph (wait 2-5 min for flows):"
echo "  sudo ./build_switch_graph.py --switch-id $VM --site-id LabSite -o ${VM,,}_graph.json"
echo ""
