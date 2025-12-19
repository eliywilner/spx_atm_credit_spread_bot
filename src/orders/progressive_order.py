"""Progressive order placement with automatic adjustments for better fill probability."""
import time
import logging
from datetime import datetime, time as dt_time
from typing import Optional, Dict
import pytz
from src.orders.order_manager import OrderManager
from src.quotes.quotes_manager import QuotesManager
from src.accounts.account_manager import AccountManager
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ET = pytz.timezone('US/Eastern')
MARKET_CLOSE = dt_time(16, 0)  # 4:00 PM ET


def place_order_with_progressive_adjustments(
    order_mgr: OrderManager,
    date: str,
    symbol: str,
    bias: str,
    short_strike: float,
    quantity: int,
    initial_quote: Dict,
    account_number: Optional[str] = None,
    opening_range_data: Optional[Dict] = None,
    breakout_data: Optional[Dict] = None,
        min_credit: float = 1.50,
        max_wait_seconds: float = 150.0,  # 2.5 minutes for Phase 1
        phase_2_check_interval: int = 300  # 5 minutes for Phase 2 periodic monitoring
) -> Optional[Dict]:
    """
    Place order with progressive adjustments to improve fill probability.
    
    Strategy:
    1. Start with MID price - $0.05 (5 cent buffer) as long as >= $1.50 minimum
    2. All prices rounded to 5 cent increments (e.g., $1.47 -> $1.45, $1.52 -> $1.50)
    3. Phase 1: Check order status every 10 seconds (aggressive monitoring for 2.5 minutes)
    4. Phase 2: Check order status every 5 minutes (periodic monitoring until market close)
    5. Before each adjustment, get fresh quote to check current MID price
    6. If not filled, increase buffer by 5 cents (MID - $0.10, then $0.15, etc.) as long as >= $1.50
    7. Continue until filled or market closes
    8. Once order is FILLED, immediately stop checking and return
    
    IMPORTANT: We use MID price with 5 cent increment buffers, all prices rounded to 5 cent increments,
    ensuring price is always >= $1.50 minimum.
    
    Args:
        order_mgr: OrderManager instance
        date: Expiration date in YYMMDD format
        symbol: Trading symbol (SPXW or XSP)
        bias: 'bearish' or 'bullish'
        short_strike: Short strike price
        quantity: Number of contracts
        initial_quote: Initial quote dict with spread_info
        account_number: Optional account number
        opening_range_data: Optional opening range data
        breakout_data: Optional breakout data
        min_credit: Minimum credit required (default: $1.50)
        max_wait_seconds: Maximum time to wait for fill (default: 150 seconds = 2.5 min)
    
    Returns:
        dict: Order response if filled, None if not filled within time limit
    """
    logger.info("=" * 70)
    logger.info("PROGRESSIVE ORDER PLACEMENT WITH ADJUSTMENTS")
    logger.info("=" * 70)
    logger.info(f"Minimum credit: ${min_credit:.2f}")
    logger.info(f"Maximum wait time: {max_wait_seconds:.0f} seconds ({max_wait_seconds/60:.1f} minutes)")
    logger.info("")
    
    # Extract initial quote data
    # net_credit = bid (minimum credit we can receive)
    # net_mid = mid price (target)
    # net_debit = ask (maximum we'd pay to close)
    spread_info = initial_quote.get('spread_info', {})
    initial_mid = spread_info.get('net_mid', 0)
    initial_bid = spread_info.get('net_credit', 0)  # This is the bid (minimum credit we can get)
    
    # Define buffer constants early to ensure they're always available
    BUFFER_INCREMENT = 0.05  # 5 cent increments
    initial_buffer = BUFFER_INCREMENT  # Start with 5 cent buffer
    
    # Verify initial quote meets minimum (use MID price, not bid)
    # We use MID price with a 5 cent buffer (in 5 cent increments)
    if initial_mid < min_credit:
        logger.error(f"❌ Initial quote mid (${initial_mid:.2f}) is below minimum ${min_credit:.2f}")
        logger.error("   Cancelling order placement - market conditions not favorable")
        # Return None to indicate we should not place order
        return None
    
    # Use MID price with 5 cent buffer (in 5 cent increments), but ensure >= $1.50
    # Start with MID - $0.05 (5 cent buffer) as long as it's >= min_credit
    
    # Calculate initial limit: MID - 5 cents, but ensure >= $1.50
    # Round to 5 cent increments to ensure clean pricing
    initial_limit_raw = max(min_credit, initial_mid - initial_buffer)
    # Round to nearest 5 cent increment (e.g., 1.47 -> 1.45, 1.52 -> 1.50)
    initial_limit = round(initial_limit_raw / BUFFER_INCREMENT) * BUFFER_INCREMENT
    # Ensure we don't go below minimum after rounding
    initial_limit = max(min_credit, initial_limit)
    
    logger.info(f"Initial Quote:")
    logger.info(f"   Mid: ${initial_mid:.2f}")
    logger.info(f"   Bid: ${initial_bid:.2f} (for reference only)")
    logger.info(f"   Initial Limit: ${initial_limit:.2f} (MID - ${initial_buffer:.2f} buffer, rounded to 5 cent increment, ensuring >= ${min_credit:.2f})")
    logger.info("")
    
    # Determine spread parameters for quote updates
    quotes_mgr = QuotesManager(default_symbol=symbol)
    if symbol.upper() == 'SPXW':
        width = 5
        underlying_symbol = 'SPXW'
    else:  # XSP
        width = 1
        underlying_symbol = '$XSP'
    
    # Round strike
    if symbol.upper() == 'SPXW':
        rounded_strike = quotes_mgr._round_strike_to_interval(short_strike, 'SPXW')
    else:
        rounded_strike = quotes_mgr._round_strike_to_interval(short_strike, '$XSP')
    
    # Place initial order
    current_limit = initial_limit
    order_id = None
    account_mgr = AccountManager()
    account_hash = account_mgr.get_account_hash(account_number)
    
    start_time = time.time()
    adjustment_count = 0
    check_interval = 10  # Check every 10 seconds (Phase 1: aggressive monitoring)
    adjustment_step = 0.05  # Lower limit by $0.05 each adjustment (5 cent increments)
    current_buffer = initial_buffer  # Track current buffer amount
    
    logger.info(f"Placing initial order at ${current_limit:.2f}...")
    logger.info(f"Quantity being passed to order manager: {quantity} contracts")
    
    try:
        # Place initial order
        order_response = order_mgr.place_credit_spread_order(
            date=date,
            symbol=symbol,
            bias=bias,
            short_strike=short_strike,
            quantity=quantity,
            account_number=account_number,
            opening_range_data=opening_range_data,
            breakout_data=breakout_data,
            order_price=current_limit
        )
        
        if 'order_details' in order_response:
            order_id = order_response['order_details'].get('orderId')
            logger.info(f"✅ Initial order placed: Order ID {order_id}")
            logger.info(f"   Limit Price: ${current_limit:.2f}")
            logger.info("")
        else:
            logger.error("❌ Failed to get order ID from response")
            return None
        
    except Exception as e:
        logger.error(f"❌ Failed to place initial order: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None
    
    # Phase 1: Aggressive monitoring (first max_wait_seconds)
    # Phase 2: Periodic monitoring (after max_wait_seconds until market close)
    phase_1_complete = False
    
    # Monitor order and adjust if needed
    while True:
        elapsed = time.time() - start_time
        
        # Check if Phase 1 is complete (aggressive monitoring period)
        if not phase_1_complete and elapsed >= max_wait_seconds:
            phase_1_complete = True
            logger.info("")
            logger.info("=" * 70)
            logger.info("PHASE 1 COMPLETE - SWITCHING TO PERIODIC MONITORING")
            logger.info("=" * 70)
            logger.info(f"Order {order_id} was not filled after {max_wait_seconds:.0f}s aggressive monitoring")
            logger.info(f"Current limit: ${current_limit:.2f}")
            logger.info("")
            logger.info("Switching to Phase 2: Periodic monitoring (every 5 minutes)")
            logger.info("  - Will check order status periodically")
            logger.info("  - Will monitor quotes for better prices")
            logger.info("  - Will cancel and replace if better price available (at least $0.05 better)")
            logger.info("  - Will continue until market close or order filled")
            logger.info("")
            logger.info("Note: Phase 1 used 10-second checks for aggressive monitoring")
            logger.info("")
            
            # Switch to Phase 2 check interval
            check_interval = phase_2_check_interval  # 5 minutes for Phase 2
            
            # Check if market is already closed
            now_et = datetime.now(ET)
            if now_et.time() >= MARKET_CLOSE:
                logger.info("Market is already closed. Returning order status.")
                return order_response
        
        # Wait for check interval (10 seconds in Phase 1, 5 minutes in Phase 2)
        if elapsed < check_interval:
            wait_time = check_interval - elapsed
            logger.info(f"Waiting {wait_time:.0f} seconds before checking order status...")
            time.sleep(wait_time)
            elapsed = time.time() - start_time
        
        # Check order status
        logger.info("")
        logger.info(f"Check #{int(elapsed/check_interval) + 1} (Elapsed: {int(elapsed)}s)")
        logger.info("=" * 70)
        
        try:
            # Get current order status
            recent_orders = account_mgr.get_orders_executed_today(
                account_number=account_number,
                max_results=10
            )
            
            current_order = None
            for order in recent_orders:
                if order.get('orderId') == order_id:
                    current_order = order
                    break
            
            if not current_order:
                logger.warning(f"⚠️  Could not find order {order_id} in recent orders")
                logger.warning("   Order may have been filled or cancelled")
                # Try to get order by ID (if API supports it)
                # For now, assume it was filled
                return order_response
            
            order_status = current_order.get('status', 'UNKNOWN')
            logger.info(f"Order Status: {order_status}")
            
            # Check if order is filled
            if order_status in ['FILLED', 'EXECUTED']:
                logger.info("")
                logger.info("✅ ORDER FILLED!")
                logger.info(f"   Order ID: {order_id}")
                logger.info(f"   Fill Price: ${current_limit:.2f}")
                logger.info(f"   Time to Fill: {int(elapsed)} seconds")
                logger.info("")
                order_response['order_details'] = current_order
                return order_response
            
            # Order is still working - check if we should adjust
            logger.info(f"   Order still {order_status} - checking if adjustment needed...")
            
            # Get fresh quote before adjusting
            logger.info("   Getting fresh quote to check current market conditions...")
            fresh_quote = quotes_mgr.get_credit_spread_quote_by_bias(
                symbol=underlying_symbol,
                bias=bias,
                short_strike=rounded_strike,
                width=width,
                expiration_date=date
            )
            
            fresh_spread_info = fresh_quote.get('spread_info', {})
            fresh_mid = fresh_spread_info.get('net_mid', 0)
            fresh_bid = fresh_spread_info.get('net_credit', 0)  # Bid = minimum credit we can get
            
            logger.info(f"   Fresh Quote - Mid: ${fresh_mid:.2f}, Bid: ${fresh_bid:.2f}")
            logger.info(f"   Current Order Limit: ${current_limit:.2f}")
            
            # Safety check: If fresh quote mid is below minimum, cancel order
            # We ALWAYS use mid price for orders
            if fresh_mid < min_credit:
                logger.error(f"❌ Fresh quote mid (${fresh_mid:.2f}) is below minimum ${min_credit:.2f}")
                logger.error("   Cancelling order - market moved against us")
                
                # Cancel order
                try:
                    cancel_endpoint = f'/accounts/{account_hash}/orders/{order_id}'
                    order_mgr.client._make_request('DELETE', cancel_endpoint)
                    logger.info(f"✅ Order {order_id} cancelled")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to cancel order: {e}")
                
                return None
            
            # Phase 2 logic: Check if we can get a better price (using MID with buffer)
            if phase_1_complete:
                # In Phase 2, we're looking for better prices (market came back)
                # Only cancel and replace if we can get significantly better price
                # Use fresh MID price with current buffer (in 5 cent increments)
                better_price_threshold = 0.05  # Need at least $0.05 better to justify cancel/replace
                # Calculate potential limit: MID - current buffer, rounded to 5 cent increments
                potential_better_limit_raw = max(min_credit, fresh_mid - current_buffer)
                potential_better_limit = round(potential_better_limit_raw / adjustment_step) * adjustment_step
                potential_better_limit = max(min_credit, potential_better_limit)  # Ensure >= minimum
                
                # Check if market is closed
                now_et = datetime.now(ET)
                if now_et.time() >= MARKET_CLOSE:
                    logger.info("Market is closed. Returning final order status.")
                    return order_response
                
                if potential_better_limit > current_limit + better_price_threshold:
                    logger.info("")
                    logger.info(f"💰 BETTER PRICE AVAILABLE IN PHASE 2!")
                    logger.info(f"   Current limit: ${current_limit:.2f}")
                    logger.info(f"   Potential better limit: ${potential_better_limit:.2f}")
                    logger.info(f"   Improvement: ${potential_better_limit - current_limit:.2f}")
                    logger.info("   Cancelling old order and placing at better price...")
                    logger.info("")
                    
                    # Cancel current order
                    try:
                        cancel_endpoint = f'/accounts/{account_hash}/orders/{order_id}'
                        order_mgr.client._make_request('DELETE', cancel_endpoint)
                        logger.info(f"✅ Cancelled order {order_id}")
                        time.sleep(1)
                    except Exception as e:
                        logger.warning(f"⚠️  Failed to cancel order: {e}")
                        logger.warning("   Will continue with existing order...")
                        time.sleep(check_interval)
                        continue
                    
                    # Place new order at better price
                    current_limit = potential_better_limit
                    try:
                        new_order_response = order_mgr.place_credit_spread_order(
                            date=date,
                            symbol=symbol,
                            bias=bias,
                            short_strike=short_strike,
                            quantity=quantity,
                            account_number=account_number,
                            opening_range_data=opening_range_data,
                            breakout_data=breakout_data,
                            order_price=current_limit
                        )
                        
                        if 'order_details' in new_order_response:
                            order_id = new_order_response['order_details'].get('orderId')
                            order_response = new_order_response
                            logger.info(f"✅ New order placed at better price: Order ID {order_id}")
                            logger.info(f"   New Limit Price: ${current_limit:.2f}")
                        else:
                            logger.error("❌ Failed to get order ID from new order response")
                            return order_response
                    except Exception as e:
                        logger.error(f"❌ Failed to place new order at better price: {e}")
                        return order_response
                    
                    # Continue monitoring the new order
                    time.sleep(check_interval)
                    continue
                else:
                    # No better price available, just wait
                    logger.info(f"   No better price available (current limit: ${current_limit:.2f}, potential: ${potential_better_limit:.2f})")
                    logger.info(f"   Keeping order at current limit: ${current_limit:.2f}")
                    logger.info(f"   Waiting {check_interval} seconds before next check...")
                    time.sleep(check_interval)
                    continue
            
            # Phase 1 logic: Adjust using 5 cent increments based on fresh MID price
            # Use fresh MID price with increasing buffer (in 5 cent increments)
            adjustment_count += 1
            
            # Increase buffer by 5 cents for this adjustment
            current_buffer += adjustment_step
            
            # Calculate next limit: MID - buffer, but ensure >= $1.50
            # Round to 5 cent increments to ensure clean pricing
            next_limit_raw = max(min_credit, fresh_mid - current_buffer)
            next_limit = round(next_limit_raw / adjustment_step) * adjustment_step
            # Ensure we don't go below minimum after rounding
            next_limit = max(min_credit, next_limit)
            
            logger.info(f"   Fresh MID price: ${fresh_mid:.2f}")
            logger.info(f"   Current buffer: ${current_buffer:.2f} (in 5 cent increments)")
            logger.info(f"   Next limit: ${next_limit:.2f} (MID - ${current_buffer:.2f}, rounded to 5 cent increment, ensuring >= ${min_credit:.2f})")
            
            # Check if we should adjust (only if we can go lower and still be >= minimum)
            if next_limit < current_limit and next_limit >= min_credit:
                logger.info("")
                logger.info(f"🔄 ADJUSTING ORDER (Adjustment #{adjustment_count})")
                logger.info(f"   Current Limit: ${current_limit:.2f}")
                logger.info(f"   New Limit: ${next_limit:.2f} (MID ${fresh_mid:.2f} - ${current_buffer:.2f} buffer)")
                logger.info(f"   Reason: Not filled, adjusting with 5 cent increment buffer")
                logger.info("")
                
                # Cancel current order
                try:
                    cancel_endpoint = f'/accounts/{account_hash}/orders/{order_id}'
                    order_mgr.client._make_request('DELETE', cancel_endpoint)
                    logger.info(f"✅ Cancelled order {order_id}")
                    time.sleep(1)  # Brief pause before placing new order
                except Exception as e:
                    logger.warning(f"⚠️  Failed to cancel order: {e}")
                    logger.warning("   Will attempt to place new order anyway...")
                
                # Place new order with adjusted limit
                current_limit = next_limit
                # Note: current_buffer is already updated above
                try:
                    new_order_response = order_mgr.place_credit_spread_order(
                        date=date,
                        symbol=symbol,
                        bias=bias,
                        short_strike=short_strike,
                        quantity=quantity,
                        account_number=account_number,
                        opening_range_data=opening_range_data,
                        breakout_data=breakout_data,
                        order_price=current_limit
                    )
                    
                    if 'order_details' in new_order_response:
                        order_id = new_order_response['order_details'].get('orderId')
                        order_response = new_order_response
                        logger.info(f"✅ New order placed: Order ID {order_id}")
                        logger.info(f"   New Limit Price: ${current_limit:.2f}")
                    else:
                        logger.error("❌ Failed to get order ID from new order response")
                        return order_response  # Return previous order response
                        
                except Exception as e:
                    logger.error(f"❌ Failed to place adjusted order: {e}")
                    logger.error("   Returning previous order response")
                    return order_response
            else:
                # Can't adjust further - either at minimum or buffer would put us below minimum
                if next_limit < min_credit:
                    logger.info(f"   Next limit (${next_limit:.2f}) would be below minimum (${min_credit:.2f})")
                    logger.info(f"   Cannot adjust further - maintaining current limit (${current_limit:.2f})")
                elif next_limit >= current_limit:
                    logger.info(f"   Next limit (${next_limit:.2f}) is not lower than current (${current_limit:.2f})")
                    logger.info(f"   Cannot adjust further - maintaining current limit (${current_limit:.2f})")
                
                logger.info(f"   Waiting {check_interval} seconds before next check...")
                time.sleep(check_interval)
        
        except Exception as e:
            logger.error(f"❌ Error checking order status: {e}")
            import traceback
            logger.error(traceback.format_exc())
            logger.info(f"   Will retry in {check_interval} seconds...")
            time.sleep(check_interval)
    
    # Should never reach here, but return order response if we do
    return order_response

