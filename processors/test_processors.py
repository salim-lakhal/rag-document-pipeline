"""
Test suite for document processors

Run with: pytest test_processors.py -v
or: python test_processors.py
"""

import pytest
from pathlib import Path
import tempfile
import asyncio
from typing import Dict

# Import processors
try:
    from pdf_processor import (
        process_pdf, extract_text_with_pages, ocr_pdf_if_needed,
        PDFProcessingError, process_pdf_async
    )
    from html_processor import (
        process_html, extract_main_content, clean_html_artifacts,
        HTMLProcessingError, extract_metadata_from_html
    )
    from url_processor import (
        process_url, fetch_and_extract, handle_http_errors,
        URLProcessingError, process_url_async
    )
except ImportError:
    # Try absolute import
    from processors.pdf_processor import (
        process_pdf, extract_text_with_pages, ocr_pdf_if_needed,
        PDFProcessingError, process_pdf_async
    )
    from processors.html_processor import (
        process_html, extract_main_content, clean_html_artifacts,
        HTMLProcessingError, extract_metadata_from_html
    )
    from processors.url_processor import (
        process_url, fetch_and_extract, handle_http_errors,
        URLProcessingError, process_url_async
    )


# Test HTML content samples
SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Article</title>
    <meta name="description" content="A test article for HTML processing">
    <meta name="author" content="Test Author">
    <style>
        body { font-family: Arial; }
    </style>
    <script>
        console.log('This should be removed');
    </script>
</head>
<body>
    <nav>
        <a href="/">Home</a>
        <a href="/about">About</a>
    </nav>
    <main>
        <article>
            <h1>Main Article Title</h1>
            <p>This is the first paragraph of the article.</p>
            <p>This is the second paragraph with more content.</p>
            <div class="content">
                <h2>Subsection</h2>
                <p>Additional content in a subsection.</p>
            </div>
        </article>
    </main>
    <footer>
        <p>Copyright 2024</p>
    </footer>
    <div class="advertisement">
        <p>This is an ad and should be removed</p>
    </div>
</body>
</html>
"""


class TestHTMLProcessor:
    """Tests for HTML processor module."""

    def test_extract_main_content(self):
        """Test main content extraction from HTML."""
        content = extract_main_content(SAMPLE_HTML)

        # Should contain main content
        assert "Main Article Title" in content
        assert "first paragraph" in content
        assert "second paragraph" in content

        # Should NOT contain navigation or footer
        assert "Home" not in content or "About" not in content
        assert "Copyright" not in content

    def test_clean_html_artifacts(self):
        """Test cleaning of HTML artifacts."""
        dirty_text = "This has &nbsp; HTML entities &#8212; and <b>tags</b>"
        cleaned = clean_html_artifacts(dirty_text)

        assert "&nbsp;" not in cleaned
        assert "&#8212;" not in cleaned
        assert "<b>" not in cleaned
        assert "tags" in cleaned

    def test_extract_metadata(self):
        """Test metadata extraction from HTML."""
        metadata = extract_metadata_from_html(SAMPLE_HTML)

        assert metadata.get('title') == "Test Article"
        assert metadata.get('description') == "A test article for HTML processing"
        assert metadata.get('author') == "Test Author"

    def test_process_html_with_file(self):
        """Test processing HTML from file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(SAMPLE_HTML)
            temp_path = f.name

        try:
            result = process_html(temp_path, {"test": "metadata"})

            assert result['status'] == 'success'
            assert 'text' in result
            assert 'page_info' in result
            assert 'metadata' in result
            assert result['metadata']['test'] == 'metadata'
            assert result['metadata']['page_count'] == 1
            assert "Main Article Title" in result['text']

        finally:
            Path(temp_path).unlink()

    def test_process_html_invalid_file(self):
        """Test processing non-existent HTML file."""
        with pytest.raises(HTMLProcessingError):
            process_html("/nonexistent/file.html", {})

    @pytest.mark.asyncio
    async def test_process_html_async(self):
        """Test async HTML processing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(SAMPLE_HTML)
            temp_path = f.name

        try:
            result = await process_html_async(temp_path, {"async": True})
            assert result['status'] == 'success'
            assert result['metadata']['async'] is True
        finally:
            Path(temp_path).unlink()


class TestURLProcessor:
    """Tests for URL processor module."""

    def test_handle_http_errors_invalid_url(self):
        """Test handling of invalid URLs."""
        result = handle_http_errors("not-a-valid-url")
        assert result is None

    def test_handle_http_errors_nonexistent(self):
        """Test handling of non-existent domains."""
        result = handle_http_errors("https://this-domain-definitely-does-not-exist-12345.com")
        assert result is None

    @pytest.mark.integration
    def test_fetch_and_extract_real_url(self):
        """Test fetching and extracting from a real URL."""
        # Using example.com as a reliable test URL
        result = fetch_and_extract("https://example.com")

        assert result is not None
        assert len(result) > 0
        # example.com contains this text
        assert "Example Domain" in result or "example" in result.lower()

    @pytest.mark.integration
    def test_process_url_success(self):
        """Test full URL processing with example.com."""
        result = process_url("https://example.com", {"test": "url"})

        assert result['status'] in ['success', 'no_content']
        assert 'text' in result
        assert 'page_info' in result
        assert 'metadata' in result
        assert result['metadata']['domain'] == 'example.com'
        assert result['metadata']['test'] == 'url'

    def test_process_url_invalid(self):
        """Test processing invalid URL."""
        with pytest.raises(URLProcessingError):
            process_url("not-a-url", {})

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_process_url_async(self):
        """Test async URL processing."""
        result = await process_url_async("https://example.com", {"async": True})

        assert result['status'] in ['success', 'no_content']
        assert result['metadata']['async'] is True


class TestPDFProcessor:
    """Tests for PDF processor module (requires sample PDF)."""

    @pytest.fixture
    def sample_text_content(self):
        """Sample text for creating test PDFs."""
        return "This is a test PDF document.\n\nIt has multiple paragraphs.\n\nPage content here."

    def test_pdf_processing_error_nonexistent(self):
        """Test error handling for non-existent PDF."""
        with pytest.raises(PDFProcessingError):
            process_pdf("/nonexistent/file.pdf", {})

    def test_pdf_processing_error_wrong_extension(self):
        """Test error handling for non-PDF file."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"Not a PDF")
            temp_path = f.name

        try:
            with pytest.raises(PDFProcessingError):
                process_pdf(temp_path, {})
        finally:
            Path(temp_path).unlink()

    # Note: Full PDF tests would require creating actual PDF files
    # or having sample PDFs available. Skipping for now.


