"""The passages an investigation has seen, numbered so the model can cite them as [n]."""

from dataclasses import dataclass

from investigation_engine.retrieval.vector_store import ChunkRecord

# What the model sees of each passage. A chunk is at most ~200 words; trimming the rest
# keeps a multi-search investigation inside the LLM's per-minute token quota.
_PROMPT_EXCERPT_CHARS = 700


@dataclass(frozen=True)
class Passage:
    number: int
    record: ChunkRecord


class Evidence:
    def __init__(self) -> None:
        self._passages: list[Passage] = []
        self._numbers: dict[tuple[str, int], int] = {}

    def add(self, records: list[ChunkRecord]) -> tuple[list[Passage], list[Passage]]:
        """Numbers new records; returns (new passages, passages already seen)."""
        new: list[Passage] = []
        seen: list[Passage] = []
        for record in records:
            key = (record.document_id, record.chunk_index)
            if key in self._numbers:
                seen.append(self._passages[self._numbers[key] - 1])
                continue
            passage = Passage(number=len(self._passages) + 1, record=record)
            self._passages.append(passage)
            self._numbers[key] = passage.number
            new.append(passage)
        return new, seen

    def get(self, number: int) -> Passage | None:
        return self._passages[number - 1] if 1 <= number <= len(self._passages) else None

    @property
    def document_ids(self) -> list[str]:
        """Distinct documents, in the order they were first seen."""
        return list(dict.fromkeys(passage.record.document_id for passage in self._passages))


def format_passages(passages: list[Passage]) -> str:
    return "\n\n".join(_format(passage) for passage in passages)


def _format(passage: Passage) -> str:
    record = passage.record
    heading = record.document_title + (f" > {record.section}" if record.section else "")
    text = record.text
    if len(text) > _PROMPT_EXCERPT_CHARS:
        text = text[:_PROMPT_EXCERPT_CHARS].rsplit(" ", 1)[0] + " …"
    return f"[{passage.number}] {heading} (document_id: {record.document_id})\n{text}"
