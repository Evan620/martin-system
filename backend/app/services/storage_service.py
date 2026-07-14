"""
Cloud Storage Service for persistent file uploads.

Uses Google Drive API to store files persistently across container restarts.
This solves the ephemeral filesystem issue with Railway/containerized deployments.
"""

import os
import io
import uuid
import threading
from typing import Optional, Tuple, BinaryIO
from datetime import datetime

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from loguru import logger

from app.core.config import settings


# Scope for Drive file management. Use ONLY full `drive`: prod authenticates via a
# service account with domain-wide delegation, and `drive` is the exact scope
# authorized for that delegation. Requesting any additional scope not in the
# delegated set (e.g. drive.readonly) makes Google reject the whole token request
# with `unauthorized_client`. Full `drive` already covers read + write.
DRIVE_SCOPES = [
    'https://www.googleapis.com/auth/drive',
]


class StorageService:
    """
    Service for persistent cloud storage using Google Drive.

    Replaces local file storage to survive container restarts on Railway.
    """

    # Default folder name for TWG documents
    DEFAULT_FOLDER_NAME = "Martin System Documents"

    def __init__(self):
        self.service = None
        self._lock = threading.Lock()
        self._initialized = False
        self._folder_cache = {}  # Cache folder IDs by name

        # Default folder for TWG documents (can be overridden via env)
        self.documents_folder_id = os.environ.get(
            'TWG_DOCUMENTS_FOLDER_ID',
            os.environ.get('SHARED_DOCUMENTS_FOLDER_ID', None)
        )

    def _ensure_initialized(self) -> bool:
        """Initialize Google Drive service if not already done."""
        if self._initialized and self.service:
            return True

        with self._lock:
            if self._initialized and self.service:
                return True

            try:
                self.service = self._get_drive_service()
                self._initialized = True
                logger.info("StorageService initialized with Google Drive")
                return True
            except Exception as e:
                logger.error(f"Failed to initialize StorageService: {e}")
                return False

    def _get_drive_service(self):
        """Get authenticated Google Drive service."""
        # Method 0: Service account + domain-wide delegation (how prod authenticates
        # Google APIs — mirrors calendar_service.py). GOOGLE_SERVICE_ACCOUNT_JSON holds
        # the SA key; GOOGLE_IMPERSONATE_EMAIL names the Workspace user to act as (e.g.
        # joseph.nganga@africacen.org), so uploads land in that user's Drive — which owns
        # the target folder and has storage quota. A bare service account has neither,
        # which is why upload previously failed with "No valid Google Drive credentials".
        import json
        sa_raw = (os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON') or '').strip()
        if sa_raw:
            try:
                if sa_raw.startswith('{'):
                    sa_creds = service_account.Credentials.from_service_account_info(
                        json.loads(sa_raw), scopes=DRIVE_SCOPES
                    )
                else:
                    sa_creds = service_account.Credentials.from_service_account_file(
                        sa_raw, scopes=DRIVE_SCOPES
                    )
                impersonate_email = (
                    getattr(settings, 'GOOGLE_IMPERSONATE_EMAIL', None)
                    or os.environ.get('GOOGLE_IMPERSONATE_EMAIL')
                )
                if impersonate_email and hasattr(sa_creds, 'with_subject'):
                    sa_creds = sa_creds.with_subject(impersonate_email)
                logger.info(
                    "StorageService using service account"
                    + (f" impersonating {impersonate_email}" if impersonate_email else "")
                )
                return build('drive', 'v3', credentials=sa_creds, cache_discovery=False)
            except Exception as e:
                logger.warning(f"Failed to use GOOGLE_SERVICE_ACCOUNT_JSON: {e}")

        # Method 1: Try service account credentials from env (legacy var name)
        google_creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
        if google_creds_json:
            try:
                import json
                creds_dict = json.loads(google_creds_json)
                creds = service_account.Credentials.from_service_account_info(
                    creds_dict,
                    scopes=DRIVE_SCOPES
                )
                return build('drive', 'v3', credentials=creds)
            except Exception as e:
                logger.warning(f"Failed to use GOOGLE_CREDENTIALS_JSON: {e}")

        # Method 2: Try OAuth2 token file
        if os.path.exists('token.json'):
            try:
                creds = Credentials.from_authorized_user_file('token.json', DRIVE_SCOPES)
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    # Save refreshed token
                    with open('token.json', 'w') as f:
                        f.write(creds.to_json())
                return build('drive', 'v3', credentials=creds)
            except Exception as e:
                logger.warning(f"Failed to use token.json: {e}")

        # Method 3: Try service account file
        if os.path.exists('credentials.json'):
            try:
                creds = service_account.Credentials.from_service_account_file(
                    'credentials.json',
                    scopes=DRIVE_SCOPES
                )
                return build('drive', 'v3', credentials=creds)
            except Exception as e:
                logger.warning(f"Failed to use credentials.json: {e}")

        raise RuntimeError("No valid Google Drive credentials found")

    def _ensure_documents_folder(self) -> Optional[str]:
        """
        Ensure the main documents folder exists, creating it if necessary.

        Returns:
            Folder ID or None on failure
        """
        # If folder ID is provided via env, use it directly
        if self.documents_folder_id:
            return self.documents_folder_id

        # Check cache first
        if 'main_folder' in self._folder_cache:
            return self._folder_cache['main_folder']

        try:
            # Search for existing folder
            query = f"name='{self.DEFAULT_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()

            files = results.get('files', [])
            if files:
                # Folder exists, use it
                folder_id = files[0]['id']
                logger.info(f"Found existing documents folder: {folder_id}")
            else:
                # Create new folder
                folder_id = self.create_folder(self.DEFAULT_FOLDER_NAME)
                if folder_id:
                    logger.info(f"Created new documents folder: {folder_id}")
                else:
                    logger.error("Failed to create documents folder")
                    return None

            # Cache and store the folder ID
            self._folder_cache['main_folder'] = folder_id
            self.documents_folder_id = folder_id
            return folder_id

        except Exception as e:
            logger.error(f"Failed to ensure documents folder: {e}")
            return None

    def get_or_create_twg_folder(self, twg_name: str) -> Optional[str]:
        """
        Get or create a subfolder for a specific TWG.

        Args:
            twg_name: Name of the TWG (used as folder name)

        Returns:
            Folder ID or None on failure
        """
        if not self._ensure_initialized():
            return None

        # Ensure main folder exists first
        main_folder_id = self._ensure_documents_folder()
        if not main_folder_id:
            return None

        # Sanitize TWG name for folder name
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in twg_name).strip()

        # Check cache
        cache_key = f"twg_{safe_name}"
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]

        try:
            # Search for existing TWG folder
            query = f"name='{safe_name}' and mimeType='application/vnd.google-apps.folder' and '{main_folder_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()

            files = results.get('files', [])
            if files:
                folder_id = files[0]['id']
                logger.info(f"Found existing TWG folder '{safe_name}': {folder_id}")
            else:
                # Create new TWG folder under main folder
                folder_id = self.create_folder(safe_name, parent_id=main_folder_id)
                if folder_id:
                    logger.info(f"Created new TWG folder '{safe_name}': {folder_id}")
                else:
                    return None

            self._folder_cache[cache_key] = folder_id
            return folder_id

        except Exception as e:
            logger.error(f"Failed to get/create TWG folder '{twg_name}': {e}")
            return None

    def upload_file(
        self,
        file_content: BinaryIO,
        file_name: str,
        mime_type: str,
        folder_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Upload a file to Google Drive.

        Args:
            file_content: File-like object with content
            file_name: Name for the file
            mime_type: MIME type of the file
            folder_id: Google Drive folder ID (uses default if not provided)
            description: Optional description for the file

        Returns:
            Tuple of (file_id, web_view_link, download_url) or (None, None, None) on failure
        """
        if not self._ensure_initialized():
            logger.error("StorageService not initialized")
            return None, None, None

        folder_id = folder_id or self.documents_folder_id

        try:
            # Prepare file metadata
            file_metadata = {
                'name': file_name,
                'description': description or f'Uploaded via Martin System on {datetime.utcnow().isoformat()}'
            }

            if folder_id:
                file_metadata['parents'] = [folder_id]

            # Create media upload
            media = MediaIoBaseUpload(
                file_content,
                mimetype=mime_type,
                resumable=True
            )

            # Upload file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, webContentLink'
            ).execute()

            file_id = file.get('id')
            web_view_link = file.get('webViewLink')
            download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

            logger.info(f"Uploaded file '{file_name}' to Drive: {file_id}")

            return file_id, web_view_link, download_url

        except Exception as e:
            logger.error(f"Failed to upload file to Drive: {e}")
            return None, None, None

    def upload_bytes(
        self,
        file_bytes: bytes,
        file_name: str,
        mime_type: str,
        folder_id: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Upload bytes directly to Google Drive.

        Args:
            file_bytes: Raw file content as bytes
            file_name: Name for the file
            mime_type: MIME type of the file
            folder_id: Google Drive folder ID

        Returns:
            Tuple of (file_id, web_view_link, download_url)
        """
        return self.upload_file(
            io.BytesIO(file_bytes),
            file_name,
            mime_type,
            folder_id
        )

    def download_file(self, file_id: str) -> Optional[bytes]:
        """
        Download a file from Google Drive.

        Args:
            file_id: Google Drive file ID

        Returns:
            File content as bytes or None on failure
        """
        if not self._ensure_initialized():
            return None

        try:
            # Get file metadata
            file = self.service.files().get(
                fileId=file_id,
                fields='name, mimeType'
            ).execute()

            # Google Workspace native files must be exported (Docs → PDF, Sheets → xlsx, etc.)
            google_export_map = {
                "application/vnd.google-apps.document": "application/pdf",
                "application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/vnd.google-apps.presentation": "application/pdf",
            }
            mime = file.get("mimeType", "")
            if mime in google_export_map:
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType=google_export_map[mime],
                )
            else:
                request = self.service.files().get_media(fileId=file_id)

            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()

            buffer.seek(0)
            return buffer.read()

        except Exception as e:
            logger.error(f"Failed to download file {file_id}: {e}")
            return None

    def get_file_url(self, file_id: str) -> Optional[str]:
        """
        Get the download URL for a file.

        Args:
            file_id: Google Drive file ID or stored URL

        Returns:
            Download URL
        """
        # If it's already a URL, return it
        if file_id.startswith('http'):
            return file_id

        return f"https://drive.google.com/uc?export=download&id={file_id}"

    def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from Google Drive.

        Args:
            file_id: Google Drive file ID

        Returns:
            True if successful, False otherwise
        """
        if not self._ensure_initialized():
            return False

        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"Deleted file {file_id} from Drive")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            return False

    def get_file_metadata(self, file_id: str) -> Optional[dict]:
        """
        Get metadata for a file.

        Args:
            file_id: Google Drive file ID

        Returns:
            Dict with file metadata or None
        """
        if not self._ensure_initialized():
            return None

        try:
            file = self.service.files().get(
                fileId=file_id,
                fields='id, name, mimeType, size, createdTime, modifiedTime, webViewLink'
            ).execute()
            return file
        except Exception as e:
            logger.error(f"Failed to get metadata for {file_id}: {e}")
            return None

    def create_folder(self, name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Create a folder in Google Drive.

        Args:
            name: Folder name
            parent_id: Parent folder ID (optional)

        Returns:
            Created folder ID or None
        """
        if not self._ensure_initialized():
            return None

        try:
            file_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder'
            }

            if parent_id:
                file_metadata['parents'] = [parent_id]

            folder = self.service.files().create(
                body=file_metadata,
                fields='id, name'
            ).execute()

            logger.info(f"Created folder '{name}': {folder.get('id')}")
            return folder.get('id')

        except Exception as e:
            logger.error(f"Failed to create folder: {e}")
            return None


# Singleton instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get the singleton StorageService instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
