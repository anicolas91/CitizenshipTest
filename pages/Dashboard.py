import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px

# Page config
st.set_page_config(
    page_title="📊 Evaluation Dashboard",
    page_icon="📊",
    layout="wide"
)

# ============================================================================
# DUMMY DATA GENERATION
# ============================================================================

def generate_dummy_data(days=30):
    """Generate dummy data for the last N days"""
    dates = [(datetime.now() - timedelta(days=x)).date() for x in range(days)]
    dates.reverse()
    
    data = []
    for date in dates:
        # Add some randomness but with trends
        base_feedback = 0.70
        noise = np.random.normal(0, 0.05)
        
        data.append({
            'date': date,
            'feedback_count': np.random.randint(50, 100),
            'positive_feedback_rate': max(0.4, min(0.95, base_feedback + noise)),
            'avg_background_word_count': np.random.normal(29.5, 3),
            'mean_similarity': np.random.normal(0.25, 0.05),
            'grading_context_pass_rate': np.random.normal(0.943, 0.03),
            'grading_accuracy_good_rate': np.random.normal(0.557, 0.05),
            'background_quality_good_rate': np.random.normal(0.786, 0.04),
            'background_context_yes_rate': np.random.normal(0.686, 0.05)
        })
    
    return pd.DataFrame(data)

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
    st.caption("💡 Tip: Metrics are calculated daily from user feedback (👍/👎)")

# Generate data based on selection
df = generate_dummy_data(days=selected_days)

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
    current_words = latest_data['avg_background_word_count']
    prev_words = previous_data['avg_background_word_count']
    delta_words = current_words - prev_words
    
    st.metric(
        label="Avg Background Word Count",
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
        label="Context Usage",
        value=f"{current:.1%}",
        delta=f"{delta:+.1%}",
        help="Proper use of context in grading (Pass rate)"
    )

with col2:
    current = latest_data['grading_accuracy_good_rate']
    prev = previous_data['grading_accuracy_good_rate']
    delta = current - prev
    
    st.metric(
        label="Grading Accuracy",
        value=f"{current:.1%}",
        delta=f"{delta:+.1%}",
        help="Quality of grading decisions (Good rate)"
    )

with col3:
    current = latest_data['background_quality_good_rate']
    prev = previous_data['background_quality_good_rate']
    delta = current - prev
    
    st.metric(
        label="Background Quality",
        value=f"{current:.1%}",
        delta=f"{delta:+.1%}",
        help="Quality of background information (Good rate)"
    )

with col4:
    current = latest_data['background_context_yes_rate']
    prev = previous_data['background_context_yes_rate']
    delta = current - prev
    
    st.metric(
        label="Background Context",
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
tab1, tab2 = st.tabs(["Quantitative Metrics", "Qualitative Metrics"])

with tab1:
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
        title="Positive Feedback Rate (%)",
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
        y=df['avg_background_word_count'],
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
        title="Background Word Count & Reason-Background Similarity",
        xaxis_title="Date",
        yaxis=dict(title="Word Count", side='left'),
        yaxis2=dict(title="Similarity", overlaying='y', side='right'),
        hovermode='x unified',
        height=300
    )
    st.plotly_chart(fig2, use_container_width=True)

with tab2:
    # All qualitative metrics in one chart
    fig3 = go.Figure()
    
    metrics = [
        ('grading_context_pass_rate', 'Context Usage', '#9b59b6'),
        ('grading_accuracy_good_rate', 'Grading Accuracy', '#e67e22'),
        ('background_quality_good_rate', 'Background Quality', '#1abc9c'),
        ('background_context_yes_rate', 'Background Context', '#34495e')
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
        title="LLM-as-Judge Metrics (%)",
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

st.write("---")

# ============================================================================
# SUMMARY TABLE
# ============================================================================

st.subheader("📋 Daily Breakdown")

# Prepare display dataframe
display_df = df.copy()
display_df['date'] = display_df['date'].astype(str)
display_df['positive_feedback_rate'] = (display_df['positive_feedback_rate'] * 100).round(1).astype(str) + '%'
display_df['avg_background_word_count'] = display_df['avg_background_word_count'].round(1)
display_df['mean_similarity'] = display_df['mean_similarity'].round(2)
display_df['grading_context_pass_rate'] = (display_df['grading_context_pass_rate'] * 100).round(1).astype(str) + '%'
display_df['grading_accuracy_good_rate'] = (display_df['grading_accuracy_good_rate'] * 100).round(1).astype(str) + '%'
display_df['background_quality_good_rate'] = (display_df['background_quality_good_rate'] * 100).round(1).astype(str) + '%'
display_df['background_context_yes_rate'] = (display_df['background_context_yes_rate'] * 100).round(1).astype(str) + '%'

# Rename columns for display
display_df.columns = [
    'Date',
    'Feedback Count',
    'Positive Rate',
    'Avg Words',
    'Similarity',
    'Context Usage',
    'Accuracy',
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