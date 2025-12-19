"""Full integration test - runs bot logic without placing orders."""
import sys
import os
from datetime import datetime, time as dt_time
import pytz
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.strategy.market_data import MarketDataFetcher
from src.strategy.opening_range import OpeningRangeTracker
from src.strategy.strike_calculator import StrikeCalculator
from src.strategy.quote_monitor import QuoteMonitor
from src.strategy.position_sizing import PositionSizer
from src.accounts.account_manager import AccountManager
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("test_full_integration")
ET = pytz.timezone('US/Eastern')

def test_full_bot_logic():
    """Test full bot logic flow without placing orders."""
    print("=" * 70)
    print("FULL INTEGRATION TEST - Bot Logic (No Orders)")
    print("=" * 70)
    print()
    print(f"DRY_RUN: {Config.DRY_RUN}")
    print(f"ENABLE_LIVE_TRADING: {Config.ENABLE_LIVE_TRADING}")
    print(f"DAILY_RISK_PCT: {Config.DAILY_RISK_PCT * 100}%")
    print(f"MIN_CONTRACTS: {Config.MIN_CONTRACTS}")
    print(f"MAX_CONTRACTS: {Config.MAX_CONTRACTS}")
    print()
    
    today = datetime.now(ET)
    today_dt = ET.localize(datetime.combine(today.date(), datetime.min.time().replace(hour=9, minute=30)))
    
    print(f"Testing with date: {today_dt.strftime('%Y-%m-%d')}")
    print()
    
    try:
        # Step 1: Get Opening Range
        print("=" * 70)
        print("STEP 1: Getting Opening Range")
        print("=" * 70)
        or_tracker = OpeningRangeTracker()
        or_data = or_tracker.get_opening_range(today_dt)
        
        if not or_data:
            print("❌ Could not get Opening Range - exiting test")
            return
        
        print(f"✅ Opening Range retrieved:")
        print(f"  ORO: ${or_data['ORO']:.2f}")
        print(f"  ORH: ${or_data['ORH']:.2f}")
        print(f"  ORL: ${or_data['ORL']:.2f}")
        print(f"  ORC: ${or_data['ORC']:.2f}")
        print()
        
        # Step 2: Get account equity
        print("=" * 70)
        print("STEP 2: Getting Account Equity")
        print("=" * 70)
        account_mgr = AccountManager()
        account_equity = account_mgr.get_net_liquidity()
        print(f"✅ Account Equity: ${account_equity:,.2f}")
        print()
        
        # Step 3: Check Step A (Bullish OR)
        print("=" * 70)
        print("STEP 3: Checking Step A (Bullish OR)")
        print("=" * 70)
        orc = or_data.get('ORC', 0)
        oro = or_data.get('ORO', 0)
        
        if orc > oro:
            print(f"✅ Bullish OR detected: ORC (${orc:.2f}) > ORO (${oro:.2f})")
            print()
            
            # Set SPX_entry = ORC
            spx_entry = orc
            print(f"SPX_entry = ORC = ${spx_entry:.2f}")
            print()
            
            # Compute strikes ONCE
            k_short, k_long = StrikeCalculator.calculate_put_spread_strikes(spx_entry)
            print(f"PUT spread strikes (computed once):")
            print(f"  K_short: ${k_short:.2f}")
            print(f"  K_long: ${k_long:.2f}")
            print()
            
            # Monitor quotes (simulate - just check a few times)
            print("=" * 70)
            print("STEP 4: Monitoring Quotes (3 checks)")
            print("=" * 70)
            quote_monitor = QuoteMonitor()
            position_sizer = PositionSizer()
            
            for i in range(3):
                print(f"Check {i+1}:")
                credit_data = quote_monitor.get_spread_credit(
                    date=today_dt,
                    k_short=k_short,
                    k_long=k_long,
                    option_type='PUT'
                )
                
                if credit_data:
                    c_gross = credit_data['C_gross']
                    c_net = credit_data['C_net']
                    print(f"  [{datetime.now(ET).strftime('%H:%M:%S')}] C_gross=${c_gross:.2f}, C_net=${c_net:.2f}")
                    
                    if quote_monitor.meets_credit_threshold(credit_data):
                        print("  ✅ Credit threshold met!")
                        print()
                        
                        # Calculate position size
                        print("=" * 70)
                        print("STEP 5: Calculating Position Size")
                        print("=" * 70)
                        sizing = position_sizer.calculate_position_size(
                            account_equity=account_equity,
                            c_net=c_net,
                            max_qty_cap=Config.MAX_CONTRACTS
                        )
                        qty = sizing['qty']
                        print()
                        
                        # Show what order would be placed (but don't place it)
                        print("=" * 70)
                        print("STEP 6: Order That Would Be Placed (DRY RUN)")
                        print("=" * 70)
                        expiration_date = today_dt.strftime('%y%m%d')
                        order_price = c_gross
                        
                        print(f"Order Details:")
                        print(f"  Expiration: {expiration_date}")
                        print(f"  Option Type: PUT")
                        print(f"  K_short: ${k_short:.2f}")
                        print(f"  K_long: ${k_long:.2f}")
                        print(f"  Quantity: {qty}")
                        print(f"  Order Price: ${order_price:.2f}")
                        print(f"  C_gross: ${c_gross:.2f}")
                        print(f"  C_net: ${c_net:.2f}")
                        print()
                        print("🚫 DRY RUN - Order NOT placed")
                        print()
                        break
                    else:
                        print("  ⚠️  Credit threshold NOT met - would continue monitoring")
                else:
                    print("  ⚠️  Could not get credit data - would continue monitoring")
                
                if i < 2:
                    time.sleep(2)  # Short delay for testing
                print()
        else:
            print(f"ORC (${orc:.2f}) <= ORO (${oro:.2f}) - Not bullish, skipping Step A")
            print()
            print("Would proceed to Step B (Bearish ORL Breakout) in real bot")
            print()
        
        print("=" * 70)
        print("✅ Full integration test complete")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print()

if __name__ == '__main__':
    test_full_bot_logic()

