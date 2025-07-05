import os
import json
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# Load survey URLs from environment
PRE_QUIZ_SURVEY_URL = os.getenv("PRE_QUIZ_SURVEY_URL", "")
POST_QUIZ_SURVEY_URL = os.getenv("POST_QUIZ_SURVEY_URL", "")

# Set page configuration (must be the first Streamlit command)
st.set_page_config(page_title="GenAI ITS", layout="wide", initial_sidebar_state="collapsed")

# Import necessary modules
import asyncio, sys

# AsyncIO fix for Streamlit on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Path patch so `import …` works
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.extend(
    [
        os.path.join(BASE, "1.2_back_end"),
        os.path.join(BASE, "1.3_models"),
        os.path.join(BASE, "1.4_agent2_quiz"),
    ]
)

from document_loader import load_and_embed_pdf
from quiz_extractor import extract_questions_from_pdf

# Ensure all required data directories exist
required_dirs = [
    "data/finalised_quizzes",
    "data/uploaded_pdfs",
    "data/student_profiles",
    "data/student_performance",
    "data/global_kb",
    "data/quiz_sessions"
]
for d in required_dirs:
    os.makedirs(d, exist_ok=True)

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["FIREBASE"]))
    firebase_admin.initialize_app(cred)
db = firestore.client()

def save_quiz_to_firestore(subject, week, questions):
    doc_id = f"{subject}_{week}"
    db.collection("finalised_quizzes").document(doc_id).set({
        "subject": subject,
        "week": week,
        "questions": questions
    })

def load_quiz_from_firestore(subject, week):
    doc_id = f"{subject}_{week}"
    doc = db.collection("finalised_quizzes").document(doc_id).get()
    if doc.exists:
        return doc.to_dict().get("questions", [])
    else:
        return []

# ── Streamlit layout ──────────────────────────────────────────────────
# Main entry page: login/role selection
if 'page' not in st.session_state:
    st.session_state.page = 'main'

# Query param management for robust session persistence
params = st.query_params
if 'page' in params and params['page']:
    st.session_state.page = params['page']
if 'subject' in params and params['subject']:
    st.session_state['student_subject'] = params['subject']
if 'week' in params and params['week']:
    st.session_state['student_week'] = params['week']
if 'student_id' in params and params['student_id']:
    st.session_state['student_id'] = params['student_id']

def set_query_params():
    st.query_params.clear()
    st.query_params.update({
        'page': st.session_state.page,
        'subject': st.session_state.get('student_subject', ''),
        'week': st.session_state.get('student_week', ''),
        'student_id': st.session_state.get('student_id', '')
    })

if st.session_state.page == 'main':
    st.markdown("""
        <style>
        .centered-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            margin-top: 8vh;
        }
        .centered-container .stButton>button {
            all: unset;
            display: block;
            width: 320px;
            max-width: 90vw;
            padding: 0;
            background: linear-gradient(90deg, #67D6FF 0%, #A78BFA 100%);
            border: none;
            border-radius: 20px;
            color: #fff;
            font-size: 1.25rem;
            font-weight: 700;
            margin: 1.1rem 0;
            box-shadow: 0px 0px 10px rgba(167, 139, 250, 0.18);
            cursor: pointer;
            text-align: center;
            transition: background 0.2s, color 0.2s, opacity 0.2s;
        }
        .centered-container .stButton>button:hover {
            opacity: 0.92;
            background: linear-gradient(90deg, #A78BFA 0%, #67D6FF 100%);
        }
        </style>
    """, unsafe_allow_html=True)
    st.markdown('<div class="centered-container">', unsafe_allow_html=True)
    st.markdown("## GenAI ITS Login")
    btn_teacher = st.button("👩‍🏫 Teacher/Tutor", key="teacher_btn", help="Click to login as Teacher")
    btn_student = st.button("🧑‍🎓 Student", key="student_btn", help="Click to login as Student")
    st.markdown('</div>', unsafe_allow_html=True)
    if btn_teacher:
        st.session_state.page = 'teacher'
        set_query_params()
        st.rerun()
    if btn_student:
        st.session_state.page = 'student_login'
        set_query_params()
        st.rerun()
    st.stop()

