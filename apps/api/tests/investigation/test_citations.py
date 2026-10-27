from investigation_engine.investigation.citations import (
    NO_EVIDENCE_ANSWER,
    check_citations,
    has_citation,
)


def test_check_citations_renumbers_cited_passages_in_reading_order() -> None:
    checked = check_citations(
        "answered", "Pool cut to 20 [7]. Retries doubled load [3][7].", [], lambda n: True
    )

    assert checked.answer == "Pool cut to 20 [1]. Retries doubled load [2][1]."
    assert checked.cited_passages == [7, 3]


def test_check_citations_removes_citations_to_passages_never_shown() -> None:
    checked = check_citations("answered", "Pool cut to 20 [2][9].", [], lambda n: n <= 5)

    assert checked.answer == "Pool cut to 20 [1]."
    assert checked.removed_citations == 1


def test_check_citations_abstains_when_no_valid_citation_is_left() -> None:
    checked = check_citations(
        "answered", "Pool cut to 20 [9].", ["A [9] vs B [8]."], lambda n: n <= 5
    )

    assert checked.status == "insufficient_evidence"
    assert checked.answer == NO_EVIDENCE_ANSWER
    assert checked.conflicts == []
    assert checked.cited_passages == []


def test_check_citations_keeps_an_uncited_explanation_when_abstaining() -> None:
    checked = check_citations(
        "insufficient_evidence", "Only a US refund policy exists.", [], lambda n: True
    )

    assert checked.status == "insufficient_evidence"
    assert checked.answer == "Only a US refund policy exists."


def test_check_citations_drops_a_conflict_that_cites_only_one_side() -> None:
    checked = check_citations(
        "answered",
        "Deployed at 09:05 [1] or 09:40 [2].",
        ["Report says 09:05 [1]; change log says 09:40 [2].", "Report says 09:05 [1]."],
        lambda n: True,
    )

    assert checked.conflicts == ["Report says 09:05 [1]; change log says 09:40 [2]."]
    assert checked.removed_conflicts == 1


def test_check_citations_understands_listed_and_fullwidth_markers() -> None:
    checked = check_citations(
        "answered", "Pool cut [1, 2]. Lag 41 min 【3†source】.", [], lambda n: True
    )

    assert checked.answer == "Pool cut [1][2]. Lag 41 min [3]."


def test_has_citation_detects_any_marker_style() -> None:
    assert has_citation("Pool cut 【2†source】.")
    assert not has_citation("Pool cut to 20.")
