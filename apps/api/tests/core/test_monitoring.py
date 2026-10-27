from datetime import UTC, datetime, timedelta

from investigation_engine.core.monitoring import Metrics


def test_metrics_count_requests_and_errors_per_route() -> None:
    metrics = Metrics()
    for duration_ms in (10.0, 20.0, 30.0):
        metrics.record_request("GET", "/documents", 200, duration_ms)
    metrics.record_request("GET", "/documents", 422, 5.0)
    metrics.record_request("POST", "/investigations", 502, 900.0)

    routes = {(route.method, route.route): route for route in metrics.snapshot().routes}

    documents = routes[("GET", "/documents")]
    assert (documents.requests, documents.client_errors, documents.server_errors) == (4, 1, 0)
    assert (documents.p50_ms, documents.p95_ms) == (10.0, 30.0)
    assert routes[("POST", "/investigations")].server_errors == 1


def test_metrics_sum_investigations_and_keep_cache_hits_apart() -> None:
    metrics = Metrics()
    metrics.record_investigation("answered", llm_calls=3, total_tokens=7000, duration_s=20.0)
    metrics.record_investigation(
        "insufficient_evidence", llm_calls=2, total_tokens=4000, duration_s=12.0
    )
    metrics.record_failed_investigation()
    metrics.record_cache_hit()

    investigations = metrics.snapshot().investigations

    assert (investigations.completed, investigations.answered, investigations.abstained) == (
        2,
        1,
        1,
    )
    assert (investigations.failed, investigations.cache_hits) == (1, 1)
    assert (investigations.llm_calls, investigations.total_tokens) == (5, 11000)
    assert (investigations.p50_s, investigations.p95_s) == (12.0, 20.0)


def test_metrics_have_no_percentiles_before_any_request() -> None:
    snapshot = Metrics().snapshot()

    assert snapshot.routes == []
    assert snapshot.investigations.p50_s is None


def test_metrics_report_uptime_since_they_were_created() -> None:
    start = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)
    times = iter([start, start + timedelta(minutes=5)])
    metrics = Metrics(now=lambda: next(times))

    assert metrics.snapshot().uptime_s == 300
