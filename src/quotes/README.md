# Quotes Module (`quotes/`)

High-level interface for retrieving market data and option quotes from the Schwab API.

## Overview

The `QuotesManager` class provides convenient methods for:
- Getting quotes for stocks, options, and other instruments
- Retrieving SPXW option quotes (same-day expiration by default)
- Getting credit spread quotes using bias (bullish/bearish) and short strike
- Formatting option symbols correctly
- Accessing market data API endpoints

## Quick Start - Same-Day Trading

For same-day SPXW option trading, use the simplified bias-based interface:

```python
from src.quotes.quotes_manager import QuotesManager

mgr = QuotesManager()

# Bullish: Sell $6765 Put, Buy $6760 Put (5 dollar wide, today's expiration)
spread = mgr.get_spxw_credit_spread_quote_by_bias('bullish', 6765)

# Bearish: Sell $6765 Call, Buy $6770 Call (5 dollar wide, today's expiration)
spread = mgr.get_spxw_credit_spread_quote_by_bias('bearish', 6765)

# Access spread information
spread_info = spread['spread_info']
print(f"Net Credit: ${spread_info['net_credit']:.2f}")
print(f"Max Profit: ${spread_info['max_profit']:.2f}")
print(f"Max Loss: ${spread_info['max_loss']:.2f}")
```

**Key Features:**
- **Automatic date**: Uses today's expiration date (no need to specify)
- **Default width**: 5 dollar wide spreads (can be customized)
- **Simple interface**: Just provide bias (bullish/bearish) and short strike

## Key Components

### `QuotesManager` Class

Manages market data and option quote retrieval.

**Initialization:**
```python
from src.quotes.quotes_manager import QuotesManager

mgr = QuotesManager()
# Automatically initializes API client
```

## Methods

### `get_quotes(symbols, fields=None, indicative=False)`
Get quotes for one or more symbols.

**Parameters:**
- `symbols` (str or list): Single symbol string or list of symbols
  - Examples: `'AAPL'`, `['AAPL', 'MSFT']`, `'SPXW  251113C06810000'`
- `fields` (str, optional): Comma-separated list of root nodes
  - Options: `quote`, `fundamental`, `extended`, `reference`, `regular`
  - Default: `'all'` (returns all fields)
- `indicative` (bool): Include indicative quotes for ETF symbols (default: False)

**Returns:**
- `dict`: Quote data for the requested symbols

**Usage:**
```python
# Get quote for a stock
quote = mgr.get_quotes('AAPL')

# Get quotes for multiple symbols
quotes = mgr.get_quotes(['AAPL', 'MSFT'])

# Get specific fields only
quote = mgr.get_quotes('AAPL', fields='quote,reference')

# Get option quote using direct symbol format
quote = mgr.get_quotes('SPXW  251113C06810000')
```

### `get_option_quote(symbol, expiration_date, option_type, strike, fields=None)`
Get quote for a specific option contract.

**Parameters:**
- `symbol` (str): Underlying symbol (e.g., 'SPXW')
- `expiration_date` (str): Expiration date in YYMMDD format
  - Example: `'251113'` for November 13, 2025
- `option_type` (str): `'C'` for Call or `'P'` for Put
- `strike` (int/float/str): Strike price
  - Examples: `6810`, `'6810'`, `6810.0`
  - Will be automatically formatted to 8 digits
- `fields` (str, optional): Optional fields to return (default: 'all')

**Returns:**
- `dict`: Quote data for the option contract

**Option Symbol Format:**
The method automatically formats the option symbol as:
```
SYMBOL  YYMMDD[C|P]STRIKE
```

Where:
- `SYMBOL`: Underlying symbol (e.g., SPXW)
- Two spaces
- `YYMMDD`: Expiration date (e.g., 251113)
- `C` or `P`: Call or Put
- `STRIKE`: Strike price * 1000, formatted to 8 digits (e.g., 6810 → 06810000)

**Example:**
```python
# Get quote for SPXW Nov 13, 2025 $6810 Call
quote = mgr.get_option_quote('SPXW', '251113', 'C', 6810)
# Generates symbol: "SPXW  251113C06810000"

# Get quote for SPXW Nov 13, 2025 $6815 Put
quote = mgr.get_option_quote('SPXW', '251113', 'P', 6815)
# Generates symbol: "SPXW  251113P06815000"
```

### `get_spxw_option_quote(expiration_date, option_type, strike, fields=None)`
Convenience method to get SPXW option quotes.