if st.session_state.page == 'teacher':
    st.sidebar.header("Teacher Options")
    if st.button("⬅️ Back to Main Page"):
        st.session_state.page = 'main'
        set_query_params()
        st.rerun()
    st.title("📘 GenAI Intelligent Tutoring System - Teacher Dashboard")

    mode = st.radio("Choose an action:", ["Select Existing Quiz", "Upload New Quiz"], horizontal=True)

    base = "data/finalised_quizzes"
    if mode == "Select Existing Quiz":
        # Only show subjects with at least one week containing quiz.json
        subjects = []
        for doc in db.collection("finalised_quizzes").stream():
            data = doc.to_dict()
            if data and "subject" in data:
                subjects.append(data["subject"])
        subjects = sorted(set(subjects))
        subject = st.selectbox("Select Subject", subjects, key="teacher_subject")
        weeks = []
        if subject:
            for doc in db.collection("finalised_quizzes").stream():
                data = doc.to_dict()
                if data and data.get("subject") == subject:
                    weeks.append(data.get("week"))
        weeks = sorted(set(weeks))
        week = st.selectbox("Select Week", weeks if weeks else [], key="teacher_week")
        quiz_data = load_quiz_from_firestore(subject, week) if subject and week else []
        if subject and week and quiz_data:
            st.success(f"Selected quiz: {subject} / {week}")
            questions = quiz_data
            edited_questions = []
            for q in questions:
                with st.expander(f"Question {q.get('id', '')}: {q.get('question', '')}"):
                    new_question = st.text_area("Question", value=q.get('question', ''), key=f"edit_q_{q.get('id','')}_question")
                    new_context = st.text_area("Context", value=q.get('context', ''), key=f"edit_q_{q.get('id','')}_context", height=150)
                    new_rubric = st.text_area("Rubric", value=q.get('answer', ''), key=f"edit_q_{q.get('id','')}_rubric", height=200)
                    edited_questions.append({
                        "id": q.get('id',''),
                        "question": new_question,
                        "context": new_context,
                        "answer": new_rubric
                    })
            if st.button("Save All Changes"):
                save_quiz_to_firestore(subject, week, edited_questions)
                st.success(f"Saved edited quiz to Firestore for {subject} / {week}")
    else:
        # Upload new quiz flow
        st.info("Upload a new quiz PDF to create a new quiz.")
        subject = st.text_input("Enter Subject Name (e.g. COMP801)", key="new_subject")
        week = st.text_input("Enter Week (e.g. Week 1)", key="new_week")
        uploaded_pdf = st.file_uploader("Upload Quiz PDF", type=["pdf"], key="new_quiz_pdf")
        if subject and week and uploaded_pdf:
            # Save uploaded PDF to a temp location
            temp_pdf_path = os.path.join("data", "uploaded_pdfs", uploaded_pdf.name)
            os.makedirs(os.path.dirname(temp_pdf_path), exist_ok=True)
            with open(temp_pdf_path, "wb") as f:
                f.write(uploaded_pdf.read())
            import quiz_extractor
            # Only run extraction if not already done for this PDF
            if 'uploaded_pdf_name' not in st.session_state or st.session_state.uploaded_pdf_name != uploaded_pdf.name:
                with st.spinner("Extracting questions from PDF (Pass 1)..."):
                    try:
                        questions = quiz_extractor.extract_questions_from_pdf(temp_pdf_path)
                        st.session_state.uploaded_questions = questions
                        st.session_state.uploaded_pdf_name = uploaded_pdf.name
                    except Exception as e:
                        st.error(f"Error processing PDF: {e}")
                        st.session_state.uploaded_questions = []
            # If already extracted, use session state
            questions = st.session_state.get('uploaded_questions', [])
            if questions:
                st.success(f"Extracted {len(questions)} questions. You can edit them below before saving.")
                # Buttons to re-run Pass 2 and Pass 3
                if st.button("Re-run Pass 2: Enrich Context"):
                    with st.spinner("Re-enriching context for all questions (Pass 2)..."):
                        enriched_questions = []
                        llm = quiz_extractor.get_llm()
                        pdf_text = quiz_extractor._pdf_to_text(temp_pdf_path)
                        for idx, q in enumerate(st.session_state.uploaded_questions, start=1):
                            q.setdefault("id", idx)
                            try:
                                enrich_prompt = quiz_extractor.ENRICH_PROMPT.format(
                                    pdf_text=pdf_text,
                                    question=q["question"],
                                    context=q["context"],
                                )
                                enriched_context = llm.invoke(
                                    [
                                        {"role": "system", "content": "Return ONLY the enriched context as plain text. Do not add any preamble or conclusion."},
                                        {"role": "user", "content": enrich_prompt},
                                    ],
                                    temperature=0.2
                                ).content
                                cleaned_context = quiz_extractor.clean_enriched_context(enriched_context)
                                if len(cleaned_context) < 40 or cleaned_context.lower().startswith("the question is asking"):
                                    q_text = q["question"][:40]
                                    pdf_lines = pdf_text.splitlines()
                                    relevant_lines = [line for line in pdf_lines if q_text.split()[0] in line or any(x in line for x in ["=", "print", ":", "+", "input", "output"])]
                                    if relevant_lines:
                                        cleaned_context += "\n" + "\n".join(relevant_lines[:6])
                                q["context"] = cleaned_context.strip()
                            except Exception as e:
                                st.warning(f"⚠️ Error enriching context for Q{idx}: {e}")
                            enriched_questions.append(q)
                        st.session_state.uploaded_questions = enriched_questions
                        st.success("Pass 2 complete: Context enriched.")
                if st.button("Re-run Pass 3: Generate Rubrics"):
                    with st.spinner("Generating rubrics for all questions (Pass 3)..."):
                        rubric_questions = []
                        llm = quiz_extractor.get_llm()
                        for q in st.session_state.uploaded_questions:
                            try:
                                rubric_prompt = quiz_extractor.RUBRIC_PROMPT.format(
                                    question=q["question"],
                                    context=q["context"],
                                )
                                rubric_response = llm.invoke(
                                    [
                                        {"role": "system", "content": "Return the marking rubric as plain text."},
                                        {"role": "user", "content": rubric_prompt},
                                    ]
                                ).content
                                q["answer"] = rubric_response.strip()
                            except Exception as e:
                                st.warning(f"⚠️ Error generating rubric for Q{q['id']}: {e}")
                                q["answer"] = "Rubric generation failed."
                            rubric_questions.append(q)
                        st.session_state.uploaded_questions = rubric_questions
                        st.success("Pass 3 complete: Rubrics generated.")
                # Always show the questions for editing
                edited_questions = []
                for q in st.session_state.uploaded_questions:
                    with st.expander(f"Question {q.get('id', '')}: {q.get('question', '')}"):
                        new_question = st.text_area("Question", value=q.get('question', ''), key=f"new_q_{q.get('id','')}_question")
                        new_context = st.text_area("Context", value=q.get('context', ''), key=f"new_q_{q.get('id','')}_context", height=150)
                        new_rubric = st.text_area("Rubric", value=q.get('answer', ''), key=f"new_q_{q.get('id','')}_rubric", height=200)
                        edited_questions.append({
                            "id": q.get('id',''),
                            "question": new_question,
                            "context": new_context,
                            "answer": new_rubric
                        })
                # If no expanders are opened, still save the current questions
                if not edited_questions:
                    edited_questions = st.session_state.uploaded_questions
                if st.button("Save Quiz"):
                    save_quiz_to_firestore(subject, week, edited_questions)
                    st.success(f"Quiz saved to Firestore for {subject} / {week}. It is now available to students.")
            else:
                st.warning("No questions extracted. Please check the PDF.")

            set_query_params()  # Update query params after any changes

