#!/usr/bin/env python3
"""
Pipeline Orchestrator for RAG Document Processing

This script orchestrates the entire document processing pipeline:
1. Read metadata.json to get pending documents (jsonl_ready=False)
2. For each document:
   - Detect document_type (pdf, html, url)
   - Download from Google Drive using drive_link (if needed)
   - Invoke appropriate processor (pdf_processor, html_processor, url_processor)
   - Run text cleaning (text_cleaning.py)
   - Run chunking with overlap (chunking.py)
   - Attach full metadata to each chunk
   - Write JSONL to data/jsonl/<document_id>.jsonl
   - Update metadata: jsonl_ready=True, embedding_done=False
3. Log all operations
4. Support per-document processing (--document-id flag) or batch processing

Supports per-document (--document-id) or batch processing of all pending docs.
"""

import argparse
import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

# Import utility modules
try:
    from utils.chunking import chunk_text_with_overlap
    from utils.gdrive_client import download_from_drive
    from utils.jsonl_writer import write_jsonl
    from utils.metadata_manager import MetadataManager
    from utils.text_cleaning import clean_text
except ImportError as e:
    # Allow script to be imported even if utilities don't exist yet
    print(f"Warning: Some utilities not yet implemented: {e}")

# Import processors
try:
    from processors.html_processor import process_html
    from processors.pdf_processor import process_pdf
    from processors.url_processor import process_url
except ImportError as e:
    print(f"Warning: Some processors not yet implemented: {e}")


