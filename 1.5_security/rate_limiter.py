"""In-memory request-rate and daily-budget controls for LLM calls.

This is intentionally lightweight for the A4 prototype. In a multi-server production
system, the counters should be moved to a shared store such as Redis or Firestore.
"""

from __future__ import annotations

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
    """Raised when the configured daily request budget has been reached."""


def _as_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class GovernanceConfig:
    enabled: bool
    requests: int
    window_seconds: int
    daily_request_limit: int

    @classmethod
    def from_environment(cls) -> "GovernanceConfig":
        return cls(
            enabled=_as_bool(os.getenv("RATE_LIMIT_ENABLED"), True),
            requests=max(1, int(os.getenv("RATE_LIMIT_REQUESTS", "10"))),
            window_seconds=max(1, int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))),
            daily_request_limit=max(1, int(os.getenv("LLM_DAILY_REQUEST_LIMIT", "250"))),
        )


class UsageGovernor:
    def __init__(self, config: GovernanceConfig | None = None) -> None:
        self.config = config or GovernanceConfig.from_environment()
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._daily_counts: dict[tuple[str, str], int] = defaultdict(int)
        self._lock = threading.Lock()

    def check_and_record(self, caller_id: str = "global") -> None:
        if not self.config.enabled:
            return

        now = time.monotonic()
        today = date.today().isoformat()
        cutoff = now - self.config.window_seconds

        with self._lock:
            request_times = self._requests[caller_id]
            while request_times and request_times[0] <= cutoff:
                request_times.popleft()

            if len(request_times) >= self.config.requests:
                retry_after = max(1, int(request_times[0] + self.config.window_seconds - now) + 1)
                raise RateLimitExceeded(
                    "Request limit reached. Please wait "
                    f"approximately {retry_after} second(s) before trying again."
                )

            daily_key = (caller_id, today)
            if self._daily_counts[daily_key] >= self.config.daily_request_limit:
                raise DailyBudgetExceeded(
                    "The daily AI request budget has been reached. "
                    "Please contact the system administrator or try again tomorrow."
                )

            request_times.append(now)
            self._daily_counts[daily_key] += 1

    def snapshot(self, caller_id: str = "global") -> dict[str, int | bool]:
        today = date.today().isoformat()
        with self._lock:
            return {
                "enabled": self.config.enabled,
                "window_request_limit": self.config.requests,
                "window_seconds": self.config.window_seconds,
                "daily_request_limit": self.config.daily_request_limit,
                "daily_requests_used": self._daily_counts[(caller_id, today)],
            }


_DEFAULT_GOVERNOR = UsageGovernor()


class GovernedLLM:
    """Small proxy that applies governance before LangChain LLM calls."""

    def __init__(self, llm: Any, caller_id: str = "global", governor: UsageGovernor | None = None) -> None:
        self._llm = llm
        self._caller_id = caller_id
        self._governor = governor or _DEFAULT_GOVERNOR

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        self._governor.check_and_record(self._caller_id)
        return self._llm.invoke(*args, **kwargs)

    async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
        self._governor.check_and_record(self._caller_id)
        return await self._llm.ainvoke(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._llm, name)


def apply_governance(llm: Any, caller_id: str = "global") -> GovernedLLM:
    return GovernedLLM(llm, caller_id=caller_id)


def get_usage_snapshot(caller_id: str = "global") -> dict[str, int | bool]:
    return _DEFAULT_GOVERNOR.snapshot(caller_id)
