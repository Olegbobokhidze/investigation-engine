"""Re-ranking: a cross-encoder reads the query and one passage together and scores the pair.

The dense model embeds query and passage separately, so it compares two summaries; a
cross-encoder sees both texts at once and can match them word by word. That is more accurate
and far too slow for 66k documents, but fine for the top 20 candidates that hybrid search
has already found. Runs on CPU (ONNX) and is synchronous: call it through
`asyncio.to_thread`.
"""

from collections.abc import Sequence
from typing import Protocol

from fastembed.rerank.cross_encoder import TextCrossEncoder

from investigation_engine.retrieval.vector_store import ChunkRecord


class Reranker(Protocol):
    """Scores each text's relevance to the query; higher is more relevant."""

    def score(self, query: str, texts: Sequence[str]) -> list[float]: ...


class CrossEncoderReranker:
    def __init__(self, model: str) -> None:
        # Downloads the model on first use and caches it on disk, like the embedders.
        self._model = TextCrossEncoder(model)

    def score(self, query: str, texts: Sequence[str]) -> list[float]:
        return [float(score) for score in self._model.rerank(query, list(texts))]


def passage_text(record: ChunkRecord) -> str:
    """What the reranker reads: the chunk with its title, so "he" or "the service" in the
    text can still be matched to the name in the query."""
    heading = (
        f"{record.document_title} > {record.section}" if record.section else record.document_title
    )
    return f"{heading}\n{record.text}"


def rerank(
    query: str, records: Sequence[ChunkRecord], reranker: Reranker
) -> list[tuple[ChunkRecord, float]]:
    """The records with their reranker scores, most relevant first. Ties keep the order
    they came in (the fused order), since Python's sort is stable."""
    scores = reranker.score(query, [passage_text(record) for record in records])
    return sorted(zip(records, scores, strict=True), key=lambda pair: pair[1], reverse=True)
