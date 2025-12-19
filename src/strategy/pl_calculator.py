"""P/L calculator for expiration settlement."""
from typing import Dict
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def clamp(x: float, min_val: float, max_val: float) -> float:
    """
    Clamp value between min and max.
    
    clamp(x, min, max) = min(max(x, min), max)
    
    Args:
        x: Value to clamp
        min_val: Minimum value
        max_val: Maximum value
    
    Returns:
        Clamped value
    """
    return min(max(x, min_val), max_val)


class PLCalculator:
    """Calculates P/L at expiration for credit spreads."""
    
    SPREAD_WIDTH = 10.0
    
    @staticmethod
    def calculate_put_spread_pl(
        k_short: float,
        spx_close: float,
        c_net_fill: float,
        qty: int
    ) -> Dict:
        """
        Calculate P/L for PUT credit spread at expiration.
        
        Args:
            k_short: Short strike
            spx_close: SPX closing price at 16:00
            c_net_fill: Net credit received at fill
            qty: Number of spreads
        
        Returns:
            Dictionary with settlement value, pnl_per_spread, total_pnl
        """
        # Settlement value: clamp(K_short - SPX_close, 0, 10)
        value = clamp(k_short - spx_close, 0, PLCalculator.SPREAD_WIDTH)
        
        # P/L per spread: (C_net_fill - value) * 100
        pnl_per_spread = (c_net_fill - value) * 100
        
        # Total P/L
        total_pnl = pnl_per_spread * qty
        
        result = {
            'settlement_value': value,
            'pnl_per_spread': pnl_per_spread,
            'total_pnl': total_pnl
        }
        
        logger.info(f"PUT spread P/L calculation:")
        logger.info(f"  K_short: ${k_short:.2f}")
        logger.info(f"  SPX_close: ${spx_close:.2f}")
        logger.info(f"  Settlement value: ${value:.2f}")
        logger.info(f"  C_net_fill: ${c_net_fill:.2f}")
        logger.info(f"  P/L per spread: ${pnl_per_spread:,.2f}")
        logger.info(f"  Total P/L ({qty} spreads): ${total_pnl:,.2f}")
        
        return result
    
    @staticmethod
    def calculate_call_spread_pl(
        k_short: float,
        spx_close: float,
        c_net_fill: float,
        qty: int
    ) -> Dict:
        """
        Calculate P/L for CALL credit spread at expiration.
        
        Args:
            k_short: Short strike
            spx_close: SPX closing price at 16:00
            c_net_fill: Net credit received at fill
            qty: Number of spreads
        
        Returns:
            Dictionary with settlement value, pnl_per_spread, total_pnl
        """
        # Settlement value: clamp(SPX_close - K_short, 0, 10)
        value = clamp(spx_close - k_short, 0, PLCalculator.SPREAD_WIDTH)
        
        # P/L per spread: (C_net_fill - value) * 100
        pnl_per_spread = (c_net_fill - value) * 100
        
        # Total P/L
        total_pnl = pnl_per_spread * qty
        
        result = {
            'settlement_value': value,
            'pnl_per_spread': pnl_per_spread,
            'total_pnl': total_pnl
        }
        
        logger.info(f"CALL spread P/L calculation:")
        logger.info(f"  K_short: ${k_short:.2f}")
        logger.info(f"  SPX_close: ${spx_close:.2f}")
        logger.info(f"  Settlement value: ${value:.2f}")
        logger.info(f"  C_net_fill: ${c_net_fill:.2f}")
        logger.info(f"  P/L per spread: ${pnl_per_spread:,.2f}")
        logger.info(f"  Total P/L ({qty} spreads): ${total_pnl:,.2f}")
        
        return result

