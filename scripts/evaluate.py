#!/usr/bin/env python3
"""
Main evaluation pipeline for US Civics Test data.

Downloads data from the neon postgres db, and then calculates the following:

Quantitative Metrics:
- Positive Feedback Rate
- Background Word Count
- Reason-Background Similarity

Qualitative Metrics (LLM-as-Judge)
- Grading use of context
- Grading Accuracy
- Background Info Quality
- Background Use of Context

Usage:
    # Run for yesterday (default - for automated daily runs)
    python scripts/evaluate.py
    
    # Run for specific date (for testing)
    python scripts/evaluate.py --date 2025-10-16
    
    # Run for date range
    python scripts/evaluate.py --start-date 2025-10-16 --end-date 2025-10-17
    
    # Custom model settings
    python scripts/evaluate.py --date 2025-10-16 --model gpt-4o-mini --temperature 0.5
"""

import argparse
import pandas as pd
import psycopg2
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from utils.evaluation import (
    add_background_word_count, 
    add_reason_background_similarity, 
    run_llm_evaluation,
    get_positive_feedback_rate
)

# Load environment variables from .env file
load_dotenv()

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Run evaluation pipeline on feedback data'
    )
    
    # Date arguments
    parser.add_argument(
        '--date',
        type=str,
        help='Specific date to evaluate (YYYY-MM-DD). Defaults to yesterday.'
    )
    
    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date for date range (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--end-date',
        type=str,
        help='End date for date range (YYYY-MM-DD)'
    )
    
    # LLM evaluation arguments
    parser.add_argument(
        '--model',
        type=str,
        default='gpt-4o',
        help='OpenAI model to use for LLM-as-judge evaluations (default: gpt-4o)'
    )
    
    parser.add_argument(
        '--temperature',
        type=float,
        default=0.2,
        help='Temperature for LLM evaluation (default: 0.2)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay between LLM API calls in seconds (default: 1.0)'
    )
    
    return parser.parse_args()

def get_date_filter(args):
    """
    Determine which date(s) to filter on based on arguments.
    Returns: (start_date, end_date) as strings in YYYY-MM-DD format
    """
    if args.start_date and args.end_date:
        # Date range mode
        return args.start_date, args.end_date
    
    elif args.date:
        # Single date mode
        return args.date, args.date
    
    else:
        # Default: yesterday
        yesterday = (datetime.now() - timedelta(days=1)).date()
        yesterday_str = yesterday.strftime('%Y-%m-%d')
        return yesterday_str, yesterday_str

def load_feedback_data(conn, start_date, end_date):
    """
    Load feedback data from database for specified date range.
    
    Args:
        conn: Database connection
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)
    
    Returns:
        DataFrame with feedback data
    """
    query = """
        SELECT * FROM feedback 
        WHERE DATE(timestamp) >= %s 
          AND DATE(timestamp) <= %s
        ORDER BY timestamp DESC
    """
    
    df = pd.read_sql(query, conn, params=(start_date, end_date))
    return df

