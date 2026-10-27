# ADR-0014: Live metrics at `GET /metrics`

**Status:** accepted · 2026-10-27

## Context

Observability was partial: structured JSON logs on the host, and usage numbers inside each
investigation. Nothing answered "is the live API healthy right now": how many requests, how
many errors, how slow, how many investigations and tokens, how often the cache helps. The
LLM provider's own dashboard (Azure) shows the model calls but not our routes, errors or
cache.

## Decision

`Metrics` (`apps/api/src/investigation_engine/core/monitoring.py`) counts, since the process
started:

- **per route**: requests, 4xx and 5xx responses, p50 and p95 latency. A middleware in
  `apps/api/src/investigation_engine/main.py` records every request under its route
  template (`/documents/{document_id}`), so ids don't create a series each; requests that
  match no route share one.
- **investigations**: completed (answered and abstained), failed, cache hits, LLM calls,
  tokens, and p50 and p95 duration of the investigations the agent ran.

`GET /metrics` returns them as JSON
(`apps/api/src/investigation_engine/api/routes/metrics.py`). Percentiles are nearest-rank
over the last 1,000 values per series, so memory stays bounded; they use the same
`percentile` as the evaluation (`apps/api/src/investigation_engine/core/percentiles.py`).
The endpoint holds no client addresses or question text.

## Alternatives considered

- **Prometheus format and a Grafana dashboard:** the standard for a real deployment, but
  it needs a scraper and a dashboard host running somewhere; the free-tier setup has
  neither. The counters map one to one onto Prometheus counters and histograms if one is
  added.
- **CloudWatch** (the API runs on EC2): needs the CloudWatch agent, an IAM role and log
  shipping on the host, and ties the monitoring to AWS while the LLM is on Azure.
- **A hosted APM** (Sentry, Datadog): another account and SDK for a single-instance demo.

## Evidence

`apps/api/tests/core/test_monitoring.py` (counts, errors, percentiles, uptime) and
`apps/api/tests/api/test_metrics.py` (route templates, unmatched requests). On the live
API: `curl https://13-53-155-129.sslip.io/metrics`.

## Consequences

Counts reset on restart and cover one instance; long-term history still comes from the
logs. For the stream route, the latency is the time until the stream starts; how long the
investigation took is in the investigation numbers.
