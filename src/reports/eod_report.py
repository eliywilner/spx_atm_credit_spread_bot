"""
End of Day Report Generator for SPX ATM Credit Spread Bot.

Generates and sends EOD email reports with trade summary and P/L.
"""
import os
import smtplib
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pytz

from src.accounts.account_manager import AccountManager
from src.utils.logger import setup_logger

logger = setup_logger(__name__)
ET = pytz.timezone('US/Eastern')


class EODReport:
    """Generates and sends end-of-day trading reports."""
    
    def __init__(self, reports_dir: Optional[str] = None):
        """
        Initialize EOD report generator.
        
        Args:
            reports_dir: Directory to save reports. If None, uses 'reports' in project root.
        """
        if reports_dir is None:
            project_root = Path(__file__).parent.parent.parent
            reports_dir = project_root / 'reports'
        
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        self.account_mgr = AccountManager()
        
        logger.info(f"EODReport initialized with reports directory: {self.reports_dir}")
    
    def generate_eod_report(
        self,
        date: datetime,
        trade_data: Dict,
        or_data: Dict,
        setup: str  # 'Bullish OR' or 'Bearish ORL Breakout'
    ) -> str:
        """
        Generate end-of-day report.
        
        Args:
            date: Trading date
            trade_data: Trade data dictionary with all trade details
            or_data: Opening Range data (ORO, ORH, ORL, ORC)
            setup: Setup name ('Bullish OR' or 'Bearish ORL Breakout')
        
        Returns:
            str: Path to generated report file
        """
        date_str = date.strftime('%Y-%m-%d')
        report_filename = f"eod_report_{date_str}.txt"
        report_path = self.reports_dir / report_filename
        
        logger.info("=" * 70)
        logger.info("GENERATING END OF DAY REPORT")
        logger.info("=" * 70)
        logger.info(f"Date: {date_str}")
        logger.info("")
        
        # Get account information
        try:
            account_equity = self.account_mgr.get_net_liquidity()
        except:
            account_equity = trade_data.get('equity_after', trade_data.get('equity_before', 'N/A'))
        
        # Build report
        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append(f"END OF DAY TRADING REPORT - {date_str}")
        report_lines.append("=" * 70)
        report_lines.append(f"Generated: {datetime.now(ET).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        report_lines.append("")
        
        # Strategy Section
        report_lines.append("=" * 70)
        report_lines.append("STRATEGY")
        report_lines.append("=" * 70)
        report_lines.append(f"Setup:                    {setup}")
        report_lines.append(f"Trade Type:               {trade_data.get('trade_type', 'N/A')}")
        report_lines.append("")
        
        # Opening Range Section
        report_lines.append("=" * 70)
        report_lines.append("OPENING RANGE (09:30-10:00 ET)")
        report_lines.append("=" * 70)
        oro = or_data.get('ORO', 0)
        orh = or_data.get('ORH', 0)
        orl = or_data.get('ORL', 0)
        orc = or_data.get('ORC', 0)
        report_lines.append(f"ORO (Open):               ${oro:.2f}")
        report_lines.append(f"ORH (High):               ${orh:.2f}")
        report_lines.append(f"ORL (Low):                ${orl:.2f}")
        report_lines.append(f"ORC (Close):              ${orc:.2f}")
        report_lines.append("")
        
        # Trade Details Section
        report_lines.append("=" * 70)
        report_lines.append("TRADE DETAILS")
        report_lines.append("=" * 70)
        report_lines.append(f"SPX Entry:                ${trade_data.get('SPX_entry', 0):.2f}")
        report_lines.append(f"Trigger Time:             {trade_data.get('trigger_time', 'N/A')}")
        report_lines.append(f"Fill Time:                {trade_data.get('fill_time', 'N/A')}")
        report_lines.append("")
        report_lines.append("Strikes:")
        report_lines.append(f"  K_short:                ${trade_data.get('K_short', 0):.2f}")
        report_lines.append(f"  K_long:                 ${trade_data.get('K_long', 0):.2f}")
        report_lines.append(f"  Spread Width:           10 points")
        report_lines.append("")
        report_lines.append("Credit:")
        report_lines.append(f"  C_gross (fill):          ${trade_data.get('C_gross_fill', 0):.2f}")
        report_lines.append(f"  Slippage Buffer (S):     ${trade_data.get('S', 0):.2f}")
        report_lines.append(f"  C_net (fill):            ${trade_data.get('C_net_fill', 0):.2f}")
        report_lines.append("")
        report_lines.append("Position:")
        report_lines.append(f"  Quantity:                {trade_data.get('qty', 0)} contracts")
        report_lines.append(f"  Daily Risk Budget:       ${trade_data.get('R_day', 0):,.2f}")
        report_lines.append(f"  Max Loss per Spread:     ${trade_data.get('maxLossPerSpread', 0):,.2f}")
        report_lines.append("")
        report_lines.append(f"Order ID:                 {trade_data.get('order_id', 'N/A')}")
        report_lines.append(f"Order Status:             {trade_data.get('order_status', 'N/A')}")
        report_lines.append("")
        
        # P/L Section
        report_lines.append("=" * 70)
        report_lines.append("PROFIT/LOSS (AT EXPIRATION)")
        report_lines.append("=" * 70)
        spx_close = trade_data.get('SPX_close', '')
        if spx_close:
            report_lines.append(f"SPX Close (16:00 ET):     ${spx_close:.2f}")
            report_lines.append(f"Settlement Value:        ${trade_data.get('settlement_value', 0):.2f} points")
            report_lines.append(f"P/L per Spread:           ${trade_data.get('pnl_per_spread', 0):,.2f}")
            report_lines.append(f"Total P/L:                ${trade_data.get('total_pnl', 0):,.2f}")
        else:
            report_lines.append("P/L calculation pending...")
        report_lines.append("")
        
        # Account Section
        report_lines.append("=" * 70)
        report_lines.append("ACCOUNT")
        report_lines.append("=" * 70)
        equity_before = trade_data.get('equity_before', 'N/A')
        equity_after = trade_data.get('equity_after', 'N/A')
        if isinstance(equity_before, (int, float)):
            report_lines.append(f"Equity Before:            ${equity_before:,.2f}")
        else:
            report_lines.append(f"Equity Before:            {equity_before}")
        if isinstance(equity_after, (int, float)):
            report_lines.append(f"Equity After:             ${equity_after:,.2f}")
        else:
            report_lines.append(f"Equity After:             {equity_after}")
        if isinstance(account_equity, (int, float)):
            report_lines.append(f"Current Equity:           ${account_equity:,.2f}")
        report_lines.append("")
        
        # Write report to file
        report_content = '\n'.join(report_lines)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"✅ EOD report saved to: {report_path}")
        return str(report_path)
    
    def send_eod_email(
        self,
        report_path: str,
        recipient_email: Optional[str] = None,
        smtp_server: str = 'smtp.gmail.com',
        smtp_port: int = 587,
        sender_email: Optional[str] = None,
        sender_password: Optional[str] = None
    ) -> bool:
        """
        Send EOD report via email.
        
        Args:
            report_path: Path to report file
            recipient_email: Email address(es) to send report to. If None, uses EMAIL_RECIPIENT from env.
            smtp_server: SMTP server (default: smtp.gmail.com)
            smtp_port: SMTP port (default: 587 for TLS)
            sender_email: Sender email address (from environment if None)
            sender_password: Sender password/app password (from environment if None)
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        # Get email credentials from environment or parameters
        if sender_email is None:
            sender_email = os.getenv('EMAIL_SENDER')
        if sender_password is None:
            sender_password = os.getenv('EMAIL_PASSWORD')
        if recipient_email is None:
            recipient_email = os.getenv('EMAIL_RECIPIENT')
        
        if not sender_email or not sender_password:
            logger.error("Email credentials not configured. Set EMAIL_SENDER and EMAIL_PASSWORD in .env file.")
            return False
        
        if not recipient_email:
            logger.warning("Email recipient not configured. Set EMAIL_RECIPIENT in .env file.")
            return False
        
        try:
            # Parse recipient emails (support comma or space separated)
            recipients = []
            if ',' in recipient_email:
                recipients = [email.strip() for email in recipient_email.split(',')]
            elif ' ' in recipient_email and '@' in recipient_email:
                recipients = [email.strip() for email in recipient_email.split() if '@' in email]
            else:
                recipients = [recipient_email.strip()]
            
            recipients = [r for r in recipients if r]
            
            if not recipients:
                logger.error("No valid recipient email addresses found")
                return False
            
            # Read report content
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()
            
            # Extract date from report path
            date_str = Path(report_path).stem.replace('eod_report_', '')
            
            # Create email
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"SPX ATM Credit Spread Bot - EOD Report - {date_str}"
            
            # Add report as plain text
            msg.attach(MIMEText(report_content, 'plain'))
            
            # Send email
            recipient_list_str = ', '.join(recipients)
            logger.info(f"Sending EOD email to {len(recipients)} recipient(s): {recipient_list_str}")
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipients, msg.as_string())
            
            logger.info(f"✅ EOD email sent successfully to {len(recipients)} recipient(s)!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send EOD email: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

