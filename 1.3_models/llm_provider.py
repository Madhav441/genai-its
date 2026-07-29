"""Configuration-driven LLM provider factory for Groq and Ollama.

Examples:
    llm = get_llm()                         # uses LLM_PROVIDER from .env
    llm = get_llm(provider="ollama")        # one-call provider override
    llm = get_llm(model_name="llama3.2")    # one-call model override
"""

from __future__ import annotations

import functools
import os
import pathlib
import sys
from typing import Any, Callable

from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
SECURITY_DIR = ROOT / "1.5_security"
if str(SECURITY_DIR) not in sys.path:
    sys.path.insert(0, str(SECURITY_DIR))

from rate_limiter import apply_governance
from groq_llm import get_groq_llm
from ollama_llm import get_ollama_llm

load_dotenv(ROOT / ".env")

ProviderFactory = Callable[..., Any]
_PROVIDER_MAP: dict[str, ProviderFactory] = {
    "groq": get_groq_llm,
    "ollama": get_ollama_llm,
}


@functools.lru_cache(maxsize=4)
def _get_llm_cached(provider: str, caller_id: str):
    return apply_governance(_PROVIDER_MAP[provider](), caller_id=caller_id)


def get_llm(provider: str | None = None, **overrides: Any):
    """Return a governed LLM selected through configuration.

    Supported providers are ``groq`` and ``ollama``. The optional ``caller_id``
    is used to maintain separate prototype rate-limit counters.
    """
    selected = (provider or os.getenv("LLM_PROVIDER", "groq")).strip().lower()
    if selected not in _PROVIDER_MAP:
        supported = ", ".join(sorted(_PROVIDER_MAP))
        raise ValueError(f"Unknown LLM provider '{selected}'. Supported providers: {supported}.")

    caller_id = str(overrides.pop("caller_id", "global"))
    # Backwards compatibility with older calls that used model=...
    if "model" in overrides and "model_name" not in overrides:
        overrides["model_name"] = overrides.pop("model")

    if not overrides:
        return _get_llm_cached(selected, caller_id)
    return apply_governance(_PROVIDER_MAP[selected](**overrides), caller_id=caller_id)
