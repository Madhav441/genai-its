"""In-memory request-rate, daily-budget and token-cost controls for LLM calls.

This is intentionally lightweight for the A4 prototype. In a multi-server
production system, counters should be moved to a shared store such as Redis
or Firestore.
"""

from __future__ import annotations

import math
import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import date
from typing import Any


class RateLimitExceeded(RuntimeError):
    """Raised when too many requests are made in the configured time window."""


class DailyBudgetExceeded(RuntimeError):
    """Raised when the configured daily request or cost budget is reached."""


def _as_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


@dataclass(frozen=True)
class GovernanceConfig:
    enabled: bool
    requests: int
    window_seconds: int
    daily_request_limit: int
    daily_budget_usd: float = 1.0

    @classmethod
    def from_environment(cls) -> "GovernanceConfig":
        return cls(
            enabled=_as_bool(
                os.getenv("RATE_LIMIT_ENABLED"),
                True,
            ),
            requests=max(
                1,
                int(os.getenv("RATE_LIMIT_REQUESTS", "10")),
            ),
            window_seconds=max(
                1,
                int(
                    os.getenv(
                        "RATE_LIMIT_WINDOW_SECONDS",
                        "60",
                    )
                ),
            ),
            daily_request_limit=max(
                1,
                int(
                    os.getenv(
                        "LLM_DAILY_REQUEST_LIMIT",
                        "250",
                    )
                ),
            ),
            daily_budget_usd=max(
                0.0,
                float(
                    os.getenv(
                        "LLM_DAILY_BUDGET_USD",
                        "1.00",
                    )
                ),
            ),
        )


class UsageGovernor:
    def __init__(
        self,
        config: GovernanceConfig | None = None,
    ) -> None:
        self.config = (
            config
            or GovernanceConfig.from_environment()
        )

        self._requests: dict[
            str,
            deque[float],
        ] = defaultdict(deque)

        self._daily_counts: dict[
            tuple[str, str],
            int,
        ] = defaultdict(int)

        self._daily_costs: dict[
            tuple[str, str],
            float,
        ] = defaultdict(float)

        self._lock = threading.Lock()

    def check_and_record(
        self,
        caller_id: str = "global",
        estimated_cost_usd: float = 0.0,
    ) -> None:
        """Check limits before allowing an AI request."""

        if not self.config.enabled:
            return

        now = time.monotonic()
        today = date.today().isoformat()
        cutoff = now - self.config.window_seconds

        estimated_cost = max(
            0.0,
            float(estimated_cost_usd),
        )

        with self._lock:
            request_times = self._requests[caller_id]

            while (
                request_times
                and request_times[0] <= cutoff
            ):
                request_times.popleft()

            if len(request_times) >= self.config.requests:
                retry_after = max(
                    1,
                    int(
                        request_times[0]
                        + self.config.window_seconds
                        - now
                    )
                    + 1,
                )

                raise RateLimitExceeded(
                    "Request limit reached. Please wait "
                    f"approximately {retry_after} second(s) "
                    "before trying again."
                )

            daily_key = (
                caller_id,
                today,
            )

            if (
                self._daily_counts[daily_key]
                >= self.config.daily_request_limit
            ):
                raise DailyBudgetExceeded(
                    "The daily AI request limit has been "
                    "reached. Please contact the system "
                    "administrator or try again tomorrow."
                )

            current_cost = self._daily_costs[daily_key]

            projected_cost = (
                current_cost
                + estimated_cost
            )

            if (
                self.config.daily_budget_usd > 0
                and projected_cost
                > self.config.daily_budget_usd
            ):
                raise DailyBudgetExceeded(
                    "The estimated cost of this AI request "
                    "would exceed the daily budget of "
                    f"${self.config.daily_budget_usd:.2f}. "
                    "Please select the local Ollama provider "
                    "or try again tomorrow."
                )

            request_times.append(now)
            self._daily_counts[daily_key] += 1

    def record_cost(
        self,
        caller_id: str,
        cost_usd: float,
    ) -> None:
        """Record provider cost after a successful request."""

        if not self.config.enabled:
            return

        today = date.today().isoformat()

        daily_key = (
            caller_id,
            today,
        )

        with self._lock:
            self._daily_costs[daily_key] += max(
                0.0,
                float(cost_usd),
            )

    def snapshot(
        self,
        caller_id: str = "global",
    ) -> dict[str, int | float | bool]:
        """Return current usage and cost information."""

        today = date.today().isoformat()

        daily_key = (
            caller_id,
            today,
        )

        with self._lock:
            return {
                "enabled": self.config.enabled,
                "window_request_limit": (
                    self.config.requests
                ),
                "window_seconds": (
                    self.config.window_seconds
                ),
                "daily_request_limit": (
                    self.config.daily_request_limit
                ),
                "daily_requests_used": (
                    self._daily_counts[daily_key]
                ),
                "daily_budget_usd": round(
                    self.config.daily_budget_usd,
                    6,
                ),
                "daily_cost_used_usd": round(
                    self._daily_costs[daily_key],
                    6,
                ),
            }


_DEFAULT_GOVERNOR = UsageGovernor()


