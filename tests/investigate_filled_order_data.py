"""
Investigate what data is available in a filled order from Schwab API.

This script will:
1. Get filled orders from today
2. Examine the structure of a filled order
3. Identify where the actual fill credit/price is stored
4. Show what data is available for EOD report
"""
import sys
import os
import json
from datetime import datetime
import pytz
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.accounts.account_manager import AccountManager
from src.utils.logger import setup_logger

logger = setup_logger("investigate_filled_order")
ET = pytz.timezone('US/Eastern')


def investigate_filled_order_data():
    """
    Investigate what data is available in filled orders.
    """
    print("=" * 70)
    print("INVESTIGATION: Filled Order Data Structure")
    print("=" * 70)
    print()
    print("This will examine filled orders to find:")
    print("  1. Where the actual fill credit/price is stored")
    print("  2. What fields are available in orderActivityCollection")
    print("  3. How to get the real credit received")
    print()
    
    try:
        account_mgr = AccountManager()
        
        # Get filled orders from today
        print("Fetching filled orders from today...")
        print()
        
        filled_orders = account_mgr.get_orders_executed_today(
            status='FILLED',
            max_results=10
        )
        
        if not filled_orders:
            print("⚠️  No filled orders found for today")
            print("   Trying to get any orders (not just FILLED)...")
            print()
            
            all_orders = account_mgr.get_orders_executed_today(max_results=10)
            
            if not all_orders:
                print("⚠️  No orders found for today")
                print("   Trying to get orders from past 7 days...")
                print()
                
                # Get orders from past 7 days
                from datetime import timedelta, timezone
                today = datetime.now(timezone.utc)
                week_ago = today - timedelta(days=7)
                
                from_time = week_ago.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                to_time = today.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                
                all_orders = account_mgr.get_orders(
                    from_entered_time=from_time,
                    to_entered_time=to_time,
                    status='FILLED',
                    max_results=10
                )
                
                if not all_orders:
                    print("❌ No filled orders found in past 7 days")
                    print()
                    print("Note: If you have a specific order ID, we can look it up")
                    print("      For example, order ID 1005028254127 from your screenshot")
                    return
                
                print(f"✅ Found {len(all_orders)} filled order(s) from past 7 days")
                print("   Examining the most recent filled order...")
                print()
                
                order = all_orders[0]
            else:
                print(f"Found {len(all_orders)} order(s) (any status)")
                print("   Examining the most recent order...")
                print()
                
                order = all_orders[0]
        else:
            print(f"✅ Found {len(filled_orders)} filled order(s)")
            print("   Examining the most recent filled order...")
            print()
            
            order = filled_orders[0]
        
        # Display full order structure
        print("=" * 70)
        print("FULL ORDER STRUCTURE")
        print("=" * 70)
        print()
        print(json.dumps(order, indent=2))
        print()
        
        # Extract key fields
        print("=" * 70)
        print("KEY FIELDS EXTRACTION")
        print("=" * 70)
        print()
        
        order_id = order.get('orderId', 'N/A')
        status = order.get('status', 'N/A')
        entered_time = order.get('enteredTime', 'N/A')
        close_time = order.get('closeTime', 'N/A')
        order_type = order.get('orderType', 'N/A')
        price = order.get('price', 'N/A')
        
        print(f"Order ID:           {order_id}")
        print(f"Status:             {status}")
        print(f"Entered Time:       {entered_time}")
        print(f"Close Time:         {close_time}")
        print(f"Order Type:         {order_type}")
        print(f"Price (limit):      {price}")
        print()
        
        # Examine orderLegCollection
        print("=" * 70)
        print("ORDER LEG COLLECTION (Spread Legs)")
        print("=" * 70)
        print()
        
        order_legs = order.get('orderLegCollection', [])
        if order_legs:
            for i, leg in enumerate(order_legs, 1):
                print(f"Leg {i}:")
                print(f"  Instruction:     {leg.get('instruction', 'N/A')}")
                print(f"  Quantity:        {leg.get('quantity', 'N/A')}")
                instrument = leg.get('instrument', {})
                print(f"  Symbol:          {instrument.get('symbol', 'N/A')}")
                print(f"  Asset Type:      {instrument.get('assetType', 'N/A')}")
                print()
        else:
            print("  No order legs found")
            print()
        
        # Examine orderActivityCollection (EXECUTION DETAILS)
        print("=" * 70)
        print("ORDER ACTIVITY COLLECTION (EXECUTION/FILL DETAILS)")
        print("=" * 70)
        print()
        
        activities = order.get('orderActivityCollection', [])
        if activities:
            print(f"Found {len(activities)} activity/execution(s)")
            print()
            
            total_credit = 0.0
            total_debit = 0.0
            
            for i, activity in enumerate(activities, 1):
                print(f"Activity {i}:")
                print(f"  Execution Type:  {activity.get('executionType', 'N/A')}")
                print(f"  Quantity:        {activity.get('quantity', 'N/A')}")
                print()
                
                # Check executionLegs - THIS IS WHERE THE ACTUAL FILL PRICES ARE!
                execution_legs = activity.get('executionLegs', [])
                if execution_legs:
                    print(f"  Execution Legs ({len(execution_legs)} legs):")
                    for leg in execution_legs:
                        leg_id = leg.get('legId', 'N/A')
                        leg_price = leg.get('price', 0)
                        leg_qty = leg.get('quantity', 0)
                        leg_time = leg.get('time', 'N/A')
                        
                        # Match leg ID to order leg to get instruction (BUY/SELL)
                        leg_instruction = 'UNKNOWN'
                        for order_leg in order_legs:
                            if order_leg.get('legId') == leg_id:
                                leg_instruction = order_leg.get('instruction', 'UNKNOWN')
                                break
                        
                        print(f"    Leg {leg_id} ({leg_instruction}):")
                        print(f"      Price:  ${leg_price:.2f}")
                        print(f"      Qty:    {leg_qty}")
                        print(f"      Time:   {leg_time}")
                        
                        # Calculate credit/debit based on instruction
                        if 'SELL' in leg_instruction or 'SELL_TO_OPEN' in leg_instruction:
                            total_credit += leg_price * leg_qty
                            print(f"      → Credit: ${leg_price * leg_qty:.2f}")
                        elif 'BUY' in leg_instruction or 'BUY_TO_OPEN' in leg_instruction:
                            total_debit += leg_price * leg_qty
                            print(f"      → Debit:  ${leg_price * leg_qty:.2f}")
                        print()
                else:
                    print("  ⚠️  No execution legs found")
                    print()
            
            # Calculate net credit
            net_credit = total_credit - total_debit
            print(f"Total Credit:      ${total_credit:.2f}")
            print(f"Total Debit:       ${total_debit:.2f}")
            print(f"Net Credit:        ${net_credit:.2f}")
            print()
            
            print("=" * 70)
            print("ACTUAL FILL CREDIT FOUND!")
            print("=" * 70)
            print(f"Net Credit Received: ${net_credit:.2f}")
            print()
            print("This is the ACTUAL credit received from the broker!")
            print("This should be used in the EOD report instead of calculated values.")
            print()
        else:
            print("⚠️  No order activities found")
            print("   This order may not have execution details yet")
            print()
        
        # Check for other potential fields
        print("=" * 70)
        print("OTHER POTENTIAL FIELDS")
        print("=" * 70)
        print()
        
        # Check for netPrice, netCredit, etc.
        potential_fields = ['netPrice', 'netCredit', 'averagePrice', 'fillPrice', 'executionPrice']
        found_fields = {}
        
        for field in potential_fields:
            if field in order:
                found_fields[field] = order[field]
        
        if found_fields:
            print("Found additional price/credit fields:")
            for field, value in found_fields.items():
                print(f"  {field}: {value}")
        else:
            print("No additional price/credit fields found at top level")
        
        print()
        
        # Summary
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print()
        print("To get actual fill credit for EOD report:")
        print("  1. Get filled order by order_id")
        print("  2. Extract orderActivityCollection")
        print("  3. Calculate: (SELL prices * quantities) - (BUY prices * quantities)")
        print("  4. This gives the actual net credit received")
        print()
        print("OR check if there's a direct field like 'netPrice' or 'netCredit'")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    investigate_filled_order_data()

