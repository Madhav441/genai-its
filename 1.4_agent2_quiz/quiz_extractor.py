# 1.4_agent2_quiz/quiz_extractor.py
# ─────────────────────────────────────────────────────────────────────────
"""
PDF → (question, context, answer-rubric) extractor
↳ OCR fallback now uses unstructured.partition.pdf with strategy="ocr_only".

Returned list item:
{
  "id":       1,
  "question": "…?",
  "context":  "…all info learner needs…",
  "answer":   [ { "criterion": str, "marks": int }, … ]
}
"""

from __future__ import annotations
from typing import List, Dict
import os, json, re, textwrap, shutil, warnings, copy
import streamlit as st
from llm_provider import get_llm

from unstructured.partition.pdf import partition_pdf          # single import

# ── Tunables ────────────────────────────────────────────────────────────
MAX_CHARS      = 24_000                # ≈ 7 200 tokens
OCR_LANGUAGES  = "eng+equ"            # add more langs if you need them
TEXT_THRESHOLD = 1_000                # chars – if fewer → trigger OCR

# ── Prompts (unchanged) ─────────────────────────────────────────────────
EXTRACT_PROMPT = """\
You are an expert teaching assistant.

TASK:
1. Read the PDF text (≤25 k characters) that follows.
2. Find every assessment question.
3. For each question, output its text and the minimal context required in the following plain text format:

Question: <question text>
Context: <minimal context>

Separate each question block with a blank line and do not output any extra text.
"""

# ENRICH_PROMPT = textwrap.dedent("""\
#     ROLE
#       • Subject-matter teaching assistant
#       • Excellent at building marking rubrics

#     TASK
#       1. *Verify & enrich* the context so the learner sees
#          **all variables / code / tables essential** to answer the question.
#       2. *Create an answer rubric* – JSON **array** of
#          {{"criterion": str, "marks": int}} items (total ≈ 10 marks).

#     RETURN STRICT JSON (no markdown):

#       {{
#         "context": "<<clean enriched context>>",
#         "answer":  [ {{ "criterion": "...", "marks": 2 }}, … ]
#       }}

#     ------------------------------------------------------------------
#     FULL PDF TEXT (truncated) ↓
#     {pdf_text}
#     ------------------------------------------------------------------

#     QUESTION
#     «{question}»

#     CURRENT CONTEXT
#     «{context}»
# """)

ENRICH_PROMPT = textwrap.dedent("""\
    ROLE
      • Experienced university tutor & assessment designer

    TASK:
      Review the CURRENT CONTEXT and the FULL PDF TEXT below in relation to the QUESTION.
      • If the question refers to code, variables, tables, or example output, copy the exact relevant lines from the PDF text into the context.
      • Do NOT just summarize or restate the question—always include all code, variables, and example output needed to answer.
      • If details are missing but can be found in the FULL PDF TEXT, append those details.
      • Otherwise, return the CURRENT CONTEXT verbatim.

    CURRENT CONTEXT:
    «{context}»

    FULL PDF TEXT (truncated):
    {pdf_text}

    QUESTION:
    «{question}»

    RESPONSE:
    Return the enriched context as plain text, including all relevant code, variables, and example output.
""")


RUBRIC_PROMPT = textwrap.dedent("""\
    ROLE
      • Senior examiner creating detailed analytic marking rubrics.
      • Follows instructions *exactly*.

    INSTRUCTIONS
      • Include all the asks mentioned in the question and its related context.
      • Almost every sentence, except background and fluff, should be a criteria item.
      • Flesh out the "how" for each criterion, detailing what the response would look like if executed.
      • Be accurate and comprehensive. Only include criteria items that are explicitly asked for.
      • Group similar items together (e.g., character names, code variables) unless specificity is key.
      • Classify each item as:
        - Objective: Yes/No answer (e.g., "Is this present?")
        - Subjective: Requires interpretation (e.g., "Is this appropriate?")
        - Formatting: Relates to presentation or structure.
    RULES
      • Provide ≥ 3 criteria unless the question is trivial; total marks 8-12.
      • Use integers for marks.
      • If a detailed rubric makes no sense, return **one** criterion that
        contains the full correct answer and set "marks": 1 or 2.
      • Never wrap the JSON in back-ticks!

    OUTPUT FORMAT
        {{
            "answer": [
          {{"criterion": "≈1 sentence describing what earns 3 marks", "marks": 3}},
          {{"criterion": "Another criterion",                         "marks": 4}},
          {{"criterion": "Yet another criterion",                     "marks": 3}}
        ]
        }}
      Provide the marking rubric as plain text, formatted as follows:

      - Criterion 1: [Classification: Objective/Subjective/Formatting]
        Description: [What the criterion is about]
        How: [Details on how to evaluate this criterion]

      - Criterion 2: [Classification: Objective/Subjective/Formatting]
        Description: [What the criterion is about]
        How: [Details on how to evaluate this criterion]

      QUESTION
      «{question}»

      CONTEXT
      «{context}»
""")



