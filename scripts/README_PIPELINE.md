# Pipeline Orchestrator - User Guide

## Overview

The `pipeline_orchestrator.py` is the main entry point for processing documents in the RAG pipeline. It orchestrates the entire workflow from raw documents (PDF, HTML, URL) to processed JSONL chunks ready for embedding.

## Architecture

### Pipeline Flow

```
metadata.json (pending documents)
         ↓
    Orchestrator
         ↓
    ┌────┴────┬────────┬──────┐
    ↓         ↓        ↓      ↓
  PDF     HTML      URL   Detect Type
  ↓         ↓        ↓
Download  Download  Fetch
  ↓         ↓        ↓
  └─────┬───┴────────┘
        ↓
   Extract Text
        ↓
   Clean Text
        ↓
   Chunk with Overlap
        ↓
   Attach Metadata
        ↓
   Write JSONL
        ↓
   Update metadata.json
   (jsonl_ready=True)
```

### Components

1. **PipelineOrchestrator**: Main orchestration class
2. **MetadataManager**: Handles metadata.json operations
3. **Processors**: Document-specific extraction (PDF, HTML, URL)
4. **Utilities**: Text cleaning, chunking, JSONL writing, Drive client
5. **Logging**: Comprehensive logging to file and console

## Installation & Setup

### Prerequisites

```bash
# Python 3.10+
python --version

# Required packages (add to requirements.txt)
pip install pdfplumber PyMuPDF beautifulsoup4 requests google-api-python-client
```

### Directory Structure

```
/home/salim/Informatique/Perso/OQTF/
├── metadata.json              # Main metadata file
├── scripts/
│   └── pipeline_orchestrator.py
├── processors/
│   ├── pdf_processor.py
│   ├── html_processor.py
│   └── url_processor.py
├── utils/
│   ├── metadata_manager.py
│   ├── text_cleaning.py
│   ├── chunking.py
│   ├── jsonl_writer.py
│   └── gdrive_client.py
├── data/
│   └── jsonl/                 # Output JSONL files
├── logs/                      # Pipeline logs
└── .env                       # Google Drive credentials
```

## Usage

### 1. Process All Pending Documents

Process all documents with `jsonl_ready=False`:

```bash
cd /home/salim/Informatique/Perso/OQTF/scripts
python pipeline_orchestrator.py
```

### 2. Process Specific Document

Process a single document by ID:

```bash
python pipeline_orchestrator.py --document-id pref92_visa2025
```

### 3. Custom Paths

Override default paths:

```bash
python pipeline_orchestrator.py \
  --metadata-path /custom/path/metadata.json \
  --output-dir /custom/path/jsonl \
  --downloads-dir /tmp/my_downloads
```

### 4. Debug Mode

Enable verbose logging:

```bash
python pipeline_orchestrator.py --log-level DEBUG
```

### 5. Custom Log File

Specify log file location:

```bash
python pipeline_orchestrator.py --log-file /path/to/custom.log
```

## Command-Line Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--document-id` | string | None | Process specific document by ID |
| `--metadata-path` | string | `./metadata.json` | Path to metadata file |
| `--output-dir` | string | `./data/jsonl` | JSONL output directory |
| `--downloads-dir` | string | `/tmp/oqtf_downloads` | Temporary downloads |
| `--log-level` | choice | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL) |
| `--log-file` | string | Auto-generated | Custom log file path |

## Metadata Format

### Input Metadata (metadata.json)

Each document requires the following fields:

```json
{
  "document_id": "pref92_visa2025",
  "document_type": "pdf",
  "drive_link": "https://drive.google.com/file/d/...",
  "source_url": "https://prefecture92.gouv.fr/visa-renewal",
  "category": "titre_sejour",
  "sub_category": "delai_renouvellement",
  "jurisdiction": "Hauts-de-Seine",
  "date": "2025-01-10",
  "authority_score": 3,
  "language": "fr",
  "jsonl_ready": false,
  "embedding_done": false
}
```

### Field Descriptions

- **document_id**: Unique identifier (required)
- **document_type**: Type of document - `pdf`, `html`, or `url` (required)
- **drive_link**: Google Drive link for PDF/HTML (required for pdf/html)
- **source_url**: Original source URL (required for url type)
- **category**: Main category (e.g., titre_sejour, integration)
- **sub_category**: Subcategory for finer filtering
- **jurisdiction**: Geographic jurisdiction (e.g., Hauts-de-Seine, National)
- **date**: Document date (YYYY-MM-DD format)
- **authority_score**: Reliability score 1-5 (higher = more authoritative)
- **language**: Document language (ISO 639-1 code, e.g., fr, en)
- **jsonl_ready**: Processing status (auto-updated)
- **embedding_done**: Embedding status (for future use)

