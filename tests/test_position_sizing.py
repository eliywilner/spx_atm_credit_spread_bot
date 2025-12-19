"""Test position sizing calculations."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.strategy.position_sizing import PositionSizer
from src.config import Config

def test_position_sizing():
    """Test position sizing with various scenarios."""
    print("=" * 70)
    print("TEST: Position Sizing Calculations")
    print("=" * 70)
    print()
    
    # Test 1: $15,000 account
    print("Test 1: $15,000 account, C_net = $4.60")
    result = PositionSizer.calculate_position_size(
        account_equity=15000,
        c_net=4.60
    )
    print(f"  Expected: 1 contract")
    print(f"  Got: {result['qty']} contracts")
    print(f"  R_day: ${result['R_day']:,.2f}")
    print(f"  maxLossPerSpread: ${result['maxLossPerSpread']:,.2f}")
    assert result['qty'] == 1, f"Expected 1, got {result['qty']}"
    print("  ✅ PASS")
    print()
    
    # Test 2: $100,000 account
    print("Test 2: $100,000 account, C_net = $4.60")
    result = PositionSizer.calculate_position_size(
        account_equity=100000,
        c_net=4.60
    )
    print(f"  Expected: 5 contracts")
    print(f"  Got: {result['qty']} contracts")
    print(f"  R_day: ${result['R_day']:,.2f}")
    print(f"  maxLossPerSpread: ${result['maxLossPerSpread']:,.2f}")
    assert result['qty'] == 5, f"Expected 5, got {result['qty']}"
    print("  ✅ PASS")
    print()
    
    # Test 3: $1,000,000 account (max cap hit)
    print("Test 3: $1,000,000 account, C_net = $4.60 (max cap test)")
    result = PositionSizer.calculate_position_size(
        account_equity=1000000,
        c_net=4.60
    )
    print(f"  Expected: {Config.MAX_CONTRACTS} contracts (max cap)")
    print(f"  Got: {result['qty']} contracts")
    print(f"  R_day: ${result['R_day']:,.2f}")
    print(f"  maxLossPerSpread: ${result['maxLossPerSpread']:,.2f}")
    assert result['qty'] == Config.MAX_CONTRACTS, f"Expected {Config.MAX_CONTRACTS}, got {result['qty']}"
    print("  ✅ PASS")
    print()
    
    # Test 4: High C_net (lower max loss)
    print("Test 4: $100,000 account, C_net = $9.00 (high credit)")
    result = PositionSizer.calculate_position_size(
        account_equity=100000,
        c_net=9.00
    )
    print(f"  Got: {result['qty']} contracts")
    print(f"  R_day: ${result['R_day']:,.2f}")
    print(f"  maxLossPerSpread: ${result['maxLossPerSpread']:,.2f}")
    print("  ✅ PASS")
    print()
    
    print("=" * 70)
    print("✅ All position sizing tests passed!")
    print("=" * 70)

if __name__ == '__main__':
    test_position_sizing()

