"""
DEPRECATED: This module is kept only for backward compatibility.
All new code should import from `services.storage` instead.

Example:
    from services.storage import storage
"""
# Re-export everything from the new canonical module
from services.storage import S3Storage as GCSStorage, storage as gcs_storage, storage

__all__ = ["GCSStorage", "gcs_storage", "storage"]
