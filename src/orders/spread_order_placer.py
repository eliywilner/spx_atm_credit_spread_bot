"""Order placer for SPXW 10-wide credit spreads."""
import json
import requests
from datetime import datetime
from typing import Optional, Dict
from src.client.schwab_client import SchwabClient
from src.accounts.account_manager import AccountManager
from src.quotes.quotes_manager import QuotesManager
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SpreadOrderPlacer:
    """Places 10-wide credit spread orders for SPXW."""
    
    SPREAD_WIDTH = 10.0  # Always 10 points wide
    
    def __init__(self):
        """Initialize order placer."""
        self.client = SchwabClient()
        self.account_mgr = AccountManager()
        self.quotes_mgr = QuotesManager(default_symbol='SPXW')
    
    def place_10wide_credit_spread(
        self,
        date: str,  # YYMMDD format
        k_short: float,
        k_long: float,
        option_type: str,  # 'PUT' or 'CALL'
        quantity: int,
        order_price: float,
        account_number: Optional[str] = None
    ) -> Dict:
        """
        Place a 10-wide credit spread order.
        
        Args:
            date: Expiration date (YYMMDD format)
            k_short: Short strike
            k_long: Long strike
            option_type: 'PUT' or 'CALL'
            quantity: Number of spreads
            order_price: Order price (credit to receive)
            account_number: Account number (optional)
        
        Returns:
            Order response dictionary
        """
        # Format strikes (multiply by 1000 for SPXW)
        short_strike_int = int(k_short * 1000)
        long_strike_int = int(k_long * 1000)
        
        option_type_char = 'P' if option_type == 'PUT' else 'C'
        
        # Format option symbols
        short_symbol = self.quotes_mgr._format_option_symbol(
            'SPXW', date, option_type_char, short_strike_int
        )
        long_symbol = self.quotes_mgr._format_option_symbol(
            'SPXW', date, option_type_char, long_strike_int
        )
        
        logger.info(f"Placing {option_type} credit spread:")
        logger.info(f"  Short leg: {short_symbol} (SELL_TO_OPEN)")
        logger.info(f"  Long leg: {long_symbol} (BUY_TO_OPEN)")
        logger.info(f"  Quantity: {quantity}")
        logger.info(f"  Order Price: ${order_price:.2f}")
        
        # Get account hash
        account_hash = self.account_mgr.get_account_hash(account_number)
        
        # Build order JSON
        order = {
            "orderType": "NET_CREDIT",
            "session": "NORMAL",
            "price": f"{order_price:.2f}",
            "duration": "DAY",
            "orderStrategyType": "SINGLE",
            "orderLegCollection": [
                {
                    "instruction": "BUY_TO_OPEN",
                    "quantity": quantity,
                    "instrument": {
                        "symbol": long_symbol,
                        "assetType": "OPTION"
                    }
                },
                {
                    "instruction": "SELL_TO_OPEN",
                    "quantity": quantity,
                    "instrument": {
                        "symbol": short_symbol,
                        "assetType": "OPTION"
                    }
                }
            ]
        }
        
        # HARD SAFETY GATE: Check DRY_RUN and ENABLE_LIVE_TRADING
        if Config.DRY_RUN or not Config.ENABLE_LIVE_TRADING:
            # DRY RUN MODE: Log order payload, do NOT place order
            logger.warning("=" * 70)
            logger.warning("🚫 DRY RUN MODE - ORDER WILL NOT BE PLACED")
            logger.warning("=" * 70)
            logger.warning(f"DRY_RUN = {Config.DRY_RUN}")
            logger.warning(f"ENABLE_LIVE_TRADING = {Config.ENABLE_LIVE_TRADING}")
            logger.warning("")
            logger.warning("ORDER PAYLOAD THAT WOULD BE SENT:")
            logger.warning(json.dumps(order, indent=2))
            logger.warning("")
            logger.warning("Order details:")
            logger.warning(f"  Date: {date}")
            logger.warning(f"  Option Type: {option_type}")
            logger.warning(f"  K_short: ${k_short:.2f}")
            logger.warning(f"  K_long: ${k_long:.2f}")
            logger.warning(f"  Quantity: {quantity}")
            logger.warning(f"  Order Price: ${order_price:.2f}")
            logger.warning(f"  Short Symbol: {short_symbol}")
            logger.warning(f"  Long Symbol: {long_symbol}")
            logger.warning("=" * 70)
            
            # Return mock response for dry-run
            return {
                'orderId': 'DRY_RUN_MOCK_ORDER_ID',
                'status': 'DRY_RUN',
                'order_details': order,
                'dry_run': True
            }
        
        # LIVE TRADING: Both gates passed, place actual order
        logger.info("=" * 70)
        logger.info("✅ LIVE TRADING ENABLED - PLACING REAL ORDER")
        logger.info("=" * 70)
        logger.info(f"DRY_RUN = {Config.DRY_RUN}")
        logger.info(f"ENABLE_LIVE_TRADING = {Config.ENABLE_LIVE_TRADING}")
        logger.info("")
        
        # Place order via API
        url = f"{self.client.base_url}/accounts/{account_hash}/orders"
        headers = self.client.auth.get_headers()
        headers['Content-Type'] = 'application/json'
        
        try:
            response = requests.post(url, json=order, headers=headers, timeout=10)
            
            if response.status_code == 401:
                logger.info("Token expired, refreshing...")
                self.client.auth.refresh_access_token()
                headers = self.client.auth.get_headers()
                headers['Content-Type'] = 'application/json'
                response = requests.post(url, json=order, headers=headers, timeout=10)
            
            response.raise_for_status()
            order_response = response.json()
            
            order_id = order_response.get('orderId', '')
            order_status = order_response.get('status', '')
            
            logger.info(f"✅ Order placed successfully:")
            logger.info(f"  Order ID: {order_id}")
            logger.info(f"  Status: {order_status}")
            
            return {
                'orderId': order_id,
                'status': order_status,
                'order_details': order_response
            }
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error placing order: {e}")
            if response.text:
                logger.error(f"Response: {response.text}")
            raise
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            raise

