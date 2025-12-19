# API Client Module (`client/`)

Low-level client for making authenticated HTTP requests to the Schwab API.

## Overview

The `SchwabClient` class provides a wrapper around HTTP requests with:
- Automatic authentication
- Token refresh on expiration
- Error handling
- Standardized request/response handling

## Key Components

### `SchwabClient` Class

Main API client that handles all HTTP communication with Schwab API.

**Initialization:**
```python
from src.client.schwab_client import SchwabClient

client = SchwabClient()
# Automatically initializes authentication
```

## Methods

### `_make_request(method, endpoint, params=None, data=None, json_data=None)`
Internal method for making authenticated API requests.

**Parameters:**
- `method` (str): HTTP method ('GET', 'POST', 'PUT', 'DELETE', etc.)
- `endpoint` (str): API endpoint path (e.g., '/accounts/accountNumbers')
- `params` (dict, optional): URL query parameters
- `data` (dict, optional): Form data for POST requests
- `json_data` (dict, optional): JSON body for POST/PUT requests

**Returns:**
- `dict`: JSON response from API

**Usage:**
```python
# GET request
response = client._make_request('GET', '/accounts/accountNumbers')

# GET with parameters
response = client._make_request('GET', '/accounts/{hash}/orders', 
                                params={'maxResults': 100})

# POST request
response = client._make_request('POST', '/orders', json_data={'order': {...}})
```

### `get_accounts()`
Get list of account numbers and their encrypted hash values.

**Returns:**
- `list`: List of account dictionaries with 'accountNumber' and 'hashValue'

**Usage:**
```python
accounts = client.get_accounts()
# Returns: [{'accountNumber': '12345678', 'hashValue': 'ABC123...'}]
```

## How It Works

### Request Flow

```
1. Client receives API call request
2. Gets authorization headers from SchwabAuth
3. Makes HTTP request to Schwab API
4. If 401 (Unauthorized):
   a. Automatically refreshes token
   b. Retries request with new token
5. Returns JSON response
```

### Automatic Token Refresh

The client automatically handles token expiration:

```python
# This happens automatically - you don't need to do anything
response = client.get_accounts()
# If token expired:
# 1. Detects 401 error
# 2. Calls auth.refresh_access_token()
# 3. Retries request
# 4. Returns response
```

### Error Handling

The client provides detailed error information:

```python
try:
    response = client.get_accounts()
except requests.exceptions.HTTPError as e:
    # Error details logged automatically
    # Includes status code and response body
```

## API Base URL

The client uses the base URL from configuration:
- Default: `https://api.schwabapi.com/trader/v1`
- Can be overridden with `SCHWAB_API_BASE_URL` in `.env`

## Example Usage

### Basic API Call
```python
from src.client.schwab_client import SchwabClient

client = SchwabClient()

# Get accounts
accounts = client.get_accounts()

# Make custom request
orders = client._make_request(
    'GET',
    '/accounts/5F099387B58E35ADC28E.../orders',
    params={'maxResults': 50}
)
```

### With Error Handling
```python
from src.client.schwab_client import SchwabClient
import requests

client = SchwabClient()

try:
    accounts = client.get_accounts()
    print(f"Found {len(accounts)} accounts")
except requests.exceptions.HTTPError as e:
    print(f"API Error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Dependencies

- `requests` - HTTP library
- `src.auth.schwab_auth` - Authentication
- `src.config` - Configuration
- `src.utils.logger` - Logging

## Extending the Client

To add new API methods:

```python
class SchwabClient:
    # ... existing methods ...
    
    def get_positions(self, account_hash: str) -> Dict:
        """Get positions for an account."""
        return self._make_request('GET', f'/accounts/{account_hash}/positions')
    
    def place_order(self, account_hash: str, order_data: Dict) -> Dict:
        """Place a new order."""
        return self._make_request('POST', f'/accounts/{account_hash}/orders', 
                                  json_data=order_data)
```

## Notes

- All requests are automatically authenticated
- Token refresh happens transparently
- Responses are automatically parsed as JSON
- Errors include detailed logging for debugging

