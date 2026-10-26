import pytest

from investigation_engine.ingestion.chunking import (
    FixedSizeChunker,
    StructuredChunker,
    create_chunker,
)


def _words(count: int, prefix: str = "w") -> str:
    return " ".join(f"{prefix}{number}" for number in range(count))


def test_fixed_chunker_windows_overlap() -> None:
    chunker = FixedSizeChunker(max_words=4, overlap_words=1)

    chunks = chunker.split(_words(10))

    assert [chunk.text for chunk in chunks] == [
        "w0 w1 w2 w3",
        "w3 w4 w5 w6",
        "w6 w7 w8 w9",
    ]
    assert [chunk.index for chunk in chunks] == [0, 1, 2]


def test_fixed_chunker_keeps_short_text_whole() -> None:
    chunks = FixedSizeChunker(max_words=200, overlap_words=40).split("Only a few words.")

    assert [chunk.text for chunk in chunks] == ["Only a few words."]


def test_fixed_chunker_rejects_overlap_not_smaller_than_size() -> None:
    with pytest.raises(ValueError, match="overlap_words"):
        FixedSizeChunker(max_words=10, overlap_words=10)


def test_structured_chunker_packs_paragraphs_up_to_the_limit() -> None:
    text = f"{_words(3, 'a')}\n\n{_words(3, 'b')}\n\n{_words(3, 'c')}"

    chunks = StructuredChunker(max_words=6).split(text)

    assert [chunk.text for chunk in chunks] == [
        f"{_words(3, 'a')}\n\n{_words(3, 'b')}",
        _words(3, "c"),
    ]


def test_structured_chunker_starts_a_chunk_at_each_heading() -> None:
    text = "# Incident\n\nAlerts fired at 09:12.\n\n## Resolution\nThe change was reverted."

    chunks = StructuredChunker(max_words=200).split(text)

    assert [(chunk.section, chunk.text) for chunk in chunks] == [
        ("Incident", "# Incident\n\nAlerts fired at 09:12."),
        ("Resolution", "## Resolution\nThe change was reverted."),
    ]


def test_structured_chunker_splits_a_long_paragraph_at_sentences() -> None:
    paragraph = "One two three. Four five six. Seven eight nine."

    chunks = StructuredChunker(max_words=6).split(paragraph)

    assert [chunk.text for chunk in chunks] == [
        "One two three. Four five six.",
        "Seven eight nine.",
    ]


def test_structured_chunker_cuts_a_sentence_longer_than_the_limit() -> None:
    chunks = StructuredChunker(max_words=4).split(_words(9))

    assert [len(chunk.text.split()) for chunk in chunks] == [4, 4, 1]


def test_create_chunker_returns_the_configured_strategy() -> None:
    assert isinstance(create_chunker("fixed", 200, 40), FixedSizeChunker)
    assert isinstance(create_chunker("structured", 200, 40), StructuredChunker)
