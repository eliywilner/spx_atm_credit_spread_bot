# Account Management Module (`accounts/`)

High-level interface for managing accounts and retrieving order information.

## Overview

The `AccountManager` class provides convenient methods for:
- Retrieving account numbers and encrypted hashes
- Getting orders executed today
- Getting orders with custom date ranges
- Managing account information

## Key Components

### `AccountManager` Class

High-level account management interface that handles account operations.

**Initialization:**
```python
from src.accounts.account_manager import AccountManager

mgr = AccountManager()
# Automatically initializes API client
```

## Methods

### `get_account_numbers()`
Get list of all account numbers and their corresponding encrypted hash values.

**Returns:**
- `list`: List of dictionaries with 'accountNumber' and 'hashValue' keys

**Example:**
```python
accounts = mgr.get_account_numbers()
# Returns: [
#   {'accountNumber': '62240062', 'hashValue': '5F099387B58E35ADC28E...'}
# ]
```

**Usage:**
```python
accounts = mgr.get_account_numbers()
for account in accounts:
    print(f"Account: {account['accountNumber']}")
    print(f"Hash: {account['hashValue']}")
```

### `get_account_hash(account_number=None)`
Get the encrypted hash value for a specific account number.

**Parameters:**
- `account_number` (str, optional): Plain text account number. If None, returns hash for first account.

**Returns:**
- `str`: Encrypted hash value to use in API calls

**Raises:**
- `ValueError`: If account number not found

**Usage:**
```python
# Get hash for first account
hash_val = mgr.get_account_hash()

# Get hash for specific account
hash_val = mgr.get_account_hash('62240062')
```

### `get_orders_executed_today(account_number=None, max_results=3000, status=None)`
Get all orders executed today for a specific account.

**Parameters:**
- `account_number` (str, optional): Plain text account number. If None, uses first account.
- `max_results` (int): Maximum number of orders to retrieve (default: 3000)
- `status` (str, optional): Filter by order status (e.g., 'FILLED', 'EXECUTED')

**Returns:**
- `list`: List of order dictionaries

**Usage:**
```python
# Get all orders executed today
orders = mgr.get_orders_executed_today()

# Get filled orders only
filled_orders = mgr.get_orders_executed_today(status='FILLED')

# For specific account
orders = mgr.get_orders_executed_today(account_number='62240062')
```

**Example Response:**
```python
[
  {
    "orderId": 1004677557225,
    "status": "FILLED",
    "enteredTime": "2025-11-13T15:43:24+0000",
    "orderLegCollection": [...],
    "orderActivityCollection": [...]
  }
]
```

### `get_account_balances(account_number=None)`
Get account balances and details for a specific account.

**Parameters:**
- `account_number` (str, optional): Plain text account number. If None, uses first account.

**Returns:**
- `dict`: Account details including:
  - `securitiesAccount`: Account information with balances
    - `currentBalances`: Current cash, equity, buying power, etc.
    - `initialBalances`: Initial account balances
    - `projectedBalances`: Projected balances
    - `accountNumber`: Account number
    - `type`: Account type (MARGIN, CASH, etc.)
  - `aggregatedBalance`: Aggregated balance information

**Usage:**
```python
# Get balances for first account
balances = mgr.get_account_balances()

# Get balances for specific account
balances = mgr.get_account_balances('62240062')

# Access balance information
securities_account = balances['securitiesAccount']
current_balances = securities_account['currentBalances']
cash_balance = current_balances['cashBalance']
buying_power = current_balances['buyingPower']
equity = current_balances['equity']
```

**Example Response:**
```python
{
  "securitiesAccount": {
    "type": "MARGIN",
    "accountNumber": "62240062",
    "currentBalances": {
      "cashBalance": 1629.27,
      "equity": 1629.27,
      "buyingPower": 1129.27,
      "availableFunds": 1129.27,
      ...
    },
    ...
  }
}
```

### `get_net_liquidity(account_number=None)`
Get net liquidity (liquidation value) for a specific account.

Net liquidity represents the total value of the account if all positions were liquidated at current market prices.