# ── Helpers ────────────────────────────────────────────────────────────
_MD_FENCE = re.compile(r"```.*?```", re.S)
_JSON_RE  = re.compile(r"(\[.*?\]|\{.*?\})", re.S)


def _pdf_to_text(path: str) -> str:
    """Return ASCII-safe text, auto-switching to OCR if needed."""
    # Pass-1: use embedded text if present
    pages = partition_pdf(filename=path,
                          strategy="fast",
                          infer_table_structure=False)

    embedded_txt = "\n".join(p.text for p in pages if p.text)

    # If text layer is tiny → re-run with OCR
    if len(embedded_txt) < TEXT_THRESHOLD:
        _warn_once(
            "No/low text layer – switching to OCR (Tesseract required).")
        pages = partition_pdf(
            filename=path,
            strategy="ocr_only",
            languages=OCR_LANGUAGES,  # updated from ocr_languages to languages
            infer_table_structure=True,
        )
        embedded_txt = "\n".join(p.text for p in pages if p.text)

    # ASCII-clean + truncate
    embedded_txt = re.sub(r"[^\x00-\x7F]+", " ", embedded_txt)
    return embedded_txt[:MAX_CHARS]


def _clean_json(raw: str) -> str:
    # Remove backticks and markdown fences
    raw = raw.strip("`").strip()
    raw = _MD_FENCE.sub("", raw).strip()

    # Extract JSON-like content
    m = _JSON_RE.search(raw)
    if m:
        return m.group(1).strip()

    # Log a warning if no JSON is found
    _warn_once(f"⚠️ No JSON found – first 300 chars:\n{raw[:300]}")
    return ""


def _repair_json(raw: str) -> str:
    try:
        # Attempt to parse the JSON directly
        json.loads(raw)
        return raw  # If valid, return as is
    except json.JSONDecodeError as e:
        st.warning(f"⚠️ Attempting to repair JSON: {e}")
        # Try basic fixes (e.g., adding missing commas)
        repaired = raw.replace("}{", "},{")  # Fix missing commas between objects
        repaired = re.sub(r",\s*}", "}", repaired)  # Remove trailing commas
        repaired = re.sub(r",\s*\]", "]", repaired)  # Remove trailing commas in arrays
        try:
            json.loads(repaired)  # Validate repaired JSON
            return repaired
        except json.JSONDecodeError:
            return raw  # If still invalid, return original


def _loads(raw: str, fallback):
    try:
        return json.loads(raw)
    except Exception as e:
        st.error(f"❌ JSON parsing error: {e}")
        return fallback


_warned = False
def _warn_once(msg: str) -> None:
    global _warned
    if not _warned:
        warnings.warn(msg)
        _warned = True


# ── Public API ─────────────────────────────────────────────────────────
def parse_extracted_questions(text: str) -> list[dict]:
    """
    Parse plain text output from the LLM into a list of questions and contexts.
    Fixes numbering and ensures correct order. Removes any leading number/label from the question text itself.
    """
    questions = []
    # Split blocks on double newlines
    blocks = [block.strip() for block in text.strip().split("\n\n") if block.strip()]
    # Remove empty or duplicate blocks
    seen = set()
    filtered_blocks = []
    for block in blocks:
        if block not in seen and block:
            filtered_blocks.append(block)
            seen.add(block)
    for idx, block in enumerate(filtered_blocks):
        q_line = None
        c_line = None
        for line in block.splitlines():
            if line.strip().startswith("Question:"):
                q_line = line.split("Question:",1)[1].strip()
            elif line.strip().startswith("Context:"):
                c_line = line.split("Context:",1)[1].strip()
        # Remove any leading number/label from the question text
        if q_line is not None:
            # Fix regex: match optional leading number, then optional ) or . or - or space
            q_line = re.sub(r"^(\d+)[\)\.\-\s]*", "", q_line)
        if q_line is not None and c_line is not None:
            questions.append({
                "id": len(questions) + 1,  # Always sequential, no skipping
                "question": q_line,
                "context": c_line,
            })
    return questions


