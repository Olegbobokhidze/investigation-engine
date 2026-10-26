"""Database model for documents in the corpus.

Postgres holds one row per document (metadata and full text) for listing, search by name,
deduplication and CRUD. The searchable chunks and their vectors live in Qdrant.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from investigation_engine.core.database import Base


class FileType(StrEnum):
    PDF = "pdf"
    DOCX = "docx"
    MARKDOWN = "md"
    TEXT = "txt"


class DocumentOrigin(StrEnum):
    """Dataset documents are the evaluation corpus and are read-only; uploads can change."""

    DATASET = "dataset"
    UPLOAD = "upload"


def _enum_column[E: StrEnum](enum_type: type[E]) -> Enum:
    # Store the enum's values ("pdf"), not its member names ("PDF"), as plain strings.
    return Enum(
        enum_type,
        native_enum=False,
        length=16,
        values_callable=lambda members: [member.value for member in members],
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    file_type: Mapped[FileType] = mapped_column(_enum_column(FileType))
    origin: Mapped[DocumentOrigin] = mapped_column(_enum_column(DocumentOrigin))
    text: Mapped[str] = mapped_column(Text)
    # SHA-256 of the normalized text; unique, so the same content can't be indexed twice.
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    chunk_count: Mapped[int] = mapped_column(Integer)
    # Whatever the loader could extract: author, page count, source URL, ...
    file_metadata: Mapped[dict[str, str | int]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
