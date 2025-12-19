"""Trade logger for SPX ATM Credit Spread Bot."""
import csv
import os
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path
import pytz
from src.utils.logger import setup_logger

logger = setup_logger(__name__)
ET = pytz.timezone('US/Eastern')

# CSV column definitions
CSV_COLUMNS = [
    'date',
    'setup',
    'trade_type',
    'trigger_time',
    'fill_time',
    'SPX_entry',
    'ORO',
    'ORH',
    'ORL',
    'ORC',
    'K_short',
    'K_long',
    'C_gross_fill',
    'S',
    'C_net_fill',
    'qty',
    'R_day',
    'maxLossPerSpread',
    'SPX_close',
    'settlement_value',
    'pnl_per_spread',
    'total_pnl',
    'equity_before',
    'equity_after',
    'order_id',
    'order_status'
]


class TradeLogger:
    """Logs trades to CSV file with optional S3 integration."""
    
    def __init__(
        self,
        csv_file_path: Optional[str] = None,
        s3_service: Optional[object] = None,
        s3_key: Optional[str] = None
    ):
        """
        Initialize trade logger.
        
        Args:
            csv_file_path: Path to CSV file. If None, uses 'tracking/trades.csv'
            s3_service: S3Service instance for S3 operations. If None, S3 operations are skipped.
            s3_key: S3 object key for CSV file. If None, uses 'trades.csv'
        """
        if csv_file_path is None:
            project_root = Path(__file__).parent.parent.parent
            csv_file_path = project_root / 'tracking' / 'trades.csv'
        
        self.csv_file_path = Path(csv_file_path)
        self.csv_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.s3_service = s3_service
        self.s3_key = s3_key or 'trades.csv'
        
        # Load from S3 if available
        if self.s3_service:
            self.load_from_s3()
        
        # Create CSV file with header if it doesn't exist
        if not self.csv_file_path.exists():
            with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                writer.writeheader()
        
        logger.info(f"TradeLogger initialized with file: {self.csv_file_path}")
        if self.s3_service:
            logger.info(f"S3 integration enabled with key: {self.s3_key}")
    
    def load_from_s3(self) -> bool:
        """
        Load CSV file from S3 at start of trading day.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.s3_service:
            return False
        
        try:
            if self.s3_service.file_exists(self.s3_key):
                logger.info(f"Loading trades CSV from S3: s3://{self.s3_service.bucket_name}/{self.s3_key}")
                return self.s3_service.download_file(self.s3_key, str(self.csv_file_path))
            else:
                logger.info("Trades CSV file not found in S3 (first run or new file)")
                return False
        except Exception as e:
            logger.warning(f"Failed to load trades CSV from S3: {e}")
            return False
    
    def save_to_s3(self) -> bool:
        """
        Save CSV file to S3 at end of trading day.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.s3_service:
            return False
        
        if not self.csv_file_path.exists():
            logger.warning("CSV file does not exist locally, cannot upload to S3")
            return False
        
        try:
            logger.info(f"Saving trades CSV to S3: s3://{self.s3_service.bucket_name}/{self.s3_key}")
            return self.s3_service.upload_file(str(self.csv_file_path), self.s3_key)
        except Exception as e:
            logger.warning(f"Failed to save trades CSV to S3: {e}")
            return False
    
    def log_trade(self, trade_data: Dict) -> bool:
        """
        Log a trade to CSV.
        
        Args:
            trade_data: Dictionary with trade data (should contain all CSV_COLUMNS)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure all columns are present
            row = {col: trade_data.get(col, '') for col in CSV_COLUMNS}
            
            # Append to CSV
            with open(self.csv_file_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                writer.writerow(row)
            
            logger.info(f"Trade logged to {self.csv_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging trade: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def format_value(self, value) -> str:
        """
        Format a value for CSV (handle None, floats, etc.).
        
        Args:
            value: Value to format
        
        Returns:
            Formatted string
        """
        if value is None:
            return ''
        elif isinstance(value, bool):
            return 'TRUE' if value else 'FALSE'
        elif isinstance(value, float):
            if value == 0.0:
                return '0'
            elif abs(value) < 0.01:
                return f"{value:.4f}"
            else:
                return f"{value:.2f}"
        elif isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return str(value)

