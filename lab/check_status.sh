#!/bin/bash
#
# check_status.sh - Verify NetFlow lab is working
#
# Usage: sudo ./check_status.sh
#

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; ERRORS=$((ERRORS + 1)); }
warn() { echo -e "  ${YELLOW}!${NC} $1"; }
info() { echo -e "  ${BLUE}→${NC} $1"; }

ERRORS=0
SUBNET=$(ip -4 addr show vsw0 2>/dev/null | awk '/inet / {print $2}' | cut -d. -f1-3)

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "           NetFlow Lab Status Check"
echo "═══════════════════════════════════════════════════════════"
echo ""

#-----------------------------------------------------------------------------
# 1. Bridge
#-----------------------------------------------------------------------------
echo "1. Bridge (vsw0)"
if ip link show vsw0 &>/dev/null; then
    IP=$(ip -4 addr show vsw0 | awk '/inet / {print $2}')
    ok "vsw0 exists with $IP"
else
    fail "vsw0 not found"
fi
echo ""

#-----------------------------------------------------------------------------
# 2. Namespaces
#-----------------------------------------------------------------------------
echo "2. Network Namespaces"
NS_COUNT=$(ip netns list 2>/dev/null | wc -l)
if [[ $NS_COUNT -ge 24 ]]; then
    ok "$NS_COUNT namespaces"
elif [[ $NS_COUNT -gt 0 ]]; then
    warn "$NS_COUNT namespaces (expected 24)"
else
    fail "No namespaces found"
fi
echo ""

#-----------------------------------------------------------------------------
# 3. NetFlow Processes
#-----------------------------------------------------------------------------
echo "3. NetFlow Processes"
if pgrep -x nfcapd >/dev/null; then
    PID=$(pgrep -x nfcapd)
    ok "nfcapd running (PID: $PID)"
else
    fail "nfcapd NOT running"
fi

if pgrep -x softflowd >/dev/null; then
    PID=$(pgrep -x softflowd)
    ok "softflowd running (PID: $PID)"
else
    fail "softflowd NOT running"
fi
echo ""

#-----------------------------------------------------------------------------
# 4. Servers
#-----------------------------------------------------------------------------
echo "4. Server Processes"
HTTP_COUNT=$(ps aux | grep "http.server" | grep -v grep | wc -l)
NC_COUNT=$(ps aux | grep "nc -l" | grep -v grep | wc -l)

if [[ $HTTP_COUNT -gt 0 ]]; then
    ok "$HTTP_COUNT HTTP server(s)"
fi
if [[ $NC_COUNT -gt 0 ]]; then
    ok "$NC_COUNT TCP listener(s) (DB/File/Print)"
fi
if [[ $HTTP_COUNT -eq 0 && $NC_COUNT -eq 0 ]]; then
    fail "No server processes found"
fi

# Test key servers
if [[ -n "$SUBNET" ]]; then
    # Try common ports
    for port in 80 8080; do
        if curl -s --max-time 1 "http://${SUBNET}.11:$port/" >/dev/null 2>&1; then
            ok "Web server responding on port $port"
            break
        fi
    done
fi
echo ""

#-----------------------------------------------------------------------------
# 5. Traffic Generators
#-----------------------------------------------------------------------------
echo "5. Traffic Generators"

# Count by role
TOTAL=0
for role in basic workstation camera badge sensor admin guest; do
    count=$(pgrep -f "traffic_${role}" 2>/dev/null | wc -l)
    if [[ $count -gt 0 ]]; then
        ok "$role: $count processes"
        TOTAL=$((TOTAL + count))
    fi
done

if [[ $TOTAL -eq 0 ]]; then
    # Check for legacy loop pattern
    CURL_COUNT=$(pgrep -f "traffic_loop" 2>/dev/null | wc -l)
    if [[ $CURL_COUNT -gt 0 ]]; then
        ok "Legacy loops: $CURL_COUNT processes"
        TOTAL=$CURL_COUNT
    fi
fi

if [[ $TOTAL -eq 0 ]]; then
    fail "No traffic generators running"
else
    info "Total: $TOTAL traffic processes"
fi
echo ""

#-----------------------------------------------------------------------------
# 6. NetFlow Files
#-----------------------------------------------------------------------------
echo "6. NetFlow Data Files"
if [[ -d /var/log/netflow ]]; then
    FILE_COUNT=$(ls -1 /var/log/netflow/nfcapd.* 2>/dev/null | wc -l)
    if [[ $FILE_COUNT -gt 0 ]]; then
        ok "$FILE_COUNT nfcapd files"
        
        # Check latest file size
        LATEST=$(ls -t /var/log/netflow/nfcapd.2* 2>/dev/null | head -1)
        if [[ -n "$LATEST" ]]; then
            SIZE=$(stat -c%s "$LATEST" 2>/dev/null || stat -f%z "$LATEST" 2>/dev/null)
            if [[ $SIZE -gt 500 ]]; then
                ok "Latest file: $SIZE bytes"
            else
                warn "Latest file small ($SIZE bytes) - wait for flow export"
            fi
        fi
    else
        fail "No nfcapd files found"
    fi
else
    fail "/var/log/netflow not found"
fi
echo ""

#-----------------------------------------------------------------------------
# 7. Flow Analysis
#-----------------------------------------------------------------------------
echo "7. Flow Analysis"
if command -v nfdump &>/dev/null; then
    FLOW_COUNT=$(nfdump -R /var/log/netflow "proto tcp" -q 2>/dev/null | wc -l)
    if [[ $FLOW_COUNT -gt 100 ]]; then
        ok "$FLOW_COUNT TCP flows captured"
    elif [[ $FLOW_COUNT -gt 0 ]]; then
        warn "$FLOW_COUNT TCP flows (wait longer for more)"
    else
        fail "No TCP flows captured"
    fi
    
    # Port distribution
    info "Top destination ports:"
    nfdump -R /var/log/netflow -s dstport/bytes -n 8 -q 2>/dev/null | head -10 | while read line; do
        echo "      $line"
    done
else
    fail "nfdump not installed"
fi
echo ""

#-----------------------------------------------------------------------------
# Summary
#-----------------------------------------------------------------------------
echo "═══════════════════════════════════════════════════════════"
if [[ $ERRORS -eq 0 ]]; then
    echo -e "${GREEN}  ✓ All checks passed - Lab is healthy${NC}"
else
    echo -e "${RED}  ✗ $ERRORS issue(s) found${NC}"
fi
echo "═══════════════════════════════════════════════════════════"
echo ""

exit $ERRORS
