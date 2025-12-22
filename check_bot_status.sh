#!/bin/bash

# Script to check if the SPX ATM Credit Spread Bot is running on EC2
# Usage: ./check_bot_status.sh

echo "=========================================="
echo "SPX ATM Credit Spread Bot - Status Check"
echo "=========================================="
echo ""

# Method 1: Check for Python process running automate_trading.py
echo "1. Checking for Python process (automate_trading.py)..."
BOT_PROCESS=$(ps aux | grep -E "[p]ython.*automate_trading.py" | grep -v grep)
if [ -n "$BOT_PROCESS" ]; then
    echo "✅ Bot process found:"
    echo ""
    # Parse and display process info
    USER=$(echo "$BOT_PROCESS" | awk '{print $1}')
    PID=$(echo "$BOT_PROCESS" | awk '{print $2}')
    CPU=$(echo "$BOT_PROCESS" | awk '{print $3}')
    MEM=$(echo "$BOT_PROCESS" | awk '{print $4}')
    RSS=$(echo "$BOT_PROCESS" | awk '{print $6}')
    START=$(echo "$BOT_PROCESS" | awk '{print $9}')
    TIME=$(echo "$BOT_PROCESS" | awk '{print $10}')
    
    echo "   User:     $USER"
    echo "   PID:      $PID"
    echo "   CPU:      ${CPU}%"
    echo "   Memory:   ${MEM}% (${RSS} KB)"
    echo "   Started:  $START"
    echo "   Runtime:  $TIME"
    
    # Get elapsed time in a more readable format
    ELAPSED=$(ps -p $PID -o etime= 2>/dev/null | xargs)
    if [ -n "$ELAPSED" ]; then
        echo "   Elapsed:  $ELAPSED"
    fi
    
    echo ""
    echo "   Full command:"
    echo "   $(echo "$BOT_PROCESS" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""}')"
else
    echo "❌ No bot process found"
fi
echo ""

# Method 2: Check for run_bot.sh script
echo "2. Checking for run_bot.sh script process..."
SCRIPT_PROCESS=$(ps aux | grep -E "[r]un_bot.sh" | grep -v grep)
if [ -n "$SCRIPT_PROCESS" ]; then
    echo "✅ run_bot.sh script is running:"
    echo "$SCRIPT_PROCESS"
else
    echo "❌ run_bot.sh script not running"
fi
echo ""

# Method 3: Check systemd service (if configured)
echo "3. Checking systemd service (if configured)..."
if systemctl list-unit-files | grep -q "spx.*bot"; then
    SERVICE_NAME=$(systemctl list-unit-files | grep "spx.*bot" | head -1 | awk '{print $1}')
    echo "   Service found: $SERVICE_NAME"
    systemctl status "$SERVICE_NAME" --no-pager -l | head -10
else
    echo "   No systemd service found"
fi
echo ""

# Method 4: Check screen sessions
echo "4. Checking screen sessions..."
SCREEN_SESSIONS=$(screen -ls 2>/dev/null | grep -E "spx|bot|trading" || echo "")
if [ -n "$SCREEN_SESSIONS" ]; then
    echo "✅ Screen sessions found:"
    echo "$SCREEN_SESSIONS"
else
    echo "❌ No relevant screen sessions found"
fi
echo ""

# Method 5: Check tmux sessions
echo "5. Checking tmux sessions..."
TMUX_SESSIONS=$(tmux ls 2>/dev/null | grep -E "spx|bot|trading" || echo "")
if [ -n "$TMUX_SESSIONS" ]; then
    echo "✅ Tmux sessions found:"
    echo "$TMUX_SESSIONS"
else
    echo "❌ No relevant tmux sessions found"
fi
echo ""

# Method 6: Check recent log activity
echo "6. Checking recent log activity..."
LOG_DIR="logs"
if [ -d "$LOG_DIR" ]; then
    echo "   Recent log files:"
    ls -lht "$LOG_DIR"/*.log 2>/dev/null | head -5 || echo "   No log files found"
    
    if [ -f "$LOG_DIR/cron.log" ]; then
        echo ""
        echo "   Last 5 lines of cron.log:"
        tail -5 "$LOG_DIR/cron.log" | sed 's/^/   /'
    fi
else
    echo "   Log directory not found"
fi
echo ""

# Method 7: Check cron jobs
echo "7. Checking cron jobs..."
CRON_JOBS=$(crontab -l 2>/dev/null | grep -E "run_bot|automate_trading" || echo "")
if [ -n "$CRON_JOBS" ]; then
    echo "✅ Cron jobs found:"
    echo "$CRON_JOBS" | sed 's/^/   /'
else
    echo "❌ No cron jobs found for bot"
fi
echo ""

# Summary
echo "=========================================="
echo "SUMMARY"
echo "=========================================="
if [ -n "$BOT_PROCESS" ] || [ -n "$SCRIPT_PROCESS" ]; then
    echo "✅ Bot appears to be RUNNING"
    exit 0
else
    echo "❌ Bot does NOT appear to be running"
    echo ""
    echo "To start the bot manually:"
    echo "  ./run_bot.sh"
    echo ""
    echo "Or check cron schedule:"
    echo "  crontab -l"
    exit 1
fi

