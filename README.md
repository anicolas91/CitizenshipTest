# Citizenship test AI learning tool

## Problem description

Studying for the U.S. Citizenship (Naturalization) Test can feel overwhelming. Most people end up memorizing flashcards or PDFs without really understanding the meaning or history behind the questions. That makes it harder to stay motivated or actually retain the information.

This project is an AI-powered study assistant that helps users practice and learn the U.S. Citizenship Test in a more interactive way. It combines both the 2008 and 2025 USCIS question sets, plus background information from the official civics materials. When users practice, it feels like a real interview with a USCIS officer, where questions are chosen randomly, and they can answer in their own words.

One key feature is that the app keeps everything **up to date**. A scraping script automatically pulls the latest information (like current senators, representatives, or governors), so the answers always stay accurate.

After each response, the assistant gives a short “Did you know?” explanation that adds context or historical background, even if the user’s answer was wrong. The goal is to make studying more engaging, educational, and fun... something closer to a conversation than a test.

In the future, the idea is to turn this into a role-playing game where users “level up” through mock citizenship interviews, making the whole experience more memorable and motivating.

## Try it out!

The deployed study assistant can be found at [https://us-citizenship-test.streamlit.app/](https://us-citizenship-test.streamlit.app/). You will find there a chatbot + the dashboard monitoring 7 metrics that track the performance of this assistant.

Feel free to give feedback via thumbs up//thumbs down. Golden data is always appreciated. Thanks!

## Reproducibility & Setup Guide

This project is fully reproducible and can be run locally from scratch.
You will need to set up accounts with **OpenAI**, **Qdrant**, and **Neon** to obtain the API keys and database connection strings required for the LLM, vector search, and monitoring database services, respectively:

- 🧠 **OpenAI (LLM + embeddings):** [https://platform.openai.com/signup](https://platform.openai.com/signup)
- 🔍 **Qdrant (vector database):** [https://qdrant.tech](https://qdrant.tech) → click “Get started”
- 🗄️ **Neon (Postgres database):** [https://neon.tech](https://neon.tech) → click “Get started for free”

Note that all these services are free... openAI gives you 5 usd to start playing with this. You may need to add some more money if you already used that.

### Folder structure

```graphql
Home.py                  # Main Streamlit chatbot app
pages/Dashboard.py       # Streamlit dashboard page
utils/                   # Helper modules (retrieval, prompts, evaluation)
scripts/
 ├─ ingest.py            # Automated ingestion and embedding upload
 └─ evaluate.py          # Evaluation metrics computation
documents/               # Pre-ingested sample data (ready for quick start)
schemas/                 # SQL files to initialize Neon Postgres tables
requirements.txt         # All pinned dependencies
.env.example             # Example of required environment variables
```

### Environment setup

#### Step 1. Clone and enter the project

```bash
git clone https://github.com/anicolas91/CitizenshipTest.git
cd CitizenshipTest
```

#### Step 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # (Windows) .venv\Scripts\activate
```

#### Step 3. Install dependencies

```bash
pip install -r requirements.txt
```

All package versions are pinned for deterministic builds (see [requirements.txt](./requirements.txt)).

### Environment variables

Create a `.env` file in the project root with the following variables:

```ini
OPENAI_API_KEY=<your OpenAI key>
QDRANT_API_KEY=<your Qdrant key>
QDRANT_URL=<your Qdrant instance URL>
DATABASE_URL=<your Neon Postgres connection string>
```

You can use `.env.example` as a template.
Option A — Use sample pre-ingested data (quick start):

### Setting up the Neon Postgres database

1. Go to https://console.neon.tech and log in (or sign up).
2. Click “Create Project” → give it a name (e.g., `citizenship-test-db`).
3. Once it’s created, open the **“SQL Editor”** tab in the left sidebar.
4. Inside your local project, open the folder `schemas/`. It contains two SQL files (for example):

```graphql
schemas/
├─ evaluation_schema.sql
└─ ingestion_schema.sql
```

5. Copy and paste the contents of each .sql file into the Neon **SQL Editor**.
6. Run each file (click the ▶️ “Run” button) to create the necessary tables.

That’s it! your Neon database now has all required tables for:

- Logging user feedback (thumbs up/down)
- Tracking LLM and retrieval performance metrics

The connection string for this database appears in Neon under **Project Settings → Connection Details**.
Copy the **SQLAlchemy-compatible URL** (it usually starts with `postgresql+psycopg://…`) and paste it into your `.env` file as `DATABASE_URL`.

#### IMPORTANT NOTE:

⚠️ You only need to run these SQL files **once** to initialize your database schema.  
If you skip this step, the Streamlit dashboard and feedback logging will not work.

### Running the project

#### Option A – Quick start (with sample data):

```bash
streamlit run Home.py
```

This launches the chatbot using pre-ingested QnA+Civics Guide data from the `documents/` folder.

#### Option B – Full refresh (re-ingest from official sources):

```bash
python scripts/ingest.py
```

This script:

- Downloads official USCIS PDFs and civics guide
- Extracts Q&A pairs and current officeholders
- Generates embeddings via OpenAI
- Uploads the processed data to Qdrant

#### Option C – Run evaluation metrics:

After using the thumbs-up//thumbs-down in the app to create some user feedback, you can run:

```bash
python scripts/evaluate.py
```

This script computes the 7 evaluation metrics tracked in the dashboard.

Once you've run it, you can go refresh the dashboard and see how your app is performing.

### Interacting with the project

The chatbot and the dashboard will automatically open in your browser after you run `streamlit run Home.py`.

If not, you can manually access it at:
👉 [http://localhost:8502/](http://localhost:8502/)  
(Note: the port number may vary depending on what’s available.)

# Evaluation criteria

- Problem description
  - 0 points: The problem is not described
  - 1 point: The problem is described but briefly or unclearly
  - ✅ **2 points: The problem is well-described and it's clear what problem the project solves** &rarr; The problem is clearly explained. It identifies the challenges of rote memorization for citizenship prep and shows how the AI assistant solves this through interactive, up-to-date, and contextual learning.
- Retrieval flow
  - 0 points: No knowledge base or LLM is used
  - 1 point: No knowledge base is used, and the LLM is queried directly
  - ✅ **2 points: Both a knowledge base and an LLM are used in the flow** &rarr; Implemented full RAG pipeline: embedded USCIS civics guide into Qdrant vector database, retrieved relevant context via semantic search, and used OpenAI LLM with retrieved context to generate educational feedback and explanations for quiz answers.
- Retrieval evaluation
  - 0 points: No evaluation of retrieval is provided
  - 1 point: Only one retrieval approach is evaluated
  - ✅ **2 points: Multiple retrieval approaches are evaluated, and the best one is used** &rarr; Systematically evaluated multiple Qdrant retrieval configurations by varying three parameters: result limit (2, 3, 4), score threshold (0.3, 0.5, 0.7), and query expansion (on/off). Compared approaches using Hit Rate and MRR metrics and selected the optimal configuration for production use (limit=4, threshold=0.3, expansion=off). See results [here](./notebooks/04_retrieval_evaluation.ipynb).
- LLM evaluation
  - 0 points: No evaluation of final LLM output is provided
  - 1 point: Only one approach (e.g., one prompt) is evaluated
  - ✅ **2 points: Multiple approaches are evaluated, and the best one is used** &rarr; Created both quantitative and qualitative metrics (latter use llm-as-judge), used multiple openAI models to compare evaluation outputs, finetuted the system prompt based on learnings from the evaluation metrics, and reached final conclusions on evaluation performance and monitoring. See results [here](./notebooks/05_llm_evaluation.ipynb).
- Interface
  - 0 points: No way to interact with the application at all
  - 1 point: Command line interface, a script, or a Jupyter notebook
  - ✅ **2 points: UI (e.g., Streamlit), web application (e.g., Django), or an API (e.g., built with FastAPI)** &rarr; User can connect to the application via a streamlit UI. Currently done via `streamlit run app.py` locally, and deployed on cloud [here](https://citizenship-test.streamlit.app/).
- Ingestion pipeline
  - 0 points: No ingestion
  - 1 point: Semi-automated ingestion of the dataset into the knowledge base, e.g., with a Jupyter notebook
  - ✅ **2 points: Automated ingestion with a Python script or a special tool (e.g., Mage, dlt, Airflow, Prefect)** &rarr; Fully automated Python script (`scripts/ingest.py`) that runs end-to-end without manual intervention: (1) downloads official USCIS PDFs from source, (2) extracts and parses Q&A pairs, (3) uses LLM to populate current officeholder data, (4) processes civics guide text, (5) generates embeddings via OpenAI, and (6) uploads to Qdrant vector database. Single command execution: `python scripts/ingest.py`. See ingestion documentation [here](./documents/INGESTION.md).
- Monitoring
  - 0 points: No monitoring
  - 1 point: User feedback is collected OR there's a monitoring dashboard.
  - ✅ **2 points: User feedback is collected and there's a dashboard with at least 5 charts.** &rarr; User feedback is collected via thumbs up/thumbs down + neo postgres. Dashboard set up via streamlit and deployed [here][https://us-citizenship-test.streamlit.app/Dashboard]. The dashboard tracks the 7 metrics developed during the [LLM evaluation analysis](./notebooks/05_llm_evaluation.ipynb) and tracks them via 5+ charts and summaries.
- Containerization
  - **0 points: No containerization** &rarr; Containerization was intentionally skipped due to time constraints. However, the project remains fully reproducible without it, thanks to a comprehensive setup guide.
  - 1 point: Dockerfile is provided for the main application OR there's a docker-compose for the dependencies only
  - 2 points: Everything is in docker-compose
- Reproducibility
  - 0 points: No instructions on how to run the code, the data is missing, or it's unclear how to access it
  - 1 point: Some instructions are provided but are incomplete, OR instructions are clear and complete, the code works, but the data is missing
  - ✅ **2 points: Instructions are clear, the dataset is accessible, it's easy to run the code, and it works. The versions for all dependencies are specified.** &rarr; The project includes a complete, step-by-step reproducibility guide covering environment setup, dependency installation, and configuration of external services (**OpenAI**, **Qdrant**, **Neon**). Sample pre-ingested data is provided in the `documents/` folder for immediate testing, while `scripts/ingest.py` can automatically rebuild the dataset from official USCIS sources. Database initialization is fully documented through the `schemas/` SQL files with explicit instructions for creating tables via the Neon SQL editor. All dependencies are pinned in `requirements.txt`, and a `.env.example` file specifies required environment variables. Together, these ensure the entire system can be reproduced locally without containerization and run exactly as described.
- Best practices
  - [ ] Hybrid search: combining both text and vector search (at least evaluating it) (1 point)
  - [ ] Document re-ranking (1 point)
  - ✅ **User query rewriting (1 point)** &rarr; Evaluated query expansion systematically by testing retrieval with and without expanded queries. Measured impact using Hit Rate and MRR metrics. Results showed no improvement (expansion actually decreased performance), so the feature was not implemented in production. See evaluation [here](./notebooks/04_retrieval_evaluation.ipynb).
- Bonus points (not covered in the course)
  - ✅ **Deployment to the cloud (2 points)** &rarr; App was deployed to the cloud via streamlit and can be found [here](https://us-citizenship-test.streamlit.app/).
  - ✅ **Up to 3 extra bonus points if you want to award for something extra (write in feedback for what)** &rarr; added automatic ingestion of raw data/uploading to QDRANT via CI/CD. See documentation [here](./documents/INGESTION.md#automated-monthly-ingestion).
