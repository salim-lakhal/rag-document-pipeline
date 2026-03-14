"""
HTML Document Processor Module

This module provides functionality for processing HTML documents, including:
- Main content extraction from HTML
- Removal of scripts, styles, and navigation elements
- Cleaning of HTML artifacts from extracted text
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class HTMLProcessingError(Exception):
    """Custom exception for HTML processing errors."""

    pass


def process_html(file_path: str, document_metadata: dict) -> dict:
    """
    Process an HTML file and extract main content.

    Args:
        file_path: Path to the HTML file
        document_metadata: Additional metadata about the document

    Returns:
        Dictionary containing:
            - text: Extracted main content text
            - page_info: List with single entry containing document info
            - status: Processing status ('success' or 'error')
            - metadata: Combined metadata

    Raises:
        HTMLProcessingError: If HTML processing fails
    """
    try:
        html_path = Path(file_path)

        if not html_path.exists():
            raise HTMLProcessingError(f"HTML file not found: {file_path}")

        # Check for HTML-like extensions
        valid_extensions = {".html", ".htm", ".xhtml", ".xml"}
        if html_path.suffix.lower() not in valid_extensions:
            logger.warning(f"File may not be HTML: {file_path}")

        logger.info(f"Processing HTML: {html_path}")

        # Read the HTML file
        try:
            with open(html_path, encoding="utf-8") as f:
                html_content = f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            logger.warning(f"UTF-8 decoding failed, trying latin-1 for {html_path}")
            with open(html_path, encoding="latin-1") as f:
                html_content = f.read()

        # Extract main content
        main_text = extract_main_content(html_content)

        # Clean HTML artifacts
        cleaned_text = clean_html_artifacts(main_text)

        # Create page info (single entry for HTML documents)
        page_info = [
            {
                "page_number": 1,
                "text": cleaned_text,
                "char_count": len(cleaned_text),
                "is_ocr": False,
            }
        ]

        result = {
            "text": cleaned_text,
            "page_info": page_info,
            "status": "success",
            "metadata": {
                **document_metadata,
                "file_path": str(html_path.absolute()),
                "file_name": html_path.name,
                "page_count": 1,
                "total_chars": len(cleaned_text),
                "processing_method": "html_extraction",
            },
        }

        logger.info(f"Successfully processed HTML: {html_path} ({len(cleaned_text)} chars)")
        return result

    except HTMLProcessingError:
        raise
    except Exception as e:
        logger.error(f"Error processing HTML {file_path}: {str(e)}")
        raise HTMLProcessingError(f"Failed to process HTML: {str(e)}") from e


def extract_main_content(html_content: str) -> str:
    """
    Parse HTML and extract main content using BeautifulSoup.

    Removes:
    - Scripts and style tags
    - Navigation elements
    - Headers and footers
    - Sidebars
    - Advertisements

    Args:
        html_content: Raw HTML content as string

    Returns:
        Extracted main text content

    Raises:
        HTMLProcessingError: If parsing fails
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise HTMLProcessingError(
            "BeautifulSoup is not installed. Install with: pip install beautifulsoup4 lxml"
        )

    try:
        # Parse HTML with lxml parser (faster) or fall back to html.parser
        try:
            soup = BeautifulSoup(html_content, "lxml")
        except Exception:
            soup = BeautifulSoup(html_content, "html.parser")

        # Remove unwanted elements
        unwanted_tags = [
            "script",
            "style",
            "noscript",
            "iframe",
            "embed",
            "object",
            "applet",
            "canvas",
            "svg",
        ]

        for tag in unwanted_tags:
            for element in soup.find_all(tag):
                element.decompose()

        # Remove common navigation and non-content elements
        unwanted_classes_ids = [
            "nav",
            "navigation",
            "navbar",
            "menu",
            "sidebar",
            "header",
            "footer",
            "advertisement",
            "ad",
            "ads",
            "social",
            "share",
            "cookie",
            "popup",
            "modal",
            "banner",
            "promo",
            "promotion",
        ]

        for identifier in unwanted_classes_ids:
            # Remove by class
            for element in soup.find_all(class_=lambda x: x and identifier in x.lower()):
                element.decompose()

            # Remove by id
            for element in soup.find_all(id=lambda x: x and identifier in x.lower()):
                element.decompose()

            # Remove by tag name
            for element in soup.find_all(identifier):
                element.decompose()

        # Try to find main content area
        main_content = None

        # Look for semantic HTML5 tags first
        main_content_tags = ["main", "article"]
        for tag in main_content_tags:
            main_element = soup.find(tag)
            if main_element:
                main_content = main_element
                break

        # Look for common content containers
        if not main_content:
            content_selectors = [
                {"id": "content"},
                {"id": "main"},
                {"id": "main-content"},
                {"class_": "content"},
                {"class_": "main-content"},
                {"class_": "post-content"},
                {"class_": "entry-content"},
                {"role": "main"},
            ]

            for selector in content_selectors:
                main_element = soup.find(attrs=selector)
                if main_element:
                    main_content = main_element
                    break

        # If no main content found, use body
        if not main_content:
            main_content = soup.find("body") or soup

        # Extract text with better spacing
        text = _extract_text_with_spacing(main_content)

        return text

    except Exception as e:
        logger.error(f"Error extracting main content: {str(e)}")
        raise HTMLProcessingError(f"Failed to extract main content: {str(e)}") from e