# Configure logging
def setup_logging(log_level: str = "INFO", log_file: str | None = None) -> logging.Logger:
    """
    Configure logging for the pipeline orchestrator.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path. If None, logs to console only.

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("pipeline_orchestrator")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


class PipelineOrchestrator:
    """
    Main pipeline orchestrator for document processing.

    This class manages the end-to-end pipeline workflow from raw documents
    to processed JSONL chunks ready for embedding.
    """

    def __init__(
        self,
        metadata_path: str = "metadata.json",
        jsonl_output_dir: str = "data/jsonl",
        downloads_dir: str = "/tmp/rag_pipeline_downloads",
        logger: logging.Logger | None = None
    ):
        """
        Initialize the pipeline orchestrator.

        Args:
            metadata_path: Path to metadata.json file
            jsonl_output_dir: Directory to store output JSONL files
            downloads_dir: Temporary directory for downloaded files
            logger: Logger instance (creates new one if None)
        """
        self.metadata_path = Path(metadata_path)
        self.jsonl_output_dir = Path(jsonl_output_dir)
        self.downloads_dir = Path(downloads_dir)
        self.logger = logger or setup_logging()

        # Create necessary directories
        self.jsonl_output_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)

        # Initialize metadata manager
        self.metadata_manager = MetadataManager(self.metadata_path, logger=self.logger)

        self.logger.info("Pipeline orchestrator initialized")
        self.logger.info(f"Metadata path: {self.metadata_path}")
        self.logger.info(f"JSONL output directory: {self.jsonl_output_dir}")
        self.logger.info(f"Downloads directory: {self.downloads_dir}")

    def _detect_document_type(self, metadata: dict[str, Any]) -> str:
        """
        Detect document type from metadata.

        Args:
            metadata: Document metadata dictionary

        Returns:
            Document type ('pdf', 'html', or 'url')

        Raises:
            ValueError: If document_type is missing or invalid
        """
        doc_type = metadata.get("document_type", "").lower()

        if doc_type not in ["pdf", "html", "url"]:
            raise ValueError(
                f"Invalid or missing document_type: {doc_type}. "
                f"Must be one of: pdf, html, url"
            )

        return doc_type

    def _download_document(
        self,
        document_id: str,
        metadata: dict[str, Any]
    ) -> Path | None:
        """
        Download document from Google Drive if needed.

        Args:
            document_id: Unique document identifier
            metadata: Document metadata containing drive_link

        Returns:
            Path to downloaded file, or None if download not needed (URL type)

        Raises:
            Exception: If download fails
        """
        doc_type = metadata.get("document_type", "").lower()
        drive_link = metadata.get("drive_link")

        # URL type doesn't need download
        if doc_type == "url":
            self.logger.info(f"Document {document_id} is URL type, no download needed")
            return None

        # PDF and HTML require download from Drive
        if not drive_link:
            raise ValueError(
                f"Document {document_id} requires drive_link for type {doc_type}"
            )

        self.logger.info(f"Downloading {document_id} from Google Drive...")

        # Determine file extension
        ext = ".pdf" if doc_type == "pdf" else ".html"
        download_path = self.downloads_dir / f"{document_id}{ext}"

        # Download from Google Drive
        download_from_drive(drive_link, str(download_path), logger=self.logger)

        if not download_path.exists():
            raise FileNotFoundError(
                f"Downloaded file not found: {download_path}"
            )

        self.logger.info(f"Successfully downloaded to {download_path}")
        return download_path

    def _process_document(
        self,
        document_id: str,
        metadata: dict[str, Any],
        file_path: Path | None
    ) -> str:
        """
        Process document using appropriate processor based on type.

        Args:
            document_id: Unique document identifier
            metadata: Document metadata
            file_path: Path to downloaded file (None for URL type)

        Returns:
            Extracted raw text from document

        Raises:
            Exception: If processing fails
        """
        doc_type = metadata.get("document_type", "").lower()

        self.logger.info(f"Processing {document_id} as {doc_type} type...")

        if doc_type == "pdf":
            if not file_path:
                raise ValueError("PDF processing requires file_path")
            raw_text = process_pdf(str(file_path), logger=self.logger)

        elif doc_type == "html":
            if not file_path:
                raise ValueError("HTML processing requires file_path")
            raw_text = process_html(str(file_path), logger=self.logger)

        elif doc_type == "url":
            source_url = metadata.get("source_url")
            if not source_url:
                raise ValueError("URL processing requires source_url in metadata")
            raw_text = process_url(source_url, logger=self.logger)

        else:
            raise ValueError(f"Unsupported document type: {doc_type}")

        if not raw_text or not raw_text.strip():
            raise ValueError(f"No text extracted from {document_id}")

        self.logger.info(
            f"Extracted {len(raw_text)} characters from {document_id}"
        )
        return raw_text

    def _clean_text(self, raw_text: str, document_id: str) -> str:
        """
        Clean and preprocess extracted text.

        Args:
            raw_text: Raw extracted text
            document_id: Document identifier for logging

        Returns:
            Cleaned text
        """
        self.logger.info(f"Cleaning text for {document_id}...")

        cleaned_text = clean_text(raw_text, logger=self.logger)

        self.logger.info(
            f"Text cleaned: {len(raw_text)} -> {len(cleaned_text)} characters"
        )
        return cleaned_text

    def _chunk_text(
        self,
        cleaned_text: str,
        document_id: str,
        metadata: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Chunk text with overlap and attach metadata.

        Args:
            cleaned_text: Cleaned text to chunk
            document_id: Document identifier
            metadata: Document metadata to attach to chunks

        Returns:
            List of chunk dictionaries with full metadata
        """
        self.logger.info(f"Chunking text for {document_id}...")

        # Chunk text with overlap (default: 500 words, 50 word overlap)
        chunks = chunk_text_with_overlap(
            cleaned_text,
            chunk_size=500,
            overlap_size=50,
            logger=self.logger
        )

        self.logger.info(f"Created {len(chunks)} chunks for {document_id}")

        # Attach full metadata to each chunk
        enriched_chunks = []
        for i, chunk in enumerate(chunks, start=1):
            chunk_id = f"{document_id}_{i:03d}"

            enriched_chunk = {
                "chunk_id": chunk_id,
                "text": chunk["text"],
                "document_id": document_id,
                "category": metadata.get("category", ""),
                "sub_category": metadata.get("sub_category", ""),
                "jurisdiction": metadata.get("jurisdiction", ""),
                "source_url": metadata.get("source_url", ""),
                "drive_link": metadata.get("drive_link", ""),
                "language": metadata.get("language", "fr"),
                "authority_score": metadata.get("authority_score", 0),
                "date": metadata.get("date", ""),
                "page_start": chunk.get("page_start", 1),
                "page_end": chunk.get("page_end", 1),
                "chunk_size": chunk.get("chunk_size", 0),
                "overlap_prev": chunk.get("overlap_prev", 0)
            }

            enriched_chunks.append(enriched_chunk)

        self.logger.info(
            f"Attached metadata to all {len(enriched_chunks)} chunks"
        )
        return enriched_chunks

    def _write_jsonl(
        self,
        document_id: str,
        chunks: list[dict[str, Any]]
    ) -> Path:
        """
        Write chunks to JSONL file.

        Args:
            document_id: Document identifier
            chunks: List of enriched chunks

        Returns:
            Path to written JSONL file
        """
        output_path = self.jsonl_output_dir / f"{document_id}.jsonl"

        self.logger.info(f"Writing {len(chunks)} chunks to {output_path}...")

        write_jsonl(chunks, str(output_path), logger=self.logger)

        self.logger.info(f"Successfully wrote JSONL to {output_path}")
        return output_path

    def _cleanup_downloads(self, file_path: Path | None) -> None:
        """
        Clean up temporary downloaded files.

        Args:
            file_path: Path to file to delete
        """
        if file_path and file_path.exists():
            try:
                file_path.unlink()
                self.logger.info(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up {file_path}: {e}")

    def process_single_document(self, document_id: str) -> bool:
        """
        Process a single document through the entire pipeline.

        Args:
            document_id: Unique document identifier

        Returns:
            True if processing succeeded, False otherwise
        """
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"Starting processing for document: {document_id}")
        self.logger.info(f"{'='*80}\n")

        file_path = None

        try:
            # Step 1: Get metadata
            metadata = self.metadata_manager.get_document_metadata(document_id)
            if not metadata:
                raise ValueError(f"No metadata found for document: {document_id}")

            # Check if already processed
            if metadata.get("jsonl_ready", False):
                self.logger.warning(
                    f"Document {document_id} already processed (jsonl_ready=True). "
                    f"Skipping..."
                )
                return False

            # Step 2: Detect document type
            doc_type = self._detect_document_type(metadata)
            self.logger.info(f"Document type: {doc_type}")

            # Step 3: Download from Google Drive (if needed)
            file_path = self._download_document(document_id, metadata)

            # Step 4: Process document (extract text)
            raw_text = self._process_document(document_id, metadata, file_path)

            # Step 5: Clean text
            cleaned_text = self._clean_text(raw_text, document_id)

            # Step 6: Chunk text with overlap and attach metadata
            chunks = self._chunk_text(cleaned_text, document_id, metadata)

            # Step 7: Write JSONL
            output_path = self._write_jsonl(document_id, chunks)

            # Step 8: Update metadata
            self.metadata_manager.update_document_status(
                document_id,
                jsonl_ready=True,
                embedding_done=False,
                jsonl_path=str(output_path),
                processed_at=datetime.now().isoformat()
            )

            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"Successfully processed document: {document_id}")
            self.logger.info(f"Output: {output_path}")
            self.logger.info(f"Chunks created: {len(chunks)}")
            self.logger.info(f"{'='*80}\n")

            return True

        except Exception as e:
            self.logger.error(f"\n{'='*80}")
            self.logger.error(f"Failed to process document: {document_id}")
            self.logger.error(f"Error: {str(e)}")
            self.logger.error(f"Traceback:\n{traceback.format_exc()}")
            self.logger.error(f"{'='*80}\n")

            # Update metadata with error status
            try:
                self.metadata_manager.update_document_status(
                    document_id,
                    jsonl_ready=False,
                    error=str(e),
                    failed_at=datetime.now().isoformat()
                )
            except Exception as meta_error:
                self.logger.error(f"Failed to update error status: {meta_error}")

            return False

        finally:
            # Clean up temporary files
            self._cleanup_downloads(file_path)

    def process_pending_documents(self) -> dict[str, Any]:
        """
        Process all pending documents (jsonl_ready=False).

        Returns:
            Dictionary with processing statistics
        """
        self.logger.info(f"\n{'#'*80}")
        self.logger.info("Starting batch processing of pending documents")
        self.logger.info(f"{'#'*80}\n")

        # Get pending documents
        pending_docs = self.metadata_manager.get_pending_documents()

        if not pending_docs:
            self.logger.info("No pending documents to process")
            return {
                "total": 0,
                "succeeded": 0,
                "failed": 0,
                "skipped": 0
            }

        self.logger.info(f"Found {len(pending_docs)} pending documents\n")

        # Process each document
        stats = {
            "total": len(pending_docs),
            "succeeded": 0,
            "failed": 0,
            "skipped": 0,
            "succeeded_ids": [],
            "failed_ids": [],
            "skipped_ids": []
        }

        for i, doc_id in enumerate(pending_docs, start=1):
            self.logger.info(f"\nProcessing document {i}/{len(pending_docs)}: {doc_id}")

            success = self.process_single_document(doc_id)

            if success:
                stats["succeeded"] += 1
                stats["succeeded_ids"].append(doc_id)
            else:
                # Check if it was skipped or failed
                metadata = self.metadata_manager.get_document_metadata(doc_id)
                if metadata and metadata.get("jsonl_ready", False):
                    stats["skipped"] += 1
                    stats["skipped_ids"].append(doc_id)
                else:
                    stats["failed"] += 1
                    stats["failed_ids"].append(doc_id)

        # Print summary
        self.logger.info(f"\n{'#'*80}")
        self.logger.info("Batch processing completed")
        self.logger.info(f"{'#'*80}")
        self.logger.info(f"Total documents: {stats['total']}")
        self.logger.info(f"Succeeded: {stats['succeeded']}")
        self.logger.info(f"Failed: {stats['failed']}")
        self.logger.info(f"Skipped: {stats['skipped']}")

        if stats["failed_ids"]:
            self.logger.warning(f"Failed document IDs: {', '.join(stats['failed_ids'])}")

        self.logger.info(f"{'#'*80}\n")

        return stats


