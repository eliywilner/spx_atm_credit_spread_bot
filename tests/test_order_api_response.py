"""
Test script to investigate Schwab API order placement response format.

This script makes a test request to see what the API actually returns,
without placing a real order (uses expired date to ensure rejection).
"""
import sys
import os
import json
import requests
from datetime import datetime, timedelta
import pytz
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.client.schwab_client import SchwabClient
from src.accounts.account_manager import AccountManager
from src.quotes.quotes_manager import QuotesManager
from src.utils.logger import setup_logger

logger = setup_logger("test_order_api")
ET = pytz.timezone('US/Eastern')


def test_order_api_response():
    """
    Test what the Schwab API actually returns when placing an order.
    Uses an expired date to ensure the order won't execute, but we can see the response format.
    """
    print("=" * 70)
    print("TEST: Schwab API Order Placement Response Investigation")
    print("=" * 70)
    print()
    print("This test will:")
    print("  1. Build an order payload (using expired date to prevent execution)")
    print("  2. Make the API request")
    print("  3. Log EVERYTHING about the response")
    print("  4. Analyze what the API actually returns")
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
        
        # Test with valid date but very high limit price to prevent immediate fill
        # This will show us what the API returns for a valid order submission
        today = datetime.now(ET)
        valid_date = today.strftime('%y%m%d')
        
        # Check if market is open - if not, use today's date anyway (order won't execute outside market hours)
        current_time = today.time()
        market_open = datetime.strptime("09:30", "%H:%M").time()
        market_close = datetime.strptime("16:00", "%H:%M").time()
        
        if market_open <= current_time <= market_close:
            print(f"⚠️  Market is currently OPEN")
            print(f"   Using VERY HIGH limit price ($999.99) to prevent immediate execution")
            print(f"   This will show us the API response format for valid orders")
            order_price = 999.99  # Unrealistically high to prevent fill
        else:
            print(f"✅ Market is CLOSED - safe to test with normal price")
            print(f"   Order won't execute outside market hours")
            order_price = 4.70
        
        print(f"Using date: {valid_date}")
        print()
        
        # Build order payload (same structure as actual code)
        k_short = 6905.0
        k_long = 6895.0
        option_type = 'PUT'
        quantity = 1
        # order_price is set above based on market status
        
        option_type_char = 'P' if option_type == 'PUT' else 'C'
        
        # Format option symbols
        short_symbol = quotes_mgr._format_option_symbol(
            'SPXW', valid_date, option_type_char, k_short
        )
        long_symbol = quotes_mgr._format_option_symbol(
            'SPXW', valid_date, option_type_char, k_long
        )
        
        print("Order payload details:")
        print(f"  Date: {valid_date}")
        print(f"  Short Symbol: {short_symbol}")
        print(f"  Long Symbol: {long_symbol}")
        print(f"  K_short: ${k_short:.2f}")
        print(f"  K_long: ${k_long:.2f}")
        print(f"  Quantity: {quantity}")
        print(f"  Order Price: ${order_price:.2f}")
        print()
        
        # Build order JSON (exact same as spread_order_placer.py)
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
        
        print("Order JSON payload:")
        print(json.dumps(order, indent=2))
        print()
        
        # Make the API request
        url = f"{client.base_url}/accounts/{account_hash}/orders"
        headers = client.auth.get_headers()
        headers['Content-Type'] = 'application/json'
        
        print("=" * 70)
        print("MAKING API REQUEST")
        print("=" * 70)
        print(f"URL: {url}")
        print(f"Method: POST")
        print(f"Headers: {json.dumps({k: v for k, v in headers.items() if k != 'Authorization'}, indent=2)}")
        print(f"  (Authorization header present: {bool(headers.get('Authorization'))})")
        print()
        
        try:
            response = requests.post(url, json=order, headers=headers, timeout=10)
            
            print("=" * 70)
            print("API RESPONSE ANALYSIS")
            print("=" * 70)
            print()
            
            # Log EVERYTHING about the response
            print(f"✅ HTTP Status Code: {response.status_code}")
            print(f"   Status Text: {response.reason}")
            print()
            
            print("Response Headers:")
            for key, value in response.headers.items():
                print(f"  {key}: {value}")
            print()
            
            print(f"Response Body Length: {len(response.text) if response.text else 0} bytes")
            print()
            
            print("Response Body Content:")
            if response.text:
                print("-" * 70)
                print(response.text)
                print("-" * 70)
            else:
                print("  (EMPTY - No response body)")
            print()
            
            # Try to parse as JSON
            print("JSON Parsing Attempt:")
            try:
                json_data = response.json()
                print("  ✅ Successfully parsed as JSON")
                print("  JSON Structure:")
                print(json.dumps(json_data, indent=2))
            except ValueError as json_error:
                print(f"  ❌ Failed to parse as JSON: {json_error}")
                print(f"  Error type: {type(json_error).__name__}")
                if "Expecting value" in str(json_error):
                    print("  ⚠️  This is the SAME ERROR we saw in production!")
                    print("  This means the response body is empty or invalid JSON")
            print()
            
            # Check response status
            print("Response Status Analysis:")
            if response.status_code == 200:
                print("  ✅ 200 OK - Request was successful")
                if not response.text or response.text.strip() == '':
                    print("  ⚠️  BUT response body is EMPTY")
                    print("  This explains the JSON parsing error!")
            elif response.status_code == 204:
                print("  ✅ 204 No Content - Request successful, no body returned")
                print("  This is normal for some APIs - order was accepted")
            elif response.status_code == 400:
                print("  ⚠️  400 Bad Request - Order was rejected")
                print("  Check response body for error details")
            elif response.status_code == 401:
                print("  ❌ 401 Unauthorized - Authentication issue")
            elif response.status_code == 403:
                print("  ❌ 403 Forbidden - Permission issue")
            elif response.status_code >= 500:
                print(f"  ❌ {response.status_code} Server Error")
            else:
                print(f"  ⚠️  Unexpected status code: {response.status_code}")
            print()
            
            # Summary
            print("=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"Status Code: {response.status_code}")
            print(f"Response Body: {'Empty' if not response.text else f'{len(response.text)} bytes'}")
            print(f"Can Parse JSON: {'Yes' if response.text else 'No'}")
            
            if response.status_code == 200 and not response.text:
                print()
                print("🔍 ROOT CAUSE IDENTIFIED:")
                print("   The API returns 200 OK with an EMPTY response body")
                print("   This causes 'Expecting value: line 1 column 1' when parsing JSON")
                print("   The order is likely placed successfully, but we can't parse the response")
            
            print()
            print("=" * 70)
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_order_api_response()

