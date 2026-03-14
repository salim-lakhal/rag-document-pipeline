"""
URL Document Processor Module

This module provides functionality for processing web URLs, including:
- Fetching and extracting content from web pages
- Using advanced content extraction libraries (trafilatura, readability)
- Robust error handling for HTTP requests
"""

import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class URLProcessingError(Exception):
    """Custom exception for URL processing errors."""
    pass


def process_url(url: str, document_metadata: dict) -> dict:
    """
    Fetch and process content from a URL.

    Args:
        url: URL to fetch and process
        document_metadata: Additional metadata about the document

    Returns:
        Dictionary containing:
            - text: Extracted main content text
            - page_info: List with single entry containing document info
            - status: Processing status ('success', 'error', 'timeout', etc.)
            - metadata: Combined metadata including URL, title, etc.

    Raises:
        URLProcessingError: If URL processing fails critically
    """
    try:
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise URLProcessingError(f"Invalid URL format: {url}")

        if parsed_url.scheme not in ['http', 'https']:
            raise URLProcessingError(f"Unsupported URL scheme: {parsed_url.scheme}")

        logger.info(f"Processing URL: {url}")

        # Fetch and extract content
        extracted_text = fetch_and_extract(url)

        if not extracted_text:
            logger.warning(f"No content extracted from URL: {url}")
            status = 'no_content'
        else:
            status = 'success'

        # Create page info
        page_info = [{
            'page_number': 1,
            'text': extracted_text,
            'char_count': len(extracted_text),
            'is_ocr': False
        }]

        result = {
            'text': extracted_text,
            'page_info': page_info,
            'status': status,
            'metadata': {
                **document_metadata,
                'url': url,
                'domain': parsed_url.netloc,
                'page_count': 1,
                'total_chars': len(extracted_text),
                'processing_method': 'url_extraction'
            }
        }

        logger.info(f"Successfully processed URL: {url} ({len(extracted_text)} chars)")
        return result

    except URLProcessingError:
        raise
    except Exception as e:
        logger.error(f"Error processing URL {url}: {str(e)}")
        raise URLProcessingError(f"Failed to process URL: {str(e)}") from e


def fetch_and_extract(url: str) -> str:
    """
    Fetch HTML from URL and extract main content.

    Uses trafilatura as the primary extraction method, with fallback to
    readability-lxml for better extraction quality.

    Args:
        url: URL to fetch and extract content from

    Returns:
        Extracted main content text, or empty string on failure

    Note:
        Install dependencies with:
        pip install trafilatura readability-lxml requests
    """
    # First, try to fetch the URL
    html_content = handle_http_errors(url)

    if not html_content:
        logger.error(f"Failed to fetch content from URL: {url}")
        return ""

    # Try trafilatura first (generally better for news articles and blogs)
    extracted_text = _extract_with_trafilatura(html_content, url)

    if extracted_text and len(extracted_text) > 100:
        logger.debug(f"Successfully extracted content with trafilatura: {len(extracted_text)} chars")
        return extracted_text

    # Fallback to readability
    logger.info("Trafilatura extraction insufficient, trying readability")
    extracted_text = _extract_with_readability(html_content, url)

    if extracted_text and len(extracted_text) > 100:
        logger.debug(f"Successfully extracted content with readability: {len(extracted_text)} chars")
        return extracted_text

    # Last resort: use BeautifulSoup
    logger.info("Readability extraction insufficient, using BeautifulSoup")
    extracted_text = _extract_with_beautifulsoup(html_content)

    return extracted_text


def _extract_with_trafilatura(html_content: str, url: str) -> str:
    """
    Extract content using trafilatura library.

    Args:
        html_content: HTML content as string
        url: Original URL (for context)

    Returns:
        Extracted text or empty string
    """
    try:
        import trafilatura
    except ImportError:
        logger.warning("trafilatura not installed, skipping this extraction method")
        return ""

    try:
        # Extract with trafilatura (optimized for web articles)
        extracted = trafilatura.extract(
            html_content,
            url=url,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            deduplicate=True,
            output_format='txt'
        )

        return extracted or ""

    except Exception as e:
        logger.warning(f"Trafilatura extraction failed: {str(e)}")
        return ""


def _extract_with_readability(html_content: str, url: str) -> str:
    """
    Extract content using readability-lxml library.

    Args:
        html_content: HTML content as string
        url: Original URL (for context)

    Returns:
        Extracted text or empty string
    """
    try:
        from bs4 import BeautifulSoup
        from readability import Document
    except ImportError:
        logger.warning("readability-lxml or beautifulsoup4 not installed")
        return ""

    try:
        # Parse with readability
        doc = Document(html_content, url=url)

        # Get the main content HTML
        content_html = doc.summary()

        # Convert to text using BeautifulSoup
        soup = BeautifulSoup(content_html, 'html.parser')

        # Remove script and style elements
        for element in soup(['script', 'style']):
            element.decompose()

        # Get text
        text = soup.get_text(separator='\n', strip=True)

        # Clean up whitespace
        import re
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

        return text.strip()

    except Exception as e:
        logger.warning(f"Readability extraction failed: {str(e)}")
        return ""


