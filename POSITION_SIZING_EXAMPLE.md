# Position Sizing Calculation Example

## Configuration (Environment Variables)

```bash
DAILY_RISK_PCT=0.03    # 3% risk per trade
MIN_CONTRACTS=1        # Minimum 1 contract
MAX_CONTRACTS=50       # Maximum 50 contracts
```

## Example Calculation

### Inputs:
- **Account Equity**: $100,000
- **C_net** (Net credit per spread): $4.60
- **Spread Width**: 10 points (always)
- **Daily Risk %**: 3% (0.03)
- **Min Contracts**: 1
- **Max Contracts**: 50

### Step-by-Step Calculation:

#### Step 1: Calculate Daily Risk Budget
```
R_day = DAILY_RISK_PCT × account_equity
R_day = 0.03 × $100,000
R_day = $3,000
```

#### Step 2: Calculate Max Loss Per Spread
```
maxLossPerSpread = (SPREAD_WIDTH - C_net) × 100
maxLossPerSpread = (10 - 4.60) × 100
maxLossPerSpread = 5.40 × 100
maxLossPerSpread = $540
```

#### Step 3: Calculate Base Quantity
```
qty = floor(R_day / maxLossPerSpread)
qty = floor($3,000 / $540)
qty = floor(5.555...)
qty = 5
```

#### Step 4: Apply Minimum
```
qty = max(MIN_CONTRACTS, qty)
qty = max(1, 5)
qty = 5  (no change, already above minimum)
```

#### Step 5: Apply Maximum
```
qty = min(qty, MAX_CONTRACTS)
qty = min(5, 50)
qty = 5  (no change, already below maximum)
```

### Final Result:
**Quantity: 5 contracts**

---

## Another Example (Higher Equity)

### Inputs:
- **Account Equity**: $500,000
- **C_net**: $4.60
- **Daily Risk %**: 3%
- **Min Contracts**: 1
- **Max Contracts**: 50

### Calculation:

#### Step 1: Daily Risk Budget
```
R_day = 0.03 × $500,000 = $15,000
```

#### Step 2: Max Loss Per Spread
```
maxLossPerSpread = (10 - 4.60) × 100 = $540
```

#### Step 3: Base Quantity
```
qty = floor($15,000 / $540) = floor(27.777...) = 27
```

#### Step 4: Apply Minimum
```
qty = max(1, 27) = 27
```

#### Step 5: Apply Maximum
```
qty = min(27, 50) = 27
```

### Final Result:
**Quantity: 27 contracts**

---

## Example with Max Cap Hit

### Inputs:
- **Account Equity**: $1,000,000
- **C_net**: $4.60
- **Daily Risk %**: 3%
- **Min Contracts**: 1
- **Max Contracts**: 50

### Calculation:

#### Step 1: Daily Risk Budget
```
R_day = 0.03 × $1,000,000 = $30,000
```

#### Step 2: Max Loss Per Spread
```
maxLossPerSpread = (10 - 4.60) × 100 = $540
```

#### Step 3: Base Quantity
```
qty = floor($30,000 / $540) = floor(55.555...) = 55
```

#### Step 4: Apply Minimum
```
qty = max(1, 55) = 55
```

#### Step 5: Apply Maximum (CAP HIT!)
```
qty = min(55, 50) = 50
```

### Final Result:
**Quantity: 50 contracts** (capped at maximum)

---

## Example with Low Equity (Minimum Hit)

### Inputs:
- **Account Equity**: $10,000
- **C_net**: $4.60
- **Daily Risk %**: 3%
- **Min Contracts**: 1
- **Max Contracts**: 50

### Calculation:

#### Step 1: Daily Risk Budget
```
R_day = 0.03 × $10,000 = $300
```

#### Step 2: Max Loss Per Spread
```
maxLossPerSpread = (10 - 4.60) × 100 = $540
```

#### Step 3: Base Quantity
```
qty = floor($300 / $540) = floor(0.555...) = 0
```

#### Step 4: Apply Minimum (MINIMUM HIT!)
```
qty = max(1, 0) = 1
```

#### Step 5: Apply Maximum
```
qty = min(1, 50) = 1
```

### Final Result:
**Quantity: 1 contract** (minimum enforced)

---

## Formula Summary

```
R_day = DAILY_RISK_PCT × account_equity
maxLossPerSpread = (10 - C_net) × 100
qty = floor(R_day / maxLossPerSpread)
qty = max(MIN_CONTRACTS, qty)
qty = min(qty, MAX_CONTRACTS)
```

## Code Location

- **Config**: `src/config.py` (lines 42-45)
- **Calculation**: `src/strategy/position_sizing.py` (lines 34-47)
- **Usage**: `automate_trading.py` (line 141-145)

