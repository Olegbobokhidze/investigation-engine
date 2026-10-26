from investigation_engine.ingestion.normalization import normalize_text


def test_normalize_text_collapses_spaces_and_keeps_paragraphs() -> None:
    text = "Title  \r\n\r\n\r\n\r\nFirst\t\tline   here.\r\nSecond line.\n\n\n"

    normalized = normalize_text(text)

    assert normalized == "Title\n\nFirst line here.\nSecond line."


def test_normalize_text_unifies_unicode_forms() -> None:
    # The "fi" ligature (U+FB01) and non-breaking spaces (U+00A0) are common in PDF output.
    normalized = normalize_text("\ufb01le\u00a0name")

    assert normalized == "file name"
