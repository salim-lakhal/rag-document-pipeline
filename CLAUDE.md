# rag-document-pipeline

RAG preprocessing pipeline: extracts text from PDFs, HTML, and URLs → cleans → chunks with overlap → writes JSONL with metadata.

## Quick start
```bash
source venv/bin/activate
pip install -e ".[dev]"
pytest -v
python scripts/pipeline_orchestrator.py --document-id pref92_visa2025
```

## Structure
- `processors/` — PDF (pdfplumber+OCR), HTML (BeautifulSoup), URL (trafilatura+readability)
- `utils/` — text_cleaning, chunking, jsonl_writer, metadata_manager, gdrive_client
- `scripts/` — pipeline_orchestrator (CLI entry point)
- `tests/` — pytest suite for all utils and processors

## Key parameters
- Chunk size: 500 words, overlap: 50 words
- OCR threshold: <50 chars triggers pytesseract fallback
- URL extraction: trafilatura → readability → BeautifulSoup cascade

## Commit style
- No AI attribution, no co-author tags
- Imperative mood, under 72 chars
- e.g. "fix chunking boundary detection", "add metadata validation tests"
