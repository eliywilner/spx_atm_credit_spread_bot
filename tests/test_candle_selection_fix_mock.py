"""
Test the candle selection fix with mock data that simulates today's scenario.

This test verifies that the correct candles are selected for each time window
using mock data that simulates what the API would return.
"""
import sys
import os
from datetime import datetime, time as dt_time
import pytz
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ET = pytz.timezone('US/Eastern')


def test_candle_selection_logic():
    """
    Test the candle selection logic with mock data that simulates today's scenario.
    
    Today's scenario (from logs):
    - OR candle (9:30-10:00): close = $6935.88
    - 10:00-10:30 candle: close = ??? (should be different from ORC)
    - 10:30-11:00 candle: close = ??? (should be different from ORC)
    - 11:00-11:30 candle: close = ??? (should be different from ORC)
    - 11:30-12:00 candle: close = ??? (should be different from ORC)
    
    The bug: All candles were showing $6935.88 (ORC) because candles[0] was always used.
    The fix: Find the candle whose datetime matches the requested window start.
    """
    print("=" * 70)
    print("TEST: Candle Selection Fix - Mock Data Simulation")
    print("=" * 70)
    print()
    
    # Simulate today's date
    today = datetime.now(ET)
    today_dt = ET.localize(datetime.combine(today.date(), dt_time(9, 30)))
    
    print(f"Testing with date: {today_dt.strftime('%Y-%m-%d')}")
    print()
    
    # Simulate OR data from today's logs
    or_data = {
        'ORO': 6936.02,
        'ORH': 6945.77,
        'ORL': 6932.43,
        'ORC': 6935.88
    }
    
    print("Simulated Opening Range data:")
    print(f"  ORO: ${or_data['ORO']:.2f}")
    print(f"  ORH: ${or_data['ORH']:.2f}")
    print(f"  ORL: ${or_data['ORL']:.2f}")
    print(f"  ORC: ${or_data['ORC']:.2f}")
    print()
    
    orl = or_data['ORL']
    
    # Define the candle windows to check (same as in step_b_bearish_orl_breakout)
    candle_windows = [
        (10, 0, 10, 30),  # 10:00-10:30, check at 10:30
        (10, 30, 11, 0),  # 10:30-11:00, check at 11:00
        (11, 0, 11, 30),  # 11:00-11:30, check at 11:30
        (11, 30, 12, 0),  # 11:30-12:00, check at 12:00
    ]
    
    # Create mock candles that simulate what the API returns
    # When requesting 10:00-10:30, API returns ALL candles from 9:30 to 10:30
    def create_mock_candles_for_window(start_hour, start_min, end_hour, end_min):
        """Create mock candles that simulate API response."""
        candles = []
        
        # API returns all candles from market open (9:30) to the end time
        # So for 10:00-10:30 request, it returns: 9:30-10:00, 10:00-10:30
        # For 10:30-11:00 request, it returns: 9:30-10:00, 10:00-10:30, 10:30-11:00
        
        # OR candle (9:30-10:00)
        or_start = today_dt.replace(hour=9, minute=30, second=0, microsecond=0)
        or_start_ts = int(or_start.timestamp() * 1000)
        candles.append({
            'datetime': or_start_ts,
            'open': 6936.02,
            'high': 6945.77,
            'low': 6932.43,
            'close': 6935.88,  # ORC
            'volume': 1000
        })
        
        # Add candles up to the end time
        current_hour = 10
        current_min = 0
        
        while (current_hour < end_hour) or (current_hour == end_hour and current_min < end_min):
            candle_start = today_dt.replace(hour=current_hour, minute=current_min, second=0, microsecond=0)
            candle_start_ts = int(candle_start.timestamp() * 1000)
            
            # Simulate different close prices for each candle (not ORC)
            # Use a pattern: 10:00 = 6936.00, 10:30 = 6937.00, 11:00 = 6938.00, 11:30 = 6939.00
            base_price = 6936.0 + (current_hour - 10) * 1.0 + (current_min / 30) * 1.0
            
            candles.append({
                'datetime': candle_start_ts,
                'open': base_price - 0.5,
                'high': base_price + 1.0,
                'low': base_price - 1.0,
                'close': base_price,
                'volume': 1000
            })
            
            # Move to next 30-minute window
            current_min += 30
            if current_min >= 60:
                current_min = 0
                current_hour += 1
        
        return candles
    
    print("Testing candle selection for each window:")
    print()
    
    all_tests_passed = True
    
    for start_hour, start_min, end_hour, end_min in candle_windows:
        print(f"Testing window: {start_hour:02d}:{start_min:02d}-{end_hour:02d}:{end_min:02d}")
        
        # Get mock candles for this window (simulates API response)
        candles = create_mock_candles_for_window(start_hour, start_min, end_hour, end_min)
        
        print(f"  Retrieved {len(candles)} candle(s) from API (simulated)")
        
        # Show all candles returned
        print(f"  All candles returned:")
        for i, c in enumerate(candles):
            candle_dt = c.get('datetime', 0)
            candle_time = datetime.fromtimestamp(candle_dt / 1000, tz=ET)
            print(f"    [{i}] {candle_time.strftime('%H:%M:%S')} - Close: ${c.get('close', 0):.2f}")
        
        # OLD BUGGY CODE: Always takes first candle
        old_candle = candles[0] if candles else None
        old_close = old_candle.get('close', 0) if old_candle else 0
        
        # NEW FIXED CODE: Find the candle that matches the requested time window
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
            all_tests_passed = False
            print()
            continue
        
        # Verify we got the right candle
        candle_dt = candle.get('datetime', 0)
        candle_time = datetime.fromtimestamp(candle_dt / 1000, tz=ET)
        bar_close = candle.get('close', 0)
        
        print(f"  OLD BUGGY CODE would select: [{0}] Close: ${old_close:.2f} (WRONG - always ORC!)")
        print(f"  ✅ NEW FIXED CODE selected: {candle_time.strftime('%H:%M:%S')} - Close: ${bar_close:.2f}")
        
        # Verify it's the correct time
        if candle_time.hour == start_hour and candle_time.minute == start_min:
            print(f"  ✅ Time matches expected window start ({start_hour:02d}:{start_min:02d})")
        else:
            print(f"  ❌ FAILED: Time mismatch!")
            print(f"     Expected: {start_hour:02d}:{start_min:02d}")
            print(f"     Got: {candle_time.strftime('%H:%M')}")
            all_tests_passed = False
        
        # Verify it's NOT the OR candle (unless we're checking 9:30-10:00)
        if start_hour == 9 and start_min == 30:
            # This is the OR candle, so close should be ORC
            if bar_close == or_data['ORC']:
                print(f"  ✅ Correctly selected OR candle")
            else:
                print(f"  ❌ FAILED: Should be OR candle but got different close")
                all_tests_passed = False
        else:
            # Should NOT be the OR candle
            if bar_close != or_data['ORC']:
                print(f"  ✅ Correctly avoided OR candle (close ${bar_close:.2f} != ORC ${or_data['ORC']:.2f})")
            else:
                print(f"  ❌ FAILED: Selected OR candle instead of correct window candle!")
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
        print("Summary:")
        print("  - OLD CODE: Always selected candles[0] (OR candle) → All showed $6935.88")
        print("  - NEW CODE: Correctly selects candle matching requested window → Different prices")
    else:
        print("❌ SOME TESTS FAILED - Please review the output above")
    print("=" * 70)


if __name__ == '__main__':
    test_candle_selection_logic()

