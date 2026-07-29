"""Configuration-driven LLM routing for Groq, Ollama and OpenAI."""

from __future__ import annotations

import functools
import json
import logging
import os
import pathlib
import sys
from typing import Any, Callable

import yaml
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "1.3_models" / "provider_config.yaml"
SECURITY_DIR = ROOT / "1.5_security"

if str(SECURITY_DIR) not in sys.path:
    sys.path.insert(0, str(SECURITY_DIR))

from rate_limiter import apply_governance
from groq_llm import get_groq_llm
from ollama_llm import get_ollama_llm
from openai_llm import get_openai_llm

load_dotenv(ROOT / ".env")

logger = logging.getLogger(__name__)

ProviderFactory = Callable[..., Any]

_PROVIDER_MAP: dict[str, ProviderFactory] = {
    "groq": get_groq_llm,
    "ollama": get_ollama_llm,
    "openai": get_openai_llm,
}

_INTERNAL_CONFIG_FIELDS = {
    "enabled",
    "api_key_env",
}


def _load_routing_config() -> dict[str, Any]:
    """Load and validate the YAML model-routing configuration."""

    if not CONFIG_PATH.exists():
        raise RuntimeError(
            f"Provider configuration was not found: {CONFIG_PATH}"
        )

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file) or {}
    except yaml.YAMLError as exc:
        raise RuntimeError(
            f"Invalid YAML in {CONFIG_PATH.name}: {exc}"
        ) from exc

    if not isinstance(config, dict):
        raise RuntimeError(
            "Provider configuration must contain a YAML mapping."
        )

    providers = config.get("providers")
    if not isinstance(providers, dict) or not providers:
        raise RuntimeError(
            "Provider configuration must contain a non-empty 'providers' section."
        )

    return config


def _resolve_provider(
    config: dict[str, Any],
    provider: str | None,
) -> str:
    """Select an explicit provider or the active provider from YAML."""

    selected = (
        provider
        or config.get("active_provider")
        or os.getenv("LLM_PROVIDER")
        or "groq"
    )

    selected = str(selected).strip().lower()

    if selected not in _PROVIDER_MAP:
        supported = ", ".join(sorted(_PROVIDER_MAP))
        raise ValueError(
            f"Unknown LLM provider '{selected}'. "
            f"Supported providers: {supported}."
        )

    return selected


def _get_provider_settings(
    config: dict[str, Any],
    provider: str,
) -> dict[str, Any]:
    """Return safe constructor settings for one provider."""

    providers = config["providers"]
    provider_config = providers.get(provider)

    if not isinstance(provider_config, dict):
        raise RuntimeError(
            f"Provider '{provider}' is missing from provider_config.yaml."
        )

    if not provider_config.get("enabled", True):
        raise RuntimeError(
            f"Provider '{provider}' is disabled in provider_config.yaml."
        )

    key_environment_name = provider_config.get("api_key_env")

    if key_environment_name:
        key_value = os.getenv(str(key_environment_name), "").strip()

        if not key_value:
            raise RuntimeError(
                f"{key_environment_name} is missing. "
                "Add it only to your local .env file."
            )

    return {
        key: value
        for key, value in provider_config.items()
        if key not in _INTERNAL_CONFIG_FIELDS and value is not None
    }


@functools.lru_cache(maxsize=12)
def _get_llm_cached(
    provider: str,
    caller_id: str,
    settings_json: str,
):
    """Create and cache a governed provider instance."""

    settings = json.loads(settings_json)
    llm = _PROVIDER_MAP[provider](**settings)

    return apply_governance(llm, caller_id=caller_id)


def _build_provider(
    provider: str,
    caller_id: str,
    settings: dict[str, Any],
):
    settings_json = json.dumps(settings, sort_keys=True)
    return _get_llm_cached(provider, caller_id, settings_json)


def get_llm(provider: str | None = None, **overrides: Any):
    """Return a governed LLM selected through YAML configuration.

    Selection order:

    1. Explicit ``provider=`` argument
    2. ``active_provider`` in provider_config.yaml
    3. Legacy ``LLM_PROVIDER`` environment variable
    """

    config = _load_routing_config()
    selected = _resolve_provider(config, provider)
    caller_id = str(overrides.pop("caller_id", "global"))

    # Backward compatibility with calls using model=...
    if "model" in overrides and "model_name" not in overrides:
        overrides["model_name"] = overrides.pop("model")

    try:
        settings = _get_provider_settings(config, selected)
        settings.update(overrides)

        return _build_provider(
            selected,
            caller_id,
            settings,
        )

    except Exception as primary_error:
        allow_fallback = bool(config.get("allow_fallback", False))
        fallback = str(
            config.get("fallback_provider", "")
        ).strip().lower()

        if (
            allow_fallback
            and fallback
            and fallback != selected
            and fallback in _PROVIDER_MAP
        ):
            logger.warning(
                "Provider '%s' could not initialise: %s. "
                "Falling back to '%s'.",
                selected,
                primary_error,
                fallback,
            )

            fallback_settings = _get_provider_settings(
                config,
                fallback,
            )

            return _build_provider(
                fallback,
                caller_id,
                fallback_settings,
            )

        raise


def get_routing_summary() -> dict[str, Any]:
    """Return a safe routing summary without exposing API keys."""

    config = _load_routing_config()
    providers = config.get("providers", {})

    return {
        "active_provider": config.get("active_provider"),
        "fallback_provider": config.get("fallback_provider"),
        "allow_fallback": bool(config.get("allow_fallback", False)),
        "enabled_providers": [
            name
            for name, settings in providers.items()
            if isinstance(settings, dict)
            and settings.get("enabled", True)
        ],
    }