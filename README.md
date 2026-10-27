# Investigation Engine

Ask a question across 66,593 documents and get an answer assembled from several of them, with
every sentence citing the passage it rests on. When the documents disagree, the answer says so
and names who says what; when they don't hold the answer, the engine abstains instead of
guessing. It is not "chat with a PDF": an agent plans the investigation, searches, follows the
names it finds to the next document, and the server checks every citation before the answer
is shown.

**[Live demo](https://investigation-engine-xi.vercel.app)** ·
[API health](https://13-53-155-129.sslip.io/health) ·
[Evaluation report](docs/evaluation-report.md) ·
[Design decisions](docs/decisions/README.md) ·
[Requirements → code, tests, evidence](docs/requirements.md) ·
[AI usage](docs/ai-usage.md)

## Contents

- [What it does](#what-it-does)
- [Example](#example)
- [Architecture](#architecture)
- [Key decisions](#key-decisions)
- [Results](#results)
- [Quick start](#quick-start)
- [Deployment and cost](#deployment-and-cost)
- [Limitations](#limitations)
- [Working with AI agents](#working-with-ai-agents)
- [Documentation map](#documentation-map)

## What it does

| | |
|---|---|
| **Corpus** | 66,581 HotpotQA Wikipedia paragraphs + 12 synthetic "Northwind Pay" company documents (incident reports, change logs, runbooks, status page, on-call schedule) in PDF, DOCX, Markdown and TXT, with planted multi-hop chains, contradictions, gaps and a prompt injection |
| **Ingest** | upload, replace and delete through the UI; parse, normalize, dedup by SHA-256, structure-aware chunking, dense + BM25 embeddings; datasets are read-only |
| **Search** | hybrid: dense (bge-small) and BM25 in Qdrant, fused with our weighted Reciprocal Rank Fusion; an optional cross-encoder reranker (measured, off by default) |
| **Answer** | a plan-then-act agent with tool calling (`search_documents`, `get_document`, `submit_answer`), then a citation check in code: answered, conflicting or abstained |
| **UI** | ask a question and watch the agent's steps arrive live; the verified answer is written out with clickable citations, conflicts and sources; browse, search, upload, replace and delete documents |
| **Evaluation** | 48 questions (simple, multi-hop, contradictory, unanswerable, prompt injection); compared: agent vs single-shot, two prompts, two models, a cross-check step, 5 search and 6 chunking configurations |
| **Stack** | FastAPI + Pydantic (Python 3.12, mypy strict) · React 19 + TypeScript · Postgres (Neon) · Qdrant Cloud · gpt-5-mini on Azure · EC2 + Caddy · Vercel |

## Example

The assignment's own example question, asked on the live demo
([full response](docs/evaluation/assignment-example.json)):

> **Which system changes caused the payment processing delays in March, which services were
> affected, and which documents confirm this?**

| Field | Value |
|---|---|
| `status` | `answered` |
| `answer` | "The delays were caused by two system changes: CHG-2294 (checkout-api timeouts reduced to 3s with one retry) and CHG-2291 (payments-db connection pool reduced from 50 to 20) … These changes made checkout-api retry slow fraud-scoring calls, which published duplicate payment events, and the reduced payments-db pool left the database unable to handle the extra round trips; ledger-worker … experienced consumer lag and delayed ledger writes, causing merchant balances to be behind [4][5][2][3][1]. …" |
| `conflicts` | "The sources disagree on CHG-2291 deployment time: 09:05 [1] or 09:40 [2]." · "The sources disagree on the number of delayed payments: 1,840 [1] or about 2,300 [3]." |
| sources | `inc-0412-payment-delays.pdf` (PDF) · `changelog-2024-03.md` (Markdown) · `ledger-worker-postmortem.md` (Markdown) · `status-page-history.txt` (TXT) |
| steps | planned 3 searches → searched → searched again for `CHG-2291 CHG-2294 March payment delays`, the names it had just found → verified 6 citations, 2 conflicts |

Both disagreements are planted in the corpus
([ground truth](docs/evaluation/northwind-ground-truth.md)); the agent found them without
being asked. Try it in the [live demo](https://investigation-engine-xi.vercel.app), or:

```bash
curl -s -X POST https://13-53-155-129.sslip.io/investigations \
  -H 'content-type: application/json' \
  -d '{"question": "Which system changes caused the payment processing delays in March?"}'
```

## Architecture

A modular monolith in layers: HTTP (`api/`) → services → adapters (Qdrant, Postgres, LLM).
Services depend on protocols (`ChatModel`, `TextEmbedder`, `Corpus`, `Chunker`), so a provider
is swapped, or faked in tests, in one place: moving the LLM from Groq to Azure changed three
settings and no code ([ADR-0001](docs/decisions/0001-modular-monolith.md),
[ADR-0010](docs/decisions/0010-azure-gpt-5-mini.md)).

### System

```mermaid
flowchart LR
    user(["Browser"])
    subgraph vercel["Vercel"]
        web["React app<br/>apps/web"]
    end
    subgraph ec2["AWS EC2 t3.small, Stockholm"]
        caddy["Caddy<br/>HTTPS, Let's Encrypt"]
        api["FastAPI<br/>apps/api<br/>embedding models in memory"]
    end
    neon[("Neon Postgres<br/>documents: source of truth")]
    qdrant[("Qdrant Cloud<br/>chunks: dense + BM25 vectors")]
    azure["Azure AI Foundry<br/>gpt-5-mini"]
    gh["GitHub Actions<br/>CI, then deploy"]
    ghcr[("GHCR<br/>API image")]

    user --> web
    user -- "HTTPS /investigations, /documents" --> caddy --> api
    api --> neon
    api --> qdrant
    api --> azure
    gh -- "build and push" --> ghcr
    gh -- "SSH: compose pull and up" --> ec2
    ghcr --> api
```

### Ask flow

`POST /investigations` ([agent.py](apps/api/src/investigation_engine/investigation/agent.py)):
at most 1 planning call + 4 loop turns, the last of which can only submit an answer. The UI
calls `POST /investigations/stream`, which runs the same agent and sends each step as a
Server-Sent Event the moment it is taken, so the 20 seconds of an investigation show progress
instead of a spinner ([investigations.py](apps/api/src/investigation_engine/api/routes/investigations.py)).

```mermaid
sequenceDiagram
    participant U as Browser
    participant R as route + rate limit
    participant A as Investigator (agent.py)
    participant S as Retriever (search.py)
    participant L as gpt-5-mini
    participant C as citations.py
    U->>R: POST /investigations {question}
    R->>A: investigate(question)
    A->>L: plan_investigation (forced)
    L-->>A: 1-4 sub-questions
    A->>S: search each sub-question, in parallel
    S-->>A: numbered passages
    loop at most 4 turns
        A->>L: question, plan, passages, tools
        L-->>A: search_documents, get_document or submit_answer
        A->>S: run the tool
        S-->>A: new passages
    end
    Note over A,L: last turn: only submit_answer, forced
    A->>C: drop citations to unseen passages, no valid citation → abstain
    C-->>A: answered or insufficient_evidence, conflicts
    A-->>U: answer, sources, conflicts, steps, usage
```

Hybrid search, the part written by hand
([search.py](apps/api/src/investigation_engine/retrieval/search.py),
[fusion.py](apps/api/src/investigation_engine/retrieval/fusion.py)):

```mermaid
flowchart LR
    q["query"] --> e["bge-small query vector<br/>+ BM25 sparse vector"]
    e --> dense["dense top 40"]
    e --> bm25["BM25 top 40"]
    dense --> rrf["weighted RRF<br/>k = 10, equal weights"]
    bm25 --> rrf
    rrf --> hits["top-k chunks"]
    rrf -.-> rerank["optional: cross-encoder reranker<br/>MiniLM-L-6 on the top 20, off by default"]
    rerank -.-> hits
```

<details>
<summary>Step by step, with code links</summary>

| Step | What happens | Code |
|---|---|---|
| 1. Rate limit | 20 investigations per client IP and 40 in total per UTC day, else 429 | [rate_limit.py](apps/api/src/investigation_engine/core/rate_limit.py) |
| 2. Plan | a forced `plan_investigation` call splits the question into 1–4 search queries | [agent.py](apps/api/src/investigation_engine/investigation/agent.py), [prompts.py](apps/api/src/investigation_engine/investigation/prompts.py) |
| 3. Search | each sub-question in parallel: dense + BM25 top 40, weighted RRF, 6 passages each (a cross-encoder can re-rank the top 20 when `RERANK_MODEL` is set) | [search.py](apps/api/src/investigation_engine/retrieval/search.py), [fusion.py](apps/api/src/investigation_engine/retrieval/fusion.py), [reranking.py](apps/api/src/investigation_engine/retrieval/reranking.py) |
| 4. Tool loop | the model reads numbered passages and searches again (the next hop), opens a document or submits; an uncited answer is sent back | [agent.py](apps/api/src/investigation_engine/investigation/agent.py), [tools.py](apps/api/src/investigation_engine/llm/tools.py) |
| 5. LLM client | timeouts, retries on 408/429/5xx with capped backoff and `Retry-After`, a fallback model, then 502 | [client.py](apps/api/src/investigation_engine/llm/client.py) |
| 6. Verify | citations to passages the model wasn't shown are removed; no valid citation → abstain; a conflict must cite both sides; sources renumbered 1..n | [citations.py](apps/api/src/investigation_engine/investigation/citations.py) |

</details>

### Ingest flow

`POST /documents` (several files), `PUT /documents/{id}`, `DELETE /documents/{id}`
([service.py](apps/api/src/investigation_engine/documents/service.py)).

```mermaid
flowchart TB
    a["upload: PDF, DOCX, MD, TXT<br/>at most 10 MB"] --> b["load text + metadata<br/>title, author, pages"]
    b --> c["normalize<br/>strip control characters"]
    c --> d{"SHA-256 of<br/>normalized text"}
    d -- "already indexed" --> dup["409 duplicate_document"]
    d -- "new" --> e["structure-aware chunks<br/>headings and paragraphs, 200 words"]
    e --> f["embed title + section + chunk<br/>dense 384-d + BM25"]
    f --> g[("Qdrant: chunks first")]
    g --> h[("Postgres: row committed last")]
```

A document is never listed without its chunks: Qdrant is written first and the Postgres row
committed last, and a failure rolls the row back
([ADR-0002](docs/decisions/0002-postgres-and-qdrant.md)).

<details>
<summary>Module map</summary>

| Module | Responsibility |
|---|---|
| [`api/`](apps/api/src/investigation_engine/api/) | HTTP only: routes, camelCase schemas, dependencies |
| [`core/`](apps/api/src/investigation_engine/core/) | settings, errors (one envelope), logging, database, rate limit |
| [`documents/`](apps/api/src/investigation_engine/documents/) | document CRUD, dedup, read-only datasets |
| [`ingestion/`](apps/api/src/investigation_engine/ingestion/) | loaders, normalization, chunking strategies |
| [`retrieval/`](apps/api/src/investigation_engine/retrieval/) | embeddings, Qdrant store, weighted RRF, hybrid search |
| [`llm/`](apps/api/src/investigation_engine/llm/) | the only LLM calls, typed tools |
| [`investigation/`](apps/api/src/investigation_engine/investigation/) | the agent, prompts, evidence numbering, citation check |
| [`datasets/`](apps/api/src/investigation_engine/datasets/) | HotpotQA and Northwind loaders, bulk indexing |
| [`evaluation/`](apps/api/src/investigation_engine/evaluation/) | retrieval, chunking and answer evaluations |
| [`apps/web/src/features/`](apps/web/src/features/) | investigations and documents pages, hooks, types |

</details>

| Endpoint | |
|---|---|
| `POST /investigations` | `{question}` → answer, cited sources, conflicts, steps; 429 past the daily cap |
| `POST /investigations/stream` | the same, as Server-Sent Events: a `step` event as each step is taken, then `result` or `error`; the UI uses it to show progress |
| `GET /documents?search=&page=&pageSize=` | paginated document list |
| `POST /documents` | multipart `files`: one result per file (indexed, duplicate or failed) |
| `PUT /documents/{id}` | multipart `file`: replace an uploaded document |
| `DELETE /documents/{id}` | delete an uploaded document and its chunks |

## Key decisions

Each decision has an ADR with context, alternatives and the evidence it rests on
([index](docs/decisions/README.md)); `make docs-check` in CI fails if a document names an ADR,
file or make target that doesn't exist.

| Decision | Why | Evidence |
|---|---|---|
| One modular monolith with ports, no RAG framework | every line explainable; providers swapped in one place | [ADR-0001](docs/decisions/0001-modular-monolith.md) |
| Postgres is the source of truth, Qdrant the index | unique hashes and pagination in SQL; dense + BM25 in one store | [ADR-0002](docs/decisions/0002-postgres-and-qdrant.md) |
| Hybrid search with our weighted RRF, k=10 | Recall@10 0.875 vs 0.792 dense, 0.785 BM25; k=10 beat the paper's 60 | [ADR-0003](docs/decisions/0003-hybrid-search-rrf.md) |
| A cross-encoder reranker: **off by default** | retrieval MRR 0.880 → 0.932, but the answers weren't better (0.69 vs 0.79), so the end-to-end result decides | [ADR-0011](docs/decisions/0011-cross-encoder-reranking.md) |
| Steps streamed as Server-Sent Events | 20 s of progress instead of a spinner; the answer is shown only after its citations are checked | [ADR-0012](docs/decisions/0012-streaming-investigation-steps.md) |
| Structure-aware chunks, 200 words | best Recall@3/5 at a third less context | [ADR-0004](docs/decisions/0004-structured-chunking.md) |
| Plan, then a bounded tool loop | beats single-shot on multi-hop and contradictions | [ADR-0005](docs/decisions/0005-agent-loop.md) |
| Citations checked in code | a hallucinated `[7]` never reaches the user | [ADR-0006](docs/decisions/0006-verified-citations.md) |
| A cross-check step: **rejected** | measured: same contradiction recall, more false conflicts | [ADR-0009](docs/decisions/0009-answer-cross-check.md) |
| gpt-5-mini on Azure, judge on Groq | Groq's free quota couldn't finish the evaluation | [ADR-0010](docs/decisions/0010-azure-gpt-5-mini.md) |
| API on EC2 behind Caddy, web on Vercel | the API needs ~500 MB for its models; free tiers were too small | [ADR-0008](docs/decisions/0008-deployment.md) |

## Results

Full method, tables and failure analysis: [docs/evaluation-report.md](docs/evaluation-report.md).

| Metric (48 questions, gpt-5-mini, deployed prompt) | agent | single-shot |
|---|---|---|
| Answer correctness | **0.79** | 0.67 |
| HotpotQA multi-hop (held out from tuning) | **15/20** | 12/20 |
| Contradiction recall | **0.67** | 0.17 |
| Unanswerable: abstained | **8/8** | 7/8 |
| Prompt injection resisted | 3/3 | 3/3 |
| Citation recall (gold documents cited) | **0.88** | 0.82 |
| Tokens / cost per question | 7.0k / ~$0.006 | 2.9k / ~$0.0025 |
| Latency p50 / p95 | 21 s / 34 s | 7 s / 12 s |
| Retrieval Recall@10 / MRR (plain hybrid search) | 0.87 / 0.82 | |

Load test of the live API ([`docs/evaluation/load-test.md`](docs/evaluation/load-test.md)):
`/health` serves about 90 requests/s at 10 clients with p95 122 ms; the document title
search is the bottleneck (p95 763 ms at 10 clients, 6 s at 25).

Also measured: a prompt revision driven by the failure analysis (same correctness, fewer
tokens, shorter abstentions), a cross-encoder reranker (better retrieval, not better answers:
off), an answer cross-check (rejected) and gpt-5-mini against gpt-oss-120b (0.74 against 0.66
on the same prompt).

## Quick start

- **Use it:** open the [live demo](https://investigation-engine-xi.vercel.app), ask a question
  ("Who was the primary on-call engineer when INC-0412 started?"), upload a PDF, DOCX,
  Markdown or TXT file, replace or delete it.
- **Run it locally:** needs [uv](https://docs.astral.sh/uv/), Node.js 22+, pnpm and Docker.

```bash
make services-up    # local Postgres and Qdrant

cp apps/api/.env.example apps/api/.env      # add LLM_API_KEY
make api-install
make api-dev        # http://localhost:8000/health

cp apps/web/.env.example apps/web/.env.local
make web-install
make web-dev        # http://localhost:5173
```

`VITE_API_MOCKING` decides which API calls the web app answers with mock data
([Mock Service Worker](https://mswjs.io)): `enabled` (all, no backend needed),
`investigations` (only investigations) or `disabled` (none).

- **Load the data** into the services in `apps/api/.env` (idempotent; a rerun skips what is
  stored):

```bash
make data-hotpotqa    # 66,581 HotpotQA paragraphs (~45 min on a laptop CPU)
make data-synthetic   # 12 Northwind Pay documents in PDF, DOCX, Markdown and TXT
```

- **Check the code:** `make api-check` (ruff, mypy strict, pytest) and `make web-check`
  (ESLint, Prettier, tsc, Vitest, build), the same as CI. `make help` lists every target.
- **Run the evaluations:**

```bash
make eval-retrieval   # 8 search configurations incl. 2 rerankers, 200 HotpotQA questions (no LLM)
make eval-chunking    # 6 chunking configurations on Northwind (local Qdrant, no LLM)
make eval-answers     # agent vs single-shot, 48 questions (LLM; resumable)
make eval-cross-check # the agent with the answer cross-check, 28 Northwind questions (LLM)
make eval-report      # metrics from the recorded answers (no LLM)
make eval-prompts     # the current prompt vs prompt v1 (no LLM)
make eval-models      # gpt-5-mini vs gpt-oss-120b, same prompt (no LLM)
make eval-reranker    # answers with the reranker on vs off (no LLM)
make load-test        # latency percentiles of the live API's read endpoints
```

## Deployment and cost

| Part | Where | How |
|---|---|---|
| Web | Vercel | builds `apps/web` on every push; a production build without `VITE_API_BASE_URL` fails on purpose |
| API | AWS EC2 t3.small, Stockholm | `.github/workflows/deploy-api.yml`: after CI passes on `main`, build the image, push to GHCR, `docker compose up` over SSH, health check. Caddy serves HTTPS for `<ip-with-dashes>.sslip.io` |
| Data | Neon (Postgres) and Qdrant Cloud, Frankfurt | loaded with the `make data-*` targets |
| LLM | Azure AI Foundry, `gpt-5-mini`, Germany West Central | OpenAI-compatible API; settings only |

**Secrets** live only in `/opt/investigation-engine/.env` on the host (mode 600); GitHub holds
only the host address and an SSH key. One-time host setup: `apps/api/deploy/bootstrap.sh`.

**Free tiers only: nothing was bought.** Every service runs on a free tier or on credit that
came with a free account, without a payment card where the provider allows it.

| Service | Plan | Limit that matters here |
|---|---|---|
| Vercel | Hobby (free) | static hosting for the web app |
| AWS EC2 t3.small | AWS Free plan credits | the instance runs on the account's credits; a 2 GB host fits the API with its embedding models (about 500 MB) |
| Neon Postgres | free tier | compute sleeps when idle and wakes on the next query (the first request after a pause is slower) |
| Qdrant Cloud | free cluster | one small cluster; 68,779 chunk points with dense and BM25 vectors fit |
| Azure AI Foundry | Azure for Students credit (no card) | the daily cap of 40 investigations keeps spend well under a dollar a day |
| Groq | free tier | about 200k tokens per model per day: the local default and the evaluation judge |

**Persistence:** documents and chunks live in Neon and Qdrant Cloud, outside the API host, so
a restart or redeploy of the API loses nothing; only the in-memory rate-limit counts reset.

| Cost | |
|---|---|
| One agent investigation (measured tokens × list price) | ~$0.006 |
| Every answer evaluation run in the report | ~$1.50 |
| EC2 t3.small, per month (AWS credits) | ~$16 |
| Neon, Qdrant Cloud, Vercel | free tiers |

## Limitations

The main ones; the evaluation's own limits are in [section 8 of the report](docs/evaluation-report.md#8-limits-of-this-evaluation).

- **Over-cautious answers.** A third of the agent's abstentions are on questions the corpus
  answers, and it sometimes stops one hop early (report, section 7).
- **Credit-funded LLM.** The demo runs on student Azure credit. So the credit can't be
  drained, the API allows 20 investigations per visitor IP and 40 in total per UTC day
  (counts are in memory, so a restart resets them).
- **No authentication.** Anyone with the URL can upload and delete *uploaded* documents
  (datasets are read-only, 403).
- **PDF paragraphs.** pypdf doesn't keep paragraph breaks inside a page, so a PDF page is
  chunked by sentences.
- **Single instance.** One EC2 host in Stockholm, no replica.

## Working with AI agents

The repository is set up for AI coding agents, and every AI-assisted change is logged in
[`docs/ai-usage.md`](docs/ai-usage.md).

- **`AGENTS.md`** (root, `apps/api`, `apps/web`): scope, commands, conventions, the API
  contract, and the rule that a change contradicting an ADR needs a new one.
- **`.claude/settings.json`**: the agent may run the quality gates; it may not read `.env`
  files or commit and push.
- **`.claude/hooks/format-edited-file.mjs`**: formats every file the agent edits.
- **`.claude/agents/`**: read-only reviewers, `contract-guardian` (backend ↔ frontend ↔ mocks)
  and `convention-reviewer` (conventions, scope, ADRs).
- **`.claude/skills/`**: `/check`, `/add-endpoint`, `/log-ai-usage`.

## Documentation map

| Document | What is in it |
|---|---|
| [docs/evaluation-report.md](docs/evaluation-report.md) | method, metrics, results, failure analysis, limits |
| [docs/decisions/](docs/decisions/README.md) | the design decisions (ADRs), each with its evidence |
| [docs/requirements.md](docs/requirements.md) | every assignment requirement → code, tests, evidence |
| [docs/evaluation/northwind-ground-truth.md](docs/evaluation/northwind-ground-truth.md) | the synthetic corpus: planted facts, chains, conflicts, gaps, injection |
| [docs/evaluation/retrieval-hotpotqa.md](docs/evaluation/retrieval-hotpotqa.md) | search configurations compared |
| [docs/evaluation/chunking-northwind.md](docs/evaluation/chunking-northwind.md) | chunking strategies compared |
| [docs/evaluation/load-test.md](docs/evaluation/load-test.md) | load test of the live API, latency percentiles, bottlenecks |
| [docs/ai-usage.md](docs/ai-usage.md) | how AI tools were used and what the author decided |
| [AGENTS.md](AGENTS.md) | conventions for humans and coding agents |
