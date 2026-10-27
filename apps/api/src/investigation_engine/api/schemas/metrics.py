"""Response body for GET /metrics. Read by people and monitoring tools, not by the web app."""

from datetime import datetime

from investigation_engine.api.schemas.base import ApiModel


class RouteMetricsResponse(ApiModel):
    method: str
    route: str
    requests: int
    client_errors: int
    server_errors: int
    # For the stream route this is the time until the stream starts, not until it ends.
    p50_ms: float | None
    p95_ms: float | None


class InvestigationMetricsResponse(ApiModel):
    completed: int
    answered: int
    abstained: int
    failed: int
    cache_hits: int
    llm_calls: int
    total_tokens: int
    p50_s: float | None
    p95_s: float | None


class MetricsResponse(ApiModel):
    started_at: datetime
    uptime_s: int
    routes: list[RouteMetricsResponse]
    investigations: InvestigationMetricsResponse
