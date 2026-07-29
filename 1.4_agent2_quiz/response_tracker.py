# 1.4_agent2_quiz/response_tracker.py
# ─────────────────────────────────────────────────────────────────────────
"""
Interaction analytics logger for research data collection.

Captures timestamped, granular events throughout a student's quiz session
so that downstream analysis (e.g., learning gain, engagement patterns,
time-on-task, feedback utilisation) can be computed without manual
reconstruction.

Every event is persisted to Firestore immediately so nothing is lost if
the browser tab closes.

Firestore collection: ``interaction_events``
Document ID:          ``{student_id}_{subject}_{week}_{event_type}_{seq}``

A companion ``session_summaries`` collection stores per-session roll-ups
(total time, attempts per question, score trajectory, etc.).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import firebase_admin
from firebase_admin import firestore


# ── helpers ────────────────────────────────────────────────────────────

def _db():
    """Return the Firestore client (assumes firebase_admin is already
    initialised by streamlit_app.py)."""
    return firestore.client()


def _utc_now() -> str:
    """ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


# ── event types ────────────────────────────────────────────────────────

EVENT_TYPES = {
    "session_start",
    "session_end",
    "question_presented",
    "answer_submitted",
    "feedback_received",
    "feedback_viewed",        # student scrolled / stayed on feedback
    "exploration_query",      # student asked a clarifying question
    "question_advanced",      # moved to next question
    "quiz_completed",
    "survey_started",
    "survey_completed",
    "hint_requested",
    "kb_chunk_retrieved",     # RAG retrieval event
}


# ── core API ───────────────────────────────────────────────────────────

EVENTS_COLLECTION = "interaction_events"
SUMMARIES_COLLECTION = "session_summaries"


def log_event(
    student_id: str,
    subject: str,
    week: str,
    event_type: str,
    *,
    session_id: str = "",
    question_id: str = "",
    data: Optional[Dict[str, Any]] = None,
) -> str:
    """Persist a single interaction event to Firestore.

    Parameters
    ----------
    student_id : str
        The student's identifier.
    subject : str
        Course code, e.g. ``"COMP801"``.
    week : str
        Quiz week, e.g. ``"Week 1"``.
    event_type : str
        One of the recognised ``EVENT_TYPES``.
    session_id : str, optional
        Unique session identifier (use ``start_session`` to generate one).
    question_id : str, optional
        Which question the event relates to.
    data : dict, optional
        Arbitrary payload — answer text, score, feedback, duration, etc.

    Returns
    -------
    str  – Firestore document ID.
    """
    seq = uuid.uuid4().hex[:8]
    doc_id = f"{student_id}_{subject}_{week}_{event_type}_{seq}"

    record = {
        "student_id": student_id,
        "subject": subject,
        "week": week,
        "session_id": session_id,
        "event_type": event_type,
        "question_id": question_id,
        "timestamp": _utc_now(),
        "data": data or {},
    }
    _db().collection(EVENTS_COLLECTION).document(doc_id).set(record)
    return doc_id


def start_session(student_id: str, subject: str, week: str) -> str:
    """Start a new quiz session and return a unique session_id.

    Logs a ``session_start`` event automatically.
    """
    session_id = f"{student_id}_{subject}_{week}_{uuid.uuid4().hex[:8]}"
    log_event(
        student_id, subject, week,
        "session_start",
        session_id=session_id,
        data={"started_at": _utc_now()},
    )
    return session_id


def end_session(
    student_id: str,
    subject: str,
    week: str,
    session_id: str,
    *,
    summary: Optional[Dict[str, Any]] = None,
) -> str:
    """End a quiz session and persist a summary roll-up.

    Parameters
    ----------
    summary : dict, optional
        Aggregated metrics for the session:
        ``total_questions``, ``questions_attempted``, ``total_attempts``,
        ``final_scores`` (dict of q_id → score), ``duration_seconds``, etc.

    Returns
    -------
    str  – Summary document ID.
    """
    log_event(
        student_id, subject, week,
        "session_end",
        session_id=session_id,
        data={"ended_at": _utc_now()},
    )

    summary_doc_id = f"{session_id}_summary"
    record = {
        "student_id": student_id,
        "subject": subject,
        "week": week,
        "session_id": session_id,
        "ended_at": _utc_now(),
        **(summary or {}),
    }
    _db().collection(SUMMARIES_COLLECTION).document(summary_doc_id).set(record)
    return summary_doc_id


