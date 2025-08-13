import os
import json
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase only once
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["FIREBASE"]))
    firebase_admin.initialize_app(cred)
db = firestore.client()

def get_groq_llm(model_name=None, temperature=None):
    # Loads model and temperature from .env, with agent-specific overrides
    from llm_provider import get_llm
    model = model_name or os.getenv("QUIZ_AGENT_MODEL", os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"))
    temp = float(temperature if temperature is not None else os.getenv("QUIZ_AGENT_TEMPERATURE", os.getenv("GROQ_TEMPERATURE", "0.0")))
    return get_llm(model_name=model, temperature=temp)

class QuizAgent:
    def __init__(self, quiz_data, subject, week, student_id, profile):
        self.quiz_data = quiz_data
        self.subject = subject
        self.week = week
        self.student_id = student_id
        self.profile = profile
        self.firestore_doc = f"student_performance/{student_id}_{subject}_{week}"
        self.load_performance()
        self.current_q = self.performance.get("current_q", 0)
        self.started = self.performance.get("started", False)
        self.instructions_given = self.performance.get("instructions_given", False)
        self.llm = get_groq_llm()

    def load_performance(self):
        doc_ref = db.document(self.firestore_doc)
        doc = doc_ref.get()
        if doc.exists:
            self.performance = doc.to_dict()
        else:
            self.performance = {
                "answers": {},  # {q_id: [{"attempt": n, "answer": str, "feedback": str, "score": float}]}
                "current_q": 0,
                "started": False,
                "instructions_given": False
            }

    def save_performance(self):
        db.document(self.firestore_doc).set(self.performance)

    def get_instructions(self):
        # Clear, accurate rules for students based on actual functionality
        return (
            "👋 **Welcome to your quiz!**\n\n"
            "You are about to take an interactive, AI-powered quiz. Here are the rules and how it works:\n\n"
            "- I will present each question with all the code, context, and instructions you need.\n"
            "- You can answer in your own words, or with code if required.\n"
            "- I will give you instant, supportive feedback and let you know if you should try again or move on.\n"
            "- Your answers will be checked against a detailed marking rubric.\n"
            "- To move to the next question, type **'next'** or **'continue'** (only after a sufficient answer).\n"
            "- To finish the quiz at any time, type **'quit'**, **'exit'**, **'stop'**, or **'finish'**.\n\n"
            "Let's get started! Here comes your first question:"
        )

    def present_question(self, q):
        # Use the shared formatting utility for consistent display, but first clean up question grammar/fluency
        import sys, os
        sys.path.append(os.path.join(os.path.dirname(__file__), '../1.1_interface/utils'))
        from format_quiz_context import format_quiz_context
        def clean_question_text(text):
            import re
            # Remove repeated words, fix common grammar, and add punctuation if missing
            text = text.strip()
            # Capitalize first letter
            if text and not text[0].isupper():
                text = text[0].upper() + text[1:]
            # Add period if missing
            if text and text[-1] not in '.?!':
                text += '.'
            # Remove double spaces
            text = re.sub(r'\s+', ' ', text)
            # Fix common awkward phrases
            text = re.sub(r'include (\d+ elements?:)', r'including \1', text, flags=re.I)
            text = re.sub(r'and the print out', 'and then print out', text, flags=re.I)
            text = re.sub(r'has keys in integer', 'has integer keys', text, flags=re.I)
            text = re.sub(r'Using the len\(\) function to get', 'Use the len() function to get', text, flags=re.I)
            text = re.sub(r'\band the\b', 'and', text, flags=re.I)
            # Remove repeated words (e.g., 'the the')
            text = re.sub(r'\b(\w+) \1\b', r'\1', text, flags=re.I)
            # Remove trailing commas before period
            text = re.sub(r',\s*\.', '.', text)
            return text
        # Clean up the question text before formatting
        q = dict(q)  # Copy to avoid mutating original
        if 'question' in q:
            q['question'] = clean_question_text(q['question'])
        return format_quiz_context(q)

    def evaluate_answer(self, answer, question):
        rubric = question.get("answer", "")
        prompt = (
            f"You are a professional, supportive university tutor for a student taking a quiz in a cybersecurity subject.\n"
            f"Here is the quiz question and context:\n"
            f"Question: {question['question']}\n"
            f"Context: {question['context']}\n"
            f"Marking Rubric: {rubric}\n"
            f"Student's Input: {answer}\n\n"
            "INSTRUCTIONS (STRICT):\n"
            "- Carefully assess the student's input using ONLY the rubric criteria.\n"
            "- If the answer is incomplete, off-topic, irrelevant, or does not address the rubric criteria, you MUST mark it as incorrect (SCORE: 0.0) and explain why.\n"
            "- If the answer is correct or mostly correct, start your reply with 'Correct:' or 'Great job! Your answer is correct because...' and justify the score by referencing specific rubric criteria that are satisfied.\n"
            "- If the answer is incorrect, start your reply with 'Incorrect:' or 'Your answer is not correct because...' and clearly state which rubric criteria are missing or unsatisfied.\n"
            "- Do NOT explain your own steps or what you are doing. Do NOT mention the rubric, criteria, or that you are assessing.\n"
            "- Be concise, professional, and humanlike.\n"
            "- If the input is a question or exploration (e.g., starts with 'how', 'why', 'what', or ends with a '?'), respond in a helpful, detailed way, but do not mention your own process.\n"
            "- Always relate your explanation or example to cybersecurity concepts, best practices, or real-world scenarios where possible.\n"
            "- If the answer is correct, you may offer a brief extension or related insight (preferably with a cybersecurity angle), but do not state 'next question' or similar.\n"
            "- If the answer is not correct, kindly point out what could be improved, offer a helpful hint or example, and encourage them to try again.\n"
            "- If the student is exploring a related topic, answer their question fully, then gently prompt them to return to the quiz when ready.\n"
            "- Do not mention scores, rubrics, or evaluation steps in your feedback.\n"
            "- Ensure that feedback is explicit and unambiguous about correctness.\n"
            "At the end, in a new line, write: SCORE: 1.0 if the answer is correct or mostly correct, or SCORE: 0.0 if not. If the input is a question or exploration, write SCORE: X (where X is the last valid score for this question, or 0.0 if not available).\n"
        )
        # Use rubric model/temperature from .env if specified
        rubric_model = os.getenv("QUIZ_AGENT_RUBRIC_MODEL", "meta-llama/llama-4-maverick-17b-128e-instruct")
        rubric_temp = float(os.getenv("QUIZ_AGENT_RUBRIC_TEMPERATURE", "0.3"))
        eval_llm = get_groq_llm(model_name=rubric_model, temperature=rubric_temp)
        response = eval_llm.invoke([{"role": "system", "content": prompt}]).content.strip()
        # Parse the score from the last line
        lines = response.splitlines()
        score = 0.0
        for line in reversed(lines):
            if line.strip().startswith("SCORE:"):
                try:
                    score_str = line.split(":", 1)[1].strip()
                    if score_str == 'X':
                        score = float(self.performance.get("last_score", 0.0))
                    else:
                        score = float(score_str)
                except Exception:
                    score = 0.0
                break
        feedback = "\n".join([l for l in lines if not l.strip().startswith("SCORE:")]).strip()
        relevant = True
        return relevant, score, feedback

    def handle_input(self, user_input, chat_history):
        user_clean = user_input.strip().lower()
        # End quiz if user wants to quit/exit/stop/finish at any time
        if user_clean in ["quit", "exit", "stop", "finish"]:
            self.performance["started"] = False
            self.save_performance()
            return "Thank you for participating! Please complete the post-quiz survey below.", "qualtrics2"

        # Give instructions and first question if not started
        if not self.performance["started"]:
            self.performance["started"] = True
            self.performance["instructions_given"] = True
            self.save_performance()
            q = self.quiz_data[self.current_q]
            # Only return the first question, not instructions again
            return self.present_question(q), False

        # If all questions are done
        if self.current_q >= len(self.quiz_data):
            self.save_performance()
            return "🎉 You've completed all questions! Type 'quit' to finish or review your answers.", False

        q = self.quiz_data[self.current_q]
        q_id = str(q["id"])
        continue_phrases = ["next", "continue", "yes", "ready", "okay", "yep"]
        if user_clean in continue_phrases:
            # Only allow continue if last answer was above a minimum threshold
            last_score = self.performance.get("last_score", 0.0)
            try:
                last_score = float(last_score)
            except Exception:
                last_score = 0.0
            if last_score >= 0.5:
                # Only allow moving to next question if not on last
                if self.current_q >= len(self.quiz_data) - 1:
                    self.current_q = len(self.quiz_data)
                    self.performance["current_q"] = self.current_q
                    self.save_performance()
                    return "🎉 You've completed all questions! Please complete the post-quiz survey below.", "qualtrics2"
                self.current_q += 1
                self.performance["current_q"] = self.current_q
                self.save_performance()
                if self.current_q < len(self.quiz_data):
                    return self.present_question(self.quiz_data[self.current_q]), False
                else:
                    return "🎉 You've completed all questions! Please complete the post-quiz survey below.", "qualtrics2"
            else:
                # Do NOT advance, must retry
                return "You need to attempt the question and receive a score of at least 0.5 before moving on.", False
        # Check if the input is an answer (simple heuristic: not a question, not empty)
        is_question = user_input.strip().endswith("?") or user_input.strip().lower().startswith(("how", "why", "what", "can", "does", "do", "is", "are", "could", "would", "should"))
        if user_input.strip() and not is_question:
            relevant, score, feedback = self.evaluate_answer(user_input, q)
            # Store the attempt
            attempts = self.performance["answers"].setdefault(q_id, [])
            attempts.append({
                "attempt": len(attempts) + 1,
                "answer": user_input,
                "feedback": feedback,
                "score": score
            })
            # Store last valid score and qid for continue logic
            self.performance["last_score"] = score
            self.performance["last_qid"] = str(self.current_q + 1)
            self.save_performance()
            # Ensure score is float for comparison
            try:
                score_float = float(score)
            except Exception:
                score_float = 0.0
            # Only auto-advance if score is 1.0 and feedback explicitly confirms correctness
            feedback_lower = feedback.lower()
            is_clearly_correct = (
                score_float == 1.0 and (
                    "correct:" in feedback_lower or 
                    "great job!" in feedback_lower or 
                    "your answer is correct because" in feedback_lower
                ) and "incorrect:" not in feedback_lower
            )
            # Ensure question is passed correctly
            q = self.quiz_data[self.current_q]  # Fetch the current question
            rubric = q.get("answer", "")  # Ensure rubric is fetched from the question
            rubric_criteria = rubric.split(";")  # Assuming rubric is semicolon-separated
            satisfied_criteria = sum(1 for criterion in rubric_criteria if criterion.lower() in feedback.lower())
            total_criteria = len(rubric_criteria)
            correctness_percentage = (satisfied_criteria / total_criteria) * 100 if total_criteria > 0 else 0

            # Only auto-advance if correctness is at least 80% and user explicitly types 'next' or 'continue'
            feedback_lower = feedback.lower()
            is_sufficiently_correct = correctness_percentage >= 80
            if is_sufficiently_correct and user_clean in ["next", "continue"] and self.current_q < len(self.quiz_data) - 1:
                encouragement = "🌟 Great job! " if correctness_percentage > 95 else "👍 Well done! "
                response = f"{encouragement}{feedback}\n\nHere is your next question:"
                self.current_q += 1
                self.performance["current_q"] = self.current_q
                self.save_performance()
                response += "\n\n" + self.present_question(self.quiz_data[self.current_q])
                return response, False
            elif is_sufficiently_correct and user_clean in ["next", "continue"] and self.current_q == len(self.quiz_data) - 1:
                encouragement = "🌟 Great job! " if correctness_percentage > 95 else "👍 Well done! "
                response = f"{encouragement}{feedback}\n\n🎉 You've completed all questions! Please complete the post-quiz survey below."
                self.current_q += 1
                self.performance["current_q"] = self.current_q
                self.save_performance()
                return response, "qualtrics2"
            else:
                # Encourage and guide for another attempt
                return (
                    f"Keep going! {feedback}\n\nTry again, or type 'next' to move on or 'quit' to exit."
                , False)
        # If the input is a question or exploration, answer but do NOT advance
        if is_question:
            relevant, score, feedback = self.evaluate_answer(user_input, q)
            # Store the attempt as an exploration
            attempts = self.performance["answers"].setdefault(q_id, [])
            attempts.append({
                "attempt": len(attempts) + 1,
                "answer": user_input,
                "feedback": feedback,
                "score": score,
                "exploration": True
            })
            self.save_performance()
            return (
                f"{feedback}\n\nWhen you're ready, you can try answering the quiz question or type 'next' to move on."
            , False)
        # If user types quit/exit/stop/finish at any time
        if user_clean in ["quit", "exit", "stop", "finish"]:
            self.performance["started"] = False
            self.save_performance()
            return "Thank you for participating! Please complete the post-quiz survey below.", "qualtrics2"
        else:
            # If not an answer, respond as a tutor
            return (
                "If you have a question about the quiz, let me know! Otherwise, please type your answer to the current question."
            , False)