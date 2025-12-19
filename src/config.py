"""Configuration management for SPX ATM Credit Spread Bot."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration for SPX ATM Credit Spread Bot."""
    
    # Schwab API Credentials
    CLIENT_ID = os.getenv('SCHWAB_CLIENT_ID')
    CLIENT_SECRET = os.getenv('SCHWAB_CLIENT_SECRET')
    REDIRECT_URI = os.getenv('SCHWAB_REDIRECT_URI', 'https://127.0.0.1:8080/callback')
    
    # API Base URLs
    API_BASE_URL = os.getenv('SCHWAB_API_BASE_URL', 'https://api.schwabapi.com/trader/v1')
    AUTH_BASE_URL = os.getenv('SCHWAB_AUTH_BASE_URL', 'https://api.schwabapi.com')
    
    # Token storage
    TOKEN_FILE = 'tokens.json'
    
    # Safety Gates (MANDATORY)
    # DRY_RUN: If True, NEVER place/modify/cancel orders. Default: True (SAFE)
    DRY_RUN = os.getenv('DRY_RUN', 'true').lower() == 'true'
    
    # ENABLE_LIVE_TRADING: Additional gate. Only allow live trading if BOTH are False/True
    # Default: False (SAFE)
    ENABLE_LIVE_TRADING = os.getenv('ENABLE_LIVE_TRADING', 'false').lower() == 'true'
    
    # Strategy Parameters
    # Minimum NET credit required (in option price points)
    MIN_NET_CREDIT = 4.60
    
    # Slippage/fees buffer (in option price points)
    SLIPPAGE_BUFFER = 0.10
    
    # Minimum GROSS credit (MIN_NET_CREDIT + SLIPPAGE_BUFFER)
    MIN_GROSS_CREDIT = MIN_NET_CREDIT + SLIPPAGE_BUFFER  # 4.70
    
    # Daily risk percentage (configurable via environment variable)
    DAILY_RISK_PCT = float(os.getenv('DAILY_RISK_PCT', '0.03'))  # Default: 3%
    
    # Position sizing limits (configurable via environment variables)
    MIN_CONTRACTS = int(os.getenv('MIN_CONTRACTS', '1'))  # Default: 1
    MAX_CONTRACTS = int(os.getenv('MAX_CONTRACTS', '50'))  # Default: 50
    
    # Spread width (always 10 points)
    SPREAD_WIDTH = 10.0
    
    # Quote monitoring interval (seconds)
    QUOTE_MONITOR_INTERVAL = 10
    
    # Market hours (ET)
    MARKET_OPEN_HOUR = 9
    MARKET_OPEN_MINUTE = 30
    MARKET_CLOSE_HOUR = 16
    MARKET_CLOSE_MINUTE = 0
    
    # Opening Range (OR) window
    OR_START_HOUR = 9
    OR_START_MINUTE = 30
    OR_END_HOUR = 10
    OR_END_MINUTE = 0
    
    # Entry windows
    BULLISH_ENTRY_START_HOUR = 10
    BULLISH_ENTRY_START_MINUTE = 0
    BEARISH_ENTRY_START_HOUR = 10
    BEARISH_ENTRY_START_MINUTE = 0
    ENTRY_END_HOUR = 12
    ENTRY_END_MINUTE = 0
    
    @classmethod
    def validate(cls):
        """Validate that required configuration is present."""
        if not cls.CLIENT_ID:
            raise ValueError("SCHWAB_CLIENT_ID is not set in environment variables")
        if not cls.CLIENT_SECRET:
            raise ValueError("SCHWAB_CLIENT_SECRET is not set in environment variables")
        if not cls.REDIRECT_URI:
            raise ValueError("SCHWAB_REDIRECT_URI is not set in environment variables")

