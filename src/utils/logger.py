"""Logging configuration."""
import logging
import sys
import pytz
from datetime import datetime


class ETFormatter(logging.Formatter):
    """Custom formatter that converts timestamps to Eastern Time."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.et_tz = pytz.timezone('US/Eastern')
    
    def formatTime(self, record, datefmt=None):
        """Convert timestamp to Eastern Time."""
        ct = datetime.fromtimestamp(record.created, tz=self.et_tz)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            s = ct.strftime(self.default_time_format)
        return s


def setup_logger(name: str = "spx_atm_bot", level: int = logging.INFO) -> logging.Logger:
    """
    Set up and configure logger with Eastern Time timestamps.
    
    Args:
        name: Logger name
        level: Logging level
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Create formatter with ET timezone
    formatter = ETFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S %Z'
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger

