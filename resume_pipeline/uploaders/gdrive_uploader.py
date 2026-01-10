"""
Google Drive upload utilities.
"""

import os
from pathlib import Path
from typing import Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


class GoogleDriveUploader:
    """Uploads files to Google Drive."""

    # Scopes required for file upload
    SCOPES = ['https://www.googleapis.com/auth/drive.file']

    def __init__(
        self,
        credentials_file: Optional[str] = None,
        token_file: Optional[str] = None
    ):
        """
        Initialize Google Drive uploader.

        Args:
            credentials_file: Path to OAuth2 credentials JSON
            token_file: Path to save/load token
        """
        self.credentials_file = credentials_file or "credentials.json"
        self.token_file = token_file or "token.json"
        self.service = None
        self.enabled = False

        # Try to authenticate
        try:
            self._authenticate()
            self.enabled = True
            print("  ✓ Google Drive authentication successful")
        except Exception as e:
            print(f"  ⚠ Google Drive authentication failed: {e}")
            print("    Upload to Google Drive disabled")

    def _authenticate(self):
        """Authenticate with Google Drive API."""
        creds = None

        # Check for existing token
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(
                self.token_file, self.SCOPES
            )

        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_file}"
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())

        # Build service
        self.service = build('drive', 'v3', credentials=creds)

    def upload_file(
        self,
        file_path: Path,
        folder_id: Optional[str] = None,
        mime_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload file to Google Drive.

        Args:
            file_path: Path to file to upload
            folder_id: Google Drive folder ID (None for root)
            mime_type: MIME type (auto-detected if None)

        Returns:
            File ID if successful, None otherwise
        """
        if not self.enabled:
            return None

        if not file_path.exists():
            print(f"  ✗ File not found: {file_path}")
            return None

        try:
            # Auto-detect MIME type
            if mime_type is None:
                mime_type = self._get_mime_type(file_path)

            # Prepare file metadata
            file_metadata = {
                'name': file_path.name
            }

            if folder_id:
                file_metadata['parents'] = [folder_id]

            # Upload file
            media = MediaFileUpload(
                str(file_path),
                mimetype=mime_type,
                resumable=True
            )

            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()

            file_id = file.get('id')
            web_link = file.get('webViewLink')

            print(f"  ✓ Uploaded to Google Drive: {file_path.name}")
            print(f"    File ID: {file_id}")
            if web_link:
                print(f"    Link: {web_link}")

            return file_id

        except HttpError as error:
            print(f"  ✗ Google Drive upload failed: {error}")
            return None
        except Exception as e:
            print(f"  ✗ Upload error: {e}")
            return None

    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type based on file extension."""
        mime_types = {
            '.pdf': 'application/pdf',
            '.tex': 'text/x-tex',
            '.txt': 'text/plain',
            '.json': 'application/json',
            '.md': 'text/markdown',
        }

        ext = file_path.suffix.lower()
        return mime_types.get(ext, 'application/octet-stream')

    def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Create a folder in Google Drive.

        Args:
            folder_name: Name of the folder
            parent_id: Parent folder ID (None for root)

        Returns:
            Folder ID if successful, None otherwise
        """
        if not self.enabled:
            return None

        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }

            if parent_id:
                file_metadata['parents'] = [parent_id]

            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()

            folder_id = folder.get('id')
            print(f"  ✓ Created folder: {folder_name} (ID: {folder_id})")
            return folder_id

        except HttpError as error:
            print(f"  ✗ Folder creation failed: {error}")
            return None

    def find_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Find folder by name.

        Args:
            folder_name: Name of the folder to find
            parent_id: Parent folder ID to search in

        Returns:
            Folder ID if found, None otherwise
        """
        if not self.enabled:
            return None

        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"

            if parent_id:
                query += f" and '{parent_id}' in parents"

            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()

            files = results.get('files', [])

            if files:
                return files[0]['id']
            return None

        except HttpError as error:
            print(f"  ✗ Folder search failed: {error}")
            return None

    def get_or_create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Get existing folder or create new one.

        Args:
            folder_name: Name of the folder
            parent_id: Parent folder ID

        Returns:
            Folder ID
        """
        folder_id = self.find_folder(folder_name, parent_id)
        if folder_id:
            return folder_id
        return self.create_folder(folder_name, parent_id)
