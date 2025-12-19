# SPX ATM Credit Spread Bot - 0DTE Strategy

Automated trading bot for SPX 0DTE ATM credit spreads with a 10-point width.

## Strategy Overview

This bot implements a systematic approach to trading SPX 0DTE credit spreads:

- **Instrument**: SPX index (underlying), SPXW options (0DTE)
- **Spread Width**: Always 10 points
- **Strike Selection**: Always ATM (at-the-money)
- **Entry Windows**:
  - **Bullish OR**: At 10:00 ET, if ORC > ORO, place PUT spread
  - **Bearish ORL Breakout**: Scan 10:00-12:00 ET for bar_close < ORL, place CALL spread
- **Credit Filter**: Minimum NET credit of 4.60 (GROSS credit >= 4.70)
- **Position Sizing**: 5% daily risk
- **Exit**: Hold to expiration (no early exit)

## Requirements

- Python 3.8+
- Schwab API credentials
- Required packages (see `requirements.txt`)

## Setup

1. **Clone/Copy the repository**:
   ```bash
   cd /Users/eliwilner/personal/spx_atm_credit_spread_bot
   ```

2. **Install dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables** (create `.env` file):
   ```bash
   # Schwab API (required)
   SCHWAB_CLIENT_ID=your_client_id
   SCHWAB_CLIENT_SECRET=your_client_secret
   SCHWAB_REDIRECT_URI=https://127.0.0.1:8080/callback
   
   # Email Configuration (for EOD reports - optional)
   EMAIL_SENDER=your-email@gmail.com
   EMAIL_PASSWORD=your-app-password
   EMAIL_RECIPIENT=recipient@example.com
   
   # Position Sizing (optional - has defaults)
   DAILY_RISK_PCT=0.03
   MIN_CONTRACTS=1
   MAX_CONTRACTS=50
   
   # Safety Gates (optional - defaults are safe)
   DRY_RUN=true
   ENABLE_LIVE_TRADING=false
   ```
   
   See `EMAIL_SETUP.md` for detailed email configuration instructions.

4. **Authenticate with Schwab API**:
   ```bash
   python manual_auth.py
   ```

## Usage

Run the bot:
```bash
python automate_trading.py
```

Dry run mode (no orders placed):
```bash
python automate_trading.py --dry-run
```

## Strategy Details

### Opening Range (OR)
- Single 30-minute candle: 09:30-10:00 ET
- ORO = OR open
- ORH = OR high
- ORL = OR low
- ORC = OR close

### Step A: Bullish OR Setup
- **Trigger**: At 10:00 ET, if ORC > ORO
- **Action**: Place PUT credit spread
- **Strikes**: K_short = round_to_5(ORC), K_long = K_short - 10
- **Monitoring**: Check quotes every 10 seconds until 12:00 ET
- **Entry**: When C_net >= 4.60

### Step B: Bearish ORL Breakout Setup
- **Precondition**: ORC < ORO (only runs if Step A didn't trigger)
- **Trigger**: First 30-minute bar (10:00-12:00) where bar_close < ORL
- **Action**: Place CALL credit spread
- **Strikes**: K_short = round_to_5(breakout_bar_close), K_long = K_short + 10
- **Monitoring**: Check quotes every 10 seconds until 12:00 ET
- **Entry**: When C_net >= 4.60

### Position Sizing
- Daily risk budget: R_day = 5% of account equity
- Max loss per spread: (10 - C_net) * 100
- Quantity: floor(R_day / maxLossPerSpread)
- Minimum: 1 spread

### Credit Filter
- Minimum NET credit: 4.60
- Slippage buffer: 0.10
- Minimum GROSS credit: 4.70
- Trade only if C_net >= 4.60

### P/L Calculation
Calculated at 16:00 ET (expiration):

**PUT Spread**:
- Settlement value = clamp(K_short - SPX_close, 0, 10)
- P/L per spread = (C_net_fill - settlement_value) * 100

**CALL Spread**:
- Settlement value = clamp(SPX_close - K_short, 0, 10)
- P/L per spread = (C_net_fill - settlement_value) * 100

## Logging

All trades are logged to `tracking/trades.csv` with the following fields:
- date, setup, trade_type, trigger_time, fill_time
- SPX_entry, ORO, ORH, ORL, ORC
- K_short, K_long
- C_gross_fill, S, C_net_fill
- qty, R_day, maxLossPerSpread
- SPX_close, settlement_value, pnl_per_spread, total_pnl
- equity_before, equity_after, order_id, order_status

## Important Notes

- **One trade per day**: After placing a trade, the bot stops monitoring
- **No early exit**: Positions are held to expiration
- **No stop loss**: No risk management exits
- **No rolling**: No position adjustments
- **Credit assumed constant**: After fill, credit is locked for P/L calculation

## File Structure

```
spx_atm_credit_spread_bot/
├── automate_trading.py      # Main automation script
├── requirements.txt         # Python dependencies
├── src/
│   ├── strategy/           # Strategy logic
│   │   ├── market_data.py  # SPX market data fetcher
│   │   ├── opening_range.py # OR calculator
│   │   ├── strike_calculator.py # Strike price calculator
│   │   ├── quote_monitor.py # Quote monitoring
│   │   ├── position_sizing.py # Position sizing
│   │   └── pl_calculator.py # P/L calculator
│   ├── orders/             # Order placement
│   ├── accounts/            # Account management
│   ├── quotes/              # Quote management
│   ├── tracking/             # Trade logging
│   └── utils/               # Utilities
├── tracking/                # Trade logs
└── logs/                    # Application logs
```

## License

Private use only.

