#!/bin/bash
#
# Demo Workflow Script
#
# Quick script to demonstrate the complete Clarion system.
# This loads synthetic data and shows the admin console.
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         Clarion Complete System Demo                    ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "scripts/run_api.py" ]; then
    echo "Error: Run this script from the project root"
    exit 1
fi

# Step 1: Start API
echo -e "${BLUE}[*]${NC} Starting API server..."
python scripts/run_api.py --port 8000 &
API_PID=$!
sleep 5

# Check if API started
if ! curl -s http://localhost:8000/api/health > /dev/null; then
    echo "Error: API failed to start"
    kill $API_PID 2>/dev/null || true
    exit 1
fi
echo -e "${GREEN}[✓]${NC} API server running on http://localhost:8000"

# Step 2: Load synthetic data
echo -e "${BLUE}[*]${NC} Loading synthetic data..."
python scripts/test_system.py
echo -e "${GREEN}[✓]${NC} Synthetic data loaded"

# Step 3: Start admin console
echo -e "${BLUE}[*]${NC} Starting admin console..."
echo -e "${YELLOW}[!]${NC} Admin console will open in your browser"
echo -e "${YELLOW}[!]${NC} Press Ctrl+C to stop all services"
echo ""

python scripts/run_admin_console.py

# Cleanup
echo ""
echo -e "${BLUE}[*]${NC} Shutting down..."
kill $API_PID 2>/dev/null || true
echo -e "${GREEN}[✓]${NC} Done"

