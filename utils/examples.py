"""
Example Usage Scripts

Demonstrates how to use the GDriveClient and MetadataManager modules.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

from gdrive_client import GDriveClient, GDriveClientError
from metadata_manager import MetadataManager, MetadataError


def example_gdrive_basic_usage():
    """Example: Basic Google Drive operations."""
    print("\n=== Google Drive Client - Basic Usage ===\n")

    # Load environment variables
    load_dotenv()

    try:
        # Initialize client
        client = GDriveClient()
        print("✓ Google Drive client initialized")

        # Extract file ID from link
        drive_link = "https://drive.google.com/file/d/1abc123xyz/view"
        file_id = client.get_file_id_from_link(drive_link)
        print(f"✓ Extracted file ID: {file_id}")

        # Download file (example - will fail if file doesn't exist)
        # output_path = "/tmp/downloaded_document.pdf"
        # downloaded_file = client.download_file(drive_link, output_path)
        # print(f"✓ Downloaded file to: {downloaded_file}")

        # Upload file (example)
        # file_to_upload = "/path/to/local/file.pdf"
        # folder_id = os.getenv('GDRIVE_PDFS_FOLDER_ID')
        # uploaded_file_id = client.upload_file(file_to_upload, folder_id)
        # print(f"✓ Uploaded file ID: {uploaded_file_id}")

    except GDriveClientError as e:
        print(f"✗ Error: {e}")


def example_metadata_basic_usage():
    """Example: Basic metadata operations."""
    print("\n=== Metadata Manager - Basic Usage ===\n")

    # Create sample metadata file
    metadata_file = "/tmp/sample_metadata.json"

    try:
        # Initialize manager (creates file if doesn't exist)
        manager = MetadataManager(metadata_file)
        print(f"✓ Metadata manager initialized: {metadata_file}")

        # Add a new document
        new_document = {
            "document_id": "pref92_visa2025",
            "document_type": "pdf",
            "drive_link": "https://drive.google.com/file/d/1abc123/view",
            "source_url": "https://prefecture92.gouv.fr/visa-renewal",
            "category": "titre_sejour",
            "sub_category": "delai_renouvellement",
            "jurisdiction": "Hauts-de-Seine",
            "date": "2025-01-10",
            "authority_score": 3,
            "language": "fr"
        }

        manager.add_document(new_document)
        print(f"✓ Added document: {new_document['document_id']}")

        # Save metadata
        manager.save()
        print("✓ Metadata saved")

        # Get pending documents
        pending = manager.get_pending_documents()
        print(f"✓ Found {len(pending)} pending documents")

        # Update document status
        manager.update_document_status(
            "pref92_visa2025",
            jsonl_ready=True,
            embedding_done=False,
            chunk_count=25
        )
        print("✓ Updated document status")

        # Get document
        doc = manager.get_document("pref92_visa2025")
        print(f"✓ Retrieved document: {doc['document_id']}")
        print(f"  - Category: {doc['category']}")
        print(f"  - JSONL ready: {doc['jsonl_ready']}")
        print(f"  - Chunk count: {doc['chunk_count']}")

        # Get statistics
        stats = manager.get_statistics()
        print("\n✓ Metadata statistics:")
        print(f"  - Total documents: {stats['total_documents']}")
        print(f"  - Pending: {stats['pending_documents']}")
        print(f"  - JSONL ready: {stats['jsonl_ready_count']}")

        # Save changes
        manager.save()
        print("\n✓ All changes saved")

    except MetadataError as e:
        print(f"✗ Error: {e}")


def example_complete_workflow():
    """Example: Complete document processing workflow."""
    print("\n=== Complete Workflow Example ===\n")

    load_dotenv()

    # Paths
    metadata_file = "/tmp/workflow_metadata.json"
    download_dir = Path("/tmp/downloads")
    download_dir.mkdir(exist_ok=True)

    try:
        # Initialize managers
        gdrive = GDriveClient()
        metadata = MetadataManager(metadata_file)

        print("✓ Initialized GDrive client and metadata manager")

        # Add sample documents
        documents = [
            {
                "document_id": "pref75_titre2025",
                "document_type": "pdf",
                "drive_link": "https://drive.google.com/file/d/sample1/view",
                "source_url": "https://prefecture75.gouv.fr/titre",
                "category": "titre_sejour",
                "sub_category": "renouvellement",
                "jurisdiction": "Paris",
                "date": "2025-12-12",
                "authority_score": 4,
                "language": "fr"
            },
            {
                "document_id": "pref92_visa2025",
                "document_type": "html",
                "drive_link": "https://drive.google.com/file/d/sample2/view",
                "source_url": "https://prefecture92.gouv.fr/visa",
                "category": "visa",
                "sub_category": "etudiant",
                "jurisdiction": "Hauts-de-Seine",
                "date": "2025-12-10",
                "authority_score": 3,
                "language": "fr"
            }
        ]

        for doc in documents:
            metadata.add_document(doc)
            print(f"✓ Added document: {doc['document_id']}")

        metadata.save()
        print(f"\n✓ Added {len(documents)} documents to metadata")

        # Process pending documents
        pending = metadata.get_pending_documents()
        print(f"\n✓ Found {len(pending)} pending documents to process")

        for doc in pending:
            doc_id = doc['document_id']
            print(f"\nProcessing: {doc_id}")

            try:
                # In a real workflow, you would:
                # 1. Download file from Drive
                # output_path = download_dir / f"{doc_id}.{doc['document_type']}"
                # gdrive.download_file(doc['drive_link'], str(output_path))
                # print(f"  ✓ Downloaded to: {output_path}")

                # 2. Extract and clean text
                # text = extract_text(output_path)
                # print(f"  ✓ Extracted text")

                # 3. Chunk text
                # chunks = chunk_text(text, chunk_size=500, overlap=50)
                # print(f"  ✓ Created {len(chunks)} chunks")

                # 4. Generate JSONL
                # jsonl_path = create_jsonl(chunks, doc)
                # print(f"  ✓ Generated JSONL: {jsonl_path}")

                # 5. Upload JSONL to Drive
                # folder_id = os.getenv('GDRIVE_JSONL_FOLDER_ID')
                # uploaded_id = gdrive.upload_file(jsonl_path, folder_id)
                # print(f"  ✓ Uploaded JSONL to Drive: {uploaded_id}")

                # 6. Update metadata
                metadata.update_document_status(
                    doc_id,
                    jsonl_ready=True,
                    embedding_done=False,
                    chunk_count=0  # Would be actual chunk count
                )
                print(f"  ✓ Updated status: jsonl_ready=True")

            except Exception as e:
                print(f"  ✗ Error processing {doc_id}: {e}")
                continue

        # Save all updates
        metadata.save()
        print("\n✓ Workflow complete - all metadata saved")

        # Show final statistics
        stats = metadata.get_statistics()
        print("\n=== Final Statistics ===")
        print(f"Total documents: {stats['total_documents']}")
        print(f"Pending: {stats['pending_documents']}")
        print(f"JSONL ready: {stats['jsonl_ready_count']}")
        print(f"Embeddings done: {stats['embedding_done_count']}")

    except Exception as e:
        print(f"✗ Workflow error: {e}")


def example_metadata_queries():
    """Example: Advanced metadata queries."""
    print("\n=== Metadata Manager - Advanced Queries ===\n")

    metadata_file = "/tmp/advanced_metadata.json"

    try:
        manager = MetadataManager(metadata_file)

        # Add sample documents with different categories
        sample_docs = [
            {
                "document_id": "doc_paris_titre_001",
                "document_type": "pdf",
                "drive_link": "https://drive.google.com/file/d/1/view",
                "source_url": "https://example.com/1",
                "category": "titre_sejour",
                "jurisdiction": "Paris",
                "date": "2025-01-15",
                "authority_score": 5,
                "language": "fr"
            },
            {
                "document_id": "doc_paris_visa_001",
                "document_type": "html",
                "drive_link": "https://drive.google.com/file/d/2/view",
                "source_url": "https://example.com/2",
                "category": "visa",
                "jurisdiction": "Paris",
                "date": "2025-02-10",
                "authority_score": 4,
                "language": "fr"
            },
            {
                "document_id": "doc_lyon_titre_001",
                "document_type": "pdf",
                "drive_link": "https://drive.google.com/file/d/3/view",
                "source_url": "https://example.com/3",
                "category": "titre_sejour",
                "jurisdiction": "Lyon",
                "date": "2025-03-05",
                "authority_score": 3,
                "language": "fr"
            }
        ]

        for doc in sample_docs:
            manager.add_document(doc)

        manager.save()
        print(f"✓ Added {len(sample_docs)} sample documents\n")

        # Query by category
        titre_docs = manager.get_documents_by_category("titre_sejour")
        print(f"Titre de séjour documents: {len(titre_docs)}")
        for doc in titre_docs:
            print(f"  - {doc['document_id']} ({doc['jurisdiction']})")

        # Query by jurisdiction
        print()
        paris_docs = manager.get_documents_by_jurisdiction("Paris")
        print(f"Paris documents: {len(paris_docs)}")
        for doc in paris_docs:
            print(f"  - {doc['document_id']} ({doc['category']})")

        # Get all documents
        print()
        all_docs = manager.get_all_documents()
        print(f"Total documents: {len(all_docs)}")

        # Get statistics
        print()
        stats = manager.get_statistics()
        print("Statistics:")
        print(f"  - Categories: {stats['categories']}")
        print(f"  - Jurisdictions: {stats['jurisdictions']}")
        print(f"  - Document types: {stats['document_types']}")

    except MetadataError as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    """Run all examples."""

    print("\n" + "=" * 60)
    print("OQTF Utils - Example Usage")
    print("=" * 60)

    # Example 1: GDrive basic usage
    example_gdrive_basic_usage()

    # Example 2: Metadata basic usage
    example_metadata_basic_usage()

    # Example 3: Advanced metadata queries
    example_metadata_queries()

    # Example 4: Complete workflow
    example_complete_workflow()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60 + "\n")
