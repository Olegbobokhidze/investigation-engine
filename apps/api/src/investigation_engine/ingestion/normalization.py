"""Text clean-up applied to every document, whatever its format."""

import hashlib
import re
import unicodedata

# NFKC (below) already turns non-breaking and other unicode spaces into plain spaces.
_HORIZONTAL_SPACE = re.compile(r"[ \t]+")
_EXTRA_BLANK_LINES = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    """Returns `text` with consistent unicode, line endings and whitespace.

    Paragraph breaks (blank lines) are kept, because the structure-aware chunker splits on
    them; runs of spaces and extra blank lines left over by PDF/DOCX extraction are not.
    """
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = (_HORIZONTAL_SPACE.sub(" ", line).strip() for line in text.split("\n"))
    text = "\n".join(lines)
    return _EXTRA_BLANK_LINES.sub("\n\n", text).strip()


def content_hash(normalized_text: str) -> str:
    """SHA-256 of normalized text: identical content gives an identical hash, whatever the
    file name, format or whitespace, so re-uploads are recognized as duplicates."""
    return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
