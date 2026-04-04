import os
import boto3
from botocore.exceptions import ClientError
from typing import Optional
import datetime
import uuid


class GCSStorage:
    """
    Drop-in replacement for the old GCSStorage class, now backed by AWS S3.
    All method signatures are kept identical so nothing else in the codebase needs changes.
    """

    def __init__(self):
        self.bucket_name = os.getenv("S3_BUCKET_NAME", os.getenv("AWS_S3_BUCKET_NAME", "infinitest-pdfs"))
        self.region = os.getenv("AWS_REGION", "ap-south-1")
        self.client = None

        try:
            self.client = boto3.client(
                "s3",
                region_name=self.region,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            )
            # Quick sanity check
            self.client.head_bucket(Bucket=self.bucket_name)
            print(f"✓ S3 Client initialized — bucket: {self.bucket_name} ({self.region})")
        except Exception as e:
            print(f"⚠ S3 Client initialization failed (might be local): {e}")
            self.client = None

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def is_configured(self) -> bool:
        """Check if S3 is properly configured."""
        return self.client is not None

    def get_object_key(self, user_id: str, filename: str) -> str:
        """Generate a unique object key for the file."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        return f"pdfs/{user_id}/{timestamp}_{unique_id}_{filename}"

    # ------------------------------------------------------------------ #
    # Public API — same signatures as old GCSStorage                      #
    # ------------------------------------------------------------------ #

    def upload_generic_file(self, file_obj, filename: str, content_type: str, folder: str = "uploads") -> Optional[str]:
        """Upload any file object to S3."""
        if not self.client:
            print("✗ S3 client not initialized")
            return None

        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = uuid.uuid4().hex[:8]
            object_key = f"{folder}/{timestamp}_{unique_id}_{filename}"

            file_obj.seek(0)
            self.client.upload_fileobj(
                file_obj,
                self.bucket_name,
                object_key,
                ExtraArgs={"ContentType": content_type},
            )
            url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{object_key}"
            print(f"✓ Uploaded generic file to S3: {url}")
            return url
        except ClientError as e:
            print(f"✗ S3 upload_generic_file failed: {e}")
            return None

    def upload_pdf(self, file_path: str, user_id: str, filename: str) -> Optional[str]:
        """Upload a PDF file from a local path to S3."""
        if not self.client:
            return None

        object_key = self.get_object_key(user_id, filename)
        try:
            self.client.upload_file(
                file_path,
                self.bucket_name,
                object_key,
                ExtraArgs={"ContentType": "application/pdf"},
            )
            url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{object_key}"
            print(f"✓ Uploaded PDF to S3: {url}")
            return url
        except ClientError as e:
            print(f"✗ S3 upload_pdf failed: {e}")
            return None

    def get_signed_url(self, object_key: str, expiration: int = 3600) -> Optional[str]:
        """Generate a pre-signed URL for temporary access."""
        if not self.client:
            return None
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": object_key},
                ExpiresIn=expiration,
            )
            return url
        except ClientError as e:
            print(f"✗ S3 generate_presigned_url failed: {e}")
            return None

    def get_public_url(self, object_key: str) -> str:
        """Return the public URL for an object."""
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{object_key}"

    def delete_file(self, object_key: str) -> bool:
        """Delete a file from S3."""
        if not self.client:
            return False
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=object_key)
            print(f"✓ Deleted S3 object: {object_key}")
            return True
        except ClientError as e:
            print(f"✗ S3 delete_file failed: {e}")
            return False

    def list_user_files(self, user_id: str) -> list:
        """List all files for a given user."""
        if not self.client:
            return []
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=f"pdfs/{user_id}/",
            )
            return response.get("Contents", [])
        except ClientError as e:
            print(f"✗ S3 list_user_files failed: {e}")
            return []

# Module-level singleton — preserves backward compat with
# `from services.gcs_storage import gcs_storage` used in all routers
gcs_storage = GCSStorage()
