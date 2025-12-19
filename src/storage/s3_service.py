"""
S3 Service for uploading and downloading CSV tracking files.

Handles S3 bucket operations for daily trading data CSV file.
"""
import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Optional
from pathlib import Path
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class S3Service:
    """Service for S3 operations."""
    
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = 'us-east-1'
    ):
        """
        Initialize S3 service.
        
        Args:
            bucket_name: S3 bucket name. If None, reads from environment variable.
            aws_access_key_id: AWS access key. If None, reads from environment variable.
            aws_secret_access_key: AWS secret key. If None, reads from environment variable.
            region_name: AWS region name (default: us-east-1)
        """
        # Get credentials from environment if not provided
        self.bucket_name = bucket_name or os.getenv('AWS_S3_BUCKET_NAME')
        aws_access_key_id = aws_access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = aws_secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY')
        self.region_name = region_name or os.getenv('AWS_REGION', 'us-east-1')
        
        # Initialize S3 client
        try:
            if aws_access_key_id and aws_secret_access_key:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    region_name=self.region_name
                )
            else:
                # Use default credentials (IAM role, environment, or ~/.aws/credentials)
                # This allows S3Service to work on EC2 with IAM role (no credentials needed)
                self.s3_client = boto3.client('s3', region_name=self.region_name)
            
            if self.bucket_name:
                logger.info(f"S3Service initialized for bucket: {self.bucket_name}")
            else:
                logger.info("S3Service initialized (no bucket specified, will be set per operation)")
        except NoCredentialsError:
            # On EC2 with IAM role, this shouldn't happen, but if it does, log warning
            logger.warning("AWS credentials not found. If using IAM role on EC2, this should work. Continuing anyway...")
            self.s3_client = boto3.client('s3', region_name=self.region_name)
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise
    
    def upload_file(self, local_file_path: str, s3_key: str) -> bool:
        """
        Upload a file to S3.
        
        Args:
            local_file_path: Path to local file to upload
            s3_key: S3 object key (path in bucket)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            local_path = Path(local_file_path)
            if not local_path.exists():
                logger.error(f"Local file does not exist: {local_file_path}")
                return False
            
            logger.info(f"Uploading {local_file_path} to s3://{self.bucket_name}/{s3_key}")
            self.s3_client.upload_file(
                str(local_path),
                self.bucket_name,
                s3_key
            )
            logger.info(f"✅ Successfully uploaded to s3://{self.bucket_name}/{s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading to S3: {e}")
            return False
    
    def download_file(self, s3_key: str, local_file_path: str) -> bool:
        """
        Download a file from S3.
        
        Args:
            s3_key: S3 object key (path in bucket)
            local_file_path: Path to save downloaded file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            local_path = Path(local_file_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Downloading s3://{self.bucket_name}/{s3_key} to {local_file_path}")
            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                str(local_path)
            )
            logger.info(f"✅ Successfully downloaded to {local_file_path}")
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchKey':
                logger.warning(f"File not found in S3: s3://{self.bucket_name}/{s3_key}")
                return False
            else:
                logger.error(f"Failed to download file from S3: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error downloading from S3: {e}")
            return False
    
    def file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in S3.
        
        Args:
            s3_key: S3 object key (path in bucket)
        
        Returns:
            bool: True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                return False
            else:
                logger.warning(f"Error checking file existence: {e}")
                return False
        except Exception as e:
            logger.warning(f"Unexpected error checking file existence: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test S3 connection and bucket access.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"✅ Successfully connected to S3 bucket: {self.bucket_name}")
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                logger.error(f"S3 bucket not found: {self.bucket_name}")
            elif error_code == '403':
                logger.error(f"Access denied to S3 bucket: {self.bucket_name}")
            else:
                logger.error(f"Failed to access S3 bucket: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error testing S3 connection: {e}")
            return False

