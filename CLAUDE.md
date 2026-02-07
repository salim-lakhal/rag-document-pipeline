# CLAUDE.md - OQTF RAG Pipeline

## Project Overview

OQTF is a **Retrieval-Augmented Generation (RAG) pipeline** for processing foreign student administrative documents in France. The system extracts, cleans, chunks, and prepares documents for future vector database ingestion and LLM-powered Q&A.

**Domain**: Immigration law, visa procedures, residence permits (titre de séjour), social aid, and administrative procedures for foreign students in France.

**Language**: Primarily French (fr), with English support.

---

## Quick Start

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Process all pending documents
python scripts/pipeline_orchestrator.py

# Process a specific document
python scripts/pipeline_orchestrator.py --document-id <document_id>

# Run tests
python processors/test_processors.py
```

---

## Architecture

```
OQTF/
├── scripts/
│   └── pipeline_orchestrator.py     # Main entry point
├── processors/
│   ├── pdf_processor.py             # PDF extraction (pdfplumber + OCR fallback)
│   ├── html_processor.py            # HTML content extraction (BeautifulSoup)
│   ├── url_processor.py             # URL fetching (trafilatura + readability)
│   └── url_processor_with_cache.py  # URL processor with HTML caching to Drive
├── utils/
│   ├── text_cleaning.py             # Boilerplate removal, whitespace normalization
│   ├── chunking.py                  # 500-word chunks with 50-word overlap
│   ├── jsonl_writer.py              # JSONL output generation
│   ├── metadata_manager.py          # Document metadata CRUD
│   └── gdrive_client.py             # Google Drive API wrapper
└── data/
    ├── meta/metadata.json           # Document registry with status tracking
    └── jsonl/                        # Per-document JSONL chunks
```

---

## Pipeline Workflow

```
1. metadata.json → 2. Document Fetch → 3. Text Extraction → 4. Cleaning
       ↓                   ↓                   ↓                ↓
  Get pending         GDrive/URL         PDF/HTML/URL        Remove boilerplate
  documents           download           processors          Normalize text
       ↓                                                         ↓
5. Chunking → 6. Metadata Attachment → 7. JSONL Write → 8. Status Update
       ↓                   ↓                   ↓                ↓
  500 words           Inherit all          One file per     jsonl_ready=true
  50 overlap          doc metadata         document
```

---

## Key Design Decisions

### Chunking Strategy
- **Chunk size**: 500 words (configurable)
- **Overlap**: 50 words between consecutive chunks
- **Rationale**: Preserves context across boundaries for better RAG retrieval

### Metadata Schema
Each document in `metadata.json` includes:
```json
{
  "document_id": "unique_identifier",
  "document_type": "pdf|html|url",
  "drive_link": "Google Drive share link",
  "source_url": "Original source URL",
  "category": "titre_sejour|visa|aide_sociale|...",
  "sub_category": "optional subcategory",
  "jurisdiction": "Hauts-de-Seine|Paris|National|...",
  "date": "YYYY-MM-DD",
  "authority_score": 1-5,  // 5 = official govt, 1 = unverified
  "language": "fr|en",
  "jsonl_ready": false,
  "embedding_done": false
}
```

### JSONL Chunk Format
Each chunk inherits document metadata plus:
```json
{
  "chunk_id": "document_id_001",
  "text": "Chunk content...",
  "page_start": 1,
  "page_end": 2,
  "chunk_size": 485,
  "overlap_prev": 50
}
```

---

## Development Guidelines

### Code Style
- Python 3.10+ with type hints
- Docstrings for all functions (Args, Returns, Raises)
- Logging at INFO level for operations, DEBUG for details
- Exception classes per module (e.g., `PDFProcessingError`)

### Adding a New Processor
1. Create `processors/new_processor.py`
2. Implement `process_<type>(file_path, document_metadata) -> dict`
3. Return dict with: `text`, `page_info`, `status`, `metadata`
4. Add document_type handling in `pipeline_orchestrator.py`

### Adding a New Utility
1. Create in `utils/` with clear module docstring
2. Export from `utils/__init__.py`
3. Include `if __name__ == "__main__":` for standalone testing

### Testing
```bash
# Test individual modules
python utils/text_cleaning.py
python utils/chunking.py
python processors/pdf_processor.py /path/to/test.pdf

