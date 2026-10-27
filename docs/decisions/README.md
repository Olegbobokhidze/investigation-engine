# Design decisions

The major decisions behind Investigation Engine, one file each: the context, what was
decided, the alternatives, and the **evidence**: a measurement, a test or a constraint
anyone can check. Small choices live in code comments instead.

A decision is never edited to say something else: a new ADR supersedes it, and the old one
says so in its status. `make docs-check` fails if any document names an ADR that doesn't
exist.

| ADR | Decision | Status | Evidence |
|---|---|---|---|
| [0001](0001-modular-monolith.md) | One modular monolith with ports for external services | accepted | test doubles for every port |
| [0002](0002-postgres-and-qdrant.md) | Postgres is the source of truth, Qdrant the search index | accepted | document API tests |
| [0003](0003-hybrid-search-rrf.md) | Hybrid search fused with weighted RRF, k=10 | accepted | retrieval evaluation, 200 questions |
| [0004](0004-structured-chunking.md) | Structure-aware chunking, 200 words | accepted | chunking evaluation |
| [0005](0005-agent-loop.md) | Plan, then a bounded tool-calling loop | accepted | 0.79 vs 0.65 correct, 48 questions |
| [0006](0006-verified-citations.md) | Citations checked in code; none valid → abstain | accepted | citation tests and metrics |
| [0007](0007-llm-provider.md) | OpenAI-compatible client on Groq, with a fallback model | partly superseded by 0010 | LLM client tests |
| [0008](0008-deployment.md) | API on EC2 behind Caddy, web on Vercel | accepted | live health check |
| [0009](0009-answer-cross-check.md) | Cross-check answers against other sources | rejected | more false conflicts, same recall |
| [0010](0010-azure-gpt-5-mini.md) | Agent on gpt-5-mini (Azure), judge stays on Groq | accepted | provider switch with no code change |
