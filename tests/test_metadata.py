import json
from pathlib import Path

import pytest

from utils.metadata_manager import (
    DocumentNotFoundError,
    MetadataError,
    MetadataManager,
    MetadataValidationError,
)


@pytest.fixture
def sample_doc():
    return {
        "document_id": "test_doc_001",
        "document_type": "pdf",
        "drive_link": "https://drive.google.com/file/d/abc/view",
        "source_url": "https://example.com/doc.pdf",
        "category": "visa",
        "jurisdiction": "National",
        "date": "2025-01-15",
        "authority_score": 4,
        "language": "en",
    }


@pytest.fixture
def metadata_file(tmp_path, sample_doc):
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps([sample_doc], indent=2))
    return str(path)


@pytest.fixture
def manager(metadata_file):
    return MetadataManager(metadata_file)


class TestMetadataManagerInit:
    def test_loads_existing_file(self, manager, sample_doc):
        docs = manager.get_all_documents()
        assert len(docs) == 1
        assert docs[0]["document_id"] == sample_doc["document_id"]

    def test_creates_file_if_missing(self, tmp_path):
        path = str(tmp_path / "new_meta.json")
        mgr = MetadataManager(path)
        assert Path(path).exists()
        assert mgr.get_all_documents() == []

    def test_handles_empty_file(self, tmp_path):
        path = tmp_path / "empty.json"
        path.write_text("")
        mgr = MetadataManager(str(path))
        assert mgr.get_all_documents() == []


class TestGetDocument:
    def test_returns_document(self, manager, sample_doc):
        doc = manager.get_document(sample_doc["document_id"])
        assert doc["document_id"] == sample_doc["document_id"]
        assert doc["category"] == "visa"

    def test_returns_deep_copy(self, manager, sample_doc):
        doc = manager.get_document(sample_doc["document_id"])
        doc["category"] = "modified"
        original = manager.get_document(sample_doc["document_id"])
        assert original["category"] == "visa"

    def test_not_found_raises(self, manager):
        with pytest.raises(DocumentNotFoundError):
            manager.get_document("nonexistent_id")


class TestGetPendingDocuments:
    def test_returns_pending(self, manager):
        pending = manager.get_pending_documents()
        assert len(pending) == 1

    def test_excludes_ready(self, manager, sample_doc):
        manager.update_document_status(sample_doc["document_id"], jsonl_ready=True)
        pending = manager.get_pending_documents()
        assert len(pending) == 0


class TestUpdateDocumentStatus:
    def test_updates_jsonl_ready(self, manager, sample_doc):
        manager.update_document_status(sample_doc["document_id"], jsonl_ready=True)
        doc = manager.get_document(sample_doc["document_id"])
        assert doc["jsonl_ready"] is True
        assert doc["processed_date"] is not None

    def test_updates_embedding_done(self, manager, sample_doc):
        manager.update_document_status(sample_doc["document_id"], embedding_done=True)
        doc = manager.get_document(sample_doc["document_id"])
        assert doc["embedding_done"] is True

    def test_updates_chunk_count(self, manager, sample_doc):
        manager.update_document_status(sample_doc["document_id"], chunk_count=42)
        doc = manager.get_document(sample_doc["document_id"])
        assert doc["chunk_count"] == 42

    def test_not_found_raises(self, manager):
        with pytest.raises(DocumentNotFoundError):
            manager.update_document_status("bad_id", jsonl_ready=True)


class TestAddDocument:
    def test_adds_new_document(self, manager):
        new_doc = {
            "document_id": "new_doc",
            "document_type": "html",
            "drive_link": "https://drive.google.com/file/d/xyz/view",
            "source_url": "https://example.com/page",
            "category": "housing",
            "jurisdiction": "Paris",
            "date": "2025-06-01",
            "authority_score": 3,
            "language": "fr",
        }
        manager.add_document(new_doc)
        assert len(manager.get_all_documents()) == 2

    def test_sets_default_optional_fields(self, manager):
        new_doc = {
            "document_id": "defaults_test",
            "document_type": "url",
            "drive_link": "",
            "source_url": "https://example.com",
            "category": "test",
            "jurisdiction": "National",
            "date": "2025-01-01",
            "authority_score": 1,
            "language": "en",
        }
        manager.add_document(new_doc)
        doc = manager.get_document("defaults_test")
        assert doc["jsonl_ready"] is False
        assert doc["embedding_done"] is False
        assert doc["chunk_count"] == 0

    def test_duplicate_raises(self, manager, sample_doc):
        with pytest.raises(MetadataError):
            manager.add_document(sample_doc)

    def test_missing_required_fields_raises(self, manager):
        with pytest.raises(MetadataValidationError):
            manager.add_document({"document_id": "incomplete"})

    def test_invalid_type_raises(self, manager):
        bad = {
            "document_id": "bad_type",
            "document_type": "docx",
            "drive_link": "",
            "source_url": "",
            "category": "test",
            "jurisdiction": "X",
            "date": "2025-01-01",
            "authority_score": 3,
            "language": "en",
        }
        with pytest.raises(MetadataValidationError):
            manager.add_document(bad)

    def test_invalid_authority_score_raises(self, manager):
        bad = {
            "document_id": "bad_score",
            "document_type": "pdf",
            "drive_link": "",
            "source_url": "",
            "category": "test",
            "jurisdiction": "X",
            "date": "2025-01-01",
            "authority_score": 10,
            "language": "en",
        }
        with pytest.raises(MetadataValidationError):
            manager.add_document(bad)


class TestRemoveDocument:
    def test_removes_existing(self, manager, sample_doc):
        manager.remove_document(sample_doc["document_id"])
        assert len(manager.get_all_documents()) == 0

    def test_not_found_raises(self, manager):
        with pytest.raises(DocumentNotFoundError):
            manager.remove_document("ghost")


class TestFilterDocuments:
    def test_by_category(self, manager):
        docs = manager.get_documents_by_category("visa")
        assert len(docs) == 1

    def test_by_category_empty(self, manager):
        docs = manager.get_documents_by_category("nonexistent")
        assert len(docs) == 0

    def test_by_jurisdiction(self, manager):
        docs = manager.get_documents_by_jurisdiction("National")
        assert len(docs) == 1


class TestSaveAndReload:
    def test_save_and_reload(self, manager, sample_doc, metadata_file):
        manager.update_document_status(sample_doc["document_id"], jsonl_ready=True, chunk_count=10)
        manager.save()

        reloaded = MetadataManager(metadata_file)
        doc = reloaded.get_document(sample_doc["document_id"])
        assert doc["jsonl_ready"] is True
        assert doc["chunk_count"] == 10

    def test_save_creates_backup(self, manager, metadata_file):
        manager.save(backup=True)
        assert (
            Path(metadata_file + ".bak").exists()
            or Path(metadata_file.replace(".json", ".json.bak")).exists()
        )


class TestStatistics:
    def test_returns_stats(self, manager):
        stats = manager.get_statistics()
        assert stats["total_documents"] == 1
        assert stats["pending_documents"] == 1
        assert stats["jsonl_ready_count"] == 0
        assert "document_types" in stats
