"""Market data fetcher for SPX index."""
import requests
from datetime import datetime
from typing import List, Dict, Optional
import pytz
from src.utils.logger import setup_logger
from src.client.schwab_client import SchwabClient

logger = setup_logger(__name__)
ET = pytz.timezone('US/Eastern')


class MarketDataFetcher:
    """Fetches SPX index market data (30-minute candles)."""
    
    def __init__(self):
        """Initialize market data fetcher."""
        self.client = SchwabClient()
        self.base_url = 'https://api.schwabapi.com/marketdata/v1'
        self.spx_symbol = '$SPX'  # SPX index symbol
    
    def get_30min_candles(
        self,
        date: datetime,
        start_hour: int = 9,
        start_minute: int = 30,
        end_hour: int = 16,
        end_minute: int = 0
    ) -> List[Dict]:
        """
        Get 30-minute candles for SPX index for a specific date.
        
        Args:
            date: Trading date (datetime object)
            start_hour: Start hour (ET)
            start_minute: Start minute (ET)
            end_hour: End hour (ET)
            end_minute: End minute (ET)
        
        Returns:
            List of candle dictionaries with keys: datetime, open, high, low, close, volume
        """
        # Create datetime objects for start and end times
        if date.tzinfo is None:
            date = ET.localize(date)
        
        day_start = date.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
        day_end = date.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
        
        # Convert to timestamps (milliseconds)
        start_timestamp = int(day_start.timestamp() * 1000)
        end_timestamp = int(day_end.timestamp() * 1000)
        
        headers = self.client.auth.get_headers()
        
        params = {
            'symbol': self.spx_symbol,
            'periodType': 'day',
            'period': 1,
            'frequencyType': 'minute',
            'frequency': 30,  # 30-minute candles
            'startDate': start_timestamp,
            'endDate': end_timestamp
        }
        
        url = f'{self.base_url}/pricehistory'
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 401:
                logger.info("Token expired, refreshing...")
                self.client.auth.refresh_access_token()
                headers = self.client.auth.get_headers()
                response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Failed to get candles: {response.status_code} - {response.text}")
                return []
            
            data = response.json()
            candles = data.get('candles', [])
            
            # Sort by datetime
            candles.sort(key=lambda x: x.get('datetime', 0))
            
            logger.info(f"Retrieved {len(candles)} 30-minute candles for {date.strftime('%Y-%m-%d')}")
            return candles
            
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def get_spx_close_price(self, date: datetime) -> Optional[float]:
        """
        Get SPX closing price at 16:00 ET for a specific date.
        
        Args:
            date: Trading date
        
        Returns:
            Closing price or None if unavailable
        """
        candles = self.get_30min_candles(
            date,
            start_hour=15,
            start_minute=30,
            end_hour=16,
            end_minute=0
        )
        
        if not candles:
            # Try getting the last candle of the day
            all_candles = self.get_30min_candles(date)
            if all_candles:
                return all_candles[-1].get('close')
            return None
        
        # Return close of the 15:30-16:00 candle
        return candles[-1].get('close') if candles else None

