"""
Unified LLM provider factory – Groq only, .env-driven.

Usage
-----
llm = get_llm()                                   # uses .env defaults
llm = get_llm(model_name="llama-3.3-70b-versatile")        # one-off model
llm = get_llm(temperature=0.7, max_tokens=2048)   # tweak params
"""

from __future__ import annotations
import os, functools
from typing import Any
from dotenv import load_dotenv
load_dotenv()                        # pick-up .env early

def _get_groq(**kw: Any):
    from langchain_groq import ChatGroq
    return ChatGroq(
        groq_api_key=os.environ["GROQ_API_KEY"],
        model_name  = kw.get("model_name" ,
                             os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")),
        temperature = float(kw.get("temperature" ,
                             os.getenv("LLM_TEMPERATURE", "0.1"))),
        max_tokens  = int  (kw.get("max_tokens"  ,
                             os.getenv("LLM_MAX_TOKENS", "1024"))),
    )

_PROVIDER_MAP = {
    "groq":         _get_groq,
}

@functools.lru_cache  # cache only *no-arg* calls
def _get_llm_cached(provider: str):
    return _PROVIDER_MAP[provider]()

def get_llm(
        provider: str | None = None,
        **overrides: Any
):
    """
    get_llm()                            – use .env defaults
    get_llm(model_name="llama3-8b")      – single-call override
    """
    sel = (provider or os.getenv("LLM_PROVIDER", "groq")).lower()
    if sel not in _PROVIDER_MAP:
        raise ValueError(f"Unknown provider '{sel}'")
    if not overrides:
        return _get_llm_cached(sel)
    return _PROVIDER_MAP[sel](**overrides)
