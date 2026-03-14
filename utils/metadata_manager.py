"""
Metadata Manager Module

Provides a clean interface for managing document metadata in the RAG pipeline.
Handles reading, updating, and persisting metadata for document processing status.

The metadata file follows the JSONL format (one JSON object per line) or
a standard JSON array format.
"""

import fcntl
import json
import logging
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetadataError(Exception):
    """Base exception for Metadata Manager errors."""
    pass


class MetadataFileNotFoundError(MetadataError):
    """Raised when metadata file doesn't exist."""
    pass


class MetadataValidationError(MetadataError):
    """Raised when metadata validation fails."""
    pass


class DocumentNotFoundError(MetadataError):
    """Raised when a document is not found in metadata."""
    pass


class MetadataManager:
    """
    Manager for document metadata operations.

    This class provides methods to read, update, and manage metadata for
    documents in the RAG pipeline. Supports both JSON array and JSONL formats.

    Attributes:
        metadata_file (Path): Path to the metadata file
        metadata (List[Dict]): In-memory metadata storage
        _is_jsonl (bool): Whether the file is in JSONL format

    Example:
        >>> manager = MetadataManager("/path/to/metadata.json")
        >>> pending = manager.get_pending_documents()
        >>> for doc in pending:
        ...     print(f"Processing: {doc['document_id']}")
        ...     # Process document...
        ...     manager.update_document_status(
        ...         doc['document_id'],
        ...         jsonl_ready=True,
        ...         embedding_done=False
        ...     )
        >>> manager.save()
    """

    # Required fields for document metadata
    REQUIRED_FIELDS = {
        'document_id', 'document_type', 'drive_link', 'source_url',
        'category', 'jurisdiction', 'date', 'authority_score', 'language'
    }

    # Optional fields with defaults
    OPTIONAL_FIELDS = {
        'sub_category': None,
        'jsonl_ready': False,
        'embedding_done': False,
        'processed_date': None,
        'chunk_count': 0
    }

    def __init__(self, metadata_file: str) -> None:
        """
        Initialize metadata manager with a metadata file.

        Args:
            metadata_file: Path to the metadata JSON/JSONL file

        Raises:
            MetadataFileNotFoundError: If metadata file doesn't exist
            MetadataError: If file format is invalid

        Example:
            >>> manager = MetadataManager("/data/meta/metadata.json")
        """
        self.metadata_file = Path(metadata_file).resolve()
        self.metadata: list[dict[str, Any]] = []
        self._is_jsonl = False
        self._last_modified: float | None = None

        if not self.metadata_file.exists():
            logger.warning(
                f"Metadata file not found: {self.metadata_file}. "
                "Creating new metadata storage."
            )
            # Create parent directory if needed
            self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
            # Initialize empty metadata file
            self._save_to_disk([])
        else:
            self._load_metadata()

    def _load_metadata(self) -> None:
        """
        Load metadata from file.

        Supports both JSON array and JSONL formats.
        Auto-detects format based on file content.

        Raises:
            MetadataError: If file format is invalid
        """
        try:
            with open(self.metadata_file, encoding='utf-8') as f:
                content = f.read().strip()

            if not content:
                # Empty file
                self.metadata = []
                self._is_jsonl = False
                logger.info("Loaded empty metadata file")
                return

            # Try to parse as JSON array first
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    self.metadata = data
                    self._is_jsonl = False
                    logger.info(
                        f"Loaded {len(self.metadata)} documents from JSON array"
                    )
                    return
                elif isinstance(data, dict):
                    # Single document in JSON format
                    self.metadata = [data]
                    self._is_jsonl = False
                    logger.info("Loaded 1 document from JSON object")
                    return
            except json.JSONDecodeError:
                pass

            # Try JSONL format (one JSON object per line)
            self.metadata = []
            for line_num, line in enumerate(content.split('\n'), 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    doc = json.loads(line)
                    self.metadata.append(doc)
                except json.JSONDecodeError as e:
                    raise MetadataError(
                        f"Invalid JSON on line {line_num}: {str(e)}"
                    ) from e

            self._is_jsonl = True
            logger.info(
                f"Loaded {len(self.metadata)} documents from JSONL format"
            )

            # Store last modified time
            self._last_modified = self.metadata_file.stat().st_mtime

        except Exception as e:
            raise MetadataError(
                f"Failed to load metadata from {self.metadata_file}: {str(e)}"
            ) from e

    def _validate_document(self, document: dict[str, Any]) -> None:
        """
        Validate document metadata structure.

        Args:
            document: Document metadata dictionary

        Raises:
            MetadataValidationError: If validation fails
        """
        # Check required fields
        missing_fields = self.REQUIRED_FIELDS - set(document.keys())
        if missing_fields:
            raise MetadataValidationError(
                f"Missing required fields: {missing_fields}"
            )

        # Validate document_id
        if not document.get('document_id'):
            raise MetadataValidationError("document_id cannot be empty")

        # Validate document_type
        valid_types = {'pdf', 'html', 'url'}
        if document.get('document_type') not in valid_types:
            raise MetadataValidationError(
                f"document_type must be one of {valid_types}"
            )

        # Validate authority_score
        score = document.get('authority_score')
        if not isinstance(score, (int, float)) or not (0 <= score <= 5):
            raise MetadataValidationError(
                "authority_score must be a number between 0 and 5"
            )

    @contextmanager
    def _file_lock(self):
        """Context manager for file locking to prevent concurrent writes."""
        lock_file = self.metadata_file.with_suffix('.lock')
        f = open(lock_file, 'w')
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            f.close()
            if lock_file.exists():
                lock_file.unlink()

    def get_pending_documents(self) -> list[dict[str, Any]]:
        """
        Get all documents where jsonl_ready is False.

        Returns:
            List of document metadata dictionaries

        Example:
            >>> manager = MetadataManager("/data/meta/metadata.json")
            >>> pending = manager.get_pending_documents()
            >>> print(f"Found {len(pending)} pending documents")
            >>> for doc in pending:
            ...     print(f"- {doc['document_id']}: {doc['category']}")
        """
        pending = [
            doc for doc in self.metadata
            if not doc.get('jsonl_ready', False)
        ]

        logger.info(f"Found {len(pending)} pending documents")
        return deepcopy(pending)

    def get_document(self, document_id: str) -> dict[str, Any]:
        """
        Get metadata for a specific document.

        Args:
            document_id: Unique document identifier

        Returns:
            Document metadata dictionary

        Raises:
            DocumentNotFoundError: If document is not found

        Example:
            >>> manager = MetadataManager("/data/meta/metadata.json")
            >>> doc = manager.get_document("pref92_visa2025")
            >>> print(doc['category'], doc['jurisdiction'])
        """
        for doc in self.metadata:
            if doc.get('document_id') == document_id:
                return deepcopy(doc)

        raise DocumentNotFoundError(
            f"Document not found: {document_id}"
        )

    def update_document_status(
        self,
        document_id: str,
        jsonl_ready: bool | None = None,
        embedding_done: bool | None = None,
        chunk_count: int | None = None
    ) -> None:
        """
        Update processing status for a document.

        Args:
            document_id: Unique document identifier
            jsonl_ready: Whether JSONL chunks are ready
            embedding_done: Whether embeddings are completed
            chunk_count: Number of chunks generated

        Raises:
            DocumentNotFoundError: If document is not found

        Example:
            >>> manager = MetadataManager("/data/meta/metadata.json")
            >>> manager.update_document_status(
            ...     "pref92_visa2025",
            ...     jsonl_ready=True,
            ...     embedding_done=False,
            ...     chunk_count=25
            ... )
            >>> manager.save()
        """
        found = False

        for doc in self.metadata:
            if doc.get('document_id') == document_id:
                # Update status fields
                if jsonl_ready is not None:
                    doc['jsonl_ready'] = jsonl_ready
                    if jsonl_ready:
                        doc['processed_date'] = datetime.now().isoformat()

                if embedding_done is not None:
                    doc['embedding_done'] = embedding_done

                if chunk_count is not None:
                    doc['chunk_count'] = chunk_count

                found = True
                logger.info(
                    f"Updated status for document {document_id}: "
                    f"jsonl_ready={doc.get('jsonl_ready')}, "
                    f"embedding_done={doc.get('embedding_done')}, "
                    f"chunk_count={doc.get('chunk_count')}"
                )
                break

        if not found:
            raise DocumentNotFoundError(
                f"Cannot update status: document not found: {document_id}"
            )

    def add_document(self, document_metadata: dict[str, Any]) -> None:
        """
        Add a new document to metadata.

        Args:
            document_metadata: Document metadata dictionary

        Raises:
            MetadataValidationError: If validation fails
            MetadataError: If document already exists

        Example:
            >>> manager = MetadataManager("/data/meta/metadata.json")
            >>> new_doc = {
            ...     "document_id": "pref75_titre2025",
            ...     "document_type": "pdf",
            ...     "drive_link": "https://drive.google.com/file/d/xyz",
            ...     "source_url": "https://prefecture75.gouv.fr/titre",
            ...     "category": "titre_sejour",
            ...     "sub_category": "renouvellement",
            ...     "jurisdiction": "Paris",
            ...     "date": "2025-12-12",
            ...     "authority_score": 4,
            ...     "language": "fr"
            ... }
            >>> manager.add_document(new_doc)
            >>> manager.save()
        """
        # Validate document
        self._validate_document(document_metadata)

        # Check if document already exists
        document_id = document_metadata['document_id']
        for doc in self.metadata:
            if doc.get('document_id') == document_id:
                raise MetadataError(
                    f"Document already exists: {document_id}. "
                    "Use update_document_status() to modify existing documents."
                )

        # Add optional fields with defaults if not present
        for field, default_value in self.OPTIONAL_FIELDS.items():
            if field not in document_metadata:
                document_metadata[field] = default_value

        # Add timestamp
        document_metadata['added_date'] = datetime.now().isoformat()

        # Add to metadata
        self.metadata.append(document_metadata)

        logger.info(f"Added new document: {document_id}")

    def remove_document(self, document_id: str) -> None:
        """
        Remove a document from metadata.

        Args:
            document_id: Unique document identifier

        Raises:
            DocumentNotFoundError: If document is not found

        Example:
            >>> manager = MetadataManager("/data/meta/metadata.json")
            >>> manager.remove_document("old_document_id")
            >>> manager.save()
        """
        original_count = len(self.metadata)
        self.metadata = [
            doc for doc in self.metadata
            if doc.get('document_id') != document_id
        ]

        if len(self.metadata) == original_count:
            raise DocumentNotFoundError(
                f"Cannot remove: document not found: {document_id}"
            )

        logger.info(f"Removed document: {document_id}")

    def get_all_documents(self) -> list[dict[str, Any]]:
        """
        Get all documents in metadata.

        Returns:
            List of all document metadata dictionaries

        Example:
            >>> manager = MetadataManager("/data/meta/metadata.json")
            >>> all_docs = manager.get_all_documents()
            >>> print(f"Total documents: {len(all_docs)}")
        """
        return deepcopy(self.metadata)

    def get_documents_by_category(self, category: str) -> list[dict[str, Any]]:
        """
        Get all documents in a specific category.

        Args:
            category: Document category to filter by

        Returns:
            List of document metadata dictionaries

        Example:
            >>> manager = MetadataManager("/data/meta/metadata.json")
            >>> visa_docs = manager.get_documents_by_category("titre_sejour")
            >>> print(f"Found {len(visa_docs)} titre_sejour documents")
        """
        docs = [
            doc for doc in self.metadata
            if doc.get('category') == category
        ]
        logger.info(f"Found {len(docs)} documents in category: {category}")
        return deepcopy(docs)

    def get_documents_by_jurisdiction(self, jurisdiction: str) -> list[dict[str, Any]]:
        """
        Get all documents for a specific jurisdiction.

        Args:
            jurisdiction: Jurisdiction to filter by

        Returns:
            List of document metadata dictionaries

        Example:
            >>> manager = MetadataManager("/data/meta/metadata.json")
            >>> paris_docs = manager.get_documents_by_jurisdiction("Paris")
        """
        docs = [
            doc for doc in self.metadata
            if doc.get('jurisdiction') == jurisdiction
        ]
        logger.info(f"Found {len(docs)} documents for jurisdiction: {jurisdiction}")
        return deepcopy(docs)

    def _save_to_disk(self, data: list[dict[str, Any]]) -> None:
        """
        Save metadata to disk in the appropriate format.

        Args:
            data: List of document metadata to save
        """
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            if self._is_jsonl:
                # JSONL format: one JSON object per line
                for doc in data:
                    f.write(json.dumps(doc, ensure_ascii=False) + '\n')
            else:
                # JSON array format: pretty-printed for readability
                json.dump(data, f, ensure_ascii=False, indent=2)

        # Update last modified time
        self._last_modified = self.metadata_file.stat().st_mtime

    def save(self, backup: bool = True) -> None:
        """
        Save metadata to file with optional backup.

        Args:
            backup: Whether to create a backup before saving (default: True)

        Raises:
            MetadataError: If save operation fails

        Example:
            >>> manager = MetadataManager("/data/meta/metadata.json")
            >>> manager.update_document_status("doc123", jsonl_ready=True)
            >>> manager.save()
        """
        try:
            with self._file_lock():
                # Create backup if requested and file exists
                if backup and self.metadata_file.exists():
                    backup_file = self.metadata_file.with_suffix('.json.bak')
                    backup_file.write_bytes(self.metadata_file.read_bytes())
                    logger.debug(f"Created backup: {backup_file}")

                # Save metadata
                self._save_to_disk(self.metadata)

                logger.info(
                    f"Saved {len(self.metadata)} documents to {self.metadata_file}"
                )

        except Exception as e:
            raise MetadataError(
                f"Failed to save metadata: {str(e)}"
            ) from e

    def reload(self) -> None:
        """
        Reload metadata from file.

        Useful for picking up changes made by other processes.

        Example:
            >>> manager = MetadataManager("/data/meta/metadata.json")
            >>> # ... some other process modifies the file ...
            >>> manager.reload()
        """
        logger.info("Reloading metadata from file")
        self._load_metadata()

    def get_statistics(self) -> dict[str, Any]:
        """
        Get statistics about the metadata collection.

        Returns:
            Dictionary containing statistics

        Example:
            >>> manager = MetadataManager("/data/meta/metadata.json")
            >>> stats = manager.get_statistics()
            >>> print(f"Total: {stats['total_documents']}")
            >>> print(f"Pending: {stats['pending_documents']}")
            >>> print(f"Ready: {stats['jsonl_ready_count']}")
        """
        stats = {
            'total_documents': len(self.metadata),
            'jsonl_ready_count': sum(
                1 for doc in self.metadata if doc.get('jsonl_ready', False)
            ),
            'embedding_done_count': sum(
                1 for doc in self.metadata if doc.get('embedding_done', False)
            ),
            'pending_documents': sum(
                1 for doc in self.metadata if not doc.get('jsonl_ready', False)
            ),
            'categories': len(set(doc.get('category') for doc in self.metadata)),
            'jurisdictions': len(set(doc.get('jurisdiction') for doc in self.metadata)),
            'document_types': {
                doc_type: sum(
                    1 for doc in self.metadata
                    if doc.get('document_type') == doc_type
                )
                for doc_type in {'pdf', 'html', 'url'}
            }
        }

        return stats
