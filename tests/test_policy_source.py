"""Engineering fixtures, not independent retrieval evaluation."""
import csv
from dataclasses import replace

import pymupdf
import pytest

from oshc.policy_source import (
    CAPTURED_ON, SOURCE_SHA256, SOURCE_URL, PolicyChunk, PolicyCorpus,
    SourceError, _column_chunks, build_corpus, index_bytes, save_index,
)
from oshc.policy_search import PolicySearch


def manifest(root, **changes):
    folder = root / "corpus"
    folder.mkdir(exist_ok=True)
    row = {"URL": SOURCE_URL, "Capture Date": CAPTURED_ON, "SHA-256": SOURCE_SHA256}
    row.update(changes)
    with (folder / "MANIFEST.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=row)
        writer.writeheader()
        writer.writerow(row)
    return folder


def chunk(ident, text, page=17):
    return PolicyChunk(ident, page, "left", text, ((20.0, 80.0, 190.0, 120.0),))


def corpus(*chunks):
    return PolicyCorpus(tuple(chunks), "synthetic-test")


def test_source_hash_checked_before_pdf_parsing(tmp_path, monkeypatch):
    folder = manifest(tmp_path)
    (folder / "Medibank_OSHC_Member_Guide.pdf").write_bytes(b"unapproved PDF")
    monkeypatch.setattr(pymupdf, "open", lambda *a, **k: pytest.fail("Parsed unverified bytes"))
    with pytest.raises(SourceError, match="SHA-256"):
        build_corpus(tmp_path)


@pytest.mark.parametrize("change", [
    {"SHA-256": "0" * 64}, {"Capture Date": "2026-10-01"}, {"URL": "https://example.com"}
], ids=["wrong-hash", "wrong-capture", "wrong-url"])
def test_manifest_mismatch_stops_before_reading_pdf(tmp_path, change):
    manifest(tmp_path, **change)
    with pytest.raises(SourceError, match="manifest"):
        build_corpus(tmp_path)


def test_missing_pdf_has_actionable_error(tmp_path):
    manifest(tmp_path)
    with pytest.raises(SourceError, match="Missing source PDF"):
        build_corpus(tmp_path)


@pytest.mark.parametrize("separate_titles", [False, True], ids=["shared-title", "two-titles"])
def test_columns_and_titles_stay_separate(separate_titles):
    with pymupdf.open() as doc:
        page = doc.new_page(width=419.528, height=595.276)
        page.insert_text((20, 50), "Left title" if separate_titles else "Shared title", fontsize=19)
        if separate_titles:
            page.insert_text((215, 50), "Right title", fontsize=19)
        page.insert_text((20, 100), "LEFT condition\nLEFT continuation", fontsize=9)
        page.insert_text((215, 100), "RIGHT exclusion\nRIGHT continuation", fontsize=9)
        page.insert_text((250, 578), "OSHC Member Guide  |  17", fontsize=6)
        left, right = _column_chunks(page, 17)
    assert "LEFT condition\nLEFT continuation" in left.text
    assert "RIGHT exclusion\nRIGHT continuation" in right.text
    assert "RIGHT" not in left.text and "LEFT" not in right.text
    assert "OSHC Member Guide" not in left.text + right.text
    assert len(left.line_boxes) == len(left.text.splitlines())
    if separate_titles:
        assert "Left title" not in right.text and "Right title" not in left.text
    else:
        assert left.text.startswith("Shared title\n") and right.text.startswith("Shared title\n")


def test_unexpected_full_width_body_is_rejected():
    with pymupdf.open() as doc:
        page = doc.new_page(width=419.528, height=595.276)
        page.insert_text((150, 120), "Body crossing the centre gutter", fontsize=12)
        with pytest.raises(SourceError, match="crosses the column boundary"):
            _column_chunks(page, 17)


def test_saved_index_is_repeatable_and_never_overwrites_different_bytes(tmp_path):
    source = corpus(chunk("a", "invented source"))
    path = tmp_path / "index.json"
    save_index(source, path)
    assert path.read_bytes() == index_bytes(source)
    save_index(source, path)
    path.write_bytes(b"changed")
    with pytest.raises(SourceError, match="differs"):
        save_index(source, path)
    assert path.read_bytes() == b"changed"


@pytest.fixture
def index():
    return PolicySearch(corpus(
        chunk("b", "lunar sample"), chunk("a", "lunar sample"),
        chunk("c", "mars orbit"), chunk("d", "venus orbit"), chunk("e", "earth orbit")
    ))


def test_search_has_stable_ranking_and_source_bound_citations(index):
    hits = index.search("lunar", k=5)
    assert [hit.chunk_id for hit in hits] == ["a", "b"]
    assert [hit.rank for hit in hits] == [1, 2]
    assert all(hit.text == "lunar sample" for hit in hits)
    assert all(hit.source_url == SOURCE_URL + "#page=17" for hit in hits)
    assert all("PDF page 17, left column" == hit.section for hit in hits)
    assert all(hit.captured_on == CAPTURED_ON for hit in hits)
    assert hits == index.search("lunar lunar", k=5)


@pytest.mark.parametrize("query", ["", "the and to", "zzxxqqvv"], ids=["empty", "stopwords", "absent"])
def test_no_evidence_returns_no_hits(index, query):
    assert index.search(query) == []


@pytest.mark.parametrize("options", [
    {"query": "x" * 2001}, {"query": None}, {"query": "lunar", "k": 0},
    {"query": "lunar", "k": 21}, {"query": "lunar", "k": True},
], ids=["long-query", "non-text", "zero-k", "large-k", "boolean-k"])
def test_invalid_search_request_is_rejected(index, options):
    with pytest.raises(ValueError):
        index.search(**options)


def test_duplicate_chunk_ids_rejected():
    item = chunk("a", "invented source")
    with pytest.raises(ValueError, match="unique"):
        PolicySearch(corpus(item, replace(item, text="different text")))
