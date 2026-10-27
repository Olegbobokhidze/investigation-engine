import httpx

from investigation_engine.evaluation.load import measure, to_markdown


async def test_measure_counts_requests_errors_and_latency() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500 if calls % 5 == 0 else 200)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(base_url="http://api", transport=transport) as client:
        result = await measure(client, "health", "/health", concurrency=4, requests=20)

    assert (result.requests, result.errors) == (20, 4)
    assert 0 <= result.p50_ms <= result.p95_ms <= result.p99_ms


async def test_to_markdown_has_one_row_per_result() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200))
    async with httpx.AsyncClient(base_url="http://api", transport=transport) as client:
        result = await measure(client, "health", "/health", concurrency=1, requests=3)

    table = to_markdown([result, result])

    assert table.count("| health | 1 | 3 | 0 |") == 2
