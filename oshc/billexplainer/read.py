'''Local PDF/text reading for the prototype. No OCR or API calls.'''

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pymupdf

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 20
MAX_CHARS = 100_000
SourceKind = Literal["pdf_text", "pasted_text", "image"]


@dataclass(frozen=True)
class BillText:
    text: str
    source_kind: SourceKind
    warnings: tuple[str, ...] = ()
    page_count: int = 0


def read_text(text: str) -> BillText:
    if not isinstance(text, str) or not text.strip():
        return BillText("", "pasted_text", ("No bill text was supplied.",))
    if len(text) > MAX_CHARS:
        return BillText("", "pasted_text", ("Bill text exceeds 100,000 characters.",))
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    if "\x00" in text:
        return BillText("", "pasted_text", ("Text contains binary characters; use a text-based PDF.",))
    return BillText(text, "pasted_text")


def _page_text(page) -> str:
    # Reconstruct rows from word positions, not PDF content-stream order.
    words = sorted(page.get_text("words"), key=lambda word: (word[3], word[0]))
    rows = []
    for word in words:
        if not rows or abs(word[3] - rows[-1][0][3]) > 2.5:
            rows.append([word])
        else:
            rows[-1].append(word)
    lines = []
    for row in rows:
        row.sort(key=lambda word: word[0])
        parts = [row[0][4]]
        for previous, current in zip(row, row[1:]):
            parts.append(("\t" if current[0] - previous[2] >= 12 else " ") + current[4])
        lines.append("".join(parts))
    return "\n".join(lines)


def read_pdf(source: bytes | str | Path) -> BillText:
    def fail(message):
        return BillText("", "pdf_text", (message,))

    try:
        if isinstance(source, (str, Path)):
            with Path(source).open("rb") as handle:
                data = handle.read(MAX_BYTES + 1)
        elif isinstance(source, bytes):
            data = source
        else:
            return fail("Supply PDF bytes or a local PDF path.")
    except OSError:
        return fail("The PDF file could not be read.")
    if not data or len(data) > MAX_BYTES:
        return fail("The PDF is empty or exceeds 10 MiB.")
    if not data.lstrip().startswith(b"%PDF-"):
        return fail("This is not a PDF. Photos and scanned images need OCR, which is not enabled.")

    try:
        with pymupdf.open(stream=data, filetype="pdf") as document:
            if document.needs_pass:
                return fail("The PDF requires a password. Supply an unlocked copy.")
            if document.is_repaired:
                return fail("The PDF has structural damage. Supply a clean copy.")
            if not 1 <= document.page_count <= MAX_PAGES:
                return fail("The PDF must contain between 1 and 20 pages.")
            pages = []
            for number, page in enumerate(document, 1):
                text = _page_text(page)
                if not text.strip():
                    return fail(f"Page {number} has no selectable text. No partial bill was extracted.")
                pages.append(text)
                if sum(map(len, pages)) > MAX_CHARS:
                    return fail("Extracted PDF text exceeds 100,000 characters.")
            warning = "Check extracted rows against the PDF; images and handwriting are not read."
            return BillText("\n\n".join(pages), "pdf_text", (warning,), document.page_count)
    except (RuntimeError, ValueError):
        return fail("The PDF could not be decoded. Supply a clean text-based PDF.")
