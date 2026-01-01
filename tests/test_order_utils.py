"""
Test order utility functions.
"""
import sys
import os
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.orders.order_utils import get_actual_fill_credit_from_order


class TestOrderUtils(unittest.TestCase):
    """Test order utility functions."""
    
    def test_get_actual_fill_credit_from_order_success(self):
        """Test extracting fill credit from a filled order."""
        # Sample order structure based on actual API response
        order = {
            'status': 'FILLED',
            'orderLegCollection': [
                {
                    'legId': 1,
                    'instruction': 'BUY_TO_OPEN',
                    'quantity': 1.0
                },
                {
                    'legId': 2,
                    'instruction': 'SELL_TO_OPEN',
                    'quantity': 1.0
                }
            ],
            'orderActivityCollection': [{
                'executionType': 'FILL',
                'executionLegs': [
                    {
                        'legId': 2,  # SELL leg
                        'price': 11.06,
                        'quantity': 1.0
                    },
                    {
                        'legId': 1,  # BUY leg
                        'price': 6.36,
                        'quantity': 1.0
                    }
                ]
            }]
        }
        
        result = get_actual_fill_credit_from_order(order)
        
        self.assertIsNotNone(result)
        self.assertEqual(result, 4.70)  # 11.06 - 6.36 = 4.70
        print("✅ Test passed: Successfully extracted fill credit")
    
    def test_get_actual_fill_credit_from_order_not_filled(self):
        """Test that function returns None for non-filled orders."""
        order = {
            'status': 'ACCEPTED',
            'orderLegCollection': [],
            'orderActivityCollection': []
        }
        
        result = get_actual_fill_credit_from_order(order)
        
        self.assertIsNone(result)
        print("✅ Test passed: Returns None for non-filled orders")
    
    def test_get_actual_fill_credit_from_order_no_activities(self):
        """Test that function returns None when no activities."""
        order = {
            'status': 'FILLED',
            'orderLegCollection': [
                {'legId': 1, 'instruction': 'BUY_TO_OPEN'},
                {'legId': 2, 'instruction': 'SELL_TO_OPEN'}
            ],
            'orderActivityCollection': []  # No activities
        }
        
        result = get_actual_fill_credit_from_order(order)
        
        self.assertIsNone(result)
        print("✅ Test passed: Returns None when no activities")
    
    def test_get_actual_fill_credit_from_order_put_spread(self):
        """Test with PUT spread (different leg order)."""
        order = {
            'status': 'FILLED',
            'orderLegCollection': [
                {
                    'legId': 1,
                    'instruction': 'SELL_TO_OPEN',  # Short leg
                    'quantity': 1.0
                },
                {
                    'legId': 2,
                    'instruction': 'BUY_TO_OPEN',  # Long leg
                    'quantity': 1.0
                }
            ],
            'orderActivityCollection': [{
                'executionType': 'FILL',
                'executionLegs': [
                    {
                        'legId': 1,  # SELL leg
                        'price': 13.30,
                        'quantity': 1.0
                    },
                    {
                        'legId': 2,  # BUY leg
                        'price': 8.55,
                        'quantity': 1.0
                    }
                ]
            }]
        }
        
        result = get_actual_fill_credit_from_order(order)
        
        self.assertIsNotNone(result)
        self.assertEqual(result, 4.75)  # 13.30 - 8.55 = 4.75
        print("✅ Test passed: PUT spread fill credit extracted correctly")
    
    def test_get_actual_fill_credit_from_order_multiple_contracts(self):
        """Test with multiple contracts."""
        order = {
            'status': 'FILLED',
            'orderLegCollection': [
                {
                    'legId': 1,
                    'instruction': 'BUY_TO_OPEN',
                    'quantity': 2.0
                },
                {
                    'legId': 2,
                    'instruction': 'SELL_TO_OPEN',
                    'quantity': 2.0
                }
            ],
            'orderActivityCollection': [{
                'executionType': 'FILL',
                'executionLegs': [
                    {
                        'legId': 2,  # SELL leg
                        'price': 11.06,
                        'quantity': 2.0
                    },
                    {
                        'legId': 1,  # BUY leg
                        'price': 6.36,
                        'quantity': 2.0
                    }
                ]
            }]
        }
        
        result = get_actual_fill_credit_from_order(order)
        
        self.assertIsNotNone(result)
        # Net credit per contract is still 4.70, but total is 9.40
        # However, function returns net credit (total), not per contract
        expected = (11.06 * 2.0) - (6.36 * 2.0)  # 22.12 - 12.72 = 9.40
        self.assertEqual(result, expected)
        print(f"✅ Test passed: Multiple contracts - net credit = ${result:.2f}")


if __name__ == '__main__':
    print("=" * 70)
    print("TEST: Order Utility Functions")
    print("=" * 70)
    print()
    unittest.main(argv=[''], exit=False, verbosity=2)

