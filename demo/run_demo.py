#!/usr/bin/env python3
"""Demo script showing the RAG pipeline processing a local document end-to-end."""

import json
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging

logging.disable(logging.CRITICAL)

from processors.html_processor import process_html  # noqa: E402
from utils.chunking import create_chunks_with_metadata  # noqa: E402
from utils.jsonl_writer import read_jsonl, write_jsonl  # noqa: E402
from utils.text_cleaning import clean_text, detect_language  # noqa: E402


def print_slow(text, delay=0.02):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def print_header(text):
    print()
    print(f"\033[1;36m{'─' * 60}\033[0m")
    print(f"\033[1;36m  {text}\033[0m")
    print(f"\033[1;36m{'─' * 60}\033[0m")
    time.sleep(0.3)


def main():
    demo_dir = Path(__file__).parent
    sample_html = demo_dir / "sample.html"
    output_jsonl = demo_dir / "output" / "demo_doc.jsonl"

    print("\033[1;33m")
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║     rag-document-pipeline  —  Demo          ║")
    print("  ║     Multi-format RAG preprocessing          ║")
    print("  ╚══════════════════════════════════════════════╝")
    print("\033[0m")
    time.sleep(1)

    # Step 1: Extract
    print_header("Step 1: Extract text from HTML document")
    print(f"  Input: {sample_html.name}")
    time.sleep(0.5)

    metadata = {
        "document_id": "pref92_renewal_guide",
        "document_type": "html",
        "category": "residence_permit",
        "jurisdiction": "Hauts-de-Seine",
        "authority_score": 5,
        "language": "en",
        "date": "2025-01-15",
        "source_url": "https://prefecture92.gouv.fr/renewal-guide",
    }

    result = process_html(str(sample_html), metadata)
    print(f"  Status: \033[1;32m{result['status']}\033[0m")
    print(f"  Characters extracted: {result['metadata']['total_chars']}")
    print(f'  Preview: "{result["text"][:80]}..."')
    time.sleep(0.8)

    # Step 2: Clean
    print_header("Step 2: Clean and normalize text")
    raw_len = len(result["text"])
    cleaned = clean_text(result["text"])
    lang = detect_language(cleaned)
    print(f"  Raw: {raw_len} chars → Cleaned: {len(cleaned)} chars")
    print(f"  Language detected: \033[1;33m{lang}\033[0m")
    print("  Boilerplate removed, whitespace normalized, dates standardized")
    time.sleep(0.8)

    # Step 3: Chunk
    print_header("Step 3: Chunk with overlap (500 words, 50 overlap)")
    chunks = create_chunks_with_metadata(
        cleaned,
        document_metadata=metadata,
        chunk_size=150,  # smaller for demo visibility
        overlap=30,
    )
    print(f"  Created \033[1;32m{len(chunks)} chunks\033[0m from document")
    for i, chunk in enumerate(chunks):
        words = chunk["word_count"]
        has_next = "→" if chunk["has_next"] else "⏹"
        has_prev = "←" if chunk["has_previous"] else "⏹"
        print(
            f'    Chunk {i + 1}: {words} words  [{has_prev}|{has_next}]  "{chunk["text"][:50]}..."'
        )
    time.sleep(0.8)

    # Step 4: Write JSONL
    print_header("Step 4: Write metadata-enriched JSONL")
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(chunks, str(output_jsonl), overwrite=True)
    file_size = output_jsonl.stat().st_size
    print(f"  Output: {output_jsonl}")
    print(f"  File size: {file_size:,} bytes")
    print(f"  Lines: {len(chunks)} (one JSON object per line)")
    time.sleep(0.5)

    # Show a sample chunk
    print()
    print("  \033[1;35mSample JSONL entry:\033[0m")
    loaded = read_jsonl(str(output_jsonl))
    sample = {
        k: v
        for k, v in loaded[0].items()
        if k
        in [
            "chunk_id",
            "text",
            "document_id",
            "category",
            "jurisdiction",
            "authority_score",
            "word_count",
        ]
    }
    sample["text"] = sample["text"][:60] + "..."
    print(f"  {json.dumps(sample, indent=2)}")
    time.sleep(0.8)

    # Summary
    print_header("Pipeline complete")
    print(f"  Document: {metadata['document_id']}")
    print("  Source:   HTML → Extract → Clean → Chunk → JSONL")
    print(f"  Output:   {len(chunks)} chunks ready for vector DB embedding")
    print("  Metadata: category, jurisdiction, authority_score propagated")
    print()
    print("  \033[1;32m✓ Ready for embedding and retrieval\033[0m")
    print()

    # Cleanup
    output_jsonl.unlink(missing_ok=True)
    output_jsonl.parent.rmdir()


if __name__ == "__main__":
    main()
