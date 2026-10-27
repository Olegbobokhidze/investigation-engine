# ADR-0012: Stream an investigation's steps as Server-Sent Events

**Status:** accepted · 2026-10-27

## Context

An investigation takes about 20 seconds (median; p95 34 s), almost all of it LLM calls. The
UI showed a spinner for that whole time, although the agent already records each step it
takes (plan, each search, each document opened, verification).

## Decision

`POST /investigations/stream` runs the same agent and sends a `step` event the moment each
step is taken, then one `result` event with the body `POST /investigations` returns, or one
`error` event with the usual error envelope
(`apps/api/src/investigation_engine/api/routes/investigations.py`). The agent reports steps
through an `on_step` callback; the route puts them on a queue and writes them out. If the
client disconnects, the investigation task is cancelled, so it stops spending LLM credit.
The web app reads the stream with `fetch` and shows the steps live
(`apps/web/src/shared/api/serverSentEvents.ts`).

## Alternatives considered

- **Stream the answer's tokens:** the answer arrives as a tool call's JSON arguments and is
  checked for citations before anyone may see it; streaming it would show text that the
  check might still reject.
- **WebSockets:** two-way, which this doesn't need, and harder to proxy and test than one
  HTTP response.
- **`EventSource`:** the browser API only sends `GET`, and the question belongs in a `POST`
  body.
- **Polling a job id:** needs job state on the server; one instance with in-memory state
  would lose it on restart.

## Evidence

`apps/api/tests/api/test_investigations.py` (steps then result; a provider failure as an
`error` event), `apps/api/tests/investigation/test_agent.py` (every step is reported, in
order), `apps/web/src/shared/api/serverSentEvents.test.ts` (events split across network
chunks). Checked against the running API: the steps arrived 13 seconds before the result.

## Consequences

Once the stream starts the HTTP status is 200, so a failure is an event, not a status code;
errors before the stream starts (validation, rate limit) are still normal error responses.
Caddy passes events through unbuffered.
