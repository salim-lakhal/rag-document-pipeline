"""
Document Processors Package

This package provides processors for various document formats:
- PDF documents (with OCR support)
- HTML documents
- Web URLs

Each processor extracts text content and returns structured data
with metadata.
"""

from .pdf_processor import (
    process_pdf,
    extract_text_with_pages,
    ocr_pdf_if_needed,
    process_pdf_async,
    PDFProcessingError
)

from .html_processor import (
    process_html,
    extract_main_content,
    clean_html_artifacts,
    process_html_async,
    extract_metadata_from_html,
    HTMLProcessingError
)

from .url_processor import (
    process_url,
    fetch_and_extract,
    handle_http_errors,
    process_url_async,
    URLProcessingError
)

__all__ = [
    # PDF Processor
    'process_pdf',
    'extract_text_with_pages',
    'ocr_pdf_if_needed',
    'process_pdf_async',
    'PDFProcessingError',

    # HTML Processor
    'process_html',
    'extract_main_content',
    'clean_html_artifacts',
    'process_html_async',
    'extract_metadata_from_html',
    'HTMLProcessingError',

    # URL Processor
    'process_url',
    'fetch_and_extract',
    'handle_http_errors',
    'process_url_async',
    'URLProcessingError',
]

__version__ = '1.0.0'
