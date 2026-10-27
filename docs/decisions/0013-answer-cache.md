# ADR-0013: Cache answers in memory, cleared on every document change

**Status:** accepted · 2026-10-27

## Context

An investigation costs about 7,000 tokens and 21 seconds (median), and the demo allows 40 a
day. Repeated questions are common: the assignment's example question, the questions in
the README, a reviewer asking again after reading the answer. Answering each of them again
spends the daily cap and the LLM credit on a result we already have.

## Decision

`InMemoryAnswerCache` (`apps/api/src/investigation_engine/investigation/cache.py`) keeps
recent answers by question. Questions that differ only in case, spacing or the closing
question mark share an entry. Both investigation routes check it first
(`apps/api/src/investigation_engine/api/routes/investigations.py`):

- **A hit** returns the stored answer with a first step, "Reused a recent answer", so the
  user can see it wasn't investigated again. It costs no LLM call and no daily quota; the
  stream sends the stored steps and the result at once.
- **A miss** takes the quota, runs the agent and stores the result. Failed or cancelled
  investigations are not stored.

**Invalidation.** An answer is only as current as the documents behind it, so uploading,
replacing or deleting a document clears the whole cache
(`apps/api/src/investigation_engine/api/routes/documents.py`). Clearing everything is
simpler and safer than tracking which answers used which document: a new document can
change an answer that never cited it, for example an abstention. Entries also expire after
24 hours (`ANSWER_CACHE_TTL_S`), which bounds changes the API can't see: the dataset
scripts index outside it. The cache holds at most 500 entries (`ANSWER_CACHE_SIZE`) and
drops the least recently used.

## Alternatives considered

- **Redis:** shared between instances and kept across deploys. This API runs as one
  instance, so the sharing buys nothing yet, and it would add a service to run, secure and
  test. The routes use the `AnswerCache` protocol (`get`, `put`, `clear`), so a Redis
  implementation is one new class; the daily quota makes the same trade-off
  (`apps/api/src/investigation_engine/core/rate_limit.py`).
- **Semantic cache** (match questions by embedding similarity): two questions can be close
  in meaning and still need different answers ("before" against "after" a change). A wrong
  hit returns a confident wrong answer, while a miss only costs one more investigation.
- **Cache search results or embeddings:** a search takes milliseconds; the LLM is 99% of
  the time and all of the cost.
- **Invalidate per document:** needs the set of documents each answer depended on,
  including ones it searched and didn't cite; more state for a rare event.

## Evidence

`apps/api/tests/investigation/test_cache.py` (key normalization, expiry, least recently
used eviction, clear), `apps/api/tests/api/test_investigations.py` (a repeated question is
answered without an LLM call and without quota; an upload makes the next answer fresh; the
stream sends a cached answer). Cache hits are counted in `GET /metrics` (ADR-0014).

## Consequences

A deploy or restart empties the cache, like the daily counts. Two visitors asking the same
new question at the same moment both run the agent; with one instance and 40 questions a
day that is not worth a lock.
