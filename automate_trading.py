"""
SPX ATM Credit Spread Bot - 0DTE Strategy

This bot implements the SPX ATM Credit Spread strategy:
- Bullish OR setup: At 10:00, if ORC > ORO, place PUT spread
- Bearish ORL Breakout: Scan 10:00-12:00 for bar_close < ORL, place CALL spread
- Always ATM, always 10-wide
- Minimum NET credit: 4.60
- 5% daily risk position sizing
- Hold to expiration (no early exit)
"""
import sys
import os
import time
import argparse
from datetime import datetime, time as dt_time, timedelta
from typing import Optional, Dict
import pytz

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.strategy.market_data import MarketDataFetcher
from src.strategy.opening_range import OpeningRangeTracker
from src.strategy.strike_calculator import StrikeCalculator
from src.strategy.quote_monitor import QuoteMonitor
from src.strategy.position_sizing import PositionSizer
from src.strategy.pl_calculator import PLCalculator
from src.orders.spread_order_placer import SpreadOrderPlacer
from src.accounts.account_manager import AccountManager
from src.tracking.trade_logger import TradeLogger
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("spx_atm_bot")
ET = pytz.timezone('US/Eastern')

# Market hours
MARKET_OPEN = dt_time(9, 30)
MARKET_CLOSE = dt_time(16, 0)
OR_END = dt_time(10, 0)
ENTRY_END = dt_time(12, 0)


def wait_until_time(target_time: dt_time, description: str):
    """
    Wait until a specific time.
    
    Args:
        target_time: Target time (ET)
        description: Description for logging
    """
    now = datetime.now(ET)
    target_dt = ET.localize(datetime.combine(now.date(), target_time))
    
    if now >= target_dt:
        logger.info(f"{description} time has already passed")
        return
    
    wait_seconds = (target_dt - now).total_seconds()
    logger.info(f"Waiting until {target_time.strftime('%H:%M')} ET for {description}...")
    logger.info(f"  Current time: {now.strftime('%H:%M:%S %Z')}")
    logger.info(f"  Waiting {wait_seconds:.0f} seconds ({wait_seconds/60:.1f} minutes)")
    
    time.sleep(wait_seconds)
    logger.info(f"✅ {description} time reached: {datetime.now(ET).strftime('%H:%M:%S %Z')}")


