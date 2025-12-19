"""Test strike calculation logic."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.strategy.strike_calculator import StrikeCalculator, round_to_5

def test_round_to_5():
    """Test round_to_5 function."""
    print("=" * 70)
    print("TEST: round_to_5() Function")
    print("=" * 70)
    print()
    
    test_cases = [
        (5432.3, 5430.0),
        (5432.5, 5435.0),  # Halves round up
        (5437.7, 5440.0),
        (5430.0, 5430.0),
        (5435.0, 5435.0),
        (5432.49, 5430.0),
        (5432.51, 5435.0),
    ]
    
    for input_val, expected in test_cases:
        result = round_to_5(input_val)
        status = "✅" if result == expected else "❌"
        print(f"{status} round_to_5({input_val}) = {result} (expected {expected})")
        assert result == expected, f"round_to_5({input_val}) = {result}, expected {expected}"
    
    print()
    print("=" * 70)
    print("✅ All round_to_5 tests passed!")
    print("=" * 70)
    print()

def test_put_spread_strikes():
    """Test PUT spread strike calculation."""
    print("=" * 70)
    print("TEST: PUT Spread Strike Calculation")
    print("=" * 70)
    print()
    
    test_cases = [
        (5432.3, 5430.0, 5420.0),  # K_short = round_to_5(5432.3) = 5430, K_long = 5430 - 10 = 5420
        (5432.5, 5435.0, 5425.0),  # K_short = round_to_5(5432.5) = 5435, K_long = 5435 - 10 = 5425
        (5437.7, 5440.0, 5430.0),  # K_short = round_to_5(5437.7) = 5440, K_long = 5440 - 10 = 5430
    ]
    
    for spx_entry, expected_k_short, expected_k_long in test_cases:
        k_short, k_long = StrikeCalculator.calculate_put_spread_strikes(spx_entry)
        status = "✅" if (k_short == expected_k_short and k_long == expected_k_long) else "❌"
        print(f"{status} SPX_entry=${spx_entry:.2f} → K_short=${k_short:.2f}, K_long=${k_long:.2f}")
        print(f"   Expected: K_short=${expected_k_short:.2f}, K_long=${expected_k_long:.2f}")
        assert k_short == expected_k_short, f"K_short mismatch: {k_short} != {expected_k_short}"
        assert k_long == expected_k_long, f"K_long mismatch: {k_long} != {expected_k_long}"
        assert k_long == k_short - 10, f"Spread width must be 10: {k_short} - {k_long} != 10"
    
    print()
    print("=" * 70)
    print("✅ All PUT spread strike tests passed!")
    print("=" * 70)
    print()

def test_call_spread_strikes():
    """Test CALL spread strike calculation."""
    print("=" * 70)
    print("TEST: CALL Spread Strike Calculation")
    print("=" * 70)
    print()
    
    test_cases = [
        (5432.3, 5430.0, 5440.0),  # K_short = round_to_5(5432.3) = 5430, K_long = 5430 + 10 = 5440
        (5432.5, 5435.0, 5445.0),  # K_short = round_to_5(5432.5) = 5435, K_long = 5435 + 10 = 5445
        (5437.7, 5440.0, 5450.0),  # K_short = round_to_5(5437.7) = 5440, K_long = 5440 + 10 = 5450
    ]
    
    for spx_entry, expected_k_short, expected_k_long in test_cases:
        k_short, k_long = StrikeCalculator.calculate_call_spread_strikes(spx_entry)
        status = "✅" if (k_short == expected_k_short and k_long == expected_k_long) else "❌"
        print(f"{status} SPX_entry=${spx_entry:.2f} → K_short=${k_short:.2f}, K_long=${k_long:.2f}")
        print(f"   Expected: K_short=${expected_k_short:.2f}, K_long=${expected_k_long:.2f}")
        assert k_short == expected_k_short, f"K_short mismatch: {k_short} != {expected_k_short}"
        assert k_long == expected_k_long, f"K_long mismatch: {k_long} != {expected_k_long}"
        assert k_long == k_short + 10, f"Spread width must be 10: {k_long} - {k_short} != 10"
    
    print()
    print("=" * 70)
    print("✅ All CALL spread strike tests passed!")
    print("=" * 70)

if __name__ == '__main__':
    test_round_to_5()
    test_put_spread_strikes()
    test_call_spread_strikes()

