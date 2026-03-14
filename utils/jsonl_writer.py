"""
JSONL (JSON Lines) file operations for storing document chunks.

This module provides functions for writing, appending, and validating chunks
in JSONL format - a format where each line is a valid JSON object, making it
efficient for streaming large datasets.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_chunk(
    chunk: dict[str, Any],
    required_fields: set[str] | None = None,
    strict: bool = False
) -> bool:
    """
    Validate that a chunk dictionary contains required fields.

    Args:
        chunk: Chunk dictionary to validate
        required_fields: Set of required field names (default: basic fields)
        strict: If True, raise ValueError on validation failure
                If False, just return False and log warning

    Returns:
        True if chunk is valid, False otherwise

    Raises:
        ValueError: If strict=True and validation fails
        TypeError: If chunk is not a dictionary

    Examples:
        >>> chunk = {'text': 'content', 'chunk_id': '123'}
        >>> validate_chunk(chunk)
        True
        >>> validate_chunk({'text': ''})
        False
    """
    # Check if chunk is a dictionary
    if not isinstance(chunk, dict):
        error_msg = f"Chunk must be a dictionary, got {type(chunk)}"
        logger.error(error_msg)
        if strict:
            raise TypeError(error_msg)
        return False

    # Default required fields
    if required_fields is None:
        required_fields = {'text', 'chunk_id'}

    # Check for required fields
    missing_fields = required_fields - set(chunk.keys())
    if missing_fields:
        error_msg = f"Chunk missing required fields: {missing_fields}"
        logger.warning(error_msg)
        if strict:
            raise ValueError(error_msg)
        return False

    # Check that text field is not empty
    if 'text' in chunk and not chunk['text']:
        error_msg = "Chunk 'text' field cannot be empty"
        logger.warning(error_msg)
        if strict:
            raise ValueError(error_msg)
        return False

    # Check that text is a string
    if 'text' in chunk and not isinstance(chunk['text'], str):
        error_msg = f"Chunk 'text' must be a string, got {type(chunk['text'])}"
        logger.warning(error_msg)
        if strict:
            raise ValueError(error_msg)
        return False

    # Validate chunk_id if present
    if 'chunk_id' in chunk:
        if not chunk['chunk_id']:
            error_msg = "Chunk 'chunk_id' cannot be empty"
            logger.warning(error_msg)
            if strict:
                raise ValueError(error_msg)
            return False

        if not isinstance(chunk['chunk_id'], str):
            error_msg = f"Chunk 'chunk_id' must be a string, got {type(chunk['chunk_id'])}"
            logger.warning(error_msg)
            if strict:
                raise ValueError(error_msg)
            return False

    # Validate numeric fields if present
    numeric_fields = ['word_count', 'char_count', 'chunk_index', 'total_chunks']
    for field in numeric_fields:
        if field in chunk:
            if not isinstance(chunk[field], (int, float)):
                error_msg = f"Chunk '{field}' must be numeric, got {type(chunk[field])}"
                logger.warning(error_msg)
                if strict:
                    raise ValueError(error_msg)
                return False

            if chunk[field] < 0:
                error_msg = f"Chunk '{field}' cannot be negative: {chunk[field]}"
                logger.warning(error_msg)
                if strict:
                    raise ValueError(error_msg)
                return False

    logger.debug(f"Chunk validation passed: {chunk.get('chunk_id', 'unknown')}")
    return True


def write_jsonl(
    chunks: list[dict[str, Any]],
    output_path: str,
    validate: bool = True,
    overwrite: bool = False,
    encoding: str = 'utf-8'
) -> bool:
    """
    Write a list of chunks to a JSONL file.

    Each chunk is written as a separate JSON object on its own line.
    Validates chunks before writing if validate=True.

    Args:
        chunks: List of chunk dictionaries to write
        output_path: Path to output JSONL file
        validate: Whether to validate chunks before writing (default: True)
        overwrite: Whether to overwrite existing file (default: False)
        encoding: File encoding (default: 'utf-8')

    Returns:
        True if write was successful, False otherwise

    Raises:
        FileExistsError: If file exists and overwrite=False
        ValueError: If chunks validation fails (when validate=True)
        IOError: If file cannot be written

    Examples:
        >>> chunks = [
        ...     {'text': 'chunk 1', 'chunk_id': '1'},
        ...     {'text': 'chunk 2', 'chunk_id': '2'}
        ... ]
        >>> write_jsonl(chunks, '/path/to/output.jsonl')
        True
    """
    if not chunks:
        logger.warning("No chunks provided to write_jsonl")
        return False

    # Validate output path
    output_file = Path(output_path)

    # Check if file exists
    if output_file.exists() and not overwrite:
        error_msg = f"File already exists: {output_path}. Use overwrite=True to replace."
        logger.error(error_msg)
        raise FileExistsError(error_msg)

    # Create parent directories if they don't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Validate all chunks before writing
    if validate:
        logger.info(f"Validating {len(chunks)} chunks before writing")
        invalid_chunks = []

        for i, chunk in enumerate(chunks):
            if not validate_chunk(chunk, strict=False):
                invalid_chunks.append(i)

        if invalid_chunks:
            error_msg = f"Found {len(invalid_chunks)} invalid chunks at indices: {invalid_chunks[:10]}"
            if len(invalid_chunks) > 10:
                error_msg += f" ... and {len(invalid_chunks) - 10} more"
            logger.error(error_msg)
            raise ValueError(error_msg)

    # Write chunks to file
    try:
        written_count = 0

        with open(output_file, 'w', encoding=encoding) as f:
            for i, chunk in enumerate(chunks):
                try:
                    # Write chunk as JSON line
                    json_line = json.dumps(chunk, ensure_ascii=False)
                    f.write(json_line + '\n')
                    written_count += 1

                except (TypeError, ValueError) as e:
                    logger.error(f"Failed to serialize chunk {i}: {e}")
                    logger.debug(f"Problematic chunk: {chunk}")
                    raise ValueError(f"Failed to serialize chunk {i}: {e}")

        logger.info(f"Successfully wrote {written_count} chunks to {output_path}")
        logger.info(f"File size: {output_file.stat().st_size} bytes")

        return True

    except OSError as e:
        logger.error(f"Failed to write to {output_path}: {e}")
        raise OSError(f"Failed to write to {output_path}: {e}")

    except Exception as e:
        logger.error(f"Unexpected error writing JSONL: {e}")
        raise


def append_jsonl(
    chunk: dict[str, Any],
    output_path: str,
    validate: bool = True,
    encoding: str = 'utf-8'
) -> bool:
    """
    Append a single chunk to an existing JSONL file.

    Creates the file if it doesn't exist. Validates chunk before appending
    if validate=True.

    Args:
        chunk: Chunk dictionary to append
        output_path: Path to JSONL file
        validate: Whether to validate chunk before appending (default: True)
        encoding: File encoding (default: 'utf-8')

    Returns:
        True if append was successful, False otherwise

    Raises:
        ValueError: If chunk validation fails (when validate=True)
        IOError: If file cannot be written

    Examples:
        >>> chunk = {'text': 'new chunk', 'chunk_id': '3'}
        >>> append_jsonl(chunk, '/path/to/output.jsonl')
        True
    """
    # Validate chunk
    if validate:
        if not validate_chunk(chunk, strict=True):
            return False

    # Validate output path
    output_file = Path(output_path)

    # Create parent directories if they don't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Append chunk to file
    try:
        with open(output_file, 'a', encoding=encoding) as f:
            json_line = json.dumps(chunk, ensure_ascii=False)
            f.write(json_line + '\n')

        logger.debug(f"Appended chunk {chunk.get('chunk_id', 'unknown')} to {output_path}")

        return True

    except (TypeError, ValueError) as e:
        logger.error(f"Failed to serialize chunk: {e}")
        raise ValueError(f"Failed to serialize chunk: {e}")

    except OSError as e:
        logger.error(f"Failed to append to {output_path}: {e}")
        raise OSError(f"Failed to append to {output_path}: {e}")

    except Exception as e:
        logger.error(f"Unexpected error appending to JSONL: {e}")
        raise


def read_jsonl(
    input_path: str,
    validate: bool = True,
    encoding: str = 'utf-8',
    skip_invalid: bool = False
) -> list[dict[str, Any]]:
    """
    Read chunks from a JSONL file.

    Args:
        input_path: Path to input JSONL file
        validate: Whether to validate chunks after reading (default: True)
        encoding: File encoding (default: 'utf-8')
        skip_invalid: If True, skip invalid chunks; if False, raise error

    Returns:
        List of chunk dictionaries

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If validation fails and skip_invalid=False
        IOError: If file cannot be read

    Examples:
        >>> chunks = read_jsonl('/path/to/input.jsonl')
        >>> len(chunks)
        100
    """
    input_file = Path(input_path)

    # Check if file exists
    if not input_file.exists():
        error_msg = f"File not found: {input_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    chunks = []
    invalid_count = 0

    try:
        with open(input_file, encoding=encoding) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines
                if not line:
                    continue

                try:
                    # Parse JSON
                    chunk = json.loads(line)

                    # Validate if requested
                    if validate:
                        if not validate_chunk(chunk, strict=False):
                            invalid_count += 1
                            if skip_invalid:
                                logger.warning(f"Skipping invalid chunk at line {line_num}")
                                continue
                            else:
                                raise ValueError(f"Invalid chunk at line {line_num}")

                    chunks.append(chunk)

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON at line {line_num}: {e}")
                    if skip_invalid:
                        invalid_count += 1
                        continue
                    else:
                        raise ValueError(f"Failed to parse JSON at line {line_num}: {e}")

        logger.info(f"Read {len(chunks)} chunks from {input_path}")
        if invalid_count > 0:
            logger.warning(f"Skipped {invalid_count} invalid chunks")

        return chunks

    except OSError as e:
        logger.error(f"Failed to read from {input_path}: {e}")
        raise OSError(f"Failed to read from {input_path}: {e}")

    except Exception as e:
        logger.error(f"Unexpected error reading JSONL: {e}")
        raise


def count_chunks(input_path: str) -> int:
    """
    Count the number of chunks in a JSONL file without loading into memory.

    Efficient for large files.

    Args:
        input_path: Path to JSONL file

    Returns:
        Number of chunks (non-empty lines)

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    input_file = Path(input_path)

    if not input_file.exists():
        raise FileNotFoundError(f"File not found: {input_path}")

    count = 0
    with open(input_file, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                count += 1

    return count


def merge_jsonl_files(
    input_paths: list[str],
    output_path: str,
    validate: bool = True
) -> bool:
    """
    Merge multiple JSONL files into a single file.

    Args:
        input_paths: List of input JSONL file paths
        output_path: Path to output merged JSONL file
        validate: Whether to validate chunks (default: True)

    Returns:
        True if merge was successful

    Raises:
        FileNotFoundError: If any input file doesn't exist
    """
    all_chunks = []

    for input_path in input_paths:
        logger.info(f"Reading {input_path}")
        chunks = read_jsonl(input_path, validate=validate, skip_invalid=True)
        all_chunks.extend(chunks)

    logger.info(f"Merging {len(all_chunks)} total chunks into {output_path}")
    return write_jsonl(all_chunks, output_path, validate=validate, overwrite=True)


if __name__ == "__main__":
    # Example usage and testing
    import tempfile

    print("=" * 60)
    print("JSONL WRITER TESTING")
    print("=" * 60)

    # Create sample chunks
    sample_chunks = [
        {
            'text': 'This is the first chunk of text.',
            'chunk_id': 'chunk_001',
            'word_count': 7,
            'char_count': 33,
            'document_id': 'doc_123'
        },
        {
            'text': 'This is the second chunk with more content.',
            'chunk_id': 'chunk_002',
            'word_count': 8,
            'char_count': 44,
            'document_id': 'doc_123'
        },
        {
            'text': 'And here is the third and final chunk.',
            'chunk_id': 'chunk_003',
            'word_count': 8,
            'char_count': 39,
            'document_id': 'doc_123'
        }
    ]

    # Test validation
    print("\n1. Testing validation:")
    for chunk in sample_chunks:
        is_valid = validate_chunk(chunk)
        print(f"   Chunk {chunk['chunk_id']}: {'Valid' if is_valid else 'Invalid'}")

    # Test writing
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, 'test_output.jsonl')

        print(f"\n2. Writing chunks to {output_file}")
        success = write_jsonl(sample_chunks, output_file)
        print(f"   Write successful: {success}")

        # Test reading
        print("\n3. Reading chunks back:")
        read_chunks = read_jsonl(output_file)
        print(f"   Read {len(read_chunks)} chunks")

        # Test append
        print("\n4. Appending new chunk:")
        new_chunk = {
            'text': 'This is an appended chunk.',
            'chunk_id': 'chunk_004',
            'word_count': 5,
            'char_count': 27,
            'document_id': 'doc_123'
        }
        append_success = append_jsonl(new_chunk, output_file)
        print(f"   Append successful: {append_success}")

        # Test count
        print("\n5. Counting chunks:")
        total = count_chunks(output_file)
        print(f"   Total chunks in file: {total}")

        # Display file content
        print("\n6. File contents:")
        with open(output_file) as f:
            for i, line in enumerate(f, 1):
                chunk_preview = json.loads(line)
                print(f"   Line {i}: {chunk_preview['chunk_id']} - {chunk_preview['text'][:40]}...")
