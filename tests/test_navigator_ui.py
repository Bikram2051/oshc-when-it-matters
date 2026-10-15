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
    text_by_topic = {
        "Making a claim": "Making a claim.\nSYNTHETIC CLAIM TEXT\nDirect billing",
        "Waiting periods": "Waiting periods.\nSYNTHETIC WAIT TEXT",
        "Membership card": "Membership card",
        "Direct billing": "Making a claim.\nSYNTHETIC CLAIM TEXT\nDirect billing",
        "Ambulance services": "Ambulance services",
        "Medicare Benefits Schedule": "Medicare Benefits Schedule",
        "GP services": "General practitioner.\nSYNTHETIC GP TEXT",
        "Medicines": "Prescription medicines.\nSYNTHETIC MEDICINES TEXT",
    }
    starts = {topic: (page, column, (text_by_topic[topic].splitlines()[0],))
              for topic, (page, column, _) in ui.TOPIC_STARTS.items()}
    chunks = {(page, column): PolicyChunk(f"test-{page}-{column}", page, column,
                                         text_by_topic[topic], ())
              for topic, (page, column, _) in starts.items()}
    # A strong passing mention must not displace the authored starting section.
    chunks[(4, "right")] = PolicyChunk("distractor", 4, "right", "Making a claim " * 20, ())
    corpus = PolicyCorpus(tuple(chunks.values()), "synthetic")
    monkeypatch.setattr(ui, "TOPIC_STARTS", starts)
    monkeypatch.setattr(ui, "build_corpus", Mock(return_value=corpus))
    yield path
    provider.assert_not_called()


def app():
    at = AppTest.from_file(str(ROOT / "app/Home.py"), default_timeout=15).run()
    at.switch_page("views/2_Navigator.py").run()
    assert not at.exception
    return at


def test_topic_switch_updates_excerpt_and_citation(sandbox):
    at = app()
    assert not at.chat_input and not at.text_input and not at.text_area
    assert any("SYNTHETIC CLAIM TEXT" in text.value for text in at.text)
    assert any("#page=28" in link.value for link in at.markdown)
    at.selectbox(key="nv_topic").select("Waiting periods").run()
    assert not at.exception
    assert any("SYNTHETIC WAIT TEXT" in text.value for text in at.text)
    assert not any("SYNTHETIC CLAIM TEXT" in text.value for text in at.text)
    assert any("#page=21" in link.value for link in at.markdown)
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
    assert not at.image and not at.get("download_button")
    assert not any(widget.key == "nv_topic" for widget in at.selectbox)
    assert not any("SYNTHETIC CLAIM TEXT" in text.value for text in at.text)


def test_manifest_failure_prevents_browsing(sandbox, monkeypatch):
    monkeypatch.setattr(ui, "build_corpus", Mock(side_effect=SourceError("manifest mismatch")))
    at = app()
    assert at.error and not at.image and not at.get("download_button")


@pytest.mark.parametrize("offline,live", [("1", "0"), ("0", "1")])
def test_verified_browsing_available_in_both_runtime_modes(sandbox, monkeypatch, offline, live):
    monkeypatch.setenv("OSHC_OFFLINE", offline)
    monkeypatch.setenv("OSHC_ENABLE_LIVE", live)
    at = app()
    ui.build_corpus.assert_called()
    assert not at.error and not at.exception
    assert at.selectbox(key="nv_topic") and at.get("download_button")
    assert any("SYNTHETIC CLAIM TEXT" in text.value for text in at.text)


@pytest.mark.parametrize("service,topic,expected", [
    ("GP appointment", "GP services", "SYNTHETIC GP TEXT"),
    ("Phone or video appointment", "GP services", "SYNTHETIC GP TEXT"),
    ("Pharmacy", "Medicines", "SYNTHETIC MEDICINES TEXT"),
    ("Making a claim", "Making a claim", "SYNTHETIC CLAIM TEXT"),
    ("Membership card", "Membership card", "Membership card"),
])
def test_service_selection_opens_related_guide_topic(sandbox, service, topic, expected):
    at = app()
    at.selectbox(key="nv_service").select(service).run()
    at.button(key="nv_related_topic").click().run()
    assert not at.exception and not at.error
    assert at.selectbox(key="nv_topic").value == topic
    assert any(expected in text.value for text in at.text)
    if service == "Phone or video appointment":
        assert any("no dedicated telehealth section" in text.value for text in at.caption)


