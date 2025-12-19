# Bot Readiness Checklist for Monday

## ✅ Core Functionality
- [x] Strategy implementation complete (Bullish OR, Bearish ORL Breakout)
- [x] Strike calculation (round_to_5, ATM spreads)
- [x] Credit monitoring and filtering (C_net >= 4.60)
- [x] Position sizing (3% daily risk, min/max contracts)
- [x] Order placement (with dry-run safety gates)
- [x] P/L calculation at expiration
- [x] Trade logging to CSV

## ✅ API Integration
- [x] Schwab API authentication (tokens.json)
- [x] Market data fetching (SPX 30-min candles)
- [x] Option quotes retrieval (SPXW 0DTE)
- [x] Account balance retrieval
- [x] Order placement endpoints

## ✅ Safety Gates
- [x] DRY_RUN mode (default: True)
- [x] ENABLE_LIVE_TRADING flag (default: False)
- [x] Order placement blocked in dry-run mode
- [x] Order payload logging in dry-run

## ⚠️ S3 Integration (REQUIRED)
- [x] S3Service class implemented
- [x] Trade logger S3 integration added
- [x] .env download from S3 implemented
- [x] tokens.json download from S3 implemented
- [ ] **ACTION REQUIRED**: Provide bucket names and configure

### S3 Setup Required:

1. **Provide Bucket Names**:
   - You need to tell the bot which S3 buckets contain `.env` and `tokens.json`
   - Options:
     - **Option A**: Set environment variable on EC2: `export AWS_S3_CONFIG_BUCKET_NAME=your-bucket-name`
     - **Option B**: Update code in `automate_trading.py` around line 485 with your bucket names

2. **S3 Buckets Needed**:
   - **Config Bucket**: Contains `.env` file (and optionally `tokens.json`)
   - **Token Bucket** (optional): Separate bucket for `tokens.json` if different from config bucket
   - **CSV Bucket**: For trade logs (set as `AWS_S3_BUCKET_NAME` in `.env`)

3. **Configure AWS Credentials** (choose one):
   - **Option A (Recommended for EC2)**: Use IAM Role
     - Attach IAM role to EC2 instance with S3 read permissions
     - No credentials needed in code
   - **Option B**: Use Access Keys
     - Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` as system environment variables

4. **Environment Variables** (Set on EC2 before running):
   ```bash
   # For downloading .env and tokens.json (before .env is loaded)
   export AWS_S3_CONFIG_BUCKET_NAME=your-config-bucket-name
   
   # Optional: Separate token bucket
   export AWS_S3_TOKEN_BUCKET_NAME=your-token-bucket-name
   
   # Optional: Custom S3 keys
   export AWS_S3_ENV_KEY=.env              # Default: .env
   export AWS_S3_TOKEN_KEY=tokens.json     # Default: tokens.json
   ```

5. **IAM Role Permissions** (if using IAM role):
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:GetObject",
           "s3:ListBucket"
         ],
         "Resource": [
           "arn:aws:s3:::your-bucket-name/*",
           "arn:aws:s3:::your-bucket-name"
         ]
       }
     ]
   }
   ```

See `S3_CONFIGURATION.md` for detailed setup instructions.

## ⚠️ Environment Variables (REQUIRED)
Create `.env` file with:

### Schwab API (REQUIRED)
```bash
SCHWAB_CLIENT_ID=your-client-id
SCHWAB_CLIENT_SECRET=your-client-secret
SCHWAB_REDIRECT_URI=https://127.0.0.1:8080/callback
```

### Position Sizing (Optional - has defaults)
```bash
DAILY_RISK_PCT=0.03  # 3% (default)
MIN_CONTRACTS=1      # Default
MAX_CONTRACTS=50     # Default
```

### Safety Gates (Optional - defaults are safe)
```bash
DRY_RUN=true              # Default: true (SAFE)
ENABLE_LIVE_TRADING=false # Default: false (SAFE)
```

