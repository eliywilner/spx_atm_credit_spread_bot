"""Analyze today's market data and show what trade would be taken (no orders placed)."""
import sys
import os
from datetime import datetime, time as dt_time
import pytz
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.strategy.market_data import MarketDataFetcher
from src.strategy.opening_range import OpeningRangeTracker
from src.strategy.strike_calculator import StrikeCalculator
from src.strategy.quote_monitor import QuoteMonitor
from src.strategy.position_sizing import PositionSizer
from src.accounts.account_manager import AccountManager
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("todays_trade_analysis")
ET = pytz.timezone('US/Eastern')

def analyze_todays_trade():
    """Analyze today's market data and show what trade would be taken."""
    print("=" * 70)
    print("TODAY'S TRADE ANALYSIS - Real Market Data")
    print("=" * 70)
    print()
    print(f"Date: {datetime.now(ET).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"DRY_RUN: {Config.DRY_RUN}")
    print(f"ENABLE_LIVE_TRADING: {Config.ENABLE_LIVE_TRADING}")
    print(f"Daily Risk: {Config.DAILY_RISK_PCT * 100}%")
    print(f"Min Contracts: {Config.MIN_CONTRACTS}")
    print(f"Max Contracts: {Config.MAX_CONTRACTS}")
    print()
    
    today = datetime.now(ET)
    today_dt = ET.localize(datetime.combine(today.date(), datetime.min.time().replace(hour=9, minute=30)))
    
    try:
        # Step 1: Get Account Equity
        print("=" * 70)
        print("STEP 1: ACCOUNT INFORMATION")
        print("=" * 70)
        account_mgr = AccountManager()
        account_equity = account_mgr.get_net_liquidity()
        print(f"✅ Account Equity (Net Liquidity): ${account_equity:,.2f}")
        print()
        
        # Step 2: Get Opening Range
        print("=" * 70)
        print("STEP 2: OPENING RANGE (09:30-10:00 ET)")
        print("=" * 70)
        or_tracker = OpeningRangeTracker()
        or_data = or_tracker.get_opening_range(today_dt)
        
        if not or_data:
            print("❌ Could not get Opening Range")
            print("   This may be because:")
            print("   - Market hasn't opened yet (before 9:30 AM ET)")
            print("   - Market is closed")
            print("   - API error")
            return
        
        oro = or_data.get('ORO', 0)
        orh = or_data.get('ORH', 0)
        orl = or_data.get('ORL', 0)
        orc = or_data.get('ORC', 0)
        
        print(f"✅ Opening Range Retrieved:")
        print(f"   ORO (Open):  ${oro:.2f}")
        print(f"   ORH (High):  ${orh:.2f}")
        print(f"   ORL (Low):   ${orl:.2f}")
        print(f"   ORC (Close): ${orc:.2f}")
        print()
        
        # Calculate OR width
        or_width = orh - orl
        or_midpoint = (orh + orl) / 2
        print(f"   OR Width:    ${or_width:.2f}")
        print(f"   OR Midpoint: ${or_midpoint:.2f}")
        print()
        
        # Step 3: Decision Tree Analysis
        print("=" * 70)
        print("STEP 3: DECISION TREE ANALYSIS")
        print("=" * 70)
        
        is_bullish = orc > oro
        is_bearish = orc < oro
        is_neutral = orc == oro
        
        print(f"OR Analysis:")
        print(f"   ORC (${orc:.2f}) vs ORO (${oro:.2f})")
        if is_bullish:
            print(f"   ✅ BULLISH OR: ORC > ORO (difference: ${orc - oro:.2f})")
        elif is_bearish:
            print(f"   ✅ BEARISH OR: ORC < ORO (difference: ${oro - orc:.2f})")
        else:
            print(f"   ⚠️  NEUTRAL OR: ORC == ORO")
        print()
        
        # Step 4: Determine which setup applies
        setup_triggered = None
        spx_entry = None
        option_type = None
        k_short = None
        k_long = None
        
        if is_bullish:
            print("=" * 70)
            print("STEP 4: STEP A - BULLISH OR SETUP")
            print("=" * 70)
            print("✅ Step A is ELIGIBLE (ORC > ORO)")
            print()
            print("Per strategy spec:")
            print("  - At 10:00, if ORC > ORO → Place PUT credit spread")
            print("  - SPX_entry = ORC (10:00 close)")
            print("  - Monitor quotes until 12:00 ET")
            print("  - Enter if C_net >= 4.60")
            print()
            
            setup_triggered = "Bullish OR"
            spx_entry = orc
            option_type = "PUT"
            k_short, k_long = StrikeCalculator.calculate_put_spread_strikes(spx_entry)
            
            print(f"Trade Parameters:")
            print(f"   Setup: {setup_triggered}")
            print(f"   SPX_entry: ${spx_entry:.2f} (locked at 10:00 close = ORC)")
            print(f"   Option Type: {option_type} Credit Spread")
            print(f"   K_short: ${k_short:.2f} (ATM, rounded to nearest 5)")
            print(f"   K_long: ${k_long:.2f} (K_short - 10)")
            print(f"   Spread Width: 10 points")
            print()
            
        elif is_bearish:
            print("=" * 70)
            print("STEP 4: STEP B - BEARISH ORL BREAKOUT SETUP")
            print("=" * 70)
            print("✅ Step B is ELIGIBLE (ORC < ORO)")
            print()
            print("Per strategy spec:")
            print("  - Scan 10:00-12:00 for first bar where bar_close < ORL")
            print("  - If breakout found → Place CALL credit spread")
            print("  - SPX_entry = breakout_bar_close")
            print("  - Monitor quotes until 12:00 ET")
            print("  - Enter if C_net >= 4.60")
            print()
            
            # Get candles from 10:00-12:00
            market_data = MarketDataFetcher()
            candles = market_data.get_30min_candles(
                today_dt,
                start_hour=10,
                start_minute=0,
                end_hour=12,
                end_minute=0
            )
            
            if candles:
                print(f"Scanning {len(candles)} candle(s) from 10:00-12:00:")
                breakout_candle = None
                for i, candle in enumerate(candles):
                    bar_close = candle.get('close', 0)
                    bar_time = candle.get('datetime', 0)
                    print(f"   Candle {i+1}: Close=${bar_close:.2f}, ORL=${orl:.2f}")
                    if bar_close < orl:
                        breakout_candle = candle
                        print(f"   ✅ BREAKOUT FOUND: bar_close (${bar_close:.2f}) < ORL (${orl:.2f})")
                        break
                
                if breakout_candle:
                    setup_triggered = "Bearish ORL Breakout"
                    spx_entry = breakout_candle.get('close', 0)
                    option_type = "CALL"
                    k_short, k_long = StrikeCalculator.calculate_call_spread_strikes(spx_entry)
                    
                    print()
                    print(f"Trade Parameters:")
                    print(f"   Setup: {setup_triggered}")
                    print(f"   SPX_entry: ${spx_entry:.2f} (breakout bar close)")
                    print(f"   Option Type: {option_type} Credit Spread")
                    print(f"   K_short: ${k_short:.2f} (ATM, rounded to nearest 5)")
                    print(f"   K_long: ${k_long:.2f} (K_short + 10)")
                    print(f"   Spread Width: 10 points")
                    print()
                else:
                    print("   ⚠️  No breakout found (all bars have close >= ORL)")
                    print("   → No trade would be placed today")
                    return
            else:
                print("⚠️  Could not get candles for 10:00-12:00 window")
                print("   → Cannot determine if Step B would trigger")
                return
        else:
            print("⚠️  NEUTRAL OR (ORC == ORO)")
            print("   → Neither Step A nor Step B applies")
            print("   → No trade would be placed today")
            return
        
        # Step 5: Get Current Quotes
        print("=" * 70)
        print("STEP 5: QUOTE MONITORING (Current Market Data)")
        print("=" * 70)
        print(f"Getting quotes for {option_type} spread:")
        print(f"   K_short: ${k_short:.2f}")
        print(f"   K_long: ${k_long:.2f}")
        print()
        
        quote_monitor = QuoteMonitor()
        credit_data = quote_monitor.get_spread_credit(
            date=today_dt,
            k_short=k_short,
            k_long=k_long,
            option_type=option_type
        )
        
        if not credit_data:
            print("⚠️  Could not get spread credit quotes")
            print("   This may be because:")
            print("   - Options not yet available (too early in day)")
            print("   - Market is closed")
            print("   - API error")
            print()
            print("In real bot, would continue monitoring every 10 seconds until 12:00 ET")
            return
        
        c_gross = credit_data['C_gross']
        c_net = credit_data['C_net']
        short_mid = credit_data['short_mid']
        long_mid = credit_data['long_mid']
        short_bid = credit_data.get('short_bid', 0)
        short_ask = credit_data.get('short_ask', 0)
        long_bid = credit_data.get('long_bid', 0)
        long_ask = credit_data.get('long_ask', 0)
        
        print(f"✅ Spread Quote Retrieved:")
        print()
        print(f"Short Leg (K_short = ${k_short:.2f}):")
        print(f"   Bid: ${short_bid:.2f}")
        print(f"   Ask: ${short_ask:.2f}")
        print(f"   Mid: ${short_mid:.2f}")
        print()
        print(f"Long Leg (K_long = ${k_long:.2f}):")
        print(f"   Bid: ${long_bid:.2f}")
        print(f"   Ask: ${long_ask:.2f}")
        print(f"   Mid: ${long_mid:.2f}")
        print()
        print(f"Spread Credit Calculation:")
        print(f"   C_gross = short_mid - long_mid")
        print(f"   C_gross = ${short_mid:.2f} - ${long_mid:.2f} = ${c_gross:.2f}")
        print(f"   Slippage Buffer (S): ${Config.SLIPPAGE_BUFFER:.2f}")
        print(f"   C_net = C_gross - S")
        print(f"   C_net = ${c_gross:.2f} - ${Config.SLIPPAGE_BUFFER:.2f} = ${c_net:.2f}")
        print()
        
        # Step 6: Credit Filter Check
        print("=" * 70)
        print("STEP 6: CREDIT FILTER CHECK")
        print("=" * 70)
        print(f"Minimum NET credit required: ${Config.MIN_NET_CREDIT:.2f}")
        print(f"Current C_net: ${c_net:.2f}")
        print()
        
        meets_threshold = quote_monitor.meets_credit_threshold(credit_data)
        
        if meets_threshold:
            print(f"✅ CREDIT THRESHOLD MET!")
            print(f"   C_net (${c_net:.2f}) >= MIN_NET_CREDIT (${Config.MIN_NET_CREDIT:.2f})")
            print()
        else:
            print(f"❌ CREDIT THRESHOLD NOT MET")
            print(f"   C_net (${c_net:.2f}) < MIN_NET_CREDIT (${Config.MIN_NET_CREDIT:.2f})")
            print()
            print("In real bot:")
            print("   - Would continue monitoring every 10 seconds until 12:00 ET")
            print("   - Would place order if credit threshold is met before 12:00")
            print("   - If 12:00 arrives with no fill → NO TRADE TODAY")
            print()
            print("=" * 70)
            print("STEP 7: POSITION SIZING (IF TRADE WERE PLACED)")
            print("=" * 70)
            position_sizer = PositionSizer()
            sizing = position_sizer.calculate_position_size(
                account_equity=account_equity,
                c_net=c_net,
                max_qty_cap=Config.MAX_CONTRACTS
            )
            qty = sizing['qty']
            r_day = sizing['R_day']
            max_loss_per_spread = sizing['maxLossPerSpread']
            
            print(f"Position Sizing Calculation (using current C_net):")
            print(f"   Account Equity (E): ${account_equity:,.2f}")
            print(f"   Daily Risk %: {Config.DAILY_RISK_PCT * 100}%")
            print(f"   Daily Risk Budget (R_day) = {Config.DAILY_RISK_PCT * 100}% × ${account_equity:,.2f} = ${r_day:,.2f}")
            print()
            print(f"   Spread Width (W): {Config.SPREAD_WIDTH} points")
            print(f"   C_net (at fill time): ${c_net:.2f}")
            print(f"   Max Loss per Spread = (W - C_net) × 100")
            print(f"   Max Loss per Spread = ({Config.SPREAD_WIDTH} - ${c_net:.2f}) × 100 = ${max_loss_per_spread:,.2f}")
            print()
            print(f"   Quantity = floor(R_day / maxLossPerSpread)")
            print(f"   Quantity = floor(${r_day:,.2f} / ${max_loss_per_spread:,.2f}) = {int(r_day / max_loss_per_spread) if max_loss_per_spread > 0 else 0}")
            print(f"   Apply min override: max(1, {int(r_day / max_loss_per_spread) if max_loss_per_spread > 0 else 0}) = {max(1, int(r_day / max_loss_per_spread) if max_loss_per_spread > 0 else 0)}")
            print(f"   Apply max cap: min({max(1, int(r_day / max_loss_per_spread) if max_loss_per_spread > 0 else 0)}, {Config.MAX_CONTRACTS}) = {qty}")
            print()
            print("=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"✅ Setup Identified: {setup_triggered}")
            print(f"✅ Strikes Calculated: K_short=${k_short:.2f}, K_long=${k_long:.2f}")
            print(f"❌ Credit Threshold: NOT MET (${c_net:.2f} < ${Config.MIN_NET_CREDIT:.2f})")
            print(f"📊 If threshold were met, would trade: {qty} contract(s)")
            print()
            return
        
        # Step 7: Position Sizing
        print("=" * 70)
        print("STEP 7: POSITION SIZING")
        print("=" * 70)
        position_sizer = PositionSizer()
        sizing = position_sizer.calculate_position_size(
            account_equity=account_equity,
            c_net=c_net,
            max_qty_cap=Config.MAX_CONTRACTS
        )
        qty = sizing['qty']
        r_day = sizing['R_day']
        max_loss_per_spread = sizing['maxLossPerSpread']
        
        print(f"Position Sizing Calculation:")
        print(f"   Account Equity (E): ${account_equity:,.2f}")
        print(f"   Daily Risk %: {Config.DAILY_RISK_PCT * 100}%")
        print(f"   Daily Risk Budget (R_day) = {Config.DAILY_RISK_PCT * 100}% × ${account_equity:,.2f} = ${r_day:,.2f}")
        print()
        print(f"   Spread Width (W): {Config.SPREAD_WIDTH} points")
        print(f"   C_net (at fill time): ${c_net:.2f}")
        print(f"   Max Loss per Spread = (W - C_net) × 100")
        print(f"   Max Loss per Spread = ({Config.SPREAD_WIDTH} - ${c_net:.2f}) × 100 = ${max_loss_per_spread:,.2f}")
        print()
        print(f"   Quantity = floor(R_day / maxLossPerSpread)")
        print(f"   Quantity = floor(${r_day:,.2f} / ${max_loss_per_spread:,.2f}) = {int(r_day / max_loss_per_spread) if max_loss_per_spread > 0 else 0}")
        print(f"   Apply min override: max(1, {int(r_day / max_loss_per_spread) if max_loss_per_spread > 0 else 0}) = {max(1, int(r_day / max_loss_per_spread) if max_loss_per_spread > 0 else 0)}")
        print(f"   Apply max cap: min({max(1, int(r_day / max_loss_per_spread) if max_loss_per_spread > 0 else 0)}, {Config.MAX_CONTRACTS}) = {qty}")
        print()
        
        # Step 8: Trade Summary
        print("=" * 70)
        print("STEP 8: TRADE SUMMARY - WHAT WOULD BE PLACED")
        print("=" * 70)
        expiration_date = today_dt.strftime('%y%m%d')
        order_price = c_gross
        
        print(f"✅ TRADE WOULD BE PLACED (DRY RUN):")
        print()
        print(f"Setup: {setup_triggered}")
        print(f"Trade Type: {option_type} Credit Spread")
        print()
        print(f"Entry Details:")
        print(f"   SPX_entry: ${spx_entry:.2f}")
        print(f"   Entry Time: 10:00 ET (for Bullish OR) or breakout time (for Bearish ORL)")
        print()
        print(f"Strikes:")
        print(f"   K_short: ${k_short:.2f} (SELL_TO_OPEN)")
        print(f"   K_long: ${k_long:.2f} (BUY_TO_OPEN)")
        print(f"   Spread Width: 10 points")
        print()
        print(f"Credit:")
        print(f"   C_gross: ${c_gross:.2f}")
        print(f"   Slippage Buffer: ${Config.SLIPPAGE_BUFFER:.2f}")
        print(f"   C_net: ${c_net:.2f}")
        print()
        print(f"Position Size:")
        print(f"   Account Equity: ${account_equity:,.2f}")
        print(f"   Daily Risk Budget ({Config.DAILY_RISK_PCT * 100}%): ${r_day:,.2f}")
        print(f"   Max Loss per Spread: ${max_loss_per_spread:,.2f}")
        print(f"   Quantity: {qty} contracts")
        print()
        print(f"Risk Analysis:")
        print(f"   Max Loss: ${max_loss_per_spread * qty:,.2f} (if spread goes to max value)")
        print(f"   Max Profit: ${c_net * 100 * qty:,.2f} (if spread expires worthless)")
        print(f"   Risk as % of Equity: {(max_loss_per_spread * qty / account_equity) * 100:.2f}%")
        print()
        print(f"Order Details:")
        print(f"   Expiration: {expiration_date} (0DTE - same day)")
        print(f"   Order Price: ${order_price:.2f} (limit credit)")
        print(f"   Quantity: {qty}")
        print()
        print("🚫 DRY RUN MODE - Order NOT placed")
        print()
        print("=" * 70)
        print("✅ ANALYSIS COMPLETE")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print()

if __name__ == '__main__':
    analyze_todays_trade()

