"""Read the pinned public guide into page/column excerpts. Never infer policy cover.

This layout profile is only for the SHA-256 below. It is not a general PDF reader.
Full column excerpts retain surrounding clauses; tables are not flattened into prose.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DOC = "Medibank_OSHC_Member_Guide.pdf"
SOURCE_URL = "https://www.medibankoshc.com.au/content/dam/b2c/docs/mpl/" + SOURCE_DOC
SOURCE_SHA256 = "6ca7151567ee2b61f8e6b50340c297d50deb249a013f055ef38f50ed07ec87c7"
CAPTURED_ON = "2026-09-28"
EFFECTIVE_MONTH = "2026-05"
PROFILE = "medibank-columns-v1"
OMITTED_PAGES = (
    (1, "Cover, used for effective-date verification"),
    (2, "Front matter"), (6, "Contents"), (7, "Contents"),
    (19, "Hospital Benefits table: inspect the original PDF table"),
    (37, "Back cover"),
)
_FOOTER = re.compile(r"(?:OSHC Member Guide\s*\|\s*\d+|\d+\s*\|\s*OSHC Member Guide)")


class SourceError(RuntimeError):
    pass


@dataclass(frozen=True)
class PolicyChunk:
    chunk_id: str
    page: int
    column: str
    text: str
    line_boxes: tuple[tuple[float, float, float, float], ...]


@dataclass(frozen=True)
class PolicyCorpus:
    chunks: tuple[PolicyChunk, ...]
    parser_version: str


def _column_chunks(page, number: int) -> tuple[PolicyChunk, ...]:
    if page.rotation or abs(page.rect.width - 419.528) > 1 or abs(page.rect.height - 595.276) > 1:
        raise SourceError(f"Unexpected page geometry on PDF page {number}.")
    lines = []
    for block in page.get_text("dict", flags=pymupdf.TEXTFLAGS_TEXT, sort=False)["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            text = " ".join("".join(span["text"] for span in line["spans"]).split())
            if not text or _FOOTER.fullmatch(text):
                continue
            if abs(line["dir"][0] - 1) > 0.01 or abs(line["dir"][1]) > 0.01:
                raise SourceError(f"Unexpected text direction on PDF page {number}.")
            lines.append({"text": text, "box": tuple(line["bbox"]),
                          "size": max(span["size"] for span in line["spans"])})
    centre = page.rect.width / 2
    titles = [line for line in lines if line["size"] >= 15 and line["box"][1] < 75]
    # A single page title applies to both columns. Page 28 has two separate titles.
    shared = titles if titles and all(line["box"][0] < centre for line in titles) else []
    columns = {"left": [], "right": []}
    for line in lines:
        if line in shared:
            continue
        x0, _, x1, _ = line["box"]
        if x1 <= centre + 0.5:
            columns["left"].append(line)
        elif x0 >= centre - 0.5:
            columns["right"].append(line)
        else:
            raise SourceError(f"Text crosses the column boundary on PDF page {number}.")

    def order(line):
        return round(line["box"][1], 1), line["box"][0]

    chunks = []
    for column, body in columns.items():
        if not body:
            continue
        ordered = sorted(shared, key=order) + sorted(body, key=order)
        text = "\n".join(line["text"] for line in ordered)
        boxes = tuple(tuple(round(value, 3) for value in line["box"]) for line in ordered)
        ident = f"{PROFILE}-{SOURCE_SHA256[:12]}-p{number:02d}-{column}"
        chunks.append(PolicyChunk(ident, number, column, text, boxes))
    return tuple(chunks)


def build_corpus(root: Path = ROOT) -> PolicyCorpus:
    """Verify manifest and raw PDF before extracting this fixed layout. No network calls."""
    root = Path(root)
    try:
        with (root / "corpus/MANIFEST.csv").open(encoding="utf-8-sig", newline="") as handle:
            entries = [row for row in csv.DictReader(handle)
                       if row.get("URL", "").strip() == SOURCE_URL]
    except (OSError, UnicodeError, csv.Error) as error:
        raise SourceError("Cannot read the source manifest.") from error
    if (len(entries) != 1 or entries[0].get("SHA-256", "").strip().lower() != SOURCE_SHA256
            or entries[0].get("Capture Date", "").strip() != CAPTURED_ON):
        raise SourceError("The manifest differs from the pinned guide metadata.")
    source = root / "corpus" / SOURCE_DOC
    try:
        with source.open("rb") as handle:
            raw = handle.read(64 * 1024 * 1024 + 1)
    except OSError as error:
        raise SourceError("Missing source PDF. Restore the frozen guide into corpus/.") from error
    if len(raw) > 64 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise SourceError("Source PDF SHA-256 differs from the frozen guide.")
    chunks = []
    try:
        with pymupdf.open(stream=raw, filetype="pdf") as book:
            if book.needs_pass or book.is_repaired or len(book) != 37:
                raise SourceError("Unexpected PDF structure.")
            if "Effective May 2026." not in book[0].get_text():
                raise SourceError("The cover effective date could not be verified.")
            omitted = {page for page, _ in OMITTED_PAGES}
            for number, page in enumerate(book, 1):
                if number not in omitted:
                    page_chunks = _column_chunks(page, number)
                    if not page_chunks:
                        raise SourceError(f"No text extracted from PDF page {number}.")
                    chunks.extend(page_chunks)
    except (RuntimeError, ValueError) as error:
        if isinstance(error, SourceError):
            raise
        raise SourceError("Could not read the verified PDF layout.") from error
    return PolicyCorpus(tuple(chunks), pymupdf.VersionBind)


def index_bytes(corpus: PolicyCorpus) -> bytes:
    record = {"profile": PROFILE, "source_doc": SOURCE_DOC, "source_url": SOURCE_URL,
              "source_sha256": SOURCE_SHA256, "captured_on": CAPTURED_ON,
              "effective_month": EFFECTIVE_MONTH, "parser_version": corpus.parser_version,
              "omitted_pages": dict(OMITTED_PAGES),
              "scope": "Column excerpts only; not complete policy interpretation or a coverage decision.",
              "chunks": [asdict(chunk) for chunk in corpus.chunks]}
    return (json.dumps(record, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode("utf-8")


def save_index(corpus: PolicyCorpus, path: Path) -> str:
    """Write derived third-party text only to a caller-selected, ignored corpus path."""
    path = Path(path)
    raw = index_bytes(corpus)
    if path.exists():
        if path.read_bytes() != raw:
            raise SourceError("Existing index differs. Keep it for review instead of overwriting.")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(raw)
    return hashlib.sha256(raw).hexdigest()