elif st.session_state.page == 'student_login':
    st.sidebar.empty()
    st.title("Student Login")
    student_id = st.text_input("Enter your student ID or name")
    if student_id:
        # Reset all user-specific session state on new login
        for key in list(st.session_state.keys()):
            if key not in ["page"]:
                del st.session_state[key]
        st.session_state.student_id = student_id
        st.session_state.page = 'student_pre_survey'
        set_query_params()
        st.rerun()
    st.stop()

elif st.session_state.page == 'student_pre_survey':
    st.sidebar.empty()
    st.title("Pre-Quiz Survey")
    st.markdown("Please complete the pre-quiz survey below before starting your quiz.")
    # Only require survey once per student per subject (not per week), store in Firestore
    survey_done = False
    if 'student_id' in st.session_state and 'student_subject' in st.session_state:
        survey_doc_id = f"{st.session_state['student_id']}_{st.session_state['student_subject']}_pre_survey"
        survey_ref = db.collection("student_surveys").document(survey_doc_id)
        survey_doc = survey_ref.get()
        if survey_doc.exists and survey_doc.to_dict().get("done"):
            survey_done = True
    if survey_done:
        st.session_state.page = 'student_quiz'
        set_query_params()
        st.rerun()
    if PRE_QUIZ_SURVEY_URL:
        st.markdown(f"""
        <iframe src=\"{PRE_QUIZ_SURVEY_URL}\" width=\"100%\" height=\"600\" frameborder=\"0\"></iframe>
        """, unsafe_allow_html=True)
    else:
        st.warning("Pre-quiz survey link is not configured.")
    confirm = st.checkbox("I confirm I have completed the survey", key="pre_survey_confirm")
    if st.button("I have completed the survey", disabled=not confirm):
        if 'student_id' in st.session_state and 'student_subject' in st.session_state:
            survey_doc_id = f"{st.session_state['student_id']}_{st.session_state['student_subject']}_pre_survey"
            survey_ref = db.collection("student_surveys").document(survey_doc_id)
            survey_ref.set({"student_id": st.session_state['student_id'], "subject": st.session_state['student_subject'], "done": True})
        st.session_state.page = 'student_quiz'
        set_query_params()
        st.rerun()
    st.stop()

