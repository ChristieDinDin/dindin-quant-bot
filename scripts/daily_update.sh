#!/bin/bash
# Daily Stock Data Update Script
# Runs automatically via cron to fetch latest Taiwan stock data

# Configuration
PROJECT_DIR="/Users/dindin/Desktop/DinDin_Quant_Bot"
VENV_PATH="$PROJECT_DIR/quant_env/bin/activate"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/daily_update_$(date +%Y%m%d).log"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Log start
echo "========================================" >> "$LOG_FILE"
echo "Daily Update Started: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Change to project directory
cd "$PROJECT_DIR" || exit 1

# Activate virtual environment
source "$VENV_PATH" || {
    echo "ERROR: Failed to activate virtual environment" >> "$LOG_FILE"
    exit 1
}

# Run the update script
python scripts/migrate_to_shioaji.py --update >> "$LOG_FILE" 2>&1

# Log completion
echo "========================================" >> "$LOG_FILE"
echo "Daily Update Completed: $(date)" >> "$LOG_FILE"
echo "Exit Code: $?" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Keep only last 30 days of logs
find "$LOG_DIR" -name "daily_update_*.log" -mtime +30 -delete
