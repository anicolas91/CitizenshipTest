# Citizenship test AI learning tool

## Problem description

Studying for the U.S. Citizenship (Naturalization) Test can feel overwhelming. Most people end up memorizing flashcards or PDFs without really understanding the meaning or history behind the questions. That makes it harder to stay motivated or actually retain the information.

This project is an AI-powered study assistant that helps users practice and learn the U.S. Citizenship Test in a more interactive way. It combines both the 2008 and 2025 USCIS question sets, plus background information from the official civics materials. When users practice, it feels like a real interview with a USCIS officer, where questions are chosen randomly, and they can answer in their own words.

One key feature is that the app keeps everything **up to date**. A scraping script automatically pulls the latest information (like current senators, representatives, or governors), so the answers always stay accurate.

After each response, the assistant gives a short “Did you know?” explanation that adds context or historical background, even if the user’s answer was wrong. The goal is to make studying more engaging, educational, and fun... something closer to a conversation than a test.

In the future, the idea is to turn this into a role-playing game where users “level up” through mock citizenship interviews, making the whole experience more memorable and motivating.

# Evaluation criteria

- Problem description
  - 0 points: The problem is not described
  - 1 point: The problem is described but briefly or unclearly
  - <u>**2 points: The problem is well-described and it's clear what problem the project solves**</u> &rarr; The problem is clearly explained. It identifies the challenges of rote memorization for citizenship prep and shows how the AI assistant solves this through interactive, up-to-date, and contextual learning.
- Retrieval flow
  - 0 points: No knowledge base or LLM is used
  - 1 point: No knowledge base is used, and the LLM is queried directly
  - <u>**2 points: Both a knowledge base and an LLM are used in the flow**</u> → Implemented full RAG pipeline: embedded USCIS civics guide into Qdrant vector database, retrieved relevant context via semantic search, and used OpenAI LLM with retrieved context to generate educational feedback and explanations for quiz answers.
- Retrieval evaluation
  - 0 points: No evaluation of retrieval is provided
  - 1 point: Only one retrieval approach is evaluated
  - <u>**2 points: Multiple retrieval approaches are evaluated, and the best one is used**</u> &rarr; Systematically evaluated multiple Qdrant retrieval configurations by varying three parameters: result limit (2, 3, 4), score threshold (0.3, 0.5, 0.7), and query expansion (on/off). Compared approaches using Hit Rate and MRR metrics and selected the optimal configuration for production use (limit=4, threshold=0.3, expansion=off). See results [here](./notebooks/04_retrieval_evaluation.ipynb).
- LLM evaluation
  - 0 points: No evaluation of final LLM output is provided
  - 1 point: Only one approach (e.g., one prompt) is evaluated
  - 2 points: Multiple approaches are evaluated, and the best one is used
- Interface
  - 0 points: No way to interact with the application at all
  - 1 point: Command line interface, a script, or a Jupyter notebook
  - <u>**2 points: UI (e.g., Streamlit), web application (e.g., Django), or an API (e.g., built with FastAPI)**</u> &rarr; User can connect to the application via a streamlit UI. Currently done via `streamlit run app.py` locally, and deployed on cloud [here](https://citizenship-test.streamlit.app/).
- Ingestion pipeline
  - 0 points: No ingestion
  - 1 point: Semi-automated ingestion of the dataset into the knowledge base, e.g., with a Jupyter notebook
  - <u>**2 points: Automated ingestion with a Python script or a special tool (e.g., Mage, dlt, Airflow, Prefect)**</u> &rarr; Fully automated Python script (`scripts/ingest.py`) that runs end-to-end without manual intervention: (1) downloads official USCIS PDFs from source, (2) extracts and parses Q&A pairs, (3) uses LLM to populate current officeholder data, (4) processes civics guide text, (5) generates embeddings via OpenAI, and (6) uploads to Qdrant vector database. Single command execution: `python scripts/ingest.py`. See ingestion documentation [here](./documents/INGESTION.md).
- Monitoring
  - 0 points: No monitoring
  - 1 point: User feedback is collected OR there's a monitoring dashboard
  - 2 points: User feedback is collected and there's a dashboard with at least 5 charts
- Containerization
  - 0 points: No containerization
  - 1 point: Dockerfile is provided for the main application OR there's a docker-compose for the dependencies only
  - 2 points: Everything is in docker-compose
- Reproducibility
  - 0 points: No instructions on how to run the code, the data is missing, or it's unclear how to access it
  - 1 point: Some instructions are provided but are incomplete, OR instructions are clear and complete, the code works, but the data is missing
  - 2 points: Instructions are clear, the dataset is accessible, it's easy to run the code, and it works. The versions for all dependencies are specified.
- Best practices
  - [ ] Hybrid search: combining both text and vector search (at least evaluating it) (1 point)
  - [ ] Document re-ranking (1 point)
  - [x] User query rewriting (1 point) → Evaluated query expansion systematically by testing retrieval with and without expanded queries. Measured impact using Hit Rate and MRR metrics. Results showed no improvement (expansion actually decreased performance), so the feature was not implemented in production. See evaluation [here](./notebooks/04_retrieval_evaluation.ipynb).
- Bonus points (not covered in the course)
  - [x] Deployment to the cloud (2 points) &rarr; App was deployed to the cloud via streamlit and can be found [here](https://citizenship-test.streamlit.app/).
  - [ ] Up to 3 extra bonus points if you want to award for something extra (write in feedback for what)
