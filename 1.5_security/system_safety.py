"""Central safety-net helpers for startup and user-facing failures."""

from __future__ import annotations

import logging
from typing import Any, Callable, TypeVar

import firebase_admin
from firebase_admin import credentials, firestore

T = TypeVar("T")
LOGGER = logging.getLogger(__name__)


class ConfigurationError(RuntimeError):
    """Raised when required startup configuration is absent or invalid."""


class ExternalServiceError(RuntimeError):
    """Raised when Firebase or another external service cannot be reached."""


def initialise_firestore(streamlit_module: Any):
    """Initialise Firestore once and return a client with clear safe errors."""
    try:
        firebase_values = streamlit_module.secrets.get("FIREBASE")
    except Exception as exc:
        raise ConfigurationError(
            "Firebase configuration could not be read. Copy "
            ".streamlit/secrets.example.toml to .streamlit/secrets.toml and add valid values."
        ) from exc

    if not firebase_values:
        raise ConfigurationError(
            "Firebase configuration is missing. Add a [FIREBASE] section to "
            ".streamlit/secrets.toml."
        )

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(dict(firebase_values))
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as exc:
        LOGGER.exception("Firebase startup failed")
        raise ExternalServiceError(
            "The database service is currently unavailable or incorrectly configured. "
            "Please check the Firebase settings and try again."
        ) from exc


def safe_call(
    operation: Callable[..., T],
    *args: Any,
    friendly_message: str = "The requested operation could not be completed safely.",
    **kwargs: Any,
) -> T:
    """Execute an operation and hide sensitive technical details from end users."""
    try:
        return operation(*args, **kwargs)
    except (ConfigurationError, ExternalServiceError):
        raise
    except Exception as exc:
        LOGGER.exception("Protected operation failed")
        raise ExternalServiceError(friendly_message) from exc
