"""Order placer for SPXW 10-wide credit spreads."""
import json
import requests
import re
import time
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
        # Format strikes (pass raw strike values, _format_option_symbol will multiply by 1000)
        option_type_char = 'P' if option_type == 'PUT' else 'C'
        
        # Format option symbols (pass raw strikes, e.g., 6875, not 6875000)
        short_symbol = self.quotes_mgr._format_option_symbol(
            'SPXW', date, option_type_char, k_short
        )
        long_symbol = self.quotes_mgr._format_option_symbol(
            'SPXW', date, option_type_char, k_long
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
            
            # Log response details for debugging
            logger.debug(f"Response status code: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            logger.debug(f"Response text length: {len(response.text) if response.text else 0}")
            
            response.raise_for_status()
            
            # Handle 201 Created or empty response body (Schwab API returns 201 Created with empty body)
            # Order ID is in the Location header
            if response.status_code == 201 or response.status_code == 204 or not response.text or response.text.strip() == '':
                logger.info(f"Order placement returned {response.status_code} with empty response body")
                logger.info("This is normal - order ID is in the Location header")
                
                # Extract order ID from Location header
                location_header = response.headers.get('Location', '')
                order_id = None
                
                if location_header:
                    # Extract order ID from Location URL
                    # Format: https://api.schwabapi.com/trader/v1/accounts/{hash}/orders/{orderId}
                    order_id_match = re.search(r'/orders/(\d+)$', location_header)
                    if order_id_match:
                        order_id = order_id_match.group(1)
                        logger.info(f"✅ Extracted Order ID from Location header: {order_id}")
                    else:
                        logger.warning(f"Could not extract order ID from Location header: {location_header}")
                
                # Wait a moment for order to be processed in the system
                logger.info("Waiting for order to be processed...")
                time.sleep(2)
                
                # Get order confirmation from recent orders
                try:
                    recent_orders = self.account_mgr.get_orders_executed_today(
                        account_number=account_number,
                        max_results=10
                    )
                    
                    if recent_orders:
                        # If we have order_id from Location header, find that specific order
                        # Otherwise, use the most recent order
                        order_details = None
                        if order_id:
                            for order in recent_orders:
                                if str(order.get('orderId', '')) == str(order_id):
                                    order_details = order
                                    break
                        
                        # If not found by ID or no ID, use most recent
                        if not order_details:
                            order_details = recent_orders[0]
                            if order_id:
                                logger.warning(f"Order ID {order_id} not found in recent orders, using most recent order")
                            else:
                                logger.info("Using most recent order (no order ID from Location header)")
                        
                        confirmed_order_id = order_details.get('orderId', order_id or 'PENDING')
                        order_status = order_details.get('status', 'ACCEPTED')
                        entered_time = order_details.get('enteredTime', 'N/A')
                        
                        logger.info(f"✅ Order confirmed from recent orders:")
                        logger.info(f"  Order ID: {confirmed_order_id}")
                        logger.info(f"  Status: {order_status}")
                        logger.info(f"  Entered Time: {entered_time}")
                        
                        return {
                            'orderId': confirmed_order_id,
                            'status': order_status,
                            'order_details': order_details
                        }
                    else:
                        logger.warning("Could not find order in recent orders list")
                        if order_id:
                            # We have order ID from Location header, return it
                            logger.info(f"Returning order ID from Location header: {order_id}")
                            return {
                                'orderId': order_id,
                                'status': 'ACCEPTED',
                                'order_details': {'orderId': order_id, 'status': 'ACCEPTED', 'message': 'Order placed, details pending'}
                            }
                except Exception as verify_error:
                    logger.warning(f"Could not verify order from recent orders: {verify_error}")
                    if order_id:
                        # We have order ID from Location header, return it
                        logger.info(f"Returning order ID from Location header: {order_id}")
                        return {
                            'orderId': order_id,
                            'status': 'ACCEPTED',
                            'order_details': {'orderId': order_id, 'status': 'ACCEPTED', 'message': 'Order placed, verification failed'}
                        }
                
                # Fallback: return response indicating success but no order details
                logger.warning("⚠️  Order placed but could not get confirmation")
                return {
                    'orderId': order_id or 'PENDING',
                    'status': 'ACCEPTED',
                    'order_details': {'message': 'Order accepted, empty response from API', 'orderId': order_id or 'PENDING'}
                }
            
            # Parse JSON response (for APIs that return JSON in body)
            try:
                order_response = response.json()
            except ValueError as json_error:
                logger.error(f"Failed to parse JSON response: {json_error}")
                logger.error(f"Response status: {response.status_code}")
                logger.error(f"Response text: {response.text[:500] if response.text else '(empty)'}")
                raise ValueError(f"Invalid JSON response from API: {json_error}")
            
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
            logger.error(f"Status code: {response.status_code}")
            if response.text:
                logger.error(f"Response body: {response.text[:1000]}")  # First 1000 chars
            else:
                logger.error("Response body is empty")
            raise
        except ValueError as e:
            # JSON parsing error
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Response status: {response.status_code}")
            logger.error(f"Response text: {response.text[:1000] if response.text else '(empty)'}")
            raise
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

