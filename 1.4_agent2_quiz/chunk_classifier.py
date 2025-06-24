# # ────────────────────────────────────────────────────────────────
# #  chunk_classifier.py
# #  Very‑light classifier → "question" | "context"
# # ────────────────────────────────────────────────────────────────
# import logging, os
# from typing import Literal
# from groq_llm import get_groq_llm        # same helper you already have

# __all__ = ["classify_chunk"]

# logging.basicConfig(level=logging.INFO)

# LLM = get_groq_llm(model=os.getenv("CLASSIFIER_MODEL", "llama3-8b-8192"))
# _VALID: set[str] = {"question", "context"}


# def classify_chunk(text: str) -> Literal["question", "context"]:
#     """
#     Classify a text chunk using an LLM.
#     Anything that is not recognised as a question ⇒ "context".
#     """
#     prompt = (
#         "You will be given a chunk of text extracted from a study PDF.\n\n"
#         "Return **exactly one word**:\n"
#         "• **question** – if the chunk is asking the learner something they need to answer.\n"
#         "• **context**  – for instructions, explanations, code, headings … anything else.\n\n"
#         "Chunk:\n"
#         "-----\n"
#         f"{text.strip()[:1500]}\n"
#         "-----\n"
#         "One‑word answer:"
#     )

#     try:
#         label = LLM.invoke(prompt).content.strip().lower()
#     except Exception:
#         logging.exception("LLM call failed – defaulting to 'context'")
#         return "context"

#     if label not in _VALID:
#         logging.warning("Unexpected label '%s' – coerced to 'context'", label)
#         return "context"

#     logging.debug("%-8s | %.90s", label, text.replace("\n", " "))
#     return label  # type: ignore[return-value]
# ────────────────────────────────────────────────────────────────
#  chunk_classifier.py   (stub – kept for legacy imports)
# ────────────────────────────────────────────────────────────────
# def classify_chunk(_: str) -> str:          # always returns "context"
#     return "context"




# ────────────────────────────────────────────────────────────────
#  chunk_classifier.py
#  Two-label Groq-LLM classifier → "question" | "context"
# ────────────────────────────────────────────────────────────────
"""
Called by context_binder.assign_context_to_questions().
If the LLM call fails or returns something unexpected we
gracefully fall back to "context" so extraction never crashes.
"""

from typing import Literal
import os, logging
from llm_provider import get_llm   # helper already in your repo

__all__ = ["classify_chunk"]

logging.basicConfig(level=logging.INFO)

LLM = get_llm(model=os.getenv("CLASSIFIER_MODEL",
                                   "llama3-8b-8192"))
+# 2025-05-10  update – allow richer labels so we keep useful chunks
_VALID: set[str] = {
    "question",          # learner must answer
    "context",           # general instructional text
    "answer",            # official solutions / rubrics
    "code",              # code blocks or variable tables
    "metadata",          # headings, section titles …
}


def classify_chunk(text: str) -> Literal["question", "context"]:
    """
    Identify whether *text* is an assessment question (learner
    must answer) or just explanatory / code / metadata context.

    Returns one of the strings in _VALID.
    """
    prompt = (
        "Classify the PDF chunk below.  Return **exactly one word** "
        "from this list:\n"
        "  question  – learner must answer\n"
        "  answer    – model answer / rubric\n"
        "  code      – code blocks, tables of variables/constants\n"
        "  context   – explanatory prose, instructions\n"
        "  metadata  – headings, page numbers, boiler-plate\n\n"
        "-----\n"
        f"{text.strip()[:1500]}\n"
        "-----\n"
        "One-word answer:"
    )

    try:
        label = LLM.invoke(prompt).content.strip().lower()
    except Exception:
        logging.exception("LLM call failed – defaulting to 'context'")
        return "context"

    if label not in _VALID:
        logging.warning("Unexpected label '%s' – coerced to 'context'", label)
        return "context"

    logging.debug("%-8s | %.90s", label, text.replace("\n", " "))
    return label  # type: ignore[return-value]
