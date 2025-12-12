"""
Text chunking utilities for splitting documents into manageable pieces.

This module provides functions for splitting text into chunks with overlap,
preserving logical sections, and maintaining metadata about chunk positions
and relationships.
"""

import re
import logging
from typing import List, Dict, Optional, Any
from uuid import uuid4

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
    page_info: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Split text into chunks of approximately chunk_size words with overlap.

    Attempts to split at logical boundaries (paragraphs, sentences) when possible
    to maintain semantic coherence. Each chunk includes metadata about its
    position and size.

    Args:
        text: Input text to chunk
        chunk_size: Target size of each chunk in words (default: 500)
        overlap: Number of overlapping words between chunks (default: 50)
        page_info: Optional dictionary with page information (page_num, total_pages)

    Returns:
        List of dictionaries, each containing:
        - text: The chunk text
        - chunk_id: Unique identifier for the chunk
        - word_count: Number of words in the chunk
        - char_count: Number of characters in the chunk
        - start_pos: Character position where chunk starts in original text
        - end_pos: Character position where chunk ends in original text
        - page_info: Page information if provided

    Examples:
        >>> text = "This is a test. " * 100
        >>> chunks = chunk_text(text, chunk_size=20, overlap=5)
        >>> len(chunks)
        5
        >>> chunks[0]['word_count']
        20
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for chunking")
        return []

    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be positive, got {chunk_size}")

    if overlap < 0:
        raise ValueError(f"overlap must be non-negative, got {overlap}")

    if overlap >= chunk_size:
        raise ValueError(f"overlap ({overlap}) must be less than chunk_size ({chunk_size})")

    # Split text into sentences for better boundary detection
    sentences = _split_into_sentences(text)

    chunks = []
    current_chunk_words = []
    current_chunk_sentences = []
    overlap_words = []
    char_position = 0

    for sentence in sentences:
        sentence_words = sentence.split()

        # Add sentence to current chunk
        current_chunk_words.extend(sentence_words)
        current_chunk_sentences.append(sentence)

        # Check if we've reached the target chunk size
        if len(current_chunk_words) >= chunk_size:
            # Create chunk
            chunk_text = ' '.join(current_chunk_sentences)
            chunk_start_pos = char_position
            chunk_end_pos = chunk_start_pos + len(chunk_text)

            chunk_data = {
                'text': chunk_text,
                'chunk_id': str(uuid4()),
                'word_count': len(current_chunk_words),
                'char_count': len(chunk_text),
                'start_pos': chunk_start_pos,
                'end_pos': chunk_end_pos,
            }

            if page_info:
                chunk_data['page_info'] = page_info

            chunks.append(chunk_data)

            # Update character position
            char_position = chunk_end_pos + 1  # +1 for space between chunks

            # Prepare overlap for next chunk
            if overlap > 0:
                # Take last 'overlap' words for next chunk
                overlap_words = current_chunk_words[-overlap:]
                overlap_sentences = []

                # Reconstruct sentences from overlap words
                overlap_text = ' '.join(overlap_words)
                overlap_sentences = [overlap_text]

                current_chunk_words = overlap_words.copy()
                current_chunk_sentences = overlap_sentences
            else:
                current_chunk_words = []
                current_chunk_sentences = []

    # Handle remaining text (last chunk)
    if current_chunk_words:
        chunk_text = ' '.join(current_chunk_sentences)
        chunk_start_pos = char_position
        chunk_end_pos = chunk_start_pos + len(chunk_text)

        chunk_data = {
            'text': chunk_text,
            'chunk_id': str(uuid4()),
            'word_count': len(current_chunk_words),
            'char_count': len(chunk_text),
            'start_pos': chunk_start_pos,
            'end_pos': chunk_end_pos,
        }

        if page_info:
            chunk_data['page_info'] = page_info

        chunks.append(chunk_data)

    logger.info(f"Created {len(chunks)} chunks from text of {len(text)} characters")

    return chunks


