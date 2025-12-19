# Authentication Module (`auth/`)

Handles OAuth 2.0 authentication with the Schwab API, including token management and automatic refresh.

## Overview

The `SchwabAuth` class manages the complete OAuth 2.0 flow:
- Authorization URL generation
- Browser-based authentication
- Token exchange and storage
- Automatic token refresh
- Secure token persistence

## Key Components

### `SchwabAuth` Class

Main authentication handler that manages the OAuth flow.

**Initialization:**
```python
from src.auth.schwab_auth import SchwabAuth

auth = SchwabAuth()
# Automatically validates configuration and loads existing tokens
```

## Methods

### `authenticate(manual_code=None)`
Complete OAuth authentication flow.

**Parameters:**
- `manual_code` (optional): Authorization code if callback server doesn't work

**Returns:**
- `str`: Access token

**Usage:**
```python
# Automatic authentication (opens browser)
token = auth.authenticate()

# Manual authentication (if callback fails)
token = auth.authenticate(manual_code='C0.abc123...')
```

### `get_access_token()`
Get a valid access token, refreshing if necessary.

**Returns:**
- `str`: Valid access token

**Usage:**
```python
token = auth.get_access_token()
# Automatically loads from file or authenticates if needed
```

### `refresh_access_token()`
Manually refresh the access token using the refresh token.

**Returns:**
- `dict`: New token data

**Usage:**
```python
token_data = auth.refresh_access_token()
# Gets new access token and saves it
```

### `get_headers()`
Get HTTP headers with authorization token.

**Returns:**
- `dict`: Headers with `Authorization` and `Accept` keys

**Usage:**
```python
headers = auth.get_headers()
# Returns: {'Authorization': 'Bearer <token>', 'Accept': 'application/json'}
```

## How It Works

### 1. Initial Authentication Flow

```
1. User calls authenticate()
2. System checks for existing tokens
3. If no tokens, generates authorization URL
4. Opens browser for user to authorize
5. Starts HTTPS callback server (localhost:8080)
6. Receives authorization code
7. Exchanges code for access + refresh tokens
8. Saves tokens to tokens.json
```

### 2. Token Refresh Flow

```
1. API call returns 401 (Unauthorized)
2. Client automatically calls refresh_access_token()
3. Uses refresh token to get new access token
4. Saves new tokens
5. Retries original API call
```

### 3. Token Storage

Tokens are stored in `tokens.json` in the project root:
```json
{
  "access_token": "I0.abc123...",
  "refresh_token": "def456...",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

## Configuration

Requires these environment variables (in `.env`):
- `SCHWAB_CLIENT_ID` - Your App Key
- `SCHWAB_CLIENT_SECRET` - Your App Secret
- `SCHWAB_REDIRECT_URI` - Must be HTTPS (e.g., `https://127.0.0.1:8080/callback`)

## Security Features

- **HTTPS Callback Server**: Uses self-signed SSL certificate for localhost
- **Token Encryption**: Tokens stored securely (not in code)
- **Automatic Refresh**: No manual token management needed
- **Error Handling**: Graceful handling of expired tokens

## Troubleshooting

### Callback Server Issues
If browser can't reach callback server:
1. Accept the security warning (Advanced → Proceed)
2. Or use `manual_auth.py` to extract code from URL

### Token Expiration
Tokens automatically refresh on 401 errors. If refresh fails:
1. Delete `tokens.json`
2. Run authentication again

### Certificate Issues
The module auto-generates SSL certificates. If issues occur:
- Ensure OpenSSL is installed
- Or use ngrok for HTTPS tunnel

## Dependencies

- `requests` - HTTP requests
- `ssl` - HTTPS server
- `http.server` - Callback server
- `webbrowser` - Open auth URL
- `src.config` - Configuration
- `src.utils.logger` - Logging

