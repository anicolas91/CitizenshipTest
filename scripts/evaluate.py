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
import os
import sys
from pathlib import Path

# Add project root to path
SCRIPT_DIR = Path(__file__).parent.resolve()  # scripts/
PROJECT_ROOT = SCRIPT_DIR.parent              # CitizenshipTest/
sys.path.append(str(PROJECT_ROOT))

from utils.evaluation import (
    add_background_word_count, 
    add_reason_background_similarity, 
    run_llm_evaluation,
    get_date_filter,
    load_feedback_data,
    save_evaluation_results
)

#add the rest of the libraries 
import argparse
import psycopg2
from dotenv import load_dotenv

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
    
    conn.close()
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
    conn = psycopg2.connect(DATABASE_URL)
    save_evaluation_results(df, conn)

    # Close connection
    conn.close()
    print("\n✅ Database connection closed")
    print("🎉 Pipeline complete!")

if __name__ == "__main__":
    main()