"""
Test script to verify we can get order details after placement.

This tests:
1. Extracting order ID from Location header
2. Getting order details via GET request
3. What information is available for EOD report
"""
import sys
import os
import json
import requests
import re
from datetime import datetime, timedelta
import pytz
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.client.schwab_client import SchwabClient
from src.accounts.account_manager import AccountManager
from src.quotes.quotes_manager import QuotesManager
from src.utils.logger import setup_logger

logger = setup_logger("test_get_order")
ET = pytz.timezone('US/Eastern')


def test_get_order_details():
    """
    Test getting order details after placement.
    """
    print("=" * 70)
    print("TEST: Get Order Details After Placement")
    print("=" * 70)
    print()
    print("This test will:")
    print("  1. Place an order (with very high limit to prevent fill)")
    print("  2. Extract order ID from Location header")
    print("  3. GET order details from the Location URL")
    print("  4. Show what information is available")
    print()
    
    try:
        # Initialize clients
        client = SchwabClient()
        account_mgr = AccountManager()
        quotes_mgr = QuotesManager(default_symbol='SPXW')
        
        # Get account hash
        account_hash = account_mgr.get_account_hash()
        print(f"✅ Account hash: {account_hash}")
        print()
        
        # Use valid date but very high limit price
        today = datetime.now(ET)
        valid_date = today.strftime('%y%m%d')
        order_price = 999.99  # Unrealistically high to prevent fill
        
        print(f"Using date: {valid_date}")
        print(f"Using limit price: ${order_price:.2f} (to prevent immediate fill)")
        print()
        
        # Build order payload
        k_short = 6905.0
        k_long = 6895.0
        option_type = 'PUT'
        quantity = 1
        
        option_type_char = 'P' if option_type == 'PUT' else 'C'
        
        # Format option symbols
        short_symbol = quotes_mgr._format_option_symbol(
            'SPXW', valid_date, option_type_char, k_short
        )
        long_symbol = quotes_mgr._format_option_symbol(
            'SPXW', valid_date, option_type_char, k_long
        )
        
        # Build order JSON
        order = {
            "orderType": "NET_CREDIT",
            "session": "NORMAL",
            "price": f"{order_price:.2f}",
            "duration": "DAY",
            "orderStrategyType": "SINGLE",
            "orderLegCollection": [
                {
                    "instruction": "BUY_TO_OPEN",
                    "quantity": quantity,
                    "instrument": {
                        "symbol": long_symbol,
                        "assetType": "OPTION"
                    }
                },
                {
                    "instruction": "SELL_TO_OPEN",
                    "quantity": quantity,
                    "instrument": {
                        "symbol": short_symbol,
                        "assetType": "OPTION"
                    }
                }
            ]
        }
        
        # Place order
        url = f"{client.base_url}/accounts/{account_hash}/orders"
        headers = client.auth.get_headers()
        headers['Content-Type'] = 'application/json'
        
        print("=" * 70)
        print("STEP 1: PLACE ORDER")
        print("=" * 70)
        print()
        
        response = requests.post(url, json=order, headers=headers, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {'Empty' if not response.text else f'{len(response.text)} bytes'}")
        print()
        
        if response.status_code not in [200, 201]:
            print(f"❌ Order placement failed: {response.status_code}")
            if response.text:
                print(f"Response: {response.text}")
            return
        
        # Extract order ID from Location header
        location_header = response.headers.get('Location', '')
        print(f"Location Header: {location_header}")
        print()
        
        if not location_header:
            print("❌ No Location header found!")
            return
        
        # Extract order ID from Location URL
        # Format: https://api.schwabapi.com/trader/v1/accounts/{hash}/orders/{orderId}
        order_id_match = re.search(r'/orders/(\d+)$', location_header)
        if order_id_match:
            order_id = order_id_match.group(1)
            print(f"✅ Extracted Order ID: {order_id}")
        else:
            print("❌ Could not extract order ID from Location header")
            return
        
        print()
        print("=" * 70)
        print("STEP 2: GET ORDER DETAILS")
        print("=" * 70)
        print()
        
        # Get order details using the Location URL
        print(f"Fetching order details from: {location_header}")
        print()
        
        order_details_response = requests.get(location_header, headers=headers, timeout=10)
        
        print(f"Status Code: {order_details_response.status_code}")
        print()
        
        if order_details_response.status_code == 200:
            try:
                order_details = order_details_response.json()
                print("✅ Successfully retrieved order details!")
                print()
                print("Order Details JSON:")
                print(json.dumps(order_details, indent=2))
                print()
                
                # Extract key information for EOD report
                print("=" * 70)
                print("KEY INFORMATION FOR EOD REPORT")
                print("=" * 70)
                print()
                
                order_id_from_details = order_details.get('orderId', 'N/A')
                order_status = order_details.get('status', 'N/A')
                entered_time = order_details.get('enteredTime', 'N/A')
                
                print(f"Order ID:        {order_id_from_details}")
                print(f"Order Status:    {order_status}")
                print(f"Entered Time:    {entered_time}")
                print()
                
                # Check if order is filled
                if 'orderActivityCollection' in order_details:
                    activities = order_details.get('orderActivityCollection', [])
                    if activities:
                        print("Order Activities:")
                        for activity in activities:
                            exec_type = activity.get('executionType', 'N/A')
                            quantity = activity.get('quantity', 'N/A')
                            price = activity.get('price', 'N/A')
                            print(f"  Type: {exec_type}, Qty: {quantity}, Price: ${price}")
                
                print()
                print("=" * 70)
                print("SUMMARY")
                print("=" * 70)
                print("✅ Order ID can be extracted from Location header")
                print("✅ Order details can be retrieved via GET request")
                print(f"✅ Order Status available: {order_status}")
                print("✅ This information is sufficient for EOD report")
                
            except ValueError as e:
                print(f"❌ Failed to parse order details JSON: {e}")
                print(f"Response: {order_details_response.text[:500]}")
        else:
            print(f"❌ Failed to get order details: {order_details_response.status_code}")
            if order_details_response.text:
                print(f"Response: {order_details_response.text[:500]}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_get_order_details()

