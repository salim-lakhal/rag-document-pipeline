"""
Utils Package

Utility modules for the RAG document pipeline.

Modules:
    - gdrive_client: Google Drive integration for file operations
    - metadata_manager: Metadata management for document processing
"""

from .gdrive_client import (
    AuthenticationError,
    FileDownloadError,
    FileUploadError,
    GDriveClient,
    GDriveClientError,
    InvalidDriveLinkError,
)
from .metadata_manager import (
    DocumentNotFoundError,
    MetadataError,
    MetadataFileNotFoundError,
    MetadataManager,
    MetadataValidationError,
)

__all__ = [
    # GDrive Client
    "GDriveClient",
    "GDriveClientError",
    "InvalidDriveLinkError",
    "FileDownloadError",
    "FileUploadError",
    "AuthenticationError",
    # Metadata Manager
    "MetadataManager",
    "MetadataError",
    "MetadataFileNotFoundError",
    "MetadataValidationError",
    "DocumentNotFoundError",
]

__version__ = "1.0.0"
