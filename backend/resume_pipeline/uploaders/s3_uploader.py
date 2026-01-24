import io
import json
from pathlib import Path

from minio import Minio


class S3Uploader:
    """
    Generic S3 Uploader compatible with AWS S3, Backblaze B2, and MinIO.
    """

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = True,
    ):
        # We use the Minio client library as it is a robust S3-compatible client
        self.client = Minio(
            endpoint, access_key=access_key, secret_key=secret_key, secure=secure
        )
        self.bucket = bucket
        self.enabled = True

        # Verify connection and bucket availability
        try:
            if not self.client.bucket_exists(self.bucket):
                try:
                    self.client.make_bucket(self.bucket)
                    print(f"  ✓ Created S3 bucket: {self.bucket}")
                except Exception as e:
                    # Note: Backblaze B2 Application Keys with restricted permissions
                    # (e.g. read/write only) might fail this check even if the bucket exists.
                    # We warn but do not disable, assuming the bucket is pre-provisioned.
                    print(
                        f"  ! Warning: Could not verify/create S3 bucket '{self.bucket}': {e}"
                    )
        except Exception as e:
            print(f"  ✗ S3 connection failed: {e}")
            self.enabled = False

    def upload_file(self, file_path: Path, remote_path: str) -> bool:
        if not self.enabled:
            return False

        try:
            self.client.fput_object(
                bucket_name=self.bucket,
                object_name=remote_path,
                file_path=str(file_path),
            )
            print(f"  ✓ Uploaded to S3: {remote_path}")
            return True
        except Exception as e:
            print(f"  ✗ S3 upload error: {e}")
            return False

    def upload_json(self, path: Path, raw_json: dict) -> bool:
        # 1. Convert the Python dictionary to a JSON formatted string and encode to bytes
        json_bytes = json.dumps(raw_json, indent=2).encode("utf-8")
        data_stream = io.BytesIO(json_bytes)
        data_length = len(json_bytes)

        if not self.enabled:
            return False

        # 2. Upload the JSON data stream to the bucket
        try:
            self.client.put_object(
                bucket_name=self.bucket,
                object_name=str(path),
                data=data_stream,
                length=data_length,
                content_type="application/json",  # Specify the content type
            )
            print(f"  ✓ Uploaded checkpoint to S3: {path}")
            return True
        except Exception as e:
            print(f"  ✗ S3 checkpoint upload error: {e}")
            return False
