from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from utils.prompts import LLM_JUDGE_SYSTEM_PROMPT, LLM_JUDGE_USER_PROMPT
from utils.rag import llm
from tqdm import tqdm
import time
import numpy as np
from datetime import datetime, timedelta
import pandas as pd

def get_positive_feedback_rate(df):
    """
    Calculate the percentage of positive feedback.
    
    Args:
        df: DataFrame with 'feedback_type' column containing 'positive' or 'negative'
    
    Returns:
        float: Percentage of positive feedback (0-100)
    """
    positive_count = (df['feedback_type'] == 'positive').sum()
    total_count = len(df)
    
    if total_count == 0:
        return 0.0
    
    return (positive_count / total_count)

def add_background_word_count(df):
    """
    Add background_word_count column to DataFrame.
    
    Args:
        df: DataFrame with 'background_info' column
    
    Returns:
        DataFrame: Original DataFrame with new 'background_info_word_count' column added
    """
    df['background_info_word_count'] = df['background_info'].str.split().str.len()
    return df


def add_reason_background_similarity(df):
    """
    Calculate cosine similarity between reason and background_info using TF-IDF.
    Adds 'reason_bkg_info_similarity' column to DataFrame.
    
    Args:
        df: DataFrame with 'reason' and 'background_info' columns
    
    Returns:
        DataFrame: Original DataFrame with new 'reason_bkg_info_similarity' column added
    """
    similarities = []
    
    for idx, row in df.iterrows():
        reason = str(row['reason'])
        background = str(row['background_info'])
        
        # Create TF-IDF vectors
        vectorizer = TfidfVectorizer()
        try:
            tfidf_matrix = vectorizer.fit_transform([reason, background])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        except:
            similarity = 0.0  # Handle edge cases
        
        similarities.append(similarity)
    
    df['reason_bkg_info_similarity'] = similarities
    return df


def run_llm_evaluation(df, model='gpt-4o-mini', temperature=0.5, delay=0.5):
    """ 
    Run llm-as-judge given a model and a temperature. Returns an updated df.
    Note: internally we are populating via user prompt all the background information of that qna
    
    Args:
        df: DataFrame with feedback data
        model: OpenAI model to use (default: gpt-4o-mini)
        temperature: Temperature for LLM (default: 0.5)
        delay: Seconds to wait between API calls to avoid rate limits (default: 0.5)
    
    Returns:
        DataFrame: Copy of original DataFrame with LLM judge columns added
    """
    # Work on a copy to avoid modifying original
    df = df.copy()
    
    evaluations = []
    errors = []

    # Loop through each row with progress bar
    for idx, row in tqdm(df.iterrows(), total=len(df), desc=f"Running {model} evaluations"):
        
        try:
            # Format the user prompt with row data
            llm_judge_user_prompt_formatted = LLM_JUDGE_USER_PROMPT.format(
                question=row['question_text'],
                answers=row['correct_answers'],
                user_state=row['user_state'],
                user_answer=row['user_answer'],
                success=row['success'],
                reason=row['reason'],
                background_info=row['background_info'],
                context=row['context'],
            )
            
            # Call the LLM
            evaluation = llm(
                system_prompt=LLM_JUDGE_SYSTEM_PROMPT,
                user_prompt=llm_judge_user_prompt_formatted,
                model=model,
                temperature=temperature
            )
            
            # Check if LLM returned an error
            if 'error' in evaluation:
                print(f"\n⚠️  Row {idx}: LLM returned error - {evaluation.get('error', 'Unknown error')}")
                errors.append({'idx': idx, 'error': evaluation.get('error', 'Unknown error')})
            
            evaluations.append(evaluation)
            
            # Add delay to avoid rate limits
            time.sleep(delay)
            
        except KeyError as e:
            # Handle missing keys in format string
            print(f"\n❌ Row {idx}: Missing required field - {e}")
            errors.append({'idx': idx, 'error': f'Missing field: {e}'})
            evaluations.append({})
            
        except Exception as e:
            # Catch all other exceptions
            print(f"\n❌ Row {idx}: Unexpected error - {e}")
            errors.append({'idx': idx, 'error': str(e)})
            evaluations.append({})

    # Parse evaluations and add as columns (raw values, no conversion)
    df['llm_judge_grading_context_usage'] = [e.get('answer_context_usage', None) for e in evaluations]
    df['llm_judge_grading_context_usage_reason'] = [e.get('answer_context_usage_reason', '') for e in evaluations]
    df['llm_judge_grading_context_usage_confidence'] = [e.get('answer_context_usage_confidence', None) for e in evaluations]

    df['llm_judge_grading_accuracy'] = [e.get('grading_accuracy', None) for e in evaluations]
    df['llm_judge_grading_accuracy_reason'] = [e.get('grading_accuracy_reason', '') for e in evaluations]
    df['llm_judge_grading_accuracy_confidence'] = [e.get('grading_accuracy_confidence', None) for e in evaluations]

    df['llm_judge_background_info_quality'] = [e.get('background_info_quality', None) for e in evaluations]
    df['llm_judge_background_info_quality_reason'] = [e.get('background_info_quality_reason', '') for e in evaluations]
    df['llm_judge_background_info_quality_confidence'] = [e.get('background_info_quality_confidence', None) for e in evaluations]

    df['llm_judge_background_context_usage'] = [e.get('background_context_usage', None) for e in evaluations]
    df['llm_judge_background_context_usage_reason'] = [e.get('background_context_usage_reason', '') for e in evaluations]
    df['llm_judge_background_context_usage_confidence'] = [e.get('background_context_usage_confidence', None) for e in evaluations]
    
    # Store raw evaluations for reference
    df['llm_judge_raw'] = evaluations
    
    # convert scores to binary
    df['grading_context_binary'] = df['llm_judge_grading_context_usage'].apply(convert_to_binary)
    df['grading_accuracy_binary'] = df['llm_judge_grading_accuracy'].apply(convert_to_binary)
    df['background_quality_binary'] = df['llm_judge_background_info_quality'].apply(convert_to_binary)
    df['background_context_binary'] = df['llm_judge_background_context_usage'].apply(convert_to_binary)

    # Print summary
    print(f"\n{'='*50}")
    print(f"✅ Completed {len(evaluations)} evaluations with {model}")
    print(f"   Temperature: {temperature}")
    print(f"   Delay: {delay}s per request")
    
    if errors:
        print(f"\n⚠️  Encountered {len(errors)} errors:")
        for err in errors[:5]:  # Show first 5 errors
            print(f"   - Row {err['idx']}: {err['error']}")
        if len(errors) > 5:
            print(f"   ... and {len(errors) - 5} more errors")
    else:
        print(f"   No errors! 🎉")
    
    print(f"{'='*50}\n")
    
    return df

def convert_to_binary(value):
    value_str = str(value).lower().strip()
    return 1 if value_str in ['yes', 'good'] else (0 if value_str in ['no', 'bad'] else np.nan)

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
                    feedback_timestamp, 
                    evaluation_version
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    feedback_timestamp = EXCLUDED.feedback_timestamp,
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
                row.get('timestamp'),
                'v1.0'  # version tracking for evaluation logic
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
                int(total_feedback),
                float(positive_feedback_rate),
                float(mean_background_word_count),
                float(mean_similarity),
                float(grading_context_pass_rate),
                float(grading_accuracy_pass_rate),
                float(background_quality_pass_rate),
                float(background_context_pass_rate)
            ))
        
        conn.commit()
        print(f"✅ Saved daily aggregates for {len(df.groupby('eval_date'))} date(s)")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error saving results: {e}")
        raise
    
    finally:
        cur.close()