### Updated Metadata (After Processing)

After successful processing, the orchestrator adds:

```json
{
  "jsonl_ready": true,
  "embedding_done": false,
  "jsonl_path": "/path/to/output.jsonl",
  "processed_at": "2025-12-12T10:30:45.123456"
}
```

If processing fails:

```json
{
  "jsonl_ready": false,
  "error": "Error message here",
  "failed_at": "2025-12-12T10:30:45.123456"
}
```

## Output Format

### JSONL Structure

Each chunk is written as one line in `data/jsonl/<document_id>.jsonl`:

```json
{
  "chunk_id": "pref92_visa2025_001",
  "text": "Le renouvellement du titre de séjour...",
  "document_id": "pref92_visa2025",
  "category": "titre_sejour",
  "sub_category": "delai_renouvellement",
  "jurisdiction": "Hauts-de-Seine",
  "source_url": "https://prefecture92.gouv.fr/visa-renewal",
  "drive_link": "https://drive.google.com/...",
  "language": "fr",
  "authority_score": 3,
  "date": "2025-01-10",
  "page_start": 1,
  "page_end": 2,
  "chunk_size": 485,
  "overlap_prev": 50
}
```

### Chunking Parameters

- **chunk_size**: ~500 words per chunk (configurable)
- **overlap_size**: ~50 words overlap between consecutive chunks
- **overlap_prev**: Number of overlapping words from previous chunk

## Logging

### Log Locations

- **Default**: `logs/pipeline_YYYYMMDD_HHMMSS.log`
- **Console**: Real-time output to stdout
- **Custom**: Use `--log-file` argument

### Log Levels

- **DEBUG**: Detailed debugging information
- **INFO**: General pipeline progress (default)
- **WARNING**: Non-critical issues (e.g., skipped documents)
- **ERROR**: Processing failures
- **CRITICAL**: System-level failures

### Example Log Output

```
2025-12-12 10:30:45 - pipeline_orchestrator - INFO - Starting processing for document: pref92_visa2025
2025-12-12 10:30:46 - pipeline_orchestrator - INFO - Document type: pdf
2025-12-12 10:30:46 - pipeline_orchestrator - INFO - Downloading pref92_visa2025 from Google Drive...
2025-12-12 10:30:50 - pipeline_orchestrator - INFO - Successfully downloaded to /tmp/oqtf_downloads/pref92_visa2025.pdf
2025-12-12 10:30:51 - pipeline_orchestrator - INFO - Processing pref92_visa2025 as pdf type...
2025-12-12 10:30:53 - pipeline_orchestrator - INFO - Extracted 15420 characters from pref92_visa2025
2025-12-12 10:30:53 - pipeline_orchestrator - INFO - Cleaning text for pref92_visa2025...
2025-12-12 10:30:54 - pipeline_orchestrator - INFO - Text cleaned: 15420 -> 14850 characters
2025-12-12 10:30:54 - pipeline_orchestrator - INFO - Chunking text for pref92_visa2025...
2025-12-12 10:30:54 - pipeline_orchestrator - INFO - Created 32 chunks for pref92_visa2025
2025-12-12 10:30:54 - pipeline_orchestrator - INFO - Attached metadata to all 32 chunks
2025-12-12 10:30:54 - pipeline_orchestrator - INFO - Writing 32 chunks to data/jsonl/pref92_visa2025.jsonl...
2025-12-12 10:30:55 - pipeline_orchestrator - INFO - Successfully processed document: pref92_visa2025
```

## Error Handling

### Common Errors

#### 1. Missing Metadata

```
ValueError: No metadata found for document: unknown_doc
```

**Solution**: Ensure document_id exists in metadata.json

#### 2. Invalid Document Type

```
ValueError: Invalid or missing document_type: txt
```

**Solution**: Use only `pdf`, `html`, or `url` as document_type

#### 3. Missing Drive Link

```
ValueError: Document pref92_visa2025 requires drive_link for type pdf
```

**Solution**: Add drive_link to metadata for PDF/HTML documents

#### 4. Download Failure

```
FileNotFoundError: Downloaded file not found: /tmp/oqtf_downloads/doc.pdf
```

**Solution**: Check Google Drive credentials and link permissions

#### 5. No Text Extracted

```
ValueError: No text extracted from pref92_visa2025
```

**Solution**: Verify document is not corrupted or image-only (may need OCR)

### Recovery Strategies