def monitor_quotes_and_place_order(
    date: datetime,
    spx_entry: float,
    k_short: float,
    k_long: float,
    option_type: str,  # 'PUT' or 'CALL'
    setup: str,  # 'Bullish OR' or 'Bearish ORL Breakout'
    or_data: Dict,
    account_equity: float,
    trigger_time: datetime
) -> Optional[Dict]:
    """
    Monitor quotes every 10 seconds until 12:00 ET and place order when credit threshold is met.
    
    Args:
        date: Trading date
        spx_entry: SPX entry price (locked at trigger)
        k_short: Short strike
        k_long: Long strike
        option_type: 'PUT' or 'CALL'
        setup: Setup name
        or_data: Opening Range data
        account_equity: Account equity for position sizing
        trigger_time: Time when setup was triggered
    
    Returns:
        Order details if placed, None otherwise
    """
    quote_monitor = QuoteMonitor()
    position_sizer = PositionSizer()
    order_placer = SpreadOrderPlacer()
    
    # Initialize trade logger with S3 support
    trade_logger = TradeLogger()
    try:
        from src.storage.s3_service import S3Service
        s3_bucket = os.getenv('AWS_S3_BUCKET_NAME')
        if s3_bucket:
            s3_service = S3Service(bucket_name=s3_bucket)
            trade_logger.s3_service = s3_service
            # Load existing trades from S3 at start
            trade_logger.load_from_s3()
    except Exception as e:
        logger.debug(f"S3 not available for trade logger: {e}")
    
    entry_end_dt = ET.localize(datetime.combine(date.date(), ENTRY_END))
    
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"MONITORING QUOTES FOR {setup}")
    logger.info("=" * 70)
    logger.info(f"SPX_entry: ${spx_entry:.2f}")
    logger.info(f"K_short: ${k_short:.2f}, K_long: ${k_long:.2f}")
    logger.info(f"Option Type: {option_type}")
    logger.info(f"Monitoring until {ENTRY_END.strftime('%H:%M')} ET")
    logger.info("")
    
    while datetime.now(ET) < entry_end_dt:
        # Get spread credit
        credit_data = quote_monitor.get_spread_credit(
            date=date,
            k_short=k_short,
            k_long=k_long,
            option_type=option_type
        )
        
        if not credit_data:
            logger.warning("Could not get credit data, retrying in 10 seconds...")
            time.sleep(Config.QUOTE_MONITOR_INTERVAL)
            continue
        
        c_gross = credit_data['C_gross']
        c_net = credit_data['C_net']
        
        logger.info(f"[{datetime.now(ET).strftime('%H:%M:%S')}] C_gross=${c_gross:.2f}, C_net=${c_net:.2f}")
        
        # Check if credit threshold is met
        if quote_monitor.meets_credit_threshold(credit_data):
            logger.info("")
            logger.info("=" * 70)
            logger.info("✅ CREDIT THRESHOLD MET - PLACING ORDER")
            logger.info("=" * 70)
            
            # Calculate position size (max_qty_cap uses Config.MAX_CONTRACTS)
            sizing = position_sizer.calculate_position_size(
                account_equity=account_equity,
                c_net=c_net,
                max_qty_cap=Config.MAX_CONTRACTS
            )
            qty = sizing['qty']
            
            # Place order
            expiration_date = date.strftime('%y%m%d')
            bias = 'bullish' if option_type == 'PUT' else 'bearish'
            
            # Use the mid price as order price
            order_price = c_gross  # Use gross credit as order price
            
            logger.info(f"Placing {option_type} credit spread order:")
            logger.info(f"  Expiration: {expiration_date}")
            logger.info(f"  K_short: ${k_short:.2f}, K_long: ${k_long:.2f}")
            logger.info(f"  Quantity: {qty}")
            logger.info(f"  Order Price: ${order_price:.2f}")
            
            try:
                order_response = order_placer.place_10wide_credit_spread(
                    date=expiration_date,
                    k_short=k_short,
                    k_long=k_long,
                    option_type=option_type,
                    quantity=qty,
                    order_price=order_price
                )
                
                order_id = order_response.get('orderId', '')
                order_status = order_response.get('status', '')
                is_dry_run = order_response.get('dry_run', False)
                
                if is_dry_run:
                    logger.info(f"✅ Order would be placed (DRY RUN): ID={order_id}, Status={order_status}")
                else:
                    logger.info(f"✅ Order placed (LIVE): ID={order_id}, Status={order_status}")
                
                # Log trade
                fill_time = datetime.now(ET)
                trade_data = {
                    'date': date.strftime('%Y-%m-%d'),
                    'setup': setup,
                    'trade_type': option_type,
                    'trigger_time': trigger_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'fill_time': fill_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'SPX_entry': spx_entry,
                    'ORO': or_data.get('ORO', 0),
                    'ORH': or_data.get('ORH', 0),
                    'ORL': or_data.get('ORL', 0),
                    'ORC': or_data.get('ORC', 0),
                    'K_short': k_short,
                    'K_long': k_long,
                    'C_gross_fill': c_gross,
                    'S': Config.SLIPPAGE_BUFFER,
                    'C_net_fill': c_net,
                    'qty': qty,
                    'R_day': sizing['R_day'],
                    'maxLossPerSpread': sizing['maxLossPerSpread'],
                    'SPX_close': '',  # Will be filled at EOD
                    'settlement_value': '',  # Will be filled at EOD
                    'pnl_per_spread': '',  # Will be filled at EOD
                    'total_pnl': '',  # Will be filled at EOD
                    'equity_before': account_equity,
                    'equity_after': '',  # Will be filled at EOD
                    'order_id': str(order_id),
                    'order_status': order_status
                }
                
                # NOTE: No trade alert email sent (user doesn't want immediate alerts)
                
                trade_logger.log_trade(trade_data)
                
                # Save to S3 after trade is logged
                if trade_logger.s3_service:
                    try:
                        trade_logger.save_to_s3()
                    except Exception as e:
                        logger.warning(f"Failed to save trades CSV to S3: {e}")
                
                return {
                    'order_id': order_id,
                    'order_status': order_status,
                    'trade_data': trade_data
                }
                
            except Exception as e:
                logger.error(f"❌ Error placing order: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                return None
        
        # Wait before next check
        time.sleep(Config.QUOTE_MONITOR_INTERVAL)
    
    logger.warning(f"⚠️  Entry window closed ({ENTRY_END.strftime('%H:%M')} ET) - No trade placed")
    return None


def step_a_bullish_or(date: datetime, or_data: Dict, account_equity: float) -> Optional[Dict]:
    """
    Step A: Bullish OR setup at 10:00.
    
    Args:
        date: Trading date
        or_data: Opening Range data
        account_equity: Account equity
    
    Returns:
        Order details if placed, None otherwise
    """
    logger.info("")
    logger.info("=" * 70)
    logger.info("STEP A: BULLISH OR SETUP")
    logger.info("=" * 70)
    
    # Check if bullish (ORC > ORO)
    orc = or_data.get('ORC', 0)
    oro = or_data.get('ORO', 0)
    
    if orc <= oro:
        logger.info(f"ORC (${orc:.2f}) <= ORO (${oro:.2f}) - Not bullish, skipping Step A")
        return None
    
    logger.info(f"✅ Bullish OR detected: ORC (${orc:.2f}) > ORO (${oro:.2f})")
    
    # Set SPX_entry = ORC (10:00 close)
    spx_entry = orc
    trigger_time = datetime.now(ET)
    
    logger.info(f"SPX_entry = ORC = ${spx_entry:.2f}")
    
    # Compute strikes ONCE for PUT spread
    k_short, k_long = StrikeCalculator.calculate_put_spread_strikes(spx_entry)
    
    logger.info(f"PUT spread strikes: K_short=${k_short:.2f}, K_long=${k_long:.2f}")
    
    # Monitor quotes and place order
    return monitor_quotes_and_place_order(
        date=date,
        spx_entry=spx_entry,
        k_short=k_short,
        k_long=k_long,
        option_type='PUT',
        setup='Bullish OR',
        or_data=or_data,
        account_equity=account_equity,
        trigger_time=trigger_time
    )


def step_b_bearish_orl_breakout(date: datetime, or_data: Dict, account_equity: float) -> Optional[Dict]:
    """
    Step B: Bearish ORL Breakout setup (10:00-12:00).
    
    Scans for breakout by checking completed 30-minute candles one by one:
    - 10:00-10:30 candle: check at 10:30
    - 10:30-11:00 candle: check at 11:00
    - 11:00-11:30 candle: check at 11:30
    - 11:30-12:00 candle: check at 12:00
    
    Args:
        date: Trading date
        or_data: Opening Range data
        account_equity: Account equity
    
    Returns:
        Order details if placed, None otherwise
    """
    logger.info("")
    logger.info("=" * 70)
    logger.info("STEP B: BEARISH ORL BREAKOUT SETUP")
    logger.info("=" * 70)
    
    # Precondition: bearishOR = (ORC < ORO)
    orc = or_data.get('ORC', 0)
    oro = or_data.get('ORO', 0)
    
    if orc >= oro:
        logger.info(f"ORC (${orc:.2f}) >= ORO (${oro:.2f}) - Not bearish, skipping Step B")
        return None
    
    logger.info(f"✅ Bearish OR detected: ORC (${orc:.2f}) < ORO (${oro:.2f})")
    
    orl = or_data.get('ORL', 0)
    logger.info(f"Scanning for breakout: bar_close < ORL (${orl:.2f})")
    logger.info("Will check completed candles at: 10:30, 11:00, 11:30, 12:00")
    
    market_data = MarketDataFetcher()
    
    # Define the candle windows to check (each closes 30 minutes after start)
    candle_windows = [
        (10, 0, 10, 30),  # 10:00-10:30, check at 10:30
        (10, 30, 11, 0),  # 10:30-11:00, check at 11:00
        (11, 0, 11, 30),  # 11:00-11:30, check at 11:30
        (11, 30, 12, 0),  # 11:30-12:00, check at 12:00
    ]
    
    # Check each candle window as it completes
    for start_hour, start_min, end_hour, end_min in candle_windows:
        check_time = dt_time(end_hour, end_min)
        
        # Wait until the candle closes
        wait_until_time(check_time, f"Candle close ({start_hour:02d}:{start_min:02d}-{end_hour:02d}:{end_min:02d})")
        
        # Get the completed candle
        candles = market_data.get_30min_candles(
            date,
            start_hour=start_hour,
            start_minute=start_min,
            end_hour=end_hour,
            end_minute=end_min
        )
        
        if not candles:
            logger.warning(f"No candle found for {start_hour:02d}:{start_min:02d}-{end_hour:02d}:{end_min:02d} window")
            continue
        
        # Get the candle (should be only one)
        candle = candles[0] if candles else None
        if not candle:
            continue
        
        bar_close = candle.get('close', 0)
        logger.info(f"Checking {start_hour:02d}:{start_min:02d}-{end_hour:02d}:{end_min:02d} candle: bar_close=${bar_close:.2f}, ORL=${orl:.2f}")
        
        # Check for breakout
        if bar_close < orl:
            logger.info(f"✅ Breakout found: bar_close=${bar_close:.2f} < ORL=${orl:.2f}")
            
            # Set SPX_entry = breakout_bar_close
            spx_entry = bar_close
            trigger_time = datetime.now(ET)
            
            logger.info(f"SPX_entry = breakout_bar_close = ${spx_entry:.2f}")
            
            # Compute strikes ONCE for CALL spread
            k_short, k_long = StrikeCalculator.calculate_call_spread_strikes(spx_entry)
            
            logger.info(f"CALL spread strikes: K_short=${k_short:.2f}, K_long=${k_long:.2f}")
            
            # Monitor quotes and place order
            return monitor_quotes_and_place_order(
                date=date,
                spx_entry=spx_entry,
                k_short=k_short,
                k_long=k_long,
                option_type='CALL',
                setup='Bearish ORL Breakout',
                or_data=or_data,
                account_equity=account_equity,
                trigger_time=trigger_time
            )
        else:
            logger.info(f"No breakout: bar_close=${bar_close:.2f} >= ORL=${orl:.2f}")
    
    # No breakout found in any completed candle
    logger.info("No breakout candle found (bar_close >= ORL for all completed bars)")
    return None


def calculate_eod_pl(date: datetime, trade_data: Dict) -> Dict:
    """
    Calculate P/L at expiration (16:00).
    
    Args:
        date: Trading date
        trade_data: Trade data dictionary
    
    Returns:
        Updated trade data with P/L information
    """
    logger.info("")
    logger.info("=" * 70)
    logger.info("CALCULATING EOD P/L")
    logger.info("=" * 70)
    
    # Get SPX close price
    market_data = MarketDataFetcher()
    spx_close = market_data.get_spx_close_price(date)
    
    if not spx_close:
        logger.warning("Could not get SPX close price")
        return trade_data
    
    logger.info(f"SPX_close (16:00): ${spx_close:.2f}")
    
    # Get trade parameters
    trade_type = trade_data.get('trade_type', '')
    k_short = float(trade_data.get('K_short', 0))
    c_net_fill = float(trade_data.get('C_net_fill', 0))
    qty = int(trade_data.get('qty', 0))
    
    # Calculate P/L
    if trade_type == 'PUT':
        pl_data = PLCalculator.calculate_put_spread_pl(
            k_short=k_short,
            spx_close=spx_close,
            c_net_fill=c_net_fill,
            qty=qty
        )
    else:  # CALL
        pl_data = PLCalculator.calculate_call_spread_pl(
            k_short=k_short,
            spx_close=spx_close,
            c_net_fill=c_net_fill,
            qty=qty
        )
    
    # Get account equity after
    account_mgr = AccountManager()
    try:
        equity_after = account_mgr.get_net_liquidity()
    except:
        equity_after = None
    
    # Update trade data
    trade_data['SPX_close'] = spx_close
    trade_data['settlement_value'] = pl_data['settlement_value']
    trade_data['pnl_per_spread'] = pl_data['pnl_per_spread']
    trade_data['total_pnl'] = pl_data['total_pnl']
    if equity_after:
        trade_data['equity_after'] = equity_after
    
    # Log updated trade
    trade_logger = TradeLogger()
    # Note: This will append a new row. In production, you might want to update the existing row.
    trade_logger.log_trade(trade_data)
    
    # Save to S3 at end of day
    try:
        from src.storage.s3_service import S3Service
        s3_bucket = os.getenv('AWS_S3_BUCKET_NAME')
        if s3_bucket:
            s3_service = S3Service(bucket_name=s3_bucket)
            trade_logger.s3_service = s3_service
            trade_logger.save_to_s3()
    except Exception as e:
        logger.warning(f"Failed to save trades CSV to S3: {e}")
    
    return trade_data


def main():
    """Main automation loop."""
    parser = argparse.ArgumentParser(description='SPX ATM Credit Spread Bot')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (do not place orders)')
    args = parser.parse_args()
    
    # FIRST THING: Download .env file from S3 (if configured)
    # This must happen before loading environment variables
    # Uses IAM role on EC2 (configured via IAM role attached to EC2 instance)
    # .env is stored in: spx-atm-credit-spread-bot-config bucket
    env_file_path = '.env'
    env_downloaded = False
    
    try:
        from src.storage.s3_service import S3Service
        
        # Get bucket name from system environment variable (set on EC2)
        # Must be set to: spx-atm-credit-spread-bot-config
        config_bucket = os.environ.get('AWS_S3_CONFIG_BUCKET_NAME')
        env_s3_key = os.environ.get('AWS_S3_ENV_KEY', '.env')
        
        if config_bucket:
            try:
                logger.info(f"Checking for .env in S3 bucket: {config_bucket}")
                # Use IAM role (no credentials needed - EC2 IAM role provides access)
                s3_service = S3Service(bucket_name=config_bucket)
                if s3_service.test_connection():
                    if s3_service.file_exists(env_s3_key):
                        logger.info(f"Downloading .env from S3: s3://{config_bucket}/{env_s3_key}")
                        if s3_service.download_file(env_s3_key, env_file_path):
                            logger.info("✅ Successfully downloaded .env from S3")
                            env_downloaded = True
                        else:
                            logger.warning(f"⚠️  Failed to download .env from {config_bucket}, using local if exists")
                    else:
                        logger.info(f".env not found in S3 (s3://{config_bucket}/{env_s3_key}), using local if exists")
                else:
                    logger.warning(f"⚠️  Could not connect to {config_bucket}, using local .env if exists")
            except Exception as e:
                logger.warning(f"Error downloading .env from S3: {e}, using local if exists")
        else:
            logger.info("S3 config bucket not configured (AWS_S3_CONFIG_BUCKET_NAME not set), using local .env if exists")
    except Exception as e:
        logger.debug(f"S3 not available for .env download (using local if exists): {e}")
    
    # Now load environment variables from .env file (local or downloaded)
    from dotenv import load_dotenv
    load_dotenv()
    
    # SECOND: Download tokens.json from S3 (if configured)
    # This must happen before any authentication attempts
    # Uses IAM role on EC2 (configured via IAM role attached to EC2 instance)
    # tokens.json is stored in: my-tokens bucket (separate from .env bucket)
    try:
        from src.storage.s3_service import S3Service
        
        # tokens.json MUST come from the dedicated token bucket (my-tokens)
        # Do NOT fall back to config bucket - tokens.json is in a separate bucket
        token_bucket_name = os.getenv('AWS_S3_TOKEN_BUCKET_NAME')
        if token_bucket_name:
            logger.info(f"Checking for tokens.json in S3 bucket: {token_bucket_name}")
            try:
                # Use IAM role (no credentials needed - EC2 IAM role provides access)
                s3_service = S3Service(bucket_name=token_bucket_name)
                if s3_service.test_connection():
                    token_s3_key = os.getenv('AWS_S3_TOKEN_KEY', 'tokens.json')
                    token_file_path = Config.TOKEN_FILE
                    if s3_service.file_exists(token_s3_key):
                        logger.info(f"Downloading tokens.json from S3: s3://{token_bucket_name}/{token_s3_key}")
                        if s3_service.download_file(token_s3_key, token_file_path):
                            logger.info("✅ Successfully downloaded tokens.json from S3")
                        else:
                            logger.warning("⚠️  Failed to download tokens.json from S3, using local file if exists")
                    else:
                        logger.info(f"tokens.json not found in S3 (s3://{token_bucket_name}/{token_s3_key}), using local file if exists")
                else:
                    logger.warning(f"⚠️  S3 connection to {token_bucket_name} failed, using local tokens.json if exists")
            except Exception as e:
                logger.warning(f"⚠️  S3 token download failed (using local if exists): {e}")
        else:
            logger.info("S3 token bucket not configured (set AWS_S3_TOKEN_BUCKET_NAME to 'my-tokens'), using local tokens.json if exists")
    except Exception as e:
        logger.debug(f"S3 not available for token download (using local if exists): {e}")
    
    # Override config if --dry-run flag is provided
    if args.dry_run:
        Config.DRY_RUN = True
        logger.warning("⚠️  --dry-run flag provided: DRY_RUN mode enabled")
    
    logger.info("=" * 70)
    logger.info("SPX ATM CREDIT SPREAD BOT - 0DTE STRATEGY")
    logger.info("=" * 70)
    logger.info("")
    logger.info(f"SAFETY GATES:")
    logger.info(f"  DRY_RUN = {Config.DRY_RUN}")
    logger.info(f"  ENABLE_LIVE_TRADING = {Config.ENABLE_LIVE_TRADING}")
    if Config.DRY_RUN or not Config.ENABLE_LIVE_TRADING:
        logger.warning("  🚫 LIVE TRADING DISABLED - Orders will NOT be placed")
    else:
        logger.warning("  ⚠️  LIVE TRADING ENABLED - Real orders will be placed!")
    logger.info("")
    
    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    # Get today's date
    today = datetime.now(ET)
    today_dt = ET.localize(datetime.combine(today.date(), dt_time(9, 30)))
    
    logger.info(f"Trading Date: {today_dt.strftime('%Y-%m-%d')}")
    logger.info("")
    
    # Wait until market open
    wait_until_time(MARKET_OPEN, "Market Open")
    
    # Wait until 10:00 (when the Opening Range candle closes)
    wait_until_time(OR_END, "OR End (10:00)")
    
    # Get Opening Range AFTER the candle has closed
    logger.info("")
    logger.info("=" * 70)
    logger.info("GETTING OPENING RANGE (09:30-10:00)")
    logger.info("=" * 70)
    
    or_tracker = OpeningRangeTracker()
    or_data = or_tracker.get_opening_range(today_dt)
    
    if not or_data:
        logger.error("❌ Could not get Opening Range - Exiting")
        sys.exit(1)
    
    # Get account equity for position sizing
    account_mgr = AccountManager()
    try:
        account_equity = account_mgr.get_net_liquidity()
        logger.info(f"Account Equity: ${account_equity:,.2f}")
    except Exception as e:
        logger.error(f"❌ Could not get account equity: {e}")
        sys.exit(1)
    
    # Step A: Bullish OR setup
    order_result = step_a_bullish_or(today_dt, or_data, account_equity)
    
    # Step B: Bearish ORL Breakout (only if Step A didn't trigger AND didn't place a trade)
    # Note: Step A ends the day if no fill by 12:00, so Step B only runs if Step A didn't trigger at all
    if not order_result:
        # Check if Step A triggered but didn't fill (would have returned None with "no fill by 12:00" message)
        # Actually, if Step A triggered, it would have monitored until 12:00 and returned None if no fill
        # So we need to check if Step A was even eligible (ORC > ORO)
        orc = or_data.get('ORC', 0)
        oro = or_data.get('ORO', 0)
        
        # Step B only runs if Step A didn't trigger (i.e., ORC <= ORO, meaning bearish OR)
        if orc < oro:
            order_result = step_b_bearish_orl_breakout(today_dt, or_data, account_equity)
        else:
            logger.info("Step A was eligible (ORC >= ORO) but no trade was placed by 12:00")
            logger.info("Per spec: END DAY - Do NOT evaluate bearish setup")
    
    # Step C: No trade
    if not order_result:
        logger.info("")
        logger.info("=" * 70)
        logger.info("NO TRADE TODAY")
        logger.info("=" * 70)
        logger.info("Neither Step A nor Step B resulted in a trade.")
        sys.exit(0)
    
    # Wait until market close for P/L calculation
    logger.info("")
    logger.info("Waiting until market close (16:00 ET) for P/L calculation...")
    wait_until_time(MARKET_CLOSE, "Market Close")
    
    # Calculate EOD P/L
    trade_data = order_result.get('trade_data', {})
    if trade_data:
        calculate_eod_pl(today_dt, trade_data)
        
        # Generate and send EOD report
        logger.info("")
        logger.info("=" * 70)
        logger.info("GENERATING END OF DAY REPORT")
        logger.info("=" * 70)
        
        try:
            from src.reports.eod_report import EODReport
            
            # Get setup name from trade data or determine from OR
            setup = trade_data.get('setup', 'Unknown')
            if not setup or setup == 'Unknown':
                orc = or_data.get('ORC', 0)
                oro = or_data.get('ORO', 0)
                if orc > oro:
                    setup = 'Bullish OR'
                elif orc < oro:
                    setup = 'Bearish ORL Breakout'
                else:
                    setup = 'Unknown'
            
            eod_report = EODReport()
            report_path = eod_report.generate_eod_report(
                date=today_dt,
                trade_data=trade_data,
                or_data=or_data,
                setup=setup
            )
            
            # Send email if configured
            recipient_email = os.getenv('EMAIL_RECIPIENT')
            if recipient_email:
                logger.info("")
                logger.info("Sending EOD report via email...")
                email_sent = eod_report.send_eod_email(report_path, recipient_email=recipient_email)
                if email_sent:
                    logger.info("✅ EOD email sent successfully!")
                else:
                    logger.warning("⚠️  EOD email sending failed. Report saved to file.")
            else:
                logger.info("")
                logger.info("Email recipient not configured (EMAIL_RECIPIENT not set in .env)")
                logger.info("Report saved to file only.")
        except Exception as e:
            logger.error(f"❌ Failed to generate/send EOD report: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("✅ TRADING DAY COMPLETE")
    logger.info("=" * 70)


if __name__ == '__main__':
    main()

