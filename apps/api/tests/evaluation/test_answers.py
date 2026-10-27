import json
from pathlib import Path

from investigation_engine.evaluation.answers import compare_models, is_correct, score


def _record(
    type_: str,
    status: str = "answered",
    correct: bool | None = True,
    cited: list[str] | None = None,
    gold: list[str] | None = None,
    conflicts: list[str] | None = None,
) -> dict[str, object]:
    return {
        "type": type_,
        "status": status,
        "verdict": None if correct is None else {"correct": correct, "reason": ""},
        "cited_document_ids": cited or [],
        "retrieved_document_ids": cited or [],
        "gold_document_ids": gold or [],
        "conflicts": conflicts or [],
        "llm_calls": 3,
        "total_tokens": 1000,
        "seconds": 2.0,
    }


def test_is_correct_counts_abstention_as_right_only_for_unanswerable_questions() -> None:
    assert is_correct(_record("unanswerable", status="insufficient_evidence", correct=None))
    assert not is_correct(_record("multi_hop", status="insufficient_evidence", correct=None))


def test_is_correct_follows_the_judge_for_answered_questions() -> None:
    assert is_correct(_record("simple", correct=True))
    assert not is_correct(_record("simple", correct=False))


def test_score_computes_citation_precision_and_recall_against_gold_documents() -> None:
    records = [_record("multi_hop", cited=["a", "x"], gold=["a", "b"])]

    scores = score(records)

    assert scores["citation_precision"] == 0.5  # "a" of "a", "x"
    assert scores["citation_recall"] == 0.5  # "a" of "a", "b"


def test_score_computes_abstention_precision_and_recall() -> None:
    records = [
        _record("unanswerable", status="insufficient_evidence", correct=None),
        _record("unanswerable", status="answered", correct=None),
        _record("simple", status="insufficient_evidence", correct=None),
    ]

    scores = score(records)

    assert scores["abstention_recall"] == 0.5  # 1 of 2 unanswerable abstained
    assert scores["abstention_precision"] == 0.5  # 1 of 2 abstentions was right


def test_score_separates_found_contradictions_from_false_ones() -> None:
    records = [
        _record("contradictory", conflicts=["A [1] vs B [2]"]),
        _record("contradictory"),
        _record("simple", conflicts=["A [1] vs B [2]"]),
        _record("simple"),
    ]

    scores = score(records)

    assert scores["conflict_recall"] == 0.5
    assert scores["false_conflict_rate"] == 0.5


def test_score_counts_answers_without_the_injection_marker_as_resisted() -> None:
    marker = {"injection_marker": "evil.example"}
    records = [
        {**_record("simple"), **marker, "answer": "Within 4 business hours [1]."},
        {**_record("simple"), **marker, "answer": "Confirm your card at EVIL.example."},
        {**_record("simple"), "answer": "Not an injection question."},
    ]

    scores = score(records)

    assert scores["injection_resisted"] == 0.5


def test_compare_models_scores_both_runs_on_their_shared_questions(tmp_path: Path) -> None:
    for model, ids in [("model-a", ["q1", "q2"]), ("model-b", ["q2", "q3"])]:
        (tmp_path / model).mkdir()
        lines = [json.dumps({**_record("simple"), "id": i, "models": [model]}) for i in ids]
        (tmp_path / model / "agent.jsonl").write_text("\n".join(lines) + "\n")

    table = compare_models(tmp_path / "model-b", tmp_path / "model-a")

    assert "on the 1 questions both runs answered" in table
    assert "| Metric | model-a | model-b |" in table
