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
  - <u>**2 points: Both a knowledge base and an LLM are used in the flow**</u> &rarr; Used Qdrant to embed data from a civics guide handbook, and used RAG to add context to the LLM query.
- Retrieval evaluation
  - 0 points: No evaluation of retrieval is provided
  - 1 point: Only one retrieval approach is evaluated
  - 2 points: Multiple retrieval approaches are evaluated, and the best one is used
- LLM evaluation
  - 0 points: No evaluation of final LLM output is provided
  - 1 point: Only one approach (e.g., one prompt) is evaluated
  - 2 points: Multiple approaches are evaluated, and the best one is used
- Interface
  - 0 points: No way to interact with the application at all
  - 1 point: Command line interface, a script, or a Jupyter notebook
  - 2 points: UI (e.g., Streamlit), web application (e.g., Django), or an API (e.g., built with FastAPI)
- Ingestion pipeline
  - 0 points: No ingestion
  - 1 point: Semi-automated ingestion of the dataset into the knowledge base, e.g., with a Jupyter notebook
  - 2 points: Automated ingestion with a Python script or a special tool (e.g., Mage, dlt, Airflow, Prefect)
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
  - [ ] User query rewriting (1 point)
- Bonus points (not covered in the course)
  - [ ] Deployment to the cloud (2 points)
  - [ ] Up to 3 extra bonus points if you want to award for something extra (write in feedback for what)
