"""Synthetic UI checks; no publisher text, held-out prompts or provider calls."""
import hashlib
from pathlib import Path
from unittest.mock import Mock

import pymupdf
import pytest
from streamlit.testing.v1 import AppTest

import oshc.llm as adapter
import oshc.navigator_ui as ui
from oshc.policy_source import PolicyChunk, PolicyCorpus, SourceError

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("OSHC_OFFLINE", "1")
    monkeypatch.setenv("OSHC_ENABLE_LIVE", "0")
    provider = Mock(side_effect=AssertionError("Unexpected provider access"))
    monkeypatch.setattr(adapter, "_client", provider)
    monkeypatch.setattr(ui, "ROOT", tmp_path)
    with pymupdf.open() as document:
        for number in range(1, 38):
            page = document.new_page(width=420, height=595)
            page.insert_text((25, 35), f"SYNTHETIC PAGE {number}")
        raw = document.tobytes()
    path = tmp_path / "corpus" / ui.SOURCE_DOC
    path.parent.mkdir()
    path.write_bytes(raw)
    monkeypatch.setattr(ui, "SOURCE_SHA256", hashlib.sha256(raw).hexdigest())
    texts = ["Making a claim.\nSYNTHETIC CLAIM TEXT", "Waiting periods.\nSYNTHETIC WAIT TEXT",
             "Membership card", "Direct billing", "Ambulance services", "Medicare Benefits Schedule"]
    corpus = PolicyCorpus(tuple(PolicyChunk(f"test-{i}", i + 3, "left", text, ())
                                for i, text in enumerate(texts)), "synthetic")
    monkeypatch.setattr(ui, "build_corpus", Mock(return_value=corpus))
    yield path
    provider.assert_not_called()


def app():
    at = AppTest.from_file(str(ROOT / "app/Home.py"), default_timeout=15).run()
    at.switch_page("pages/2_Navigator.py").run()
    assert not at.exception
    return at


def test_topic_switch_updates_excerpt_and_citation(sandbox):
    at = app()
    assert not at.chat_input and not at.text_input and not at.text_area
    assert any("SYNTHETIC CLAIM TEXT" in text.value for text in at.text)
    assert any("#page=3" in link.value for link in at.markdown)
    at.selectbox(key="nv_topic").select("Waiting periods").run()
    assert not at.exception
    assert any("SYNTHETIC WAIT TEXT" in text.value for text in at.text)
    assert not any("SYNTHETIC CLAIM TEXT" in text.value for text in at.text)
    assert any("#page=4" in link.value for link in at.markdown)
    assert len(at.image) == 1 and len(at.get("download_button")) == 1


def test_original_table_and_adjacent_page_are_accessible(sandbox):
    at = app()
    at.radio(key="nv_view").set_value(ui.PAGE_VIEW).run()
    assert at.number_input(key="nv_page").value == 19
    assert not any("SYNTHETIC CLAIM TEXT" in text.value for text in at.text)
    assert any("#page=19" in link.value for link in at.markdown)
    at.number_input(key="nv_page").set_value(20).run()
    assert not at.exception
    assert any("#page=20" in link.value for link in at.markdown)
    assert len(at.image) == 1


def test_source_change_removes_previously_displayed_content(sandbox):
    at = app()
    sandbox.write_bytes(b"changed source")
    at.run()
    assert not at.exception and at.error
    assert not at.image and not at.get("download_button") and not at.selectbox
    assert not any("SYNTHETIC CLAIM TEXT" in text.value for text in at.text)


def test_manifest_failure_prevents_browsing(sandbox, monkeypatch):
    monkeypatch.setattr(ui, "build_corpus", Mock(side_effect=SourceError("manifest mismatch")))
    at = app()
    assert at.error and not at.image and not at.get("download_button")


@pytest.mark.parametrize("name,value", [("OSHC_OFFLINE", "0"), ("OSHC_ENABLE_LIVE", "1")])
def test_offline_flags_checked_before_source_read(sandbox, monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    at = app()
    ui.build_corpus.assert_not_called()
    assert at.error and not at.selectbox and not at.get("download_button")


def test_empty_search_does_not_show_an_old_excerpt(sandbox, monkeypatch):
    at = app()
    monkeypatch.setattr(ui.PolicySearch, "search", lambda *args, **kwargs: [])
    at.run()
    assert not at.exception and at.warning
    assert not at.image
    assert not any("SYNTHETIC CLAIM TEXT" in text.value for text in at.text)
    assert len(at.get("download_button")) == 1


@pytest.mark.parametrize("number", [0, 38, True], ids=["zero", "too-large", "bool"])
def test_page_bounds_are_rejected(sandbox, number):
    with pytest.raises(SourceError):
        ui.page_png(sandbox.read_bytes(), number)


def test_preview_is_a_real_png(sandbox):
    assert ui.page_png(sandbox.read_bytes(), 19).startswith(b"\x89PNG\r\n\x1a\n")
