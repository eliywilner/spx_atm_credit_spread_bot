# EC2 Bot Monitoring Guide

## Quick Status Check

Run the status check script:
```bash
./check_bot_status.sh
```

## Manual Status Checks

### 1. Check if Python process is running
```bash
ps aux | grep automate_trading.py | grep -v grep
```

### 2. Check if run_bot.sh is running
```bash
ps aux | grep run_bot.sh | grep -v grep
```

### 3. Check recent log activity
```bash
# View last 20 lines of cron log
tail -20 logs/cron.log

# View last 50 lines with timestamps
tail -50 logs/cron.log | grep "$(date +%Y-%m-%d)"
```

### 4. Check cron schedule
```bash
crontab -l
```

### 5. Check systemd service (if configured)
```bash
# List services
systemctl list-units | grep spx

# Check status
systemctl status spx-bot.service  # (adjust service name as needed)
```

### 6. Check screen/tmux sessions
```bash
# Screen
screen -ls

# Tmux
tmux ls
```

## Viewing Logs in Real-Time

### Watch cron log
```bash
tail -f logs/cron.log
```

### Watch application log (if separate)
```bash
tail -f logs/*.log
```

## Common Issues

### Bot not running
1. Check if cron job is scheduled correctly:
   ```bash
   crontab -l
   ```

2. Check cron execution logs:
   ```bash
   grep CRON /var/log/syslog | tail -20
   # Or on Amazon Linux:
   grep CRON /var/log/cron | tail -20
   ```

3. Manually test the bot:
   ```bash
   ./run_bot.sh
   ```

### Bot crashed
1. Check exit code in cron.log:
   ```bash
   tail -50 logs/cron.log | grep "exit code"
   ```

2. Check for Python errors:
   ```bash
   grep -i error logs/cron.log | tail -20
   ```

3. Check system resources:
   ```bash
   # Memory
   free -h
   
   # Disk space
   df -h
   
   # CPU
   top -bn1 | head -20
   ```

## Restarting the Bot

### If running as a process
```bash
# Find and kill the process
pkill -f automate_trading.py

# Restart
./run_bot.sh
```

### If running in screen
```bash
# Attach to screen
screen -r <session_name>

# Or start new session
screen -S spx_bot ./run_bot.sh
```

### If running in tmux
```bash
# Attach to tmux
tmux attach -t <session_name>

# Or start new session
tmux new -s spx_bot -d './run_bot.sh'
```

## Setting Up Automated Monitoring

### Option 1: Add to cron (check every 5 minutes)
```bash
# Add to crontab: crontab -e
*/5 * * * * /path/to/check_bot_status.sh >> /path/to/bot_status.log 2>&1
```

### Option 2: Use AWS CloudWatch (if configured)
- Set up CloudWatch alarms for process monitoring
- Monitor log files via CloudWatch Logs

### Option 3: Email alerts on failure
Add to `check_bot_status.sh`:
```bash
if [ $? -ne 0 ]; then
    echo "Bot is not running!" | mail -s "Bot Status Alert" your@email.com
fi
```

