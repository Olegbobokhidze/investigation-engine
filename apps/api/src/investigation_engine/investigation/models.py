"""What an investigation returns. Mirrors apps/web/src/features/investigations/types.ts,
plus usage numbers the evaluation reads."""

from dataclasses import dataclass
from typing import Literal

# insufficient_evidence: the documents don't support an answer, so the engine abstains.
type InvestigationStatus = Literal["answered", "insufficient_evidence"]


@dataclass(frozen=True)
class Source:
    """A cited passage. The answer and conflicts refer to it as `[number]`."""

    number: int
    document_id: str
    document_title: str
    file_type: str
    excerpt: str


@dataclass(frozen=True)
class Conflict:
    """Sources that disagree; the summary cites each side."""

    summary: str


@dataclass(frozen=True)
class Step:
    """One thing the engine did, shown to the user as the investigation's trace."""

    title: str
    detail: str
    result: str | None = None


@dataclass(frozen=True)
class Usage:
    llm_calls: int
    total_tokens: int
    # Every model that answered a call; more than one means the fallback was used.
    models: list[str]


@dataclass(frozen=True)
class Investigation:
    id: str
    question: str
    status: InvestigationStatus
    answer: str
    sources: list[Source]
    conflicts: list[Conflict]
    steps: list[Step]
    usage: Usage
    # Every document the agent saw, cited or not: lets the evaluation separate retrieval
    # misses from answering mistakes.
    retrieved_document_ids: list[str]
