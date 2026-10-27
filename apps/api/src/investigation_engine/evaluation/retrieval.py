"""Measures retrieval quality on HotpotQA questions and compares search configurations.

For each question the gold documents are its two supporting paragraphs. Dense and BM25
candidates are fetched once per question; every configuration (dense alone, BM25 alone,
RRF with various k and weights, RRF re-ranked by a cross-encoder) is then ranked from those
same candidates, so the comparison is fair and needs no extra searches.

Run from apps/api against the loaded corpus:
    uv run python -m investigation_engine.evaluation.retrieval --questions 200 --output FILE
"""

import argparse
import asyncio
import hashlib
import json
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import pyarrow.parquet as parquet
import structlog

from investigation_engine.core.config import Settings, get_settings
from investigation_engine.core.logging import configure_logging
from investigation_engine.datasets.hotpotqa import document_id, download
from investigation_engine.evaluation.metrics import recall_at_k, reciprocal_rank, unique_in_order
from investigation_engine.retrieval.embeddings import Embedder
from investigation_engine.retrieval.fusion import weighted_rrf
from investigation_engine.retrieval.reranking import CrossEncoderReranker, Reranker, rerank
from investigation_engine.retrieval.vector_store import ScoredChunk, VectorStore

log = structlog.get_logger()

CANDIDATES = 40
# Fused candidates a reranker reads, as in the app (`RERANK_CANDIDATES`).
RERANK_CANDIDATES = 20


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    type: str  # HotpotQA's "bridge" or "comparison"
    gold_document_ids: frozenset[str]


@dataclass(frozen=True)
class Config:
    name: str
    mode: str  # "dense", "sparse" or "hybrid"
    rrf_k: int = 60
    dense_weight: float = 1.0
    sparse_weight: float = 1.0
    rerank_model: str | None = None  # re-rank the fused candidates with this cross-encoder


CONFIGS = [
    Config("dense", "dense"),
    Config("sparse (BM25)", "sparse"),
    Config("hybrid RRF k=60 (paper)", "hybrid", rrf_k=60),
    Config("hybrid RRF k=60, BM25 x0.5", "hybrid", rrf_k=60, sparse_weight=0.5),
    Config("hybrid RRF k=10", "hybrid", rrf_k=10),
    Config("hybrid RRF k=10, BM25 x0.5", "hybrid", rrf_k=10, sparse_weight=0.5),
    Config(
        "hybrid RRF k=10 + MiniLM-L-6 reranker",
        "hybrid",
        rrf_k=10,
        rerank_model="Xenova/ms-marco-MiniLM-L-6-v2",
    ),
    Config(
        "hybrid RRF k=10 + MiniLM-L-12 reranker",
        "hybrid",
        rrf_k=10,
        rerank_model="Xenova/ms-marco-MiniLM-L-12-v2",
    ),
]


def load_questions(path: Path, count: int) -> list[Question]:
    """A fixed sample: the first `count` questions ordered by SHA-256 of their id."""
    table = parquet.read_table(path, columns=["id", "question", "type", "supporting_facts"])
    questions = [
        Question(
            id=row["id"],
            text=row["question"],
            type=row["type"],
            gold_document_ids=frozenset(
                document_id(title) for title in row["supporting_facts"]["title"]
            ),
        )
        for row in table.to_pylist()
    ]
    questions.sort(key=lambda question: hashlib.sha256(question.id.encode()).hexdigest())
    return questions[:count]


def rank_documents(
    config: Config,
    dense: list[ScoredChunk],
    sparse: list[ScoredChunk],
    query: str = "",
    reranker: Reranker | None = None,
) -> list[str]:
    """Document ids in the order the configuration ranks them. A reranker reorders the top
    fused candidates and drops the rest, as the app does."""
    if config.mode == "dense":
        chunks = dense
    elif config.mode == "sparse":
        chunks = sparse
    else:
        by_point = {hit.point_id: hit for hit in [*dense, *sparse]}
        fused = weighted_rrf(
            [[hit.point_id for hit in dense], [hit.point_id for hit in sparse]],
            weights=[config.dense_weight, config.sparse_weight],
            k=config.rrf_k,
        )
        chunks = [by_point[point_id] for point_id, _ in fused]
        if reranker is not None:
            candidates = [chunk.record for chunk in chunks[:RERANK_CANDIDATES]]
            reranked = rerank(query, candidates, reranker)
            return unique_in_order(record.document_id for record, _ in reranked)
    return unique_in_order(chunk.record.document_id for chunk in chunks)


async def evaluate(settings: Settings, question_count: int) -> dict[str, dict[str, float]]:
    questions = load_questions(download(), question_count)
    embedder = Embedder(settings.embedding_model, settings.embedding_query_prefix)
    store = VectorStore.from_settings(settings)

    rerankers = {
        config.rerank_model: CrossEncoderReranker(config.rerank_model)
        for config in CONFIGS
        if config.rerank_model
    }
    per_config: dict[str, dict[str, list[float]]] = {
        config.name: {"recall@2": [], "recall@5": [], "recall@10": [], "mrr": [], "ms": []}
        for config in CONFIGS
    }
    for number, question in enumerate(questions, start=1):
        embedding = embedder.embed_query(question.text)
        dense, sparse = await asyncio.gather(
            store.search_dense(embedding.dense, CANDIDATES),
            store.search_sparse(embedding.sparse, CANDIDATES),
        )
        for config in CONFIGS:
            reranker = rerankers[config.rerank_model] if config.rerank_model else None
            started = time.perf_counter()
            ranked = rank_documents(config, dense, sparse, question.text, reranker)
            scores = per_config[config.name]
            # Ranking time only: the searches are shared by every configuration.
            scores["ms"].append((time.perf_counter() - started) * 1000)
            for k in (2, 5, 10):
                scores[f"recall@{k}"].append(recall_at_k(ranked, question.gold_document_ids, k))
            scores["mrr"].append(reciprocal_rank(ranked, question.gold_document_ids))
        if number % 50 == 0:
            log.info("evaluation_progress", done=number, total=len(questions))
    await store.close()

    return {
        name: {metric: round(statistics.mean(values), 3) for metric, values in scores.items()}
        for name, scores in per_config.items()
    }


def to_markdown(results: dict[str, dict[str, float]], question_count: int) -> str:
    lines = [
        f"Retrieval on {question_count} HotpotQA dev questions (2 gold documents each)",
        "",
        "| Configuration | Recall@2 | Recall@5 | Recall@10 | MRR | Ranking ms |",
        "|---|---|---|---|---|---|",
    ]
    for name, scores in results.items():
        lines.append(
            f"| {name} | {scores['recall@2']:.3f} | {scores['recall@5']:.3f} "
            f"| {scores['recall@10']:.3f} | {scores['mrr']:.3f} | {scores['ms']:.0f} |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate retrieval on HotpotQA.")
    parser.add_argument("--questions", type=int, default=200)
    parser.add_argument("--output", type=Path, required=True, help="where to write the JSON")
    arguments = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level, json=False)
    results = asyncio.run(evaluate(settings, arguments.questions))

    report = {
        "questions": arguments.questions,
        "candidates_per_retriever": CANDIDATES,
        "configs": [asdict(config) for config in CONFIGS],
        "results": results,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2) + "\n")
    print(to_markdown(results, arguments.questions))


if __name__ == "__main__":
    main()
