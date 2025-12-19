"""Quotes manager for retrieving market data and option quotes."""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union
from src.client.schwab_client import SchwabClient
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class QuotesManager:
    """Manages market data and option quotes retrieval."""
    
    # Strike conversion factors between SPXW and XSP
    # XSP is 1/10th the size of SPXW
    STRIKE_CONVERSION_FACTOR = {
        'SPXW': {'XSP': 0.1},  # SPXW to XSP: divide by 10
        'XSP': {'SPXW': 10.0}  # XSP to SPXW: multiply by 10
    }
    
    def __init__(self, default_symbol: Optional[str] = None):
        """
        Initialize the quotes manager.
        
        Args:
            default_symbol: Default option symbol to use ('SPXW' or 'XSP').
                          If None, uses Config.DEFAULT_OPTION_SYMBOL.
        """
        self.client = SchwabClient()
        # Market data uses a different base URL
        self.market_data_base_url = 'https://api.schwabapi.com/marketdata/v1'
        
        # Set default symbol
        if default_symbol is None:
            symbol_from_config = Config.DEFAULT_OPTION_SYMBOL.upper()
        else:
            symbol_from_config = default_symbol.upper()
        
        # Map XSP to $XSP (the actual symbol used by Schwab API)
        if symbol_from_config == 'XSP':
            self.default_symbol = '$XSP'
        elif symbol_from_config == 'SPXW':
            self.default_symbol = 'SPXW'
        else:
            raise ValueError(f"default_symbol must be 'SPXW' or 'XSP', got '{symbol_from_config}'")
        
        logger.info(f"QuotesManager initialized with default symbol: {self.default_symbol}")
    
    def _make_market_data_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Make a request to the market data API (different base URL).
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/quotes')
            params: URL parameters
        
        Returns:
            dict: Response JSON data
        """
        url = f"{self.market_data_base_url}{endpoint}"
        headers = self.client.auth.get_headers()
        
        try:
            import requests
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params
            )
            
            # If token expired, try refreshing
            if response.status_code == 401:
                logger.warning("Token expired, refreshing...")
                self.client.auth.refresh_access_token()
                headers = self.client.auth.get_headers()
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params
                )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error: {e}")
            if response.text:
                logger.error(f"Response: {response.text}")
            raise
    
    def get_quotes(
        self,
        symbols: Union[str, List[str]],
        fields: Optional[str] = None,
        indicative: bool = False
    ) -> Dict:
        """
        Get quotes for one or more symbols.
        
        Args:
            symbols: Single symbol string or list of symbols
                    Examples: 'AAPL', ['AAPL', 'MSFT'], 'SPXW  251113C06810000'
            fields: Comma-separated list of root nodes (quote, fundamental, extended, reference, regular)
                   Default: 'all' (returns all fields)
            indicative: Include indicative quotes for ETF symbols (default: False)
        
        Returns:
            dict: Quote data for the requested symbols
        
        Example:
            >>> quotes = mgr.get_quotes('AAPL')
            >>> quotes = mgr.get_quotes(['AAPL', 'MSFT'], fields='quote,reference')
            >>> quotes = mgr.get_quotes('SPXW  251113C06810000')
        """
        # Convert list to comma-separated string if needed
        if isinstance(symbols, list):
            symbols_str = ','.join(symbols)
        else:
            symbols_str = symbols
        
        logger.info(f"Fetching quotes for symbol(s): {symbols_str}")
        
        # Build query parameters
        params = {
            'symbols': symbols_str
        }
        
        if fields:
            params['fields'] = fields
        
        if indicative:
            params['indicative'] = 'true'
        
        # Make the API call
        quotes = self._make_market_data_request('GET', '/quotes', params=params)
        
        logger.info(f"Quotes retrieved successfully")
        
        return quotes
    
    def get_option_quote(
        self,
        symbol: str,
        expiration_date: str,
        option_type: str,
        strike: Union[int, float, str],
        fields: Optional[str] = None
    ) -> Dict:
        """
        Get quote for a specific option contract.
        
        Args:
            symbol: Underlying symbol (e.g., 'SPXW')
            expiration_date: Expiration date in YYMMDD format (e.g., '251113' for Nov 13, 2025)
            option_type: 'C' for Call or 'P' for Put
            strike: Strike price (will be formatted to 8 digits with leading zeros)
                   Examples: 6810, '6810', 6810.0
            fields: Optional fields to return (default: 'all')
        
        Returns:
            dict: Quote data for the option contract
        
        Example:
            >>> # Get quote for SPXW Nov 13, 2025 $6810 Call
            >>> quote = mgr.get_option_quote('SPXW', '251113', 'C', 6810)
        """
        # Format strike to get strike integer for logging
        if isinstance(strike, float):
            strike_int = int(strike)
        elif isinstance(strike, str):
            strike_int = int(float(strike))
        else:
            strike_int = int(strike)
        
        # Use _format_option_symbol to get the correct format
        # This handles SPXW (2 spaces) and $XSP (3 spaces, no $) correctly
        option_symbol = self._format_option_symbol(symbol, expiration_date, option_type, strike_int)
        
        logger.info(f"Getting quote for option: {option_symbol}")
        logger.info(f"  Symbol: {symbol}, Expiration: {expiration_date}, Type: {option_type}, Strike: {strike_int}")
        
        # Get the quote
        quotes = self.get_quotes(option_symbol, fields=fields)
        
        return quotes
    
    def get_spxw_option_quote(
        self,
        expiration_date: str,
        option_type: str,
        strike: Union[int, float, str],
        fields: Optional[str] = None
    ) -> Dict:
        """
        Convenience method to get SPXW option quotes.
        
        Args:
            expiration_date: Expiration date in YYMMDD format (e.g., '251113' for Nov 13, 2025)
            option_type: 'C' for Call or 'P' for Put
            strike: Strike price (will be formatted to 8 digits)
            fields: Optional fields to return (default: 'all')
        
        Returns:
            dict: Quote data for the SPXW option contract
        
        Example:
            >>> # Get quote for SPXW Nov 13, 2025 $6810 Call
            >>> quote = mgr.get_spxw_option_quote('251113', 'C', 6810)
        """
        return self.get_option_quote(self.default_symbol, expiration_date, option_type, strike, fields)
    
    def convert_strike(self, strike: Union[int, float], from_symbol: str, to_symbol: str) -> float:
        """
        Convert strike price between SPXW and XSP.
        
        Args:
            strike: Strike price to convert
            from_symbol: Source symbol ('SPXW' or 'XSP')
            to_symbol: Target symbol ('SPXW' or 'XSP')
        
        Returns:
            float: Converted strike price
        
        Examples:
            >>> # Convert SPXW strike to XSP (divide by 10)
            >>> mgr.convert_strike(6750, 'SPXW', 'XSP')  # Returns 675.0
            
            >>> # Convert XSP strike to SPXW (multiply by 10)
            >>> mgr.convert_strike(675, 'XSP', 'SPXW')  # Returns 6750.0
        """
        from_symbol = from_symbol.upper()
        to_symbol = to_symbol.upper()
        
        if from_symbol == to_symbol:
            return float(strike)
        
        if from_symbol not in ['SPXW', 'XSP'] or to_symbol not in ['SPXW', 'XSP']:
            raise ValueError(f"Symbols must be 'SPXW' or 'XSP', got '{from_symbol}' -> '{to_symbol}'")
        
        conversion_factor = self.STRIKE_CONVERSION_FACTOR[from_symbol][to_symbol]
        return float(strike) * conversion_factor
    
    def get_today_expiration_date(self) -> str:
        """
        Get today's date in YYMMDD format for option expiration.
        
        Returns:
            str: Today's date in YYMMDD format (e.g., '251113' for Nov 13, 2025)
        """
        today = datetime.now()
        return today.strftime('%y%m%d')
    
    def get_credit_spread_quote_by_bias(
        self,
        symbol: str,
        bias: str,
        short_strike: Union[int, float, str],
        width: int = 5,
        expiration_date: Optional[str] = None,
        fields: Optional[str] = None
    ) -> Dict:
        """
        Get credit spread quote using bias (bearish/bullish) and short strike.
        Uses today's expiration date by default.
        
        Args:
            symbol: Underlying symbol (e.g., 'SPXW')
            bias: 'bearish' for Call Credit Spread or 'bullish' for Put Credit Spread
            short_strike: Strike price of the short leg (the one you sell)
            width: Width of the spread in dollars (default: 5)
            expiration_date: Optional expiration date in YYMMDD format. If None, uses today's date.
            fields: Optional fields to return (default: 'all')
        
        Returns:
            dict: Combined spread quote data
        
        Example:
            >>> # Bullish: Sell $6765 Put, Buy $6760 Put (5 dollar wide)
            >>> quote = mgr.get_credit_spread_quote_by_bias('SPXW', 'bullish', 6765)
            
            >>> # Bearish: Sell $6765 Call, Buy $6770 Call (5 dollar wide)
            >>> quote = mgr.get_credit_spread_quote_by_bias('SPXW', 'bearish', 6765)
        """
        # Use today's date if not provided
        if expiration_date is None:
            expiration_date = self.get_today_expiration_date()
            logger.info(f"Using today's expiration date: {expiration_date}")
        
        # Convert bias to spread type
        bias_lower = bias.lower()
        if bias_lower in ['bearish', 'bear']:
            spread_type = 'CALL'
        elif bias_lower in ['bullish', 'bull']:
            spread_type = 'PUT'
        else:
            raise ValueError("bias must be 'bearish' or 'bullish'")
        
        return self.get_credit_spread_quote(
            symbol=symbol,
            expiration_date=expiration_date,
            spread_type=spread_type,
            short_strike=short_strike,
            width=width,
            fields=fields
        )
    
    def _round_strike_to_interval(self, strike: Union[int, float], symbol: str) -> int:
        """
        Round strike to the correct interval for the symbol.
        
        Args:
            strike: Strike price to round
            symbol: 'SPXW' (intervals of 5) or '$XSP'/'XSP' (intervals of 1)
        
        Returns:
            int: Rounded strike price
        
        Examples:
            >>> mgr._round_strike_to_interval(6763, 'SPXW')  # Returns 6765
            >>> mgr._round_strike_to_interval(675.7, '$XSP')  # Returns 676
        """
        symbol_upper = symbol.upper().replace('$', '')
        strike_float = float(strike)
        
        if symbol_upper == 'SPXW':
            # SPXW strikes are in intervals of 5
            return int(round(strike_float / 5) * 5)
        elif symbol_upper == 'XSP':
            # XSP strikes are in intervals of 1
            return int(round(strike_float))
        else:
            raise ValueError(f"Symbol must be 'SPXW' or 'XSP'/'$XSP', got '{symbol}'")
    
    def get_credit_spread_quote_by_bias_default(
        self,
        bias: str,
        short_strike: Union[int, float, str],
        width: Optional[Union[int, float]] = None,
        expiration_date: Optional[str] = None,
        fields: Optional[str] = None
    ) -> Dict:
        """
        Get credit spread quote using bias and short strike with default symbol.
        Uses today's expiration date by default.
        
        Args:
            bias: 'bearish' for Call Credit Spread or 'bullish' for Put Credit Spread
            short_strike: Strike price of the short leg (the one you sell)
                         Note: For XSP, strikes are 1/10th of SPXW (e.g., 675 in XSP = 6750 in SPXW)
                         SPXW strikes are in intervals of 5, XSP strikes are in intervals of 1
            width: Width of the spread in dollars.
                  If None, uses default: 5 for SPXW, 1 for XSP
            expiration_date: Optional expiration date in YYMMDD format. If None, uses today's date.
            fields: Optional fields to return (default: 'all')
        
        Returns:
            dict: Combined spread quote data
        
        Example:
            >>> # Bullish with XSP: Sell $675 Put, Buy $674 Put (1 dollar wide, today's expiration)
            >>> quote = mgr.get_credit_spread_quote_by_bias_default('bullish', 675)
            
            >>> # Bearish with SPXW: Sell $6765 Call, Buy $6770 Call (5 dollar wide, today's expiration)
            >>> quote = mgr.get_credit_spread_quote_by_bias_default('bearish', 6765)
        """
        # Round strike to correct interval
        short_strike_rounded = self._round_strike_to_interval(short_strike, self.default_symbol)
        
        # Set default width if not provided
        if width is None:
            if self.default_symbol == 'SPXW':
                width = 5
            else:  # XSP
                width = 1
        
        return self.get_credit_spread_quote_by_bias(
            symbol=self.default_symbol,
            bias=bias,
            short_strike=short_strike_rounded,
            width=width,
            expiration_date=expiration_date,
            fields=fields
        )
    
    def get_spxw_credit_spread_quote_by_bias(
        self,
        bias: str,
        short_strike: Union[int, float, str],
        width: int = 5,
        expiration_date: Optional[str] = None,
        fields: Optional[str] = None
    ) -> Dict:
        """
        Get SPXW credit spread quote using bias and short strike.
        Uses today's expiration date by default.
        
        Note: This method is for SPXW specifically. For the default symbol (configurable),
        use get_credit_spread_quote_by_bias_default() instead.
        SPXW strikes are in intervals of 5 (e.g., 6750, 6755, 6760, 6765).
        
        Args:
            bias: 'bearish' for Call Credit Spread or 'bullish' for Put Credit Spread
            short_strike: Strike price of the short leg (the one you sell)
                         SPXW strikes are in intervals of 5 (will be rounded if needed)
            width: Width of the spread in dollars (default: 5)
            expiration_date: Optional expiration date in YYMMDD format. If None, uses today's date.
            fields: Optional fields to return (default: 'all')
        
        Returns:
            dict: Combined spread quote data
        
        Example:
            >>> # Bullish: Sell $6765 Put, Buy $6760 Put (5 dollar wide, today's expiration)
            >>> quote = mgr.get_spxw_credit_spread_quote_by_bias('bullish', 6765)
            
            >>> # Bearish: Sell $6765 Call, Buy $6770 Call (5 dollar wide, today's expiration)
            >>> quote = mgr.get_spxw_credit_spread_quote_by_bias('bearish', 6765)
        """
        # Round strike to interval of 5 for SPXW
        short_strike_rounded = self._round_strike_to_interval(short_strike, 'SPXW')
        
        return self.get_credit_spread_quote_by_bias(
            symbol='SPXW',
            bias=bias,
            short_strike=short_strike_rounded,
            width=width,
            expiration_date=expiration_date,
            fields=fields
        )
    
    def get_xsp_credit_spread_quote_by_bias(
        self,
        bias: str,
        short_strike: Union[int, float, str],
        width: int = 1,
        expiration_date: Optional[str] = None,
        fields: Optional[str] = None
    ) -> Dict:
        """
        Get XSP credit spread quote using bias and short strike.
        Uses today's expiration date by default.
        
        Note: XSP strikes are 1/10th of SPXW and are in intervals of 1.
              Default width is 1 dollar (equivalent to 5 in SPXW).
        
        Args:
            bias: 'bearish' for Call Credit Spread or 'bullish' for Put Credit Spread
            short_strike: Strike price of the short leg (the one you sell)
                         Note: XSP strikes are 1/10th of SPXW (e.g., 675 in XSP = 6750 in SPXW)
                         XSP strikes are in intervals of 1 (e.g., 675, 676, 677)
            width: Width of the spread in dollars (default: 1 for XSP)
            expiration_date: Optional expiration date in YYMMDD format. If None, uses today's date.
            fields: Optional fields to return (default: 'all')
        
        Returns:
            dict: Combined spread quote data
        
        Example:
            >>> # Bullish: Sell $675 Put, Buy $674 Put (1 dollar wide, today's expiration)
            >>> quote = mgr.get_xsp_credit_spread_quote_by_bias('bullish', 675)
            
            >>> # Bearish: Sell $675 Call, Buy $676 Call (1 dollar wide, today's expiration)
            >>> quote = mgr.get_xsp_credit_spread_quote_by_bias('bearish', 675)
        """
        # Round strike to interval of 1 for XSP
        short_strike_rounded = self._round_strike_to_interval(short_strike, 'XSP')
        
        return self.get_credit_spread_quote_by_bias(
            symbol='$XSP',
            bias=bias,
            short_strike=short_strike_rounded,
            width=width,
            expiration_date=expiration_date,
            fields=fields
        )
    
    def get_credit_spread_quote(
        self,
        symbol: str,
        expiration_date: str,
        spread_type: str,
        short_strike: Union[int, float, str],
        width: Union[int, float] = 5,
        fields: Optional[str] = None
    ) -> Dict:
        """
        Get quote for a credit spread.
        
        Args:
            symbol: Underlying symbol (e.g., 'SPXW' or 'XSP')
            expiration_date: Expiration date in YYMMDD format (e.g., '251113')
            spread_type: 'CALL' for Call Credit Spread (bearish) or 'PUT' for Put Credit Spread (bullish)
            short_strike: Strike price of the short leg (the one you sell)
                         Note: For XSP, strikes are 1/10th of SPXW (e.g., 675 in XSP = 6750 in SPXW)
                         SPXW strikes are in intervals of 5 (e.g., 6750, 6755, 6760)
                         XSP strikes are in intervals of 1 (e.g., 675, 676, 677)
            width: Width of the spread in dollars (default: 5 for SPXW, 1 for XSP)
                   Note: For XSP, width is typically 1 (equivalent to 5 in SPXW)
            fields: Optional fields to return (default: 'all')
        
        Returns:
            dict: Combined spread quote data with:
                - short_leg: Quote for short leg (sold option)
                - long_leg: Quote for long leg (bought option)
                - spread_info: Spread details (net credit/debit, width, etc.)
        
        Example:
            >>> # Call Credit Spread: Sell $6810 Call, Buy $6815 Call
            >>> quote = mgr.get_credit_spread_quote('SPXW', '251113', 'CALL', 6810, width=5)
            
            >>> # Put Credit Spread: Sell $6810 Put, Buy $6805 Put
            >>> quote = mgr.get_credit_spread_quote('SPXW', '251113', 'PUT', 6810, width=5)
        """
        spread_type_upper = spread_type.upper()
        
        if spread_type_upper not in ['CALL', 'PUT']:
            raise ValueError("spread_type must be 'CALL' or 'PUT'")
        
        # Calculate long leg strike based on spread type
        if spread_type_upper == 'CALL':
            # Call Credit Spread: Short lower strike, Long higher strike
            long_strike = short_strike + width
            short_option_type = 'C'
            long_option_type = 'C'
        else:
            # Put Credit Spread: Short higher strike, Long lower strike
            long_strike = short_strike - width
            short_option_type = 'P'
            long_option_type = 'P'
        
        logger.info(f"Getting {spread_type} Credit Spread quote:")
        logger.info(f"  Symbol: {symbol}, Expiration: {expiration_date}")
        logger.info(f"  Short Strike: ${short_strike}, Long Strike: ${long_strike}, Width: ${width}")
        
        # Get quotes for both legs simultaneously
        short_symbol = self._format_option_symbol(symbol, expiration_date, short_option_type, short_strike)
        long_symbol = self._format_option_symbol(symbol, expiration_date, long_option_type, long_strike)
        
        # Get both quotes in one API call
        quotes = self.get_quotes([short_symbol, long_symbol], fields=fields)
        
        # Extract individual leg quotes
        short_leg_quote = quotes.get(short_symbol, {})
        long_leg_quote = quotes.get(long_symbol, {})
        
        # Calculate spread metrics
        short_quote_data = short_leg_quote.get('quote', {})
        long_quote_data = long_leg_quote.get('quote', {})
        
        # Net credit = Bid of short leg - Ask of long leg (what you'd receive)
        short_bid = short_quote_data.get('bidPrice', 0.0)
        long_ask = long_quote_data.get('askPrice', 0.0)
        net_credit = short_bid - long_ask
        
        # Net debit = Ask of short leg - Bid of long leg (what you'd pay to close)
        short_ask = short_quote_data.get('askPrice', 0.0)
        long_bid = long_quote_data.get('bidPrice', 0.0)
        net_debit = short_ask - long_bid
        
        # Mid price
        short_mid = short_quote_data.get('mark', 0.0)
        long_mid = long_quote_data.get('mark', 0.0)
        net_mid = short_mid - long_mid
        
        spread_info = {
            'spread_type': f'{spread_type} Credit Spread',
            'symbol': symbol,
            'expiration_date': expiration_date,
            'short_strike': short_strike,
            'long_strike': long_strike,
            'width': width,
            'net_credit': round(net_credit, 2),  # Best case: receive this
            'net_debit': round(net_debit, 2),    # Worst case: pay this to close
            'net_mid': round(net_mid, 2),        # Mid price
            'max_profit': round(net_credit, 2),  # Maximum profit (net credit received)
            'max_loss': round(width - net_credit, 2),  # Maximum loss (width - credit)
            'breakeven': round(short_strike + net_credit, 2) if spread_type_upper == 'CALL' else round(short_strike - net_credit, 2)
        }
        
        result = {
            'short_leg': short_leg_quote,
            'long_leg': long_leg_quote,
            'spread_info': spread_info
        }
        
        logger.info(f"Spread Quote - Net Credit: ${net_credit:.2f}, Net Debit: ${net_debit:.2f}, Mid: ${net_mid:.2f}")
        
        return result
    
    def get_spxw_credit_spread_quote(
        self,
        expiration_date: str,
        spread_type: str,
        short_strike: Union[int, float, str],
        width: int = 5,
        fields: Optional[str] = None
    ) -> Dict:
        """
        Convenience method to get SPXW credit spread quotes (5-dollar wide).
        
        Args:
            expiration_date: Expiration date in YYMMDD format
            spread_type: 'CALL' for Call Credit Spread or 'PUT' for Put Credit Spread
            short_strike: Strike price of the short leg
            width: Width of the spread (default: 5)
            fields: Optional fields to return
        
        Returns:
            dict: Combined spread quote data
        
        Example:
            >>> # Call Credit Spread: Sell $6810 Call, Buy $6815 Call
            >>> quote = mgr.get_spxw_credit_spread_quote('251113', 'CALL', 6810)
        """
        return self.get_credit_spread_quote('SPXW', expiration_date, spread_type, short_strike, width, fields)
    
    def get_xsp_credit_spread_quote(
        self,
        expiration_date: str,
        spread_type: str,
        short_strike: Union[int, float, str],
        width: int = 1,
        fields: Optional[str] = None
    ) -> Dict:
        """
        Convenience method to get XSP credit spread quotes (1-dollar wide by default).
        
        Note: XSP strikes are 1/10th of SPXW and are in intervals of 1.
              Default width is 1 dollar (equivalent to 5 in SPXW).
        
        Args:
            expiration_date: Expiration date in YYMMDD format
            spread_type: 'CALL' for Call Credit Spread or 'PUT' for Put Credit Spread
            short_strike: Strike price of the short leg (XSP strikes are 1/10th of SPXW, intervals of 1)
            width: Width of the spread (default: 1 for XSP)
            fields: Optional fields to return
        
        Returns:
            dict: Combined spread quote data
        
        Example:
            >>> # Call Credit Spread: Sell $675 Call, Buy $676 Call (1 dollar wide)
            >>> quote = mgr.get_xsp_credit_spread_quote('251113', 'CALL', 675)
        """
        # Round strike to interval of 1 for XSP
        short_strike_rounded = self._round_strike_to_interval(short_strike, '$XSP')
        
        return self.get_credit_spread_quote('$XSP', expiration_date, spread_type, short_strike_rounded, width, fields)
    
    def _format_option_symbol(
        self,
        symbol: str,
        expiration_date: str,
        option_type: str,
        strike: Union[int, float, str]
    ) -> str:
        """
        Format option symbol in the correct format.
        
        Args:
            symbol: Underlying symbol (e.g., 'SPXW' or '$XSP')
            expiration_date: YYMMDD format
            option_type: 'C' or 'P'
            strike: Strike price
        
        Returns:
            str: Formatted option symbol
        
        Note:
            - SPXW uses format: "SPXW  YYMMDD[C|P]STRIKE" (2 spaces)
            - $XSP uses format: "XSP   YYMMDD[C|P]STRIKE" (3 spaces, no $ in option symbol)
        """
        # Format strike to 8 digits (multiply by 1000, pad to 8)
        if isinstance(strike, float):
            strike_int = int(strike)
        elif isinstance(strike, str):
            strike_int = int(float(strike))
        else:
            strike_int = int(strike)
        
        strike_formatted = strike_int * 1000
        strike_str = f"{strike_formatted:08d}"
        
        # For $XSP, the option symbol uses "XSP" (without $) and 3 spaces
        # For SPXW, it uses 2 spaces
        if symbol == '$XSP':
            option_symbol_base = 'XSP'
            spaces = '   '  # 3 spaces for XSP
        else:
            option_symbol_base = symbol
            spaces = '  '  # 2 spaces for SPXW
        
        return f"{option_symbol_base}{spaces}{expiration_date}{option_type.upper()}{strike_str}"