class TestIntegration:
    """Integration tests for all processors."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_processing(self):
        """Test processing multiple documents concurrently."""
        # Create test HTML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(SAMPLE_HTML)
            html_path = f.name

        try:
            # Process HTML and URL concurrently
            results = await asyncio.gather(
                process_html_async(html_path, {"id": 1}),
                process_url_async("https://example.com", {"id": 2})
            )

            assert len(results) == 2
            assert results[0]['metadata']['id'] == 1
            assert results[1]['metadata']['id'] == 2

        finally:
            Path(html_path).unlink()

    def test_result_structure_consistency(self):
        """Test that all processors return consistent structure."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(SAMPLE_HTML)
            html_path = f.name

        try:
            result = process_html(html_path, {})

            # Check required keys
            required_keys = {'text', 'page_info', 'status', 'metadata'}
            assert required_keys.issubset(result.keys())

            # Check page_info structure
            assert isinstance(result['page_info'], list)
            assert len(result['page_info']) > 0

            page = result['page_info'][0]
            page_keys = {'page_number', 'text', 'char_count', 'is_ocr'}
            assert page_keys.issubset(page.keys())

        finally:
            Path(html_path).unlink()


def run_manual_tests():
    """Run manual tests without pytest."""
    print("=" * 70)
    print("Manual Test Suite for Document Processors")
    print("=" * 70)

    # Test HTML processing
    print("\n1. Testing HTML Processing...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write(SAMPLE_HTML)
        temp_path = f.name

    try:
        result = process_html(temp_path, {"test": "manual"})
        print(f"   Status: {result['status']}")
        print(f"   Characters: {result['metadata']['total_chars']}")
        print(f"   Sample text: {result['text'][:100]}...")
        print("   ✓ HTML processing passed")
    except Exception as e:
        print(f"   ✗ HTML processing failed: {e}")
    finally:
        Path(temp_path).unlink()

    # Test URL processing (may fail without internet)
    print("\n2. Testing URL Processing...")
    try:
        result = process_url("https://example.com", {"test": "manual"})
        print(f"   Status: {result['status']}")
        print(f"   Characters: {result['metadata']['total_chars']}")
        print(f"   Domain: {result['metadata']['domain']}")
        print("   ✓ URL processing passed")
    except Exception as e:
        print(f"   ✗ URL processing failed: {e}")

    # Test HTML content extraction
    print("\n3. Testing HTML Content Extraction...")
    try:
        content = extract_main_content(SAMPLE_HTML)
        assert "Main Article Title" in content
        assert len(content) > 0
        print(f"   Extracted {len(content)} characters")
        print("   ✓ Content extraction passed")
    except Exception as e:
        print(f"   ✗ Content extraction failed: {e}")

    # Test HTML cleaning
    print("\n4. Testing HTML Artifact Cleaning...")
    try:
        dirty = "Text with &nbsp; and &#8212; entities"
        clean = clean_html_artifacts(dirty)
        assert "&nbsp;" not in clean
        print(f"   Before: {dirty}")
        print(f"   After: {clean}")
        print("   ✓ Artifact cleaning passed")
    except Exception as e:
        print(f"   ✗ Artifact cleaning failed: {e}")

    print("\n" + "=" * 70)
    print("Manual tests completed!")
    print("=" * 70)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--manual":
        run_manual_tests()
    else:
        # Try to run with pytest
        try:
            pytest.main([__file__, "-v", "-m", "not integration"])
        except SystemExit:
            pass
        except Exception:
            print("\nPytest not available. Running manual tests...\n")
            run_manual_tests()