1. **Single Document Failure**: Process other documents continue
2. **Metadata Updates**: Failed documents marked with error message
3. **Temporary Files**: Automatically cleaned up after processing
4. **Retry**: Simply re-run the pipeline for failed documents

## Performance Optimization

### Batch Processing

Process all pending documents efficiently:

```bash
# Process all pending documents
python pipeline_orchestrator.py
```

### Parallel Processing (Future Enhancement)

For large-scale processing, consider:
- Process multiple documents in parallel using multiprocessing
- Use async I/O for Google Drive downloads
- Implement chunked processing for very large documents

### Resource Management

- **Memory**: Large PDFs are processed in streaming mode
- **Disk**: Temporary files cleaned up immediately after processing
- **Network**: Downloads are cached temporarily to avoid re-downloading

## Integration with Other Components

### Required Utilities

Ensure these modules are implemented:

1. **utils/metadata_manager.py**: Metadata operations
   - `get_document_metadata(document_id)`
   - `get_pending_documents()`
   - `update_document_status(document_id, **kwargs)`

2. **utils/text_cleaning.py**: Text preprocessing
   - `clean_text(text, logger)`

3. **utils/chunking.py**: Text chunking
   - `chunk_text_with_overlap(text, chunk_size, overlap_size, logger)`

4. **utils/jsonl_writer.py**: JSONL file writing
   - `write_jsonl(chunks, output_path, logger)`

5. **utils/gdrive_client.py**: Google Drive integration
   - `download_from_drive(drive_link, output_path, logger)`

### Required Processors

1. **processors/pdf_processor.py**: PDF extraction
   - `process_pdf(file_path, logger) -> str`

2. **processors/html_processor.py**: HTML extraction
   - `process_html(file_path, logger) -> str`

3. **processors/url_processor.py**: URL fetching and extraction
   - `process_url(url, logger) -> str`

## Testing

### Test Single Document

```bash
# Test with a known good document
python pipeline_orchestrator.py --document-id test_doc --log-level DEBUG
```

### Validate Output

```bash
# Check JSONL format
cd /home/salim/Informatique/Perso/OQTF/data/jsonl
cat pref92_visa2025.jsonl | jq .

# Count chunks
wc -l pref92_visa2025.jsonl

# Validate JSON structure
cat pref92_visa2025.jsonl | jq -e . >/dev/null && echo "Valid JSONL"
```

### Verify Metadata Updates

```bash
# Check metadata was updated
cat /home/salim/Informatique/Perso/OQTF/metadata.json | jq '.[] | select(.document_id=="pref92_visa2025")'
```

## Troubleshooting

### Enable Debug Logging

```bash
python pipeline_orchestrator.py --log-level DEBUG --document-id problematic_doc
```

### Check Metadata Status

```python
import json

with open('metadata.json') as f:
    metadata = json.load(f)

# Find pending documents
pending = [doc for doc in metadata if not doc.get('jsonl_ready', False)]
print(f"Pending: {len(pending)}")

# Find failed documents
failed = [doc for doc in metadata if 'error' in doc]
print(f"Failed: {len(failed)}")
```

### Manual Metadata Reset

To reprocess a document, set `jsonl_ready` to `false`:

```python
import json

with open('metadata.json', 'r+') as f:
    metadata = json.load(f)
    for doc in metadata:
        if doc['document_id'] == 'pref92_visa2025':
            doc['jsonl_ready'] = False
            doc.pop('error', None)
            doc.pop('failed_at', None)
    f.seek(0)
    json.dump(metadata, f, indent=2)
    f.truncate()
```

## Best Practices

1. **Version Control**: Track metadata.json changes
2. **Backups**: Backup metadata.json before batch processing
3. **Incremental**: Process documents incrementally as they're added
4. **Validation**: Validate JSONL output after processing
5. **Monitoring**: Review logs regularly for errors
6. **Testing**: Test with small documents before batch processing
7. **Documentation**: Keep metadata fields consistent and well-documented

## Future Enhancements

- Parallel document processing with multiprocessing
- Real-time progress tracking with progress bars
- Webhook notifications on completion/failure
- Automatic retry mechanism for failed downloads
- S3/GCS storage integration as alternative to Google Drive
- Incremental processing for updated documents
- Document deduplication and versioning
- Advanced chunking strategies (semantic chunking, sliding window)
- OCR integration for scanned PDFs
- Multi-language text detection and handling

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Verify all utility modules are implemented
3. Test with `--log-level DEBUG`
4. Review metadata.json structure
5. Ensure Google Drive credentials are valid

---

**Last Updated**: 2025-12-12
**Version**: 1.0.0
**Author**: Data Engineering Pipeline