**Parameters:**
- `expiration_date` (str): Expiration date in YYMMDD format
- `option_type` (str): `'C'` for Call or `'P'` for Put
- `strike` (int/float/str): Strike price
- `fields` (str, optional): Optional fields to return

**Returns:**
- `dict`: Quote data for the SPXW option contract

**Usage:**
```python
# Get quote for SPXW Nov 13, 2025 $6810 Call
quote = mgr.get_spxw_option_quote('251113', 'C', 6810)

# Get quote for SPXW Nov 13, 2025 $6815 Put
quote = mgr.get_spxw_option_quote('251113', 'P', 6815)
```

## How It Works

### Option Symbol Formatting

The module automatically handles option symbol formatting:

```
Strike: 6810
→ Multiply by 1000: 6810000
→ Pad to 8 digits: 06810000
→ Final symbol: "SPXW  251113C06810000"
```

### Market Data API

The quotes module uses a different base URL than the trading API:
- Trading API: `https://api.schwabapi.com/trader/v1`
- Market Data API: `https://api.schwabapi.com/marketdata/v1`

The module automatically uses the correct endpoint for market data requests.

## Complete Example

```python
from src.quotes.quotes_manager import QuotesManager

# Initialize
mgr = QuotesManager()

# Get SPXW option quote
quote = mgr.get_spxw_option_quote('251113', 'C', 6810)

# Access quote data
symbol_data = quote.get('SPXW  251113C06810000', {})
quote_data = symbol_data.get('quote', {})

print(f"Bid: ${quote_data.get('bidPrice', 0):.2f}")
print(f"Ask: ${quote_data.get('askPrice', 0):.2f}")
print(f"Last: ${quote_data.get('lastPrice', 0):.2f}")
print(f"Mark: ${quote_data.get('mark', 0):.2f}")
print(f"Delta: {quote_data.get('delta', 0):.4f}")
print(f"Gamma: {quote_data.get('gamma', 0):.4f}")
print(f"Open Interest: {quote_data.get('openInterest', 0)}")
```

## Quote Response Structure

The quote response contains:

```python
{
  "SPXW  251113C06810000": {
    "assetMainType": "OPTION",
    "symbol": "SPXW  251113C06810000",
    "quote": {
      "bidPrice": 1.5,
      "askPrice": 1.6,
      "lastPrice": 1.5,
      "mark": 1.55,
      "delta": 0.09250745,
      "gamma": 0.0045271,
      "openInterest": 370,
      "highPrice": 27.7,
      "lowPrice": 1.45,
      "closePrice": 47.2816,
      "netChange": -45.7816,
      "netPercentChange": -96.82751853,
      ...
    }
  }
}
```

## Key Quote Fields

- `bidPrice` - Current bid price
- `askPrice` - Current ask price
- `lastPrice` - Last trade price
- `mark` - Mark price (midpoint)
- `delta` - Option delta (price sensitivity)
- `gamma` - Option gamma (delta sensitivity)
- `openInterest` - Number of open contracts
- `highPrice` - Day's high
- `lowPrice` - Day's low
- `closePrice` - Previous close
- `netChange` - Price change from previous close
- `netPercentChange` - Percentage change

## Dependencies

- `src.client.schwab_client` - API client (for authentication)
- `src.utils.logger` - Logging
- `requests` - HTTP requests

### `get_credit_spread_quote(symbol, expiration_date, spread_type, short_strike, width=5, fields=None)`
Get quote for a credit spread (5-dollar wide by default).

**Parameters:**
- `symbol` (str): Underlying symbol (e.g., 'SPXW')
- `expiration_date` (str): Expiration date in YYMMDD format
- `spread_type` (str): 'CALL' for Call Credit Spread (bearish) or 'PUT' for Put Credit Spread (bullish)
- `short_strike` (int/float/str): Strike price of the short leg (the one you sell)
- `width` (int): Width of the spread in dollars (default: 5)
- `fields` (str, optional): Optional fields to return

**Returns:**
- `dict`: Combined spread quote with:
  - `short_leg`: Quote for short leg (sold option)
  - `long_leg`: Quote for long leg (bought option)
  - `spread_info`: Spread details including:
    - `net_credit`: Best case credit you'd receive
    - `net_debit`: Worst case debit to close
    - `net_mid`: Mid price
    - `max_profit`: Maximum profit potential
    - `max_loss`: Maximum loss potential
    - `breakeven`: Breakeven price

