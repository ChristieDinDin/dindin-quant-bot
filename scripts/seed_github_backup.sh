#!/bin/bash
# Seed GitHub Actions backup with initial database
# This only needs to be run once to initialize the backup system

echo "=================================================="
echo "🌱 Seeding GitHub Actions Backup"
echo "=================================================="
echo ""
echo "This will upload your current database to GitHub Actions"
echo "as the initial backup artifact."
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed."
    echo ""
    echo "Please install it first:"
    echo "  brew install gh"
    echo ""
    echo "Then authenticate:"
    echo "  gh auth login"
    echo ""
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub CLI."
    echo ""
    echo "Please authenticate first:"
    echo "  gh auth login"
    echo ""
    exit 1
fi

# Check if database exists
DB_PATH="data/database/market_data.db"
if [ ! -f "$DB_PATH" ]; then
    echo "❌ Database not found at $DB_PATH"
    echo ""
    echo "Please run an update first:"
    echo "  python scripts/migrate_to_shioaji.py --update"
    echo ""
    exit 1
fi

echo "✅ Database found: $(du -h $DB_PATH | cut -f1)"
echo ""

# Create a temporary directory for the artifact
TEMP_DIR=$(mktemp -d)
cp "$DB_PATH" "$TEMP_DIR/market_data.db"

echo "📦 Creating artifact package..."
cd "$TEMP_DIR"
zip -q market_data.zip market_data.db

echo "⬆️  Uploading to GitHub..."
echo ""
echo "This requires manually triggering a workflow and letting it complete."
echo "The workflow will create the artifact that future runs can use."
echo ""
echo "Please follow these steps:"
echo ""
echo "1. Go to: https://github.com/ChristieDinDin/dindin-quant-bot/actions"
echo "2. Click on 'Daily Stock Data Update (Backup)'"
echo "3. Click 'Run workflow' (right side)"
echo "4. Click the green 'Run workflow' button"
echo "5. Wait ~2 minutes for it to complete"
echo ""
echo "After that completes, your backup system will be fully functional!"
echo ""

# Cleanup
cd -
rm -rf "$TEMP_DIR"

echo "=================================================="
echo "✅ Ready to go!"
echo "=================================================="
