"""Live metrics served by `GET /metrics`: requests per route and investigations.

In memory, like the daily quota and the answer cache: the API runs as one instance, and the
numbers count from the last restart. Latency percentiles come from a window of the most
recent requests per route, so memory stays bounded however long the process runs. With
several instances or long-term history these would be exported to Prometheus or CloudWatch
instead (docs/decisions/0014-metrics-endpoint.md).
"""

from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from investigation_engine.core.percentiles import percentile

# Recent latencies kept per route (and for investigations) for the percentiles.
LATENCY_WINDOW = 1000


@dataclass(frozen=True)
class RouteMetrics:
    method: str
    route: str
    requests: int
    client_errors: int
    server_errors: int
    p50_ms: float | None
    p95_ms: float | None


@dataclass(frozen=True)
class InvestigationMetrics:
    # Investigations the agent ran; cache hits and failures are counted on their own.
    completed: int
    answered: int
    abstained: int
    failed: int
    cache_hits: int
    llm_calls: int
    total_tokens: int
    p50_s: float | None
    p95_s: float | None


@dataclass(frozen=True)
class MetricsSnapshot:
    started_at: datetime
    uptime_s: int
    routes: list[RouteMetrics]
    investigations: InvestigationMetrics


@dataclass
class _RouteCounts:
    requests: int = 0
    client_errors: int = 0
    server_errors: int = 0
    latencies_ms: deque[float] = field(default_factory=lambda: deque(maxlen=LATENCY_WINDOW))


def _now() -> datetime:
    return datetime.now(UTC)


class Metrics:
    def __init__(self, now: Callable[[], datetime] = _now) -> None:
        """`now` is for tests."""
        self._now = now
        self._started_at = now()
        self._routes: defaultdict[tuple[str, str], _RouteCounts] = defaultdict(_RouteCounts)
        self._answered = 0
        self._abstained = 0
        self._failed = 0
        self._cache_hits = 0
        self._llm_calls = 0
        self._total_tokens = 0
        self._investigation_s: deque[float] = deque(maxlen=LATENCY_WINDOW)

    def record_request(self, method: str, route: str, status_code: int, duration_ms: float) -> None:
        counts = self._routes[(method, route)]
        counts.requests += 1
        if 400 <= status_code < 500:
            counts.client_errors += 1
        elif status_code >= 500:
            counts.server_errors += 1
        counts.latencies_ms.append(duration_ms)

    def record_investigation(
        self, status: str, llm_calls: int, total_tokens: int, duration_s: float
    ) -> None:
        if status == "answered":
            self._answered += 1
        else:
            self._abstained += 1
        self._llm_calls += llm_calls
        self._total_tokens += total_tokens
        self._investigation_s.append(duration_s)

    def record_failed_investigation(self) -> None:
        self._failed += 1

    def record_cache_hit(self) -> None:
        self._cache_hits += 1

    def snapshot(self) -> MetricsSnapshot:
        routes = [
            RouteMetrics(
                method=method,
                route=route,
                requests=counts.requests,
                client_errors=counts.client_errors,
                server_errors=counts.server_errors,
                p50_ms=_rounded_percentile(counts.latencies_ms, 0.50),
                p95_ms=_rounded_percentile(counts.latencies_ms, 0.95),
            )
            for (method, route), counts in sorted(self._routes.items())
        ]
        investigations = InvestigationMetrics(
            completed=self._answered + self._abstained,
            answered=self._answered,
            abstained=self._abstained,
            failed=self._failed,
            cache_hits=self._cache_hits,
            llm_calls=self._llm_calls,
            total_tokens=self._total_tokens,
            p50_s=_rounded_percentile(self._investigation_s, 0.50),
            p95_s=_rounded_percentile(self._investigation_s, 0.95),
        )
        return MetricsSnapshot(
            started_at=self._started_at,
            uptime_s=int((self._now() - self._started_at).total_seconds()),
            routes=routes,
            investigations=investigations,
        )


def _rounded_percentile(values: deque[float], share: float) -> float | None:
    return round(percentile(values, share), 1) if values else None
