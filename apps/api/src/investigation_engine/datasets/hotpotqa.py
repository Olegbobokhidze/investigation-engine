"""Loads the HotpotQA corpus: every distinct paragraph of the dev (distractor) set becomes one
read-only dataset document.

Why this subset: each of the 7,405 dev questions ships with the paragraphs that answer it
(`supporting_facts`), so one file gives a 66,581-document corpus *and* evaluation questions
whose gold sources are inside that corpus. The file is pinned to a dataset revision and
checked against its SHA-256, so every run indexes the same bytes.

Run from apps/api: `uv run python -m investigation_engine.datasets.hotpotqa [--limit N]`.
It is resumable: documents already in Postgres are skipped.
"""

import argparse
import asyncio
import hashlib
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import pyarrow.parquet as parquet
import structlog

from investigation_engine.core.config import get_settings
from investigation_engine.core.logging import configure_logging
from investigation_engine.datasets.indexing import DatasetDocument, index_dataset
from investigation_engine.documents.models import Document, DocumentOrigin, FileType
from investigation_engine.ingestion.chunking import Chunker, chunker_from_settings
from investigation_engine.ingestion.normalization import content_hash, normalize_text

log = structlog.get_logger()

REVISION = "1908d6afbbead072334abe2965f91bd2709910ab"
DATASET_URL = (
    "https://huggingface.co/datasets/hotpotqa/hotpot_qa/resolve/"
    f"{REVISION}/distractor/validation-00000-of-00001.parquet"
)
DATASET_SHA256 = "c20b638ca82b21d04fe12e14ff417ad05153d4d215a65de54497fca4e972f7c6"
DATASET_PATH = Path("data/raw/hotpotqa-validation.parquet")


@dataclass(frozen=True)
class Paragraph:
    title: str
    text: str


def document_id(title: str) -> str:
    """Stable id from the paragraph title (unique in the corpus), so reloads match."""
    return f"hotpot_{hashlib.sha256(title.encode('utf-8')).hexdigest()[:12]}"


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download(path: Path = DATASET_PATH) -> Path:
    """Downloads the pinned file once and verifies its checksum."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        log.info("dataset_downloading", url=DATASET_URL)
        urllib.request.urlretrieve(DATASET_URL, path)
    actual = _sha256_of(path)
    if actual != DATASET_SHA256:
        raise RuntimeError(f"{path} has SHA-256 {actual}, expected {DATASET_SHA256}.")
    return path


def read_paragraphs(path: Path) -> list[Paragraph]:
    """Every distinct paragraph (by title) across all questions' contexts, in file order."""
    contexts = parquet.read_table(path, columns=["context"]).column("context").to_pylist()
    paragraphs: dict[str, Paragraph] = {}
    for context in contexts:
        if context is None:  # Parquet allows null rows; HotpotQA has none, but don't crash
            continue
        for title, sentences in zip(context["title"], context["sentences"], strict=True):
            if title not in paragraphs:
                # Sentences carry their own leading spaces, so they join with "".
                paragraphs[title] = Paragraph(title=title, text=normalize_text("".join(sentences)))
    return [paragraph for paragraph in paragraphs.values() if paragraph.text]


def to_dataset_document(paragraph: Paragraph, chunker: Chunker) -> DatasetDocument:
    chunks = chunker.split(paragraph.text)
    document = Document(
        id=document_id(paragraph.title),
        title=paragraph.title,
        file_type=FileType.TEXT,
        origin=DocumentOrigin.DATASET,
        text=paragraph.text,
        content_hash=content_hash(paragraph.text),
        chunk_count=len(chunks),
        file_metadata={"source": "hotpotqa", "revision": REVISION[:12]},
    )
    return DatasetDocument(document=document, chunks=chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Load the HotpotQA corpus.")
    parser.add_argument("--limit", type=int, default=None, help="load only the first N paragraphs")
    arguments = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level, json=False)
    chunker = chunker_from_settings(settings)
    paragraphs = read_paragraphs(download())[: arguments.limit]
    items = [to_dataset_document(paragraph, chunker) for paragraph in paragraphs]
    asyncio.run(index_dataset(settings, items))


if __name__ == "__main__":
    main()