# ── convenience loggers ────────────────────────────────────────────────

def log_answer(
    student_id: str,
    subject: str,
    week: str,
    session_id: str,
    question_id: str,
    attempt_number: int,
    answer_text: str,
    score: float,
    feedback: str,
    *,
    is_exploration: bool = False,
    evaluation_latency_ms: Optional[int] = None,
) -> str:
    """Log a student answer submission together with the AI feedback.

    This is the most common event and captures everything needed for
    per-question learning-gain analysis.
    """
    event_type = "exploration_query" if is_exploration else "answer_submitted"
    return log_event(
        student_id, subject, week,
        event_type,
        session_id=session_id,
        question_id=question_id,
        data={
            "attempt_number": attempt_number,
            "answer_text": answer_text,
            "score": score,
            "feedback": feedback,
            "is_exploration": is_exploration,
            "evaluation_latency_ms": evaluation_latency_ms,
        },
    )


def log_question_presented(
    student_id: str,
    subject: str,
    week: str,
    session_id: str,
    question_id: str,
) -> str:
    """Log that a question was shown to the student."""
    return log_event(
        student_id, subject, week,
        "question_presented",
        session_id=session_id,
        question_id=question_id,
    )


def log_question_advanced(
    student_id: str,
    subject: str,
    week: str,
    session_id: str,
    from_question: str,
    to_question: str,
    final_score: float,
    total_attempts: int,
) -> str:
    """Log that the student moved from one question to the next."""
    return log_event(
        student_id, subject, week,
        "question_advanced",
        session_id=session_id,
        question_id=from_question,
        data={
            "from_question": from_question,
            "to_question": to_question,
            "final_score": final_score,
            "total_attempts": total_attempts,
        },
    )


# ── query helpers (for dashboards / export) ────────────────────────────

def get_session_events(session_id: str) -> List[Dict]:
    """Return all events for a session, ordered by timestamp."""
    coll = _db().collection(EVENTS_COLLECTION)
    query = coll.where("session_id", "==", session_id).order_by("timestamp")
    return [doc.to_dict() for doc in query.stream()]


def get_student_events(
    student_id: str,
    subject: str = "",
    week: str = "",
    event_type: str = "",
) -> List[Dict]:
    """Return events for a student, optionally filtered."""
    coll = _db().collection(EVENTS_COLLECTION)
    query = coll.where("student_id", "==", student_id)
    if subject:
        query = query.where("subject", "==", subject)
    if week:
        query = query.where("week", "==", week)
    if event_type:
        query = query.where("event_type", "==", event_type)
    return [doc.to_dict() for doc in query.stream()]


def get_session_summary(session_id: str) -> Optional[Dict]:
    """Return the summary for a session (or None)."""
    doc_id = f"{session_id}_summary"
    doc = _db().collection(SUMMARIES_COLLECTION).document(doc_id).get()
    return doc.to_dict() if doc.exists else None


def export_events_csv(subject: str = "", week: str = "") -> str:
    """Export interaction events as CSV for offline analysis.

    Columns: student_id, subject, week, session_id, event_type,
             question_id, timestamp, + flattened data fields.
    """
    import csv
    import io

    coll = _db().collection(EVENTS_COLLECTION)
    query = coll
    if subject:
        query = query.where("subject", "==", subject)
    if week:
        query = query.where("week", "==", week)

    rows = []
    extra_keys: set = set()

    for doc in query.stream():
        d = doc.to_dict()
        data = d.pop("data", {}) or {}
        extra_keys.update(data.keys())
        row = {
            "student_id": d.get("student_id", ""),
            "subject": d.get("subject", ""),
            "week": d.get("week", ""),
            "session_id": d.get("session_id", ""),
            "event_type": d.get("event_type", ""),
            "question_id": d.get("question_id", ""),
            "timestamp": d.get("timestamp", ""),
        }
        row.update(data)
        rows.append(row)

    sorted_extras = sorted(extra_keys)
    fieldnames = [
        "student_id", "subject", "week", "session_id",
        "event_type", "question_id", "timestamp",
    ] + sorted_extras

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return buf.getvalue()
