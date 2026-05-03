"""
config_validator.py

Sprint 1 infrastructure validation module for GenAI ITS.

Design Principle Alignment:
- DP1 Modular Decoupling: This module is standalone and can be used without changing UI or agent logic.
- DP5 Configuration-Driven Model Routing: Validates provider-related environment settings before runtime.

Purpose:
Checks whether required environment variables and Streamlit secrets are available before the app runs.
This helps avoid unclear runtime crashes caused by missing API keys or Firebase configuration.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Tuple

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
STREAMLIT_SECRETS_PATH = PROJECT_ROOT / ".streamlit" / "secrets.toml"

SUPPORTED_PROVIDERS = {"groq", "openai", "ollama"}


def load_environment() -> None:
    """Load environment variables from the .env file if it exists."""
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH)


def check_env_file_exists() -> Tuple[bool, str]:
    """Check whether the .env file exists."""
    if ENV_PATH.exists():
        return True, ".env file found."
    return False, ".env file missing. Copy .env.example to .env and add real values."


def check_provider_config() -> Tuple[bool, str]:
    """Validate the selected LLM provider."""
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()

    if not provider:
        return False, "LLM_PROVIDER is missing in .env."

    if provider not in SUPPORTED_PROVIDERS:
        return False, f"Unsupported LLM_PROVIDER '{provider}'. Use one of: {', '.join(SUPPORTED_PROVIDERS)}."

    return True, f"LLM_PROVIDER is valid: {provider}"


def check_provider_keys() -> Tuple[bool, str]:
    """Validate API key requirements based on selected provider."""
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()

    if provider == "groq":
        if os.getenv("GROQ_API_KEY"):
            return True, "GROQ_API_KEY found."
        return False, "GROQ_API_KEY missing. Add it to .env."

    if provider == "openai":
        if os.getenv("OPENAI_API_KEY"):
            return True, "OPENAI_API_KEY found."
        return False, "OPENAI_API_KEY missing. Add it to .env."

    if provider == "ollama":
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return True, f"Ollama selected. Expected local server at {ollama_url}."

    return False, "Cannot validate provider key because LLM_PROVIDER is invalid or missing."


def check_streamlit_secrets() -> Tuple[bool, str]:
    """Check whether Streamlit Firebase secrets file exists."""
    if STREAMLIT_SECRETS_PATH.exists():
        return True, ".streamlit/secrets.toml found."
    return False, ".streamlit/secrets.toml missing. Firebase/Firestore will not connect until this is configured."


def run_all_checks() -> Dict[str, List[str]]:
    """Run all configuration checks and return passed/failed messages."""
    load_environment()

    checks = [
        check_env_file_exists(),
        check_provider_config(),
        check_provider_keys(),
        check_streamlit_secrets(),
    ]

    passed = [message for status, message in checks if status]
    failed = [message for status, message in checks if not status]

    return {"passed": passed, "failed": failed}


def print_validation_report() -> None:
    """Print a readable validation report for developers."""
    results = run_all_checks()

    print("\nGenAI ITS Configuration Validation Report")
    print("----------------------------------------")

    if results["passed"]:
        print("\nPassed checks:")
        for message in results["passed"]:
            print(f"  [OK] {message}")

    if results["failed"]:
        print("\nFailed checks:")
        for message in results["failed"]:
            print(f"  [WARN] {message}")

    if not results["failed"]:
        print("\nAll required configuration checks passed.")
    else:
        print("\nSome configuration checks failed. Fix these before full deployment.")


if __name__ == "__main__":
    print_validation_report()