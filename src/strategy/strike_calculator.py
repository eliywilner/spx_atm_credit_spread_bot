"""Strike price calculator for ATM credit spreads."""
import math
from typing import Tuple
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def round_to_5(x: float) -> float:
    """
    Round to nearest 5, with halves rounding up.
    
    Formula: round_to_5(x) = 5 * floor((x + 2.5)/5)
    
    Args:
        x: Price to round
    
    Returns:
        Rounded price (nearest 5)
    
    Examples:
        >>> round_to_5(5432.3)
        5430.0
        >>> round_to_5(5432.5)
        5435.0
        >>> round_to_5(5437.7)
        5440.0
    """
    return 5.0 * math.floor((x + 2.5) / 5.0)


class StrikeCalculator:
    """Calculates strike prices for ATM credit spreads."""
    
    SPREAD_WIDTH = 10.0  # Always 10 points wide
    
    @staticmethod
    def calculate_put_spread_strikes(spx_entry: float) -> Tuple[float, float]:
        """
        Calculate strikes for PUT credit spread (bullish trade).
        
        Args:
            spx_entry: SPX entry price
        
        Returns:
            Tuple of (K_short, K_long)
        """
        k_short = round_to_5(spx_entry)
        k_long = k_short - StrikeCalculator.SPREAD_WIDTH
        
        logger.debug(f"PUT spread strikes for SPX_entry=${spx_entry:.2f}: K_short=${k_short:.2f}, K_long=${k_long:.2f}")
        
        return (k_short, k_long)
    
    @staticmethod
    def calculate_call_spread_strikes(spx_entry: float) -> Tuple[float, float]:
        """
        Calculate strikes for CALL credit spread (bearish trade).
        
        Args:
            spx_entry: SPX entry price
        
        Returns:
            Tuple of (K_short, K_long)
        """
        k_short = round_to_5(spx_entry)
        k_long = k_short + StrikeCalculator.SPREAD_WIDTH
        
        logger.debug(f"CALL spread strikes for SPX_entry=${spx_entry:.2f}: K_short=${k_short:.2f}, K_long=${k_long:.2f}")
        
        return (k_short, k_long)