def _extract_text_with_spacing(element) -> str:
    """
    Extract text from BeautifulSoup element with proper spacing.

    Args:
        element: BeautifulSoup element

    Returns:
        Text with proper spacing between elements
    """
    # Block-level elements that should have newlines
    block_elements = {
        "p",
        "div",
        "section",
        "article",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "tr",
        "br",
        "hr",
        "pre",
        "blockquote",
        "table",
        "ul",
        "ol",
        "dl",
    }

    text_parts = []

    for child in element.descendants:
        if isinstance(child, str):
            text = child.strip()
            if text:
                text_parts.append(text)
        elif child.name in block_elements:
            text_parts.append("\n")

    # Join and clean up
    text = " ".join(text_parts)

    # Normalize whitespace
    text = re.sub(r" +", " ", text)
    text = re.sub(r"\n +", "\n", text)
    text = re.sub(r" +\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def clean_html_artifacts(text: str) -> str:
    """
    Remove HTML remnants and artifacts from extracted text.

    Removes:
    - HTML entities (both named and numeric)
    - Remaining HTML tags
    - URLs that are artifacts
    - Excessive whitespace

    Args:
        text: Text potentially containing HTML artifacts

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    import html

    # Decode HTML entities
    text = html.unescape(text)

    # Remove any remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Remove numeric HTML entities that weren't decoded
    text = re.sub(r"&#\d+;", "", text)
    text = re.sub(r"&#x[0-9a-fA-F]+;", "", text)

    # Remove common HTML artifacts
    artifacts = [
        r"\[if\s+.*?\]",  # IE conditional comments
        r"\[endif\]",
        r"<!--.*?-->",  # HTML comments
    ]

    for pattern in artifacts:
        text = re.sub(pattern, "", text, flags=re.DOTALL)

    # Clean up whitespace
    text = re.sub(r" +", " ", text)
    text = re.sub(r"\t+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

    # Remove lines that are just whitespace
    lines = [line.strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    text = "\n".join(lines)

    # Remove URLs that are likely artifacts (standalone URLs)
    text = re.sub(r"^\s*https?://\S+\s*$", "", text, flags=re.MULTILINE)

    return text.strip()


async def process_html_async(file_path: str, document_metadata: dict) -> dict:
    """
    Async wrapper for HTML processing.

    Args:
        file_path: Path to the HTML file
        document_metadata: Additional metadata about the document

    Returns:
        Dictionary with processing results
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(executor, process_html, file_path, document_metadata)

    return result


def extract_metadata_from_html(html_content: str) -> dict:
    """
    Extract metadata from HTML head section.

    Args:
        html_content: Raw HTML content

    Returns:
        Dictionary with extracted metadata (title, description, author, etc.)
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return {}

    metadata = {}

    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract title
        title_tag = soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.get_text().strip()

        # Extract meta tags
        meta_tags = {
            "description": ["name", "description"],
            "author": ["name", "author"],
            "keywords": ["name", "keywords"],
            "og_title": ["property", "og:title"],
            "og_description": ["property", "og:description"],
        }

        for key, (attr, value) in meta_tags.items():
            meta = soup.find("meta", attrs={attr: value})
            if meta and meta.get("content"):
                metadata[key] = meta["content"].strip()

    except Exception as e:
        logger.warning(f"Error extracting metadata: {str(e)}")

    return metadata


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    import sys

    if len(sys.argv) > 1:
        test_html = sys.argv[1]
        metadata = {"source": "command_line", "category": "test"}

        try:
            result = process_html(test_html, metadata)
            print(f"\nProcessing Status: {result['status']}")
            print(f"Total Characters: {result['metadata']['total_chars']}")
            print(f"\nFirst 500 characters:\n{result['text'][:500]}")
        except HTMLProcessingError as e:
            print(f"Error: {e}")
    else:
        print("Usage: python html_processor.py <path_to_html>")
