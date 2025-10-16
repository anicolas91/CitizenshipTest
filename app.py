# streamlit run app.py

# import main libraries
import os
import random
import streamlit as st

# Set all secrets as environment variables
for key, value in st.secrets.items():
    os.environ[key] = value

# Import from your existing utils
from utils.rag import rag
from utils.prompts import USCIS_OFFICER_SYSTEM_PROMPT, USCIS_OFFICER_USER_PROMPT
from utils.streamlit import (
    US_LOCATIONS, 
    RAG_CONFIG,
    reset_quiz_state, 
    reset_all_state, 
    check_test_completion, 
    log_feedback,
    load_questions,
    get_test_requirements)

# Page config (must be first Streamlit command)
st.set_page_config(
    page_title="🇺🇸 USCIS Citizenship Test Prep",
    page_icon="🇺🇸",
    layout="centered"
)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if 'setup_complete' not in st.session_state:
    st.session_state.setup_complete = False
    st.session_state.user_state = None
    st.session_state.test_year = None

# ============================================================================
# SETUP SCREEN
# ============================================================================

if not st.session_state.setup_complete:
    st.title("🇺🇸 USCIS Citizenship Test Preparation")
    st.write("Welcome! Let's personalize your test experience.")
    
    st.write("---")
    
    # Question 1: State
    st.subheader("1️⃣ Which state are you applying from?")
    st.caption("This helps us provide accurate information about your governor, senators, and representatives.")
    
    selected_state = st.selectbox(
        "Select your location:",
        options=[""] + US_LOCATIONS,
        index=0,
        key="state_selector"
    )
    
    st.write("---")
    
    # Question 2: Application date
    st.subheader("2️⃣ When did you submit your N-400 application?")
    st.caption("The cutoff date is October 20, 2025")
    
    application_date = st.radio(
        "I submitted my application:",
        options=[
            "Before October 20, 2025 (Take 2008 test)",
            "On or after October 20, 2025 (Take 2025 test)"
        ],
        key="date_selector"
    )
    
    st.write("---")
    
    # Start button
    if st.button("🚀 Start Practice", type="primary", use_container_width=True):
        if not selected_state:
            st.error("⚠️ Please select your state before continuing.")
        else:
            # Save to session state
            st.session_state.user_state = selected_state
            
            # Determine test year
            if "Before" in application_date:
                st.session_state.test_year = "2008"
            else:
                st.session_state.test_year = "2025"
            
            st.session_state.setup_complete = True
            st.rerun()
    
    # Stop here - don't show the rest of the app
    st.stop()

# ============================================================================
# MAIN APP - Quiz Interface
# ============================================================================

# Load questions based on the selected test year
questions = load_questions(st.session_state.test_year)

# Safety check
if not questions:
    st.error("❌ Failed to load questions. Please refresh the page or contact support.")
    st.stop()

# Display setup info in sidebar
with st.sidebar:
    st.header("📋 Your Test Info")
    st.write(f"**State:** {st.session_state.user_state}")
    st.write(f"**Test Version:** {st.session_state.test_year} Civics Test")
    
    st.write("---")
    
    st.warning("⚠️ Changing settings will restart your quiz and clear your progress.")
    
    if st.button("🔄 Change Settings", type="secondary"):
        reset_all_state()
        st.rerun()
    
    st.write("---")

# Main app title
st.title("🇺🇸 USCIS Citizenship Test Preparation")
st.write(f"Practicing with the **{st.session_state.test_year} Civics Test**")

# Initialize quiz session state
if 'question' not in st.session_state:
    st.session_state.question = random.choice(questions)
    st.session_state.answered = False
    st.session_state.total_attempted = 0
    st.session_state.total_correct = 0
    st.session_state.total_incorrect = 0
    st.session_state.question_counter = 0
    st.session_state.asked_questions = [st.session_state.question]
    st.session_state.test_complete = False
    st.session_state.test_passed = False
    st.session_state.feedback_given = False

# CHECK IF TEST IS COMPLETE - Show completion screen
if st.session_state.test_complete:
    if st.session_state.test_passed:
        st.balloons()  # Celebrate!
        st.success("# 🎉 Congratulations! You Passed!")
        st.write(f"You answered **{st.session_state.total_correct}** questions correctly!")
        st.write("You're ready for your citizenship test! 🇺🇸")
    else:
        st.error("# 📚 Keep Practicing!")
        st.write(f"You got **{st.session_state.total_incorrect}** questions wrong.")
        st.write("Don't worry, practice makes perfect!")
    
    # Show test details
    test_reqs = get_test_requirements(st.session_state.test_year)
    st.info(f"**{test_reqs['name']} Rules:**\n- Need {test_reqs['passing']} correct out of {test_reqs['total']} questions\n- You got {st.session_state.total_correct} correct")

    st.write("---")
    
    # Restart button
    if st.button("🔄 Start New Test", type="primary", use_container_width=True):
        reset_quiz_state()
        st.rerun()
    
    st.stop()  # Don't show the quiz interface

# Display question
st.subheader("Question:")
st.write(st.session_state.question.get('question', 'No question found'))

# Answer input with unique key based on question counter
user_answer = st.text_input(
    "Your answer:",
    disabled=st.session_state.answered,
    key=f"answer_input_{st.session_state.question_counter}"
)

# Create button row with Submit, Next/Results, and Feedback buttons
col1, col2, col3, col4 = st.columns([2, 2, 0.5, 0.5])

