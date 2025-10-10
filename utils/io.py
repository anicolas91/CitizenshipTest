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