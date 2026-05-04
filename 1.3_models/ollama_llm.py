# 1.3_models/ollama_llm.py  –  DEPRECATED PLACEHOLDER
# ─────────────────────────────────────────────────────────────────────────
"""
Ollama support was removed in favour of the Groq-only ``llm_provider``.
This file exists only to prevent ``ImportError`` from stale references.
"""
raise ImportError(
    "ollama_llm is no longer supported.  Use llm_provider.get_llm() instead."
)
