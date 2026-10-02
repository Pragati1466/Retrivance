#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

# Install the package in editable mode
project_root = Path(__file__).parent
subprocess.run([sys.executable, "-m", "pip", "install", "-e", str(project_root)], check=True)

# Now run the dashboard
import streamlit.cli as stcli
sys.argv = ["streamlit", "run", "ragsentinel/ui/dashboard.py"]
stcli.main()