def _split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences using regex patterns.

    Handles common sentence boundaries while avoiding false positives
    (e.g., abbreviations, decimals).

    Args:
        text: Input text to split

    Returns:
        List of sentences
    """
    # Pattern for sentence boundaries
    # Looks for . ! ? followed by whitespace and capital letter
    sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])'

    sentences = re.split(sentence_pattern, text)

    # Filter out empty sentences and strip whitespace
    sentences = [s.strip() for s in sentences if s.strip()]

    # If no sentences were detected, treat entire text as one sentence
    if not sentences:
        sentences = [text.strip()]

    return sentences


def create_chunks_with_metadata(
    text: str,
    document_metadata: Dict[str, Any],
    chunk_size: int = 500,
    overlap: int = 50
) -> List[Dict[str, Any]]:
    """
    Create chunks with comprehensive metadata for document processing pipelines.

    Generates chunks with full metadata including document information,
    chunk position, and relationships between chunks.

    Args:
        text: Input text to chunk
        document_metadata: Document-level metadata to include with each chunk
            Expected keys: document_id, filename, document_type, etc.
        chunk_size: Target size of each chunk in words (default: 500)
        overlap: Number of overlapping words between chunks (default: 50)

    Returns:
        List of dictionaries with comprehensive metadata:
        - All fields from chunk_text()
        - document_id: ID of source document
        - filename: Name of source file
        - chunk_index: Sequential index of chunk in document
        - total_chunks: Total number of chunks in document
        - has_next: Boolean indicating if there's a next chunk
        - has_previous: Boolean indicating if there's a previous chunk
        - All additional fields from document_metadata

    Examples:
        >>> metadata = {
        ...     'document_id': 'doc_123',
        ...     'filename': 'report.pdf',
        ...     'document_type': 'legal'
        ... }
        >>> chunks = create_chunks_with_metadata(text, metadata, chunk_size=500)
        >>> chunks[0]['document_id']
        'doc_123'
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for chunking with metadata")
        return []

    if not document_metadata:
        logger.warning("No document metadata provided")
        document_metadata = {}

    # Validate required metadata fields
    if 'document_id' not in document_metadata:
        logger.warning("document_id not in metadata, generating one")
        document_metadata['document_id'] = str(uuid4())

    # Extract page info if available
    page_info = None
    if 'page_num' in document_metadata or 'page_number' in document_metadata:
        page_info = {
            'page_num': document_metadata.get('page_num') or document_metadata.get('page_number'),
            'total_pages': document_metadata.get('total_pages', None)
        }

    # Create base chunks
    base_chunks = chunk_text(
        text=text,
        chunk_size=chunk_size,
        overlap=overlap,
        page_info=page_info
    )

    # Enhance chunks with metadata
    total_chunks = len(base_chunks)
    enhanced_chunks = []

    for index, chunk in enumerate(base_chunks):
        # Create enhanced chunk with all metadata
        enhanced_chunk = {
            **chunk,  # Include all base chunk fields
            **document_metadata,  # Include all document metadata
            'chunk_index': index,
            'total_chunks': total_chunks,
            'has_next': index < total_chunks - 1,
            'has_previous': index > 0,
        }

        # Add page range if processing multi-page document
        if page_info:
            enhanced_chunk['page_start'] = page_info['page_num']
            enhanced_chunk['page_end'] = page_info['page_num']

        # Add relationship information
        if index > 0:
            enhanced_chunk['previous_chunk_id'] = base_chunks[index - 1]['chunk_id']

        if index < total_chunks - 1:
            enhanced_chunk['next_chunk_id'] = base_chunks[index + 1]['chunk_id']

        enhanced_chunks.append(enhanced_chunk)

    logger.info(
        f"Created {len(enhanced_chunks)} chunks with metadata "
        f"for document {document_metadata.get('document_id', 'unknown')}"
    )

    return enhanced_chunks


