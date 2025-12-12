# RAG Pipeline for Foreign Student Documents

A comprehensive Retrieval-Augmented Generation (RAG) pipeline for processing foreign student documents including legal, visa, immigration, and aid documentation. This system automates document collection, chunking, metadata management, and JSONL generation with Google Drive integration.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Folder Structure](#folder-structure)
- [Metadata Format](#metadata-format)
- [Pipeline Workflow](#pipeline-workflow)
- [Troubleshooting](#troubleshooting)
- [Future Enhancements](#future-enhancements)
- [Contributing](#contributing)

---

## Overview

This project builds a RAG pipeline focused on per-document processing for foreign student administrative documents. Key features include:

- **Google Drive Integration**: Raw documents stored on Google Drive for centralized access
- **Per-Document Processing**: Each document generates individual JSONL chunks with rich metadata
- **Multi-Format Support**: PDF, HTML, and URL processing capabilities
- **Metadata-Rich Chunks**: Each chunk includes document metadata for enhanced retrieval
- **Status Tracking**: Monitor processing status (`jsonl_ready`, `embedding_done`)
- **Incremental Processing**: Process documents individually or in batch

### Project Goals

1. Maintain clean folder architecture for raw documents, JSONL chunks, and metadata
2. Automate pipeline from document collection through chunking to JSONL creation
3. Enable per-document processing via metadata JSON management
4. Prepare data for future embedding generation and vector database ingestion

---

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Google Drive Storage                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  DB/                                                       │  │
│  │  ├── pdfs/          (Raw PDF files)                       │  │
│  │  ├── html/          (Raw HTML files)                      │  │
│  │  ├── jsonl/         (Per-document JSONL chunks)           │  │
│  │  └── meta/          (Metadata JSON/CSV)                   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RAG Pipeline Orchestrator                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  1. Read metadata.json                                    │  │
│  │  2. Fetch document from Google Drive                      │  │
│  │  3. Process based on document_type (PDF/HTML/URL)         │  │
│  │  4. Extract & clean text                                  │  │
│  │  5. Chunk with overlap (500 words, 50 word overlap)       │  │
│  │  6. Attach metadata to each chunk                         │  │
│  │  7. Generate JSONL file                                   │  │
│  │  8. Update status: jsonl_ready = True                     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Local Data Storage                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  data/                                                     │  │
│  │  ├── meta/          (Local metadata cache)                │  │
│  │  └── jsonl/         (Local JSONL output)                  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Processing Pipeline Flow

```
Document Input → Document Type Detection → Processor Selection
                                                 │
                      ┌──────────────────────────┼──────────────────────────┐
                      │                          │                          │
                  [PDF Processor]           [HTML Processor]           [URL Processor]
                      │                          │                          │
                      └──────────────────────────┼──────────────────────────┘
                                                 │
                                          Text Extraction
                                                 │
                                          Text Cleaning
                                        - Remove boilerplate
                                        - Normalize whitespace
                                        - Handle special chars
                                        - OCR if needed
                                                 │
                                         Smart Chunking
                                        - 500 words per chunk
                                        - 50 word overlap
                                        - Logical boundaries
                                        - Preserve context
                                                 │
                                      Metadata Attachment
                                        - Document metadata
                                        - Chunk-specific fields
                                        - Page references
                                                 │
                                        JSONL Generation
                                        - One line per chunk
                                        - Rich metadata
                                        - Traceability info
                                                 │
                                         Status Update
                                      jsonl_ready = True
```

## Architecture Schema
<img width="2816" height="1536" alt="Architecture Schema" src="https://github.com/user-attachments/assets/63d7bb09-0e65-4e52-8668-3ba2d8342abf" />

---

## Prerequisites

Before installing and running the RAG pipeline, ensure you have:

### System Requirements

- **Python 3.10+** (Python 3.12+ recommended)
- **pip** package manager
- **Git** for repository cloning
- Minimum 2GB RAM (4GB+ recommended for large documents)
- Internet connection for Google Drive API access

### Required Accounts & Credentials

- **Google Cloud Project** with Drive API enabled
- **Google Drive API credentials** (OAuth 2.0)
  - Client ID
  - Client Secret
  - Refresh Token

### Python Dependencies

Core libraries (will be installed via `requirements.txt`):
- `google-auth` - Google authentication
- `google-auth-oauthlib` - OAuth flow
- `google-api-python-client` - Drive API client
- `pdfplumber` or `PyMuPDF` - PDF processing
- `beautifulsoup4` - HTML parsing
- `requests` - HTTP requests
- `python-dotenv` - Environment variable management
- `langdetect` - Language detection

Optional dependencies:
- `pytesseract` + `pdf2image` - OCR for scanned PDFs
- `Pillow` - Image processing

---

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/OQTF.git
cd OQTF
```

### 2. Create Virtual Environment (Recommended)

```bash
# Using venv
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Or using uv (modern alternative)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt

# Or using uv (faster)
uv pip install -r requirements.txt
```

### 4. Verify Installation

```bash
python --version  # Should be 3.10+
python -c "import google.auth; print('Google Auth installed successfully')"
```

---

## Configuration

### 1. Environment Variables Setup

Create a `.env` file in the project root:

```bash
cp .env.example .env  # If example exists, or create new file
```

Edit `.env` with your credentials:

```env
# Google Drive API Configuration
GOOGLE_DRIVE_CLIENT_ID=your_client_id_here.apps.googleusercontent.com
GOOGLE_DRIVE_CLIENT_SECRET=your_client_secret_here
GOOGLE_DRIVE_REFRESH_TOKEN=your_refresh_token_here

# Pipeline Configuration
CHUNK_SIZE=500              # Words per chunk
CHUNK_OVERLAP=50            # Words overlap between chunks
GDRIVE_BASE_FOLDER=DB       # Base folder name in Google Drive

# Processing Options
ENABLE_OCR=false            # Enable OCR for scanned PDFs
DEFAULT_LANGUAGE=fr         # Default language (fr, en, etc.)
LOG_LEVEL=INFO              # Logging level (DEBUG, INFO, WARNING, ERROR)
```

### 2. Google Drive API Credentials Setup

#### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable **Google Drive API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click "Enable"

#### Step 2: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Select "Desktop app" as application type
4. Download credentials JSON file
5. Save as `credentials.json` in project root

#### Step 3: Generate Refresh Token

Run the authentication script (first time only):

```bash
python scripts/setup_gdrive_auth.py
```

This will:
- Open browser for Google authentication
- Request Drive access permissions
- Generate and save refresh token to `.env`

**Security Note**: Never commit `.env` or `credentials.json` to version control!

### 3. Google Drive Folder Structure

Create the following folder structure in your Google Drive:

```
Google Drive/
└── DB/
    ├── pdfs/          # Upload your PDF documents here
    ├── html/          # Upload HTML files here
    ├── jsonl/         # Generated JSONL chunks (auto-created)
    └── meta/          # Metadata files (auto-created)
```

Get the folder IDs:
1. Open each folder in Google Drive
2. Copy the ID from URL: `https://drive.google.com/drive/folders/[FOLDER_ID]`
3. Add to `.env` (optional, for direct access):

```env
GDRIVE_PDF_FOLDER_ID=your_pdf_folder_id
GDRIVE_HTML_FOLDER_ID=your_html_folder_id
GDRIVE_JSONL_FOLDER_ID=your_jsonl_folder_id
GDRIVE_META_FOLDER_ID=your_meta_folder_id
```

---

## Usage

### Adding Documents to Pipeline

#### 1. Create/Update Metadata File

Edit `data/meta/metadata.json` to add document entries:

```json
{
  "document_id": "pref92_visa2025",
  "document_type": "pdf",
  "drive_link": "https://drive.google.com/file/d/1ABC...XYZ/view",
  "source_url": "https://prefecture92.gouv.fr/visa-renewal",
  "category": "titre_sejour",
  "sub_category": "delai_renouvellement",
  "jurisdiction": "Hauts-de-Seine",
  "date": "2025-01-10",
  "authority_score": 3,
  "language": "fr"
}
```

Add one JSON object per line (JSONL format) or use a single JSON array.

#### 2. Run Full Pipeline

Process all documents with `jsonl_ready = false`:

```bash
python scripts/pipeline_orchestrator.py
```

**Expected Output:**
```
[INFO] Loading metadata from data/meta/metadata.json
[INFO] Found 5 documents to process
[INFO] Processing document: pref92_visa2025
[INFO] ├── Fetching from Google Drive
[INFO] ├── Extracting text (PDF)
[INFO] ├── Cleaning text
[INFO] ├── Chunking (500 words, 50 overlap)
[INFO] ├── Generated 12 chunks
[INFO] ├── Writing JSONL to data/jsonl/pref92_visa2025.jsonl
[INFO] └── Status updated: jsonl_ready = true
[INFO] ✓ Successfully processed 5/5 documents
```

#### 3. Process Single Document

Process a specific document by ID:

```bash
python scripts/pipeline_orchestrator.py --document-id pref92_visa2025
```

**Use Cases:**
- Reprocess updated document
- Test new document before batch processing
- Debug specific document issues

#### 4. Process by Category

Process documents by category or jurisdiction:

```bash
# Process all titre_sejour documents
python scripts/pipeline_orchestrator.py --category titre_sejour

# Process documents for specific jurisdiction
python scripts/pipeline_orchestrator.py --jurisdiction "Hauts-de-Seine"
```

### Advanced Usage

#### Dry Run Mode

Preview what would be processed without executing:

```bash
python scripts/pipeline_orchestrator.py --dry-run
```

#### Force Reprocessing

Reprocess documents even if already marked as `jsonl_ready`:

```bash
python scripts/pipeline_orchestrator.py --force
```

#### Custom Configuration

Override default chunk size and overlap:

```bash
python scripts/pipeline_orchestrator.py --chunk-size 800 --overlap 100
```

#### Verbose Logging

Enable detailed debug output:

```bash
python scripts/pipeline_orchestrator.py --verbose
# Or set in .env: LOG_LEVEL=DEBUG
```

---

## Folder Structure

```
OQTF/
├── .env                          # Environment variables (DO NOT COMMIT)
├── .env.example                  # Example environment file
├── .gitignore                    # Git ignore patterns
├── README.md                     # This file
├── requirements.txt              # Python dependencies
├── Consigne.txt                  # Project specifications
│
├── data/                         # Local data storage
│   ├── meta/                     # Metadata files
│   │   ├── metadata.json         # Main metadata file (JSONL)
│   │   └── status_log.json       # Processing status tracking
│   └── jsonl/                    # Generated JSONL chunks
│       ├── pref92_visa2025.jsonl
│       ├── cir_vie2024.jsonl
│       └── ...
│
├── utils/                        # Utility modules
│   ├── __init__.py
│   ├── text_cleaning.py          # Text normalization & cleaning
│   ├── chunking.py               # Smart chunking with overlap
│   ├── jsonl_writer.py           # JSONL file generation
│   ├── gdrive_client.py          # Google Drive API wrapper
│   ├── metadata_manager.py       # Metadata CRUD operations
│   └── logger.py                 # Logging configuration
│
├── processors/                   # Document processors
│   ├── __init__.py
│   ├── base_processor.py         # Abstract base processor
│   ├── pdf_processor.py          # PDF document processing
│   ├── html_processor.py         # HTML document processing
│   └── url_processor.py          # URL fetching & processing
│
├── scripts/                      # Executable scripts
│   ├── pipeline_orchestrator.py  # Main pipeline script
│   ├── setup_gdrive_auth.py      # Google Drive authentication setup
│   ├── validate_metadata.py      # Validate metadata format
│   └── generate_embeddings.py    # Future: embedding generation
│
└── tests/                        # Test suite (future)
    ├── __init__.py
    ├── test_processors.py
    ├── test_chunking.py
    └── test_metadata.py
```

### Directory Explanations

#### `/utils/`
Reusable utility modules shared across the pipeline:

- **`text_cleaning.py`**: Text preprocessing functions
  - Remove boilerplate (headers, footers, navigation)
  - Normalize whitespace and punctuation
  - Handle special characters and encoding
  - Remove duplicate paragraphs

- **`chunking.py`**: Intelligent text chunking
  - Split on logical boundaries (paragraphs, sections)
  - Configurable chunk size with word overlap
  - Preserve context between chunks
  - Assign chunk metadata (IDs, page references)

- **`jsonl_writer.py`**: JSONL file operations
  - Write chunks with metadata to JSONL
  - Validate JSON structure
  - Handle encoding and special characters

- **`gdrive_client.py`**: Google Drive integration
  - Authenticate with OAuth 2.0
  - Download files by ID or share link
  - Upload JSONL results
  - Manage folder structure

- **`metadata_manager.py`**: Metadata operations
  - Load/save metadata.json
  - Update document status
  - Query documents by filters
  - Validate metadata schema

#### `/processors/`
Document-type-specific processing logic:

- **`base_processor.py`**: Abstract base class defining processor interface
- **`pdf_processor.py`**: PDF extraction using pdfplumber/PyMuPDF, optional OCR
- **`html_processor.py`**: HTML parsing with BeautifulSoup, content extraction
- **`url_processor.py`**: Fetch URLs, extract main content, handle redirects

#### `/scripts/`
Executable pipeline scripts:

- **`pipeline_orchestrator.py`**: Main entry point coordinating all processing
- **`setup_gdrive_auth.py`**: One-time Google Drive authentication
- **`validate_metadata.py`**: Validate metadata.json format and completeness

#### `/data/`
Local data storage (duplicates Google Drive for faster access):

- **`meta/`**: Metadata and status tracking files
- **`jsonl/`**: Generated JSONL chunks per document

---

## Metadata Format

### Document Metadata Schema

Each document entry in `metadata.json` must include:

```json
{
  "document_id": "string (required, unique)",
  "document_type": "pdf|html|url (required)",
  "drive_link": "string (required, Google Drive share link)",
  "source_url": "string (required, original source URL)",
  "category": "string (required)",
  "sub_category": "string (optional)",
  "jurisdiction": "string (optional)",
  "date": "YYYY-MM-DD (required)",
  "authority_score": "integer 1-5 (required)",
  "language": "string ISO 639-1 code (required)",
  "jsonl_ready": "boolean (auto-managed)",
  "embedding_done": "boolean (auto-managed)"
}
```

### Field Descriptions

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `document_id` | string | Yes | Unique identifier for document | `"pref92_visa2025"` |
| `document_type` | enum | Yes | Document format: `pdf`, `html`, or `url` | `"pdf"` |
| `drive_link` | string | Yes | Google Drive shareable link | `"https://drive.google.com/file/d/..."` |
| `source_url` | string | Yes | Original document URL | `"https://prefecture92.gouv.fr/..."` |
| `category` | string | Yes | Primary document category | `"titre_sejour"` |
| `sub_category` | string | No | Secondary category | `"delai_renouvellement"` |
| `jurisdiction` | string | No | Geographic jurisdiction | `"Hauts-de-Seine"` |
| `date` | date | Yes | Document publication date | `"2025-01-10"` |
| `authority_score` | integer | Yes | Reliability score (1-5) | `3` |
| `language` | string | Yes | ISO 639-1 language code | `"fr"` |
| `jsonl_ready` | boolean | Auto | Chunking completion status | `true` |
| `embedding_done` | boolean | Auto | Embedding generation status | `false` |

### Category Guidelines

**Primary Categories:**
- `titre_sejour` - Residence permits
- `visa` - Visa information
- `naturalisation` - Citizenship/naturalization
- `aide_sociale` - Social assistance
- `logement` - Housing
- `emploi` - Employment
- `sante` - Healthcare
- `education` - Education

**Sub-Categories (Examples):**
- `delai_renouvellement` - Renewal deadlines
- `documents_requis` - Required documents
- `procedure` - Procedures
- `droits` - Rights
- `obligations` - Obligations

### Authority Score Guidelines

Score documents based on reliability:

- **5**: Official government sources (prefecture, OFII, service-public.fr)
- **4**: Government-affiliated organizations, legal databases
- **3**: Established NGOs, legal aid organizations
- **2**: Community organizations, verified blogs
- **1**: Individual blogs, unverified sources

### Complete Metadata Example

```json
{
  "document_id": "pref92_visa2025",
  "document_type": "pdf",
  "drive_link": "https://drive.google.com/file/d/1ABCxyz123/view?usp=sharing",
  "source_url": "https://www.hauts-de-seine.gouv.fr/demarches/titres-sejour",
  "category": "titre_sejour",
  "sub_category": "delai_renouvellement",
  "jurisdiction": "Hauts-de-Seine",
  "date": "2025-01-10",
  "authority_score": 5,
  "language": "fr",
  "jsonl_ready": false,
  "embedding_done": false
}
```

### JSONL Chunk Format

After processing, each chunk in the generated JSONL file includes:

```json
{
  "chunk_id": "pref92_visa2025_001",
  "text": "Les étudiants étrangers doivent renouveler leur titre de séjour au moins 2 mois avant son expiration. Il est recommandé de prendre rendez-vous en ligne via le site de la préfecture. Les documents nécessaires incluent : passeport valide, titre de séjour actuel, certificat de scolarité, justificatif de domicile récent, et photos d'identité conformes.",
  "document_id": "pref92_visa2025",
  "category": "titre_sejour",
  "sub_category": "delai_renouvellement",
  "jurisdiction": "Hauts-de-Seine",
  "source_url": "https://www.hauts-de-seine.gouv.fr/demarches/titres-sejour",
  "drive_link": "https://drive.google.com/file/d/1ABCxyz123/view?usp=sharing",
  "language": "fr",
  "authority_score": 5,
  "date": "2025-01-10",
  "page_start": 1,
  "page_end": 2,
  "chunk_size": 487,
  "overlap_prev": 50
}
```

---

## Pipeline Workflow

### Detailed Processing Steps

#### 1. Document Fetching

```
Input: metadata.json entry with drive_link
       ↓
[Google Drive API]
├── Authenticate with OAuth 2.0
├── Parse share link to extract file ID
├── Download file via Drive API
└── Save to temporary buffer (no local storage)
       ↓
Output: Document binary data
```

#### 2. Document Type Detection & Processing

**PDF Processing:**
```python
# Using pdfplumber (preferred for text-based PDFs)
with pdfplumber.open(pdf_buffer) as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        # Track page numbers for metadata

# Fallback: OCR for scanned PDFs
if enable_ocr and text_extraction_failed:
    images = convert_from_bytes(pdf_buffer)
    text = pytesseract.image_to_string(images, lang='fra')
```

**HTML Processing:**
```python
soup = BeautifulSoup(html_content, 'html.parser')
# Remove scripts, styles, navigation
for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
    tag.decompose()
# Extract main content
main_content = soup.find('main') or soup.find('article') or soup.body
text = main_content.get_text(separator=' ', strip=True)
```

**URL Processing:**
```python
response = requests.get(url, timeout=30)
# Follow redirects, handle HTTP errors
# Parse HTML as above
```

#### 3. Text Cleaning Pipeline

```
Raw Text
    ↓
[Boilerplate Removal]
├── Remove repeated headers/footers
├── Strip navigation elements
├── Remove page numbers
└── Clean metadata sections
    ↓
[Normalization]
├── Normalize whitespace (spaces, newlines, tabs)
├── Fix encoding issues (UTF-8)
├── Standardize punctuation
└── Handle special characters
    ↓
[Deduplication]
├── Remove duplicate paragraphs
├── Merge fragmented sentences
└── Clean bullet points and lists
    ↓
[Language Processing]
├── Detect language per section
├── Tag mixed-language content
└── Preserve language metadata
    ↓
Cleaned Text
```

#### 4. Smart Chunking with Overlap

```
Cleaned Text (e.g., 3000 words)
    ↓
[Chunk Size: 500 words, Overlap: 50 words]
    ↓
Chunk 1: words [1-500]
    ├── chunk_id: doc_001
    ├── page_start: 1
    ├── page_end: 2
    └── overlap_prev: 0
    ↓
Chunk 2: words [451-950]  ← 50 word overlap with Chunk 1
    ├── chunk_id: doc_002
    ├── page_start: 2
    ├── page_end: 4
    └── overlap_prev: 50
    ↓
Chunk 3: words [901-1400]  ← 50 word overlap with Chunk 2
    ├── chunk_id: doc_003
    ├── page_start: 4
    ├── page_end: 6
    └── overlap_prev: 50
    ↓
... (continues)
    ↓
Total: 6 chunks with preserved context
```

**Why Overlap?**
- Prevents context loss at chunk boundaries
- Ensures LLM sees complete concepts
- Improves retrieval accuracy for queries spanning boundaries

#### 5. Metadata Attachment

Each chunk inherits all document metadata plus chunk-specific fields:

```python
chunk_metadata = {
    # Document metadata (inherited)
    "document_id": doc.document_id,
    "category": doc.category,
    "sub_category": doc.sub_category,
    "jurisdiction": doc.jurisdiction,
    "source_url": doc.source_url,
    "drive_link": doc.drive_link,
    "date": doc.date,
    "authority_score": doc.authority_score,
    "language": doc.language,

    # Chunk-specific metadata
    "chunk_id": f"{doc.document_id}_{chunk_num:03d}",
    "text": chunk_text,
    "page_start": chunk.page_start,
    "page_end": chunk.page_end,
    "chunk_size": len(chunk_text.split()),
    "overlap_prev": 50 if chunk_num > 1 else 0
}
```

#### 6. JSONL Generation

```python
# One line per chunk
with open(f"data/jsonl/{document_id}.jsonl", "w", encoding="utf-8") as f:
    for chunk in chunks:
        f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
```

**File Structure:**
```
data/jsonl/pref92_visa2025.jsonl
├── Line 1: {"chunk_id": "pref92_visa2025_001", "text": "...", ...}
├── Line 2: {"chunk_id": "pref92_visa2025_002", "text": "...", ...}
├── Line 3: {"chunk_id": "pref92_visa2025_003", "text": "...", ...}
└── ...
```

#### 7. Status Update

```python
# Update metadata.json
metadata["jsonl_ready"] = True
metadata["jsonl_path"] = f"data/jsonl/{document_id}.jsonl"
metadata["chunks_count"] = len(chunks)
metadata["processed_at"] = "2025-01-15T10:30:00Z"

# Log to status_log.json
status_log.append({
    "document_id": document_id,
    "timestamp": "2025-01-15T10:30:00Z",
    "status": "success",
    "chunks_generated": len(chunks)
})
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Google Drive Authentication Errors

**Problem:** `RefreshError: invalid_grant`

**Solutions:**
```bash
# Re-authenticate with Google Drive
python scripts/setup_gdrive_auth.py

# Verify credentials.json is present
ls -la credentials.json

# Check .env has correct credentials
cat .env | grep GOOGLE_DRIVE
```

**Problem:** `HttpError 404: File not found`

**Solution:**
- Verify drive_link is a shareable link (not "Restricted")
- Check file hasn't been deleted or moved
- Ensure service account has access to file

#### 2. PDF Processing Issues

**Problem:** `PDFSyntaxError: could not find startxref`

**Solutions:**
```bash
# Install alternative PDF library
pip install PyMuPDF  # More robust than pdfplumber

# Enable OCR for scanned PDFs
pip install pytesseract pdf2image
# Set ENABLE_OCR=true in .env
```

**Problem:** Empty text extraction from PDF

**Solution:**
- PDF may be scanned image - enable OCR
- PDF may be corrupted - try opening in PDF reader
- PDF may have security restrictions - use PyMuPDF

#### 3. Text Encoding Issues

**Problem:** `UnicodeDecodeError: 'utf-8' codec can't decode byte`

**Solution:**
```python
# In text_cleaning.py, add encoding detection
import chardet

def detect_encoding(text_bytes):
    result = chardet.detect(text_bytes)
    return result['encoding']

# Use detected encoding
text = text_bytes.decode(detect_encoding(text_bytes), errors='ignore')
```

#### 4. Chunking Produces Too Many/Few Chunks

**Problem:** Documents generate unexpected chunk counts

**Solution:**
```bash
# Adjust chunk size in .env or command line
python scripts/pipeline_orchestrator.py --chunk-size 800 --overlap 100

# For very short documents (< 500 words), adjust minimum chunk size
# Edit chunking.py to set min_chunk_size
```

#### 5. Memory Issues with Large PDFs

**Problem:** `MemoryError` when processing large documents

**Solutions:**
```python
# Process page-by-page instead of loading entire PDF
# In pdf_processor.py:
for page_num in range(len(pdf.pages)):
    page = pdf.pages[page_num]
    text = page.extract_text()
    yield text  # Generator pattern

# Increase system memory or use streaming
```

#### 6. metadata.json Validation Errors

**Problem:** `Invalid metadata format`

**Solution:**
```bash
# Validate metadata before running pipeline
python scripts/validate_metadata.py data/meta/metadata.json

# Common issues:
# - Missing required fields (document_id, date, etc.)
# - Invalid date format (use YYYY-MM-DD)
# - Invalid document_type (must be pdf/html/url)
# - Invalid authority_score (must be 1-5)
```

#### 7. JSONL File Corruption

**Problem:** Cannot read generated JSONL file

**Solution:**
```bash
# Validate JSONL format
python -c "
import json
with open('data/jsonl/pref92_visa2025.jsonl') as f:
    for i, line in enumerate(f, 1):
        try:
            json.loads(line)
        except json.JSONDecodeError as e:
            print(f'Error on line {i}: {e}')
"

# Regenerate with --force flag
python scripts/pipeline_orchestrator.py --document-id pref92_visa2025 --force
```

### Debugging Tips

#### Enable Verbose Logging

```bash
# Set in .env
LOG_LEVEL=DEBUG

# Or command line
python scripts/pipeline_orchestrator.py --verbose
```

#### Test Individual Components

```python
# Test PDF processor
from processors.pdf_processor import PDFProcessor
processor = PDFProcessor()
text = processor.extract_text("path/to/test.pdf")
print(f"Extracted {len(text)} characters")

# Test chunking
from utils.chunking import chunk_text
chunks = chunk_text(text, chunk_size=500, overlap=50)
print(f"Generated {len(chunks)} chunks")

# Test Google Drive
from utils.gdrive_client import GDriveClient
client = GDriveClient()
file_id = client.get_file_id_from_link(drive_link)
print(f"File ID: {file_id}")
```

#### Check Pipeline Status

```bash
# View processing status for all documents
python scripts/validate_metadata.py --check-status

# Expected output:
# Total documents: 10
# ├── jsonl_ready: 8 (80%)
# ├── embedding_done: 3 (30%)
# └── pending: 2 (20%)
```

---

## Future Enhancements

### Planned Features

#### 1. Embedding Generation
- Generate vector embeddings for each chunk
- Support multiple embedding models:
  - OpenAI `text-embedding-3-large` (English/multilingual)
  - Cohere `embed-multilingual-v3.0` (100+ languages)
  - Sentence Transformers (local, privacy-focused)
- Batch processing for efficiency
- Cache embeddings to avoid regeneration

```bash
# Future command
python scripts/generate_embeddings.py --model openai --batch-size 100
```

#### 2. Vector Database Integration
- Pinecone for cloud-hosted vector search
- Weaviate for self-hosted with semantic search
- Qdrant for high-performance local deployment
- Metadata filtering and hybrid search
- Multi-tenancy support per jurisdiction/category

#### 3. Enhanced RAG Features
- **Hybrid Search**: Combine dense vector search with BM25 keyword search
- **Reranking**: Use cross-encoder models to rerank results by relevance
- **Query Expansion**: Automatically expand user queries with synonyms
- **Citation Tracking**: Link responses back to source documents and pages
- **Multi-hop Reasoning**: Answer complex queries requiring multiple documents

#### 4. Advanced Processing
- **Table Extraction**: Parse tables from PDFs with layout analysis
- **Image Analysis**: Extract information from document images
- **Multi-language Support**: Automatic translation for cross-language queries
- **Entity Recognition**: Extract and index key entities (dates, locations, laws)
- **Relationship Extraction**: Build knowledge graph of document relationships

#### 5. Pipeline Improvements
- **Incremental Updates**: Only process new/modified documents
- **Parallel Processing**: Multi-threaded document processing
- **Scheduled Processing**: Cron jobs for automatic updates
- **Web Scraping**: Automatic monitoring of prefecture websites
- **Quality Metrics**: Track chunk quality, coherence, and coverage

#### 6. User Interface
- **Web Dashboard**: Monitor pipeline status, view statistics
- **Search Interface**: Test RAG queries with result visualization
- **Document Management**: Upload, edit, delete documents via UI
- **Analytics**: Usage statistics, popular queries, document coverage

#### 7. API Development
- **REST API**: Expose RAG functionality via FastAPI
- **Streaming Responses**: Real-time answer generation
- **Rate Limiting**: Control API usage and costs
- **Authentication**: User management and access control
- **Webhooks**: Notify on processing completion

### Contribution Ideas

We welcome contributions in these areas:

1. **Document Processors**
   - Add support for DOCX, ODT formats
   - Improve OCR accuracy for scanned documents
   - Handle password-protected PDFs

2. **Text Processing**
   - Better header/footer detection algorithms
   - Improved chunking strategies (semantic, sentence-based)
   - Language-specific preprocessing

3. **Testing & Quality**
   - Unit tests for all modules
   - Integration tests for pipeline
   - Performance benchmarks
   - Documentation improvements

4. **Deployment**
   - Docker containerization
   - Kubernetes deployment configs
   - CI/CD pipeline setup
   - Monitoring and alerting

---

## Contributing

We appreciate contributions! Please follow these guidelines:

### Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Set up development environment (see Installation)
4. Make your changes
5. Run tests (when available): `pytest tests/`
6. Commit with clear messages: `git commit -m "Add feature: description"`
7. Push to your fork: `git push origin feature/your-feature-name`
8. Open a Pull Request

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Add docstrings for all functions and classes
- Keep functions focused and under 50 lines
- Use meaningful variable names

```python
def process_document(document_id: str, chunk_size: int = 500) -> list[dict]:
    """
    Process a document and generate JSONL chunks.

    Args:
        document_id: Unique identifier for the document
        chunk_size: Number of words per chunk (default: 500)

    Returns:
        List of chunk dictionaries with metadata

    Raises:
        ValueError: If document_id not found in metadata
        ProcessingError: If document processing fails
    """
    # Implementation
```

### Pull Request Guidelines

- Include clear description of changes
- Reference related issues: `Fixes #123`
- Add tests for new functionality
- Update documentation (README, docstrings)
- Ensure all tests pass
- Keep PRs focused on single feature/fix

---

## License

This project is licensed under the MIT License - see LICENSE file for details.

---

## Support

For questions, issues, or feature requests:

- Open an issue on GitHub
- Contact: your-email@example.com
- Documentation: [Link to detailed docs]

---

## Acknowledgments

- Google Drive API for seamless document storage
- pdfplumber/PyMuPDF for robust PDF processing
- BeautifulSoup for HTML parsing
- The open-source community for excellent Python libraries

---

**Last Updated:** 2025-12-12
**Version:** 1.0.0
**Maintainer:** Your Name
