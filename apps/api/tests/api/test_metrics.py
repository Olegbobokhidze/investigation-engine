import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def test_metrics_count_requests_by_route_template(client: TestClient) -> None:
    client.get("/health")
    client.delete("/documents/doc_missing")
    client.delete("/documents/doc_other")

    response = client.get("/metrics")

    assert response.status_code == 200
    routes = {(route["method"], route["route"]): route for route in response.json()["routes"]}
    assert routes[("GET", "/health")]["requests"] == 1
    deletes = routes[("DELETE", "/documents/{document_id}")]
    assert (deletes["requests"], deletes["clientErrors"]) == (2, 2)
    assert deletes["p95Ms"] is not None


def test_metrics_group_requests_that_match_no_route(client: TestClient) -> None:
    client.get("/no-such-page")

    routes = client.get("/metrics").json()["routes"]

    assert {"method": "GET", "route": "unmatched"}.items() <= routes[0].items()


def test_metrics_start_with_no_investigations(client: TestClient) -> None:
    investigations = client.get("/metrics").json()["investigations"]

    assert investigations["completed"] == 0
    assert investigations["cacheHits"] == 0
