"""S3 storage manager for LaTeX service."""

import io
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import structlog
from minio import Minio

from config import settings

logger = structlog.get_logger()


class S3Manager:
    """Manages S3 storage operations."""

    def __init__(self):
        self.enabled = settings.enable_s3

        if not self.enabled:
            logger.warning("S3 storage disabled")
            return

        # Parse endpoint
        endpoint = settings.s3_endpoint
        secure = settings.s3_secure

        if "://" in endpoint:
            parsed = urlparse(endpoint)
            endpoint = parsed.netloc
            if parsed.scheme == "http":
                secure = False

        if "/" in endpoint:
            endpoint = endpoint.split("/")[0]

        # Initialize MinIO client
        try:
            self.client = Minio(
                endpoint,
                access_key=settings.s3_access_key,
                secret_key=settings.s3_secret_key,
                secure=secure
            )
            self.bucket = settings.s3_bucket

            # Verify bucket exists
            if not self.client.bucket_exists(self.bucket):
                logger.warning(f"Bucket {self.bucket} does not exist")
            else:
                logger.info(f"S3 initialized: {self.bucket}")

        except Exception as e:
            logger.error(f"S3 initialization failed: {e}")
            self.enabled = False

    def upload_file(self, local_path: Path, s3_key: str) -> bool:
        """Upload file to S3."""
        if not self.enabled:
            return False

        try:
            self.client.fput_object(
                bucket_name=self.bucket,
                object_name=s3_key,
                file_path=str(local_path)
            )
            logger.info(f"Uploaded to S3: {s3_key}")
            return True
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return False

    def upload_bytes(self, content: bytes, s3_key: str, content_type: str = "application/octet-stream") -> bool:
        """Upload bytes to S3."""
        if not self.enabled:
            return False

        try:
            data_stream = io.BytesIO(content)
            self.client.put_object(
                bucket_name=self.bucket,
                object_name=s3_key,
                data=data_stream,
                length=len(content),
                content_type=content_type
            )
            logger.info(f"Uploaded bytes to S3: {s3_key}")
            return True
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return False

    def download_file(self, s3_key: str, local_path: Path) -> bool:
        """Download file from S3."""
        if not self.enabled:
            return False

        try:
            self.client.fget_object(
                bucket_name=self.bucket,
                object_name=s3_key,
                file_path=str(local_path)
            )
            logger.info(f"Downloaded from S3: {s3_key}")
            return True
        except Exception as e:
            logger.error(f"S3 download failed: {e}")
            return False

    def get_bytes(self, s3_key: str) -> Optional[bytes]:
        """Get file content as bytes from S3."""
        if not self.enabled:
            return None

        try:
            response = self.client.get_object(
                bucket_name=self.bucket,
                object_name=s3_key
            )
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except Exception as e:
            logger.error(f"S3 download failed: {e}")
            return None

    def list_versions(self, job_id: str) -> list:
        """List backup versions for a job."""
        if not self.enabled:
            return []

        try:
            objects = self.client.list_objects(
                bucket_name=self.bucket,
                prefix=f"{job_id}/backups/",
                recursive=True
            )

            versions = []
            for obj in objects:
                versions.append({
                    "filename": obj.object_name.split("/")[-1],
                    "s3_key": obj.object_name,
                    "size": obj.size,
                    "modified": obj.last_modified.isoformat()
                })

            return sorted(versions, key=lambda x: x["modified"], reverse=True)

        except Exception as e:
            logger.error(f"Failed to list versions: {e}")
            return []


s3_manager = S3Manager()
