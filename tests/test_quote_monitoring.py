"""Test quote monitoring (uses real API, no orders placed)."""
import sys
import os
from datetime import datetime
import pytz
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.strategy.quote_monitor import QuoteMonitor
from src.strategy.strike_calculator import StrikeCalculator
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("test_quote_monitoring")
ET = pytz.timezone('US/Eastern')

def test_get_spread_credit():
    """Test getting spread credit from real API."""
    print("=" * 70)
    print("TEST: Get Spread Credit (Real API)")
    print("=" * 70)
    print()
    
    today = datetime.now(ET)
    today_dt = ET.localize(datetime.combine(today.date(), datetime.min.time().replace(hour=9, minute=30)))
    
    # Example strikes (you can adjust these)
    # Using current SPX price rounded to nearest 5
    spx_entry = 5430.0  # Example - adjust based on current market
    k_short, k_long = StrikeCalculator.calculate_put_spread_strikes(spx_entry)
    
    print(f"Testing PUT spread credit:")
    print(f"  Date: {today_dt.strftime('%Y-%m-%d')}")
    print(f"  SPX_entry: ${spx_entry:.2f}")
    print(f"  K_short: ${k_short:.2f}")
    print(f"  K_long: ${k_long:.2f}")
    print()
    
    try:
        quote_monitor = QuoteMonitor()
        credit_data = quote_monitor.get_spread_credit(
            date=today_dt,
            k_short=k_short,
            k_long=k_long,
            option_type='PUT'
        )
        
        if credit_data:
            print("✅ Spread credit retrieved:")
            print(f"  Short leg mid: ${credit_data['short_mid']:.2f}")
            print(f"  Long leg mid: ${credit_data['long_mid']:.2f}")
            print(f"  C_gross: ${credit_data['C_gross']:.2f}")
            print(f"  C_net: ${credit_data['C_net']:.2f} (C_gross - ${Config.SLIPPAGE_BUFFER:.2f})")
            print()
            
            # Check credit threshold
            meets_threshold = quote_monitor.meets_credit_threshold(credit_data)
            print(f"  Meets threshold (C_net >= ${Config.MIN_NET_CREDIT:.2f}): {meets_threshold}")
            print()
            
            if meets_threshold:
                print("  ✅ Credit threshold met - would proceed to order placement (in dry-run)")
            else:
                print("  ⚠️  Credit threshold NOT met - would continue monitoring")
            print()
        else:
            print("⚠️  Could not get spread credit (options may not be available or outside market hours)")
            print()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print()
    
    print("=" * 70)
    print("✅ Quote monitoring test complete")
    print("=" * 70)

def test_quote_monitoring_loop():
    """Test quote monitoring loop (simulates real monitoring)."""
    print("=" * 70)
    print("TEST: Quote Monitoring Loop (Real API, 3 checks)")
    print("=" * 70)
    print()
    
    today = datetime.now(ET)
    today_dt = ET.localize(datetime.combine(today.date(), datetime.min.time().replace(hour=9, minute=30)))
    
    spx_entry = 5430.0  # Example - adjust based on current market
    k_short, k_long = StrikeCalculator.calculate_put_spread_strikes(spx_entry)
    
    print(f"Monitoring PUT spread:")
    print(f"  K_short: ${k_short:.2f}, K_long: ${k_long:.2f}")
    print(f"  Checking every {Config.QUOTE_MONITOR_INTERVAL} seconds")
    print(f"  Will check 3 times (simulated)")
    print()
    
    try:
        quote_monitor = QuoteMonitor()
        
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
                    print("  (In real bot, would place order here - but we're testing)")
                    break
            else:
                print("  ⚠️  Could not get credit data")
            
            if i < 2:  # Don't sleep after last check
                time.sleep(Config.QUOTE_MONITOR_INTERVAL)
            print()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print()
    
    print("=" * 70)
    print("✅ Quote monitoring loop test complete")
    print("=" * 70)

if __name__ == '__main__':
    test_get_spread_credit()
    print()
    test_quote_monitoring_loop()

