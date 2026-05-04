"""
Module 5: Audit & Observability
Sujal - GenAITS Security Framework

This module provides a standalone audit logger for security-relevant events.
It supports local JSONL logging now, and can later be extended to Firestore.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional


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
    """
    Represents one auditable system/security event.
    """

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
    Standalone audit logger for GenAITS.

    Default behaviour:
    - Writes audit logs to local JSONL file.
    - Each line is one JSON audit event.
    - Avoids storing full sensitive prompts or student answers by default.

    Later extension:
    - Add Firestore write support for the audit_logs collection.
    """

    def __init__(self, log_file_path: str = "logs/audit_logs.jsonl"):
        self.log_file_path = log_file_path
        self._ensure_log_directory_exists()

    def _ensure_log_directory_exists(self) -> None:
        log_dir = os.path.dirname(self.log_file_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

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
        """
        Create and persist an audit event.

        Args:
            event_type: Type of event, e.g. "llm_api_call" or "contract_violation".
            message: Human-readable event summary.
            severity: INFO, WARNING, ERROR, or CRITICAL.
            user_id: Optional user identifier.
            session_id: Optional session identifier.
            source_module: Module or file that generated the event.
            metadata: Extra structured data. Avoid raw secrets, full prompts, or full answers.

        Returns:
            AuditEvent object.
        """

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
        return event

    def _write_event(self, event: AuditEvent) -> None:
        with open(self.log_file_path, "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")

    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove or mask sensitive fields before writing logs.
        """

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

        sanitized = {}

        for key, value in metadata.items():
            key_lower = key.lower()

            if key_lower in sensitive_keys:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > 500:
                sanitized[key] = value[:500] + "...[TRUNCATED]"
            else:
                sanitized[key] = value

        return sanitized


# Convenience logger instance for simple imports
audit_logger = AuditLogger()


if __name__ == "__main__":
    logger = AuditLogger()

    logger.log_event(
        event_type="system_error",
        severity="INFO",
        user_id="test_user",
        session_id="test_session",
        source_module="audit_logger.py",
        message="Audit logger test event created successfully.",
        metadata={
            "test": True,
            "raw_prompt": "This should not appear in the log file.",
        },
    )

    print("Audit logger test event written to logs/audit_logs.jsonl")