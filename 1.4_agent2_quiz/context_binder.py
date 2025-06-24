# ────────────────────────────────────────────────────────────────
#  context_binder.py
#  Attach preceding context / code to every QUESTION chunk
# ────────────────────────────────────────────────────────────────
"""
Works in tandem with chunk_classifier.classify_chunk().
Window size can be increased (default = 3) if you feel context
is still too sparse.
"""

from typing import List, Dict
from chunk_classifier import classify_chunk

__all__ = ["assign_context_to_questions"]

_WINDOW = 3                           # ← broaden if you like (e.g. 5)
_CODE_HINTS = ("```", "print(", "=")  # quick-n-dirty code heuristics


def assign_context_to_questions(chunks: List[str]) -> List[Dict]:
    """Return [{'id', 'question', 'context'}, …]"""
    labeled = [{"text": c, "label": classify_chunk(c)} for c in chunks]

    questions = []
    for idx, item in enumerate(labeled):
        if item["label"] != "question":
            continue

        ctx_parts, code_parts = [], []

        for off in range(-_WINDOW, _WINDOW + 1):
            if off == 0 or not (0 <= idx + off < len(labeled)):
                continue
            neighbour = labeled[idx + off]

            if neighbour["label"] == "question":
                continue

            text = neighbour["text"].strip()
            looks_like_code = any(h in text for h in _CODE_HINTS)

            if looks_like_code:
                code_parts.append(text)
            elif neighbour["label"] == "context":
                ctx_parts.append(text)

        context_blob = "\n\n".join(code_parts + ctx_parts)

        questions.append({
            "id": len(questions) + 1,
            "question": item["text"].strip(),
            "context": context_blob.strip()
        })

    return questions
