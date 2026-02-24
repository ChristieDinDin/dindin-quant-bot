#!/usr/bin/env python3
"""
Launcher script for DinDin Quant Bot Dashboard.

This script properly sets up the Python path and launches the Streamlit dashboard.
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Now we can import and run the dashboard
if __name__ == '__main__':
    import subprocess
    
    dashboard_path = project_root / 'src' / 'presentation' / 'dashboard' / 'app.py'
    
    print("🚀 Launching DinDin Quant Bot Dashboard...")
    print(f"📍 Project: {project_root}")
    print(f"🌐 Dashboard will open at: http://localhost:8501")
    print("\n" + "="*50 + "\n")
    
    # Launch streamlit
    subprocess.run([
        'streamlit', 'run', str(dashboard_path),
        '--server.headless', 'false'
    ])
