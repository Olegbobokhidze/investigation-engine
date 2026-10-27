"""Checks the model's citations before an answer is shown.

A citation must point at a passage the model was actually given; an answer with no valid
citation is not grounded, so the engine abstains instead; a conflict must cite both sides.
Cited passages are then renumbered 1..n in reading order, which is how the UI lists them.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass

from investigation_engine.investigation.models import InvestigationStatus

NO_EVIDENCE_ANSWER = "The documents don't contain enough evidence to answer this question."

_CITATION = re.compile(r"\[(\d+)\]")
# Variants models write instead of [n]: [1, 2] and OpenAI-style 【3†source】.
_CITATION_LIST = re.compile(r"\[(\d+(?:\s*,\s*\d+)+)\]")
_FULLWIDTH_CITATION = re.compile(r"【(\d+)[^】]*】")
# Left behind when an invalid marker is removed: "text [99]." → "text ."
_SPACE_BEFORE_PUNCTUATION = re.compile(r"[ \t]+([.,;:!?])")


@dataclass(frozen=True)
class CheckedAnswer:
    status: InvestigationStatus
    answer: str
    conflicts: list[str]
    # Original passage numbers of the cited passages; the passage at index i is now [i + 1].
    cited_passages: list[int]
    removed_citations: int
    removed_conflicts: int


def check_citations(
    status: InvestigationStatus,
    answer: str,
    conflicts: list[str],
    is_known: Callable[[int], bool],
) -> CheckedAnswer:
    removed_citations = 0

    def keep_known(text: str) -> str:
        nonlocal removed_citations
        text = _normalize(text)
        unknown = [int(number) for number in _CITATION.findall(text) if not is_known(int(number))]
        removed_citations += len(unknown)
        text = _CITATION.sub(lambda m: m[0] if is_known(int(m[1])) else "", text)
        return _SPACE_BEFORE_PUNCTUATION.sub(r"\1", text).strip()

    answer = keep_known(answer)
    checked_conflicts = [keep_known(conflict) for conflict in conflicts]
    # One side of a disagreement isn't a conflict the user can check.
    kept_conflicts = [c for c in checked_conflicts if len(set(_CITATION.findall(c))) >= 2]

    if status == "answered" and not _CITATION.search(answer):
        status, answer, kept_conflicts = "insufficient_evidence", NO_EVIDENCE_ANSWER, []

    cited_passages = list(
        dict.fromkeys(int(n) for text in [answer, *kept_conflicts] for n in _CITATION.findall(text))
    )
    new_number = {old: index + 1 for index, old in enumerate(cited_passages)}

    def renumber(text: str) -> str:
        return _CITATION.sub(lambda m: f"[{new_number[int(m[1])]}]", text)

    return CheckedAnswer(
        status=status,
        answer=renumber(answer),
        conflicts=[renumber(conflict) for conflict in kept_conflicts],
        cited_passages=cited_passages,
        removed_citations=removed_citations,
        removed_conflicts=len(conflicts) - len(kept_conflicts),
    )


def has_citation(text: str) -> bool:
    return _CITATION.search(_normalize(text)) is not None


def _normalize(text: str) -> str:
    text = _FULLWIDTH_CITATION.sub(r"[\1]", text)
    return _CITATION_LIST.sub(
        lambda m: "".join(f"[{number.strip()}]" for number in m[1].split(",")), text
    )
