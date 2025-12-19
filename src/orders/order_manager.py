"""Order Manager - Places credit spread orders."""
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Union
from src.client.schwab_client import SchwabClient
from src.accounts.account_manager import AccountManager
from src.quotes.quotes_manager import QuotesManager
from src.strategy.contract_scaling import ContractScaler
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class OrderManager:
    """
    Manages order placement for credit spreads.
    Works with both SPXW and XSP.
    """
    
    def __init__(self):
        """Initialize the order manager."""
        self.client = SchwabClient()
        self.account_mgr = AccountManager()
        self.quotes_mgr = QuotesManager()
        self.contract_scaler = ContractScaler()
        
        # Create reports directory if it doesn't exist
        self.reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'reports')
        os.makedirs(self.reports_dir, exist_ok=True)
        
        logger.info("OrderManager initialized")
    
    def place_credit_spread_order(
        self,
        date: str,
        symbol: str,
        bias: str,
        short_strike: Union[int, float],
        quantity: int = 1,
        account_number: Optional[str] = None,
        opening_range_data: Optional[Dict] = None,
        breakout_data: Optional[Dict] = None,
        order_price: Optional[float] = None
    ) -> Dict:
        """
        Place a credit spread order based on strategy parameters.
        
        This method is designed to work with the OpeningRangeTracker strategy:
        - After the opening range (9:30-10:00 AM) is determined, the strategy finds
          the first 30-minute candle that closes outside the opening range.
        - The bias is determined by the breakout direction:
          * 'bearish' = breakout closed BELOW opening range → Call Credit Spread (bearish strategy)
          * 'bullish' = breakout closed ABOVE opening range → Put Credit Spread (bullish strategy)
        - The short_strike is the midpoint of the opening range (rounded appropriately)
        
        Args:
            date: Expiration date in YYMMDD format (e.g., '251114' for Nov 14, 2025)
                  This should come from the strategy's breakout detection date.
            symbol: 'SPXW' or 'XSP' - must match the symbol used in OpeningRangeTracker
            bias: 'bullish' or 'bearish' - determined by breakout direction:
                  - 'bearish' if breakout candle closed BELOW opening range (call credit spread)
                  - 'bullish' if breakout candle closed ABOVE opening range (put credit spread)
            short_strike: Strike price for the short leg - should be the midpoint of opening range
                          (already rounded: nearest $5 for SPXW, nearest $1 for XSP)
            quantity: Number of contracts. If None, will be calculated automatically based on
                      current account capital using contract scaling logic.
            account_number: Account number to place order in. If None, uses first account.
            opening_range_data: Optional dict with 'high', 'low', 'midpoint' from opening range
            breakout_data: Optional dict with 'close_price', 'direction' from breakout candle
        
        Returns:
            dict: Order response from Schwab API with order_details if available
        
        Strategy Integration:
            This method expects parameters from OpeningRangeTracker.find_first_breakout_candle():
            >>> from src.strategy.opening_range import OpeningRangeTracker
            >>> from src.orders.order_manager import OrderManager
            >>> 
            >>> tracker = OpeningRangeTracker(symbol='XSP')
            >>> breakout = tracker.find_first_breakout_candle(date=datetime.now())
            >>> 
            >>> if breakout['found']:
            >>>     # Determine bias from direction
            >>>     # BELOW opening range = bearish = Call Credit Spread
            >>>     # ABOVE opening range = bullish = Put Credit Spread
            >>>     bias = 'bearish' if breakout['direction'] == 'below' else 'bullish'
            >>>     # Get midpoint as short strike
            >>>     short_strike = breakout['midpoint']
            >>>     # Get date (convert to YYMMDD format)
            >>>     date = breakout['date'].strftime('%y%m%d')
            >>>     
            >>>     order_mgr = OrderManager()
            >>>     order = order_mgr.place_credit_spread_order(
            >>>         date=date,
            >>>         symbol='XSP',
            >>>         bias=bias,
            >>>         short_strike=short_strike,
            >>>         quantity=1
            >>>     )
        
        Example:
            >>> # Place a bullish put credit spread for XSP
            >>> order = mgr.place_credit_spread_order('251114', 'XSP', 'bullish', 675, quantity=2)
        """
        # Validate inputs
        symbol_upper = symbol.upper()
        if symbol_upper not in ['SPXW', 'XSP']:
            raise ValueError(f"symbol must be 'SPXW' or 'XSP', got '{symbol}'")
        
        bias_lower = bias.lower()
        if bias_lower not in ['bullish', 'bearish', 'bull', 'bear']:
            raise ValueError(f"bias must be 'bullish' or 'bearish', got '{bias}'")
        
        # Normalize bias (handle 'bull'/'bear' variants)
        if bias_lower in ['bull', 'bullish']:
            bias_normalized = 'bullish'
        else:
            bias_normalized = 'bearish'
        
        # Determine spread width and underlying symbol based on strategy symbol
        # Strategy provides: SPXW or XSP
        # For quotes: SPXW uses 'SPXW', XSP uses '$XSP'
        if symbol_upper == 'SPXW':
            width = 5  # SPXW spreads are 5 points wide
            underlying_symbol = 'SPXW'
        else:  # XSP
            width = 1  # XSP spreads are 1 point wide
            underlying_symbol = '$XSP'
        
        # Round strike to correct interval (as per strategy requirements)
        # SPXW: nearest $5, XSP: nearest $1
        # Note: The strategy's calculate_midpoint() already rounds, but we round again
        # here to ensure consistency in case the value wasn't pre-rounded
        if symbol_upper == 'SPXW':
            rounded_strike = self.quotes_mgr._round_strike_to_interval(short_strike, 'SPXW')
        else:  # XSP
            rounded_strike = self.quotes_mgr._round_strike_to_interval(short_strike, '$XSP')
        
        # Calculate quantity using contract scaling if not provided
        # Only recalculate if quantity is None (not provided)
        # If quantity is explicitly provided (even if it's 1), use it as-is
        if quantity is None:
            try:
                # Get current account option buying power for contract scaling
                option_buying_power = self.account_mgr.get_option_buying_power(account_number)
                calculated_quantity = self.contract_scaler.calculate_contracts(option_buying_power)
                quantity = calculated_quantity
                logger.info(f"Contract scaling: Calculated {quantity} contracts based on option buying power ${option_buying_power:,.2f}")
            except Exception as e:
                logger.warning(f"Failed to calculate contracts using scaling: {e}. Using default quantity of 1 contract")
                quantity = 1
        else:
            # Quantity was explicitly provided, log scaling info for reference
            try:
                option_buying_power = self.account_mgr.get_option_buying_power(account_number)
                scaling_info = self.contract_scaler.get_scaling_info(option_buying_power)
                recommended = scaling_info.get('contracts', quantity)
                logger.info(f"Contract scaling info: Option Buying Power=${option_buying_power:,.2f}, Recommended={recommended}, Using={quantity} (explicitly provided)")
                if recommended != quantity:
                    logger.warning(f"⚠️  Quantity mismatch: Recommended {recommended} contracts but using {quantity} contracts")
            except Exception as e:
                logger.debug(f"Could not get scaling info: {e}")
        
        # Log strategy parameters being used
        logger.info(f"Placing credit spread order based on strategy parameters:")
        logger.info(f"  Symbol: {symbol_upper} (from strategy)")
        logger.info(f"  Date: {date} (from strategy breakout detection)")
        logger.info(f"  Bias: {bias_normalized} (from breakout direction)")
        logger.info(f"  Short Strike: ${rounded_strike} (midpoint from opening range, rounded from ${short_strike})")
        logger.info(f"  Spread Width: ${width} ({symbol_upper} default)")
        logger.info(f"  Quantity: {quantity} contracts (FINAL - will be used in order)")
        
        # Get quote for the credit spread
        logger.info(f"Getting quote for {symbol_upper} credit spread:")
        logger.info(f"  Date: {date}, Bias: {bias_normalized}, Short Strike: ${rounded_strike}")
        
        # Get quote using strategy parameters
        # bias_normalized determines spread type:
        # - 'bearish' → Call Credit Spread (sell call at short_strike, buy call at short_strike + width)
        # - 'bullish' → Put Credit Spread (sell put at short_strike, buy put at short_strike - width)
        spread_quote = self.quotes_mgr.get_credit_spread_quote_by_bias(
            symbol=underlying_symbol,
            bias=bias_normalized,
            short_strike=rounded_strike,
            width=width,
            expiration_date=date
        )
        
        spread_info = spread_quote.get('spread_info', {})
        net_mid = spread_info.get('net_mid', 0)
        short_strike_actual = spread_info.get('short_strike')
        long_strike_actual = spread_info.get('long_strike')
        spread_type = spread_info.get('spread_type', '')
        
        # Capture underlying SPX price at order placement time
        underlying_price_at_fill = None
        try:
            # Get SPX price (for SPXW) or XSP price (for XSP)
            underlying_symbol_for_quote = '$SPX' if symbol_upper == 'SPXW' else '$XSP'
            underlying_quote = self.quotes_mgr.get_quotes(underlying_symbol_for_quote, fields='quote')
            if underlying_quote and underlying_symbol_for_quote in underlying_quote:
                quote_data = underlying_quote[underlying_symbol_for_quote].get('quote', {})
                underlying_price_at_fill = quote_data.get('lastPrice') or quote_data.get('mark')
                logger.info(f"Underlying price at order placement: ${underlying_price_at_fill:.2f} ({underlying_symbol_for_quote})")
        except Exception as e:
            logger.warning(f"Could not get underlying price at order placement: {e}")
        
        # Use provided order_price if given, otherwise use net_mid from quote
        # This ensures we use the validated price (which may be higher than minimum)
        if order_price is not None:
            price_to_use = order_price
            logger.info(f"Using provided order price: ${price_to_use:.2f}")
        else:
            price_to_use = net_mid
            logger.info(f"Using quote mid price: ${price_to_use:.2f}")
        
        logger.info(f"Spread quote: Net Mid=${net_mid:.2f}")
        logger.info(f"  Short Strike: ${short_strike_actual}, Long Strike: ${long_strike_actual}")
        logger.info(f"  Order will be placed at: ${price_to_use:.2f}")
        
        # Get option symbols for both legs
        if 'PUT' in spread_type.upper():
            option_type = 'P'
        elif 'CALL' in spread_type.upper():
            option_type = 'C'
        else:
            raise ValueError(f"Could not determine option type from spread_type: {spread_type}")
        
        # Format option symbols
        short_symbol = self.quotes_mgr._format_option_symbol(
            underlying_symbol, date, option_type, short_strike_actual
        )
        long_symbol = self.quotes_mgr._format_option_symbol(
            underlying_symbol, date, option_type, long_strike_actual
        )
        
        logger.info(f"Short leg: {short_symbol}")
        logger.info(f"Long leg: {long_symbol}")
        
        # Get account hash
        account_hash = self.account_mgr.get_account_hash(account_number)
        logger.info(f"Placing order in account: {account_number or 'default'}")
        
        # Build order JSON
        # For credit spreads:
        # - SELL_TO_OPEN the short leg (the one we're selling for credit)
        # - BUY_TO_OPEN the long leg (the one we're buying for protection)
        # Note: Order matters - short leg should be second in the array for NET_CREDIT orders
        order = {
            "orderType": "NET_CREDIT",
            "session": "NORMAL",
            "price": f"{price_to_use:.2f}",  # Use validated price (actual mid, not minimum)
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
        
        logger.info(f"Order JSON structure:")
        logger.info(f"  Order Type: NET_CREDIT")
        logger.info(f"  Price: ${price_to_use:.2f}")
        logger.info(f"  Quantity: {quantity}")
        logger.info(f"  Long Leg: {long_symbol} (BUY_TO_OPEN)")
        logger.info(f"  Short Leg: {short_symbol} (SELL_TO_OPEN)")
        
        logger.info(f"Placing order: {order}")
        
        # Place the order
        # Note: The endpoint should be relative to the base URL (which includes /v1)
        endpoint = f'/accounts/{account_hash}/orders'
        
        try:
            response = self.client._make_request('POST', endpoint, json_data=order)
            logger.info("Order placed successfully")
            
            # Check order status by getting recent orders
            logger.info("Checking order status...")
            import time
            time.sleep(1)  # Wait a moment for order to be processed
            
            # Get orders executed today to find our order
            recent_orders = self.account_mgr.get_orders_executed_today(
                account_number=account_number,
                max_results=10
            )
            
            if recent_orders:
                # Find the most recent order (should be ours)
                latest_order = recent_orders[0]
                logger.info(f"Latest order found:")
                logger.info(f"  Order ID: {latest_order.get('orderId', 'N/A')}")
                logger.info(f"  Status: {latest_order.get('status', 'N/A')}")
                logger.info(f"  Entered Time: {latest_order.get('enteredTime', 'N/A')}")
                
                # Add order details to response
                response['order_details'] = latest_order
                
                # Add underlying price to response (captured at order placement time)
                if underlying_price_at_fill is not None:
                    response['underlying_price_at_fill'] = underlying_price_at_fill
                    response['underlying_symbol'] = 'SPX' if symbol_upper == 'SPXW' else 'XSP'
                
                # Generate report for the order
                self._generate_order_report(
                    order_details=latest_order,
                    symbol=symbol_upper,
                    bias=bias_normalized,
                    short_strike=short_strike_actual,
                    long_strike=long_strike_actual,
                    net_mid=net_mid,
                    date=date,
                    opening_range_data=opening_range_data,
                    breakout_data=breakout_data
                )
            else:
                logger.warning("Could not find order in recent orders list")
            
            return response
        except Exception as e:
            # If there's an error, try to get more details
            logger.error(f"Error placing order: {e}")
            # Try to get the raw response
            import requests
            url = f"{self.client.base_url}{endpoint}"
            headers = self.client.auth.get_headers()
            try:
                raw_response = requests.post(url, headers=headers, json=order)
                logger.error(f"Response status: {raw_response.status_code}")
                if raw_response.status_code in [200, 201, 204]:
                    logger.info("Order may have been placed successfully (check your account)")
                logger.error(f"Response text: {raw_response.text[:500]}")
            except:
                pass
            raise
    
    def _generate_order_report(
        self,
        order_details: Dict,
        symbol: str,
        bias: str,
        short_strike: Union[int, float],
        long_strike: Union[int, float],
        net_mid: float,
        date: str,
        opening_range_data: Optional[Dict] = None,
        breakout_data: Optional[Dict] = None
    ) -> str:
        """
        Generate a text report for a placed order.
        
        Args:
            order_details: Order details from API response
            symbol: Trading symbol (SPXW or XSP)
            bias: Trading bias (bullish or bearish)
            short_strike: Short leg strike price
            long_strike: Long leg strike price
            net_mid: Net mid price for the spread
            date: Expiration date (YYMMDD format)
            opening_range_data: Optional dict with 'high', 'low', 'midpoint' from opening range
            breakout_data: Optional dict with 'close_price', 'direction' from breakout candle
        
        Returns:
            str: Path to the generated report file
        """
        order_id = order_details.get('orderId', 'UNKNOWN')
        entered_time = order_details.get('enteredTime', '')
        status = order_details.get('status', 'UNKNOWN')
        
        # Parse date for filename (use expiration date, not order time)
        # Convert YYMMDD format to YYYY-MM-DD for readability
        try:
            # date is in YYMMDD format (e.g., '251114')
            year = 2000 + int(date[:2])
            month = int(date[2:4])
            day = int(date[4:6])
            date_formatted = f"{year:04d}-{month:02d}-{day:02d}"
        except:
            # Fallback to current date if parsing fails
            date_formatted = datetime.now().strftime('%Y-%m-%d')
        
        # Generate filename: SYMBOL_DATE_BIAS.txt
        # Example: XSP_2025-11-14_BEARISH.txt
        filename = f"{symbol}_{date_formatted}_{bias.upper()}.txt"
        filepath = os.path.join(self.reports_dir, filename)
        
        # Build report content
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("CREDIT SPREAD ORDER REPORT")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        # Order Information
        report_lines.append("ORDER INFORMATION")
        report_lines.append("-" * 80)
        report_lines.append(f"Order ID:           {order_id}")
        report_lines.append(f"Status:            {status}")
        report_lines.append(f"Entered Time:       {entered_time}")
        report_lines.append(f"Order Type:        {order_details.get('orderType', 'N/A')}")
        report_lines.append(f"Session:           {order_details.get('session', 'N/A')}")
        report_lines.append(f"Duration:          {order_details.get('duration', 'N/A')}")
        report_lines.append(f"Quantity:          {order_details.get('quantity', 0)}")
        report_lines.append(f"Filled Quantity:   {order_details.get('filledQuantity', 0)}")
        report_lines.append(f"Remaining Qty:     {order_details.get('remainingQuantity', 0)}")
        report_lines.append(f"Cancelable:        {order_details.get('cancelable', False)}")
        report_lines.append(f"Editable:          {order_details.get('editable', False)}")
        report_lines.append("")
        
        # Strategy Parameters
        report_lines.append("STRATEGY PARAMETERS")
        report_lines.append("-" * 80)
        report_lines.append(f"Symbol:            {symbol}")
        report_lines.append(f"Bias:              {bias.upper()}")
        report_lines.append(f"Expiration Date:   {date} (YYMMDD format)")
        report_lines.append("")
        
        # Opening Range Data
        if opening_range_data:
            orh = opening_range_data.get('high')
            orl = opening_range_data.get('low')
            midpoint = opening_range_data.get('midpoint')
            report_lines.append("Opening Range:")
            if orh is not None:
                report_lines.append(f"  ORH (High):       ${orh:.2f}")
            if orl is not None:
                report_lines.append(f"  ORL (Low):        ${orl:.2f}")
            if midpoint is not None:
                report_lines.append(f"  Midpoint:        ${midpoint:.2f}")
        else:
            report_lines.append("Opening Range:     N/A")
        report_lines.append("")
        
        # Breakout Candle Data
        if breakout_data:
            close_price = breakout_data.get('close_price')
            direction = breakout_data.get('direction', 'N/A')
            if close_price is not None and opening_range_data:
                midpoint = opening_range_data.get('midpoint')
                if midpoint is not None:
                    distance = abs(close_price - midpoint)
                    report_lines.append("Breakout Candle:")
                    report_lines.append(f"  Close Price:     ${close_price:.2f}")
                    report_lines.append(f"  Direction:       {direction.upper()}")
                    report_lines.append(f"  Distance from Midpoint: ${distance:.2f}")
                else:
                    report_lines.append("Breakout Candle:")
                    report_lines.append(f"  Close Price:     ${close_price:.2f}")
                    report_lines.append(f"  Direction:       {direction.upper()}")
            elif close_price is not None:
                report_lines.append("Breakout Candle:")
                report_lines.append(f"  Close Price:     ${close_price:.2f}")
                report_lines.append(f"  Direction:       {direction.upper()}")
        else:
            report_lines.append("Breakout Candle:   N/A")
        report_lines.append("")
        
        # Spread Details
        report_lines.append("SPREAD DETAILS")
        report_lines.append("-" * 80)
        spread_type = "Call Credit Spread" if bias == 'bearish' else "Put Credit Spread"
        report_lines.append(f"Spread Type:       {spread_type}")
        report_lines.append(f"Short Strike:       ${short_strike:.2f}")
        report_lines.append(f"Long Strike:      ${long_strike:.2f}")
        width = abs(long_strike - short_strike)
        report_lines.append(f"Width:             ${width:.2f}")
        report_lines.append(f"Net Mid Price:     ${net_mid:.2f}")
        report_lines.append(f"Max Profit:        ${net_mid:.2f} (net credit)")
        max_loss = width - net_mid
        report_lines.append(f"Max Loss:          ${max_loss:.2f}")
        if bias == 'bearish':
            breakeven = short_strike + net_mid
        else:
            breakeven = short_strike - net_mid
        report_lines.append(f"Breakeven:         ${breakeven:.2f}")
        report_lines.append("")
        
        # Order Legs
        report_lines.append("ORDER LEGS")
        report_lines.append("-" * 80)
        order_legs = order_details.get('orderLegCollection', [])
        for i, leg in enumerate(order_legs, 1):
            instrument = leg.get('instrument', {})
            report_lines.append(f"Leg {i}:")
            report_lines.append(f"  Instruction:     {leg.get('instruction', 'N/A')}")
            report_lines.append(f"  Symbol:          {instrument.get('symbol', 'N/A')}")
            report_lines.append(f"  Description:      {instrument.get('description', 'N/A')}")
            report_lines.append(f"  Quantity:        {leg.get('quantity', 0)}")
            report_lines.append(f"  Asset Type:      {instrument.get('assetType', 'N/A')}")
            report_lines.append(f"  Put/Call:        {instrument.get('putCall', 'N/A')}")
            report_lines.append("")
        
        # Account Information
        report_lines.append("ACCOUNT INFORMATION")
        report_lines.append("-" * 80)
        report_lines.append(f"Account Number:    {order_details.get('accountNumber', 'N/A')}")
        report_lines.append("")
        
        # Footer
        report_lines.append("=" * 80)
        report_lines.append(f"Report Generated:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Report File:       {filename}")
        report_lines.append("=" * 80)
        
        # Write report to file
        try:
            with open(filepath, 'w') as f:
                f.write('\n'.join(report_lines))
            logger.info(f"Order report generated: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to generate order report: {e}")
            return ""