elif st.session_state.page == 'student_quiz':
    st.sidebar.empty()
    if st.button("\u2B05\uFE0F Back to Main Page"):
        st.session_state.page = 'main'
        set_query_params()
        st.rerun()
    st.markdown(f"**Logged in as:** `{st.session_state.student_id}`")
    # Quiz selection (Firestore only)
    # Get all subjects from Firestore
    subjects = []
    for doc in db.collection("finalised_quizzes").stream():
        data = doc.to_dict()
        if data and "subject" in data:
            subjects.append(data["subject"])
    subjects = sorted(set(subjects))
    weeks = []
    if 'student_subject' in st.session_state:
        subject = st.session_state['student_subject']
    else:
        subject = subjects[0] if subjects else ''
    if subject:
        for doc in db.collection("finalised_quizzes").stream():
            data = doc.to_dict()
            if data and data.get("subject") == subject:
                weeks.append(data.get("week"))
    weeks = sorted(set(weeks))
    def on_subject_or_week_change():
        set_query_params()
    subject = st.selectbox("Select Subject", subjects, key="student_subject", on_change=on_subject_or_week_change)
    week = st.selectbox("Select Week", weeks if weeks else [], key="student_week", on_change=on_subject_or_week_change)
    quiz_data = load_quiz_from_firestore(subject, week) if subject and week else []
    if subject and week and quiz_data:
        # Per-student, per-subject, per-week chat history (local, for now)
        student_profile_dir = os.path.join("data", "student_profiles", st.session_state.student_id)
        os.makedirs(student_profile_dir, exist_ok=True)
        chat_history_path = os.path.join(student_profile_dir, f"{subject}_{week}_quiz.json")
        if os.path.exists(chat_history_path):
            with open(chat_history_path, "r", encoding="utf-8") as cf:
                chat_history = json.load(cf)
        else:
            chat_history = []
        if st.button("Clear chat"):
            chat_history = []
            st.session_state.last_displayed_index = 0
            with open(chat_history_path, "w", encoding="utf-8") as cf:
                json.dump(chat_history, cf)
            # Also reset quiz progress in Firestore
            perf_doc_id = f"{st.session_state.student_id}_{subject}_{week}"
            perf_ref = db.collection("student_performance").document(perf_doc_id)
            perf = perf_ref.get().to_dict() if perf_ref.get().exists else None
            if perf:
                perf["current_q"] = 0
                perf["last_score"] = 0.0
                perf_ref.set(perf)
            st.rerun()
        st.markdown("---")
        # Only initialize with instructions/first question if chat_history is empty
        if not chat_history:
            from quiz_agent import QuizAgent
            agent = QuizAgent(quiz_data, subject, week, st.session_state.student_id, {})
            rules = agent.get_instructions()
            first_q = agent.present_question(quiz_data[0])
            chat_history.append({"role": "assistant", "content": rules + "\n\n" + first_q})
            with open(chat_history_path, "w", encoding="utf-8") as cf:
                json.dump(chat_history, cf)
            st.session_state.last_displayed_index = 0
        # Always display all previous chat history statically (no streaming)
        if 'last_displayed_index' not in st.session_state or st.session_state.last_displayed_index > len(chat_history):
            st.session_state.last_displayed_index = len(chat_history)
        chat_container = st.container()
        with chat_container:
            for i, msg in enumerate(chat_history):
                if msg['role'] == 'user':
                    st.chat_message("user").markdown(f"**User:** {msg['content']}")
                else:
                    st.chat_message("assistant").markdown(f"**Assistant:** {msg['content']}")
            st.write("<script>window.scrollTo(0, document.body.scrollHeight);</script>", unsafe_allow_html=True)
        # Only show chat input at the bottom
        user_input = st.chat_input("Type your answer and press Enter...")
        if user_input:
            chat_history.append({"role": "user", "content": user_input})
            from quiz_agent import QuizAgent
            agent = QuizAgent(quiz_data, subject, week, st.session_state.student_id, {})
            response, end_quiz = agent.handle_input(user_input, chat_history)
            # If the response signals Qualtrics 2, show the survey and stop
            if end_quiz == "qualtrics2":
                chat_history.append({"role": "assistant", "content": response})
                with open(chat_history_path, "w", encoding="utf-8") as cf:
                    json.dump(chat_history, cf)
                st.session_state.last_displayed_index = len(chat_history)
                st.success("Please complete the post-quiz survey below:")
                post_survey_done = False
                if 'student_id' in st.session_state and 'student_subject' in st.session_state:
                    post_survey_doc_id = f"{st.session_state['student_id']}_{st.session_state['student_subject']}_post_survey"
                    post_survey_ref = db.collection("student_surveys").document(post_survey_doc_id)
                    post_survey_doc = post_survey_ref.get()
                    if post_survey_doc.exists and post_survey_doc.to_dict().get("done"):
                        post_survey_done = True
                if post_survey_done:
                    st.success("You have already completed the post-quiz survey. Returning to main page...")
                    st.session_state.page = 'main'
                    set_query_params()
                    st.rerun()
                elif POST_QUIZ_SURVEY_URL:
                    st.markdown(f"""
                    <iframe src=\"{POST_QUIZ_SURVEY_URL}\" width=\"100%\" height=\"600\" frameborder=\"0\"></iframe>
                    """, unsafe_allow_html=True)
                    post_confirm = st.checkbox("I confirm I have completed the post-quiz survey", key="post_survey_confirm")
                    if st.button("I have completed the post-quiz survey", disabled=not post_confirm):
                        if 'student_id' in st.session_state and 'student_subject' in st.session_state:
                            post_survey_doc_id = f"{st.session_state['student_id']}_{st.session_state['student_subject']}_post_survey"
                            post_survey_ref = db.collection("student_surveys").document(post_survey_doc_id)
                            post_survey_ref.set({"student_id": st.session_state['student_id'], "subject": st.session_state['student_subject'], "done": True})
                        st.session_state.page = 'main'
                        set_query_params()
                        st.rerun()
                else:
                    st.warning("Post-quiz survey link is not configured.")
                st.stop()
            # If the response contains both feedback and a new question, split and append both
            if ("**Question" in response) and ("Context & Instructions" in response):
                # Try to split at the start of the next question
                parts = response.split("**Question", 1)
                feedback = parts[0].strip()
                question = "**Question" + parts[1].strip()
                if feedback:
                    chat_history.append({"role": "assistant", "content": feedback})
                if question:
                    chat_history.append({"role": "assistant", "content": question})
            else:
                chat_history.append({"role": "assistant", "content": response})
            with open(chat_history_path, "w", encoding="utf-8") as cf:
                json.dump(chat_history, cf)
            st.session_state.last_displayed_index = len(chat_history)
            st.rerun()

    # If user types 'quit', return to main page or skip post-quiz survey if already done
    if user_input and user_input.strip().lower() == 'quit':
        post_survey_done = False
        if 'student_id' in st.session_state and 'student_subject' in st.session_state:
            post_survey_doc_id = f"{st.session_state['student_id']}_{st.session_state['student_subject']}_post_survey"
            post_survey_ref = db.collection("student_surveys").document(post_survey_doc_id)
            post_survey_doc = post_survey_ref.get()
            if post_survey_doc.exists and post_survey_doc.to_dict().get("done"):
                post_survey_done = True
        st.session_state.page = 'main'
        set_query_params()
        st.rerun()

    set_query_params()  # Update query params after any changes
