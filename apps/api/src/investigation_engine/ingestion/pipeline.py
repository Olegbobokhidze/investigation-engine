"""The steps from file bytes to indexable chunks, shared by uploads and the dataset loader.

Embedding and storage are left to the caller, which batches them differently: an upload
embeds one document, the dataset loader thousands at a time.
"""

from dataclasses import dataclass

from investigation_engine.documents.models import Document, FileType
from investigation_engine.ingestion.chunking import Chunk, Chunker
from investigation_engine.ingestion.loaders import Metadata, load_document
from investigation_engine.ingestion.normalization import content_hash
from investigation_engine.retrieval.vector_store import ChunkRecord


@dataclass(frozen=True)
class PreparedDocument:
    text: str
    file_type: FileType
    metadata: Metadata
    content_hash: str
    chunks: list[Chunk]


def prepare_document(content: bytes, file_name: str, chunker: Chunker) -> PreparedDocument:
    """Loads, normalizes, hashes and chunks a file. Raises the loader's `AppError`s."""
    loaded = load_document(content, file_name)
    return PreparedDocument(
        text=loaded.text,
        file_type=loaded.file_type,
        metadata=loaded.metadata,
        content_hash=content_hash(loaded.text),
        chunks=chunker.split(loaded.text),
    )


def embedding_text(document_title: str, chunk: Chunk) -> str:
    """The text we embed for a chunk: its own text plus where it comes from.

    A chunk often refers to its subject only as "he" or "the service"; the document title
    and section heading put the subject back, so the chunk is found by name.
    """
    header = [document_title] if chunk.section is None else [document_title, chunk.section]
    return "\n".join([*header, chunk.text])


def chunk_records(document: Document, chunks: list[Chunk]) -> list[ChunkRecord]:
    return [
        ChunkRecord(
            document_id=document.id,
            document_title=document.title,
            file_type=document.file_type.value,
            origin=document.origin.value,
            chunk_index=chunk.index,
            section=chunk.section,
            text=chunk.text,
        )
        for chunk in chunks
    ]
