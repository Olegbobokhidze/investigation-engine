"""The synthetic Northwind Pay corpus: renders it into real PDF, DOCX, Markdown and TXT files,
then indexes those files as read-only dataset documents.

Indexing goes through the same loaders as uploads (`ingestion.loaders`), so the corpus also
exercises every supported format end to end.

    uv run python -m investigation_engine.datasets.synthetic            # render + index
    uv run python -m investigation_engine.datasets.synthetic --render   # only write files

The rendered files are committed in data/synthetic/ so they can be opened and inspected;
rendering needs the dev dependency fpdf2, indexing doesn't.
"""

import argparse
import asyncio
from pathlib import Path

import docx

from investigation_engine.core.config import get_settings
from investigation_engine.core.logging import configure_logging
from investigation_engine.datasets.indexing import DatasetDocument, index_dataset
from investigation_engine.datasets.northwind_corpus import DOCUMENTS, SyntheticDocument
from investigation_engine.documents.models import Document, DocumentOrigin
from investigation_engine.ingestion.chunking import Chunker, chunker_from_settings
from investigation_engine.ingestion.pipeline import prepare_document

CORPUS_DIR = Path("data/synthetic")


def document_id(file_name: str) -> str:
    return f"northwind_{Path(file_name).stem.replace('-', '_')}"


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _render_docx(document: SyntheticDocument, path: Path) -> None:
    output = docx.Document()
    output.core_properties.title = document.title
    output.core_properties.author = document.author
    rows: list[list[str]] = []

    def flush_table() -> None:
        if rows:
            table = output.add_table(rows=len(rows), cols=len(rows[0]))
            for row_cells, row in zip(table.rows, rows, strict=True):
                for cell, text in zip(row_cells.cells, row, strict=True):
                    cell.text = text
            rows.clear()

    for line in document.body.splitlines():
        if line.startswith("|"):
            rows.append(_table_cells(line))
            continue
        flush_table()
        if line.startswith("## "):
            output.add_heading(line[3:], level=2)
        elif line.startswith("# "):
            output.add_heading(line[2:], level=1)
        elif line.strip():
            output.add_paragraph(line)
    flush_table()
    output.save(str(path))


def _render_pdf(document: SyntheticDocument, path: Path) -> None:
    from fpdf import FPDF  # dev-only dependency, needed just for rendering

    pdf = FPDF()
    pdf.set_title(document.title)
    pdf.set_author(document.author)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    for line in document.body.splitlines():
        if line.startswith("# "):
            pdf.set_font("Helvetica", style="B", size=16)
            pdf.multi_cell(0, 9, line[2:], new_x="LMARGIN", new_y="NEXT")
        elif line.startswith("## "):
            pdf.set_font("Helvetica", style="B", size=12)
            pdf.ln(3)
            pdf.multi_cell(0, 7, line[3:], new_x="LMARGIN", new_y="NEXT")
        elif line.strip():
            pdf.set_font("Helvetica", size=11)
            pdf.multi_cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.ln(3)  # a blank line separates paragraphs
    pdf.output(str(path))


def render_corpus(directory: Path = CORPUS_DIR) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for document in DOCUMENTS:
        path = directory / document.file_name
        if path.suffix == ".pdf":
            _render_pdf(document, path)
        elif path.suffix == ".docx":
            _render_docx(document, path)
        else:
            path.write_text(document.body, encoding="utf-8")


def to_dataset_document(document: SyntheticDocument, chunker: Chunker) -> DatasetDocument:
    path = CORPUS_DIR / document.file_name
    prepared = prepare_document(path.read_bytes(), document.file_name, chunker)
    row = Document(
        id=document_id(document.file_name),
        title=document.file_name,
        file_type=prepared.file_type,
        origin=DocumentOrigin.DATASET,
        text=prepared.text,
        content_hash=prepared.content_hash,
        chunk_count=len(prepared.chunks),
        file_metadata={**prepared.metadata, "source": "northwind-synthetic"},
    )
    return DatasetDocument(document=row, chunks=prepared.chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render and index the Northwind Pay corpus.")
    parser.add_argument("--render", action="store_true", help="only write the files")
    arguments = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level, json=False)
    if arguments.render or not CORPUS_DIR.exists():
        render_corpus()
    if arguments.render:
        return
    chunker = chunker_from_settings(settings)
    items = [to_dataset_document(document, chunker) for document in DOCUMENTS]
    asyncio.run(index_dataset(settings, items))


if __name__ == "__main__":
    main()
