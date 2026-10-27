# ADR-0001: One modular monolith, with ports for every external service

**Status:** accepted · 2026-10-25

## Context

One developer, four days, one backend to deploy for free. The system still has clearly
separate jobs: ingestion, retrieval, the LLM agent, evaluation. Each external service (LLM,
embedding model, vector store) must be replaceable and fakeable in tests.

## Decision

One FastAPI app (`apps/api`) split into packages by job, with dependencies pointing inward:
HTTP (`api/`) → services (`documents/`, `investigation/`) → adapters (Qdrant, Postgres, LLM).
Services depend on small protocols, not on concrete clients:

| Protocol | Defined in | Real implementation | Test double |
|---|---|---|---|
| `ChatModel` | `apps/api/src/investigation_engine/llm/client.py` | `LlmClient` | `ScriptedLlm` |
| `TextEmbedder` | `apps/api/src/investigation_engine/retrieval/embeddings.py` | `Embedder` (fastembed) | `FakeEmbedder` |
| `Corpus` | `apps/api/src/investigation_engine/investigation/agent.py` | `Retriever` | `FakeCorpus` |
| `Chunker` | `apps/api/src/investigation_engine/ingestion/chunking.py` | fixed, structured | — |

## Alternatives considered

- **Microservices** (ingestion, search, agent as separate services): network calls, several
  deployments and service contracts for no benefit at this size; the free tier hosts one
  process.
- **A framework (LangChain, LlamaIndex):** less code to write, but hides the retry, fusion and
  citation logic this project must explain line by line.

## Evidence

- The test doubles live in `apps/api/tests/conftest.py` and
  `apps/api/tests/investigation/test_agent.py`; the agent's tests run without a network.
- Switching the LLM provider is a setting (`LLM_BASE_URL`, `LLM_MODEL`), not a code change:
  see [ADR-0007](0007-llm-provider.md).

## Consequences

Packages could become services later along the same seams. Until then a slow job (bulk
indexing) runs as a CLI next to the app (`make data-hotpotqa`), not as a worker.
