"""Quote monitor for checking credit spreads."""
from datetime import datetime
from typing import Dict, Optional, Tuple
import pytz
from src.quotes.quotes_manager import QuotesManager
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)
ET = pytz.timezone('US/Eastern')


class QuoteMonitor:
    """Monitors option quotes and calculates credit for spreads."""
    
    def __init__(self):
        """Initialize quote monitor."""
        self.quotes_mgr = QuotesManager(default_symbol='SPXW')
    
    def get_expiration_date(self, date: datetime) -> str:
        """
        Get expiration date in YYMMDD format for 0DTE (same day).
        
        Args:
            date: Trading date
        
        Returns:
            Expiration date string (YYMMDD format)
        """
        return date.strftime('%y%m%d')
    
    def calculate_mid_price(self, quote_data: Dict) -> Optional[float]:
        """
        Calculate mid price from quote data.
        
        mid = (bid + ask) / 2
        
        Args:
            quote_data: Quote data dictionary from API
        
        Returns:
            Mid price or None if unavailable
        """
        # Quote data structure may vary, try different paths
        quote = quote_data.get('quote', {})
        if not quote:
            quote = quote_data
        
        bid = quote.get('bidPrice', quote.get('bid', 0))
        ask = quote.get('askPrice', quote.get('ask', 0))
        
        if bid is None or ask is None or bid == 0 or ask == 0:
            return None
        
        mid = (bid + ask) / 2.0
        return mid
    
    def get_spread_credit(
        self,
        date: datetime,
        k_short: float,
        k_long: float,
        option_type: str  # 'PUT' or 'CALL'
    ) -> Optional[Dict]:
        """
        Get credit spread quote and calculate C_gross and C_net.
        
        Args:
            date: Trading date
            k_short: Short strike
            k_long: Long strike
            option_type: 'PUT' or 'CALL'
        
        Returns:
            Dictionary with:
            - C_gross: Gross credit (mid price difference)
            - C_net: Net credit (C_gross - slippage buffer)
            - short_mid: Short leg mid price
            - long_mid: Long leg mid price
            - short_bid: Short leg bid
            - short_ask: Short leg ask
            - long_bid: Long leg bid
            - long_ask: Long leg ask
            Returns None if quotes unavailable
        """
        expiration_date = self.get_expiration_date(date)
        option_type_char = 'P' if option_type == 'PUT' else 'C'
        
        # Format strikes - QuotesManager expects strike in original format (not multiplied)
        # It will multiply by 1000 internally
        short_strike_for_api = int(k_short)
        long_strike_for_api = int(k_long)
        
        try:
            # Use the same pattern as original bot: format symbols and get quotes together
            short_symbol = self.quotes_mgr._format_option_symbol('SPXW', expiration_date, option_type_char, short_strike_for_api)
            long_symbol = self.quotes_mgr._format_option_symbol('SPXW', expiration_date, option_type_char, long_strike_for_api)
            
            # Get both quotes in one API call (like original bot does)
            quotes = self.quotes_mgr.get_quotes([short_symbol, long_symbol], fields='quote')
            
            # Extract individual leg quotes (same pattern as original bot)
            short_leg_quote = quotes.get(short_symbol, {})
            long_leg_quote = quotes.get(long_symbol, {})
            
            # Check for errors
            if 'errors' in quotes:
                logger.warning(f"API errors in quote response: {quotes.get('errors', {})}")
            
            # Extract quote data (same pattern as original bot)
            short_quote_data = short_leg_quote.get('quote', {})
            long_quote_data = long_leg_quote.get('quote', {})
            
            # Extract bid/ask prices for detailed logging
            short_bid = short_quote_data.get('bidPrice', 0)
            short_ask = short_quote_data.get('askPrice', 0)
            long_bid = long_quote_data.get('bidPrice', 0)
            long_ask = long_quote_data.get('askPrice', 0)
            
            # Get mid prices using mark (like original bot)
            short_mid = self.calculate_mid_price(short_quote_data)
            long_mid = self.calculate_mid_price(long_quote_data)
            
            if short_mid is None or long_mid is None:
                logger.warning(f"Could not get mid prices: short_mid={short_mid}, long_mid={long_mid}")
                if not short_quote_data:
                    logger.debug(f"Short leg quote structure: {short_leg_quote}")
                if not long_quote_data:
                    logger.debug(f"Long leg quote structure: {long_leg_quote}")
                return None
            
            # Calculate credit using both methods for comparison
            # Method 1: Using mid prices (current implementation)
            c_gross_mid = short_mid - long_mid
            
            # Method 2: Using bid/ask (actual executable credit)
            c_gross_bid_ask = short_bid - long_ask
            
            # For credit spreads: C_gross = short_mid - long_mid (current implementation)
            c_gross = c_gross_mid
            
            # Apply slippage buffer
            c_net = c_gross - Config.SLIPPAGE_BUFFER
            
            # DETAILED LOGGING - Show each leg and calculation
            logger.info("")
            logger.info("=" * 70)
            logger.info("SPREAD QUOTE DETAILS")
            logger.info("=" * 70)
            logger.info(f"Option Symbols:")
            logger.info(f"  Short leg: {short_symbol} (K_short=${k_short:.2f})")
            logger.info(f"  Long leg:  {long_symbol} (K_long=${k_long:.2f})")
            logger.info("")
            logger.info("Short Leg (SELL) Quote:")
            logger.info(f"  Bid: ${short_bid:.2f}")
            logger.info(f"  Ask: ${short_ask:.2f}")
            logger.info(f"  Mid: ${short_mid:.2f} = (${short_bid:.2f} + ${short_ask:.2f}) / 2")
            logger.info("")
            logger.info("Long Leg (BUY) Quote:")
            logger.info(f"  Bid: ${long_bid:.2f}")
            logger.info(f"  Ask: ${long_ask:.2f}")
            logger.info(f"  Mid: ${long_mid:.2f} = (${long_bid:.2f} + ${long_ask:.2f}) / 2")
            logger.info("")
            logger.info("Credit Calculation:")
            logger.info(f"  Using MID prices:  C_gross = ${short_mid:.2f} - ${long_mid:.2f} = ${c_gross_mid:.2f}")
            logger.info(f"  Using BID/ASK:     C_gross = ${short_bid:.2f} - ${long_ask:.2f} = ${c_gross_bid_ask:.2f} (actual executable)")
            logger.info(f"  Difference:        ${abs(c_gross_mid - c_gross_bid_ask):.2f}")
            logger.info("")
            logger.info(f"Final Credit (using MID):")
            logger.info(f"  C_gross: ${c_gross:.2f}")
            logger.info(f"  Slippage buffer: -${Config.SLIPPAGE_BUFFER:.2f}")
            logger.info(f"  C_net: ${c_net:.2f}")
            logger.info("=" * 70)
            logger.info("")
            
            # Extract bid/ask for logging (using quote_data, same as original bot)
            result = {
                'C_gross': c_gross,
                'C_net': c_net,
                'short_mid': short_mid,
                'long_mid': long_mid,
                'short_bid': short_bid,
                'short_ask': short_ask,
                'long_bid': long_bid,
                'long_ask': long_ask
            }
            
            logger.debug(f"Spread credit: C_gross=${c_gross:.2f}, C_net=${c_net:.2f} (S=${Config.SLIPPAGE_BUFFER:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting spread credit: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def meets_credit_threshold(self, credit_data: Dict) -> bool:
        """
        Check if credit meets minimum threshold.
        
        Args:
            credit_data: Credit data dictionary from get_spread_credit()
        
        Returns:
            True if C_net >= MIN_NET_CREDIT, False otherwise
        """
        if not credit_data:
            return False
        
        c_net = credit_data.get('C_net', 0)
        meets_threshold = c_net >= Config.MIN_NET_CREDIT
        
        if meets_threshold:
            logger.info(f"✅ Credit threshold met: C_net=${c_net:.2f} >= ${Config.MIN_NET_CREDIT:.2f}")
        else:
            logger.info(f"❌ Credit threshold NOT met: C_net=${c_net:.2f} < ${Config.MIN_NET_CREDIT:.2f}")
        
        return meets_threshold

