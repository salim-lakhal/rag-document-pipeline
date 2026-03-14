import pytest

from utils.chunking import (
    _split_into_sentences,
    chunk_by_paragraphs,
    chunk_text,
    create_chunks_with_metadata,
    merge_small_chunks,
)


class TestChunkText:
    def test_basic_chunking(self):
        text = ". ".join(["Word " + str(i) for i in range(1000)]) + "."
        chunks = chunk_text(text, chunk_size=200, overlap=0)
        assert len(chunks) >= 4
        for c in chunks:
            assert "text" in c
            assert "chunk_id" in c
            assert "word_count" in c

    def test_overlap_creates_shared_content(self):
        text = " ".join([f"w{i}" for i in range(600)])
        chunks = chunk_text(text, chunk_size=300, overlap=50)
        assert len(chunks) >= 2
        last_words_first = chunks[0]["text"].split()[-50:]
        first_words_second = chunks[1]["text"].split()[:50]
        assert last_words_first == first_words_second

    def test_single_chunk_for_short_text(self):
        text = "This is a short text."
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        assert len(chunks) == 1
        assert chunks[0]["text"].strip() == text.strip()

    def test_empty_text_returns_empty(self):
        assert chunk_text("", chunk_size=500, overlap=50) == []
        assert chunk_text("   ", chunk_size=500, overlap=50) == []

    def test_invalid_chunk_size_raises(self):
        with pytest.raises(ValueError):
            chunk_text("some text", chunk_size=0, overlap=0)
        with pytest.raises(ValueError):
            chunk_text("some text", chunk_size=-1, overlap=0)

    def test_overlap_exceeds_chunk_size_raises(self):
        with pytest.raises(ValueError):
            chunk_text("some text", chunk_size=10, overlap=10)
        with pytest.raises(ValueError):
            chunk_text("some text", chunk_size=10, overlap=20)

    def test_chunk_ids_are_unique(self):
        text = " ".join(["word"] * 2000)
        chunks = chunk_text(text, chunk_size=200, overlap=20)
        ids = [c["chunk_id"] for c in chunks]
        assert len(ids) == len(set(ids))

    def test_word_count_accuracy(self):
        text = " ".join(["word"] * 500)
        chunks = chunk_text(text, chunk_size=500, overlap=0)
        assert chunks[0]["word_count"] == 500

    def test_char_count_matches_text(self):
        text = " ".join(["hello"] * 300)
        chunks = chunk_text(text, chunk_size=200, overlap=0)
        for c in chunks:
            assert c["char_count"] == len(c["text"])

    def test_page_info_attached(self):
        text = " ".join(["word"] * 100)
        page_info = {"page_num": 3, "total_pages": 10}
        chunks = chunk_text(text, chunk_size=50, overlap=0, page_info=page_info)
        for c in chunks:
            assert c["page_info"] == page_info


class TestSplitIntoSentences:
    def test_splits_on_period(self):
        text = "First sentence. Second sentence. Third sentence."
        sentences = _split_into_sentences(text)
        assert len(sentences) >= 2

    def test_single_sentence(self):
        text = "Just one sentence without punctuation"
        sentences = _split_into_sentences(text)
        assert len(sentences) == 1

    def test_preserves_all_text(self):
        text = "Hello world. This is a test. Final line."
        sentences = _split_into_sentences(text)
        joined = " ".join(sentences)
        for word in text.split():
            assert word.rstrip(".") in joined


class TestCreateChunksWithMetadata:
    def test_includes_document_metadata(self):
        text = " ".join(["word"] * 600)
        meta = {"document_id": "doc_42", "filename": "test.pdf", "document_type": "legal"}
        chunks = create_chunks_with_metadata(text, meta, chunk_size=200, overlap=20)
        for c in chunks:
            assert c["document_id"] == "doc_42"
            assert c["filename"] == "test.pdf"
            assert "chunk_index" in c
            assert "total_chunks" in c

    def test_navigation_fields(self):
        text = ". ".join(["Sentence " + str(i) for i in range(1000)]) + "."
        meta = {"document_id": "nav_test"}
        chunks = create_chunks_with_metadata(text, meta, chunk_size=200, overlap=0)
        assert len(chunks) >= 2
        assert chunks[0]["has_previous"] is False
        assert chunks[0]["has_next"] is True
        assert chunks[-1]["has_next"] is False
        assert chunks[-1]["has_previous"] is True

    def test_generates_document_id_if_missing(self):
        text = " ".join(["word"] * 100)
        chunks = create_chunks_with_metadata(text, {}, chunk_size=50, overlap=0)
        assert "document_id" in chunks[0]

    def test_empty_text_returns_empty(self):
        assert create_chunks_with_metadata("", {"document_id": "x"}) == []


class TestChunkByParagraphs:
    def test_respects_paragraph_boundaries(self):
        paras = ["Paragraph one with content."] * 3
        text = "\n\n".join(paras)
        chunks = chunk_by_paragraphs(text, max_chunk_size=100)
        assert len(chunks) >= 1

    def test_splits_large_paragraphs(self):
        large_para = " ".join(["word"] * 1000)
        chunks = chunk_by_paragraphs(large_para, max_chunk_size=200)
        assert len(chunks) >= 1
        total_words = sum(c["word_count"] for c in chunks)
        assert total_words >= 900

    def test_empty_returns_empty(self):
        assert chunk_by_paragraphs("") == []


class TestMergeSmallChunks:
    def test_merges_small_with_next(self):
        chunks = [
            {
                "text": "tiny",
                "word_count": 1,
                "char_count": 4,
                "start_pos": 0,
                "end_pos": 4,
                "chunk_id": "a",
            },
            {
                "text": " ".join(["word"] * 60),
                "word_count": 60,
                "char_count": 300,
                "start_pos": 5,
                "end_pos": 305,
                "chunk_id": "b",
            },
        ]
        merged = merge_small_chunks(chunks, min_size=10)
        assert len(merged) == 1
        assert "tiny" in merged[0]["text"]

    def test_keeps_large_chunks(self):
        chunks = [
            {
                "text": " ".join(["w"] * 100),
                "word_count": 100,
                "char_count": 200,
                "start_pos": 0,
                "end_pos": 200,
                "chunk_id": "a",
            },
            {
                "text": " ".join(["w"] * 100),
                "word_count": 100,
                "char_count": 200,
                "start_pos": 201,
                "end_pos": 401,
                "chunk_id": "b",
            },
        ]
        merged = merge_small_chunks(chunks, min_size=50)
        assert len(merged) == 2

    def test_empty_returns_empty(self):
        assert merge_small_chunks([]) == []
