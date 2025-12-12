"""
Utils Package

Utility modules for the OQTF RAG Pipeline project.

Modules:
    - gdrive_client: Google Drive integration for file operations
    - metadata_manager: Metadata management for document processing
"""

from .gdrive_client import (
    GDriveClient,
    GDriveClientError,
    InvalidDriveLinkError,
    FileDownloadError,
    FileUploadError,
    AuthenticationError
)

from .metadata_manager import (
    MetadataManager,
    MetadataError,
    MetadataFileNotFoundError,
    MetadataValidationError,
    DocumentNotFoundError
)

__all__ = [
    # GDrive Client
    'GDriveClient',
    'GDriveClientError',
    'InvalidDriveLinkError',
    'FileDownloadError',
    'FileUploadError',
    'AuthenticationError',
    # Metadata Manager
    'MetadataManager',
    'MetadataError',
    'MetadataFileNotFoundError',
    'MetadataValidationError',
    'DocumentNotFoundError',
]

__version__ = '0.1.0'
