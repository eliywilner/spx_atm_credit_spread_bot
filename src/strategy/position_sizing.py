"""Position sizing calculator for configurable daily risk."""
import math
from typing import Dict, Optional
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class PositionSizer:
    """Calculates position size based on configurable daily risk percentage."""
    
    @staticmethod
    def calculate_position_size(
        account_equity: float,
        c_net: float,
        max_qty_cap: Optional[int] = None
    ) -> Dict:
        """
        Calculate position size based on configurable daily risk percentage.
        
        Args:
            account_equity: Account equity (net liquidity)
            c_net: Net credit per spread (at fill time)
            max_qty_cap: Optional maximum quantity cap (if None, uses Config.MAX_CONTRACTS)
        
        Returns:
            Dictionary with:
            - qty: Number of spreads
            - R_day: Daily risk budget
            - maxLossPerSpread: Maximum loss per spread (in dollars)
        """
        # Daily risk budget: Config.DAILY_RISK_PCT * account_equity
        r_day = Config.DAILY_RISK_PCT * account_equity
        
        # Max loss per spread: (spread_width - C_net) * 100
        max_loss_per_spread = (Config.SPREAD_WIDTH - c_net) * 100
        
        # Calculate quantity: floor(R_day / maxLossPerSpread)
        qty = math.floor(r_day / max_loss_per_spread) if max_loss_per_spread > 0 else 1
        
        # Apply minimum: at least MIN_CONTRACTS
        qty = max(Config.MIN_CONTRACTS, qty)
        
        # Apply maximum cap: use provided max_qty_cap or Config.MAX_CONTRACTS
        max_cap = max_qty_cap if max_qty_cap is not None else Config.MAX_CONTRACTS
        qty = min(qty, max_cap)
        
        result = {
            'qty': qty,
            'R_day': r_day,
            'maxLossPerSpread': max_loss_per_spread,
            'account_equity': account_equity
        }
        
        risk_pct = Config.DAILY_RISK_PCT * 100
        logger.info(f"Position sizing calculation:")
        logger.info(f"  Account Equity: ${account_equity:,.2f}")
        logger.info(f"  Daily Risk Budget ({risk_pct}%): ${r_day:,.2f}")
        logger.info(f"  C_net: ${c_net:.2f}")
        logger.info(f"  Max Loss per Spread: ${max_loss_per_spread:,.2f}")
        logger.info(f"  Min Contracts: {Config.MIN_CONTRACTS}")
        logger.info(f"  Max Contracts: {max_cap}")
        logger.info(f"  Recommended Quantity: {qty} spreads")
        
        return result