# Add a function to clean up LLM output for context (remove preambles/conclusions)
def clean_enriched_context(text: str) -> str:
    # Remove common preambles and trailing sentences
    text = text.strip()
    # Remove 'Here is the enriched context:' and similar
    text = re.sub(r"^Here is the enriched context:.*?\n+", "", text, flags=re.I)
    text = re.sub(r"^The question is asking.*?\n+", "", text, flags=re.I)
    text = re.sub(r"^The code is.*?\n+", "", text, flags=re.I)
    # Remove trailing generic sentences
    text = re.sub(r"\n*The (output|answer|result) (is|will be):.*", "", text, flags=re.I)
    # Remove trailing 'This is question ...' or similar
    text = re.sub(r"\n*This is question.*", "", text, flags=re.I)
    # Remove 'The variables are:' etc. if not code
    text = re.sub(r"^The variables (are|used are):.*?\n+", "", text, flags=re.I)
    return text.strip()


def extract_questions_from_pdf(pdf_path: str) -> list[dict]:
    """
    Extract questions, enrich context, and generate rubrics from a PDF using the LLM.
    """
    llm = get_llm()

    # Use partition_pdf to extract text from the PDF
    try:
        pdf_text = _pdf_to_text(pdf_path)  # Use the helper function to extract text
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
        return []

    st.write(f"✂️ Characters sent to LLM (per call): {len(pdf_text):,}")

    # Pass-1: Extract questions
    try:
        response = llm.invoke(
            [
                {"role": "system", "content": EXTRACT_PROMPT},
                {"role": "user", "content": pdf_text},
            ]
        ).content
    except Exception as e:
        st.error(f"Error invoking LLM for question extraction: {e}")
        return []

    questions = parse_extracted_questions(response)
    if not questions:
        st.warning("No questions extracted from the PDF. Please check the file.")
        return []

    st.success(f"✅ Pass-1: extracted {len(questions)} questions")

    # Pass-2: Enrich context
    enriched_questions = []
    for idx, q in enumerate(questions, start=1):
        q.setdefault("id", idx)  # Ensure every question has an ID
        try:
            enrich_prompt = ENRICH_PROMPT.format(
                pdf_text=pdf_text,
                question=q["question"],
                context=q["context"],
            )
            enriched_context = llm.invoke(
                [
                    {"role": "system", "content": "Return ONLY the enriched context as plain text. Do not add any preamble, conclusion, or any answer. Do NOT include any answer, solution, or worked example—just the context needed to answer the question. If the PDF contains an answer or solution, OMIT it from the context."},
                    {"role": "user", "content": enrich_prompt},
                ],
                temperature=0.2  # Slightly higher for more helpful completions
            ).content
            cleaned_context = clean_enriched_context(enriched_context)
            # Remove any lines that look like an answer (e.g., start with 'Answer:', 'Solution:', 'Worked Example:', or are long and not code)
            cleaned_context = re.sub(r"^Answer:.*$", "", cleaned_context, flags=re.MULTILINE)
            cleaned_context = re.sub(r"^Solution:.*$", "", cleaned_context, flags=re.MULTILINE)
            cleaned_context = re.sub(r"^Worked Example:.*$", "", cleaned_context, flags=re.MULTILINE)
            # Remove lines that look like full-sentence answers (not code, not variable, not table)
            cleaned_context = "\n".join([
                line for line in cleaned_context.splitlines()
                if not (line.strip().lower().startswith(("the answer is", "in summary", "to solve this", "therefore", "thus", "correct answer", "final answer")) or (len(line.strip().split()) > 8 and not any(x in line for x in ["=", ":", "print", "input", "for ", "while ", "if ", "def ", "class "])) )
            ])
            # Post-processing: If context is too short or just a restatement, try to extract relevant lines from PDF
            if len(cleaned_context) < 40 or cleaned_context.lower().startswith("the question is asking"):
                # Try to find lines from the PDF that match the question or contain code/output
                q_text = q["question"][:40]
                pdf_lines = pdf_text.splitlines()
                relevant_lines = [line for line in pdf_lines if q_text.split()[0] in line or any(x in line for x in ["=", "print", ":", "+", "input", "output"])]
                if relevant_lines:
                    cleaned_context += "\n" + "\n".join(relevant_lines[:6])
            q["context"] = cleaned_context.strip()
            enriched_questions.append(q)
        except Exception as e:
            st.warning(f"⚠️ Error enriching context for Q{idx}: {e}")
            enriched_questions.append(q)  # Add the question without enrichment
    st.success("✅ Pass-2: context enriched")

    # Pass-3: Generate rubrics
    for q in enriched_questions:
        try:
            rubric_prompt = RUBRIC_PROMPT.format(
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
    st.success("✅ Pass-3: rubrics generated")
    return enriched_questions