**Parameters:**
- `account_number` (str, optional): Plain text account number. If None, uses first account.

**Returns:**
- `float`: Net liquidity value (liquidation value)

**Usage:**
```python
# Get net liquidity for first account
net_liquidity = mgr.get_net_liquidity()

# Get net liquidity for specific account
net_liquidity = mgr.get_net_liquidity('62240062')

print(f"Net Liquidity: ${net_liquidity:,.2f}")
```

**Note:** Net liquidity is the same as `liquidationValue` in the account balances response. It represents the total account value if all positions were closed at current market prices.

### `get_orders(account_number=None, from_entered_time=None, to_entered_time=None, max_results=3000, status=None)`
Get orders for a specific account with custom date range.

**Parameters:**
- `account_number` (str, optional): Plain text account number
- `from_entered_time` (str): Start time in ISO-8601 format (e.g., '2024-03-29T00:00:00.000Z')
- `to_entered_time` (str): End time in ISO-8601 format (e.g., '2024-04-28T23:59:59.000Z')
- `max_results` (int): Maximum number of orders (default: 3000)
- `status` (str, optional): Filter by order status

**Returns:**
- `list`: List of order dictionaries

**Raises:**
- `ValueError`: If date parameters are invalid

**Usage:**
```python
# Get orders for date range
orders = mgr.get_orders(
    from_entered_time='2024-03-29T00:00:00.000Z',
    to_entered_time='2024-04-28T23:59:59.000Z'
)

# Get filled orders for specific account
orders = mgr.get_orders(
    account_number='62240062',
    from_entered_time='2024-03-29T00:00:00.000Z',
    to_entered_time='2024-04-28T23:59:59.000Z',
    status='FILLED'
)
```

## How It Works

### Account Hash Management

The module automatically handles the conversion between plain text account numbers and encrypted hashes:

```
1. User provides plain text account number (e.g., '62240062')
2. Module fetches account list from API
3. Finds matching account and returns encrypted hash
4. Uses hash for subsequent API calls
```

### Date Range Handling

For `get_orders_executed_today()`:
- Automatically calculates today's date range in UTC
- Formats dates in ISO-8601 format required by API
- Sets time range from 00:00:00 to 23:59:59

### Caching

The module caches account information to reduce API calls:
- First call fetches and caches account list
- Subsequent calls use cached data when possible

## Complete Example

```python
from src.accounts.account_manager import AccountManager

# Initialize
mgr = AccountManager()

# Get all accounts
accounts = mgr.get_account_numbers()
print(f"Found {len(accounts)} account(s)")

# Get hash for first account
hash_val = mgr.get_account_hash()
print(f"Hash: {hash_val[:30]}...")

# Get orders executed today
orders = mgr.get_orders_executed_today()
print(f"Found {len(orders)} order(s) executed today")

# Process orders
for order in orders:
    print(f"Order ID: {order['orderId']}")
    print(f"Status: {order['status']}")
    print(f"Entered: {order['enteredTime']}")
```

## Order Object Structure

Orders returned by the API contain:

- `orderId` - Unique order identifier
- `status` - Order status (FILLED, EXECUTED, etc.)
- `enteredTime` - When order was entered
- `closeTime` - When order was closed
- `orderLegCollection` - Legs of the order (for multi-leg orders)
- `orderActivityCollection` - Execution details
- `accountNumber` - Account number
- `price` - Order price
- `quantity` - Order quantity

## Dependencies

- `src.client.schwab_client` - API client
- `src.utils.logger` - Logging
- `datetime` - Date/time handling

## Error Handling

The module provides clear error messages:

```python
try:
    hash_val = mgr.get_account_hash('99999999')
except ValueError as e:
    print(f"Account not found: {e}")

try:
    orders = mgr.get_orders(from_entered_time='2024-01-01')
except ValueError as e:
    print(f"Invalid date range: {e}")
```

## Notes

- Account hashes are required for most API calls (security feature)
- Date ranges must be within 1 year (API limitation)
- Maximum date range is 1 year per API documentation
- All times are in UTC

