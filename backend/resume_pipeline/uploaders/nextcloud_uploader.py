# resume_pipeline/uploaders/nextcloud_uploader.py
from pathlib import Path
from webdav4.client import Client

class NextcloudUploader:
    def __init__(self, endpoint: str, username: str, password: str):
        # Change 'host' to 'base_url'
        self.client = Client(base_url=endpoint, auth=(username, password))
        self.enabled = self.client.exists("/") # Simple health check

    def upload_file(self, file_path: Path, remote_parent: str, remote_dir: str) -> bool:
        if not self.enabled: return False
        try:
            if not self.client.exists(remote_parent):
                self.client.mkdir(remote_parent)
            if not self.client.exists(remote_dir):
                self.client.mkdir(remote_dir)

            dest_path = f"{remote_dir}/{file_path.name}"
            with open(file_path, 'rb') as f:
                self.client.upload_fileobj(f, dest_path, overwrite=True)
            print(f"  ✓ Uploaded to Nextcloud: {dest_path}")
            return True
        except Exception as e:
            print(f"  ✗ Nextcloud upload error: {e}")
            return False
