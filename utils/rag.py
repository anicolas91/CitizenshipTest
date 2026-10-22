import os
import json
from typing import Dict, Any
import anthropic
from dotenv import load_dotenv
from fastembed import TextEmbedding
from qdrant_client import QdrantClient

# Load environment variables from .env file
load_dotenv()

# Initialize clients with API keys from .env
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

# Constants
DEFAULT_COLLECTION = "usa_civics_guide"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"  # runs locally via fastembed, 384 dims
DEFAULT_LLM_MODEL = "claude-haiku-5-5"
DEFAULT_EFFORT = "low"  # Claude effort level: low | medium | high | xhigh | max

# Embedding models are loaded once and cached (first load downloads the weights)
_embedding_models: Dict[str, TextEmbedding] = {}


def embed(texts, model: str = DEFAULT_EMBEDDING_MODEL):
    """Embed a list of texts locally with fastembed. Returns a list of vectors."""
    if model not in _embedding_models:
        _embedding_models[model] = TextEmbedding(model)
    return [vector.tolist() for vector in _embedding_models[model].embed(texts)]


def parse_json_output(text: str) -> Dict[str, Any]:
    """Parse a JSON object from the model output, tolerating ```json fences or stray text around it."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise json.JSONDecodeError("No JSON object found", text, 0)
    return json.loads(text[start:end + 1])


def get_context(
    question: str,
    collection_name: str = DEFAULT_COLLECTION,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    limit: int = 2,
    score_threshold: float = 0.5,
    query_expansion: bool = False,
    expansion_terms: dict = None 
) -> str:
    """
    Retrieve relevant context from Qdrant based on a question.
    
    Args:
        question: The user's question to search for
        collection_name: Name of the Qdrant collection to search
        embedding_model: fastembed embedding model to use
        limit: Number of top results to return
        score_threshold: Minimum similarity score (0-1) for results
        query_expansion: If True, expand query with related civics terms
        expansion_terms: Dictionary of expansion terms (loaded externally for efficiency)
    
    Returns:
        Formatted string containing relevant page contexts
    
    Raises:
        ValueError: If question is empty
    """
    if not question or not question.strip():
        raise ValueError("Question cannot be empty")
    
    # Apply query expansion if requested
    if query_expansion and expansion_terms:
        from .io import expand_query
        question = expand_query(question, expansion_terms)
    
    # Embed the question
    question_embedding = embed([question], model=embedding_model)[0]

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
    model: str = DEFAULT_LLM_MODEL,
    effort: str = DEFAULT_EFFORT,
) -> Dict[str, Any]:
    """
    Get an answer from the LLM using custom system and user prompts.
    
    Args:
        system_prompt: The system message that defines the assistant's behavior and role
        user_prompt: The user message containing the question and any context
        model: Claude model to use (default: claude-haiku-5-5)
        effort: Claude effort level, trades thinking depth for speed/cost (default: low)
    
    Returns:
        The LLM's parsed JSON output as a dict. If parsing fails, returns {"error": "..."}.
    """
    if not system_prompt or not user_prompt:
        return {"error": "Both system_prompt and user_prompt are required"}
    
    try:
        response = anthropic_client.messages.create(
            model=model,
            max_tokens=16000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            output_config={"effort": effort},
        )

        if response.stop_reason == "refusal":
            return {"error": "Model declined to answer"}

        response_text = "".join(block.text for block in response.content if block.type == "text")

        try:
            data = parse_json_output(response_text)
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
    context_limit: int = 2,
    score_threshold: float = 0.5,
    query_expansion: bool = False,
    effort: str = DEFAULT_EFFORT
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
        model: Claude model to use
        collection_name: Qdrant collection name
        context_limit: Number of context chunks to retrieve
        score_threshold: Minimum similarity score (0-1) for results
        query_expansion: If True, expand query with related civics terms
        effort: Claude effort level (default: low)
    
    Returns:
        Dict containing:
            - LLM response (parsed JSON)
            - metadata: system_prompt, user_prompt, model, effort, context
    Example:
        >>> user_prompt_template = "Question: {question}\nAnswers: {answers}\n..."
        >>> result = rag(
        ...     user_prompt=user_prompt_template,
        ...     system_prompt="You are a civics tutor...",
        ...     question="What are the branches of government?",
        ...     answers="A) 2 B) 3 C) 4",
        ...     user_state="AZ",
        ...     user_answer="B"
        ... )
    """
    try:
        # Get context from Qdrant
        context = get_context(
            question=question,
            collection_name=collection_name,
            limit=context_limit,
            score_threshold=score_threshold,
            query_expansion=query_expansion
        )
        
        # Format the user prompt with all variables
        qna_user_prompt = user_prompt.format(
            question=question,
            answers=answers,
            user_state=user_state,
            user_answer=user_answer,
            context=context
        )
        
        # Send to LLM (llm function already parses JSON output, and it has 'score','reason', 'background_info', that sort of thing)
        llm_response=llm(system_prompt, qna_user_prompt, model, effort)

        # Add metadata to response
        llm_response['metadata'] = {
            'system_prompt': system_prompt,
            'user_prompt': qna_user_prompt,
            'model': model,
            'effort': effort,
            'context': context,
            'context_limit': context_limit,
            'score_threshold': score_threshold,
            'query_expansion': query_expansion
        }
        
        return llm_response

    except KeyError as e:
        return {
            "error": f"Missing placeholder in user_prompt template: {e}",
            "metadata": {
                'system_prompt': system_prompt,
                'user_prompt': user_prompt,  # Original template, not formatted
                'model': model,
                'effort': effort,
                'context': context if 'context' in locals() else None,
                'context_limit': context_limit,
                'score_threshold': score_threshold,
                'query_expansion': query_expansion
            }
        }
    except Exception as e:
        return {
            "error": f"RAG pipeline error: {str(e)}",
            "metadata": {
                'system_prompt': system_prompt,
                'user_prompt': qna_user_prompt if 'qna_user_prompt' in locals() else user_prompt,
                'model': model,
                'effort': effort,
                'context': context if 'context' in locals() else None,
                'context_limit': context_limit,
                'score_threshold': score_threshold,
                'query_expansion': query_expansion
            }
        }