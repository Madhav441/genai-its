"""Automated tests for the shared LLM request governor."""

from pathlib import Path
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SECURITY_DIR = PROJECT_ROOT / "1.5_security"

if str(SECURITY_DIR) not in sys.path:
    sys.path.insert(0, str(SECURITY_DIR))


from rate_limiter import (  # noqa: E402
    GovernanceConfig,
    GovernedLLM,
    RateLimitExceeded,
    UsageGovernor,
)


class FakeLLM:
    """Fake model that does not contact Groq or Ollama."""

    def invoke(self, message):
        return f"received: {message}"


def test_governed_llm_allows_requests_within_limit():
    governor = UsageGovernor(
        GovernanceConfig(
            enabled=True,
            requests=2,
            window_seconds=60,
            daily_request_limit=10,
        )
    )

    llm = GovernedLLM(
        FakeLLM(),
        caller_id="allowed-user",
        governor=governor,
    )

    assert llm.invoke("one") == "received: one"
    assert llm.invoke("two") == "received: two"


def test_governed_llm_blocks_request_over_limit():
    governor = UsageGovernor(
        GovernanceConfig(
            enabled=True,
            requests=2,
            window_seconds=60,
            daily_request_limit=10,
        )
    )

    llm = GovernedLLM(
        FakeLLM(),
        caller_id="blocked-user",
        governor=governor,
    )

    llm.invoke("one")
    llm.invoke("two")

    with pytest.raises(RateLimitExceeded):
        llm.invoke("three")


def test_disabled_governance_allows_all_requests():
    governor = UsageGovernor(
        GovernanceConfig(
            enabled=False,
            requests=1,
            window_seconds=60,
            daily_request_limit=1,
        )
    )

    llm = GovernedLLM(
        FakeLLM(),
        caller_id="disabled-user",
        governor=governor,
    )

    assert llm.invoke("one") == "received: one"
    assert llm.invoke("two") == "received: two"