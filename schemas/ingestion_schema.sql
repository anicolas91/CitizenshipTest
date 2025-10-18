CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    
    -- User context
    user_state VARCHAR(50),
    test_year VARCHAR(4),
    
    -- Question & Answer
    question_text TEXT,
    correct_answers TEXT,
    user_answer TEXT,
    
    -- Evaluation results
    success BOOLEAN,
    reason TEXT,
    background_info TEXT,
    
    -- User feedback
    feedback_type VARCHAR(20),
    
    -- Session info
    session_id VARCHAR(100),
    
    -- RAG configuration
    rag_context_limit INTEGER,
    rag_score_threshold FLOAT,
    rag_query_expansion BOOLEAN,
    
    -- LLM inputs (for debugging/monitoring)
    system_prompt TEXT,
    user_prompt TEXT,
    model VARCHAR(50),
    llm_temperature FLOAT,
    context TEXT
);