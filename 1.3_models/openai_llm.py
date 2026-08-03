"""OpenAI chat-model configuration."""

from __future__ import annotations

import os
from typing import Any

from langchain_openai import ChatOpenAI


def create_openai_llm(**overrides: Any) -> ChatOpenAI:
    """Create an OpenAI chat model using environment configuration."""

    api_key = (
        overrides.get("api_key")
        or overrides.get("openai_api_key")
        or os.getenv("OPENAI_API_KEY")
    )

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured. "
            "Add it to your local .env file or select Groq or Ollama."
        )

    model = str(
        overrides.get("model")
        or overrides.get("model_name")
        or os.getenv("OPENAI_MODEL", "gpt-5-mini")
    )

    temperature_value = overrides.get("temperature")
    if temperature_value is None:
        temperature_value = os.getenv("LLM_TEMPERATURE", "0.1")

    max_tokens_value = overrides.get("max_tokens")
    if max_tokens_value is None:
        max_tokens_value = os.getenv("LLM_MAX_TOKENS", "1024")

    return ChatOpenAI(
        api_key=api_key,
        model=model,
        temperature=float(temperature_value),
        max_tokens=int(max_tokens_value),
    )