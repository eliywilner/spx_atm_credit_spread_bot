"""Opening Range (OR) calculator for SPX."""
from datetime import datetime
from typing import Dict, Optional
import pytz
from src.strategy.market_data import MarketDataFetcher
from src.utils.logger import setup_logger

logger = setup_logger(__name__)
ET = pytz.timezone('US/Eastern')


class OpeningRangeTracker:
    """Tracks the Opening Range (09:30-10:00 ET candle) for SPX."""
    
    def __init__(self):
        """Initialize opening range tracker."""
        self.market_data = MarketDataFetcher()
    
    def get_opening_range(self, date: datetime) -> Optional[Dict]:
        """
        Get Opening Range data from the 09:30-10:00 ET candle.
        
        Args:
            date: Trading date
        
        Returns:
            Dictionary with keys: ORO, ORH, ORL, ORC
            Returns None if OR candle not found
        """
        # Get 30-minute candles for the OR window
        candles = self.market_data.get_30min_candles(
            date,
            start_hour=9,
            start_minute=30,
            end_hour=10,
            end_minute=0
        )
        
        if not candles:
            logger.warning(f"No candles found for OR window on {date.strftime('%Y-%m-%d')}")
            return None
        
        # The OR candle should be the first (and only) candle in this window
        or_candle = candles[0] if candles else None
        
        if not or_candle:
            logger.warning(f"OR candle not found for {date.strftime('%Y-%m-%d')}")
            return None
        
        or_data = {
            'ORO': or_candle.get('open', 0),
            'ORH': or_candle.get('high', 0),
            'ORL': or_candle.get('low', 0),
            'ORC': or_candle.get('close', 0),
            'datetime': or_candle.get('datetime', 0)
        }
        
        logger.info(f"Opening Range for {date.strftime('%Y-%m-%d')}:")
        logger.info(f"  ORO: ${or_data['ORO']:.2f}")
        logger.info(f"  ORH: ${or_data['ORH']:.2f}")
        logger.info(f"  ORL: ${or_data['ORL']:.2f}")
        logger.info(f"  ORC: ${or_data['ORC']:.2f}")
        
        return or_data
    
    def is_bullish_or(self, or_data: Dict) -> bool:
        """
        Check if Opening Range is bullish (ORC > ORO).
        
        Args:
            or_data: Opening Range data dictionary
        
        Returns:
            True if bullish, False otherwise
        """
        return or_data.get('ORC', 0) > or_data.get('ORO', 0)
    
    def is_bearish_or(self, or_data: Dict) -> bool:
        """
        Check if Opening Range is bearish (ORC < ORO).
        
        Args:
            or_data: Opening Range data dictionary
        
        Returns:
            True if bearish, False otherwise
        """
        return or_data.get('ORC', 0) < or_data.get('ORO', 0)

