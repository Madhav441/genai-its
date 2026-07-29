"""Groq provider adapter."""

from __future__ import annotations

import os
from typing import Any


def get_groq_llm(**overrides: Any):
    from langchain_groq import ChatGroq

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing. Add it to your local .env file.")

    model_name = overrides.get("model_name") or overrides.get("model") or os.getenv(
        "GROQ_MODEL", "llama-3.3-70b-versatile"
    )
    temperature = float(overrides.get("temperature", os.getenv("LLM_TEMPERATURE", "0.1")))
    max_tokens = int(overrides.get("max_tokens", os.getenv("LLM_MAX_TOKENS", "1024")))

    return ChatGroq(
        groq_api_key=api_key,
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
    )
