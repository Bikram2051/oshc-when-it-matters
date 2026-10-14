"""Ask page checks on a synthetic guide. No publisher text, no held-out probes, no provider.

The properties worth defending here are not "does it return something". They are:
  - the boundary filter runs before any retrieval, on every question
  - an advice or clinical refusal shows no source excerpt at all
  - no sentence is composed; oshc.composer is never reachable from this page
  - the question text never leaves the session
"""
import hashlib
from pathlib import Path
from unittest.mock import Mock

import pymupdf
import pytest
from streamlit.testing.v1 import AppTest

import oshc.ask_ui as ui
import oshc.llm as adapter
import oshc.navigator_ui as navigator
from oshc.policy_source import PolicyChunk, PolicyCorpus, SourceError

ROOT = Path(__file__).resolve().parents[1]

PAGES = {
    21: "Waiting periods.\nSYNTHETIC WAITING TEXT",
    25: "Ambulance services.\nSYNTHETIC AMBULANCE TEXT",
    28: "Making a claim.\nSYNTHETIC CLAIM TEXT",
}


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("OSHC_OFFLINE", "1")
    monkeypatch.setenv("OSHC_ENABLE_LIVE", "0")
    provider = Mock(side_effect=AssertionError("Unexpected provider access"))
    monkeypatch.setattr(adapter, "_client", provider)
    composer = Mock(side_effect=AssertionError("The composer must not be reachable"))
    monkeypatch.setattr("oshc.composer.compose", composer, raising=False)
    monkeypatch.setattr(ui, "ROOT", tmp_path)
    monkeypatch.setattr(navigator, "ROOT", tmp_path)
    with pymupdf.open() as document:
        for number in range(1, 38):
            page = document.new_page(width=420, height=595)
            page.insert_text((25, 35), f"SYNTHETIC PAGE {number}")
        raw = document.tobytes()
    path = tmp_path / "corpus" / navigator.SOURCE_DOC
    path.parent.mkdir()
    path.write_bytes(raw)
    monkeypatch.setattr(navigator, "SOURCE_SHA256", hashlib.sha256(raw).hexdigest())
    corpus = PolicyCorpus(
        tuple(PolicyChunk(f"test-p{page}", page, "left", text, ())
              for page, text in PAGES.items()), "synthetic")
    monkeypatch.setattr(navigator, "build_corpus", Mock(return_value=corpus))
    yield path
    provider.assert_not_called()
    composer.assert_not_called()


def app():
    at = AppTest.from_file(str(ROOT / "app/Home.py"), default_timeout=30).run()
    at.switch_page("pages/4_Ask.py").run()
    assert not at.exception
    return at


def ask(at, question):
    at.text_input(key="ask_box").set_value(question).run()
    assert not at.exception
    return at


def body(at):
    """Everything the page rendered as text, excerpt bodies included."""
    return " ".join([item.value for item in at.text]
                    + [item.value for item in at.markdown]
                    + [item.value for item in at.caption]
                    + [item.value for item in at.success]
                    + [item.value for item in at.error]
                    + [item.value for item in at.warning])


def test_allowed_question_returns_source_excerpts(sandbox):
    at = ask(app(), "when does a waiting period apply")
    assert at.success and not at.error
    assert "SYNTHETIC WAITING TEXT" in body(at)
    assert any("#page=21" in item.value for item in at.markdown)


@pytest.mark.parametrize("question", [
    "am I covered for physio",
    "how much will I get back on this",
])
def test_advice_question_shows_no_excerpt(sandbox, question):
    at = ask(app(), question)
    assert at.error and not at.success
    rendered = body(at)
    assert not any(f"SYNTHETIC {word} TEXT" in rendered
                   for word in ("WAITING", "AMBULANCE", "CLAIM"))
    assert "Medibank confirms" in rendered


@pytest.mark.parametrize("question", [
    "I have a sore throat and fever",
    "what is wrong with me",
])
def test_clinical_question_shows_no_excerpt(sandbox, question):
    at = ask(app(), question)
    assert at.error and not at.success
    assert "SYNTHETIC" not in body(at).replace("SYNTHETIC PAGE", "")
    assert "healthdirect" in body(at)


def test_emergency_escalates_before_any_source_is_offered(sandbox):
    at = ask(app(), "when is ambulance treatment covered")
    assert at.error and not at.success
    rendered = body(at)
    # The escalation is unconditional and comes first.
    assert "call 000 now" in rendered
    # The general-information follow-up is offered, but only inside an expander
    # the reader has to open, and clearly labelled as not emergency help.
    assert any("asking how this is covered" in item.label for item in at.expander)


def test_no_question_asked_shows_no_results(sandbox):
    at = app()
    assert not at.success and not at.error and not at.warning
    assert "SYNTHETIC AMBULANCE TEXT" not in body(at)


def test_unmatched_question_warns_rather_than_guessing(sandbox):
    at = ask(app(), "zzqqxx nothing in the guide says this")
    assert at.warning and not at.success
    assert "SYNTHETIC CLAIM TEXT" not in body(at)


def test_starter_question_populates_the_box_and_runs(sandbox):
    at = app()
    starter = next(button for button in at.button if button.label == ui.STARTERS[1])
    starter.click().run()
    assert not at.exception
    assert at.text_input(key="ask_box").value == ui.STARTERS[1]
    assert at.success or at.warning


def test_question_is_truncated_not_unbounded(sandbox):
    at = ask(app(), "waiting period " * 400)
    assert not at.exception
    assert at.text_input(key="ask_box").max_chars == ui.MAX_QUESTION_CHARS


def test_offline_flags_are_checked_before_the_source_is_read(sandbox, monkeypatch):
    monkeypatch.setenv("OSHC_OFFLINE", "0")
    at = app()
    navigator.build_corpus.assert_not_called()
    assert at.error and not at.text_input


def test_changed_source_blocks_the_page(sandbox):
    at = app()
    sandbox.write_bytes(b"changed source")
    at.run()
    assert not at.exception and at.error
    assert not at.text_input


def test_source_failure_blocks_the_page(sandbox, monkeypatch):
    monkeypatch.setattr(navigator, "build_corpus",
                        Mock(side_effect=SourceError("manifest mismatch")))
    at = app()
    assert at.error and not at.text_input


def test_page_number_is_parsed_from_the_section_label(sandbox):
    class Hit:
        section = "PDF page 28, right column"

    class Broken:
        section = None

    assert ui._page_of(Hit()) == 28
    assert ui._page_of(Broken()) == 0


def test_session_counters_hold_no_question_text(sandbox):
    at = ask(app(), "when does a waiting period apply")
    assert at.session_state["ask_answered"] == 1
    leaked = [key for key in ui.SESSION_KEYS
              if isinstance(at.session_state.get(key), str)]
    assert not leaked, f"question text may be held in {leaked}"
    assert at.session_state["ask_box"] == "when does a waiting period apply"
