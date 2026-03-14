import tempfile
from pathlib import Path

import pytest

from processors.html_processor import (
    HTMLProcessingError,
    clean_html_artifacts,
    extract_main_content,
    extract_metadata_from_html,
    process_html,
)
from processors.pdf_processor import PDFProcessingError, process_pdf
from processors.url_processor import URLProcessingError, process_url

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Article</title>
    <meta name="description" content="A test article">
    <meta name="author" content="Test Author">
    <style>body { font-family: Arial; }</style>
    <script>console.log('removed');</script>
</head>
<body>
    <nav><a href="/">Home</a></nav>
    <main>
        <article>
            <h1>Main Article Title</h1>
            <p>This is the first paragraph of the article.</p>
            <p>This is the second paragraph with more content.</p>
        </article>
    </main>
    <footer><p>Copyright 2024</p></footer>
    <div class="advertisement"><p>Ad content</p></div>
</body>
</html>
"""


class TestHTMLProcessor:
    def test_extracts_main_content(self):
        content = extract_main_content(SAMPLE_HTML)
        assert "Main Article Title" in content
        assert "first paragraph" in content

    def test_removes_scripts_and_styles(self):
        content = extract_main_content(SAMPLE_HTML)
        assert "console.log" not in content
        assert "font-family" not in content

    def test_cleans_html_entities(self):
        dirty = "Text with &nbsp; entities &#8212; and <b>tags</b>"
        cleaned = clean_html_artifacts(dirty)
        assert "&nbsp;" not in cleaned
        assert "<b>" not in cleaned
        assert "tags" in cleaned

    def test_extracts_metadata(self):
        meta = extract_metadata_from_html(SAMPLE_HTML)
        assert meta["title"] == "Test Article"
        assert meta["author"] == "Test Author"

    def test_processes_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(SAMPLE_HTML)
            path = f.name
        try:
            result = process_html(path, {"source": "test"})
            assert result["status"] == "success"
            assert "Main Article Title" in result["text"]
            assert result["metadata"]["source"] == "test"
        finally:
            Path(path).unlink()

    def test_missing_file_raises(self):
        with pytest.raises(HTMLProcessingError):
            process_html("/nonexistent.html", {})


class TestPDFProcessor:
    def test_missing_file_raises(self):
        with pytest.raises(PDFProcessingError):
            process_pdf("/nonexistent.pdf", {})

    def test_wrong_extension_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"Not a PDF")
            path = f.name
        try:
            with pytest.raises(PDFProcessingError):
                process_pdf(path, {})
        finally:
            Path(path).unlink()


class TestURLProcessor:
    def test_invalid_url_raises(self):
        with pytest.raises(URLProcessingError):
            process_url("not-a-url", {})

    def test_unsupported_scheme_raises(self):
        with pytest.raises(URLProcessingError):
            process_url("ftp://example.com", {})

    def test_result_structure(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(SAMPLE_HTML)
            path = f.name
        try:
            result = process_html(path, {})
            assert {"text", "page_info", "status", "metadata"}.issubset(result.keys())
            assert isinstance(result["page_info"], list)
            page = result["page_info"][0]
            assert {"page_number", "text", "char_count", "is_ocr"}.issubset(page.keys())
        finally:
            Path(path).unlink()
