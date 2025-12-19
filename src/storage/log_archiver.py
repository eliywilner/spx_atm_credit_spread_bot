"""
Log Archiver - Uploads logs to S3 and deletes local copies.

Archives log files at end of day to prevent disk space issues on EC2.
"""
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import pytz
from src.utils.logger import setup_logger
from src.storage.s3_service import S3Service

logger = setup_logger(__name__)

ET = pytz.timezone('US/Eastern')


class LogArchiver:
    """Archives log files to S3 and deletes local copies."""
    
    def __init__(
        self,
        logs_directory: Optional[str] = None,
        s3_service: Optional[S3Service] = None,
        s3_prefix: str = 'logs'
    ):
        """
        Initialize log archiver.
        
        Args:
            logs_directory: Directory containing log files. If None, uses 'logs' in project root.
            s3_service: S3Service instance. If None, creates one.
            s3_prefix: S3 prefix/folder for logs (default: 'logs')
        """
        if logs_directory is None:
            project_root = Path(__file__).parent.parent.parent
            logs_directory = project_root / 'logs'
        
        self.logs_directory = Path(logs_directory)
        
        if s3_service is None:
            try:
                # Use separate logs bucket if configured, otherwise use default bucket
                logs_bucket = os.getenv('AWS_S3_LOGS_BUCKET_NAME')
                if logs_bucket:
                    s3_service = S3Service(bucket_name=logs_bucket)
                else:
                    s3_service = S3Service()  # Use default bucket
            except Exception as e:
                logger.warning(f"Could not initialize S3 service: {e}")
                s3_service = None
        
        self.s3_service = s3_service
        self.s3_prefix = s3_prefix
        
        logger.info(f"LogArchiver initialized with directory: {self.logs_directory}")
        if self.s3_service:
            logger.info(f"S3 archiving enabled with prefix: {self.s3_prefix}")
    
    def find_log_files(self) -> List[Path]:
        """
        Find all log files in the logs directory and project root.
        
        Returns:
            List of Path objects for log files found
        """
        log_files = []
        
        # Check logs directory if it exists
        if self.logs_directory.exists() and self.logs_directory.is_dir():
            for file_path in self.logs_directory.rglob('*'):
                if file_path.is_file() and (file_path.suffix == '.log' or 'log' in file_path.name.lower()):
                    log_files.append(file_path)
        
        # Also check project root for .log files
        project_root = Path(__file__).parent.parent.parent
        for file_path in project_root.glob('*.log'):
            if file_path.is_file():
                log_files.append(file_path)
        
        # Check for log files with date patterns (e.g., trading_bot_2025-12-03.log)
        for file_path in project_root.glob('*.log.*'):
            if file_path.is_file():
                log_files.append(file_path)
        
        return log_files
    
    def archive_logs(self, date: Optional[datetime] = None) -> dict:
        """
        Archive all log files to S3 and delete local copies.
        
        Args:
            date: Date for archiving (used in S3 path). If None, uses today.
        
        Returns:
            dict with 'uploaded', 'failed', 'deleted' counts
        """
        if not self.s3_service:
            logger.warning("S3 service not available, cannot archive logs")
            return {'uploaded': 0, 'failed': 0, 'deleted': 0}
        
        if date is None:
            date = datetime.now(ET)
        
        date_str = date.strftime('%Y-%m-%d')
        year = date.strftime('%Y')
        month = date.strftime('%m')
        
        log_files = self.find_log_files()
        
        if not log_files:
            logger.info("No log files found to archive")
            return {'uploaded': 0, 'failed': 0, 'deleted': 0}
        
        logger.info(f"Found {len(log_files)} log file(s) to archive")
        
        uploaded = 0
        failed = 0
        deleted = 0
        
        for log_file in log_files:
            try:
                # Create S3 key with date-based path: logs/YYYY/MM/YYYY-MM-DD_filename.log
                filename = log_file.name
                s3_key = f"{self.s3_prefix}/{year}/{month}/{date_str}_{filename}"
                
                logger.info(f"Uploading {log_file} to s3://{self.s3_service.bucket_name}/{s3_key}")
                
                # Upload to S3
                if self.s3_service.upload_file(str(log_file), s3_key):
                    logger.info(f"✅ Successfully uploaded {filename}")
                    uploaded += 1
                    
                    # Delete local file after successful upload
                    try:
                        log_file.unlink()
                        logger.info(f"✅ Deleted local file: {filename}")
                        deleted += 1
                    except Exception as e:
                        logger.warning(f"⚠️  Failed to delete local file {filename}: {e}")
                else:
                    logger.error(f"❌ Failed to upload {filename}")
                    failed += 1
                    
            except Exception as e:
                logger.error(f"❌ Error archiving {log_file}: {e}")
                failed += 1
        
        logger.info(f"Archive complete: {uploaded} uploaded, {failed} failed, {deleted} deleted")
        
        return {
            'uploaded': uploaded,
            'failed': failed,
            'deleted': deleted,
            'total': len(log_files)
        }

