"""
Root entry point for Streamlit Cloud deployment.
Streamlit Cloud looks for this file at the repo root by default.
"""
import sys
import os
from pathlib import Path

# Add project root to path
root = Path(__file__).resolve().parent
sys.path.insert(0, str(root))

# Show diagnostic info if anything fails
import streamlit as st

try:
    from src.presentation.dashboard.app import main
    main()
except Exception as e:
    import traceback
    st.error(f"Startup error: {e}")
    st.code(traceback.format_exc())
