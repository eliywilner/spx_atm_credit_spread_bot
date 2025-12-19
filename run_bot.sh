#!/bin/bash

# SPX ATM Credit Spread Bot - Daily Runner Script
# This script is called by cron to run the bot every trading day

# Set script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] $1" | tee -a logs/cron.log
}

# Create logs directory if it doesn't exist
mkdir -p logs

log "=========================================="
log "SPX ATM Credit Spread Bot - Starting"
log "=========================================="

# Step 1: Set environment variables (required for S3 downloads)
export AWS_S3_CONFIG_BUCKET_NAME=spx-atm-credit-spread-bot-config
export AWS_S3_TOKEN_BUCKET_NAME=my-tokens

log "Environment variables set:"
log "  AWS_S3_CONFIG_BUCKET_NAME=$AWS_S3_CONFIG_BUCKET_NAME"
log "  AWS_S3_TOKEN_BUCKET_NAME=$AWS_S3_TOKEN_BUCKET_NAME"

# Step 2: Pull latest code from Git
log ""
log "Step 1: Pulling latest code from Git..."
git pull >> logs/cron.log 2>&1
if [ $? -eq 0 ]; then
    log "✅ Git pull successful"
else
    log "⚠️  Git pull had issues (continuing anyway)"
fi

# Step 3: Activate virtual environment
log ""
log "Step 2: Activating virtual environment..."
if [ -d "venv" ]; then
    source venv/bin/activate
    log "✅ Virtual environment activated"
else
    log "❌ Virtual environment not found at venv/"
    log "Please create it with: python3 -m venv venv"
    exit 1
fi

# Step 4: Install/update dependencies (optional - uncomment if needed)
# log ""
# log "Step 3: Checking dependencies..."
# pip install -q -r requirements.txt >> logs/cron.log 2>&1
# log "✅ Dependencies checked"

# Step 5: Run the bot
# The bot will automatically:
# - Download .env from S3 (spx-atm-credit-spread-bot-config bucket)
# - Download tokens.json from S3 (my-tokens bucket)
# - Download trades.csv from S3 if it exists (spx-atm-credit-spread-bot-data bucket)
# - Wait for market open (9:30 ET)
# - Run the strategy
# - Upload trades.csv to S3 at end of day
log ""
log "Step 3: Starting bot..."
log "=========================================="

# Run the bot (remove --dry-run when ready for live trading)
python3 automate_trading.py --dry-run >> logs/cron.log 2>&1

BOT_EXIT_CODE=$?

log ""
log "=========================================="
if [ $BOT_EXIT_CODE -eq 0 ]; then
    log "✅ Bot completed successfully"
else
    log "❌ Bot exited with error code: $BOT_EXIT_CODE"
    log "Check logs/cron.log for details"
fi
log "=========================================="

exit $BOT_EXIT_CODE
