import json
from pathlib import Path

import pytest

from utils.jsonl_writer import (
    append_jsonl,
    count_chunks,
    merge_jsonl_files,
    read_jsonl,
    validate_chunk,
    write_jsonl,
)


@pytest.fixture
def sample_chunks():
    return [
        {"text": "First chunk content.", "chunk_id": "c001", "word_count": 3, "char_count": 20},
        {"text": "Second chunk content.", "chunk_id": "c002", "word_count": 3, "char_count": 21},
        {"text": "Third chunk content.", "chunk_id": "c003", "word_count": 3, "char_count": 20},
    ]


@pytest.fixture
def tmp_jsonl(tmp_path):
    return str(tmp_path / "output.jsonl")


class TestValidateChunk:
    def test_valid_chunk(self):
        assert validate_chunk({"text": "hello", "chunk_id": "1"}) is True

    def test_missing_text(self):
        assert validate_chunk({"chunk_id": "1"}) is False

    def test_missing_chunk_id(self):
        assert validate_chunk({"text": "hello"}) is False

    def test_empty_text(self):
        assert validate_chunk({"text": "", "chunk_id": "1"}) is False

    def test_non_dict_input(self):
        assert validate_chunk("not a dict") is False
        assert validate_chunk(42) is False

    def test_strict_mode_raises(self):
        with pytest.raises(TypeError):
            validate_chunk("bad", strict=True)
        with pytest.raises(ValueError):
            validate_chunk({"text": "", "chunk_id": "1"}, strict=True)

    def test_negative_numeric_field(self):
        chunk = {"text": "ok", "chunk_id": "1", "word_count": -5}
        assert validate_chunk(chunk) is False

    def test_custom_required_fields(self):
        chunk = {"text": "ok", "chunk_id": "1"}
        assert validate_chunk(chunk, required_fields={"text", "chunk_id", "source"}) is False


class TestWriteJsonl:
    def test_writes_chunks(self, sample_chunks, tmp_jsonl):
        assert write_jsonl(sample_chunks, tmp_jsonl) is True
        with open(tmp_jsonl) as f:
            lines = f.readlines()
        assert len(lines) == 3
        for line in lines:
            obj = json.loads(line)
            assert "text" in obj

    def test_refuses_overwrite_by_default(self, sample_chunks, tmp_jsonl):
        write_jsonl(sample_chunks, tmp_jsonl)
        with pytest.raises(FileExistsError):
            write_jsonl(sample_chunks, tmp_jsonl)

    def test_allows_overwrite(self, sample_chunks, tmp_jsonl):
        write_jsonl(sample_chunks, tmp_jsonl)
        assert write_jsonl(sample_chunks, tmp_jsonl, overwrite=True) is True

    def test_empty_chunks_returns_false(self, tmp_jsonl):
        assert write_jsonl([], tmp_jsonl) is False

    def test_creates_parent_dirs(self, sample_chunks, tmp_path):
        deep_path = str(tmp_path / "a" / "b" / "c" / "output.jsonl")
        assert write_jsonl(sample_chunks, deep_path) is True
        assert Path(deep_path).exists()

    def test_validation_rejects_bad_chunks(self, tmp_jsonl):
        bad_chunks = [{"text": "", "chunk_id": "1"}]
        with pytest.raises(ValueError):
            write_jsonl(bad_chunks, tmp_jsonl, validate=True)

    def test_skip_validation(self, tmp_jsonl):
        weird_chunks = [{"text": "", "chunk_id": "1"}]
        assert write_jsonl(weird_chunks, tmp_jsonl, validate=False) is True


class TestAppendJsonl:
    def test_appends_to_existing(self, sample_chunks, tmp_jsonl):
        write_jsonl(sample_chunks, tmp_jsonl)
        new_chunk = {"text": "Appended.", "chunk_id": "c004"}
        assert append_jsonl(new_chunk, tmp_jsonl) is True
        assert count_chunks(tmp_jsonl) == 4

    def test_creates_new_file(self, tmp_jsonl):
        chunk = {"text": "First.", "chunk_id": "c001"}
        assert append_jsonl(chunk, tmp_jsonl) is True
        assert count_chunks(tmp_jsonl) == 1


class TestReadJsonl:
    def test_reads_written_chunks(self, sample_chunks, tmp_jsonl):
        write_jsonl(sample_chunks, tmp_jsonl)
        read = read_jsonl(tmp_jsonl)
        assert len(read) == 3
        assert read[0]["chunk_id"] == "c001"

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            read_jsonl("/nonexistent/path.jsonl")

    def test_skip_invalid_lines(self, tmp_jsonl):
        with open(tmp_jsonl, "w") as f:
            f.write('{"text": "ok", "chunk_id": "1"}\n')
            f.write("not valid json\n")
            f.write('{"text": "also ok", "chunk_id": "2"}\n')
        chunks = read_jsonl(tmp_jsonl, skip_invalid=True)
        assert len(chunks) == 2


class TestCountChunks:
    def test_counts_lines(self, sample_chunks, tmp_jsonl):
        write_jsonl(sample_chunks, tmp_jsonl)
        assert count_chunks(tmp_jsonl) == 3

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            count_chunks("/nonexistent.jsonl")


class TestMergeJsonlFiles:
    def test_merges_multiple_files(self, sample_chunks, tmp_path):
        f1 = str(tmp_path / "a.jsonl")
        f2 = str(tmp_path / "b.jsonl")
        out = str(tmp_path / "merged.jsonl")
        write_jsonl(sample_chunks[:2], f1)
        write_jsonl(sample_chunks[2:], f2)
        assert merge_jsonl_files([f1, f2], out) is True
        assert count_chunks(out) == 3
