# Email Setup for EOD Reports

The bot automatically sends end-of-day (EOD) trading reports via email after market close.

## Required Environment Variables

Add the following to your `.env` file:

```bash
# Email Configuration (for EOD reports)
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_RECIPIENT=recipient-email@gmail.com
```

### Environment Variables

- **EMAIL_SENDER**: Email address to send from (must match the account for EMAIL_PASSWORD)
- **EMAIL_PASSWORD**: App password or account password (see provider-specific instructions below)
- **EMAIL_RECIPIENT**: Email address(es) to send reports to
  - Single email: `recipient@example.com`
  - Multiple emails (comma-separated): `email1@example.com,email2@example.com`
  - Multiple emails (space-separated): `email1@example.com email2@example.com`

## Gmail Setup (Recommended)

### Step 1: Enable 2-Factor Authentication
1. Go to your [Google Account settings](https://myaccount.google.com/)
2. Navigate to Security
3. Enable 2-Factor Authentication if not already enabled

### Step 2: Generate App Password
1. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
2. Select "Mail" as the app
3. Select "Other (Custom name)" as the device
4. Enter "SPX ATM Bot" as the name
5. Click "Generate"
6. Copy the 16-character password (it will look like: `abcd efgh ijkl mnop`)

### Step 3: Add to .env File
```bash
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=abcdefghijklmnop  # Use the 16-character app password (remove spaces)
EMAIL_RECIPIENT=recipient1@gmail.com,recipient2@gmail.com
```

**Important:** 
- Use the **App Password**, NOT your regular Gmail password
- Remove spaces from the app password when adding to `.env`
- The app password is 16 characters without spaces

## Other Email Providers

### Outlook/Hotmail
```bash
EMAIL_SENDER=your-email@outlook.com
EMAIL_PASSWORD=your-password
EMAIL_RECIPIENT=recipient@example.com
```
- SMTP Server: `smtp-mail.outlook.com` (default)
- SMTP Port: `587` (default)

### Yahoo Mail
```bash
EMAIL_SENDER=your-email@yahoo.com
EMAIL_PASSWORD=your-app-password  # Generate app password from Yahoo account settings
EMAIL_RECIPIENT=recipient@example.com
```
- SMTP Server: `smtp.mail.yahoo.com` (default)
- SMTP Port: `587` (default)

### Custom SMTP Server
The bot uses Gmail SMTP by default (`smtp.gmail.com:587`). To use a different provider, you can modify the code in `src/reports/eod_report.py`:

```python
eod_report.send_eod_email(
    report_path,
    recipient_email='recipient@example.com',
    smtp_server='smtp.your-provider.com',
    smtp_port=587
)
```

## When Emails Are Sent

- **Timing**: After market close (16:00 ET) when P/L calculation is complete
- **Condition**: Only sent if a trade was taken during the day
- **Content**: Complete EOD report with trade details, P/L, and account information

## Report Content

The EOD email report includes:
- **Strategy**: Setup name (Bullish OR / Bearish ORL Breakout)
- **Opening Range**: ORO, ORH, ORL, ORC
- **Trade Details**: 
  - SPX entry price
  - Trigger time and fill time
  - Strikes (K_short, K_long)
  - Credit received (C_gross, C_net)
  - Position size (quantity, risk budget)
- **Profit/Loss**: 
  - SPX close price
  - Settlement value
  - P/L per spread
  - Total P/L
- **Account**: Equity before/after trade

## Testing Email

You can test email functionality by running:

```python
from src.reports.eod_report import EODReport
import os
from dotenv import load_dotenv

load_dotenv()

# Create a test report
eod_report = EODReport()
# ... generate test report ...

# Send test email
recipient = os.getenv('EMAIL_RECIPIENT')
if recipient:
    eod_report.send_eod_email(report_path, recipient_email=recipient)
```

## Troubleshooting

### "Authentication failed"
- **Gmail**: Make sure you're using an App Password (not your regular password)
- **Gmail**: Ensure 2FA is enabled
- Check that `EMAIL_SENDER` and `EMAIL_PASSWORD` are set correctly in `.env`
- Verify there are no extra spaces in the password

### "Connection refused" or "Connection timeout"
- Check your firewall settings
- Verify SMTP server and port are correct
- Some networks block SMTP ports (587, 465)
- Try using a different network or VPN

### Email not received
- Check spam/junk folder
- Verify `EMAIL_RECIPIENT` is correct
- Check that email was actually sent (check logs)
- Verify sender email is not blocked by recipient's email provider

### "Email recipient not configured"
- Set `EMAIL_RECIPIENT` in `.env` file
- Bot will still generate and save report locally even if email fails

## Security Notes

- **Never commit `.env` file to git** (already in `.gitignore`)
- App passwords are safer than regular passwords
- Consider using a dedicated email account for the bot
- Rotate passwords periodically
- Store `.env` file securely (especially on EC2)

## Email Not Sent?

If email sending fails:
- Report is still saved to `reports/eod_report_YYYY-MM-DD.txt`
- Check bot logs for error messages
- Bot continues running normally (email failure doesn't stop the bot)

## Example .env Configuration

```bash
# Schwab API (required)
SCHWAB_CLIENT_ID=your_client_id
SCHWAB_CLIENT_SECRET=your_client_secret
SCHWAB_REDIRECT_URI=https://127.0.0.1:8080/callback

# Email Configuration (for EOD reports)
EMAIL_SENDER=your-bot-email@gmail.com
EMAIL_PASSWORD=abcdefghijklmnop
EMAIL_RECIPIENT=your-email@gmail.com,another-email@gmail.com

# Position Sizing (optional - has defaults)
DAILY_RISK_PCT=0.03
MIN_CONTRACTS=1
MAX_CONTRACTS=50

# Safety Gates (optional - defaults are safe)
DRY_RUN=true
ENABLE_LIVE_TRADING=false

# S3 Configuration (for CSV backup)
AWS_S3_BUCKET_NAME=your-bucket-name
```

