# Ingestion Pipeline Documentation

## Overview

The ingestion pipeline is a fully automated Python script that downloads, processes, and uploads US Civics Test data to the knowledge base. It runs end-to-end without manual intervention.

## What It Does

The pipeline performs the following steps automatically:

1. **Downloads PDFs** - Fetches official USCIS documents from source

   - 2008 Civics Test (100 questions)
   - 2025 Civics Test (128 questions)
   - Civics Study Guide textbook

2. **Extracts Q&A Pairs** - Parses questions and answers from test PDFs using custom PDF extraction logic

3. **Populates Current Data** - Uses LLM to fill in variable answers (current government officials, etc.)

4. **Processes Guide Text** - Cleans and segments the civics textbook content

5. **Generates Embeddings** - Creates vector embeddings using OpenAI's `text-embedding-3-small` model

6. **Uploads to Qdrant** - Stores embeddings in vector database for semantic search

## Prerequisites

### API Keys Required

- **OpenAI API Key** - For generating embeddings and populating current data
- **Qdrant Access** - URL and API key for vector database

### Environment Setup

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your_openai_api_key_here
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_qdrant_api_key_here
```

For local Qdrant development, you can omit `QDRANT_API_KEY` if running without authentication.

### Dependencies

Install required packages:

```bash
pip install -r requirements.txt
```

Key dependencies:

- openai - For embeddings and LLM calls
- qdrant-client - Vector database client
- PyPDF2 - PDF parsing
- beautifulsoup4 - Web scraping for current officials
- requests - HTTP requests
- python-dotenv - Environment variable management

## Running the Ingestion Pipeline

### Basic Usage

From the project root directory:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the ingestion script
python scripts/ingest.py
```

### What to Expect

The script will output progress for each step:

```bash
======================================================================
US CIVICS TEST - MAIN INGESTION PIPELINE
======================================================================

[Setup] Initializing API clients...
✓ Clients initialized successfully

[Step 1/4] Downloading civics documents...
  Downloading 2008_civics_test...
    ✓ Saved as ../documents/2008_civics_test.pdf
  Downloading 2025_civics_test...
    ✓ Saved as ../documents/2025_civics_test.pdf
  Downloading civics_guide...
    ✓ Saved as ../documents/civics_guide.pdf
✓ Downloaded 2 tests and 1 guide

[Step 2/4] Processing civics test Q&A pairs...
  Processing 2008_civics_test...
    • Parsing PDF...
    • Extracted 100 questions
    • Populating missing answers...
    ✓ Saved 100 Q&A pairs to ../documents/2008_civics_test_qa_pairs.json
  Processing 2025_civics_test...
    • Parsing PDF...
    • Extracted 128 questions
    • Populating missing answers...
    ✓ Saved 128 Q&A pairs to ../documents/2025_civics_test_qa_pairs.json
✓ Processed 228 total questions

[Step 3/4] Extracting text from civics guide...
✓ Extracted 45 text segments from guide

[Step 4/4] Uploading embeddings to Qdrant...
  Creating/verifying collection 'usa_civics_guide'...
  Generating embeddings using text-embedding-3-small...
  ✓ Created 45 embedded points
  Uploading 45 points to Qdrant...
✓ Successfully uploaded 45 embedded documents

======================================================================
✓ INGESTION PIPELINE COMPLETED SUCCESSFULLY
======================================================================
  Civics Tests processed: 2
  Total Q&A pairs: 228
  Guide segments: 45
  Qdrant collection: usa_civics_guide
  Embedding model: text-embedding-3-small
======================================================================
```

### Output Files

After successful ingestion, you'll find:

```bash
documents/
├── 2008_civics_test.pdf
├── 2008_civics_test_qa_pairs.json
├── 2025_civics_test.pdf
├── 2025_civics_test_qa_pairs.json
├── civics_guide.pdf
```

## Pipeline Architecture

### Script Structure

```bash
scripts/
└── ingest.py                 # Main ingestion script

utils/
├── ingestion.py              # Core ingestion functions
│   ├── download_civics_documents()
│   ├── process_civics_tests()
│   ├── parse_clean_qa_pdf()
│   ├── populate_missing_questions()
│   └── extract_clean_text_from_guide()
├── qdrant.py                 # Vector database utilities
│   ├── create_qdrant_collection()
│   └── create_embedded_points()
├── io.py                     # File I/O utilities
│   └── save_to_json()
└── prompts.py                # LLM prompt templates
```

### Data Flow

```bash
USCIS Website
    ↓ (download)
PDF Files
    ↓ (parse)
Raw Q&A Pairs
    ↓ (populate with LLM)
Complete Q&A Pairs → JSON Files
    ↓ (extract & clean)
Text Segments
    ↓ (embed with OpenAI)
Vector Embeddings
    ↓ (upload)
Qdrant Vector Database
```

## Configuration

### Customizing Settings

Edit the configuration section in `scripts/ingest.py`:

```python
# Project paths (automatically determined)
SCRIPT_DIR = Path(__file__).parent.resolve()  # scripts/
PROJECT_ROOT = SCRIPT_DIR.parent              # CitizenshipTest/
DOCUMENTS_DIR = PROJECT_ROOT / 'documents'    # Where files are saved

# Configuration
COLLECTION_NAME = 'usa_civics_guide'          # Qdrant collection name
EMBEDDING_MODEL = "text-embedding-3-small"    # OpenAI embedding model
EMBEDDING_DIMENSION = 1536                    # Vector dimension (must match model)
```

### Qdrant Collection

The script creates a Qdrant collection with:

- Name: `usa_civics_guide`
- Vector Dimension: 1536 (matches `text-embedding-3-small`)
- Distance Metric: Cosine similarity

Each point contains:

```python
{
    "id": "uuid",
    "vector": [1536-dimensional embedding],
    "payload": {
        "page_number": 1,
        "text": "Full text content...",
        "source": "USCIS Civics Textbook"
    }
}
```
