import os
import json
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from qdrant_client import QdrantClient

# Load environment variables from .env file
load_dotenv()

# Initialize clients with API keys from .env
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

# Constants
DEFAULT_COLLECTION = "usa_civics_guide"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_LLM_MODEL = "gpt-4o-mini"


def get_context(
    question: str,
    collection_name: str = DEFAULT_COLLECTION,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    limit: int = 2,
    score_threshold: float = 0.5,
    query_expansion: bool = False,
    expansion_file: str = "../documents/expansion_terms.json"
) -> str:
    """
    Retrieve relevant context from Qdrant based on a question.
    
    Args:
        question: The user's question to search for
        collection_name: Name of the Qdrant collection to search
        embedding_model: OpenAI embedding model to use
        limit: Number of top results to return
        score_threshold: Minimum similarity score (0-1) for results
        query_expansion: If True, expand query with related civics terms
        expansion_file: Path to JSON file with expansion terms
    
    Returns:
        Formatted string containing relevant page contexts
    
    Raises:
        ValueError: If question is empty
    """
    if not question or not question.strip():
        raise ValueError("Question cannot be empty")
    
    # Apply query expansion if requested
    if query_expansion:
        from .io import expand_query
        question = expand_query(question, expansion_file)
    
    # Embed the question
    embedding_response = openai_client.embeddings.create(
        model=embedding_model,
        input=question
    )
    question_embedding = embedding_response.data[0].embedding

    # Search Qdrant for relevant pages
    search_results = qdrant_client.query_points(
        collection_name=collection_name,
        query=question_embedding,
        limit=limit,
        score_threshold=score_threshold
    )

    # Handle empty results
    if not search_results.points:
        return "No relevant context found."

    # Build context from search results
    context = "\n\n---\n\n".join([
        f"Page {result.payload.get('page_number', 'Unknown')}:\n{result.payload.get('text', '')}"
        for result in search_results.points
    ])

    return context


def llm(
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_LLM_MODEL
) -> Dict[str, Any]:
    """
    Get an answer from the LLM using custom system and user prompts.
    
    Args:
        system_prompt: The system message that defines the assistant's behavior and role
        user_prompt: The user message containing the question and any context
        model: OpenAI model to use (default: gpt-4o-mini)
    
    Returns:
        The LLM's parsed JSON output as a dict. If parsing fails, returns {"error": "..."}.
    """
    if not system_prompt or not user_prompt:
        return {"error": "Both system_prompt and user_prompt are required"}
    
    try:
        completion = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )

        response_text = completion.choices[0].message.content

        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            return {
                "error": f"Failed to parse JSON response: {e}",
                "raw_output": response_text
            }

        return data

    except Exception as e:
        return {"error": str(e)}


def rag(
    user_prompt: str,
    system_prompt: str,
    question: str,
    answers: str,
    user_state: str,
    user_answer: str,
    model: str = DEFAULT_LLM_MODEL,
    collection_name: str = DEFAULT_COLLECTION,
    context_limit: int = 2
) -> Dict[str, Any]:
    """
    Complete RAG pipeline for Q&A with context retrieval.
    
    Args:
        user_prompt: Template string for user prompt (should contain format placeholders)
        system_prompt: System message defining assistant behavior
        question: The quiz/test question
        answers: Available answer choices
        user_state: Current state information about the user
        user_answer: The user's submitted answer
        model: OpenAI model to use
        collection_name: Qdrant collection name
        context_limit: Number of context chunks to retrieve
    
    Returns:
        Dict containing LLM response (parsed JSON) or error information
    
    Example:
        >>> user_prompt_template = "Question: {question}\nAnswers: {answers}\n..."
        >>> result = rag(
        ...     user_prompt=user_prompt_template,
        ...     system_prompt="You are a civics tutor...",
        ...     question="What are the branches of government?",
        ...     answers="A) 2 B) 3 C) 4",
        ...     user_state="beginner",
        ...     user_answer="B"
        ... )
    """
    try:
        # Get context from Qdrant
        context = get_context(
            question=question,
            collection_name=collection_name,
            limit=context_limit
        )
        
        # Format the user prompt with all variables
        qna_user_prompt = user_prompt.format(
            question=question,
            answers=answers,
            user_state=user_state,
            user_answer=user_answer,
            context=context
        )
        
        # Send to LLM (llm function already parses JSON output)
        return llm(system_prompt, qna_user_prompt, model)
    
    except KeyError as e:
        return {"error": f"Missing placeholder in user_prompt template: {e}"}
    except Exception as e:
        return {"error": f"RAG pipeline error: {str(e)}"}