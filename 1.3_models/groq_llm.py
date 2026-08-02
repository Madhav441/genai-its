# 1.3_models/groq_llm.py  –  DEPRECATED SHIM
# ─────────────────────────────────────────────────────────────────────────
"""
Backward-compatibility shim.  All LLM access should go through
``llm_provider.get_llm()`` instead.  This module re-exports the factory
so old imports (``from groq_llm import get_groq_llm``) still resolve.
"""
import warnings as _w
from llm_provider import get_llm as _get_llm

def get_groq_llm(**kwargs):
    _w.warn(
        "groq_llm.get_groq_llm() is deprecated — use llm_provider.get_llm()",
        DeprecationWarning,
        stacklevel=2,
    )
    return _get_llm(**kwargs)
