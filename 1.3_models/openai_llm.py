"""OpenAI provider adapter for cloud model routing."""

from __future__ import annotations

import os
from typing import Any


def get_openai_llm(**overrides: Any):
    """Create an OpenAI chat model using local environment credentials."""

    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI support is not installed. Run: pip install langchain-openai"
        ) from exc

    api_key = str(
        overrides.pop("api_key", None)
        or os.getenv("OPENAI_API_KEY", "")
    ).strip()

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Add it only to your local .env file."
        )

    model_name = str(
        overrides.pop("model_name", None)
        or overrides.pop("model", None)
        or os.getenv("OPENAI_MODEL", "gpt-5-mini")
    )

    parameters: dict[str, Any] = {
        "api_key": api_key,
        "model": model_name,
    }

    max_tokens = overrides.pop(
        "max_tokens",
        os.getenv("LLM_MAX_TOKENS", "1024"),
    )
    if max_tokens not in (None, ""):
        parameters["max_tokens"] = int(max_tokens)

    temperature = overrides.pop(
        "temperature",
        os.getenv("LLM_TEMPERATURE", "0.1"),
    )

    # Some reasoning models do not accept a custom temperature.
    if temperature not in (None, "") and not model_name.lower().startswith("gpt-5"):
        parameters["temperature"] = float(temperature)

    parameters.update(overrides)

    return ChatOpenAI(**parameters)