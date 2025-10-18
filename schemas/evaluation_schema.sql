-- ============================================================================
-- EVALUATION TABLES SCHEMA
-- For US Civics Test Bot Evaluation System
-- ============================================================================

-- Drop tables if they exist (careful with this in production!)
-- Uncomment these lines if you need to recreate the tables
-- DROP TABLE IF EXISTS daily_metrics_summary CASCADE;
-- DROP TABLE IF EXISTS evaluations CASCADE;

-- ============================================================================
-- TABLE 1: evaluations
-- Stores individual evaluation results for each feedback entry
-- ============================================================================

CREATE TABLE IF NOT EXISTS evaluations (
    id SERIAL PRIMARY KEY,
    feedback_id INTEGER UNIQUE NOT NULL REFERENCES feedback(id),
    evaluation_date DATE NOT NULL,
    
    -- Original question/answer data (for reference)
    question TEXT,
    correct_answers TEXT,
    user_answer TEXT,
    user_state VARCHAR(100),
    success BOOLEAN,
    reason TEXT,
    user_feedback VARCHAR(20),  -- 'positive' or 'negative'
    
    -- Quantitative Metrics
    background_word_count INTEGER,
    reason_background_similarity FLOAT,
    
    -- Qualitative Metrics: Grading Context Usage
    grading_context_score VARCHAR(10),   -- 'yes', 'no', etc.
    grading_context_reason TEXT,
    
    -- Qualitative Metrics: Grading Accuracy
    grading_accuracy_score VARCHAR(10),  -- 'good', 'bad', etc.
    grading_accuracy_reason TEXT,
    
    -- Qualitative Metrics: Background Info Quality
    background_quality_score VARCHAR(10),
    background_quality_reason TEXT,
    
    -- Qualitative Metrics: Background Context Usage
    background_context_score VARCHAR(10),
    background_context_reason TEXT,
    
    -- Timestamp from original feedback
    feedback_timestamp TIMESTAMP,

    -- Metadata
    evaluation_version VARCHAR(50) DEFAULT 'v1.0',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_evaluations_date ON evaluations(evaluation_date);
CREATE INDEX IF NOT EXISTS idx_evaluations_feedback_id ON evaluations(feedback_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_user_feedback ON evaluations(user_feedback);

-- ============================================================================
-- TABLE 2: daily_metrics_summary
-- Stores aggregated daily metrics for dashboard
-- ============================================================================

CREATE TABLE IF NOT EXISTS daily_metrics_summary (
    date DATE PRIMARY KEY,
    feedback_count INTEGER NOT NULL,
    
    -- Quantitative Metrics (Aggregated)
    positive_feedback_rate FLOAT,           -- 0.0 to 1.0 (e.g., 0.70 = 70%)
    mean_background_word_count FLOAT,
    mean_similarity FLOAT,
    
    -- Qualitative Metrics (Aggregated Pass Rates)
    grading_context_pass_rate FLOAT,        -- 0.0 to 1.0
    grading_accuracy_pass_rate FLOAT,       -- 0.0 to 1.0
    background_quality_pass_rate FLOAT,     -- 0.0 to 1.0
    background_context_pass_rate FLOAT,     -- 0.0 to 1.0
    
    -- Metadata
    calculated_at TIMESTAMP DEFAULT NOW()
);

-- Index for date-based queries
CREATE INDEX IF NOT EXISTS idx_daily_metrics_date ON daily_metrics_summary(date);

-- ============================================================================
-- HELPFUL QUERIES
-- ============================================================================

-- View recent evaluations
-- SELECT * FROM evaluations ORDER BY evaluation_date DESC LIMIT 10;

-- View daily metrics for last 30 days
-- SELECT * FROM daily_metrics_summary 
-- WHERE date >= CURRENT_DATE - INTERVAL '30 days'
-- ORDER BY date DESC;

-- Check evaluation coverage
-- SELECT 
--     evaluation_date,
--     COUNT(*) as evaluation_count,
--     SUM(CASE WHEN user_feedback = 'positive' THEN 1 ELSE 0 END) as positive_count
-- FROM evaluations
-- GROUP BY evaluation_date
-- ORDER BY evaluation_date DESC;

-- ============================================================================
-- NOTES
-- ============================================================================
-- 1. The 'feedback' table must exist before running this (it's your source table)
-- 2. ON CONFLICT clauses in evaluate.py ensure safe re-runs
-- 3. Rates are stored as decimals (0-1), multiply by 100 for percentages
-- 4. All timestamps are in UTC by default