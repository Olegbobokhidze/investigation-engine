"""Compares chunking strategies and sizes on retrieval over the Northwind Pay corpus.

HotpotQA paragraphs are a single chunk at any size, so chunking is measured on the
multi-section Northwind documents, indexed together with HotpotQA distractor paragraphs
so search has something to get wrong. Each configuration is indexed into its own
temporary collection on a local Qdrant (never the cloud one) and searched with the
production hybrid search.

Metrics per configuration, over the answerable Northwind questions:
- document Recall@3 / Recall@5 and MRR: are the right documents found;
- fact recall@5: are the exact facts an answer needs inside the 5 chunks the LLM would
  read; this is what chunking changes most directly;
- context words@5: how much text those 5 chunks cost.

Run from apps/api with `make services-up` running:
    uv run python -m investigation_engine.evaluation.chunking --output FILE
"""

import argparse
import asyncio
import hashlib
import json
import re
import statistics
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

import structlog

from investigation_engine.core.config import ChunkingStrategy, get_settings
from investigation_engine.core.logging import configure_logging
from investigation_engine.datasets import hotpotqa, synthetic
from investigation_engine.datasets.indexing import DatasetDocument
from investigation_engine.datasets.northwind_corpus import DOCUMENTS
from investigation_engine.evaluation.answers import EvalQuestion, load_northwind_questions
from investigation_engine.evaluation.metrics import recall_at_k, reciprocal_rank, unique_in_order
from investigation_engine.ingestion.chunking import create_chunker
from investigation_engine.ingestion.pipeline import chunk_records, embedding_text
from investigation_engine.retrieval.embeddings import Embedder, TextEmbedder
from investigation_engine.retrieval.search import FusionSettings, Retriever
from investigation_engine.retrieval.vector_store import VectorStore

log = structlog.get_logger()

DISTRACTORS = 1000
TOP_K = 5
_BATCH = 64


@dataclass(frozen=True)
class Config:
    strategy: ChunkingStrategy
    max_words: int
    overlap_words: int

    @property
    def name(self) -> str:
        overlap = f", overlap {self.overlap_words}" if self.strategy == "fixed" else ""
        return f"{self.strategy} {self.max_words} words{overlap}"


# Overlap is 20% of the size for the fixed strategy; structured chunks don't overlap.
CONFIGS = [
    Config(strategy, size, size // 5 if strategy == "fixed" else 0)
    for size in (60, 120, 200)
    for strategy in ("fixed", "structured")
]


def _squash(text: str) -> str:
    """Whitespace-insensitive, so a fact split over a PDF line break still matches."""
    return re.sub(r"\s+", " ", text)


def _distractors(chunker_config: Config) -> list[DatasetDocument]:
    paragraphs = hotpotqa.read_paragraphs(hotpotqa.download())
    paragraphs.sort(key=lambda p: hashlib.sha256(p.title.encode()).hexdigest())
    chunker = create_chunker(
        chunker_config.strategy, chunker_config.max_words, chunker_config.overlap_words
    )
    return [hotpotqa.to_dataset_document(p, chunker) for p in paragraphs[:DISTRACTORS]]


async def evaluate(
    config: Config, questions: list[EvalQuestion], embedder: TextEmbedder, qdrant_url: str
) -> dict[str, object]:
    chunker = create_chunker(config.strategy, config.max_words, config.overlap_words)
    northwind = [synthetic.to_dataset_document(document, chunker) for document in DOCUMENTS]
    items = northwind + _distractors(config)

    store = VectorStore(qdrant_url, api_key=None, collection=f"chunking_{uuid.uuid4().hex}")
    try:
        await store.ensure_collection(embedder.dense_size)
        pairs = [
            (record, embedding_text(item.document.title, chunk))
            for item in items
            for record, chunk in zip(
                chunk_records(item.document, item.chunks), item.chunks, strict=True
            )
        ]
        for start in range(0, len(pairs), _BATCH):
            batch = pairs[start : start + _BATCH]
            embeddings = await asyncio.to_thread(
                embedder.embed_passages, [text for _, text in batch]
            )
            await store.upsert([record for record, _ in batch], embeddings)

        retriever = Retriever(
            embedder,
            store,
            FusionSettings(candidates=40, rrf_k=10, dense_weight=1.0, sparse_weight=1.0),
        )
        rows = []
        for question in questions:
            hits = await retriever.search(question.question, limit=TOP_K)
            ranked = unique_in_order(hit.record.document_id for hit in hits)
            gold = set(question.gold_document_ids)
            context = _squash(" ".join(hit.record.text for hit in hits))
            rows.append(
                {
                    "recall_at_3": recall_at_k(ranked, gold, 3),
                    "recall_at_5": recall_at_k(ranked, gold, 5),
                    "mrr": reciprocal_rank(ranked, gold),
                    "fact_recall_at_5": sum(fact in context for fact in question.key_facts)
                    / len(question.key_facts),
                    "context_words_at_5": len(context.split()),
                }
            )
    finally:
        await store.delete_collection()
        await store.close()

    chunk_counts = [len(item.chunks) for item in northwind]
    log.info("chunking_config_evaluated", config=config.name)
    return {
        "config": asdict(config),
        "name": config.name,
        "northwind_chunks": sum(chunk_counts),
        **{key: statistics.mean(float(row[key]) for row in rows) for key in rows[0]},
    }


def check_facts(questions: list[EvalQuestion]) -> None:
    """Every key fact must appear in the corpus, or fact recall would measure a typo."""
    chunker = create_chunker("structured", 10_000, 0)
    corpus = _squash(
        " ".join(synthetic.to_dataset_document(d, chunker).document.text for d in DOCUMENTS)
    )
    missing = [fact for q in questions for fact in q.key_facts if fact not in corpus]
    if missing:
        raise ValueError(f"Key facts not in the corpus: {missing}")


def to_markdown(results: list[dict[str, object]], question_count: int) -> str:
    lines = [
        f"Chunking on {question_count} answerable Northwind questions "
        f"({len(DOCUMENTS)} documents + {DISTRACTORS} HotpotQA distractors, hybrid search)",
        "",
        "| Configuration | Northwind chunks | Recall@3 | Recall@5 | MRR | Fact recall@5 "
        "| Context words@5 |",
        "|---|---|---|---|---|---|---|",
    ]
    for result in results:
        lines.append(
            f"| {result['name']} | {result['northwind_chunks']} "
            f"| {float(str(result['recall_at_3'])):.3f} | {float(str(result['recall_at_5'])):.3f} "
            f"| {float(str(result['mrr'])):.3f} | {float(str(result['fact_recall_at_5'])):.3f} "
            f"| {float(str(result['context_words_at_5'])):.0f} |"
        )
    return "\n".join(lines)


async def run(qdrant_url: str) -> list[dict[str, object]]:
    settings = get_settings()
    questions = [q for q in load_northwind_questions() if q.gold_document_ids]
    check_facts(questions)
    embedder = Embedder(settings.embedding_model, settings.embedding_query_prefix)
    return [await evaluate(config, questions, embedder, qdrant_url) for config in CONFIGS]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="where to write the JSON")
    parser.add_argument("--qdrant-url", default="http://localhost:6333", help="a local Qdrant")
    arguments = parser.parse_args()

    configure_logging(get_settings().log_level, json=False)
    results = asyncio.run(run(arguments.qdrant_url))
    question_count = len([q for q in load_northwind_questions() if q.gold_document_ids])
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(results, indent=2) + "\n")
    print(to_markdown(results, question_count))


if __name__ == "__main__":
    main()
