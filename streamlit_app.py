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
    # Test core imports one by one so we can pinpoint failures
    st.write("Loading...")

    import pandas as pd
    import numpy as np
    import yfinance as yf
    import yaml
    import plotly.graph_objects as go

    st.write("Core imports OK. Loading app...")

    # Import and run the main app
    from src.presentation.dashboard.app import main
    main()

except ImportError as e:
    st.error(f"Import error: {e}")
    st.code(str(e))
    st.info("Check requirements.txt and ensure all packages are listed.")
except Exception as e:
    import traceback
    st.error(f"Startup error: {e}")
    st.code(traceback.format_exc())
