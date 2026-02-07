# PROGRESSION.md - OQTF RAG Pipeline

> **Last Updated**: 2026-02-07
> **Current Phase**: Core Pipeline Development

---

## Project Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 1. Core Pipeline | **In Progress** | Document processing, chunking, JSONL generation |
| 2. Embedding Generation | Planned | Vector embeddings for chunks |
| 3. Vector DB Integration | Planned | Pinecone/Weaviate ingestion |
| 4. RAG API | Planned | FastAPI service for queries |
| 5. Production Deployment | Planned | Docker, monitoring, scaling |

---

## Completed Tasks

### Phase 1: Core Pipeline

| Task | Date | Commit | Notes |
|------|------|--------|-------|
| Initial project structure | 2025-12-12 | `7b4e83f` | Set up folders, requirements.txt, .env.example |
| PDF processor with pdfplumber | 2025-12-12 | `7b4e83f` | Includes OCR fallback with pytesseract |
| HTML processor with BeautifulSoup | 2025-12-12 | `7b4e83f` | Main content extraction, boilerplate removal |
| URL processor with trafilatura | 2025-12-12 | `7b4e83f` | Multi-library fallback (trafilatura → readability → BS4) |
| Text cleaning utilities | 2025-12-12 | `7b4e83f` | Whitespace normalization, date standardization |
| Chunking with overlap | 2025-12-12 | `7b4e83f` | 500 words, 50 overlap, metadata attachment |
| JSONL writer with validation | 2025-12-12 | `7b4e83f` | Write, append, read, merge operations |
| Metadata manager | 2025-12-12 | `7b4e83f` | CRUD operations, status tracking, statistics |
| Google Drive client | 2025-12-12 | `7b4e83f` | OAuth authentication, download/upload |
| Pipeline orchestrator | 2025-12-12 | `7b4e83f` | End-to-end document processing |
| URL processor with HTML caching | 2025-12-15 | `7a9079d` | Cache HTML to Drive before processing |
| Pipeline documentation | 2025-12-15 | `2a1fe82` | README_PIPELINE.md, workflow documentation |
| Comprehensive testing guide | 2025-12-16 | `ca501da` | TESTING.md with step-by-step instructions |
| CLAUDE.md and PROGRESSION.md | 2026-02-07 | *pending* | Project context for Claude sessions |

---

## Current Sprint

### Active Tasks

| Task | Priority | Status | Assignee | Notes |
|------|----------|--------|----------|-------|
| Document new metadata fields | High | Not Started | - | Add section_header, title fields |
| Implement parallel processing | Medium | Not Started | - | Process multiple docs concurrently |
| Add progress bar for batch ops | Low | Not Started | - | Visual feedback during processing |

### Blockers

*None currently*

---

## Known Issues

| ID | Issue | Severity | Status | Workaround |
|----|-------|----------|--------|------------|
| #1 | OCR slow for large PDFs | Medium | Open | Reduce DPI, limit pages |
| #2 | Some websites block scraping | Low | Open | Use cached HTML from Drive |
| #3 | Memory usage on large batches | Medium | Open | Process in smaller batches |

---

## Backlog

### High Priority
- [ ] Implement embedding generation script
- [ ] Add vector database connector (Pinecone/Weaviate)
- [ ] Create hybrid search (vector + BM25)
- [ ] Add authority_score weighting in retrieval

### Medium Priority
- [ ] Parallel document processing
- [ ] Automatic retry for failed downloads
- [ ] Web scraping for prefecture updates
- [ ] Multi-language embedding support

### Low Priority
- [ ] Web dashboard for status monitoring
- [ ] Webhook notifications on completion
- [ ] Docker containerization
- [ ] CI/CD pipeline setup

---

## Technical Debt

| Item | Description | Effort | Priority |
|------|-------------|--------|----------|
| Test coverage | Add pytest unit tests | Medium | High |
| Type hints | Complete type annotations | Low | Medium |
| Error handling | Standardize across modules | Medium | Medium |
| Logging format | Structured JSON logging | Low | Low |

---

## Metrics

### Pipeline Statistics (as of last run)
- **Total Documents**: 2 (sample data)
- **JSONL Ready**: 0
- **Embedding Done**: 0
- **Categories**: titre_sejour, aide_sociale
- **Jurisdictions**: Hauts-de-Seine, National

### Performance Benchmarks
- PDF extraction: ~2-5 seconds per page
- HTML extraction: ~1 second per document
- URL fetching: ~3-10 seconds (network dependent)
- Chunking: ~0.5 seconds per document
- JSONL writing: ~0.1 seconds per document

---

## Changelog

### [Unreleased]
- Added CLAUDE.md for project context
- Added PROGRESSION.md for task tracking

### [v0.1.0] - 2025-12-16
- Initial release with core pipeline
- PDF, HTML, URL processing
- Text cleaning and chunking
- JSONL generation
- Google Drive integration
- Comprehensive documentation

---

## Notes

### Session Continuity
When starting a new Claude session:
1. Read `CLAUDE.md` for project context
2. Check `PROGRESSION.md` for current tasks
3. Review recent commits with `git log --oneline -10`
4. Check for pending documents: `python -c "from utils.metadata_manager import MetadataManager; m = MetadataManager('data/meta/metadata.json'); print(m.get_statistics())"`

### After Completing a Task
1. Update this file (PROGRESSION.md)
2. Move task from "Active" to "Completed"
3. Add date and commit hash
4. Create git commit with simple message
5. **No AI attribution in commits**

---

*This file is updated after each task completion. Keep it concise and actionable.*
