# resume_pipeline/uploaders/minio_uploader.py
from pathlib import Path
from typing import Optional
from minio import Minio

class MinioUploader:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str, secure: bool = True):
        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        self.bucket = bucket
        self.enabled = True
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except Exception as e:
            print(f"  ✗ MinIO connection failed: {e}")
            self.enabled = False

    def upload_file(self, file_path: Path, remote_path: str) -> bool:
        if not self.enabled: return False
        try:
            self.client.fput_object(self.bucket, remote_path, str(file_path))
            print(f"  ✓ Uploaded to MinIO: {remote_path}")
            return True
        except Exception as e:
            print(f"  ✗ MinIO upload error: {e}")
            return False
