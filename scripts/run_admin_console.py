#!/usr/bin/env python3
"""
Run Clarion Admin Console

Starts the Streamlit-based administrative console.
"""

import sys
import subprocess
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

if __name__ == "__main__":
    # Run streamlit with the admin console
    admin_console = Path(__file__).parent.parent / "src" / "clarion" / "ui" / "admin_console.py"
    
    subprocess.run([
        "streamlit", "run",
        str(admin_console),
        "--server.port", "8502",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ])

