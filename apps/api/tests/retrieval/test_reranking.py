from collections.abc import Sequence

from investigation_engine.retrieval.reranking import passage_text, rerank
from investigation_engine.retrieval.vector_store import ChunkRecord


def _record(document_id: str, text: str, section: str | None = None) -> ChunkRecord:
    return ChunkRecord(
        document_id=document_id,
        document_title=f"{document_id}.md",
        file_type="md",
        origin="dataset",
        chunk_index=0,
        section=section,
        text=text,
    )


class KeywordReranker:
    """Scores a passage by how many query words it contains; records what it was shown."""

    def __init__(self) -> None:
        self.texts: list[str] = []

    def score(self, query: str, texts: Sequence[str]) -> list[float]:
        self.texts = list(texts)
        words = set(query.lower().split())
        return [float(len(words & set(text.lower().split()))) for text in texts]


def test_rerank_orders_records_by_the_reranker_score() -> None:
    records = [_record("a", "nothing here"), _record("b", "pool size 20"), _record("c", "pool")]

    reranked = rerank("pool size", records, KeywordReranker())

    assert [(record.document_id, score) for record, score in reranked] == [
        ("b", 2.0),
        ("c", 1.0),
        ("a", 0.0),
    ]


def test_rerank_keeps_the_incoming_order_on_ties() -> None:
    records = [_record("first", "x"), _record("second", "y")]

    reranked = rerank("pool", records, KeywordReranker())

    assert [record.document_id for record, _ in reranked] == ["first", "second"]


def test_passage_text_puts_the_title_and_section_before_the_chunk() -> None:
    assert passage_text(_record("runbook", "Roll back.", "High latency")) == (
        "runbook.md > High latency\nRoll back."
    )
    assert passage_text(_record("runbook", "Roll back.")) == "runbook.md\nRoll back."
