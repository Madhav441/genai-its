"""
Module 5: Audit & Observability
Sujal - GenAITS Security Framework

This module provides audit logging for security-relevant events.

Current support:
- Local JSONL logging.
- Optional Firestore logging to the audit_logs collection.
- Sensitive metadata redaction.
- Local JSONL fallback if Firestore is unavailable.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


LOGGER = logging.getLogger(__name__)


VALID_EVENT_TYPES = {
    "auth_attempt",
    "rbac_check",
    "input_sanitisation_flag",
    "output_guardrail_trigger",
    "rate_limit_hit",
    "llm_api_call",
    "quiz_state_change",
    "prompt_template_change",
    "contract_violation",
    "system_error",
}


VALID_SEVERITIES = {
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
}


@dataclass
class AuditEvent:
    """Represents one auditable system or security event."""

    event_id: str
    timestamp: str
    event_type: str
    severity: str
    user_id: Optional[str]
    session_id: Optional[str]
    source_module: Optional[str]
    message: str
    metadata: Dict[str, Any]


class AuditLogger:
    """
    Audit logger for GenAITS.

    Every event is written to a local JSONL file. Firestore is optional
    and disabled by default. If a Firestore write fails, local logging
    continues and the error is stored on the logger instance.
    """

    def __init__(
        self,
        log_file_path: str = "logs/audit_logs.jsonl",
        enable_firestore: bool = False,
        firestore_client: Optional[Any] = None,
        firestore_collection: str = "audit_logs",
    ) -> None:
        self.log_file_path = log_file_path
        self.firestore_collection = firestore_collection
        self.firestore_client = firestore_client

        self.firestore_enabled = (
            enable_firestore or firestore_client is not None
        )

        self.last_firestore_write_succeeded: Optional[bool] = None
        self.last_firestore_error: Optional[str] = None

        self._ensure_log_directory_exists()

        if self.firestore_enabled and self.firestore_client is None:
            self._initialise_firestore_safely()

    def _ensure_log_directory_exists(self) -> None:
        """Create the local log directory when needed."""

        log_directory = os.path.dirname(self.log_file_path)

        if log_directory:
            os.makedirs(log_directory, exist_ok=True)

    def _initialise_firestore_safely(self) -> None:
        """Initialise Firestore without interrupting local logging."""

        try:
            self.firestore_client = self._create_firestore_client()
            self.last_firestore_error = None

        except Exception as exc:
            self.firestore_client = None
            self.firestore_enabled = False
            self.last_firestore_write_succeeded = False
            self.last_firestore_error = f"{type(exc).__name__}: {exc}"

            LOGGER.warning(
                "Firestore could not be initialised. "
                "Local JSONL logging will continue. Error: %s",
                self.last_firestore_error,
            )

    def _create_firestore_client(self) -> Any:
        """Create and return a Firebase Admin Firestore client."""

        try:
            import firebase_admin
            from firebase_admin import firestore

        except ImportError as exc:
            raise RuntimeError(
                "firebase-admin is not installed. Run "
                "'python3 -m pip install firebase-admin'."
            ) from exc

        try:
            firebase_admin.get_app()

        except ValueError:
            firebase_admin.initialize_app()

        return firestore.client()

    def log_event(
        self,
        event_type: str,
        message: str,
        severity: str = "INFO",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        source_module: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Create, sanitise and persist one audit event."""

        if event_type not in VALID_EVENT_TYPES:
            raise ValueError(f"Invalid event_type: {event_type}")

        if severity not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity: {severity}")

        safe_metadata = self._sanitize_metadata(metadata or {})

        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            session_id=session_id,
            source_module=source_module,
            message=message,
            metadata=safe_metadata,
        )

        self._write_event(event)

        if self.firestore_enabled:
            self._write_event_to_firestore(event)

        return event

    def _write_event(self, event: AuditEvent) -> None:
        """Append one audit event to the local JSONL file."""

        with open(
            self.log_file_path,
            "a",
            encoding="utf-8",
        ) as log_file:
            log_file.write(
                json.dumps(
                    asdict(event),
                    ensure_ascii=False,
                )
                + "\n"
            )

    def _write_event_to_firestore(self, event: AuditEvent) -> bool:
        """Write one sanitised audit event to Firestore."""

        if self.firestore_client is None:
            self.last_firestore_write_succeeded = False
            self.last_firestore_error = (
                "Firestore client is not available."
            )
            return False

        try:
            (
                self.firestore_client
                .collection(self.firestore_collection)
                .document(event.event_id)
                .set(asdict(event))
            )

            self.last_firestore_write_succeeded = True
            self.last_firestore_error = None
            return True

        except Exception as exc:
            self.last_firestore_write_succeeded = False
            self.last_firestore_error = f"{type(exc).__name__}: {exc}"

            LOGGER.warning(
                "Firestore audit write failed. "
                "The local JSONL event was retained. Error: %s",
                self.last_firestore_error,
            )

            return False

    def _sanitize_metadata(
        self,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Redact sensitive values and truncate long strings."""

        sensitive_keys = {
            "password",
            "api_key",
            "secret",
            "token",
            "private_key",
            "raw_prompt",
            "full_prompt",
            "student_answer",
            "rubric",
            "answer_key",
        }

        sanitized: Dict[str, Any] = {}

        for key, value in metadata.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "[REDACTED]"

            elif isinstance(value, str) and len(value) > 500:
                sanitized[key] = value[:500] + "...[TRUNCATED]"

            else:
                sanitized[key] = value

        return sanitized


audit_logger = AuditLogger()


if __name__ == "__main__":
    firestore_requested = (
        os.getenv("AUDIT_FIRESTORE_ENABLED", "false")
        .strip()
        .lower()
        in {"1", "true", "yes", "on"}
    )

    logger = AuditLogger(
        enable_firestore=firestore_requested,
    )

    created_event = logger.log_event(
        event_type="system_error",
        severity="INFO",
        user_id="test_user",
        session_id="test_session",
        source_module="audit_logger.py",
        message="Audit logger integration test event created.",
        metadata={
            "test": True,
            "environment": "local_firestore_test",
            "prompt_version": "v1",
            "raw_prompt": (
                "This sensitive test prompt must be redacted."
            ),
        },
    )

    print(f"Local audit event written to {logger.log_file_path}")
    print(f"Event ID: {created_event.event_id}")

    if firestore_requested:
        if logger.last_firestore_write_succeeded:
            print(
                "The same event was written to the Firestore "
                f"'{logger.firestore_collection}' collection."
            )
        else:
            print(
                "Firestore write was not successful. "
                f"Reason: {logger.last_firestore_error}"
            )
    else:
        print(
            "Firestore was not enabled. "
            "Only the local JSONL event was written."
        )
