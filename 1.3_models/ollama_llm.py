"""Ollama provider adapter for local/offline model routing."""

from __future__ import annotations

import os
from typing import Any


def get_ollama_llm(**overrides: Any):
    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        try:
            from langchain_community.chat_models import ChatOllama
        except ImportError as exc:
            raise RuntimeError(
                "Ollama support is not installed. Run: pip install langchain-ollama ollama"
            ) from exc

    model_name = overrides.get("model_name") or overrides.get("model") or os.getenv(
        "OLLAMA_MODEL", "llama3.2"
    )
    base_url = overrides.get("base_url") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    temperature = float(overrides.get("temperature", os.getenv("LLM_TEMPERATURE", "0.1")))

    return ChatOllama(model=model_name, base_url=base_url, temperature=temperature)
