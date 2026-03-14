"""
PDF Document Processor Module

This module provides functionality for processing PDF documents, including:
- Text extraction with page-level granularity
- OCR support for non-selectable text PDFs
- Structured output with metadata
"""

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PageInfo:
    """Represents information about a single page in a PDF."""

    page_number: int
    text: str
    char_count: int
    is_ocr: bool = False


class PDFProcessingError(Exception):
    """Custom exception for PDF processing errors."""

    pass


def process_pdf(file_path: str, document_metadata: dict) -> dict:
    """
    Process a PDF file and extract text with metadata.

    Args:
        file_path: Path to the PDF file
        document_metadata: Additional metadata about the document

    Returns:
        Dictionary containing:
            - text: Full extracted text
            - page_info: List of page-level information
            - status: Processing status ('success', 'ocr_required', 'error')
            - metadata: Combined metadata

    Raises:
        PDFProcessingError: If PDF processing fails
    """
    try:
        pdf_path = Path(file_path)

        if not pdf_path.exists():
            raise PDFProcessingError(f"PDF file not found: {file_path}")

        if not pdf_path.suffix.lower() == ".pdf":
            raise PDFProcessingError(f"File is not a PDF: {file_path}")

        logger.info(f"Processing PDF: {pdf_path}")

        # First, try to extract text normally
        pages_data = extract_text_with_pages(str(pdf_path))

        # Check if OCR is needed (no text extracted or very little text)
        total_chars = sum(page["char_count"] for page in pages_data)
        needs_ocr = total_chars < 50  # Threshold for considering OCR

        if needs_ocr:
            logger.info(f"PDF appears to be image-based, attempting OCR: {pdf_path}")
            ocr_text = ocr_pdf_if_needed(str(pdf_path))

            if ocr_text:
                # Create a single page info for OCR'd content
                pages_data = [
                    {
                        "page_number": 1,
                        "text": ocr_text,
                        "char_count": len(ocr_text),
                        "is_ocr": True,
                    }
                ]
                status = "success_ocr"
            else:
                status = "ocr_failed"
        else:
            status = "success"

        # Combine all text
        full_text = "\n\n".join(page["text"] for page in pages_data if page["text"])

        result = {
            "text": full_text,
            "page_info": pages_data,
            "status": status,
            "metadata": {
                **document_metadata,
                "file_path": str(pdf_path.absolute()),
                "file_name": pdf_path.name,
                "page_count": len(pages_data),
                "total_chars": len(full_text),
                "processing_method": "ocr" if needs_ocr else "text_extraction",
            },
        }

        logger.info(f"Successfully processed PDF: {pdf_path} ({len(pages_data)} pages)")
        return result

    except PDFProcessingError:
        raise
    except Exception as e:
        logger.error(f"Error processing PDF {file_path}: {str(e)}")
        raise PDFProcessingError(f"Failed to process PDF: {str(e)}") from e


def extract_text_with_pages(pdf_path: str) -> list[dict]:
    """
    Extract text from PDF with page-level granularity using pdfplumber.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of dictionaries, one per page, containing:
            - page_number: 1-indexed page number
            - text: Extracted text from the page
            - char_count: Character count
            - is_ocr: Whether OCR was used (False for this method)

    Raises:
        PDFProcessingError: If text extraction fails
    """
    try:
        import pdfplumber
    except ImportError:
        raise PDFProcessingError(
            "pdfplumber is not installed. Install with: pip install pdfplumber"
        )

    pages_data: list[dict] = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                try:
                    # Extract text from the page
                    text = page.extract_text() or ""

                    # Clean up excessive whitespace
                    text = _clean_extracted_text(text)

                    page_data = {
                        "page_number": page_num,
                        "text": text,
                        "char_count": len(text),
                        "is_ocr": False,
                    }

                    pages_data.append(page_data)
                    logger.debug(f"Extracted {len(text)} characters from page {page_num}")

                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num}: {str(e)}")
                    # Add empty page data to maintain page numbering
                    pages_data.append(
                        {"page_number": page_num, "text": "", "char_count": 0, "is_ocr": False}
                    )

        return pages_data

    except Exception as e:
        logger.error(f"Error opening PDF with pdfplumber: {str(e)}")
        raise PDFProcessingError(f"Failed to extract text from PDF: {str(e)}") from e


def ocr_pdf_if_needed(pdf_path: str) -> str:
    """
    Perform OCR on a PDF if text is not selectable.

    Uses pytesseract and pdf2image to convert PDF pages to images
    and extract text via OCR.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Extracted text via OCR, or empty string if OCR fails

    Note:
        Requires tesseract-ocr to be installed on the system:
        - Ubuntu/Debian: sudo apt-get install tesseract-ocr
        - macOS: brew install tesseract
        - Windows: Download from GitHub releases
    """
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError:
        logger.error(
            "OCR dependencies not installed. Install with: pip install pdf2image pytesseract pillow"
        )
        return ""

    try:
        logger.info(f"Starting OCR process for: {pdf_path}")

        # Convert PDF to images
        # Using lower DPI for faster processing; increase to 300 for better quality
        images = convert_from_path(pdf_path, dpi=200)

        extracted_texts: list[str] = []

        for page_num, image in enumerate(images, start=1):
            try:
                # Perform OCR on the image
                text = pytesseract.image_to_string(image, lang="fra+eng")

                # Clean up the text
                text = _clean_extracted_text(text)

                if text:
                    extracted_texts.append(f"--- Page {page_num} ---\n{text}")
                    logger.debug(f"OCR extracted {len(text)} characters from page {page_num}")

            except Exception as e:
                logger.warning(f"OCR failed for page {page_num}: {str(e)}")
                continue

        full_text = "\n\n".join(extracted_texts)
        logger.info(f"OCR completed: extracted {len(full_text)} total characters")

        return full_text

    except Exception as e:
        logger.error(f"OCR processing failed: {str(e)}")
        return ""


def _clean_extracted_text(text: str) -> str:
    """
    Clean extracted text by normalizing whitespace and removing artifacts.

    Args:
        text: Raw extracted text

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    # Replace multiple spaces with single space
    import re

    text = re.sub(r" +", " ", text)

    # Replace multiple newlines with maximum of 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text.strip()


# Async version for concurrent processing
async def process_pdf_async(file_path: str, document_metadata: dict) -> dict:
    """
    Async wrapper for PDF processing (runs in executor for I/O-bound operations).

    Args:
        file_path: Path to the PDF file
        document_metadata: Additional metadata about the document

    Returns:
        Dictionary with processing results
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(executor, process_pdf, file_path, document_metadata)

    return result


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Test with a sample PDF
    import sys

    if len(sys.argv) > 1:
        test_pdf = sys.argv[1]
        metadata = {"source": "command_line", "category": "test"}

        try:
            result = process_pdf(test_pdf, metadata)
            print(f"\nProcessing Status: {result['status']}")
            print(f"Pages: {result['metadata']['page_count']}")
            print(f"Total Characters: {result['metadata']['total_chars']}")
            print(f"\nFirst 500 characters:\n{result['text'][:500]}")
        except PDFProcessingError as e:
            print(f"Error: {e}")
    else:
        print("Usage: python pdf_processor.py <path_to_pdf>")
