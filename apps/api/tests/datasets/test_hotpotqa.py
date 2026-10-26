from pathlib import Path

import pyarrow as arrow
import pyarrow.parquet as parquet

from investigation_engine.datasets.hotpotqa import Paragraph, document_id, read_paragraphs


def _write_contexts(path: Path, contexts: list[dict[str, list[object]]]) -> None:
    parquet.write_table(arrow.table({"context": contexts}), path)


def test_read_paragraphs_keeps_the_first_paragraph_per_title(tmp_path: Path) -> None:
    path = tmp_path / "hotpotqa.parquet"
    _write_contexts(
        path,
        [
            {
                "title": ["Ed Wood", "Scott Derrickson"],
                "sentences": [["Ed Wood is a film.", " It stars Johnny Depp."], ["A director."]],
            },
            {"title": ["Ed Wood"], "sentences": [["A later copy of the same paragraph."]]},
        ],
    )

    paragraphs = read_paragraphs(path)

    assert paragraphs == [
        Paragraph(title="Ed Wood", text="Ed Wood is a film. It stars Johnny Depp."),
        Paragraph(title="Scott Derrickson", text="A director."),
    ]


def test_document_id_is_stable_and_distinct_per_title() -> None:
    assert document_id("Ed Wood") == document_id("Ed Wood")
    assert document_id("Ed Wood") != document_id("Ed Wood (film)")
    assert document_id("Ed Wood").startswith("hotpot_")
