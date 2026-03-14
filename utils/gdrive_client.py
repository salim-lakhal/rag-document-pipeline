"""
Google Drive Client Module

Provides a clean interface for interacting with Google Drive API,
including downloading files, uploading files, and managing Drive links.

Dependencies:
    - google-auth
    - google-auth-oauthlib
    - google-auth-httplib2
    - google-api-python-client

Environment Variables Required:
    - GOOGLE_DRIVE_CLIENT_ID
    - GOOGLE_DRIVE_CLIENT_SECRET
    - GOOGLE_DRIVE_REFRESH_TOKEN
"""

import logging
import os
import re
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GDriveClientError(Exception):
    """Base exception for GDrive Client errors."""

    pass


class InvalidDriveLinkError(GDriveClientError):
    """Raised when a Drive link is invalid or malformed."""

    pass


class FileDownloadError(GDriveClientError):
    """Raised when file download fails."""

    pass


class FileUploadError(GDriveClientError):
    """Raised when file upload fails."""

    pass


class AuthenticationError(GDriveClientError):
    """Raised when authentication fails."""

    pass


class GDriveClient:
    """
    Google Drive client for downloading and uploading files.

    This class provides methods to interact with Google Drive API using
    OAuth 2.0 credentials stored in environment variables.

    Attributes:
        credentials (Credentials): Google OAuth credentials
        service: Google Drive API service instance

    Example:
        >>> client = GDriveClient()
        >>> file_path = client.download_file(
        ...     "https://drive.google.com/file/d/1234567890/view",
        ...     "/path/to/output.pdf"
        ... )
        >>> print(f"Downloaded to: {file_path}")
    """

    # Scopes required for Drive operations
    SCOPES = ["https://www.googleapis.com/auth/drive"]

    def __init__(self, credentials_file: str | None = None) -> None:
        """
        Initialize Google Drive client with OAuth credentials.

        Args:
            credentials_file: Optional path to credentials JSON file.
                            If not provided, uses environment variables.

        Raises:
            AuthenticationError: If credentials are invalid or missing.

        Environment Variables:
            GOOGLE_DRIVE_CLIENT_ID: OAuth client ID
            GOOGLE_DRIVE_CLIENT_SECRET: OAuth client secret
            GOOGLE_DRIVE_REFRESH_TOKEN: OAuth refresh token
        """
        self.credentials: Credentials | None = None
        self.service = None

        try:
            self._authenticate(credentials_file)
            self.service = build("drive", "v3", credentials=self.credentials)
            logger.info("Google Drive client initialized successfully")
        except Exception as e:
            raise AuthenticationError(f"Failed to initialize Google Drive client: {str(e)}") from e

    def _authenticate(self, credentials_file: str | None = None) -> None:
        """
        Authenticate with Google Drive API using OAuth credentials.

        Args:
            credentials_file: Optional path to credentials JSON file.

        Raises:
            AuthenticationError: If authentication fails.
        """
        if credentials_file and Path(credentials_file).exists():
            # Load from file if provided
            try:
                from google.oauth2 import service_account

                self.credentials = service_account.Credentials.from_service_account_file(
                    credentials_file, scopes=self.SCOPES
                )
                return
            except Exception as e:
                logger.warning(f"Failed to load credentials from file: {e}")

        # Load from environment variables
        client_id = os.getenv("GOOGLE_DRIVE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_DRIVE_CLIENT_SECRET")
        refresh_token = os.getenv("GOOGLE_DRIVE_REFRESH_TOKEN")

        if not all([client_id, client_secret, refresh_token]):
            raise AuthenticationError(
                "Missing required environment variables: "
                "GOOGLE_DRIVE_CLIENT_ID, GOOGLE_DRIVE_CLIENT_SECRET, "
                "GOOGLE_DRIVE_REFRESH_TOKEN"
            )

        # Create credentials from environment variables
        self.credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=self.SCOPES,
        )

        # Refresh the token if needed
        if self.credentials and self.credentials.expired:
            try:
                self.credentials.refresh(Request())
            except Exception as e:
                raise AuthenticationError(f"Failed to refresh credentials: {str(e)}") from e

    def get_file_id_from_link(self, drive_link: str) -> str:
        """
        Extract file ID from a Google Drive link.

        Supports various Drive link formats:
        - https://drive.google.com/file/d/FILE_ID/view
        - https://drive.google.com/open?id=FILE_ID
        - https://drive.google.com/uc?id=FILE_ID
        - https://docs.google.com/document/d/FILE_ID/edit

        Args:
            drive_link: Google Drive sharing link

        Returns:
            The extracted file ID

        Raises:
            InvalidDriveLinkError: If the link format is invalid

        Example:
            >>> client = GDriveClient()
            >>> file_id = client.get_file_id_from_link(
            ...     "https://drive.google.com/file/d/1abc123xyz/view"
            ... )
            >>> print(file_id)  # "1abc123xyz"
        """
        if not drive_link:
            raise InvalidDriveLinkError("Drive link cannot be empty")

        # Pattern 1: /file/d/FILE_ID/ or /document/d/FILE_ID/
        pattern1 = r"/(?:file|document|presentation|spreadsheets)/d/([a-zA-Z0-9_-]+)"
        match = re.search(pattern1, drive_link)
        if match:
            return match.group(1)

        # Pattern 2: ?id=FILE_ID or &id=FILE_ID
        pattern2 = r"[?&]id=([a-zA-Z0-9_-]+)"
        match = re.search(pattern2, drive_link)
        if match:
            return match.group(1)

        # Pattern 3: Direct file ID (already extracted)
        if re.match(r"^[a-zA-Z0-9_-]+$", drive_link):
            return drive_link

        raise InvalidDriveLinkError(f"Unable to extract file ID from link: {drive_link}")

    def download_file(self, drive_link: str, output_path: str) -> str:
        """
        Download a file from Google Drive to local path.

        Args:
            drive_link: Google Drive sharing link or file ID
            output_path: Local path where file should be saved

        Returns:
            The absolute path to the downloaded file

        Raises:
            InvalidDriveLinkError: If the Drive link is invalid
            FileDownloadError: If download fails

        Example:
            >>> client = GDriveClient()
            >>> path = client.download_file(
            ...     "https://drive.google.com/file/d/1abc123/view",
            ...     "/tmp/document.pdf"
            ... )
            >>> print(f"File saved to: {path}")
        """
        try:
            file_id = self.get_file_id_from_link(drive_link)
            output_path = Path(output_path).resolve()

            # Create parent directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Request file metadata to get filename if needed
            file_metadata = (
                self.service.files().get(fileId=file_id, fields="name, mimeType").execute()
            )

            logger.info(f"Downloading file: {file_metadata.get('name')} (ID: {file_id})")

            # Download the file
            request = self.service.files().get_media(fileId=file_id)

            with open(output_path, "wb") as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        progress = int(status.progress() * 100)
                        logger.info(f"Download progress: {progress}%")

            logger.info(f"File downloaded successfully to: {output_path}")
            return str(output_path)

        except InvalidDriveLinkError:
            raise
        except HttpError as e:
            raise FileDownloadError(
                f"HTTP error downloading file: {e.resp.status} - {e.error_details}"
            ) from e
        except Exception as e:
            raise FileDownloadError(f"Failed to download file from Drive: {str(e)}") from e

    def upload_file(
        self, file_path: str, drive_folder_id: str | None = None, file_name: str | None = None
    ) -> str:
        """
        Upload a file to Google Drive.

        Args:
            file_path: Local path to file to upload
            drive_folder_id: Optional Drive folder ID to upload to.
                           If None, uploads to root directory.
            file_name: Optional custom filename. If None, uses original filename.

        Returns:
            The file ID of the uploaded file

        Raises:
            FileUploadError: If upload fails

        Example:
            >>> client = GDriveClient()
            >>> file_id = client.upload_file(
            ...     "/path/to/document.pdf",
            ...     drive_folder_id="folder123"
            ... )
            >>> print(f"Uploaded file ID: {file_id}")
        """
        try:
            file_path = Path(file_path).resolve()

            if not file_path.exists():
                raise FileUploadError(f"File does not exist: {file_path}")

            if not file_path.is_file():
                raise FileUploadError(f"Path is not a file: {file_path}")

            # Determine filename
            name = file_name or file_path.name

            # Prepare file metadata
            file_metadata = {"name": name}
            if drive_folder_id:
                file_metadata["parents"] = [drive_folder_id]

            # Create media upload
            media = MediaFileUpload(str(file_path), resumable=True)

            logger.info(f"Uploading file: {name} ({file_path.stat().st_size} bytes)")

            # Upload file
            file = (
                self.service.files()
                .create(body=file_metadata, media_body=media, fields="id, name, webViewLink")
                .execute()
            )

            file_id = file.get("id")
            web_link = file.get("webViewLink", "N/A")

            logger.info(f"File uploaded successfully - ID: {file_id}, Link: {web_link}")

            return file_id

        except FileUploadError:
            raise
        except HttpError as e:
            raise FileUploadError(
                f"HTTP error uploading file: {e.resp.status} - {e.error_details}"
            ) from e
        except Exception as e:
            raise FileUploadError(f"Failed to upload file to Drive: {str(e)}") from e

    def get_file_metadata(self, file_id: str) -> dict:
        """
        Get metadata for a file in Google Drive.

        Args:
            file_id: Google Drive file ID

        Returns:
            Dictionary containing file metadata

        Raises:
            GDriveClientError: If metadata retrieval fails

        Example:
            >>> client = GDriveClient()
            >>> metadata = client.get_file_metadata("file123")
            >>> print(metadata['name'], metadata['mimeType'])
        """
        try:
            file_metadata = (
                self.service.files()
                .get(
                    fileId=file_id,
                    fields="id, name, mimeType, size, createdTime, modifiedTime, webViewLink",
                )
                .execute()
            )

            return file_metadata

        except HttpError as e:
            raise GDriveClientError(
                f"Failed to get file metadata: {e.resp.status} - {e.error_details}"
            ) from e
        except Exception as e:
            raise GDriveClientError(f"Error retrieving file metadata: {str(e)}") from e
