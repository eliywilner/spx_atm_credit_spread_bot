# Plan: Get Actual Fill Credit from Broker Instead of Calculated Values

## Current Problem

**EOD Report shows:**
- C_gross (fill): $4.70
- Slippage Buffer (S): $0.10
- C_net (fill): $4.60 ❌ (WRONG - calculated, not actual)
- P/L: $460.00 ❌ (WRONG - based on $4.60)

**Broker shows:**
- Net Price: $4.70 ✅ (ACTUAL fill credit)
- P/L Open: $470.00 ✅ (ACTUAL P/L)

**Difference:** $0.10 per contract = $10.00 total P/L difference

## Root Cause

Currently in `automate_trading.py` line 207-209:
```python
'C_gross_fill': c_gross,  # From quote at time of order
'S': Config.SLIPPAGE_BUFFER,  # $0.10 buffer
'C_net_fill': c_net,  # c_gross - slippage buffer = $4.60
```

This uses **calculated/estimated** values, not the **actual fill credit** from the broker.

## Solution: Get Actual Fill Credit from Filled Order

### Step 1: Create Helper Function to Extract Fill Credit

**Location:** New function in `src/orders/` or add to existing module

**Function:** `get_actual_fill_credit_from_order(order_details: Dict) -> float`

**Logic:**
1. Check if order has `orderActivityCollection`
2. Get first activity (the fill)
3. Extract `executionLegs` from activity
4. Match each execution leg to order leg to determine BUY vs SELL
5. Calculate: (SELL leg prices × quantities) - (BUY leg prices × quantities)
6. Return net credit

**Pseudocode:**
```python
def get_actual_fill_credit_from_order(order_details: Dict) -> Optional[float]:
    """
    Extract actual fill credit from filled order.
    
    Args:
        order_details: Order dictionary from broker API
    
    Returns:
        Actual net credit received, or None if not available
    """
    # Check if order is filled
    if order_details.get('status') != 'FILLED':
        return None
    
    # Get order legs to map legId to instruction (BUY/SELL)
    order_legs = order_details.get('orderLegCollection', [])
    leg_map = {}
    for leg in order_legs:
        leg_map[leg.get('legId')] = leg.get('instruction', '')
    
    # Get execution activities
    activities = order_details.get('orderActivityCollection', [])
    if not activities:
        return None
    
    # Get first activity (the fill)
    activity = activities[0]
    execution_legs = activity.get('executionLegs', [])
    if not execution_legs:
        return None
    
    # Calculate net credit
    total_credit = 0.0
    total_debit = 0.0
    
    for exec_leg in execution_legs:
        leg_id = exec_leg.get('legId')
        price = exec_leg.get('price', 0)
        quantity = exec_leg.get('quantity', 0)
        instruction = leg_map.get(leg_id, '')
        
        if 'SELL' in instruction or 'SELL_TO_OPEN' in instruction:
            total_credit += price * quantity
        elif 'BUY' in instruction or 'BUY_TO_OPEN' in instruction:
            total_debit += price * quantity
    
    net_credit = total_credit - total_debit
    return net_credit
```

### Step 2: Modify `calculate_eod_pl()` Function

**Location:** `automate_trading.py` line 429

**Current Flow:**
1. Gets `c_net_fill` from `trade_data` (calculated $4.60)
2. Uses it for P/L calculation

**New Flow:**
1. Get `order_id` from `trade_data`
2. Fetch filled order from broker using `order_id`
3. Extract actual fill credit using helper function
4. If available, use actual fill credit; otherwise fall back to `c_net_fill`
5. Use actual fill credit for P/L calculation

**Changes Needed:**
```python
def calculate_eod_pl(date: datetime, trade_data: Dict) -> Dict:
    # ... existing code ...
    
    # Get trade parameters
    trade_type = trade_data.get('trade_type', '')
    k_short = float(trade_data.get('K_short', 0))
    c_net_fill = float(trade_data.get('C_net_fill', 0))  # Fallback value
    qty = int(trade_data.get('qty', 0))
    order_id = trade_data.get('order_id', '')
    
    # NEW: Try to get actual fill credit from filled order
    actual_fill_credit = None
    if order_id:
        try:
            from src.accounts.account_manager import AccountManager
            from src.orders.order_utils import get_actual_fill_credit_from_order  # New helper
            
            account_mgr = AccountManager()
            
            # Get filled orders from today
            filled_orders = account_mgr.get_orders_executed_today(
                status='FILLED',
                max_results=10
            )
            
            # Find our order
            our_order = None
            for order in filled_orders:
                if str(order.get('orderId', '')) == str(order_id):
                    our_order = order
                    break
            
            if our_order:
                actual_fill_credit = get_actual_fill_credit_from_order(our_order)
                if actual_fill_credit:
                    logger.info(f"✅ Found actual fill credit from broker: ${actual_fill_credit:.2f}")
                    logger.info(f"   (vs calculated: ${c_net_fill:.2f})")
                    # Update trade_data with actual fill credit
                    trade_data['C_net_fill_actual'] = actual_fill_credit
                    trade_data['C_net_fill_source'] = 'BROKER'
                else:
                    logger.warning("⚠️  Could not extract fill credit from order, using calculated value")
                    trade_data['C_net_fill_source'] = 'CALCULATED'
            else:
                logger.warning(f"⚠️  Order {order_id} not found in filled orders, using calculated value")
                trade_data['C_net_fill_source'] = 'CALCULATED'
        except Exception as e:
            logger.warning(f"⚠️  Error getting actual fill credit: {e}, using calculated value")
            trade_data['C_net_fill_source'] = 'CALCULATED'
    
    # Use actual fill credit if available, otherwise use calculated
    fill_credit_for_pl = actual_fill_credit if actual_fill_credit is not None else c_net_fill
    
    # Calculate P/L using actual fill credit
    if trade_type == 'PUT':
        pl_data = PLCalculator.calculate_put_spread_pl(
            k_short=k_short,
            spx_close=spx_close,
            c_net_fill=fill_credit_for_pl,  # Use actual fill credit
            qty=qty
        )
    else:  # CALL
        pl_data = PLCalculator.calculate_call_spread_pl(
            k_short=k_short,
            spx_close=spx_close,
            c_net_fill=fill_credit_for_pl,  # Use actual fill credit
            qty=qty
        )
    
    # ... rest of function ...
```

