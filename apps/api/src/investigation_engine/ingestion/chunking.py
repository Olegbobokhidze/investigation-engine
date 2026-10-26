"""Splits a document's text into chunks, the units we embed, index and retrieve.

Two strategies share one interface so the evaluation can compare them:

- `FixedSizeChunker`: windows of N words with an overlap. Simple and uniform, but cuts
  through sentences, tables and sections.
- `StructuredChunker`: packs whole paragraphs up to N words, starts a new chunk at every
  Markdown heading and remembers that heading as the chunk's section. Only a paragraph
  longer than N words is split, at sentence boundaries.

Sizes are in words, a close-enough proxy for tokens (`bge-small` reads up to 512 tokens;
200 English words are roughly 260).
"""

import re
from dataclasses import dataclass
from typing import Protocol

from investigation_engine.core.config import ChunkingStrategy, Settings

_HEADING = re.compile(r"^#{1,6}\s+(.+)$")
# A sentence ends at . ! or ? followed by whitespace. Naive about abbreviations such as
# "e.g.", which only costs an occasional early split.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class Chunk:
    index: int
    text: str
    # The Markdown heading the chunk falls under, kept as retrieval context.
    section: str | None = None


class Chunker(Protocol):
    def split(self, text: str) -> list[Chunk]: ...


class FixedSizeChunker:
    def __init__(self, max_words: int, overlap_words: int) -> None:
        if not 0 <= overlap_words < max_words:
            raise ValueError("overlap_words must be at least 0 and less than max_words.")
        self.max_words = max_words
        self.overlap_words = overlap_words

    def split(self, text: str) -> list[Chunk]:
        words = text.split()
        step = self.max_words - self.overlap_words
        chunks: list[Chunk] = []
        for start in range(0, len(words), step):
            window = words[start : start + self.max_words]
            chunks.append(Chunk(index=len(chunks), text=" ".join(window)))
            if start + self.max_words >= len(words):
                break
        return chunks


class StructuredChunker:
    def __init__(self, max_words: int) -> None:
        if max_words <= 0:
            raise ValueError("max_words must be positive.")
        self.max_words = max_words

    def split(self, text: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        section: str | None = None
        pending: list[str] = []  # paragraphs collected for the next chunk
        pending_words = 0

        def flush() -> None:
            nonlocal pending_words
            if pending:
                chunks.append(Chunk(index=len(chunks), text="\n\n".join(pending), section=section))
                pending.clear()
                pending_words = 0

        for paragraph in text.split("\n\n"):
            first_line = paragraph.split("\n", 1)[0]
            heading = _HEADING.match(first_line)
            if heading:
                # A heading closes the previous section's chunk and opens a new one.
                flush()
                section = heading.group(1).strip()

            for piece in self._fit(paragraph):
                piece_words = len(piece.split())
                if pending_words + piece_words > self.max_words:
                    flush()
                pending.append(piece)
                pending_words += piece_words

        flush()
        return chunks

    def _fit(self, paragraph: str) -> list[str]:
        """Returns the paragraph whole, or split into pieces of at most max_words."""
        if len(paragraph.split()) <= self.max_words:
            return [paragraph]

        # Pack whole sentences into pieces of at most max_words.
        pieces: list[str] = []
        current: list[str] = []
        current_words = 0
        for sentence in _SENTENCE_END.split(paragraph):
            sentence_words = len(sentence.split())
            if current and current_words + sentence_words > self.max_words:
                pieces.append(" ".join(current))
                current, current_words = [], 0
            current.append(sentence)
            current_words += sentence_words
        if current:
            pieces.append(" ".join(current))

        # A single sentence can still be too long (e.g. a table row); cut it by words.
        fitted: list[str] = []
        for piece in pieces:
            words = piece.split()
            for start in range(0, len(words), self.max_words):
                fitted.append(" ".join(words[start : start + self.max_words]))
        return fitted


def create_chunker(strategy: ChunkingStrategy, max_words: int, overlap_words: int) -> Chunker:
    if strategy == "fixed":
        return FixedSizeChunker(max_words=max_words, overlap_words=overlap_words)
    return StructuredChunker(max_words=max_words)


def chunker_from_settings(settings: Settings) -> Chunker:
    return create_chunker(
        settings.chunking_strategy, settings.chunk_max_words, settings.chunk_overlap_words
    )