def _content_to_text(value: Any) -> str:
    """Convert LangChain inputs and outputs into text."""

    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        return " ".join(
            _content_to_text(item)
            for item in value.values()
        )

    if isinstance(value, (list, tuple)):
        return " ".join(
            _content_to_text(item)
            for item in value
        )

    content = getattr(
        value,
        "content",
        None,
    )

    if content is not None:
        return _content_to_text(content)

    return str(value)


def _estimate_tokens(value: Any) -> int:
    """Estimate tokens using four characters per token."""

    text = _content_to_text(value)

    if not text:
        return 0

    return max(
        1,
        math.ceil(len(text) / 4),
    )


def _extract_token_usage(
    response: Any,
) -> tuple[int, int]:
    """Read LangChain or provider token metadata."""

    usage = getattr(
        response,
        "usage_metadata",
        None,
    )

    if isinstance(usage, dict):
        input_tokens = int(
            usage.get("input_tokens")
            or usage.get("prompt_tokens")
            or 0
        )

        output_tokens = int(
            usage.get("output_tokens")
            or usage.get("completion_tokens")
            or 0
        )

        if input_tokens or output_tokens:
            return (
                input_tokens,
                output_tokens,
            )

    response_metadata = getattr(
        response,
        "response_metadata",
        None,
    )

    if isinstance(response_metadata, dict):
        token_usage = (
            response_metadata.get("token_usage")
            or response_metadata.get("usage")
            or {}
        )

        if isinstance(token_usage, dict):
            input_tokens = int(
                token_usage.get("input_tokens")
                or token_usage.get("prompt_tokens")
                or 0
            )

            output_tokens = int(
                token_usage.get("output_tokens")
                or token_usage.get(
                    "completion_tokens"
                )
                or 0
            )

            if input_tokens or output_tokens:
                return (
                    input_tokens,
                    output_tokens,
                )

    return 0, 0


class GovernedLLM:
    """Proxy that applies request and cost governance."""

    def __init__(
        self,
        llm: Any,
        caller_id: str = "global",
        governor: UsageGovernor | None = None,
        *,
        provider: str = "unknown",
        input_cost_per_million_usd: float = 0.0,
        output_cost_per_million_usd: float = 0.0,
        max_output_tokens: int = 1024,
    ) -> None:
        self._llm = llm
        self._caller_id = caller_id
        self._governor = (
            governor
            or _DEFAULT_GOVERNOR
        )
        self._provider = provider

        self._input_cost_per_million_usd = max(
            0.0,
            float(input_cost_per_million_usd),
        )

        self._output_cost_per_million_usd = max(
            0.0,
            float(output_cost_per_million_usd),
        )

        self._max_output_tokens = max(
            0,
            int(max_output_tokens),
        )

    def _calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        input_cost = (
            max(0, input_tokens)
            / 1_000_000
            * self._input_cost_per_million_usd
        )

        output_cost = (
            max(0, output_tokens)
            / 1_000_000
            * self._output_cost_per_million_usd
        )

        return input_cost + output_cost

    def _estimated_request_cost(
        self,
        request: Any,
    ) -> float:
        return self._calculate_cost(
            _estimate_tokens(request),
            self._max_output_tokens,
        )

    def _record_response_cost(
        self,
        request: Any,
        response: Any,
    ) -> None:
        input_tokens, output_tokens = (
            _extract_token_usage(response)
        )

        if not input_tokens:
            input_tokens = _estimate_tokens(
                request
            )

        if not output_tokens:
            output_tokens = _estimate_tokens(
                getattr(
                    response,
                    "content",
                    response,
                )
            )

        self._governor.record_cost(
            self._caller_id,
            self._calculate_cost(
                input_tokens,
                output_tokens,
            ),
        )

    def invoke(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        request = (
            args[0]
            if args
            else kwargs.get("input")
        )

        self._governor.check_and_record(
            self._caller_id,
            estimated_cost_usd=(
                self._estimated_request_cost(
                    request
                )
            ),
        )

        response = self._llm.invoke(
            *args,
            **kwargs,
        )

        self._record_response_cost(
            request,
            response,
        )

        return response

    async def ainvoke(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        request = (
            args[0]
            if args
            else kwargs.get("input")
        )

        self._governor.check_and_record(
            self._caller_id,
            estimated_cost_usd=(
                self._estimated_request_cost(
                    request
                )
            ),
        )

        response = await self._llm.ainvoke(
            *args,
            **kwargs,
        )

        self._record_response_cost(
            request,
            response,
        )

        return response

    def __getattr__(
        self,
        name: str,
    ) -> Any:
        return getattr(
            self._llm,
            name,
        )


def apply_governance(
    llm: Any,
    caller_id: str = "global",
    *,
    provider: str = "unknown",
    input_cost_per_million_usd: float = 0.0,
    output_cost_per_million_usd: float = 0.0,
    max_output_tokens: int = 1024,
) -> GovernedLLM:
    """Wrap an LLM with request and cost governance."""

    return GovernedLLM(
        llm,
        caller_id=caller_id,
        provider=provider,
        input_cost_per_million_usd=(
            input_cost_per_million_usd
        ),
        output_cost_per_million_usd=(
            output_cost_per_million_usd
        ),
        max_output_tokens=max_output_tokens,
    )


def get_usage_snapshot(
    caller_id: str = "global",
) -> dict[str, int | float | bool]:
    """Return usage and cost information for one caller."""

    return _DEFAULT_GOVERNOR.snapshot(
        caller_id
    )