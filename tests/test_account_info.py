"""Test account information retrieval (uses real API)."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.accounts.account_manager import AccountManager
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("test_account_info")

def test_get_account_info():
    """Test getting account information from real API."""
    print("=" * 70)
    print("TEST: Get Account Information (Real API)")
    print("=" * 70)
    print()
    
    try:
        account_mgr = AccountManager()
        
        # Get net liquidity
        print("Getting account net liquidity...")
        net_liquidity = account_mgr.get_net_liquidity()
        print(f"✅ Net Liquidity: ${net_liquidity:,.2f}")
        print()
        
        # Get option buying power
        print("Getting option buying power...")
        option_buying_power = account_mgr.get_option_buying_power()
        print(f"✅ Option Buying Power: ${option_buying_power:,.2f}")
        print()
        
        # Calculate what position sizing would use
        print("Position Sizing Preview:")
        print(f"  Account Equity (Net Liquidity): ${net_liquidity:,.2f}")
        print(f"  Daily Risk %: {Config.DAILY_RISK_PCT * 100}%")
        print(f"  Daily Risk Budget: ${Config.DAILY_RISK_PCT * net_liquidity:,.2f}")
        print(f"  Min Contracts: {Config.MIN_CONTRACTS}")
        print(f"  Max Contracts: {Config.MAX_CONTRACTS}")
        print()
        
        # Example calculation with C_net = 4.60
        example_c_net = 4.60
        max_loss_per_spread = (Config.SPREAD_WIDTH - example_c_net) * 100
        r_day = Config.DAILY_RISK_PCT * net_liquidity
        example_qty = int(r_day / max_loss_per_spread)
        example_qty = max(Config.MIN_CONTRACTS, min(example_qty, Config.MAX_CONTRACTS))
        
        print(f"Example calculation (C_net = ${example_c_net:.2f}):")
        print(f"  Max Loss per Spread: ${max_loss_per_spread:,.2f}")
        print(f"  Recommended Quantity: {example_qty} contracts")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print()
    
    print("=" * 70)
    print("✅ Account info test complete")
    print("=" * 70)

if __name__ == '__main__':
    test_get_account_info()