# Full pipeline test (see TESTING.md for details)
python scripts/pipeline_orchestrator.py --document-id test_doc --log-level DEBUG
```

---

## Environment Variables

Required in `.env`:
```env
GOOGLE_DRIVE_CLIENT_ID=your_client_id
GOOGLE_DRIVE_CLIENT_SECRET=your_client_secret
GOOGLE_DRIVE_REFRESH_TOKEN=your_refresh_token

# Optional
METADATA_FILE=data/meta/metadata.json
CHUNK_SIZE=500
CHUNK_OVERLAP=50
LOG_LEVEL=INFO
```

---

## Common Tasks

### Add a new document
1. Upload to Google Drive (pdfs/ or html/ folder)
2. Add entry to `data/meta/metadata.json`
3. Run `python scripts/pipeline_orchestrator.py`

### Reprocess a document
1. Set `jsonl_ready: false` in metadata.json
2. Run pipeline with `--document-id <id>`

### Debug extraction issues
```bash
# Test PDF extraction directly
python processors/pdf_processor.py /path/to/document.pdf

# Test HTML extraction
python processors/html_processor.py /path/to/page.html

# Test URL extraction
python processors/url_processor.py https://example.com/page
```

### Validate JSONL output
```bash
# Check JSON validity
cat data/jsonl/document_id.jsonl | python -m json.tool > /dev/null && echo "Valid"

# Count chunks
wc -l data/jsonl/document_id.jsonl
```

---

## Dependencies

### Core
- `pdfplumber`, `PyMuPDF` - PDF extraction
- `beautifulsoup4`, `lxml` - HTML parsing
- `trafilatura`, `readability-lxml` - Web content extraction
- `langdetect` - Language detection
- `google-api-python-client` - Google Drive integration

### OCR (optional)
- `pytesseract`, `pdf2image` - OCR for scanned PDFs
- System: `tesseract-ocr`, `tesseract-ocr-fra` packages

---

## File Naming Conventions

- **document_id**: `<source>_<topic><year>` (e.g., `pref92_visa2025`)
- **JSONL files**: `data/jsonl/<document_id>.jsonl`
- **Logs**: `logs/pipeline_YYYYMMDD_HHMMSS.log`

---

## Current Status

See `PROGRESSION.md` for:
- Completed features
- Current sprint tasks
- Known issues
- Roadmap

---

## Commit & Progression Guidelines

### After Each Task Completion
1. **Update PROGRESSION.md** - Mark task complete, add notes
2. **Create a Git commit** - Simple, descriptive message
3. **No Claude references** - Never include "Co-authored-by: Claude" or any AI attribution

### Commit Message Format
```
Add PDF extraction script with basic text cleaning
Implement HTML processor with section-aware chunking
Fix metadata validation for empty authority_score
Update chunking to handle French date formats
```

### Rules
- One commit per logical change
- Imperative mood ("Add", "Fix", "Update", not "Added", "Fixed")
- Keep under 72 characters
- No co-author tags or AI mentions
- Human-friendly and readable

### Example Workflow
```bash
# After completing a task:
# 1. Update PROGRESSION.md
# 2. Stage changes
git add .
# 3. Commit with simple message
git commit -m "Add URL processor with HTML caching to Google Drive"
```

---

## Future Enhancements (Roadmap)

1. **Embedding Generation** - Vector embeddings per chunk
2. **Vector DB Integration** - Pinecone/Weaviate ingestion
3. **Hybrid Search** - Dense + BM25 retrieval
4. **Web Scraping** - Automatic prefecture website monitoring
5. **API Development** - FastAPI for RAG queries
6. **Multi-language** - Full English support with translation

---

## Contact & Support

For issues:
1. Check logs in `logs/` directory
2. Review `TESTING.md` for troubleshooting
3. Verify Google Drive credentials
4. Test individual processors in isolation
