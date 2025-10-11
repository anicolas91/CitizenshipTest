import json
import os
from typing import Dict, Any, List, Union


def save_to_json(savefile: str, qa_pairs: Dict) -> None:
    """Save data to a JSON file."""
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(savefile) or '.', exist_ok=True)
    
    with open(savefile, "w", encoding="utf-8") as f:
        json.dump(qa_pairs, f, ensure_ascii=False, indent=2)

    print(f"Data saved to {savefile}")


def load_from_json(filepath: str) -> Union[Dict[str, Any], List[Any]]:
    """Load data from a JSON file."""
    
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"Data loaded from {filepath}")
    return data


def save_to_txt(savefile: str, text: str) -> None:
    """Save text to a plain text file."""
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(savefile) or '.', exist_ok=True)
    
    with open(savefile, 'w', encoding='utf-8') as f:
        f.write(text)

    print(f"Text saved to {savefile}")


def load_from_txt(filepath: str) -> str:
    """Load text from a plain text file."""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    print(f"Text loaded from {filepath}")
    return text

def expand_query(question: str, expansion_file: str = "../documents/expansion_terms.json") -> str:
    """
    Expand a civics question with relevant contextual terms (rule-based).
    Based on USCIS civics textbook topics.
    
    Args:
        question: Original question
        expansion_file: Path to JSON file with expansion terms
    
    Returns:
        Expanded query string with additional context
    """
    try:
        # Load expansion terms from JSON file using existing load_from_json
        expansion_terms = load_from_json(expansion_file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load expansion terms: {e}")
        return question
    
    question_lower = question.lower()
    added_terms = []
    
    # Find matching terms
    for keyword, terms in expansion_terms.items():
        if keyword in question_lower:
            # Add up to 2 related terms per matched keyword
            added_terms.extend(terms[:2])
    
    # Remove duplicates and limit to 5 additional terms max
    added_terms = list(dict.fromkeys(added_terms))[:5]
    
    if added_terms:
        return f"{question} {' '.join(added_terms)}"
    else:
        return question