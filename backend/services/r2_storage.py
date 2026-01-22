"""
Cloudflare R2 Storage Service
Handles uploading and managing PDFs in Cloudflare R2.
"""

import os
import boto3
from botocore.config import Config
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class R2StorageService:
    """Service for interacting with Cloudflare R2 storage."""
    
    def __init__(self):
        self.account_id = os.getenv("R2_ACCOUNT_ID")
        self.access_key_id = os.getenv("R2_ACCESS_KEY_ID")
        self.secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY")
        self.bucket_name = os.getenv("R2_BUCKET_NAME", "infinitest-pdfs")
        self.public_url = os.getenv("R2_PUBLIC_URL", "")  # e.g., https://pub-xxx.r2.dev
        
        self.client = None
        if self.account_id and self.access_key_id and self.secret_access_key:
            self._init_client()
    
    def _init_client(self):
        """Initialize the S3-compatible client for R2."""
        import urllib3
        import ssl
        import os
        from botocore.config import Config as BotoConfig
        
        # Suppress SSL warnings
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Set environment variable to disable SSL verification
        os.environ['CURL_CA_BUNDLE'] = ''
        os.environ['REQUESTS_CA_BUNDLE'] = ''
        
        # Create client with SSL verification disabled
        self.client = boto3.client(
            "s3",
            endpoint_url=f"https://{self.account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                connect_timeout=30,
                read_timeout=60,
                retries={"max_attempts": 3}
            ),
            region_name="auto",
            verify=False
        )
    
    def is_configured(self) -> bool:
        """Check if R2 is properly configured."""
        return self.client is not None
    
    def upload_pdf(self, file_path: str, object_key: str) -> Optional[str]:
        """
        Upload a PDF file to R2.
        
        Args:
            file_path: Local path to the PDF file
            object_key: The key (path) to store the file as in R2
            
        Returns:
            Public URL of the uploaded file, or None if failed
        """
        if not self.is_configured():
            print("R2 not configured, skipping upload")
            return None
        
        try:
            with open(file_path, "rb") as file:
                self.client.put_object(
                    Bucket=self.bucket_name,
                    Key=object_key,
                    Body=file,
                    ContentType="application/pdf"
                )
            
            # Return public URL
            if self.public_url:
                return f"{self.public_url}/{object_key}"
            else:
                # Fallback to S3-style URL (requires public bucket)
                return f"https://{self.bucket_name}.{self.account_id}.r2.cloudflarestorage.com/{object_key}"
                
        except Exception as e:
            print(f"Error uploading to R2: {e}")
            return None
    
    def delete_pdf(self, object_key: str) -> bool:
        """
        Delete a PDF from R2.
        
        Args:
            object_key: The key (path) of the file in R2
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.is_configured():
            return False
        
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return True
        except Exception as e:
            print(f"Error deleting from R2: {e}")
            return False
    
    def get_object_key(self, user_id: str, filename: str) -> str:
        """Generate a unique object key for a PDF."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        return f"pdfs/{user_id}/{unique_id}_{filename}"


# Singleton instance
r2_storage = R2StorageService()
