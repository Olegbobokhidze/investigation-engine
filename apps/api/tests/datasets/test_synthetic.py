from pathlib import Path

import pytest

from investigation_engine.datasets.northwind_corpus import DOCUMENTS, SyntheticDocument
from investigation_engine.datasets.synthetic import document_id, render_corpus
from investigation_engine.ingestion.loaders import load_document


@pytest.fixture(scope="module")
def corpus_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("northwind")
    render_corpus(directory)
    return directory


@pytest.mark.parametrize("document", DOCUMENTS, ids=lambda document: document.file_name)
def test_every_rendered_file_loads_back_with_its_content(
    corpus_dir: Path, document: SyntheticDocument
) -> None:
    path = corpus_dir / document.file_name

    loaded = load_document(path.read_bytes(), document.file_name)

    assert loaded.file_type.value == path.suffix.removeprefix(".")
    # The first body line after the heading survives each format's round trip.
    first_sentence = next(
        line for line in document.body.splitlines() if line and not line.startswith("#")
    )
    assert first_sentence.split(".")[0] in loaded.text.replace("\n", " ")


def test_document_ids_are_unique_and_readable() -> None:
    ids = [document_id(document.file_name) for document in DOCUMENTS]

    assert len(ids) == len(set(ids))
    assert document_id("inc-0412-payment-delays.pdf") == "northwind_inc_0412_payment_delays"
