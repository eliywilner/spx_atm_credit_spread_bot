"""Logging configuration."""
import logging
import sys
import os
import pytz
from pathlib import Path
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
    Logs to both console (stdout) and file (logs/bot_YYYY-MM-DD.log).
    
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
    
    # Create formatter with ET timezone
    formatter = ETFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S %Z'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler (logs to logs/bot_YYYY-MM-DD.log)
    try:
        # Get project root (assume this file is in src/utils/)
        project_root = Path(__file__).parent.parent.parent
        logs_dir = project_root / 'logs'
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log file with today's date
        today = datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d')
        log_file = logs_dir / f'bot_{today}.log'
        
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # If file logging fails, continue with console logging only
        logger.warning(f"Failed to set up file logging: {e}")
    
    return logger

