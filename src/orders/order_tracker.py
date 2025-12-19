"""Order Tracker - Tracks placed orders to prevent duplicates."""
import os
import json
import logging
from datetime import datetime, date
from typing import Optional, Dict, List
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class OrderTracker:
    """
    Tracks placed orders to prevent duplicate orders on the same day.
    Stores order information in a JSON file.
    """
    
    def __init__(self, tracking_file: str = 'order_tracking.json'):
        """
        Initialize the order tracker.
        
        Args:
            tracking_file: Path to the JSON file storing order tracking data
        """
        # Store tracking file in project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.tracking_file = os.path.join(project_root, tracking_file)
        self._ensure_tracking_file()
        logger.info(f"OrderTracker initialized with tracking file: {self.tracking_file}")
    
    def _ensure_tracking_file(self):
        """Create tracking file if it doesn't exist."""
        if not os.path.exists(self.tracking_file):
            with open(self.tracking_file, 'w') as f:
                json.dump({}, f)
            logger.info(f"Created tracking file: {self.tracking_file}")
    
    def _load_tracking_data(self) -> Dict:
        """Load tracking data from file."""
        try:
            with open(self.tracking_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_tracking_data(self, data: Dict):
        """Save tracking data to file."""
        try:
            with open(self.tracking_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tracking data: {e}")
    
    def has_order_placed_today(self, symbol: Optional[str] = None) -> bool:
        """
        Check if an order has been placed today.
        
        Args:
            symbol: Optional symbol to check (SPXW or XSP). If None, checks for any order.
        
        Returns:
            bool: True if an order has been placed today, False otherwise
        """
        today_str = date.today().isoformat()
        tracking_data = self._load_tracking_data()
        
        if today_str not in tracking_data:
            return False
        
        today_orders = tracking_data[today_str]
        
        if symbol:
            symbol_upper = symbol.upper()
            # Check if there's an order for this specific symbol
            for order in today_orders:
                if order.get('symbol', '').upper() == symbol_upper:
                    logger.info(f"Order already placed today for {symbol_upper}")
                    return True
            return False
        else:
            # Check if there's any order for today
            has_orders = len(today_orders) > 0
            if has_orders:
                logger.info(f"Order(s) already placed today: {len(today_orders)} order(s)")
            return has_orders
    
    def record_order(
        self,
        order_id: str,
        symbol: str,
        bias: str,
        expiration_date: str,
        order_details: Optional[Dict] = None,
        underlying_price_at_fill: Optional[float] = None,
        underlying_symbol: Optional[str] = None
    ):
        """
        Record a placed order in the tracking file.
        
        Args:
            order_id: Order ID from broker
            symbol: Trading symbol (SPXW or XSP)
            bias: Trading bias (bullish or bearish)
            expiration_date: Expiration date (YYMMDD format)
            order_details: Optional full order details
            underlying_price_at_fill: Underlying price (SPX/XSP) at order placement time
            underlying_symbol: Underlying symbol ('SPX' or 'XSP')
        """
        today_str = date.today().isoformat()
        tracking_data = self._load_tracking_data()
        
        if today_str not in tracking_data:
            tracking_data[today_str] = []
        
        order_record = {
            'order_id': order_id,
            'symbol': symbol.upper(),
            'bias': bias.upper(),
            'expiration_date': expiration_date,
            'placed_at': datetime.now().isoformat(),
            'order_details': order_details,
            'underlying_price_at_fill': underlying_price_at_fill,
            'underlying_symbol': underlying_symbol
        }
        
        tracking_data[today_str].append(order_record)
        self._save_tracking_data(tracking_data)
        
        logger.info(f"Recorded order {order_id} for {symbol} ({bias}) in tracking file")
        if underlying_price_at_fill is not None:
            logger.info(f"  Underlying price at fill: ${underlying_price_at_fill:.2f} ({underlying_symbol})")
    
    def get_today_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get all orders placed today.
        
        Args:
            symbol: Optional symbol to filter by (SPXW or XSP)
        
        Returns:
            list: List of order records
        """
        today_str = date.today().isoformat()
        tracking_data = self._load_tracking_data()
        
        if today_str not in tracking_data:
            return []
        
        today_orders = tracking_data[today_str]
        
        if symbol:
            symbol_upper = symbol.upper()
            return [order for order in today_orders if order.get('symbol', '').upper() == symbol_upper]
        
        return today_orders
    
    def clear_old_data(self, days_to_keep: int = 30):
        """
        Clear tracking data older than specified days.
        
        Args:
            days_to_keep: Number of days of history to keep (default: 30)
        """
        from datetime import timedelta
        cutoff_date = date.today() - timedelta(days=days_to_keep)
        
        tracking_data = self._load_tracking_data()
        dates_to_remove = []
        
        for date_str in tracking_data.keys():
            try:
                order_date = datetime.fromisoformat(date_str).date()
                if order_date < cutoff_date:
                    dates_to_remove.append(date_str)
            except:
                dates_to_remove.append(date_str)
        
        for date_str in dates_to_remove:
            del tracking_data[date_str]
            logger.info(f"Removed old tracking data for {date_str}")
        
        if dates_to_remove:
            self._save_tracking_data(tracking_data)