def save_evaluation_results(df, conn):
    """
    Save evaluation results back to the database.
    
    This function will:
    1. Insert individual evaluation results into 'evaluations' table
    2. Insert daily aggregates into 'daily_metrics_summary' table
    
    Args:
        df: DataFrame with evaluation results (with all new columns)
        conn: Database connection
    """
    cur = conn.cursor()
    
    try:
        # Insert individual evaluation results
        print("\n💾 Saving individual evaluation results...")
        
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO evaluations (
                    feedback_id,
                    evaluation_date,
                    question,
                    correct_answers,
                    user_answer,
                    user_state,
                    success,
                    reason,
                    user_feedback,
                    background_word_count,
                    reason_background_similarity,
                    grading_context_score,
                    grading_context_reason,
                    grading_accuracy_score,
                    grading_accuracy_reason,
                    background_quality_score,
                    background_quality_reason,
                    background_context_score,
                    background_context_reason,
                    evaluation_version
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (feedback_id) 
                DO UPDATE SET
                    question = EXCLUDED.question,
                    correct_answers = EXCLUDED.correct_answers,
                    user_answer = EXCLUDED.user_answer,
                    user_state = EXCLUDED.user_state,
                    success = EXCLUDED.success,
                    reason = EXCLUDED.reason,
                    user_feedback = EXCLUDED.user_feedback,
                    background_word_count = EXCLUDED.background_word_count,
                    reason_background_similarity = EXCLUDED.reason_background_similarity,
                    grading_context_score = EXCLUDED.grading_context_score,
                    grading_context_reason = EXCLUDED.grading_context_reason,
                    grading_accuracy_score = EXCLUDED.grading_accuracy_score,
                    grading_accuracy_reason = EXCLUDED.grading_accuracy_reason,
                    background_quality_score = EXCLUDED.background_quality_score,
                    background_quality_reason = EXCLUDED.background_quality_reason,
                    background_context_score = EXCLUDED.background_context_score,
                    background_context_reason = EXCLUDED.background_context_reason,
                    evaluation_version = EXCLUDED.evaluation_version,
                    created_at = NOW()
            """, (
                row.get('id'),  # feedback_id from original feedback table
                pd.to_datetime(row.get('timestamp')).date(),
                row.get('question_text'),
                row.get('correct_answers'),
                row.get('user_answer'),
                row.get('user_state'),
                row.get('success'),
                row.get('reason'),
                row.get('feedback_type'),
                row.get('background_info_word_count'),
                row.get('reason_bkg_info_similarity'),
                row.get('llm_judge_grading_context_usage'),
                row.get('llm_judge_grading_context_usage_reason'),
                row.get('llm_judge_grading_accuracy'),
                row.get('llm_judge_grading_accuracy_reason'),
                row.get('llm_judge_background_info_quality'),
                row.get('llm_judge_background_info_quality_reason'),
                row.get('llm_judge_background_context_usage'),
                row.get('llm_judge_background_context_usage_reason'),
                'v1.0'  # version tracking for your evaluation logic
            ))
        
        print(f"✅ Saved {len(df)} individual evaluation results")
        
        # Calculate and insert daily aggregates
        print("\n📊 Calculating daily aggregates...")
        
        # Group by date
        df['eval_date'] = pd.to_datetime(df['timestamp']).dt.date
        
        for date, group in df.groupby('eval_date'):
            # Calculate aggregates for this specific date
            total_feedback = len(group)
            positive_feedback_rate = (group['feedback_type'] == 'positive').mean()
            mean_background_word_count = group['background_info_word_count'].mean()
            mean_similarity = group['reason_bkg_info_similarity'].mean()
            
            # Qualitative metrics (using your binary columns)
            grading_context_pass_rate = (group['grading_context_binary'].mean() or 0)
            grading_accuracy_pass_rate = (group['grading_accuracy_binary'].mean() or 0)
            background_quality_pass_rate = (group['background_quality_binary'].mean() or 0)
            background_context_pass_rate = (group['background_context_binary'].mean() or 0)
            
            cur.execute("""
                INSERT INTO daily_metrics_summary (
                    date,
                    feedback_count,
                    positive_feedback_rate,
                    mean_background_word_count,
                    mean_similarity,
                    grading_context_pass_rate,
                    grading_accuracy_pass_rate,
                    background_quality_pass_rate,
                    background_context_pass_rate
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (date) 
                DO UPDATE SET
                    feedback_count = EXCLUDED.feedback_count,
                    positive_feedback_rate = EXCLUDED.positive_feedback_rate,
                    mean_background_word_count = EXCLUDED.mean_background_word_count,
                    mean_similarity = EXCLUDED.mean_similarity,
                    grading_context_pass_rate = EXCLUDED.grading_context_pass_rate,
                    grading_accuracy_pass_rate = EXCLUDED.grading_accuracy_pass_rate,
                    background_quality_pass_rate = EXCLUDED.background_quality_pass_rate,
                    background_context_pass_rate = EXCLUDED.background_context_pass_rate,
                    calculated_at = NOW()
            """, (
                date,
                total_feedback,
                positive_feedback_rate,
                mean_background_word_count,
                mean_similarity,
                grading_context_pass_rate,
                grading_accuracy_pass_rate,
                background_quality_pass_rate,
                background_context_pass_rate
            ))
        
        conn.commit()
        print(f"✅ Saved daily aggregates for {len(df.groupby('eval_date'))} date(s)")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error saving results: {e}")
        raise
    
    finally:
        cur.close()


def main():
    # Parse command line arguments
    args = parse_args()
    
    # Get date filter
    start_date, end_date = get_date_filter(args)
    
    print(f"📅 Evaluating feedback from {start_date} to {end_date}")
    print(f"🤖 Using model: {args.model} (temp={args.temperature}, delay={args.delay}s)")
    print("-" * 60)
    
    # Get the database URL
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    if not DATABASE_URL:
        raise ValueError("❌ DATABASE_URL not found in environment variables")
    
    # Connect to Neon
    conn = psycopg2.connect(DATABASE_URL)
    print("✅ Connected to Neon!")
    
    # Load feedback data for specified date range
    df = load_feedback_data(conn, start_date, end_date)
    
    print(f"📊 Total feedback entries: {len(df)}")
    
    if len(df) == 0:
        print("⚠️  No feedback data found for the specified date range")
        conn.close()
        return
    
    # Show breakdown by feedback type
    if 'feedback_type' in df.columns:
        print("\n👍👎 Feedback breakdown:")
        print(df['feedback_type'].value_counts())
    
    # Run evaluations
    print("\n" + "=" * 60)
    print("🔬 Running evaluations...")
    print("=" * 60)
    
    # 1. Calculate Positive Feedback Rate
    print("\n1️⃣ Calculating Positive Feedback Rate...")
    #positive_rate = get_positive_feedback_rate(df) We actually calculate this when saving results

    # 2. Calculate Background Word Count
    print("2️⃣ Calculating Background Word Count...")
    df = add_background_word_count(df)
    
    # 3. Calculate Reason-Background Similarity
    print("3️⃣ Calculating Reason-Background Similarity...")
    df = add_reason_background_similarity(df)

    # 4. Run LLM-as-Judge for all qualitative metrics
    print("4️⃣ Running LLM-as-Judge evaluations...")
    df = run_llm_evaluation(df, args.model, args.temperature, args.delay)

    print("\n✅ Evaluation calculations complete!")
    
    # Save results back to database
    save_evaluation_results(df, conn)

    # Close connection
    conn.close()
    print("\n✅ Database connection closed")
    print("🎉 Pipeline complete!")

if __name__ == "__main__":
    main()