with col1:
    if st.button("Submit Answer", disabled=st.session_state.answered or not user_answer.strip()):

        with st.spinner("Evaluating your answer..."):
            # Call your RAG function
            result = rag(
                user_prompt=USCIS_OFFICER_USER_PROMPT,
                system_prompt=USCIS_OFFICER_SYSTEM_PROMPT,
                question=st.session_state.question.get('question', ''),
                answers=st.session_state.question.get('answers', ''),
                user_state=st.session_state.user_state,
                user_answer=user_answer,
                **RAG_CONFIG
            )
            
            # Store results in session state
            st.session_state.result = result
            st.session_state.user_answer_text = user_answer
            st.session_state.answered = True
            st.session_state.total_attempted += 1
            st.session_state.feedback_given = False 
            
            # Check if passed - FIXED: removed .lower()
            if 'error' not in result:
                success = result.get('success', False)
                if success:
                    st.session_state.total_correct += 1
                else:
                    st.session_state.total_incorrect += 1
                
                # Check if test is complete
                check_test_completion()
            
            st.rerun()

with col2:
    # Check if test WOULD BE complete (but don't set state yet)
    would_be_complete, would_pass = check_test_completion()

    # Determine button text and type based on test completion status
    if would_be_complete and st.session_state.answered:
        button_text = "📊 See Test Results"
        button_type = "primary"
    else:
        button_text = "Next Question"
        button_type = "secondary"

    if st.button(button_text, disabled=not st.session_state.answered, type=button_type):
        # If test WOULD BE complete, set the state and show results
        if would_be_complete:
            st.session_state.test_complete = True
            st.session_state.test_passed = would_pass
            st.rerun()
        else:
            # Continue to next question
            # Get list of unasked questions
            unasked = [q for q in questions if q not in st.session_state.asked_questions]
            
            # If all questions asked, reset and start over
            if not unasked:
                st.session_state.asked_questions = []
                unasked = questions
                st.toast("🎉 You've completed all questions! Starting over...")
            
            # Pick from unasked questions
            st.session_state.question = random.choice(unasked)
            st.session_state.asked_questions.append(st.session_state.question)
            
            st.session_state.answered = False
            st.session_state.question_counter += 1
            st.session_state.feedback_given = False
            if 'result' in st.session_state:
                del st.session_state.result
            if 'user_answer_text' in st.session_state:
                del st.session_state.user_answer_text
            st.rerun()

with col3:
    # Thumbs up button - disabled until answer is submitted and no feedback given yet
    thumbs_up_disabled = not st.session_state.answered or st.session_state.feedback_given
    if st.button("👍", disabled=thumbs_up_disabled, key=f"thumbs_up_{st.session_state.question_counter}", help="Good bot"):
        log_feedback('positive')
        st.toast("✅ Thanks for your feedback!")
        st.rerun()

with col4:
    # Thumbs down button - disabled until answer is submitted and no feedback given yet
    thumbs_down_disabled = not st.session_state.answered or st.session_state.feedback_given
    if st.button("👎", disabled=thumbs_down_disabled, key=f"thumbs_down_{st.session_state.question_counter}", help="Bad bot"):
        log_feedback('negative')
        st.toast("📝 Thanks for your feedback!")
        st.rerun()

# Show feedback confirmation
if st.session_state.answered and st.session_state.feedback_given:
    st.caption("✓ Feedback recorded - thank you!")
elif st.session_state.answered:
    st.caption("Was this evaluation helpful? 👍 👎")
else:
    st.caption("Answer the question to provide feedback")

# Show results if answered
if st.session_state.answered and 'result' in st.session_state:
    result = st.session_state.result
    
    # Check for errors
    if 'error' in result:
        st.error(f"❌ Error: {result['error']}")
    else:
        # Display results
        success = result.get('success', False)
        reason = result.get('reason', '')
        background_info = result.get('background_info', '')

        # Show reason with tick or X
        if success:
            st.success(f"✅ {reason}")
        else:
            st.error(f"❌ {reason}")
        
        # Show user's answer
        st.info(f"**Your answer:** {st.session_state.user_answer_text}")
        
        # Show correct answer
        st.info(f"**Correct answer(s):** {st.session_state.question.get('answers', 'N/A')}")
        
        # Background info in a box
        st.write("---")
        st.info(f"📚 **Did you know?**\n\n{background_info}")

      
# Sidebar with stats
with st.sidebar:
    st.header("📊 Your Progress")
    
    if st.session_state.total_attempted > 0:
        accuracy = (st.session_state.total_correct / st.session_state.total_attempted) * 100
        # Show test-specific progress
        test_reqs = get_test_requirements(st.session_state.test_year)
        st.write(f"**{test_reqs['name']} Progress:**")
        st.write(f"- Need {test_reqs['passing']} correct to pass")
        st.write(f"- Can miss up to {test_reqs['total'] - test_reqs['passing']} questions")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("✅ Correct", st.session_state.total_correct)
        with col2:
            st.metric("❌ Incorrect", st.session_state.total_incorrect)
        
        st.write("---")
        
        st.metric("Questions Attempted", st.session_state.total_attempted)
        st.metric("Accuracy", f"{accuracy:.1f}%")
        
        # Show progress through question bank
        total_questions = len(questions)
        questions_seen = len(st.session_state.asked_questions)
        st.progress(questions_seen / total_questions)
        st.caption(f"{questions_seen} of {total_questions} questions seen")
    else:
        st.write("Start answering questions to see your progress!")
    
    st.write("---")
    st.caption("Made for LLM Zoomcamp 2025")