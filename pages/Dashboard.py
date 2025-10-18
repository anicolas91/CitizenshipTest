import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import psycopg2
from utils.evaluation import convert_to_binary

# Page config
st.set_page_config(
    page_title="📊 Evaluation Dashboard",
    page_icon="📊",
    layout="wide"
)

# ============================================================================
# DATA LOADING FROM NEON POSTGRES
# ============================================================================

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_metrics_from_db(days=30):
    """Load daily metrics summary from Neon Postgres"""
    try:
        # Get database URL from Streamlit secrets
        database_url = st.secrets["database"]["url"]
        
        # Connect to database
        conn = psycopg2.connect(database_url)
        
        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Query daily metrics
        query = """
            SELECT 
                date,
                feedback_count,
                positive_feedback_rate,
                mean_background_word_count,
                mean_similarity,
                grading_context_pass_rate,
                grading_accuracy_pass_rate,
                background_quality_pass_rate,
                background_context_pass_rate
            FROM daily_metrics_summary
            WHERE date >= %s AND date <= %s
            ORDER BY date ASC
        """
        
        df = pd.read_sql(query, conn, params=(start_date, end_date))
        conn.close()
        
        return df
        
    except Exception as e:
        st.error(f"Error loading data from database: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_individual_evaluations(days=30):
    """Load individual evaluations from Neon Postgres"""
    try:
        # Get database URL from Streamlit secrets
        database_url = st.secrets["database"]["url"]
        
        # Connect to database
        conn = psycopg2.connect(database_url)
        
        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Query daily metrics
        query = """
            SELECT 
                evaluation_date,
                question,
                correct_answers,
                user_answer,
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
                feedback_timestamp
            FROM evaluations
            WHERE evaluation_date >= %s AND evaluation_date <= %s
            ORDER BY feedback_timestamp ASC
        """
        
        df = pd.read_sql(query, conn, params=(start_date, end_date))
        conn.close()
        
        return df
        
    except Exception as e:
        st.error(f"Error loading data from database: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error


# ============================================================================
# MAIN DASHBOARD
# ============================================================================

st.title("📊 Bot Evaluation Dashboard")
st.write("Track daily performance metrics based on user feedback")

# Sidebar filters
with st.sidebar:
    st.header("⚙️ Filters")
    
    # Date range selector
    date_range = st.selectbox(
        "Select time range:",
        options=["Last 7 days", "Last 14 days", "Last 30 days", "Last 90 days"],
        index=2
    )
    
    # Map selection to days
    days_map = {
        "Last 7 days": 7,
        "Last 14 days": 14,
        "Last 30 days": 30,
        "Last 90 days": 90
    }
    selected_days = days_map[date_range]
    
    st.write("---")
    
    # Refresh button
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    st.caption("💡 Tip: Metrics are calculated daily from user feedback (👍/👎)")
    st.caption("🔄 Data is cached for 5 minutes. Click 'Refresh Data' to force update.")

# Load data from database
with st.spinner("Loading metrics from database..."):
    df = load_metrics_from_db(days=selected_days)
    df_individual = load_individual_evaluations(days=selected_days)

# Check if data was loaded
if df.empty:
    st.warning("⚠️ No evaluation data found. Run the evaluation script to generate metrics.")
    st.code("python scripts/evaluate.py --date 2025-10-16", language="bash")
    st.stop()

# Display data info
st.success(f"✅ Loaded {len(df)} days of evaluation data")

# Calculate summary stats for the selected period
latest_data = df.iloc[-1]
previous_data = df.iloc[-2] if len(df) > 1 else latest_data

# ============================================================================
# METRIC CARDS - Row 1: Quantitative Metrics
# ============================================================================

st.subheader("📈 Quantitative Metrics")

col1, col2, col3 = st.columns(3)

with col1:
    current_feedback = latest_data['positive_feedback_rate']
    prev_feedback = previous_data['positive_feedback_rate']
    delta_feedback = current_feedback - prev_feedback
    
    st.metric(
        label="Positive Feedback Rate",
        value=f"{current_feedback:.1%}",
        delta=f"{delta_feedback:+.1%}",
        help="Percentage of 👍 ratings vs total feedback"
    )

with col2:
    current_words = latest_data['mean_background_word_count']
    prev_words = previous_data['mean_background_word_count']
    delta_words = current_words - prev_words
    
    st.metric(
        label="Background Info Word Count",
        value=f"{current_words:.1f}",
        delta=f"{delta_words:+.1f}",
        help="Average number of words in background information"
    )

with col3:
    current_sim = latest_data['mean_similarity']
    prev_sim = previous_data['mean_similarity']
    delta_sim = current_sim - prev_sim
    
    st.metric(
        label="Reason-Background Similarity",
        value=f"{current_sim:.2f}",
        delta=f"{delta_sim:+.2f}",
        help="Semantic similarity between reasoning and background info"
    )

st.write("---")

# ============================================================================
# METRIC CARDS - Row 2: Qualitative Metrics (LLM-as-Judge)
# ============================================================================

st.subheader("🤖 Qualitative Metrics (LLM-as-Judge)")

col1, col2, col3, col4 = st.columns(4)

with col1:
    current = latest_data['grading_context_pass_rate']
    prev = previous_data['grading_context_pass_rate']
    delta = current - prev
    
    st.metric(
        label="Grading Context Usage",
        value=f"{current:.1%}",
        delta=f"{delta:+.1%}",
        help="Proper use of context in grading (Yes rate)"
    )

with col2:
    current = latest_data['grading_accuracy_pass_rate']
    prev = previous_data['grading_accuracy_pass_rate']
    delta = current - prev
    
    st.metric(
        label="Grading Accuracy",
        value=f"{current:.1%}",
        delta=f"{delta:+.1%}",
        help="Quality of grading decisions (Good rate)"
    )

with col3:
    current = latest_data['background_quality_pass_rate']
    prev = previous_data['background_quality_pass_rate']
    delta = current - prev
    
    st.metric(
        label="Background Quality",
        value=f"{current:.1%}",
        delta=f"{delta:+.1%}",
        help="Quality of background information (Good rate)"
    )

with col4:
    current = latest_data['background_context_pass_rate']
    prev = previous_data['background_context_pass_rate']
    delta = current - prev
    
    st.metric(
        label="Background Context Usage",
        value=f"{current:.1%}",
        delta=f"{delta:+.1%}",
        help="Background uses retrieved context (Yes rate)"
    )

st.write("---")

# ============================================================================
# TREND CHARTS
# ============================================================================

st.subheader("📊 Metric Trends Over Time")

# Create tabs for different metric groups
tab1, tab2, tab3 = st.tabs(["Daily Aggregates", "Individual Data Points", "Distributions"])

with tab1:
    st.markdown("**Daily aggregated metrics from `daily_metrics_summary` table**")
    
    # Positive Feedback Rate Chart
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=df['date'],
        y=df['positive_feedback_rate'] * 100,
        mode='lines+markers',
        name='Positive Feedback Rate',
        line=dict(color='#2ecc71', width=2),
        marker=dict(size=6)
    ))
    fig1.update_layout(
        title="Positive Feedback Rate (%) - Daily Average",
        xaxis_title="Date",
        yaxis_title="Rate (%)",
        hovermode='x unified',
        height=300
    )
    st.plotly_chart(fig1, use_container_width=True)
    
    # Background Word Count & Similarity
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=df['date'],
        y=df['mean_background_word_count'],
        mode='lines+markers',
        name='Avg Word Count',
        yaxis='y',
        line=dict(color='#3498db', width=2)
    ))
    fig2.add_trace(go.Scatter(
        x=df['date'],
        y=df['mean_similarity'],
        mode='lines+markers',
        name='Similarity Score',
        yaxis='y2',
        line=dict(color='#e74c3c', width=2)
    ))
    fig2.update_layout(
        title="Background Word Count & Reason-Background Similarity - Daily Average",
        xaxis_title="Date",
        yaxis=dict(title="Word Count", side='left'),
        yaxis2=dict(title="Similarity", overlaying='y', side='right'),
        hovermode='x unified',
        height=300
    )
    st.plotly_chart(fig2, use_container_width=True)
    
    # All qualitative metrics in one chart
    fig3 = go.Figure()
    
    metrics = [
        ('grading_context_pass_rate', 'Grading Context Usage', '#9b59b6'),
        ('grading_accuracy_pass_rate', 'Grading Accuracy', '#e67e22'),
        ('background_quality_pass_rate', 'Background Quality', '#1abc9c'),
        ('background_context_pass_rate', 'Background Context Usage', '#34495e')
    ]
    
    for metric_col, metric_name, color in metrics:
        fig3.add_trace(go.Scatter(
            x=df['date'],
            y=df[metric_col] * 100,
            mode='lines+markers',
            name=metric_name,
            line=dict(width=2, color=color),
            marker=dict(size=5)
        ))
    
    fig3.update_layout(
        title="LLM-as-Judge Metrics (%) - Daily Average",
        xaxis_title="Date",
        yaxis_title="Pass/Good/Yes Rate (%)",
        hovermode='x unified',
        height=400,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    st.plotly_chart(fig3, use_container_width=True)

with tab2:
    st.markdown("**Individual evaluation records from `evaluations` table**")
    
    if df_individual.empty:
        st.warning("No individual evaluation data available.")
    else:
        # Convert LLM judge scores to binary
        df_individual['grading_context_binary'] = df_individual['grading_context_score'].apply(convert_to_binary)
        df_individual['grading_accuracy_binary'] = df_individual['grading_accuracy_score'].apply(convert_to_binary)
        df_individual['background_quality_binary'] = df_individual['background_quality_score'].apply(convert_to_binary)
        df_individual['background_context_binary'] = df_individual['background_context_score'].apply(convert_to_binary)
        
        # Color scheme
        colors = {'positive': '#2ecc71', 'negative': '#e74c3c'}
        
        st.markdown("### Quantitative Metrics Over Time")

        # Scatter plot: Background Word Count over time
        fig4 = go.Figure()
        
        for feedback_type in df_individual['user_feedback'].unique():
            subset = df_individual[df_individual['user_feedback'] == feedback_type]
            fig4.add_trace(go.Scatter(
                x=subset['feedback_timestamp'],  # Use actual timestamp
                y=subset['background_word_count'],
                mode='markers',
                name=f'{feedback_type.capitalize()} Feedback',
                marker=dict(
                    size=8,
                    color=colors.get(feedback_type, '#95a5a6'),
                    opacity=0.6
                ),
                text=subset['feedback_timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S'),
                hovertemplate='<b>%{text}</b><br>Word Count: %{y}<extra></extra>'
            ))
        
        fig4.update_layout(
            title="Background Word Count - Individual Evaluations (by Feedback Time)",
            xaxis_title="Feedback Timestamp",
            yaxis_title="Word Count",
            hovermode='closest',
            height=350
        )
        st.plotly_chart(fig4, use_container_width=True)
        
        # Scatter plot: Similarity over time
        fig5 = go.Figure()
        
        for feedback_type in df_individual['user_feedback'].unique():
            subset = df_individual[df_individual['user_feedback'] == feedback_type]
            fig5.add_trace(go.Scatter(
                x=subset['feedback_timestamp'],  # Use actual timestamp
                y=subset['reason_background_similarity'],
                mode='markers',
                name=f'{feedback_type.capitalize()} Feedback',
                marker=dict(
                    size=8,
                    color=colors.get(feedback_type, '#95a5a6'),
                    opacity=0.6
                ),
                text=subset['feedback_timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S'),
                hovertemplate='<b>%{text}</b><br>Similarity: %{y:.3f}<extra></extra>'
            ))
        
        fig5.update_layout(
            title="Reason-Background Similarity - Individual Evaluations (by Feedback Time)",
            xaxis_title="Feedback Timestamp",
            yaxis_title="Similarity Score",
            hovermode='closest',
            height=350
        )
        st.plotly_chart(fig5, use_container_width=True)

        st.write("---")
        st.markdown("### LLM-as-Judge Metrics Over Time")
        
        # Create 2x2 grid for LLM judge metrics
        col1, col2 = st.columns(2)
        
        with col1:
            # Scatter plot: Grading Context Usage
            fig6 = go.Figure()
            
            for feedback_type in df_individual['user_feedback'].unique():
                subset = df_individual[df_individual['user_feedback'] == feedback_type]
                fig6.add_trace(go.Scatter(
                    x=subset['feedback_timestamp'],
                    y=subset['grading_context_binary'],
                    mode='markers',
                    name=f'{feedback_type.capitalize()} Feedback',
                    marker=dict(
                        size=10,
                        color=colors.get(feedback_type, '#95a5a6'),
                        opacity=0.6
                    ),
                    text=subset['grading_context_score'],
                    hovertemplate='<b>%{x}</b><br>Score: %{text}<br>Binary: %{y}<extra></extra>'
                ))
            
            fig6.update_layout(
                title="Grading Context Usage",
                xaxis_title="Feedback Timestamp",
                yaxis_title="Binary Score (0=No, 1=Yes)",
                yaxis=dict(tickvals=[0, 1], ticktext=['No', 'Yes']),
                hovermode='closest',
                height=300
            )
            st.plotly_chart(fig6, use_container_width=True)
        
        with col2:
            # Scatter plot: Grading Accuracy
            fig7 = go.Figure()
            
            for feedback_type in df_individual['user_feedback'].unique():
                subset = df_individual[df_individual['user_feedback'] == feedback_type]
                fig7.add_trace(go.Scatter(
                    x=subset['feedback_timestamp'],
                    y=subset['grading_accuracy_binary'],
                    mode='markers',
                    name=f'{feedback_type.capitalize()} Feedback',
                    marker=dict(
                        size=10,
                        color=colors.get(feedback_type, '#95a5a6'),
                        opacity=0.6
                    ),
                    text=subset['grading_accuracy_score'],
                    hovertemplate='<b>%{x}</b><br>Score: %{text}<br>Binary: %{y}<extra></extra>'
                ))
            
            fig7.update_layout(
                title="Grading Accuracy",
                xaxis_title="Feedback Timestamp",
                yaxis_title="Binary Score (0=Bad, 1=Good)",
                yaxis=dict(tickvals=[0, 1], ticktext=['Bad', 'Good']),
                hovermode='closest',
                height=300
            )
            st.plotly_chart(fig7, use_container_width=True)
        
        col3, col4 = st.columns(2)
        
        with col3:
            # Scatter plot: Background Quality
            fig8 = go.Figure()
            
            for feedback_type in df_individual['user_feedback'].unique():
                subset = df_individual[df_individual['user_feedback'] == feedback_type]
                fig8.add_trace(go.Scatter(
                    x=subset['feedback_timestamp'],
                    y=subset['background_quality_binary'],
                    mode='markers',
                    name=f'{feedback_type.capitalize()} Feedback',
                    marker=dict(
                        size=10,
                        color=colors.get(feedback_type, '#95a5a6'),
                        opacity=0.6
                    ),
                    text=subset['background_quality_score'],
                    hovertemplate='<b>%{x}</b><br>Score: %{text}<br>Binary: %{y}<extra></extra>'
                ))
            
            fig8.update_layout(
                title="Background Info Quality",
                xaxis_title="Feedback Timestamp",
                yaxis_title="Binary Score (0=Bad, 1=Good)",
                yaxis=dict(tickvals=[0, 1], ticktext=['Bad', 'Good']),
                hovermode='closest',
                height=300
            )
            st.plotly_chart(fig8, use_container_width=True)
        
        with col4:
            # Scatter plot: Background Context Usage
            fig9 = go.Figure()
            
            for feedback_type in df_individual['user_feedback'].unique():
                subset = df_individual[df_individual['user_feedback'] == feedback_type]
                fig9.add_trace(go.Scatter(
                    x=subset['feedback_timestamp'],
                    y=subset['background_context_binary'],
                    mode='markers',
                    name=f'{feedback_type.capitalize()} Feedback',
                    marker=dict(
                        size=10,
                        color=colors.get(feedback_type, '#95a5a6'),
                        opacity=0.6
                    ),
                    text=subset['background_context_score'],
                    hovertemplate='<b>%{x}</b><br>Score: %{text}<br>Binary: %{y}<extra></extra>'
                ))
            
            fig9.update_layout(
                title="Background Context Usage",
                xaxis_title="Feedback Timestamp",
                yaxis_title="Binary Score (0=No, 1=Yes)",
                yaxis=dict(tickvals=[0, 1], ticktext=['No', 'Yes']),
                hovermode='closest',
                height=300
            )
            st.plotly_chart(fig9, use_container_width=True)


with tab3:
    st.markdown("**Distribution analysis from `evaluations` table**")
    
    if df_individual.empty:
        st.warning("No individual evaluation data available.")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            # Histogram: Background Word Count
            fig6 = go.Figure()
            fig6.add_trace(go.Histogram(
                x=df_individual['background_word_count'],
                nbinsx=20,
                marker_color='#3498db',
                opacity=0.7,
                name='Word Count'
            ))
            fig6.update_layout(
                title="Distribution of Background Word Count",
                xaxis_title="Word Count",
                yaxis_title="Frequency",
                height=300
            )
            st.plotly_chart(fig6, use_container_width=True)
        
        with col2:
            # Histogram: Similarity
            fig7 = go.Figure()
            fig7.add_trace(go.Histogram(
                x=df_individual['reason_background_similarity'],
                nbinsx=20,
                marker_color='#e74c3c',
                opacity=0.7,
                name='Similarity'
            ))
            fig7.update_layout(
                title="Distribution of Similarity Scores",
                xaxis_title="Similarity Score",
                yaxis_title="Frequency",
                height=300
            )
            st.plotly_chart(fig7, use_container_width=True)
        
        # Count plot: LLM Judge Scores
        st.subheader("LLM-as-Judge Score Distributions")
        
        score_cols = [
            ('grading_context_score', 'Context Usage'),
            ('grading_accuracy_score', 'Grading Accuracy'),
            ('background_quality_score', 'Background Quality'),
            ('background_context_score', 'Background Context')
        ]
        
        col1, col2 = st.columns(2)
        
        for idx, (col_name, title) in enumerate(score_cols):
            with col1 if idx % 2 == 0 else col2:
                if col_name in df_individual.columns:
                    counts = df_individual[col_name].value_counts().sort_index()
                    
                    fig = go.Figure(data=[
                        go.Bar(
                            x=counts.index,
                            y=counts.values,
                            marker_color='#9b59b6',
                            opacity=0.7
                        )
                    ])
                    fig.update_layout(
                        title=title,
                        xaxis_title="Score",
                        yaxis_title="Count",
                        height=250
                    )
                    st.plotly_chart(fig, use_container_width=True)

st.write("---")
# ============================================================================
# SUMMARY TABLE
# ============================================================================

st.subheader("📋 Daily Breakdown")

# Prepare display dataframe
display_df = df.copy()
display_df['date'] = display_df['date'].astype(str)
display_df['positive_feedback_rate'] = (display_df['positive_feedback_rate'] * 100).round(1).astype(str) + '%'
display_df['mean_background_word_count'] = display_df['mean_background_word_count'].round(1)
display_df['mean_similarity'] = display_df['mean_similarity'].round(2)
display_df['grading_context_pass_rate'] = (display_df['grading_context_pass_rate'] * 100).round(1).astype(str) + '%'
display_df['grading_accuracy_pass_rate'] = (display_df['grading_accuracy_pass_rate'] * 100).round(1).astype(str) + '%'
display_df['background_quality_pass_rate'] = (display_df['background_quality_pass_rate'] * 100).round(1).astype(str) + '%'
display_df['background_context_pass_rate'] = (display_df['background_context_pass_rate'] * 100).round(1).astype(str) + '%'

# Rename columns for display
display_df.columns = [
    'Date',
    'Feedback Count',
    'Positive Rate',
    'Avg Words',
    'Similarity',
    'GR Context',
    'GR Accuracy',
    'BG Quality',
    'BG Context'
]

# Show last 10 days by default
st.dataframe(
    display_df.tail(10).sort_values('Date', ascending=False),
    use_container_width=True,
    hide_index=True
)

# Download button
csv = df.to_csv(index=False)
st.download_button(
    label="📥 Download Full Data (CSV)",
    data=csv,
    file_name=f"evaluation_metrics_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv"
)

# ============================================================================
# FOOTER
# ============================================================================

st.write("---")
st.caption("🔄 Dashboard updates daily with new evaluation results | Last updated: " + 
           datetime.now().strftime("%Y-%m-%d %H:%M:%S"))