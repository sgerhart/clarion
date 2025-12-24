#!/usr/bin/env python3
"""
Complete System Orchestrator

Starts the full Clarion system:
1. Backend API with database
2. Loads synthetic data (optional)
3. React frontend
4. Opens browser

Usage:
    python scripts/run_complete_system.py --mode demo
    python scripts/run_complete_system.py --mode api-only
    python scripts/run_complete_system.py --mode full
"""

import argparse
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
import signal
import os

# Colors for output
GREEN = '\033[0;32m'
BLUE = '\033[0;34m'
YELLOW = '\033[0;33m'
RED = '\033[0;31m'
NC = '\033[0m'  # No Color

def log(msg):
    print(f"{BLUE}[*]{NC} {msg}")

def ok(msg):
    print(f"{GREEN}[✓]{NC} {msg}")

def warn(msg):
    print(f"{YELLOW}[!]{NC} {msg}")

def err(msg):
    print(f"{RED}[✗]{NC} {msg}")

# Track background processes
processes = []

def cleanup():
    """Clean up background processes."""
    log("Shutting down processes...")
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except:
            proc.kill()
    ok("All processes stopped")

def signal_handler(sig, frame):
    """Handle Ctrl+C."""
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def check_dependencies():
    """Check if required dependencies are installed."""
    log("Checking dependencies...")
    
    try:
        import fastapi
        import pandas
        import plotly
        ok("All dependencies installed")
        return True
    except ImportError as e:
        err(f"Missing dependency: {e}")
        err("Run: pip install -r requirements.txt")
        return False

def start_api(port=8000, host="127.0.0.1"):
    """Start the FastAPI backend."""
    log(f"Starting API server on {host}:{port}...")
    
    script_path = Path(__file__).parent / "run_api.py"
    proc = subprocess.Popen(
        [sys.executable, str(script_path), "--port", str(port), "--host", host],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    processes.append(proc)
    
    # Wait for API to start
    import requests
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(f"http://{host}:{port}/api/health", timeout=1)
            if response.status_code == 200:
                ok(f"API server started on http://{host}:{port}")
                return True
        except:
            pass
        time.sleep(1)
    
    err("API server failed to start")
    return False

def load_synthetic_data():
    """Load synthetic data into the system."""
    log("Loading synthetic data...")
    
    script_path = Path(__file__).parent / "test_system.py"
    proc = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
    )
    
    if proc.returncode == 0:
        ok("Synthetic data loaded successfully")
        return True
    else:
        warn("Synthetic data loading had issues (may be expected)")
        return False

def start_frontend(port=3000):
    """Start the React frontend."""
    log(f"Starting React frontend on port {port}...")
    
    frontend_dir = Path(__file__).parent.parent / "frontend"
    if not frontend_dir.exists():
        err("Frontend directory not found. Run: cd frontend && npm install")
        return False
    
    # Check if node_modules exists
    if not (frontend_dir / "node_modules").exists():
        warn("Frontend dependencies not installed. Installing...")
        proc = subprocess.run(
            ["npm", "install"],
            cwd=frontend_dir,
            capture_output=True,
        )
        if proc.returncode != 0:
            err("Failed to install frontend dependencies")
            return False
    
    proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    processes.append(proc)
    
    # Wait for frontend to start
    time.sleep(8)
    
    import requests
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(f"http://localhost:{port}", timeout=1)
            if response.status_code == 200:
                ok(f"Frontend started on http://localhost:{port}")
                return True
        except:
            pass
        time.sleep(1)
    
    warn("Admin console may not be ready yet")
    return False

def open_browser(url):
    """Open browser to URL."""
    log(f"Opening browser to {url}...")
    try:
        webbrowser.open(url)
        ok("Browser opened")
    except Exception as e:
        warn(f"Could not open browser: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Orchestrate the complete Clarion system"
    )
    parser.add_argument(
        "--mode",
        choices=["demo", "api-only", "full"],
        default="demo",
        help="Mode: demo (synthetic data), api-only (just API), full (with lab)",
    )
    parser.add_argument(
        "--api-port",
        type=int,
        default=8000,
        help="API server port (default: 8000)",
    )
    parser.add_argument(
        "--api-host",
        default="127.0.0.1",
        help="API server host (default: 127.0.0.1, use 0.0.0.0 for VMs)",
    )
    parser.add_argument(
        "--frontend-port",
        type=int,
        default=3000,
        help="Frontend port (default: 3000)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open browser automatically",
    )
    parser.add_argument(
        "--skip-data",
        action="store_true",
        help="Skip loading synthetic data",
    )
    
    args = parser.parse_args()
    
    print(f"\n{GREEN}╔═══════════════════════════════════════════════════════════╗{NC}")
    print(f"{GREEN}║         Clarion System Orchestrator                      ║{NC}")
    print(f"{GREEN}╚═══════════════════════════════════════════════════════════╝{NC}\n")
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Start API
    if not start_api(port=args.api_port, host=args.api_host):
        cleanup()
        sys.exit(1)
    
    # Load data (if not skipped)
    if args.mode == "demo" and not args.skip_data:
        load_synthetic_data()
    
    # Start frontend (if not api-only)
    if args.mode != "api-only":
        if not start_frontend(port=args.frontend_port):
            warn("Frontend may not be ready")
        
        # Open browser
        if not args.no_browser:
            time.sleep(2)
            open_browser(f"http://localhost:{args.frontend_port}")
    
    # Summary
    print(f"\n{GREEN}╔═══════════════════════════════════════════════════════════╗{NC}")
    print(f"{GREEN}║                    System Running!                        ║{NC}")
    print(f"{GREEN}╚═══════════════════════════════════════════════════════════╝{NC}\n")
    
    print(f"API Server:     http://{args.api_host}:{args.api_port}")
    print(f"API Docs:       http://{args.api_host}:{args.api_port}/api/docs")
    if args.mode != "api-only":
        print(f"Frontend:       http://localhost:{args.frontend_port}")
    print(f"\nDatabase:       clarion.db")
    print(f"\nPress Ctrl+C to stop all services\n")
    
    # Keep running
    try:
        while True:
            time.sleep(1)
            # Check if processes are still alive
            for proc in processes:
                if proc.poll() is not None:
                    err(f"Process {proc.pid} exited unexpectedly")
                    cleanup()
                    sys.exit(1)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()

if __name__ == "__main__":
    main()

