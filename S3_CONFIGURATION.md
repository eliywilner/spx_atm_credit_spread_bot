# S3 Configuration Guide

## Overview

The bot downloads `.env` and `tokens.json` from S3 at startup before running. This allows you to:
- Store credentials securely in S3
- Pull fresh credentials on each run
- Use IAM role on EC2 (no credentials needed in code)

## Configuration

### IAM Role Setup (REQUIRED)

**The bot uses IAM role credentials on EC2 - no access keys needed in code.**

1. **Attach IAM Role to EC2 Instance**:
   - Go to EC2 Console → Select your instance
   - Actions → Security → Modify IAM role
   - Attach IAM role with S3 read permissions

2. **IAM Role Permissions** (minimum required):
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:GetObject",
           "s3:ListBucket"
         ],
         "Resource": [
           "arn:aws:s3:::your-bucket-name/*",
           "arn:aws:s3:::your-bucket-name"
         ]
       }
     ]
   }
   ```

### Environment Variables (Set on EC2)

Set these environment variables on your EC2 instance before running the bot:

```bash
# For .env file (REQUIRED if using S3)
export AWS_S3_CONFIG_BUCKET_NAME=your-config-bucket-name

# For tokens.json (optional - uses config bucket if not set)
export AWS_S3_TOKEN_BUCKET_NAME=your-token-bucket-name

# Optional: Custom S3 keys
export AWS_S3_ENV_KEY=.env              # Default: .env
export AWS_S3_TOKEN_KEY=tokens.json     # Default: tokens.json
```

**No hardcoded bucket names** - everything is configured via environment variables.

## How It Works

### 1. .env Download (Before Environment Variables Loaded)

1. Bot checks system environment variable `AWS_S3_CONFIG_BUCKET_NAME` (must be set on EC2)
2. Downloads `.env` from S3 using IAM role (no credentials needed in code)
3. Falls back to local `.env` if S3 download fails or bucket not configured

### 2. tokens.json Download (After .env Loaded)

1. Bot loads `.env` file (from S3 or local)
2. Checks for `AWS_S3_TOKEN_BUCKET_NAME` (or uses config bucket)
3. Downloads `tokens.json` from S3
4. Falls back to local `tokens.json` if S3 download fails

## IAM Role Setup (Recommended for EC2)

1. Create IAM role with S3 read permissions:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:GetObject",
           "s3:ListBucket"
         ],
         "Resource": [
           "arn:aws:s3:::your-bucket-name/*",
           "arn:aws:s3:::your-bucket-name"
         ]
       }
     ]
   }
   ```

2. Attach role to EC2 instance
3. No credentials needed in code - IAM role provides access automatically

## S3 File Structure

Your S3 buckets should contain:

```
your-config-bucket/
  └── .env

your-token-bucket/  (or same bucket)
  └── tokens.json
```

## Testing

Test S3 download before running the bot:

```bash
# Set bucket name (must match your IAM role permissions)
export AWS_S3_CONFIG_BUCKET_NAME=your-bucket-name

# Test connection (uses IAM role automatically)
python3 -c "
from src.storage.s3_service import S3Service
import os
bucket = os.environ.get('AWS_S3_CONFIG_BUCKET_NAME')
if bucket:
    s3 = S3Service(bucket_name=bucket)
    if s3.test_connection():
        print('✅ S3 Connected')
        if s3.file_exists('.env'):
            print('✅ .env found in S3')
        else:
            print('⚠️  .env not found in S3')
    else:
        print('❌ S3 Connection Failed - Check IAM role permissions')
else:
    print('⚠️  AWS_S3_CONFIG_BUCKET_NAME not set')
"
```

## Fallback Behavior

- If S3 is unavailable → Uses local files
- If file not found in S3 → Uses local files
- If download fails → Uses local files
- Bot continues running even if S3 download fails

This ensures the bot can run even if S3 is temporarily unavailable.

