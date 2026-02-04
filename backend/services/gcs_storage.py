import os
from google.cloud import storage
from typing import Optional
import datetime
import uuid

class GCSStorage:
    def __init__(self):
        self.bucket_name = os.getenv("GCS_BUCKET_NAME", "infinitest-pdfs")
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.client = None
        self.bucket = None
        
        # Initialize client if running in Cloud Run (auto-auth) or if credentials present
        try:
            self.client = storage.Client()
            print(f"✓ GCS Client initialized for project: {self.client.project}")
        except Exception as e:
            print(f"⚠ GCS Client initialization failed (might be local): {e}")

    def is_configured(self) -> bool:
        """Check if GCS is properly configured."""
        return self.client is not None

    def get_object_key(self, user_id: str, filename: str) -> str:
        """Generate a unique object key for the file."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        # Structure: pdfs/user_id/timestamp_uuid_filename
        return f"pdfs/{user_id}/{timestamp}_{unique_id}_{filename}"

    def upload_generic_file(self, file_obj, filename: str, content_type: str, folder: str = "uploads") -> Optional[str]:
        """Upload any file object to GCS."""
        if not self.client:
            print("✗ GCS client not initialized")
            return None

        try:
            # Generate key
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = uuid.uuid4().hex[:8]
            object_key = f"{folder}/{timestamp}_{unique_id}_{filename}"

            bucket = self.client.bucket(self.bucket_name)
            blob = bucket.blob(object_key)
            
            # Upload file object
            print(f"Uploading generic file to GCS: gs://{self.bucket_name}/{object_key}")
            file_obj.seek(0) # Ensure start of file
            blob.upload_from_file(file_obj, content_type=content_type)
            
            public_url = f"https://storage.googleapis.com/{self.bucket_name}/{object_key}"
            return public_url
            
        except Exception as e:
            print(f"✗ GCS upload failed: {e}")
            raise e

    def upload_pdf(self, file_path: str, object_key: str) -> Optional[str]:
        """Upload a PDF file to GCS and return the public URL."""
        if not self.client:
            print("✗ GCS client not initialized")
            return None

        try:
            bucket = self.client.bucket(self.bucket_name)
            blob = bucket.blob(object_key)
            
            # Upload file
            print(f"Uploading to GCS: gs://{self.bucket_name}/{object_key}")
            blob.upload_from_filename(file_path, content_type='application/pdf')
            
            # Return public URL
            public_url = f"https://storage.googleapis.com/{self.bucket_name}/{object_key}"
            
            print(f"✓ GCS upload successful: {public_url}")
            return public_url
            
        except Exception as e:
            print(f"✗ GCS upload failed: {e}")
            return None

    def delete_pdf(self, object_key: str) -> bool:
        """Delete a PDF file from GCS."""
        if not self.client:
            return False
            
        try:
            bucket = self.client.bucket(self.bucket_name)
            blob = bucket.blob(object_key)
            blob.delete()
            print(f"✓ GCS file deleted: {object_key}")
            return True
        except Exception as e:
            print(f"✗ GCS delete failed: {e}")
            return False

# Singleton instance
gcs_storage = GCSStorage()
