# Load test: production API

`make load-test` · raw numbers in [`load-test.json`](load-test.json) · run on 27 October 2026
from Tbilisi against the live API (EC2 t3.small in Stockholm, one uvicorn worker behind
Caddy; Postgres on Neon's free tier in Frankfurt).

## Setup

- **Endpoints:** `GET /health` (the app and Caddy only) and
  `GET /documents?search=incident&page=1&pageSize=20` (a title search over 66,593 rows plus a
  count, in Postgres).
- **Load:** 200 requests per endpoint at 1, 10 and 25 concurrent clients
  (`apps/api/src/investigation_engine/evaluation/load.py`).
- **Not load-tested:** `POST /investigations`. It is capped at 40 a day and every call spends
  LLM credit; its latency comes from the 48 recorded evaluation answers instead.

## Results

| Endpoint | Concurrency | Requests | Errors | Requests/s | p50 (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|---|---|---|---|
| health | 1 | 200 | 0 | 10.6 | 94 | 95 | 98 |
| health | 10 | 200 | 0 | 89.8 | 96 | 122 | 336 |
| health | 25 | 200 | 0 | 74.6 | 320 | 389 | 396 |
| documents search | 1 | 200 | 0 | 3.0 | 307 | 369 | 434 |
| documents search | 10 | 200 | 0 | 17.9 | 536 | 763 | 1,056 |
| documents search | 25 | 200 | 1 | 4.6 | 1,180 | 6,208 | 7,061 |

Investigations, from the evaluation records ([report, section 6](../evaluation-report.md#6-answers)):

| Configuration | p50 (s) | p95 (s) | max (s) |
|---|---|---|---|
| agent | 21.2 | 34.0 | 84.7 |
| single-shot | 7.1 | 12.3 | 18.3 |

## Findings

1. **The network sets the floor.** `/health` takes 94 ms with one client: the round trip from
   Tbilisi to Stockholm and TLS, not the app.
2. **The API process scales to about 90 requests per second** on `/health` at 10 clients; at
   25 the single uvicorn worker queues requests and p50 rises to 320 ms.
3. **The document search is the bottleneck.** `ILIKE '%incident%'` can't use an index, so
   every request scans all 66,593 titles and counts them, on Neon's smallest compute, from
   another country. At 25 clients throughput drops to 4.6 requests per second, p95 reaches
   6 s and one request failed. With 25 clients and a pool of 15 connections (5 + 10
   overflow), some requests also wait for a connection; this run doesn't separate the two.
4. **An investigation is dominated by the LLM.** The agent's 21 s median is 3.1 LLM calls
   with reasoning-model output; single-shot, with one search and one call, takes 7 s.

## What would change it

- A trigram index (`pg_trgm`, GIN on `title`) would turn the title scan into an index lookup;
  the count could be capped or estimated for broad searches.
- Done since: the web app skips a search request when a shorter search inside it already
  found nothing, since a substring match can't find more with more characters
  (`apps/web/src/features/documents/api.ts`); this removes requests, not the scan.
- More uvicorn workers would raise `/health`-style throughput, but each worker loads its own
  copy of the embedding models (about 500 MB), so a 2 GB host fits two.
- Investigations: streaming the steps to the UI would change perceived latency, not the
  total; fewer turns or a non-reasoning model would change the total.

These are not needed for a demo with a daily cap of 40 investigations; they are what the
numbers point at for more traffic.