### S3 Configuration (REQUIRED for production)
```bash
AWS_S3_BUCKET_NAME=your-bucket-name
AWS_REGION=us-east-1
# If using access keys (not IAM role):
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

## ✅ File Structure
- [x] Main script: `automate_trading.py`
- [x] Configuration: `src/config.py`
- [x] Strategy modules: `src/strategy/`
- [x] Order placement: `src/orders/`
- [x] Trade logging: `src/tracking/trade_logger.py`
- [x] S3 service: `src/storage/s3_service.py`
- [x] Requirements: `requirements.txt`

## ✅ Dependencies
- [x] All dependencies in `requirements.txt`:
  - requests
  - python-dotenv
  - pytz
  - boto3
  - matplotlib

## ⚠️ Pre-Launch Testing (RECOMMENDED)
Before Monday, test:

1. **Dry Run Test**:
   ```bash
   python3 automate_trading.py --dry-run
   ```
   - Verify it identifies setups correctly
   - Verify it calculates strikes correctly
   - Verify it monitors quotes correctly
   - Verify NO orders are placed

2. **S3 Connection Test**:
   ```bash
   python3 -c "from src.storage.s3_service import S3Service; s = S3Service(); print('✅ S3 Connected' if s.test_connection() else '❌ S3 Failed')"
   ```

3. **API Connection Test**:
   ```bash
   python3 tests/test_account_info.py
   python3 tests/test_market_data.py
   python3 tests/test_quote_monitoring.py
   ```

4. **Full Integration Test**:
   ```bash
   python3 tests/test_todays_trade_analysis.py
   ```

## ⚠️ EC2 Deployment Checklist

### Before Monday:
1. [ ] **Upload `.env` file to EC2** (or configure S3 download)
2. [ ] **Upload `tokens.json` file to EC2** (or configure S3 download)
3. [ ] **Install dependencies**: `pip3 install -r requirements.txt`
4. [ ] **Test S3 connection** on EC2
5. [ ] **Test API connection** on EC2
6. [ ] **Set up systemd service** (if using)
7. [ ] **Verify timezone** is set to ET/US Eastern
8. [ ] **Set DRY_RUN=true** initially (test first day)

### Systemd Service (Optional):
Create `/etc/systemd/system/spx-atm-bot.service`:
```ini
[Unit]
Description=SPX ATM Credit Spread Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/spx_atm_credit_spread_bot
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 /path/to/spx_atm_credit_spread_bot/automate_trading.py
Restart=on-failure
RestartSec=60

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable spx-atm-bot
sudo systemctl start spx-atm-bot
```

## ⚠️ Critical Pre-Launch Items

### MUST DO Before Monday:
1. [ ] **Set up S3 bucket** and configure credentials
2. [ ] **Test S3 connection** (upload/download)
3. [ ] **Verify `.env` file** has all required variables
4. [ ] **Verify `tokens.json`** is present and valid
5. [ ] **Run dry-run test** to verify bot logic
6. [ ] **Set DRY_RUN=true** for first day (safety)

### Recommended:
1. [ ] **Monitor first day** closely (check logs)
2. [ ] **Verify trade logs** are saved to S3
3. [ ] **Check position sizing** calculations
4. [ ] **Verify credit threshold** filtering works

## 🚨 Safety Reminders

1. **DRY_RUN is ON by default** - Bot will NOT place orders unless:
   - `DRY_RUN=false` AND
   - `ENABLE_LIVE_TRADING=true`

2. **First Day Recommendation**:
   - Keep `DRY_RUN=true` for first day
   - Monitor logs and verify behavior
   - Check that it would have placed correct trades
   - Then enable live trading

3. **Position Sizing**:
   - Default: 3% daily risk
   - Max contracts: 50
   - Min contracts: 1
   - Adjust in `.env` if needed

## 📝 Notes

- Bot runs once per day (not a continuous loop)
- Bot waits for market open (9:30 ET)
- Bot waits for OR close (10:00 ET)
- Bot monitors quotes until 12:00 ET
- Bot waits for market close (16:00 ET) for P/L calculation
- Trade logs saved to `tracking/trades.csv` and uploaded to S3

## ✅ Status Summary

**Ready for Monday?**
- ✅ Core functionality: YES
- ✅ API integration: YES
- ✅ Safety gates: YES
- ⚠️ S3 setup: **ACTION REQUIRED**
- ⚠️ Environment variables: **VERIFY**
- ⚠️ Testing: **RECOMMENDED**

**Next Steps:**
1. Set up S3 bucket and configure credentials
2. Test S3 connection
3. Run dry-run test
4. Deploy to EC2
5. Monitor first day closely