def chunk_by_paragraphs(
    text: str,
    max_chunk_size: int = 500,
    min_chunk_size: int = 100
) -> List[Dict[str, Any]]:
    """
    Split text into chunks based on paragraph boundaries.

    Groups paragraphs together until max_chunk_size is reached,
    while respecting logical paragraph boundaries. Useful for
    documents where paragraph structure is important.

    Args:
        text: Input text to chunk
        max_chunk_size: Maximum size of each chunk in words
        min_chunk_size: Minimum size before creating new chunk

    Returns:
        List of chunk dictionaries

    Examples:
        >>> text = "Para 1.\\n\\nPara 2.\\n\\nPara 3."
        >>> chunks = chunk_by_paragraphs(text, max_chunk_size=20)
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for paragraph chunking")
        return []

    # Split into paragraphs
    paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks = []
    current_chunk_paras = []
    current_word_count = 0
    char_position = 0

    for para in paragraphs:
        para_word_count = len(para.split())

        # If single paragraph exceeds max_chunk_size, split it
        if para_word_count > max_chunk_size:
            # Save current chunk if exists
            if current_chunk_paras:
                chunk_text = '\n\n'.join(current_chunk_paras)
                chunks.append({
                    'text': chunk_text,
                    'chunk_id': str(uuid4()),
                    'word_count': current_word_count,
                    'char_count': len(chunk_text),
                    'start_pos': char_position,
                    'end_pos': char_position + len(chunk_text),
                })
                char_position += len(chunk_text) + 2
                current_chunk_paras = []
                current_word_count = 0

            # Split large paragraph using word-based chunking
            para_chunks = chunk_text(para, chunk_size=max_chunk_size, overlap=0)
            chunks.extend(para_chunks)
            char_position += len(para) + 2

        # If adding paragraph would exceed max_chunk_size, create chunk
        elif current_word_count + para_word_count > max_chunk_size and current_word_count >= min_chunk_size:
            chunk_text = '\n\n'.join(current_chunk_paras)
            chunks.append({
                'text': chunk_text,
                'chunk_id': str(uuid4()),
                'word_count': current_word_count,
                'char_count': len(chunk_text),
                'start_pos': char_position,
                'end_pos': char_position + len(chunk_text),
            })
            char_position += len(chunk_text) + 2

            # Start new chunk with current paragraph
            current_chunk_paras = [para]
            current_word_count = para_word_count

        else:
            # Add paragraph to current chunk
            current_chunk_paras.append(para)
            current_word_count += para_word_count

    # Handle remaining paragraphs
    if current_chunk_paras:
        chunk_text = '\n\n'.join(current_chunk_paras)
        chunks.append({
            'text': chunk_text,
            'chunk_id': str(uuid4()),
            'word_count': current_word_count,
            'char_count': len(chunk_text),
            'start_pos': char_position,
            'end_pos': char_position + len(chunk_text),
        })

    logger.info(f"Created {len(chunks)} paragraph-based chunks")

    return chunks


def merge_small_chunks(
    chunks: List[Dict[str, Any]],
    min_size: int = 50
) -> List[Dict[str, Any]]:
    """
    Merge chunks that are smaller than min_size with adjacent chunks.

    Useful for post-processing to ensure no chunks are too small.

    Args:
        chunks: List of chunk dictionaries
        min_size: Minimum word count for a chunk

    Returns:
        List of merged chunks
    """
    if not chunks:
        return []

    merged_chunks = []
    i = 0

    while i < len(chunks):
        current_chunk = chunks[i]

        # If chunk is too small and not the last chunk
        if current_chunk['word_count'] < min_size and i < len(chunks) - 1:
            # Merge with next chunk
            next_chunk = chunks[i + 1]
            merged_text = current_chunk['text'] + ' ' + next_chunk['text']

            merged_chunk = {
                'text': merged_text,
                'chunk_id': str(uuid4()),
                'word_count': current_chunk['word_count'] + next_chunk['word_count'],
                'char_count': len(merged_text),
                'start_pos': current_chunk['start_pos'],
                'end_pos': next_chunk['end_pos'],
            }

            # Preserve other metadata if present
            for key in current_chunk:
                if key not in merged_chunk:
                    merged_chunk[key] = current_chunk[key]

            merged_chunks.append(merged_chunk)
            i += 2  # Skip next chunk as it's been merged
        else:
            merged_chunks.append(current_chunk)
            i += 1

    logger.info(f"Merged {len(chunks) - len(merged_chunks)} small chunks")

    return merged_chunks


if __name__ == "__main__":
    # Example usage and testing
    sample_text = """
    This is the first paragraph. It contains some important information.

    This is the second paragraph. It has more details about the topic. We want to ensure
    that the chunking algorithm properly handles paragraph boundaries and creates
    meaningful chunks.

    Here's a third paragraph with additional content. The algorithm should split this
    text into reasonable chunks that maintain semantic coherence.
    """ * 5

    print("=" * 60)
    print("BASIC CHUNKING")
    print("=" * 60)

    chunks = chunk_text(sample_text, chunk_size=100, overlap=20)
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i + 1}:")
        print(f"  Word count: {chunk['word_count']}")
        print(f"  Char count: {chunk['char_count']}")
        print(f"  Start pos: {chunk['start_pos']}")
        print(f"  Preview: {chunk['text'][:100]}...")

    print("\n" + "=" * 60)
    print("CHUNKING WITH METADATA")
    print("=" * 60)

    metadata = {
        'document_id': 'test_doc_001',
        'filename': 'sample.txt',
        'document_type': 'text',
        'author': 'Test Author'
    }

    metadata_chunks = create_chunks_with_metadata(
        sample_text, metadata, chunk_size=100, overlap=20
    )

    for i, chunk in enumerate(metadata_chunks[:2]):  # Show first 2
        print(f"\nChunk {i + 1}:")
        print(f"  Document ID: {chunk['document_id']}")
        print(f"  Filename: {chunk['filename']}")
        print(f"  Chunk index: {chunk['chunk_index']} / {chunk['total_chunks']}")
        print(f"  Has next: {chunk['has_next']}")
        print(f"  Word count: {chunk['word_count']}")
