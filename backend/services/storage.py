"""
AWS S3 Storage Service
Handles all file uploads, downloads, and management for the application.
"""
import os
from urllib.parse import urlparse
import boto3
from botocore.exceptions import ClientError
from typing import Optional
import datetime
import uuid


class S3Storage:
    """
    AWS S3-backed storage service.
    Handles PDF generation outputs and any generic file uploads.
    """

    def __init__(self):
        self.bucket_name = os.getenv("S3_BUCKET_NAME", "infinitest-pdfs")
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
            print(f"[SUCCESS] S3 Storage initialized — bucket: {self.bucket_name} ({self.region})")
        except Exception as e:
            print(f"[WARNING] S3 Storage initialization failed (might be local): {e}")
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

    def _upload_file_path(self, file_path: str, object_key: str, content_type: str) -> Optional[str]:
        """Upload a local file path to S3 using a precomputed object key."""
        if not self.client:
            return None

        try:
            self.client.upload_file(
                file_path,
                self.bucket_name,
                object_key,
                ExtraArgs={"ContentType": content_type},
            )
            url = self.get_public_url(object_key)
            print(f"[SUCCESS] Uploaded file to S3: {url}")
            return url
        except ClientError as e:
            print(f"[ERROR] S3 file upload failed: {e}")
            return None

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def upload_generic_file(self, file_obj, filename: str, content_type: str, folder: str = "uploads") -> Optional[str]:
        """Upload any file object to S3."""
        if not self.client:
            print("[ERROR] S3 client not initialized")
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
            print(f"[SUCCESS] Uploaded file to S3: {url}")
            return url
        except ClientError as e:
            print(f"[ERROR] S3 upload_generic_file failed: {e}")
            return None

    def upload_pdf(self, file_path: str, user_id_or_object_key: str, filename: Optional[str] = None) -> Optional[str]:
        """
        Upload a PDF file from a local path to S3.

        Supports both call styles:
        - upload_pdf(file_path, user_id, filename)
        - upload_pdf(file_path, object_key)
        """
        object_key = (
            self.get_object_key(str(user_id_or_object_key), filename)
            if filename is not None
            else str(user_id_or_object_key)
        )
        return self._upload_file_path(file_path, object_key, "application/pdf")

    def upload_video(self, file_path: str, object_key: str) -> Optional[str]:
        """Upload a rendered MP4 video using a precomputed object key."""
        return self._upload_file_path(file_path, object_key, "video/mp4")

    def get_signed_url(
        self,
        object_key: str,
        expiration: int = 3600,
        expiration_minutes: Optional[int] = None,
    ) -> Optional[str]:
        """Generate a pre-signed URL for temporary access."""
        if not self.client:
            return None

        expires_in = expiration_minutes * 60 if expiration_minutes is not None else expiration
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": object_key},
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            print(f"[ERROR] S3 generate_presigned_url failed: {e}")
            return None

    def get_public_url(self, object_key: str) -> str:
        """Return the public URL for an object."""
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{object_key}"

    def extract_object_key(self, file_url: Optional[str]) -> Optional[str]:
        """Extract the S3 object key from a managed S3 URL."""
        if not file_url or file_url == "pending":
            return None

        parsed = urlparse(file_url)
        if parsed.scheme == "s3" and parsed.path:
            return parsed.path.lstrip("/")

        if not parsed.netloc or ".amazonaws.com" not in parsed.netloc:
            return None

        bucket_prefix = f"{self.bucket_name}.s3."
        if parsed.netloc.startswith(bucket_prefix):
            return parsed.path.lstrip("/") or None

        host_parts = parsed.netloc.split(".")
        if len(host_parts) >= 4 and host_parts[0] == "s3" and parsed.path:
            path_parts = parsed.path.lstrip("/").split("/", 1)
            if len(path_parts) == 2 and path_parts[0] == self.bucket_name:
                return path_parts[1]

        return None

    def is_managed_url(self, file_url: Optional[str]) -> bool:
        """Check whether a URL belongs to the configured S3 bucket."""
        return self.extract_object_key(file_url) is not None

    @staticmethod
    def is_legacy_url(file_url: Optional[str]) -> bool:
        """Identify old URLs that should no longer be served."""
        return bool(
            file_url
            and (
                file_url == "pending"
                or file_url.startswith("gs://")
                or "storage.googleapis.com/" in file_url
            )
        )

    def delete_file(self, object_key: str) -> bool:
        """Delete a file from S3."""
        if not self.client:
            return False
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=object_key)
            print(f"[SUCCESS] Deleted S3 object: {object_key}")
            return True
        except ClientError as e:
            print(f"[ERROR] S3 delete_file failed: {e}")
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
            print(f"[ERROR] S3 list_user_files failed: {e}")
            return []


# Module-level singleton
storage = S3Storage()

# Backward-compat aliases so existing imports keep working without changes
gcs_storage = storage
GCSStorage = S3Storage
