# Orders Module (`orders/`)

Order placement and management for credit spread trades.

## Overview

The `OrderManager` class provides functionality to:
- Get quotes for credit spreads
- Build order structures in the correct format
- Place credit spread orders via the Schwab API
- Support both SPXW and XSP symbols

## Key Components

### `OrderManager` Class

Manages order placement for credit spreads.

**Initialization:**
```python
from src.orders.order_manager import OrderManager

mgr = OrderManager()
```

## Methods

### `place_credit_spread_order(date, symbol, bias, short_strike, quantity=1, account_number=None)`

Place a credit spread order.

**Parameters:**
- `date` (str): Expiration date in YYMMDD format (e.g., '251114' for Nov 14, 2025)
- `symbol` (str): 'SPXW' or 'XSP'
- `bias` (str): 'bullish' or 'bearish'
  - **Bullish** → Put Credit Spread (sell higher strike put, buy lower strike put)
  - **Bearish** → Call Credit Spread (sell lower strike call, buy higher strike call)
- `short_strike` (int/float): Strike price for the short leg (typically the midpoint of opening range)
- `quantity` (int): Number of contracts (default: 1)
- `account_number` (str, optional): Account number to place order in. If None, uses first account.

**Returns:**
- `dict`: Order response from Schwab API

**Usage:**
```python
from src.orders.order_manager import OrderManager

mgr = OrderManager()

# Place a bullish put credit spread for XSP
order = mgr.place_credit_spread_order(
    date='251114',
    symbol='XSP',
    bias='bullish',
    short_strike=675,
    quantity=1
)

# Place a bearish call credit spread for SPXW
order = mgr.place_credit_spread_order(
    date='251114',
    symbol='SPXW',
    bias='bearish',
    short_strike=6810,
    quantity=2
)
```

## Order Format

The method automatically builds the order in the correct Schwab API format:

```json
{
  "orderType": "NET_CREDIT",
  "session": "NORMAL",
  "price": "0.50",
  "duration": "DAY",
  "orderStrategyType": "SINGLE",
  "orderLegCollection": [
    {
      "instruction": "BUY_TO_OPEN",
      "quantity": 1,
      "instrument": {
        "symbol": "XSP   251114P00674000",
        "assetType": "OPTION"
      }
    },
    {
      "instruction": "SELL_TO_OPEN",
      "quantity": 1,
      "instrument": {
        "symbol": "XSP   251114P00675000",
        "assetType": "OPTION"
      }
    }
  ]
}
```

## Spread Widths

- **SPXW**: 5 dollar wide spreads (default)
- **XSP**: 1 dollar wide spreads (default)

## Strike Rounding

Strikes are automatically rounded to the correct intervals:
- **SPXW**: Rounds to nearest 5 dollars
- **XSP**: Rounds to nearest 1 dollar

## Price

The order is placed at the **mid price** from the spread quote:
- Mid price = (Bid + Ask) / 2 for the spread
- Automatically calculated from the individual leg quotes

## Example Workflow

```python
from src.orders.order_manager import OrderManager
from src.strategy.opening_range import OpeningRangeTracker

# 1. Get opening range and midpoint
tracker = OpeningRangeTracker(symbol='XSP')
opening_range = tracker.get_historical_opening_range()
midpoint = opening_range['midpoint']  # e.g., 675

# 2. Find breakout candle
breakout = tracker.find_first_breakout_candle()
# CRITICAL: Breakout BELOW = bearish = Call Credit Spread
#           Breakout ABOVE = bullish = Put Credit Spread
bias = 'bearish' if breakout['direction'] == 'below' else 'bullish'

# 3. Place order
order_mgr = OrderManager()
order = order_mgr.place_credit_spread_order(
    date='251114',  # Tomorrow's date
    symbol='XSP',
    bias=bias,
    short_strike=midpoint,
    quantity=1
)
```

## Error Handling

The method will raise exceptions for:
- Invalid symbol (must be 'SPXW' or 'XSP')
- Invalid bias (must be 'bullish' or 'bearish')
- Account not found
- API errors (logged with details)

## Dependencies

- `src.client.schwab_client` - API client for authenticated requests
- `src.accounts.account_manager` - Account hash retrieval
- `src.quotes.quotes_manager` - Spread quotes and option symbol formatting