def _extract_with_beautifulsoup(html_content: str) -> str:
    """
    Fallback extraction using BeautifulSoup.

    Args:
        html_content: HTML content as string

    Returns:
        Extracted text or empty string
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("BeautifulSoup not available for fallback extraction")
        return ""

    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()

        # Get text
        text = soup.get_text(separator='\n', strip=True)

        # Clean up
        import re
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

        return text.strip()

    except Exception as e:
        logger.error(f"BeautifulSoup extraction failed: {str(e)}")
        return ""


def handle_http_errors(url: str, timeout: int = 30, max_retries: int = 3) -> str | None:
    """
    Fetch URL content with comprehensive error handling.

    Features:
    - Retry logic with exponential backoff
    - User-agent spoofing to avoid blocks
    - Timeout handling
    - SSL error handling
    - Redirect following

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts

    Returns:
        HTML content as string, or None if fetch fails
    """
    try:
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
    except ImportError:
        raise URLProcessingError(
            "requests library not installed. Install with: pip install requests"
        )

    # Configure session with retry strategy
    session = requests.Session()

    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set headers to avoid being blocked
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    try:
        logger.info(f"Fetching URL: {url}")

        response = session.get(
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
            verify=True
        )

        # Check for successful response
        response.raise_for_status()

        # Check content type
        content_type = response.headers.get('Content-Type', '').lower()
        if 'html' not in content_type and 'xml' not in content_type:
            logger.warning(f"URL does not return HTML content: {content_type}")

        # Try to decode with proper encoding
        if response.encoding:
            html_content = response.text
        else:
            # Guess encoding
            html_content = response.content.decode('utf-8', errors='replace')

        logger.info(f"Successfully fetched {len(html_content)} bytes from {url}")
        return html_content

    except requests.exceptions.Timeout:
        logger.error(f"Timeout while fetching URL: {url}")
        return None

    except requests.exceptions.TooManyRedirects:
        logger.error(f"Too many redirects for URL: {url}")
        return None

    except requests.exceptions.SSLError as e:
        logger.error(f"SSL error for URL {url}: {str(e)}")
        # Retry without SSL verification as last resort
        try:
            logger.warning("Retrying without SSL verification")
            response = session.get(url, headers=headers, timeout=timeout, verify=False)
            response.raise_for_status()
            return response.text
        except Exception:
            return None

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error for URL {url}: {str(e)}")
        return None

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else 'unknown'
        logger.error(f"HTTP error {status_code} for URL {url}: {str(e)}")
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for URL {url}: {str(e)}")
        return None

    except Exception as e:
        logger.error(f"Unexpected error fetching URL {url}: {str(e)}")
        return None

    finally:
        session.close()


async def process_url_async(url: str, document_metadata: dict) -> dict:
    """
    Async version of URL processing using aiohttp.

    Args:
        url: URL to fetch and process
        document_metadata: Additional metadata about the document

    Returns:
        Dictionary with processing results
    """
    try:
        import aiohttp
    except ImportError:
        raise URLProcessingError(
            "aiohttp not installed. Install with: pip install aiohttp"
        )

    try:
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise URLProcessingError(f"Invalid URL format: {url}")

        logger.info(f"Processing URL (async): {url}")

        # Fetch content
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=30) as response:
                response.raise_for_status()
                html_content = await response.text()

        # Extract content (synchronous operations)
        extracted_text = _extract_with_trafilatura(html_content, url)

        if not extracted_text or len(extracted_text) < 100:
            extracted_text = _extract_with_readability(html_content, url)

        if not extracted_text or len(extracted_text) < 100:
            extracted_text = _extract_with_beautifulsoup(html_content)

        # Create result
        page_info = [{
            'page_number': 1,
            'text': extracted_text,
            'char_count': len(extracted_text),
            'is_ocr': False
        }]

        result = {
            'text': extracted_text,
            'page_info': page_info,
            'status': 'success' if extracted_text else 'no_content',
            'metadata': {
                **document_metadata,
                'url': url,
                'domain': parsed_url.netloc,
                'page_count': 1,
                'total_chars': len(extracted_text),
                'processing_method': 'url_extraction_async'
            }
        }

        logger.info(f"Successfully processed URL (async): {url} ({len(extracted_text)} chars)")
        return result

    except Exception as e:
        logger.error(f"Error in async URL processing: {str(e)}")
        raise URLProcessingError(f"Failed to process URL asynchronously: {str(e)}") from e


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    import sys

    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        metadata = {'source': 'command_line', 'category': 'test'}

        try:
            result = process_url(test_url, metadata)
            print(f"\nProcessing Status: {result['status']}")
            print(f"Total Characters: {result['metadata']['total_chars']}")
            print(f"Domain: {result['metadata']['domain']}")
            print(f"\nFirst 500 characters:\n{result['text'][:500]}")
        except URLProcessingError as e:
            print(f"Error: {e}")
    else:
        print("Usage: python url_processor.py <url>")
