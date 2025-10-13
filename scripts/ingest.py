#!/usr/bin/env python3
"""
Main ingestion pipeline for US Civics Test data.

Downloads PDFs, extracts Q&A pairs, processes civics guide text,
and uploads embeddings to Qdrant vector database.

Usage:
    python scripts/ingest.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient

from utils.ingestion import (
    download_civics_documents,
    process_civics_tests,
    extract_clean_text_from_guide
)
from utils.qdrant import create_qdrant_collection, create_embedded_points


# Configuration
SAVE_DIR = '../documents/'
COLLECTION_NAME = 'usa_civics_guide'
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536  # Matches text-embedding-3-small


def main():
    """Main ingestion pipeline."""
    
    print("=" * 70)
    print("US CIVICS TEST - MAIN INGESTION PIPELINE")
    print("=" * 70)
    
    # Load environment variables
    load_dotenv()
    
    # Initialize clients
    try:
        print("\n[Setup] Initializing API clients...")
        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        qdrant_client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
        print("✓ Clients initialized successfully")
    except Exception as e:
        print(f"✗ Error initializing clients: {str(e)}")
        print("  Make sure your .env file contains OPENAI_API_KEY, QDRANT_URL, and QDRANT_API_KEY")
        sys.exit(1)
    
    try:
        # Step 1: Download all PDFs
        print("\n[Step 1/4] Downloading civics documents...")
        download_info = download_civics_documents(save_dir=SAVE_DIR)
        print(f"✓ Downloaded {len(download_info['tests'])} tests and 1 guide")
        
        # Step 2: Extract Q&As, fill missing data, and save as JSON
        print("\n[Step 2/4] Processing civics test Q&A pairs...")
        all_qa_pairs = process_civics_tests(download_info, SAVE_DIR)
        total_questions = sum(len(qa) for qa in all_qa_pairs.values())
        print(f"✓ Processed {total_questions} total questions")
        
        # Step 3: Extract the civics guide information
        print("\n[Step 3/4] Extracting text from civics guide...")
        guide_document = os.path.join(
            SAVE_DIR,
            f"{download_info['guide']['test_type']}.pdf"
        )
        
        if not os.path.exists(guide_document):
            print(f"✗ Error: Guide PDF not found at {guide_document}")
            sys.exit(1)
        
        datapoints = extract_clean_text_from_guide(guide_document)
        print(f"✓ Extracted {len(datapoints)} text segments from guide")
        
        # Step 4: Upload the civics guide pages to Qdrant
        print("\n[Step 4/4] Uploading embeddings to Qdrant...")
        
        # Create collection
        print(f"  Creating/verifying collection '{COLLECTION_NAME}'...")
        create_qdrant_collection(
            client=qdrant_client,
            collection_name=COLLECTION_NAME,
            dimension_size=EMBEDDING_DIMENSION
        )
        
        # Create embeddings
        print(f"  Generating embeddings using {EMBEDDING_MODEL}...")
        points = create_embedded_points(
            datapoints=datapoints,
            openai_client=openai_client,
            model=EMBEDDING_MODEL
        )
        
        # Upload to Qdrant
        print(f"  Uploading {len(points)} points to Qdrant...")
        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        print(f"✓ Successfully uploaded {len(points)} embedded documents")
        
        # Final summary
        print("\n" + "=" * 70)
        print("✓ INGESTION PIPELINE COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print(f"  Civics Tests processed: {len(all_qa_pairs)}")
        print(f"  Total Q&A pairs: {total_questions}")
        print(f"  Guide segments: {len(datapoints)}")
        print(f"  Qdrant collection: {COLLECTION_NAME}")
        print(f"  Embedding model: {EMBEDDING_MODEL}")
        print("=" * 70)
        
    except FileNotFoundError as e:
        print(f"\n✗ File not found error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error during ingestion: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()