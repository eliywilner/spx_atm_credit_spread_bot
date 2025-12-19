# Compliance Checklist - Exact File/Function Names

## ✅ 1. Hard Safety Gates

### DRY_RUN Configuration
- **File**: `src/config.py`
- **Line**: 24-25
- **Default**: `DRY_RUN = True`
- **Source**: Environment variable `DRY_RUN` (defaults to 'true')

### ENABLE_LIVE_TRADING Configuration
- **File**: `src/config.py`
- **Line**: 28-29
- **Default**: `ENABLE_LIVE_TRADING = False`
- **Source**: Environment variable `ENABLE_LIVE_TRADING` (defaults to 'false')

### Order Placement Safety Check
- **File**: `src/orders/spread_order_placer.py`
- **Function**: `place_10wide_credit_spread()`
- **Lines**: 99-130
- **Logic**: 
  ```python
  if Config.DRY_RUN or not Config.ENABLE_LIVE_TRADING:
      # Log order payload, return mock response
      # NEVER calls requests.post()
  ```
- **Status**: ✅ **HARD-BLOCKED** - No API calls when DRY_RUN=True or ENABLE_LIVE_TRADING=False

### Safety Gate Display
- **File**: `automate_trading.py`
- **Function**: `main()`
- **Lines**: 448-456
- **Status**: ✅ Displays safety gate status at startup

---

## ✅ 2. Decision Tree Logic

### OR Candle (09:30-10:00)
- **File**: `src/strategy/opening_range.py`
- **Function**: `get_opening_range()`
- **Lines**: 19-64
- **Status**: ✅ Fetches single 30-minute candle (09:30-10:00), returns ORO/ORH/ORL/ORC

### Step A: Bullish OR at 10:00
- **File**: `automate_trading.py`
- **Function**: `step_a_bullish_or()`
- **Lines**: 227-276
- **Checks**: 
  - Line 248: `if orc <= oro: return None` (only proceeds if ORC > ORO)
  - Line 255: `spx_entry = orc` (SPX_entry = ORC)
  - Line 261: `k_short, k_long = StrikeCalculator.calculate_put_spread_strikes(spx_entry)` (strikes computed ONCE)
  - Line 266: Calls `monitor_quotes_and_place_order()` (monitors until 12:00)
- **Status**: ✅ **CORRECT**

### Step B: Bearish ORL Breakout (10:00-12:00)
- **File**: `automate_trading.py`
- **Function**: `step_b_bearish_orl_breakout()`
- **Lines**: 279-356
- **Checks**:
  - Line 300: `if orc >= oro: return None` (only proceeds if ORC < ORO)
  - Lines 311-317: Gets 30-minute candles from 10:00-12:00
  - Lines 324-330: Finds FIRST bar where `bar_close < ORL`
  - Line 337: `spx_entry = breakout_candle.get('close', 0)` (SPX_entry = breakout_bar_close)
  - Line 343: `k_short, k_long = StrikeCalculator.calculate_call_spread_strikes(spx_entry)` (strikes computed ONCE)
  - Line 348: Calls `monitor_quotes_and_place_order()` (monitors until 12:00)
- **Status**: ✅ **CORRECT**

### Step A End-of-Day Logic
- **File**: `automate_trading.py`
- **Function**: `main()`
- **Lines**: 507-519
- **Logic**: 
  - If Step A returned None AND ORC > ORO: END DAY (Step B skipped)
  - If Step A returned None AND ORC < ORO: Proceed to Step B
- **Status**: ✅ **CORRECT** - Matches spec: "If no fill by 12:00 → END DAY and do NOT evaluate bearish setup"

### Max 1 Trade Per Day
- **File**: `automate_trading.py`
- **Function**: `main()`
- **Lines**: 502-519
- **Logic**: Step B only runs if Step A didn't place a trade
- **Status**: ✅ **CORRECT**

---

## ✅ 3. Strike Selection

### round_to_5() Function
- **File**: `src/strategy/strike_calculator.py`
- **Function**: `round_to_5()`
- **Lines**: 9-29
- **Formula**: `5.0 * math.floor((x + 2.5) / 5.0)`
- **Status**: ✅ **CORRECT** - Matches spec exactly

### PUT Spread Strikes
- **File**: `src/strategy/strike_calculator.py`
- **Function**: `calculate_put_spread_strikes()`
- **Lines**: 38-53
- **Formulas**: 
  - `k_short = round_to_5(spx_entry)`
  - `k_long = k_short - 10`
- **Status**: ✅ **CORRECT**

### CALL Spread Strikes
- **File**: `src/strategy/strike_calculator.py`
- **Function**: `calculate_call_spread_strikes()`
- **Lines**: 56-71
- **Formulas**:
  - `k_short = round_to_5(spx_entry)`
  - `k_long = k_short + 10`