**Call Credit Spread (Bearish):**
- Short lower strike call, Long higher strike call
- Example: Short $6810 Call, Long $6815 Call

**Put Credit Spread (Bullish):**
- Short higher strike put, Long lower strike put
- Example: Short $6810 Put, Long $6805 Put

**Usage:**
```python
# Call Credit Spread: Sell $6810 Call, Buy $6815 Call
spread = mgr.get_credit_spread_quote('SPXW', '251113', 'CALL', 6810, width=5)

# Put Credit Spread: Sell $6810 Put, Buy $6805 Put
spread = mgr.get_credit_spread_quote('SPXW', '251113', 'PUT', 6810, width=5)

# Access spread information
spread_info = spread['spread_info']
print(f"Net Credit: ${spread_info['net_credit']:.2f}")
print(f"Max Profit: ${spread_info['max_profit']:.2f}")
print(f"Max Loss: ${spread_info['max_loss']:.2f}")
```

### `get_spxw_credit_spread_quote_by_bias(bias, short_strike, width=5, expiration_date=None, fields=None)`
**Simplified method to get SPXW credit spread quotes using bias and short strike.**
Uses today's expiration date by default (for same-day trading).

**Parameters:**
- `bias` (str): 'bearish' for Call Credit Spread or 'bullish' for Put Credit Spread
- `short_strike` (int/float/str): Strike price of the short leg (the one you sell)
- `width` (int): Width of the spread in dollars (default: 5)
- `expiration_date` (str, optional): Expiration date in YYMMDD format. If None, uses today's date.
- `fields` (str, optional): Optional fields to return

**Returns:**
- `dict`: Combined spread quote data

**Usage:**
```python
# Bullish: Sell $6765 Put, Buy $6760 Put (5 dollar wide, today's expiration)
spread = mgr.get_spxw_credit_spread_quote_by_bias('bullish', 6765)

# Bearish: Sell $6765 Call, Buy $6770 Call (5 dollar wide, today's expiration)
spread = mgr.get_spxw_credit_spread_quote_by_bias('bearish', 6765)

# With custom width (future use)
spread = mgr.get_spxw_credit_spread_quote_by_bias('bullish', 6765, width=10)

# Access spread information
spread_info = spread['spread_info']
print(f"Net Credit: ${spread_info['net_credit']:.2f}")
print(f"Max Profit: ${spread_info['max_profit']:.2f}")
print(f"Max Loss: ${spread_info['max_loss']:.2f}")
```

**How it works:**
- **Bullish bias** → Put Credit Spread: Short higher strike, Long lower strike
  - Example: Short $6765 Put, Long $6760 Put (width: $5)
- **Bearish bias** → Call Credit Spread: Short lower strike, Long higher strike
  - Example: Short $6765 Call, Long $6770 Call (width: $5)

### `get_spxw_credit_spread_quote(expiration_date, spread_type, short_strike, width=5, fields=None)`
Original method to get SPXW credit spread quotes with explicit expiration date.

**Usage:**
```python
# Call Credit Spread
spread = mgr.get_spxw_credit_spread_quote('251113', 'CALL', 6810)

# Put Credit Spread
spread = mgr.get_spxw_credit_spread_quote('251113', 'PUT', 6810)
```

## Credit Spread Details

### Call Credit Spread (Bearish)
- **Structure**: Sell lower strike call, Buy higher strike call
- **Example**: Short $6810 Call, Long $6815 Call (5-dollar wide)
- **Max Profit**: Net credit received
- **Max Loss**: Width - Net credit
- **Breakeven**: Short strike + Net credit

### Put Credit Spread (Bullish)
- **Structure**: Sell higher strike put, Buy lower strike put
- **Example**: Short $6810 Put, Long $6805 Put (5-dollar wide)
- **Max Profit**: Net credit received
- **Max Loss**: Width - Net credit
- **Breakeven**: Short strike - Net credit

## Notes

- Option symbols must be formatted exactly as shown
- Strike prices are multiplied by 1000 and padded to 8 digits
- Market data API uses different base URL than trading API
- All authentication is handled automatically
- Token refresh happens transparently on expiration
- Credit spreads are 5-dollar wide by default (configurable)
- Both legs are quoted simultaneously in one API call

## Future Enhancements

For trading strategies, you can:
- Build option chains dynamically
- Calculate Greeks for strategy analysis
- Monitor bid/ask spreads
- Track open interest changes
- Build volatility surfaces
- Analyze multiple spread widths

