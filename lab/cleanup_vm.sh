#!/bin/bash
#
# cleanup_vm.sh - Clean up NetFlow lab on this VM
#
# Usage: sudo ./cleanup_vm.sh
#

set -e

if [[ $EUID -ne 0 ]]; then
    echo "Run as root: sudo $0"
    exit 1
fi

echo "=== Cleaning up NetFlow Lab ==="

# Stop traffic
echo "[*] Stopping traffic generators..."
pkill -f "curl.*8080" 2>/dev/null || true
pkill -f "http.server" 2>/dev/null || true

# Stop NetFlow
echo "[*] Stopping NetFlow..."
pkill softflowd 2>/dev/null || true
pkill nfcapd 2>/dev/null || true

# Delete namespaces
echo "[*] Deleting namespaces h1-h24..."
for i in $(seq 1 24); do
    ip netns del "h$i" 2>/dev/null || true
done

# Delete veths
echo "[*] Deleting veth interfaces..."
for i in $(seq 1 24); do
    ip link del "vb_h$i" 2>/dev/null || true
done

# Delete bridge
echo "[*] Deleting bridge vsw0..."
ip link set vsw0 down 2>/dev/null || true
ip link del vsw0 2>/dev/null || true

# Delete routes
echo "[*] Removing lab routes..."
ip route del 10.10.0.0/24 2>/dev/null || true
ip route del 10.10.1.0/24 2>/dev/null || true
ip route del 10.10.2.0/24 2>/dev/null || true

# Clear NetFlow data
echo "[*] Clearing NetFlow data..."
rm -f /var/log/netflow/nfcapd.* 2>/dev/null || true

echo ""
echo "=== Cleanup Complete ==="
echo ""