- **Status**: ✅ **CORRECT**

### Strikes Locked at Trigger
- **File**: `automate_trading.py`
- **Function**: `monitor_quotes_and_place_order()`
- **Parameters**: `k_short`, `k_long` (passed in, computed once before monitoring)
- **Status**: ✅ **CORRECT** - Strikes never recomputed during monitoring

---

## ✅ 4. Credit Computation + Filter

### Mid Price Calculation
- **File**: `src/strategy/quote_monitor.py`
- **Function**: `calculate_mid_price()`
- **Lines**: 32-56
- **Formula**: `mid = (bid + ask) / 2.0`
- **Status**: ✅ **CORRECT**

### C_gross Calculation
- **File**: `src/strategy/quote_monitor.py`
- **Function**: `get_spread_credit()`
- **Line**: 129
- **Formula**: `c_gross = short_mid - long_mid`
- **Status**: ✅ **CORRECT**

### C_net Calculation
- **File**: `src/strategy/quote_monitor.py`
- **Function**: `get_spread_credit()`
- **Line**: 132
- **Formula**: `c_net = c_gross - Config.SLIPPAGE_BUFFER`
- **Slippage Buffer**: `S = 0.10` (Config line 29)
- **Status**: ✅ **CORRECT**

### Credit Filter
- **File**: `src/strategy/quote_monitor.py`
- **Function**: `meets_credit_threshold()`
- **Lines**: 159-180
- **Logic**: `c_net >= Config.MIN_NET_CREDIT` (4.60)
- **Status**: ✅ **CORRECT**

### Missing Quotes Handling
- **File**: `src/strategy/quote_monitor.py`
- **Function**: `get_spread_credit()`
- **Lines**: 124-126, 153-157
- **Behavior**: Returns `None` if quotes unavailable
- **File**: `automate_trading.py`
- **Function**: `monitor_quotes_and_place_order()`
- **Lines**: 107-112
- **Behavior**: Logs warning, continues monitoring (does not crash)
- **Status**: ✅ **CORRECT**

---

## ✅ 5. Position Sizing (5% Daily Risk)

### Position Size Calculation
- **File**: `src/strategy/position_sizing.py`
- **Function**: `calculate_position_size()`
- **Lines**: 14-63
- **Formulas**:
  - Line 34: `r_day = Config.DAILY_RISK_PCT * account_equity` (5%)
  - Line 37: `max_loss_per_spread = (Config.SPREAD_WIDTH - c_net) * 100`
  - Line 40: `qty = math.floor(r_day / max_loss_per_spread)`
  - Line 43: `qty = max(1, qty)` (minimum 1)
- **Status**: ✅ **CORRECT**

### Account Equity Source
- **File**: `automate_trading.py`
- **Function**: `main()`
- **Line**: 496
- **Source**: `account_mgr.get_net_liquidity()`
- **Status**: ✅ **CORRECT**

---

## ✅ 6. Logging Requirements

### Trade Logger CSV Columns
- **File**: `src/tracking/trade_logger.py`
- **Lines**: 18-35
- **Columns**: All required fields present ✅
  - date, setup, trade_type
  - trigger_time, fill_time
  - SPX_entry, ORO, ORH, ORL, ORC
  - K_short, K_long
  - C_gross_fill, S, C_net_fill
  - qty, R_day, maxLossPerSpread
  - SPX_close, settlement_value, pnl_per_spread, total_pnl
  - equity_before, equity_after, order_id, order_status

### Order Payload Logging (Dry-Run)
- **File**: `src/orders/spread_order_placer.py`
- **Function**: `place_10wide_credit_spread()`
- **Lines**: 99-130
- **Output**: Logs complete order JSON payload when DRY_RUN=True
- **Status**: ✅ **COMPLETE**

### Credit Logging During Monitoring
- **File**: `automate_trading.py`
- **Function**: `monitor_quotes_and_place_order()`
- **Line**: 115
- **Output**: Logs C_gross and C_net at each check
- **Status**: ✅ **COMPLETE**

---

## Deviations Found

### None
All requirements match the spec exactly.

---

## Final Confirmation

### DRY_RUN Hard-Block: ✅ **CONFIRMED**
- **File**: `src/orders/spread_order_placer.py`
- **Function**: `place_10wide_credit_spread()`
- **Lines**: 99-130
- **Logic**: `if Config.DRY_RUN or not Config.ENABLE_LIVE_TRADING:` → Log payload, return mock, **NEVER call API**
- **Default State**: DRY_RUN=True, ENABLE_LIVE_TRADING=False
- **Result**: ✅ **LIVE ORDERS ARE HARD-BLOCKED BY DEFAULT**

### All Spec Requirements: ✅ **MET**

