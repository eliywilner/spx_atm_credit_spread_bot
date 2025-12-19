"""Test market data fetching (uses real API)."""
import sys
import os
from datetime import datetime
import pytz
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.strategy.market_data import MarketDataFetcher
from src.strategy.opening_range import OpeningRangeTracker
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("test_market_data")
ET = pytz.timezone('US/Eastern')

def test_get_opening_range():
    """Test getting Opening Range from real API."""
    print("=" * 70)
    print("TEST: Get Opening Range (Real API)")
    print("=" * 70)
    print()
    
    # Use today's date
    today = datetime.now(ET)
    today_dt = ET.localize(datetime.combine(today.date(), datetime.min.time().replace(hour=9, minute=30)))
    
    print(f"Testing with date: {today_dt.strftime('%Y-%m-%d')}")
    print()
    
    try:
        or_tracker = OpeningRangeTracker()
        or_data = or_tracker.get_opening_range(today_dt)
        
        if or_data:
            print("✅ Opening Range retrieved successfully:")
            print(f"  ORO: ${or_data['ORO']:.2f}")
            print(f"  ORH: ${or_data['ORH']:.2f}")
            print(f"  ORL: ${or_data['ORL']:.2f}")
            print(f"  ORC: ${or_data['ORC']:.2f}")
            print()
            
            # Validate OR data
            assert or_data['ORO'] > 0, "ORO must be positive"
            assert or_data['ORH'] >= or_data['ORO'], "ORH must be >= ORO"
            assert or_data['ORL'] <= or_data['ORO'], "ORL must be <= ORO"
            assert or_data['ORC'] > 0, "ORC must be positive"
            assert or_data['ORH'] >= or_data['ORL'], "ORH must be >= ORL"
            
            print("✅ OR data validation passed")
            print()
            
            # Check if bullish or bearish
            is_bullish = or_tracker.is_bullish_or(or_data)
            is_bearish = or_tracker.is_bearish_or(or_data)
            
            print(f"  Bullish OR: {is_bullish} (ORC > ORO)")
            print(f"  Bearish OR: {is_bearish} (ORC < ORO)")
            print()
            
        else:
            print("⚠️  Could not retrieve Opening Range (may be outside market hours)")
            print("   This is OK if testing outside trading hours")
            print()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print()
    
    print("=" * 70)
    print("✅ Market data test complete")
    print("=" * 70)

def test_get_30min_candles():
    """Test getting 30-minute candles from real API."""
    print("=" * 70)
    print("TEST: Get 30-Minute Candles (Real API)")
    print("=" * 70)
    print()
    
    today = datetime.now(ET)
    today_dt = ET.localize(datetime.combine(today.date(), datetime.min.time().replace(hour=9, minute=30)))
    
    print(f"Testing with date: {today_dt.strftime('%Y-%m-%d')}")
    print()
    
    try:
        market_data = MarketDataFetcher()
        
        # Test getting OR window candles
        candles = market_data.get_30min_candles(
            today_dt,
            start_hour=9,
            start_minute=30,
            end_hour=10,
            end_minute=0
        )
        
        if candles:
            print(f"✅ Retrieved {len(candles)} candle(s) for OR window")
            for i, candle in enumerate(candles):
                print(f"  Candle {i+1}:")
                print(f"    Open: ${candle.get('open', 0):.2f}")
                print(f"    High: ${candle.get('high', 0):.2f}")
                print(f"    Low: ${candle.get('low', 0):.2f}")
                print(f"    Close: ${candle.get('close', 0):.2f}")
            print()
        else:
            print("⚠️  No candles retrieved (may be outside market hours)")
            print()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print()
    
    print("=" * 70)
    print("✅ 30-minute candles test complete")
    print("=" * 70)

if __name__ == '__main__':
    test_get_30min_candles()
    print()
    test_get_opening_range()

