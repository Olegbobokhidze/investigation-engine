"""Load test: many concurrent requests against a running API, with latency percentiles.

It targets the read endpoints (`/health`, `/documents` with a search), which exercise
uvicorn, Caddy and Postgres. `POST /investigations` is left out on purpose: it is capped per
day and every call spends LLM credit; its latency comes from the answer evaluation instead.

Run from apps/api (the API must be up):
    uv run python -m investigation_engine.evaluation.load --base-url URL --output FILE
"""

import argparse
import asyncio
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

from investigation_engine.evaluation.metrics import percentile

# (name, path): the document list is searched, so the request reaches Postgres.
ENDPOINTS = [
    ("health", "/health"),
    ("documents search", "/documents?search=incident&page=1&pageSize=20"),
]
LEVELS = [1, 10, 25]  # concurrent clients
REQUESTS_PER_LEVEL = 200


@dataclass(frozen=True)
class LevelResult:
    endpoint: str
    concurrency: int
    requests: int
    errors: int
    requests_per_second: float
    p50_ms: float
    p95_ms: float
    p99_ms: float


async def measure(
    client: httpx.AsyncClient, endpoint: str, path: str, concurrency: int, requests: int
) -> LevelResult:
    """Sends `requests` GETs to `path`, at most `concurrency` at a time."""
    gate = asyncio.Semaphore(concurrency)
    latencies: list[float] = []
    errors = 0

    async def one() -> None:
        nonlocal errors
        async with gate:
            started = time.perf_counter()
            try:
                response = await client.get(path)
                failed = response.status_code != httpx.codes.OK
            except httpx.HTTPError:
                failed = True
            latencies.append((time.perf_counter() - started) * 1000)
            errors += failed

    started = time.perf_counter()
    await asyncio.gather(*(one() for _ in range(requests)))
    elapsed = time.perf_counter() - started
    return LevelResult(
        endpoint=endpoint,
        concurrency=concurrency,
        requests=requests,
        errors=errors,
        requests_per_second=round(requests / elapsed, 1),
        p50_ms=round(percentile(latencies, 0.50)),
        p95_ms=round(percentile(latencies, 0.95)),
        p99_ms=round(percentile(latencies, 0.99)),
    )


async def run(base_url: str) -> list[LevelResult]:
    results = []
    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
        await client.get("/health")  # warm-up: connection and TLS set up before measuring
        for endpoint, path in ENDPOINTS:
            for concurrency in LEVELS:
                result = await measure(client, endpoint, path, concurrency, REQUESTS_PER_LEVEL)
                results.append(result)
                print(asdict(result), flush=True)
    return results


def to_markdown(results: list[LevelResult]) -> str:
    columns = ["Endpoint", "Concurrency", "Requests", "Errors", "Requests/s", "p50 (ms)"]
    columns += ["p95 (ms)", "p99 (ms)"]
    lines = [f"| {' | '.join(columns)} |", f"|{'---|' * len(columns)}"]
    lines += [
        f"| {r.endpoint} | {r.concurrency} | {r.requests} | {r.errors} | "
        f"{r.requests_per_second} | {r.p50_ms:.0f} | {r.p95_ms:.0f} | {r.p99_ms:.0f} |"
        for r in results
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()

    results = asyncio.run(run(arguments.base_url))
    arguments.output.write_text(json.dumps([asdict(r) for r in results], indent=2) + "\n")
    print(to_markdown(results))


if __name__ == "__main__":
    main()
