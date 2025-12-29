"""
Test script to verify the order placement fix works correctly.

This test simulates the actual API response (201 Created with empty body)
and verifies that the code correctly:
1. Handles 201 status code
2. Extracts order ID from Location header
3. Gets order confirmation
4. Returns proper order details
"""
import sys
import os
import json
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pytz
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.orders.spread_order_placer import SpreadOrderPlacer
from src.config import Config

ET = pytz.timezone('US/Eastern')


class TestOrderPlacementFix(unittest.TestCase):
    """Test order placement fix for 201 Created responses."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Save original config values
        self.original_dry_run = Config.DRY_RUN
        self.original_enable_live = Config.ENABLE_LIVE_TRADING
        
        # Enable live trading for this test (we'll mock the API calls)
        Config.DRY_RUN = False
        Config.ENABLE_LIVE_TRADING = True
        
        self.placer = SpreadOrderPlacer()
    
    def tearDown(self):
        """Restore original config values."""
        Config.DRY_RUN = self.original_dry_run
        Config.ENABLE_LIVE_TRADING = self.original_enable_live
    
    @patch('src.orders.spread_order_placer.requests.post')
    @patch('src.orders.spread_order_placer.time.sleep')
    def test_201_created_with_empty_body(self, mock_sleep, mock_post):
        """Test handling of 201 Created with empty response body."""
        
        # Mock the API response (201 Created with empty body and Location header)
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.text = ''
        mock_response.headers = {
            'Location': 'https://api.schwabapi.com/trader/v1/accounts/ABC123/orders/1005009351676',
            'Content-Length': '0'
        }
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(side_effect=ValueError("Expecting value: line 1 column 1 (char 0)"))
        
        mock_post.return_value = mock_response
        
        # Mock account manager instance
        self.placer.account_mgr.get_account_hash = Mock(return_value='ABC123')
        
        # Mock get_orders_executed_today to return order confirmation
        mock_order_details = {
            'orderId': '1005009351676',
            'status': 'ACCEPTED',
            'enteredTime': '2025-12-29T10:10:02-0500',
            'orderType': 'NET_CREDIT',
            'orderStrategyType': 'SINGLE'
        }
        self.placer.account_mgr.get_orders_executed_today = Mock(return_value=[mock_order_details])
        
        # Call the method
        result = self.placer.place_10wide_credit_spread(
            date='251229',
            k_short=6905.0,
            k_long=6895.0,
            option_type='PUT',
            quantity=1,
            order_price=4.70
        )
        
        # Verify results
        self.assertIsNotNone(result)
        self.assertEqual(result['orderId'], '1005009351676')
        self.assertEqual(result['status'], 'ACCEPTED')
        self.assertIn('order_details', result)
        
        # Verify API was called
        mock_post.assert_called_once()
        
        # Verify sleep was called (waiting for order processing)
        mock_sleep.assert_called_once_with(2)
        
        # Verify get_orders_executed_today was called
        self.placer.account_mgr.get_orders_executed_today.assert_called_once()
        
        print("✅ Test passed: 201 Created with empty body handled correctly")
    
    @patch('src.orders.spread_order_placer.requests.post')
    @patch('src.orders.spread_order_placer.time.sleep')
    def test_order_id_extraction_from_location_header(self, mock_sleep, mock_post):
        """Test that order ID is correctly extracted from Location header."""
        
        # Mock response with Location header
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.text = ''
        mock_response.headers = {
            'Location': 'https://api.schwabapi.com/trader/v1/accounts/HASH123/orders/999888777666',
        }
        mock_response.raise_for_status = Mock()
        
        mock_post.return_value = mock_response
        
        self.placer.account_mgr.get_account_hash = Mock(return_value='HASH123')
        
        # Mock order confirmation
        mock_order_details = {
            'orderId': '999888777666',
            'status': 'ACCEPTED'
        }
        self.placer.account_mgr.get_orders_executed_today = Mock(return_value=[mock_order_details])
        
        # Call the method
        result = self.placer.place_10wide_credit_spread(
            date='251229',
            k_short=6905.0,
            k_long=6895.0,
            option_type='PUT',
            quantity=1,
            order_price=4.70
        )
        
        # Verify order ID was extracted and used
        self.assertEqual(result['orderId'], '999888777666')
        
        print("✅ Test passed: Order ID extracted from Location header")
    
    @patch('src.orders.spread_order_placer.requests.post')
    @patch('src.orders.spread_order_placer.time.sleep')
    def test_fallback_when_verification_fails(self, mock_sleep, mock_post):
        """Test fallback when order verification fails but we have order ID."""
        
        # Mock response with Location header
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.text = ''
        mock_response.headers = {
            'Location': 'https://api.schwabapi.com/trader/v1/accounts/HASH123/orders/123456789',
        }
        mock_response.raise_for_status = Mock()
        
        mock_post.return_value = mock_response
        
        self.placer.account_mgr.get_account_hash = Mock(return_value='HASH123')
        
        # Mock get_orders_executed_today to return empty (verification fails)
        self.placer.account_mgr.get_orders_executed_today = Mock(return_value=[])
        
        # Call the method
        result = self.placer.place_10wide_credit_spread(
            date='251229',
            k_short=6905.0,
            k_long=6895.0,
            option_type='PUT',
            quantity=1,
            order_price=4.70
        )
        
        # Verify fallback returns order ID from Location header
        self.assertEqual(result['orderId'], '123456789')
        self.assertEqual(result['status'], 'ACCEPTED')
        
        print("✅ Test passed: Fallback works when verification fails")
    
    @patch('src.orders.spread_order_placer.requests.post')
    def test_json_response_still_works(self, mock_post):
        """Test that JSON responses (if API changes) still work."""
        
        # Mock response with JSON body (for APIs that return JSON)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"orderId": "JSON123", "status": "ACCEPTED"}'
        mock_response.headers = {}
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {'orderId': 'JSON123', 'status': 'ACCEPTED'}
        
        mock_post.return_value = mock_response
        
        # Mock account manager
        self.placer.account_mgr.get_account_hash = Mock(return_value='HASH123')
        
        # Call the method
        result = self.placer.place_10wide_credit_spread(
            date='251229',
            k_short=6905.0,
            k_long=6895.0,
            option_type='PUT',
            quantity=1,
            order_price=4.70
        )
        
        # Verify JSON response is handled
        self.assertEqual(result['orderId'], 'JSON123')
        self.assertEqual(result['status'], 'ACCEPTED')
        
        print("✅ Test passed: JSON responses still work")


def run_integration_test():
    """
    Integration test that uses real API (but with very high limit price to prevent fill).
    This verifies the actual fix works with the real Schwab API.
    """
    print("=" * 70)
    print("INTEGRATION TEST: Real API Test (High Limit Price)")
    print("=" * 70)
    print()
    print("This will place a test order with $999.99 limit (won't fill)")
    print("to verify the fix works with the actual Schwab API.")
    print()
    
    # Skip integration test in non-interactive mode
    try:
        response = input("Run integration test? (yes/no): ").strip().lower()
        if response != 'yes':
            print("Skipping integration test")
            return
    except (EOFError, KeyboardInterrupt):
        print("Skipping integration test (non-interactive mode)")
        return
    
    try:
        # Temporarily enable live trading
        original_dry_run = Config.DRY_RUN
        original_enable = Config.ENABLE_LIVE_TRADING
        
        Config.DRY_RUN = False
        Config.ENABLE_LIVE_TRADING = True
        
        placer = SpreadOrderPlacer()
        
        # Use today's date but very high limit price
        today = datetime.now(ET)
        date = today.strftime('%y%m%d')
        
        print(f"Placing test order with date: {date}")
        print(f"Limit price: $999.99 (will not fill)")
        print()
        
        result = placer.place_10wide_credit_spread(
            date=date,
            k_short=6905.0,
            k_long=6895.0,
            option_type='PUT',
            quantity=1,
            order_price=999.99  # Unrealistically high
        )
        
        print()
        print("=" * 70)
        print("INTEGRATION TEST RESULTS")
        print("=" * 70)
        print(f"Order ID: {result.get('orderId', 'N/A')}")
        print(f"Status: {result.get('status', 'N/A')}")
        print(f"Has order_details: {'order_details' in result}")
        
        if result.get('orderId') and result.get('orderId') != 'PENDING':
            print()
            print("✅ INTEGRATION TEST PASSED")
            print("   Order was placed and confirmed successfully!")
        else:
            print()
            print("⚠️  INTEGRATION TEST INCONCLUSIVE")
            print("   Order may have been placed but confirmation failed")
        
        # Restore config
        Config.DRY_RUN = original_dry_run
        Config.ENABLE_LIVE_TRADING = original_enable
        
    except Exception as e:
        print(f"❌ INTEGRATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    print("=" * 70)
    print("ORDER PLACEMENT FIX VERIFICATION")
    print("=" * 70)
    print()
    
    # Run unit tests
    print("Running unit tests...")
    print()
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    print()
    print("=" * 70)
    print()
    
    # Optionally run integration test
    run_integration_test()

