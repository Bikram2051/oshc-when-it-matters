"""Synthetic download tests; never access the network or modify frozen sources."""
import hashlib
import io
import urllib.request
from dataclasses import replace

import pytest

from scripts import bootstrap_sources as bootstrap


PAYLOAD = b"synthetic frozen public source\n"


def source():
    return replace(bootstrap.SOURCES[0], sha256=hashlib.sha256(PAYLOAD).hexdigest())


class Response(io.BytesIO):
    def __init__(self, payload=PAYLOAD, *, url=bootstrap.GUIDE_URL, length=None):
        super().__init__(payload)
        self.url = url
        self.headers = {} if length is None else {"Content-Length": length}

    def geturl(self):
        return self.url


def test_verified_download_is_published_and_temporary_file_is_removed(tmp_path, monkeypatch):
    monkeypatch.setattr(bootstrap, "_open", lambda url: Response())
    assert bootstrap.ensure_source(source(), tmp_path) == "downloaded and verified"
    assert (tmp_path / source().filename).read_bytes() == PAYLOAD
    assert list(tmp_path.iterdir()) == [tmp_path / source().filename]


def test_failed_hash_never_publishes_any_file(tmp_path, monkeypatch):
    monkeypatch.setattr(bootstrap, "_open", lambda url: Response(b"changed upstream source"))
    with pytest.raises(bootstrap.SourceBootstrapError, match="Restore the frozen"):
        bootstrap.ensure_source(source(), tmp_path)
    assert not list(tmp_path.iterdir())


def test_existing_correct_source_skips_network(tmp_path, monkeypatch):
    destination = tmp_path / source().filename
    destination.write_bytes(PAYLOAD)
    monkeypatch.setattr(bootstrap, "_open", lambda url: pytest.fail("unexpected network request"))
    assert bootstrap.ensure_source(source(), tmp_path) == "verified"
    assert bootstrap.ensure_source(source(), tmp_path, check=True) == "verified"
    assert destination.read_bytes() == PAYLOAD


def test_existing_changed_source_is_not_overwritten(tmp_path, monkeypatch):
    destination = tmp_path / source().filename
    destination.write_bytes(b"keep existing file")
    monkeypatch.setattr(bootstrap, "_open", lambda url: pytest.fail("unexpected network request"))
    with pytest.raises(bootstrap.SourceBootstrapError, match="not overwritten"):
        bootstrap.ensure_source(source(), tmp_path)
    assert destination.read_bytes() == b"keep existing file"


def test_check_missing_source_is_actionable_and_never_downloads(tmp_path, monkeypatch):
    monkeypatch.setattr(bootstrap, "_open", lambda url: pytest.fail("unexpected network request"))
    with pytest.raises(bootstrap.SourceBootstrapError, match="bootstrap_sources.py --check"):
        bootstrap.ensure_source(source(), tmp_path, check=True)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("url", [
    "http://www.medibankoshc.com.au/guide.pdf",
    "https://example.com/guide.pdf",
    "https://www.medibankoshc.com.au.evil.example/guide.pdf",
    "https://user:password@www.medibankoshc.com.au/guide.pdf",
    "https://www.mbsonline.gov.au:8080/data.xml",
])
def test_unsafe_redirect_is_rejected_before_following(url):
    request = urllib.request.Request(bootstrap.GUIDE_URL)
    with pytest.raises(bootstrap.SourceBootstrapError, match="approved HTTPS"):
        bootstrap.OfficialRedirectHandler().redirect_request(request, None, 302, "Found", {}, url)


def test_unapproved_final_url_leaves_no_published_file(tmp_path, monkeypatch):
    monkeypatch.setattr(bootstrap, "_open", lambda url: Response(url="https://example.com/file"))
    with pytest.raises(bootstrap.SourceBootstrapError):
        bootstrap.ensure_source(source(), tmp_path)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("length", [None, "1000000000"])
def test_size_limit_is_enforced_before_publication(tmp_path, monkeypatch, length):
    monkeypatch.setattr(bootstrap, "MAX_DOWNLOAD_BYTES", 8)
    monkeypatch.setattr(bootstrap, "_open", lambda url: Response(length=length))
    with pytest.raises(bootstrap.SourceBootstrapError):
        bootstrap.ensure_source(source(), tmp_path)
    assert not list(tmp_path.iterdir())


def test_destination_created_during_download_is_preserved(tmp_path, monkeypatch):
    destination = tmp_path / source().filename

    def open_after_race(url):
        destination.write_bytes(b"another process owns this file")
        return Response()

    monkeypatch.setattr(bootstrap, "_open", open_after_race)
    with pytest.raises(bootstrap.SourceBootstrapError):
        bootstrap.ensure_source(source(), tmp_path)
    assert destination.read_bytes() == b"another process owns this file"
    assert list(tmp_path.iterdir()) == [destination]


def test_manifest_must_match_application_pins(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    manifest = corpus / "MANIFEST.csv"
    rows = ["URL,SHA-256"] + [f"{item.manifest_url},{item.sha256}" for item in bootstrap.SOURCES]
    manifest.write_text("\n".join(rows) + "\n", encoding="utf-8")
    assert bootstrap.load_sources(tmp_path) == bootstrap.SOURCES
    assert bootstrap.load_sources(tmp_path, guide_only=True) == bootstrap.SOURCES[:1]
    manifest.write_text("\n".join(rows).replace(bootstrap.SOURCES[0].sha256, "0" * 64), encoding="utf-8")
    with pytest.raises(bootstrap.SourceBootstrapError, match="manifest does not match"):
        bootstrap.load_sources(tmp_path)
