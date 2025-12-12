"""
URL Document Processor with HTML Caching

This module processes web URLs with caching functionality:
1. Fetches webpage from source_url
2. Saves HTML to GDrive/DB/html/<document_id>.html
3. Updates drive_link in metadata to point to cached HTML
4. Processes cached HTML like a local file
5. Keeps source_url in metadata for reference

Per Consigne.txt section: "Quick Note for Claude – URL Handling in Pipeline"
"""

from pathlib import Path
from typing import Dict, Optional
import logging
from urllib.parse import urlparse
import tempfile

logger = logging.getLogger(__name__)


class URLProcessingError(Exception):
    """Custom exception for URL processing errors."""
    pass


def fetch_and_cache_url(
    url: str,
    document_id: str,
    gdrive_client,
    metadata_manager,
    html_folder_id: Optional[str] = None,
    local_cache_dir: str = "/home/salim/Informatique/Perso/OQTF/data/html_cache"
) -> tuple[str, str]:
    """
    Fetch URL content and cache it as HTML to Google Drive.

    Args:
        url: Source URL to fetch
        document_id: Unique document identifier
        gdrive_client: GDriveClient instance for uploading
        metadata_manager: MetadataManager instance for updating metadata
        html_folder_id: Google Drive folder ID for HTML files
        local_cache_dir: Local directory for temporary HTML cache

    Returns:
        Tuple of (local_html_path, drive_link)

    Raises:
        URLProcessingError: If fetching or caching fails
    """
    try:
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise URLProcessingError(f"Invalid URL format: {url}")

        logger.info(f"Fetching URL: {url}")

        # Import requests here to avoid circular imports
        import requests

        # Fetch the webpage
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
        }

        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()

        html_content = response.text
        logger.info(f"Successfully fetched {len(html_content)} bytes from {url}")

        # Create local cache directory
        cache_dir = Path(local_cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Save HTML locally
        html_filename = f"{document_id}.html"
        local_html_path = cache_dir / html_filename

        with open(local_html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"Cached HTML locally: {local_html_path}")

        # Upload to Google Drive
        logger.info(f"Uploading HTML to Google Drive...")
        file_id = gdrive_client.upload_file(
            str(local_html_path),
            drive_folder_id=html_folder_id,
            file_name=html_filename
        )

        # Generate Drive link
        drive_link = f"https://drive.google.com/file/d/{file_id}/view"
        logger.info(f"HTML uploaded to Drive: {drive_link}")

        # Update metadata with new drive_link
        logger.info(f"Updating metadata for {document_id} with drive_link")
        metadata_manager.update_document(
            document_id,
            drive_link=drive_link
        )

        return str(local_html_path), drive_link

    except requests.exceptions.RequestException as e:
        raise URLProcessingError(f"Failed to fetch URL {url}: {str(e)}") from e
    except Exception as e:
        raise URLProcessingError(f"Failed to cache URL {url}: {str(e)}") from e


def process_url_with_cache(
    document_id: str,
    source_url: str,
    document_metadata: Dict,
    gdrive_client,
    metadata_manager,
    html_processor,
    html_folder_id: Optional[str] = None
) -> dict:
    """
    Process URL by caching HTML and then processing like a local file.

    Workflow:
    1. Fetch webpage from source_url
    2. Save HTML to GDrive/DB/html/<document_id>.html
    3. Update drive_link in metadata
    4. Process HTML like local file
    5. Keep source_url in metadata

    Args:
        document_id: Unique document identifier
        source_url: Original URL to fetch
        document_metadata: Document metadata dict
        gdrive_client: GDriveClient instance
        metadata_manager: MetadataManager instance
        html_processor: HTML processor function
        html_folder_id: Google Drive folder ID for HTML files

    Returns:
        Dictionary with processing results from HTML processor

    Raises:
        URLProcessingError: If processing fails
    """
    try:
        logger.info(f"Processing URL with caching: {document_id}")
        logger.info(f"Source URL: {source_url}")

        # Step 1: Fetch and cache HTML
        local_html_path, drive_link = fetch_and_cache_url(
            url=source_url,
            document_id=document_id,
            gdrive_client=gdrive_client,
            metadata_manager=metadata_manager,
            html_folder_id=html_folder_id
        )

        # Step 2: Process cached HTML file using HTML processor
        logger.info(f"Processing cached HTML file: {local_html_path}")
        result = html_processor(
            file_path=local_html_path,
            document_metadata=document_metadata
        )

        # Step 3: Ensure source_url is preserved in metadata
        result['metadata']['source_url'] = source_url
        result['metadata']['drive_link'] = drive_link
        result['metadata']['cached_from_url'] = True

        logger.info(f"Successfully processed URL {document_id}")
        logger.info(f"Source URL: {source_url}")
        logger.info(f"Cached HTML: {drive_link}")

        return result

    except Exception as e:
        logger.error(f"Failed to process URL {document_id}: {str(e)}")
        raise URLProcessingError(
            f"Failed to process URL for document {document_id}: {str(e)}"
        ) from e


def process_url_simple(url: str, document_metadata: dict) -> dict:
    """
    Simple URL processing without caching (legacy method).

    For backward compatibility. Processes URL directly without caching to Drive.

    Args:
        url: URL to process
        document_metadata: Document metadata

    Returns:
        Dictionary with extracted content
    """
    from processors.url_processor import process_url as _process_url_original
    return _process_url_original(url, document_metadata)


# Convenience function for integration with pipeline
def process_url(
    document_id: str,
    source_url: str,
    document_metadata: Dict,
    gdrive_client=None,
    metadata_manager=None,
    html_processor=None,
    html_folder_id: Optional[str] = None,
    cache_to_drive: bool = True
) -> dict:
    """
    Main entry point for URL processing.

    Args:
        document_id: Unique document identifier
        source_url: URL to process
        document_metadata: Document metadata
        gdrive_client: Optional GDriveClient (required if cache_to_drive=True)
        metadata_manager: Optional MetadataManager (required if cache_to_drive=True)
        html_processor: Optional HTML processor function (required if cache_to_drive=True)
        html_folder_id: Google Drive folder ID for cached HTML
        cache_to_drive: Whether to cache HTML to Drive (default: True)

    Returns:
        Dictionary with processing results
    """
    if cache_to_drive:
        if not all([gdrive_client, metadata_manager, html_processor]):
            raise URLProcessingError(
                "cache_to_drive=True requires gdrive_client, metadata_manager, "
                "and html_processor arguments"
            )

        return process_url_with_cache(
            document_id=document_id,
            source_url=source_url,
            document_metadata=document_metadata,
            gdrive_client=gdrive_client,
            metadata_manager=metadata_manager,
            html_processor=html_processor,
            html_folder_id=html_folder_id
        )
    else:
        # Legacy mode: process without caching
        return process_url_simple(source_url, document_metadata)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("URL Processor with HTML Caching")
    print("=" * 60)
    print()
    print("This module implements URL caching to Google Drive:")
    print("1. Fetches webpage from source_url")
    print("2. Saves HTML to GDrive/DB/html/<document_id>.html")
    print("3. Updates drive_link in metadata")
    print("4. Processes cached HTML like local file")
    print("5. Keeps source_url for reference")
    print()
    print("Usage:")
    print("  from processors.url_processor_with_cache import process_url")
    print("  from utils.gdrive_client import GDriveClient")
    print("  from utils.metadata_manager import MetadataManager")
    print("  from processors.html_processor import process_html")
    print()
    print("  result = process_url(")
    print("      document_id='doc_123',")
    print("      source_url='https://example.com/page',")
    print("      document_metadata=metadata,")
    print("      gdrive_client=gdrive_client,")
    print("      metadata_manager=metadata_manager,")
    print("      html_processor=process_html")
    print("  )")
