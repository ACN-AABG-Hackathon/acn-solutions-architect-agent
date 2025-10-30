"""
S3 Utilities - Helper functions for S3 operations
"""

import os
from typing import Optional
import boto3
from botocore.exceptions import ClientError
import structlog

logger = structlog.get_logger(__name__)


class S3Manager:
    """
    Manage S3 operations for document storage
    """
    
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        aws_region: str = "us-east-1"
    ):
        """
        Initialize S3 manager
        
        Args:
            bucket_name: S3 bucket name
            aws_region: AWS region
        """
        self.bucket_name = bucket_name or os.getenv("S3_BUCKET_NAME")
        self.aws_region = aws_region
        
        if not self.bucket_name:
            raise ValueError("S3 bucket name must be provided or set in S3_BUCKET_NAME env var")
        
        # Initialize S3 client
        self.s3_client = boto3.client('s3', region_name=self.aws_region)
        
        logger.info("s3_manager_initialized", bucket=self.bucket_name, region=self.aws_region)
    
    def upload_file(
        self,
        file_path: str,
        s3_key: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload file to S3
        
        Args:
            file_path: Local file path
            s3_key: S3 key (if None, uses filename with timestamp)
            metadata: Optional metadata dict
            
        Returns:
            S3 key
        """
        if not s3_key:
            from datetime import datetime
            filename = os.path.basename(file_path)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            s3_key = f"documents/{timestamp}_{filename}"
        
        logger.info("uploading_file", file=file_path, bucket=self.bucket_name, key=s3_key)
        
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.s3_client.upload_file(
                Filename=file_path,
                Bucket=self.bucket_name,
                Key=s3_key,
                ExtraArgs=extra_args if extra_args else None
            )
            
            logger.info("file_uploaded", key=s3_key)
            return s3_key
            
        except ClientError as e:
            logger.error("upload_failed", error=str(e), bucket=self.bucket_name, key=s3_key)
            raise
    
    def upload_fileobj(
        self,
        fileobj,
        s3_key: str,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload file object to S3
        
        Args:
            fileobj: File-like object
            s3_key: S3 key
            metadata: Optional metadata dict
            
        Returns:
            S3 key
        """
        logger.info("uploading_fileobj", bucket=self.bucket_name, key=s3_key)
        
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.s3_client.upload_fileobj(
                Fileobj=fileobj,
                Bucket=self.bucket_name,
                Key=s3_key,
                ExtraArgs=extra_args if extra_args else None
            )
            
            logger.info("fileobj_uploaded", key=s3_key)
            return s3_key
            
        except ClientError as e:
            logger.error("upload_failed", error=str(e), bucket=self.bucket_name, key=s3_key)
            raise
    
    def download_file(self, s3_key: str, local_path: str) -> str:
        """
        Download file from S3
        
        Args:
            s3_key: S3 key
            local_path: Local file path to save
            
        Returns:
            Local file path
        """
        logger.info("downloading_file", bucket=self.bucket_name, key=s3_key, local=local_path)
        
        try:
            self.s3_client.download_file(
                Bucket=self.bucket_name,
                Key=s3_key,
                Filename=local_path
            )
            
            logger.info("file_downloaded", local=local_path)
            return local_path
            
        except ClientError as e:
            logger.error("download_failed", error=str(e), bucket=self.bucket_name, key=s3_key)
            raise
    
    def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600,
        operation: str = 'get_object'
    ) -> str:
        """
        Generate presigned URL for S3 object
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration in seconds (default 1 hour)
            operation: S3 operation (get_object or put_object)
            
        Returns:
            Presigned URL
        """
        logger.info("generating_presigned_url", bucket=self.bucket_name, key=s3_key, expiration=expiration)
        
        try:
            url = self.s3_client.generate_presigned_url(
                operation,
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            
            logger.info("presigned_url_generated", key=s3_key)
            return url
            
        except ClientError as e:
            logger.error("presigned_url_failed", error=str(e), bucket=self.bucket_name, key=s3_key)
            raise
    
    def get_object_url(self, s3_key: str) -> str:
        """
        Get public S3 object URL (not presigned)
        
        Args:
            s3_key: S3 object key
            
        Returns:
            S3 URL
        """
        return f"https://{self.bucket_name}.s3.{self.aws_region}.amazonaws.com/{s3_key}"
    
    def delete_object(self, s3_key: str):
        """
        Delete object from S3
        
        Args:
            s3_key: S3 object key
        """
        logger.info("deleting_object", bucket=self.bucket_name, key=s3_key)
        
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            logger.info("object_deleted", key=s3_key)
            
        except ClientError as e:
            logger.error("delete_failed", error=str(e), bucket=self.bucket_name, key=s3_key)
            raise
    
    def list_objects(self, prefix: str = "") -> list:
        """
        List objects in S3 bucket
        
        Args:
            prefix: S3 key prefix filter
            
        Returns:
            List of object keys
        """
        logger.info("listing_objects", bucket=self.bucket_name, prefix=prefix)
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            objects = []
            if 'Contents' in response:
                objects = [obj['Key'] for obj in response['Contents']]
            
            logger.info("objects_listed", count=len(objects))
            return objects
            
        except ClientError as e:
            logger.error("list_failed", error=str(e), bucket=self.bucket_name, prefix=prefix)
            raise
    
    def object_exists(self, s3_key: str) -> bool:
        """
        Check if object exists in S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            True if exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except ClientError:
            return False
    
    def get_object_metadata(self, s3_key: str) -> dict:
        """
        Get object metadata
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Metadata dict
        """
        logger.info("getting_metadata", bucket=self.bucket_name, key=s3_key)
        
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            metadata = {
                'size': response['ContentLength'],
                'last_modified': response['LastModified'],
                'content_type': response.get('ContentType'),
                'metadata': response.get('Metadata', {})
            }
            
            return metadata
            
        except ClientError as e:
            logger.error("metadata_failed", error=str(e), bucket=self.bucket_name, key=s3_key)
            raise


# Example usage
if __name__ == "__main__":
    s3_manager = S3Manager(bucket_name="my-documents-bucket")
    
    # Upload file
    s3_key = s3_manager.upload_file("sample.pdf")
    print(f"Uploaded to: {s3_key}")
    
    # Generate presigned URL
    url = s3_manager.generate_presigned_url(s3_key)
    print(f"Presigned URL: {url}")
    
    # Check if exists
    exists = s3_manager.object_exists(s3_key)
    print(f"Exists: {exists}")
    
    # Get metadata
    metadata = s3_manager.get_object_metadata(s3_key)
    print(f"Metadata: {metadata}")

