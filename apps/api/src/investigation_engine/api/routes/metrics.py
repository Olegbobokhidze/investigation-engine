from fastapi import APIRouter

from investigation_engine.api.dependencies import MetricsDependency
from investigation_engine.api.schemas.metrics import MetricsResponse

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def get_metrics(metrics: MetricsDependency) -> MetricsResponse:
    """Requests per route and investigations since the API started; no client addresses."""
    return MetricsResponse.model_validate(metrics.snapshot())
