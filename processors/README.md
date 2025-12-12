# Document Processors

A collection of Python modules for processing various document formats and extracting text content.

## Features

### PDF Processor (`pdf_processor.py`)
- Extract text from PDF files with page-level granularity using `pdfplumber`
- OCR support for scanned PDFs using `pytesseract` and `pdf2image`
- Automatic detection of image-based PDFs
- Async processing support

### HTML Processor (`html_processor.py`)
- Extract main content from HTML documents
- Remove scripts, styles, navigation, and other non-content elements
- Clean HTML artifacts and entities
- Metadata extraction from HTML head tags

### URL Processor (`url_processor.py`)
- Fetch and process web pages
- Multiple extraction strategies (trafilatura, readability, BeautifulSoup)
- Robust error handling with retries
- Async processing with aiohttp

## Installation

### System Requirements

For PDF OCR support, install Tesseract OCR:

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

### Python Dependencies

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
# PDF processing
pip install pdfplumber pdf2image pytesseract Pillow

# HTML processing
pip install beautifulsoup4 lxml

# URL processing
pip install requests trafilatura readability-lxml aiohttp
```

## Usage

### Basic Usage

```python
from processors import process_pdf, process_html, process_url

# Process a PDF
result = process_pdf(
    file_path="/path/to/document.pdf",
    document_metadata={"source": "upload", "category": "legal"}
)

# Process an HTML file
result = process_html(
    file_path="/path/to/document.html",
    document_metadata={"source": "web_scrape"}
)

# Process a URL
result = process_url(
    url="https://example.com/article",
    document_metadata={"category": "news"}
)
```

### Result Structure

All processors return a consistent structure:

```python
{
    "text": str,              # Full extracted text
    "page_info": [            # List of page information
        {
            "page_number": int,
            "text": str,
            "char_count": int,
            "is_ocr": bool
        }
    ],
    "status": str,            # 'success', 'success_ocr', 'error', etc.
    "metadata": {             # Combined metadata
        "file_path": str,     # (PDF/HTML only)
        "url": str,           # (URL only)
        "page_count": int,
        "total_chars": int,
        "processing_method": str,
        ...                   # Plus user-provided metadata
    }
}
```

### Async Processing

```python
import asyncio
from processors import process_pdf_async, process_url_async

async def main():
    # Process multiple documents concurrently
    results = await asyncio.gather(
        process_pdf_async("/path/to/doc1.pdf", {"id": 1}),
        process_pdf_async("/path/to/doc2.pdf", {"id": 2}),
        process_url_async("https://example.com", {"id": 3})
    )

    for result in results:
        print(f"Extracted {result['metadata']['total_chars']} characters")

asyncio.run(main())
```

### Command-Line Usage

Each module can be run directly:

```bash
# PDF
python processors/pdf_processor.py /path/to/document.pdf

# HTML
python processors/html_processor.py /path/to/document.html

# URL
python processors/url_processor.py https://example.com/article
```

## Advanced Features

### PDF Processing

```python
from processors import extract_text_with_pages, ocr_pdf_if_needed

# Extract text with page details
pages = extract_text_with_pages("/path/to/document.pdf")
for page in pages:
    print(f"Page {page['page_number']}: {page['char_count']} chars")

# Force OCR on a PDF
ocr_text = ocr_pdf_if_needed("/path/to/scanned.pdf")
```

### HTML Processing

```python
from processors import extract_main_content, clean_html_artifacts, extract_metadata_from_html

# Extract from HTML string
with open("/path/to/page.html") as f:
    html = f.read()

main_content = extract_main_content(html)
metadata = extract_metadata_from_html(html)
cleaned = clean_html_artifacts(main_content)
```

### URL Processing

```python
from processors import fetch_and_extract, handle_http_errors

# Just fetch HTML
html = handle_http_errors("https://example.com", timeout=30, max_retries=3)

# Fetch and extract
text = fetch_and_extract("https://example.com/article")
```

## Error Handling

Each processor has its own exception class:

```python
from processors import PDFProcessingError, HTMLProcessingError, URLProcessingError

try:
    result = process_pdf("/path/to/document.pdf", {})
except PDFProcessingError as e:
    print(f"PDF processing failed: {e}")
```

## Logging

All processors use Python's logging module:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Process with logging
result = process_pdf("/path/to/document.pdf", {})
```

## Performance Tips

1. **Use async processing** for multiple documents
2. **Adjust OCR DPI**: Lower DPI (150-200) for speed, higher (300+) for quality
3. **Cache HTTP requests** when processing multiple URLs
4. **Pre-filter PDFs**: Check file size before OCR processing

## License

MIT License

## Contributing

Contributions welcome! Please ensure:
- Type hints on all functions
- Comprehensive error handling
- Docstrings following Google style
- Unit tests with pytest
