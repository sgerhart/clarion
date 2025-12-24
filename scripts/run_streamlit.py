#!/usr/bin/env python3
"""
Run the Clarion Streamlit UI.

Usage:
    python scripts/run_streamlit.py
    streamlit run src/clarion/ui/streamlit_app.py
"""

import subprocess
import sys
from pathlib import Path

def main():
    script_path = Path(__file__).parent.parent / "src" / "clarion" / "ui" / "streamlit_app.py"
    
    subprocess.run([
        sys.executable,
        "-m", "streamlit", "run",
        str(script_path),
    ] + sys.argv[1:])

if __name__ == "__main__":
    main()