def test_official_handoffs_have_fixed_urls_and_no_personal_input(sandbox):
    at = app()
    assert not at.text_input and not at.text_area and not at.chat_input
    urls = {button.url for button in at.get("link_button")}
    assert ui.SERVICE_FINDER_URL in urls
    assert ui.SYMPTOM_CHECKER_URL in urls
    assert all("?" not in url for url in urls)
    assert any("does not assess symptoms" in text.value for text in at.caption)


def test_source_failure_keeps_official_service_handoffs(sandbox, monkeypatch):
    monkeypatch.setattr(ui, "build_corpus", Mock(side_effect=SourceError("manifest mismatch")))
    at = app()
    assert at.error and not at.image and not at.get("download_button")
    urls = {button.url for button in at.get("link_button")}
    assert ui.SERVICE_FINDER_URL in urls and ui.SYMPTOM_CHECKER_URL in urls


def test_empty_related_search_keeps_verified_starting_section(sandbox, monkeypatch):
    at = app()
    monkeypatch.setattr(ui.PolicySearch, "search", lambda *args, **kwargs: [])
    at.run()
    assert not at.exception and not at.error
    assert at.image
    assert any("SYNTHETIC CLAIM TEXT" in text.value for text in at.text)
    assert len(at.get("download_button")) == 1


def test_passing_mention_cannot_replace_the_curated_claim_section(sandbox):
    at = app()
    assert at.selectbox(key="nv_match").value == "test-28-right"
    assert "distractor" in at.selectbox(key="nv_match").options or any(
        "Related" in option for option in at.selectbox(key="nv_match").options)
    assert any("Start here" in option for option in at.selectbox(key="nv_match").options)


def test_existing_session_resets_old_default_to_curated_start(sandbox):
    at = app()
    at.selectbox(key="nv_match").select("distractor").run()
    assert not any("SYNTHETIC CLAIM TEXT" in text.value for text in at.text)
    at.session_state["nv_starting_section"] = None
    at.run()
    assert not at.exception
    assert at.selectbox(key="nv_match").value == "test-28-right"
    assert any("SYNTHETIC CLAIM TEXT" in text.value for text in at.text)


def test_missing_starting_anchor_hides_topic_excerpt(sandbox, monkeypatch):
    starts = dict(ui.TOPIC_STARTS)
    starts["Making a claim"] = (28, "right", ("MISSING SUPPORTING TEXT",))
    monkeypatch.setattr(ui, "TOPIC_STARTS", starts)
    at = app()
    assert at.error and not at.image
    assert not any("SYNTHETIC CLAIM TEXT" in text.value for text in at.text)


def test_every_fixed_topic_has_a_verified_starting_column():
    assert set(ui.TOPIC_STARTS) == set(ui.TOPICS)
    assert {topic: value[:2] for topic, value in ui.TOPIC_STARTS.items()} == {
        "Making a claim": (28, "right"), "Waiting periods": (21, "right"),
        "Membership card": (8, "left"), "Direct billing": (28, "right"),
        "Ambulance services": (25, "left"), "Medicare Benefits Schedule": (17, "left"),
        "GP services": (17, "right"), "Medicines": (24, "left"),
    }


@pytest.mark.parametrize("number", [0, 38, True], ids=["zero", "too-large", "bool"])
def test_page_bounds_are_rejected(sandbox, number):
    with pytest.raises(SourceError):
        ui.page_png(sandbox.read_bytes(), number)


def test_preview_is_a_real_png(sandbox):
    assert ui.page_png(sandbox.read_bytes(), 19).startswith(b"\x89PNG\r\n\x1a\n")
