# Requirements

Every requirement of the assignment, where it is implemented, what tests it and what
measures it. `make docs-check` (run in CI) fails if a path, ADR or make target named in this
file stops existing. Paths below are relative to `apps/api/src/investigation_engine/`
unless they start with `apps/`, `docs/` or `.github/`.

## Data ingestion

| Requirement | Implementation | Tests | Evidence |
|---|---|---|---|
| At least 3 file formats | PDF, DOCX, Markdown, TXT: `ingestion/loaders.py` | `apps/api/tests/ingestion/test_loaders.py` | Northwind corpus has all four |
| Metadata extraction | title, author, page count, file type, origin: `ingestion/loaders.py`, `documents/models.py` | `apps/api/tests/ingestion/test_loaders.py` | |
| Chunking, 2+ strategies compared | fixed-size and structure-aware: `ingestion/chunking.py` | `apps/api/tests/ingestion/test_chunking.py` | [`docs/evaluation/chunking-northwind.md`](evaluation/chunking-northwind.md), [ADR-0004](decisions/0004-structured-chunking.md) |
| Deduplication | SHA-256 of normalized text, unique in Postgres: `ingestion/normalization.py`, `documents/service.py` | `apps/api/tests/api/test_documents.py` | |
| Add, update, delete documents | `api/routes/documents.py`, `documents/service.py` | `apps/api/tests/api/test_documents.py` | |

## Retrieval

| Requirement | Implementation | Tests | Evidence |
|---|---|---|---|
| Vector database and embeddings | Qdrant, bge-small dense + BM25 sparse: `retrieval/vector_store.py`, `retrieval/embeddings.py` | `apps/api/tests/retrieval/test_vector_store.py`, `apps/api/tests/retrieval/test_embeddings.py` | [ADR-0002](decisions/0002-postgres-and-qdrant.md) |
| Hybrid search | `retrieval/search.py` | `apps/api/tests/retrieval/test_search.py` | [`docs/evaluation/retrieval-hotpotqa.md`](evaluation/retrieval-hotpotqa.md) |
| Own ranking or fusion algorithm | weighted Reciprocal Rank Fusion: `retrieval/fusion.py` | `apps/api/tests/retrieval/test_fusion.py` | [ADR-0003](decisions/0003-hybrid-search-rrf.md) |

## LLM reasoning

| Requirement | Implementation | Tests | Evidence |
|---|---|---|---|
| Multi-step decomposition | planner and tool loop: `investigation/agent.py` | `apps/api/tests/investigation/test_agent.py` | agent vs single-shot in [`docs/evaluation-report.md`](evaluation-report.md), [ADR-0005](decisions/0005-agent-loop.md) |
| Citations | `[n]` checked against shown passages: `investigation/citations.py` | `apps/api/tests/investigation/test_citations.py` | citation precision and recall, [ADR-0006](decisions/0006-verified-citations.md) |
| Contradiction detection | prompt rule and conflicts that must cite both sides: `investigation/prompts.py`, `investigation/citations.py`; an optional cross-check, measured and left off, in `investigation/agent.py` | `apps/api/tests/investigation/test_agent.py` | contradiction recall 0.67 vs 0.17 single-shot, [ADR-0009](decisions/0009-answer-cross-check.md) |
| Abstention | `insufficient_evidence` status; no valid citation → abstain: `investigation/citations.py` | `apps/api/tests/investigation/test_citations.py` | abstention precision and recall |
| LLM error handling | timeouts, retries, backoff, fallback model, 502: `llm/client.py` | `apps/api/tests/llm/test_client.py` | [ADR-0007](decisions/0007-llm-provider.md), [ADR-0010](decisions/0010-azure-gpt-5-mini.md) |
| Tool calling | `plan_investigation`, `search_documents`, `get_document`, `submit_answer`: `llm/tools.py`, `investigation/agent.py` | `apps/api/tests/investigation/test_agent.py` | |

## Evaluation

| Requirement | Implementation | Tests | Evidence |
|---|---|---|---|
| 40+ questions: simple, multi-hop, unanswerable, contradictory | 48 questions: `apps/api/data/eval/northwind-questions.jsonl` + 20 held-out HotpotQA, `evaluation/answers.py` | `apps/api/tests/evaluation/test_chunking.py` (every key fact is in the corpus) | [`docs/evaluation-report.md`](evaluation-report.md), section 2 |
| Recall@K, MRR, answer correctness, citation accuracy | `evaluation/metrics.py`, `evaluation/answers.py` | `apps/api/tests/evaluation/test_metrics.py`, `apps/api/tests/evaluation/test_answers.py` | report sections 4–6 |
| 2+ configurations compared | search (5), chunking (6), answers (agent, single-shot, cross-check), models (gpt-5-mini, gpt-oss-120b) | | `make eval-retrieval`, `make eval-chunking`, `make eval-answers`, `make eval-cross-check`, `make eval-models` |
| Failure analysis | | | report section 7 |

## Application and deployment

| Requirement | Implementation | Evidence |
|---|---|---|
| Python backend | `apps/api` (FastAPI) | `make api-check` in `.github/workflows/api.yml` |
| Functional UI | `apps/web`: `apps/web/src/features/investigations/InvestigationPage.tsx`, `apps/web/src/features/documents/DocumentsPage.tsx` | `make web-check` in `.github/workflows/web.yml` |
| 50k+ documents | 66,581 HotpotQA paragraphs: `datasets/hotpotqa.py` | `make data-hotpotqa` |
| Free-tier deployment with persistence and secrets | `apps/api/deploy/compose.yaml`, `.github/workflows/deploy-api.yml` | [ADR-0008](decisions/0008-deployment.md), README → Deployment |
| Tests and documentation | `apps/api/tests`, `apps/web/src`, `README.md`, `docs/` | CI on every push |

## Deliverables

| Deliverable | Where |
|---|---|
| Repository with history | this repository |
| Live demo | https://investigation-engine-xi.vercel.app |
| README | `README.md` |
| Evaluation report | [`docs/evaluation-report.md`](evaluation-report.md) |
| AI usage report | [`docs/ai-usage.md`](ai-usage.md) |

## Bonus items

| Item | Status |
|---|---|
| Agentic RAG | done: the tool-calling agent ([ADR-0005](decisions/0005-agent-loop.md)) |
| Prompt-injection tests | done: a planted injection in the corpus and 3 questions (report, section 2) |
| Observability | partial: structured JSON logs, and every investigation reports its LLM calls, tokens and steps |
| Model comparison | done: gpt-5-mini vs gpt-oss-120b on 35 questions (report, section 6) |
| Prompt-injection result | 3/3 resisted in every configuration |
| Reranking, caching, streaming, load tests | not done |
