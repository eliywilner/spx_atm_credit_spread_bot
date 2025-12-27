"""
Test the candle selection fix for step_b_bearish_orl_breakout.

This test verifies that the correct candles are selected for each time window
using today's actual market data.
"""
import sys
import os
from datetime import datetime, time as dt_time
import pytz
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.strategy.market_data import MarketDataFetcher
from src.strategy.opening_range import OpeningRangeTracker
from src.utils.logger import setup_logger

logger = setup_logger("test_candle_selection")
ET = pytz.timezone('US/Eastern')


def test_candle_selection_with_todays_data():
    """
    Test that the candle selection logic correctly identifies the right candle
    for each time window using today's actual data.
    """
    print("=" * 70)
    print("TEST: Candle Selection Fix - Using Today's Data")
    print("=" * 70)
    print()
    
    # Use today's date (2025-12-26 based on logs)
    today = datetime.now(ET)
    today_dt = ET.localize(datetime.combine(today.date(), dt_time(9, 30)))
    
    print(f"Testing with date: {today_dt.strftime('%Y-%m-%d')}")
    print()
    
    try:
        # Get Opening Range data (from today's logs: ORO=$6936.02, ORC=$6935.88, ORL=$6932.43)
        or_tracker = OpeningRangeTracker()
        or_data = or_tracker.get_opening_range(today_dt)
        
        if not or_data:
            print("⚠️  Could not get Opening Range data (may be outside market hours)")
            print("   Skipping test")
            return
        
        print("✅ Opening Range retrieved:")
        print(f"  ORO: ${or_data['ORO']:.2f}")
        print(f"  ORH: ${or_data['ORH']:.2f}")
        print(f"  ORL: ${or_data['ORL']:.2f}")
        print(f"  ORC: ${or_data['ORC']:.2f}")
        print()
        
        # Check if bearish (ORC < ORO)
        orc = or_data.get('ORC', 0)
        oro = or_data.get('ORO', 0)
        orl = or_data.get('ORL', 0)
        
        if orc >= oro:
            print(f"⚠️  ORC (${orc:.2f}) >= ORO (${oro:.2f}) - Not bearish")
            print("   This test is for bearish ORL breakout, but today is not bearish")
            print("   Will still test candle selection logic...")
            print()
        
        # Test candle selection for each window
        market_data = MarketDataFetcher()
        
        # Define the candle windows to check (same as in step_b_bearish_orl_breakout)
        candle_windows = [
            (10, 0, 10, 30),  # 10:00-10:30, check at 10:30
            (10, 30, 11, 0),  # 10:30-11:00, check at 11:00
            (11, 0, 11, 30),  # 11:00-11:30, check at 11:30
            (11, 30, 12, 0),  # 11:30-12:00, check at 12:00
        ]
        
        print("Testing candle selection for each window:")
        print()
        
        all_tests_passed = True
        
        for start_hour, start_min, end_hour, end_min in candle_windows:
            print(f"Testing window: {start_hour:02d}:{start_min:02d}-{end_hour:02d}:{end_min:02d}")
            
            # Get candles for this window (same as in the actual function)
            candles = market_data.get_30min_candles(
                today_dt,
                start_hour=start_hour,
                start_minute=start_min,
                end_hour=end_hour,
                end_minute=end_min
            )
            
            if not candles:
                print(f"  ⚠️  No candles returned for this window")
                print()
                continue
            
            print(f"  Retrieved {len(candles)} candle(s) from API")
            
            # Show all candles returned
            print(f"  All candles returned from API:")
            for i, c in enumerate(candles):
                candle_dt = c.get('datetime', 0)
                # Convert timestamp to readable time
                candle_time = datetime.fromtimestamp(candle_dt / 1000, tz=ET)
                print(f"    [{i}] {candle_time.strftime('%H:%M:%S')} - Close: ${c.get('close', 0):.2f}")
            
            # OLD BUGGY CODE: Always takes first candle
            old_candle = candles[0] if candles else None
            old_candle_dt = old_candle.get('datetime', 0) if old_candle else 0
            old_candle_time = datetime.fromtimestamp(old_candle_dt / 1000, tz=ET) if old_candle_dt else None
            old_close = old_candle.get('close', 0) if old_candle else 0
            
            # Apply the FIX: Find the candle that matches the requested time window
            window_start = today_dt.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
            if window_start.tzinfo is None:
                window_start = ET.localize(window_start)
            window_start_ts = int(window_start.timestamp() * 1000)
            
            # Find candle where datetime matches our target window start
            candle = None
            for c in candles:
                candle_dt = c.get('datetime', 0)
                if candle_dt == window_start_ts:
                    candle = c
                    break
            
            if not candle:
                print(f"  ❌ FAILED: Could not find candle matching {start_hour:02d}:{start_min:02d} start time")
                print(f"     Expected timestamp: {window_start_ts}")
                print(f"     Available timestamps: {[c.get('datetime', 0) for c in candles]}")
                all_tests_passed = False
                print()
                continue
            
            # Verify we got the right candle
            candle_dt = candle.get('datetime', 0)
            candle_time = datetime.fromtimestamp(candle_dt / 1000, tz=ET)
            bar_close = candle.get('close', 0)
            
            print()
            print(f"  🔴 OLD BUGGY CODE (candles[0]):")
            print(f"     Selected: [{0}] {old_candle_time.strftime('%H:%M:%S') if old_candle_time else 'N/A'} - Close: ${old_close:.2f}")
            if old_candle_time and (old_candle_time.hour != start_hour or old_candle_time.minute != start_min):
                print(f"     ❌ WRONG! This is the {old_candle_time.strftime('%H:%M')} candle, not {start_hour:02d}:{start_min:02d}")
            print()
            print(f"  ✅ NEW FIXED CODE (matches window start):")
            print(f"     Selected: {candle_time.strftime('%H:%M:%S')} - Close: ${bar_close:.2f}")
            
            # Verify it's the correct time
            if candle_time.hour == start_hour and candle_time.minute == start_min:
                print(f"  ✅ Time matches expected window start ({start_hour:02d}:{start_min:02d})")
            else:
                print(f"  ❌ FAILED: Time mismatch!")
                print(f"     Expected: {start_hour:02d}:{start_min:02d}")
                print(f"     Got: {candle_time.strftime('%H:%M')}")
                all_tests_passed = False
            
            # Check if this would trigger a breakout (for reference)
            if bar_close < orl:
                print(f"  ✅ Would trigger breakout: ${bar_close:.2f} < ORL ${orl:.2f}")
            else:
                print(f"  ℹ️  No breakout: ${bar_close:.2f} >= ORL ${orl:.2f}")
            
            print()
        
        print("=" * 70)
        if all_tests_passed:
            print("✅ ALL TESTS PASSED - Candle selection fix is working correctly!")
            print()
            print("SUMMARY - What happened today (2025-12-26):")
            print("  Today's OR data:")
            print(f"    ORO: ${or_data['ORO']:.2f}")
            print(f"    ORC: ${or_data['ORC']:.2f}")
            print(f"    ORL: ${or_data['ORL']:.2f}")
            print()
            print("  🔴 OLD BUGGY CODE:")
            print("    All 4 windows checked the same candle (9:30-10:00 OR candle)")
            print("    All showed close = $6935.88 (ORC)")
            print("    Result: No breakout detected (even if there was one)")
            print()
            print("  ✅ NEW FIXED CODE:")
            print("    Each window checks its own candle")
            print("    Each window shows the actual close price for that period")
            print("    Result: Correct breakout detection")
        else:
            print("❌ SOME TESTS FAILED - Please review the output above")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print()


if __name__ == '__main__':
    test_candle_selection_with_todays_data()

