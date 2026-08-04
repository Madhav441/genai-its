"""Controlled RT-06 rate-limit abuse demonstration.

This script:
1. Uses the real UsageGovernor and GovernedLLM.
2. Allows the first request.
3. Blocks the second request.
4. Records the real rate_limit_hit event.
5. Verifies that the event exists in Firestore.

Test records are stored in audit_logs_test.
"""

from typing import Any

import rate_limiter
from audit_logger import AuditEvent, AuditLogger
from rate_limiter import (
    GovernanceConfig,
    GovernedLLM,
    RateLimitExceeded,
    UsageGovernor,
)


class CapturingAuditLogger(AuditLogger):
    """Audit logger that retains created events for verification."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.created_events: list[AuditEvent] = []

    def log_event(self, **kwargs: Any) -> AuditEvent:
        event = super().log_event(**kwargs)
        self.created_events.append(event)
        return event


class DemoLLM:
    """Safe fake provider used without contacting a real AI model."""

    def invoke(self, message: str) -> str:
        return f"Processed: {message}"


def main() -> None:
    logger = CapturingAuditLogger(
        log_file_path="logs/rt06_rate_limit_demo.jsonl",
        enable_firestore=True,
        firestore_collection="audit_logs_test",
    )

    if logger.firestore_client is None:
        raise RuntimeError(
            "Firestore could not be initialised: "
            f"{logger.last_firestore_error}"
        )

    # Replace the rate limiter's default local logger only for this demo.
    rate_limiter.audit_logger = logger

    governor = UsageGovernor(
        GovernanceConfig(
            enabled=True,
            requests=1,
            window_seconds=60,
            daily_request_limit=10,
            daily_budget_usd=1.0,
        )
    )

    llm = GovernedLLM(
        DemoLLM(),
        caller_id="rt06-controlled-demo-user",
        governor=governor,
        provider="controlled-demo",
    )

    first_result = llm.invoke("allowed request")
    print(f"First request: {first_result}")

    try:
        llm.invoke("repeated request")
    except RateLimitExceeded as exc:
        print(f"Second request blocked: {exc}")
    else:
        raise RuntimeError(
            "RT-06 failed because the second request was not blocked."
        )

    rate_limit_events = [
        event
        for event in logger.created_events
        if event.event_type == "rate_limit_hit"
    ]

    if not rate_limit_events:
        raise RuntimeError(
            "The request was blocked but no rate_limit_hit event was created."
        )

    event = rate_limit_events[-1]

    document = (
        logger.firestore_client
        .collection(logger.firestore_collection)
        .document(event.event_id)
        .get()
    )

    if not document.exists:
        raise RuntimeError(
            "The rate_limit_hit event was not found in Firestore."
        )

    stored_event = document.to_dict()

    if stored_event.get("event_type") != "rate_limit_hit":
        raise RuntimeError(
            "The Firestore document contains the wrong event type."
        )

    print()
    print("RT-06 RED-TEAM TEST PASSED")
    print(f"Event ID: {event.event_id}")
    print(f"Event type: {event.event_type}")
    print(f"Severity: {event.severity}")
    print(f"Source module: {event.source_module}")
    print(f"Firestore collection: {logger.firestore_collection}")
    print("Firestore verification: successful")


if __name__ == "__main__":
    main()
