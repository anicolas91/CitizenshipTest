import os
import uuid
import psycopg2
import streamlit as st
from pathlib import Path
from datetime import datetime
from utils.io import load_from_json

# Get project paths
SCRIPT_DIR = Path(__file__).parent.parent.resolve()
DOCUMENTS_DIR = SCRIPT_DIR / 'documents'

# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# US States, Territories, and D.C. - All 50 states plus Washington D.C. and 5 inhabited territories
# Used for location selection to personalize civics questions with local officials
US_LOCATIONS = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming",
    # Federal District
    "Washington D.C.",
    # US Territories
    "American Samoa",
    "Guam",
    "Northern Mariana Islands",
    "Puerto Rico",
    "US Virgin Islands"
]

# RAG System Configuration
# - context_limit: Max documents to retrieve (2)
# - score_threshold: Min similarity score (0.5)
# - query_expansion: Expand queries with synonyms (False)
# - temperature: LLM creativity level (0.5 = balanced)
RAG_CONFIG = {
    'context_limit': 4,
    'score_threshold': 0.3,
    'query_expansion': False,
    'temperature': 0.5
}

# USCIS Test Configuration by Version
# 2008: 10 questions, need 6 correct (or max 4 incorrect)
# 2025: 20 questions, need 12 correct (or max 8 incorrect)
# Cutoff date: October 20, 2025 (determines which test to take)
TEST_CONFIG = {
    "2008": {
        "total": 10,
        "passing": 6,
        "max_incorrect": 4,  # 10 - 6
        "name": "2008 Civics Test"
    },
    "2025": {
        "total": 20,
        "passing": 12,
        "max_incorrect": 8,  # 20 - 12
        "name": "2025 Civics Test"
    }
}

def get_test_requirements(test_year):
    """Get test requirements for a given year"""
    return TEST_CONFIG.get(test_year, TEST_CONFIG["2008"])
    
def reset_quiz_state():
    """Clear all quiz-related session state"""
    quiz_keys = [
        'question',
        'answered', 
        'total_attempted',
        'total_correct',
        'total_incorrect',
        'result',
        'user_answer_text',
        'question_counter',
        'asked_questions',
        'test_complete',
        'test_passed', 
        'feedback_given',
    ]
    
    for key in quiz_keys:
        if key in st.session_state:
            del st.session_state[key]

def check_test_completion():
    """Check if the test WOULD BE complete based on 2008 or 2025 rules - returns True/False but doesn't set state"""
    test_year = st.session_state.test_year
    correct = st.session_state.total_correct
    incorrect = st.session_state.total_incorrect
    
    config = TEST_CONFIG[test_year]
    
    # Pass with enough correct answers
    if correct >= config["passing"]:
        return True, True  # (test_complete, test_passed)
    
    # Fail with too many incorrect answers
    elif incorrect > config["max_incorrect"]:
        return True, False  # (test_complete, test_failed)
    
    return False, False  # Test not complete yet

def reset_all_state():
    """Clear everything and go back to setup"""
    # Clear setup
    st.session_state.setup_complete = False
    st.session_state.user_state = None
    st.session_state.test_year = None
    
    # Clear quiz
    reset_quiz_state()

def log_feedback(feedback_type):
    """Log user feedback to Neon Postgres database with session state fallback"""
    # Mark feedback as given to disable buttons
    st.session_state.feedback_given = True
    
    # Generate session ID if not exists
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    
    # Get LLM metadata if available
    llm_metadata = st.session_state.get('llm_metadata', {})
    
    # Prepare feedback entry
    feedback_entry = {
        'timestamp': datetime.now().isoformat(),
        'user_state': st.session_state.user_state,
        'test_year': st.session_state.test_year,
        'question': st.session_state.question.get('question', ''),
        'user_answer': st.session_state.user_answer_text,
        'correct_answers': st.session_state.question.get('answers', ''),
        'success': st.session_state.result.get('success', False),
        'reason': st.session_state.result.get('reason', ''),
        'background_info': st.session_state.result.get('background_info', ''),
        'feedback': feedback_type,
        'session_id': st.session_state.session_id,
        # LLM inputs from metadata
        'system_prompt': llm_metadata.get('system_prompt', ''),
        'user_prompt': llm_metadata.get('user_prompt', ''),
        'model': llm_metadata.get('model', ''),
        'llm_temperature': llm_metadata.get('temperature', 0.5),
        'context': llm_metadata.get('context', ''),
        'context_limit': llm_metadata.get('context_limit', RAG_CONFIG['context_limit']),
        'score_threshold': llm_metadata.get('score_threshold', RAG_CONFIG['score_threshold']),
        'query_expansion': llm_metadata.get('query_expansion', RAG_CONFIG['query_expansion']),
    }
    
    try:
        # Connect to Neon Postgres
        conn = psycopg2.connect(st.secrets["database"]["url"])
        cur = conn.cursor()
        
        # Insert feedback into database
        cur.execute("""
            INSERT INTO feedback (
                timestamp, user_state, test_year, question_text, 
                correct_answers, user_answer, success, reason, 
                background_info, feedback_type, session_id,
                rag_context_limit, rag_score_threshold, rag_query_expansion,
                system_prompt, user_prompt, model, llm_temperature, context
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            feedback_entry['timestamp'],
            feedback_entry['user_state'],
            feedback_entry['test_year'],
            feedback_entry['question'],
            feedback_entry['correct_answers'],
            feedback_entry['user_answer'],
            feedback_entry['success'],
            feedback_entry['reason'],
            feedback_entry['background_info'],
            feedback_entry['feedback'],
            feedback_entry['session_id'],
            feedback_entry['context_limit'],
            feedback_entry['score_threshold'],
            feedback_entry['query_expansion'],
            feedback_entry['system_prompt'],
            feedback_entry['user_prompt'],
            feedback_entry['model'],
            feedback_entry['llm_temperature'],
            feedback_entry['context']
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
    except Exception as e:
        # Fallback to session state if database fails
        if 'feedback_log' not in st.session_state:
            st.session_state.feedback_log = []
        
        feedback_entry['error'] = str(e)
        st.session_state.feedback_log.append(feedback_entry)
        
        # Silent fail - don't disrupt user experience
        print(f"Database logging failed, saved to session state: {e}")

@st.cache_data
def load_questions(test_year):
    """Load the QnA related to that particular year"""
    filepath = os.path.join(DOCUMENTS_DIR, f"{test_year}_civics_test_qa_pairs.json")
    return load_from_json(filepath)