def process_pipeline(document_id: str | None = None) -> int:
    """
    Main pipeline processing function.

    Args:
        document_id: Optional document ID for single document processing.
                    If None, processes all pending documents.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Initialize orchestrator
    log_file = f"logs/pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(log_level="INFO", log_file=log_file)

    try:
        orchestrator = PipelineOrchestrator(logger=logger)

        if document_id:
            # Process single document
            success = orchestrator.process_single_document(document_id)
            return 0 if success else 1
        else:
            # Process all pending documents
            stats = orchestrator.process_pending_documents()
            return 0 if stats["failed"] == 0 else 1

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return 1


def main():
    """
    CLI entry point for pipeline orchestrator.
    """
    parser = argparse.ArgumentParser(
        description="RAG Pipeline Orchestrator - Process documents to JSONL chunks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all pending documents
  python pipeline_orchestrator.py

  # Process a specific document
  python pipeline_orchestrator.py --document-id pref92_visa2025

  # Process with debug logging
  python pipeline_orchestrator.py --log-level DEBUG

  # Process specific document with custom paths
  python pipeline_orchestrator.py \\
    --document-id pref92_visa2025 \\
    --metadata-path /path/to/metadata.json \\
    --output-dir /path/to/jsonl
        """
    )

    parser.add_argument(
        "--document-id",
        type=str,
        help="Process a specific document by ID. If not provided, processes all pending documents."
    )

    parser.add_argument(
        "--metadata-path",
        type=str,
        default="metadata.json",
        help="Path to metadata.json file (default: ./metadata.json)"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/jsonl",
        help="Output directory for JSONL files (default: ./data/jsonl)"
    )

    parser.add_argument(
        "--downloads-dir",
        type=str,
        default="/tmp/rag_pipeline_downloads",
        help="Temporary directory for downloads"
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level (default: INFO)"
    )

    parser.add_argument(
        "--log-file",
        type=str,
        help="Optional log file path. If not provided, creates timestamped log in logs/"
    )

    args = parser.parse_args()

    # Setup logging
    if not args.log_file:
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        args.log_file = log_dir / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logger = setup_logging(log_level=args.log_level, log_file=args.log_file)

    # Create orchestrator
    try:
        orchestrator = PipelineOrchestrator(
            metadata_path=args.metadata_path,
            jsonl_output_dir=args.output_dir,
            downloads_dir=args.downloads_dir,
            logger=logger
        )

        # Process documents
        if args.document_id:
            success = orchestrator.process_single_document(args.document_id)
            sys.exit(0 if success else 1)
        else:
            stats = orchestrator.process_pending_documents()
            sys.exit(0 if stats["failed"] == 0 else 1)

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
