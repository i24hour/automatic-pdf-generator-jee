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
        
        # Try boto3 first
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
                return f"https://{self.bucket_name}.{self.account_id}.r2.cloudflarestorage.com/{object_key}"
                
        except Exception as e:
            print(f"Boto3 upload failed: {e}")
            print("Trying fallback upload with requests...")
            
            # Fallback: Use requests with AWS4 signing
            try:
                return self._upload_with_requests(file_path, object_key)
            except Exception as e2:
                print(f"Fallback upload also failed: {e2}")
                return None
    
    def _upload_with_requests(self, file_path: str, object_key: str) -> Optional[str]:
        """Fallback upload using requests library with manual AWS4 signing."""
        import requests
        import hashlib
        import hmac
        from datetime import datetime
        
        # Disable SSL warnings
        import urllib3
        urllib3.disable_warnings()
        
        endpoint = f"https://{self.account_id}.r2.cloudflarestorage.com"
        url = f"{endpoint}/{self.bucket_name}/{object_key}"
        
        # Read file
        with open(file_path, "rb") as f:
            file_content = f.read()
        
        # AWS4 signing
        method = "PUT"
        service = "s3"
        region = "auto"
        
        t = datetime.utcnow()
        amz_date = t.strftime('%Y%m%dT%H%M%SZ')
        date_stamp = t.strftime('%Y%m%d')
        
        content_hash = hashlib.sha256(file_content).hexdigest()
        
        # Create canonical request
        canonical_uri = f"/{self.bucket_name}/{object_key}"
        canonical_querystring = ""
        canonical_headers = f"host:{self.account_id}.r2.cloudflarestorage.com\nx-amz-content-sha256:{content_hash}\nx-amz-date:{amz_date}\n"
        signed_headers = "host;x-amz-content-sha256;x-amz-date"
        
        canonical_request = f"{method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{content_hash}"
        
        # Create string to sign
        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
        string_to_sign = f"{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        
        # Create signing key
        def sign(key, msg):
            return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
        
        k_date = sign(('AWS4' + self.secret_access_key).encode('utf-8'), date_stamp)
        k_region = sign(k_date, region)
        k_service = sign(k_region, service)
        k_signing = sign(k_service, 'aws4_request')
        
        signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        authorization_header = f"{algorithm} Credential={self.access_key_id}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
        
        headers = {
            'Host': f"{self.account_id}.r2.cloudflarestorage.com",
            'x-amz-date': amz_date,
            'x-amz-content-sha256': content_hash,
            'Authorization': authorization_header,
            'Content-Type': 'application/pdf'
        }
        
        # Make request with SSL verification disabled
        response = requests.put(url, data=file_content, headers=headers, verify=False, timeout=60)
        
        if response.status_code in [200, 201]:
            print(f"✓ Fallback upload successful: {response.status_code}")
            if self.public_url:
                return f"{self.public_url}/{object_key}"
            return url
        else:
            print(f"✗ Fallback upload failed: {response.status_code} - {response.text}")
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
