#!/bin/bash
# Simple shell script to launch the dashboard

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "quant_env" ]; then
    echo "🔧 Activating virtual environment..."
    source quant_env/bin/activate
fi

echo "🚀 Launching DinDin Quant Bot Dashboard..."
echo ""

# Run the dashboard
streamlit run src/presentation/dashboard/app.py
