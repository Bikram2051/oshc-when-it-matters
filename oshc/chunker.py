"""Chunk the frozen OSHC content corpus into retrieval-ready text chunks.

Owner: Aayush Khade.
The chunker keeps source metadata attached to every chunk so retrieval can
return the frozen RetrievalHit interface.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

import pymupdf


ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "corpus"
MANIFEST_FILE = CORPUS_DIR / "MANIFEST.csv"

MIN_TOKENS = 200
MAX_TOKENS = 400


@dataclass(frozen=True)
class Chunk:
    """A retrieval-ready chunk with its source metadata."""

    chunk_id: str
    text: str
    source_doc: str
    source_url: str
    section: str | None
    captured_on: str


def load_manifest() -> dict[str, dict[str, str]]:
    """Load corpus metadata keyed by local filename."""
    with MANIFEST_FILE.open(encoding="utf-8", newline="") as file:
        rows = csv.DictReader(file)

        manifest = {}

        for row in rows:
            url = row["URL"]
            title = row["Title"]

            if "MBS-XML-20260801.XML" in title:
                filename = "MBS-XML-20260801.XML"
            else:
                filename = Path(url.split("?", 1)[0]).name

            manifest[filename] = row

    return manifest


def normalise_text(text: str) -> str:
    """Clean repeated whitespace while preserving readable paragraphs."""
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def tokenise(text: str) -> list[str]:
    """Return simple whitespace tokens for deterministic chunk sizing."""
    return text.split()


def split_into_chunks(text: str) -> list[str]:
    """Split text into chunks of approximately 200–400 tokens.

    Paragraph boundaries are preferred. A paragraph larger than the maximum
    size is split into smaller token groups.
    """
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]

    chunks: list[str] = []
    current: list[str] = []

    for paragraph in paragraphs:
        paragraph_tokens = tokenise(paragraph)

        if len(paragraph_tokens) > MAX_TOKENS:
            if current:
                chunks.append(" ".join(current))
                current = []

            for start in range(0, len(paragraph_tokens), MAX_TOKENS):
                piece = paragraph_tokens[start : start + MAX_TOKENS]
                chunks.append(" ".join(piece))

            continue

        current_tokens = len(tokenise(" ".join(current)))

        if current and current_tokens + len(paragraph_tokens) > MAX_TOKENS:
            chunks.append(" ".join(current))
            current = []

        current.extend(paragraph_tokens)

    if current:
        chunks.append(" ".join(current))

    return [
        chunk
        for chunk in chunks
        if len(tokenise(chunk)) >= MIN_TOKENS
    ]


def chunk_pdf(
    path: Path,
    *,
    source_url: str,
    captured_on: str,
) -> list[Chunk]:
    """Extract and chunk the Medibank PDF."""
    chunks: list[Chunk] = []

    with pymupdf.open(path) as document:
        for page_number, page in enumerate(document, start=1):
            text = normalise_text(page.get_text())

            if not text:
                continue

            page_chunks = split_into_chunks(text)

            for index, chunk_text in enumerate(page_chunks, start=1):
                chunk_id = f"{path.name}:p{page_number}:c{index}"

                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        text=chunk_text,
                        source_doc=path.name,
                        source_url=source_url,
                        section=f"Page {page_number}",
                        captured_on=captured_on,
                    )
                )

    return chunks


def chunk_xml(
    path: Path,
    *,
    source_url: str,
    captured_on: str,
) -> list[Chunk]:
    """Extract readable text from the MBS XML and chunk it."""
    root = ElementTree.parse(path).getroot()

    text_parts: list[str] = []

    for element in root.iter():
        if element.text and element.text.strip():
            text_parts.append(element.text.strip())

    text = normalise_text("\n\n".join(text_parts))

    chunks: list[Chunk] = []

    for index, chunk_text in enumerate(split_into_chunks(text), start=1):
        chunks.append(
            Chunk(
                chunk_id=f"{path.name}:c{index}",
                text=chunk_text,
                source_doc=path.name,
                source_url=source_url,
                section=None,
                captured_on=captured_on,
            )
        )

    return chunks


def build_chunks() -> list[Chunk]:
    """Build chunks from every approved file in the frozen corpus."""
    manifest = load_manifest()
    chunks: list[Chunk] = []

    for filename, metadata in manifest.items():
        path = CORPUS_DIR / filename

        if not path.exists():
            raise FileNotFoundError(f"Corpus file not found: {path}")

        source_url = metadata["URL"]
        captured_on = metadata["Capture Date"]

        if path.suffix.lower() == ".pdf":
            chunks.extend(
                chunk_pdf(
                    path,
                    source_url=source_url,
                    captured_on=captured_on,
                )
            )

        elif path.suffix.lower() == ".xml":
            chunks.extend(
                chunk_xml(
                    path,
                    source_url=source_url,
                    captured_on=captured_on,
                )
            )

    return chunks