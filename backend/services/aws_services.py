"""
AWS Services - S3 and SQS integration.
"""

import os
import json
import asyncio
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional

class AWSServices:
    """AWS Services wrapper for S3 and SQS."""
    
    def __init__(self):
        self.region_name = os.getenv("AWS_REGION", "us-east-1")
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        
        # S3 Configuration
        self.bucket_name = os.getenv("S3_BUCKET_NAME", "infinitest-videos")
        
        # SQS Configuration
        self.queue_url = os.getenv("SQS_QUEUE_URL")
        
        # Initialize clients
        self.s3_client = boto3.client(
            "s3",
            region_name=self.region_name,
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key
        )
        
        self.sqs_client = boto3.client(
            "sqs",
            region_name=self.region_name,
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key
        )

    async def upload_file(self, file_path: str, object_name: str = None) -> Optional[str]:
        """
        Upload a file to an S3 bucket.
        
        Args:
            file_path: File to upload
            object_name: S3 object name. If not specified then file_name is used
            
        Returns:
             Public URL if successful, else None
        """
        if object_name is None:
            object_name = os.path.basename(file_path)

        try:
            await asyncio.to_thread(
                self.s3_client.upload_file,
                file_path,
                self.bucket_name,
                object_name,
                ExtraArgs={'ContentType': 'video/mp4'}
            )
            return f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{object_name}"
        except ClientError as e:
            print(f"S3 Upload Error: {e}")
            return None

    async def send_job_to_queue(self, job_data: Dict[str, Any]) -> bool:
        """
        Send a job to the SQS queue.
        
        Args:
            job_data: Dictionary containing job details
            
        Returns:
            True if successful, else False
        """
        if not self.queue_url:
            print("SQS_QUEUE_URL not set")
            return False
            
        try:
            await asyncio.to_thread(
                self.sqs_client.send_message,
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(job_data)
            )
            return True
        except ClientError as e:
            print(f"SQS Send Error: {e}")
            return False

# Singleton instance
_aws_services: Optional[AWSServices] = None

def get_aws_services() -> AWSServices:
    """Get the global AWS services instance."""
    global _aws_services
    if _aws_services is None:
        _aws_services = AWSServices()
    return _aws_services
