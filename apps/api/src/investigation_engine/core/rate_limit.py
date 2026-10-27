"""Daily caps on investigations, so one visitor (or many) can't use up the LLM quota.

Counts live in memory: the API runs as a single instance, and a restart resetting the
counts is acceptable for a demo. Several instances would need a shared store (Redis).
"""

from collections import Counter
from collections.abc import Callable
from datetime import UTC, date, datetime

from investigation_engine.core.errors import RateLimitedError


def _today() -> date:
    return datetime.now(UTC).date()


class DailyQuota:
    def __init__(self, per_client: int, total: int, today: Callable[[], date] = _today) -> None:
        """`today` is for tests; days are UTC days."""
        self._per_client = per_client
        self._total = total
        self._today = today
        self._day = today()
        self._counts: Counter[str] = Counter()

    def take(self, client: str) -> None:
        """Counts one use by `client`; raises `RateLimitedError` once a cap is reached."""
        if self._today() != self._day:
            self._day, self._counts = self._today(), Counter()
        if self._counts[client] >= self._per_client:
            raise RateLimitedError(
                f"You've reached today's limit of {self._per_client} investigations. "
                "Please try again tomorrow."
            )
        if self._counts.total() >= self._total:
            raise RateLimitedError(
                "The demo has reached today's investigation limit. Please try again tomorrow."
            )
        self._counts[client] += 1
