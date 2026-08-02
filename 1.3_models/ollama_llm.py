"""Ollama chat-model configuration."""

from __future__ import annotations

import os
from typing import Any

from langchain_ollama import ChatOllama


def create_ollama_llm(**overrides: Any) -> ChatOllama:
    """Create an Ollama chat model using environment configuration."""

    model = str(
        overrides.get("model")
        or overrides.get("model_name")
        or os.getenv("OLLAMA_MODEL", "llama3.2")
    )

    base_url = str(
        overrides.get("base_url")
        or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )

    temperature_value = overrides.get("temperature")
    if temperature_value is None:
        temperature_value = os.getenv("LLM_TEMPERATURE", "0.1")

    max_tokens_value = overrides.get("max_tokens")
    if max_tokens_value is None:
        max_tokens_value = os.getenv("LLM_MAX_TOKENS", "1024")

    return ChatOllama(
        model=model,
        base_url=base_url,
        temperature=float(temperature_value),
        num_predict=int(max_tokens_value),
        validate_model_on_init=False,
    )