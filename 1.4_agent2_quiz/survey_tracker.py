# 1.4_agent2_quiz/survey_tracker.py
# ─────────────────────────────────────────────────────────────────────────
"""
Persistent survey participant tracker for pre/post analysis.

Solves the manual-matching problem: every survey response is tagged with
a stable anonymous participant ID, a survey phase (pre / post), and a
UTC timestamp.  All records live in Firestore so nothing is lost when
the session ends.

Firestore collection: ``survey_responses``
Document ID:          ``{participant_id}_{subject}_{phase}``

Also provides CSV export for offline statistical analysis.
"""

from __future__ import annotations

import csv
import hashlib
import io
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import firebase_admin
from firebase_admin import firestore


# ── helpers ────────────────────────────────────────────────────────────
def _db():
    """Return the Firestore client (assumes firebase_admin is already
    initialised by streamlit_app.py)."""
    return firestore.client()


def generate_participant_id(student_id: str, secret_salt: str = "") -> str:
    """Deterministic, anonymised participant ID.

    SHA-256 of (student_id + salt), truncated to 12 hex chars.
    The same student always gets the same ID, enabling pre/post linkage
    without storing PII.
    """
    raw = f"{student_id}{secret_salt}".encode()
    return hashlib.sha256(raw).hexdigest()[:12].upper()


# ── core API ───────────────────────────────────────────────────────────
COLLECTION = "survey_responses"


def record_survey(
    participant_id: str,
    student_id: str,
    subject: str,
    phase: str,  # "pre" | "post"
    responses: Dict[str, Any],
    *,
    week: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Persist a complete survey snapshot to Firestore.

    Parameters
    ----------
    participant_id : str
        Anonymous ID from ``generate_participant_id``.
    student_id : str
        Raw student identifier (kept for admin lookup; not exported).
    subject : str
        Course code, e.g. ``"COMP801"``.
    phase : str
        ``"pre"`` or ``"post"``.
    responses : dict
        ``{item_code: likert_value}`` — the actual survey answers.
    week : str, optional
        Quiz week, if survey is per-week.
    metadata : dict, optional
        Extra info (browser, session duration, etc.).

    Returns
    -------
    str  – Firestore document ID.
    """
    doc_id = f"{participant_id}_{subject}_{phase}"
    if week:
        doc_id = f"{participant_id}_{subject}_{week}_{phase}"

    record = {
        "participant_id": participant_id,
        "student_id": student_id,
        "subject": subject,
        "week": week,
        "phase": phase,
        "responses": responses,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }
    _db().collection(COLLECTION).document(doc_id).set(record)
    return doc_id


def get_survey(participant_id: str, subject: str, phase: str, week: str = "") -> Optional[Dict]:
    """Retrieve a single survey record (or None)."""
    doc_id = f"{participant_id}_{subject}_{phase}"
    if week:
        doc_id = f"{participant_id}_{subject}_{week}_{phase}"
    doc = _db().collection(COLLECTION).document(doc_id).get()
    return doc.to_dict() if doc.exists else None


def has_completed_survey(participant_id: str, subject: str, phase: str, week: str = "") -> bool:
    """Check whether a survey record already exists."""
    return get_survey(participant_id, subject, phase, week) is not None


def get_paired_participants(subject: str, week: str = "") -> List[str]:
    """Return participant IDs that have BOTH pre and post records for a subject."""
    coll = _db().collection(COLLECTION)
    query = coll.where("subject", "==", subject)
    if week:
        query = query.where("week", "==", week)

    pre_ids = set()
    post_ids = set()
    for doc in query.stream():
        data = doc.to_dict()
        pid = data.get("participant_id", "")
        if data.get("phase") == "pre":
            pre_ids.add(pid)
        elif data.get("phase") == "post":
            post_ids.add(pid)

    return sorted(pre_ids & post_ids)


# ── CSV export ─────────────────────────────────────────────────────────
def export_surveys_csv(subject: str = "", phase: str = "") -> str:
    """Export survey data as a CSV string suitable for pandas / SPSS / R.

    Columns: participant_id, subject, week, phase, recorded_at,
             <item_1>, <item_2>, …

    Parameters
    ----------
    subject : str, optional
        Filter to a single subject.  Empty = all subjects.
    phase : str, optional
        Filter to ``"pre"`` or ``"post"``.  Empty = both.

    Returns
    -------
    str  – CSV content.
    """
    coll = _db().collection(COLLECTION)
    query = coll
    if subject:
        query = query.where("subject", "==", subject)
    if phase:
        query = query.where("phase", "==", phase)

    rows: List[Dict] = []
    all_item_keys: set = set()

    for doc in query.stream():
        data = doc.to_dict()
        resp = data.get("responses", {})
        all_item_keys.update(resp.keys())
        row = {
            "participant_id": data.get("participant_id", ""),
            "subject": data.get("subject", ""),
            "week": data.get("week", ""),
            "phase": data.get("phase", ""),
            "recorded_at": data.get("recorded_at", ""),
        }
        row.update(resp)
        rows.append(row)

    # Stable column order
    sorted_items = sorted(all_item_keys)
    fieldnames = ["participant_id", "subject", "week", "phase", "recorded_at"] + sorted_items

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return buf.getvalue()


def export_paired_csv(subject: str, week: str = "") -> str:
    """Export a wide-format CSV with pre and post columns side-by-side
    for paired analysis (Wilcoxon, etc.).

    Columns: participant_id, subject, <item_1>_pre, <item_1>_post, …
    """
    paired_ids = get_paired_participants(subject, week)
    if not paired_ids:
        return ""

    rows = []
    all_items: set = set()

    for pid in paired_ids:
        pre = get_survey(pid, subject, "pre", week) or {}
        post = get_survey(pid, subject, "post", week) or {}
        pre_resp = pre.get("responses", {})
        post_resp = post.get("responses", {})
        all_items.update(pre_resp.keys())
        all_items.update(post_resp.keys())

        row = {"participant_id": pid, "subject": subject, "week": week}
        for item in pre_resp:
            row[f"{item}_pre"] = pre_resp[item]
        for item in post_resp:
            row[f"{item}_post"] = post_resp[item]
        rows.append(row)

    sorted_items = sorted(all_items)
    fieldnames = ["participant_id", "subject", "week"]
    for item in sorted_items:
        fieldnames.extend([f"{item}_pre", f"{item}_post"])

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return buf.getvalue()