### Step 3: Update EOD Report to Show Actual Fill Credit

**Location:** `src/reports/eod_report.py` line 121-124

**Current:**
```python
report_lines.append("Credit:")
report_lines.append(f"  C_gross (fill):          ${trade_data.get('C_gross_fill', 0):.2f}")
report_lines.append(f"  Slippage Buffer (S):     ${trade_data.get('S', 0):.2f}")
report_lines.append(f"  C_net (fill):            ${trade_data.get('C_net_fill', 0):.2f}")
```

**New:**
```python
report_lines.append("Credit:")
fill_source = trade_data.get('C_net_fill_source', 'CALCULATED')
actual_fill = trade_data.get('C_net_fill_actual')
calculated_fill = trade_data.get('C_net_fill', 0)

if actual_fill is not None:
    # Show actual fill credit from broker
    report_lines.append(f"  C_net (actual fill):     ${actual_fill:.2f} ✅ FROM BROKER")
    if calculated_fill != actual_fill:
        report_lines.append(f"  C_net (calculated):      ${calculated_fill:.2f} (not used)")
else:
    # Fallback to calculated
    report_lines.append(f"  C_gross (fill):          ${trade_data.get('C_gross_fill', 0):.2f}")
    report_lines.append(f"  Slippage Buffer (S):     ${trade_data.get('S', 0):.2f}")
    report_lines.append(f"  C_net (fill):           ${calculated_fill:.2f} ⚠️  CALCULATED")
```

## Implementation Steps

### Step 1: Create Helper Function
- **File:** `src/orders/order_utils.py` (new file)
- **Function:** `get_actual_fill_credit_from_order()`
- **Test:** Create unit test with sample order data

### Step 2: Modify `calculate_eod_pl()`
- **File:** `automate_trading.py`
- **Location:** Line 429
- **Changes:**
  - Add logic to fetch filled order
  - Extract actual fill credit
  - Use actual fill credit for P/L calculation
  - Store source in trade_data

### Step 3: Update EOD Report
- **File:** `src/reports/eod_report.py`
- **Location:** Line 121-124
- **Changes:**
  - Show actual fill credit if available
  - Indicate source (BROKER vs CALCULATED)
  - Show calculated value for comparison if different

### Step 4: Add Logging
- Log when actual fill credit is found
- Log when falling back to calculated
- Log the difference between actual and calculated

## Testing Plan

1. **Unit Test:** Test helper function with sample order data
2. **Integration Test:** Test with actual filled order from API
3. **EOD Test:** Run EOD calculation and verify it uses actual fill credit
4. **Report Test:** Verify EOD report shows correct values

## Expected Results

**Before:**
- C_net (fill): $4.60 (calculated)
- P/L: $460.00

**After:**
- C_net (actual fill): $4.70 ✅ FROM BROKER
- P/L: $470.00 ✅ (matches broker)

## Edge Cases to Handle

1. **Order not found:** Fall back to calculated value
2. **Order not filled yet:** Fall back to calculated value
3. **No executionLegs:** Fall back to calculated value
4. **API error:** Fall back to calculated value
5. **Multiple fills:** Sum all fills (shouldn't happen for single order)

## Files to Modify

1. **New:** `src/orders/order_utils.py` - Helper function
2. **Modify:** `automate_trading.py` - `calculate_eod_pl()` function
3. **Modify:** `src/reports/eod_report.py` - Report generation
4. **New:** `tests/test_order_utils.py` - Unit tests

## Summary

This plan will:
- ✅ Get actual fill credit from broker API
- ✅ Use actual fill credit for P/L calculation
- ✅ Show actual fill credit in EOD report
- ✅ Match broker's numbers exactly
- ✅ Have fallback to calculated if actual unavailable
- ✅ Log what source was used

The key is fetching the filled order by `order_id` and extracting the fill prices from `executionLegs` to calculate the actual net credit received.

