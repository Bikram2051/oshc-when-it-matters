"""Session behaviour and boundary ordering; synthetic text, no providers."""
from pathlib import Path
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

import oshc.ask_ui as ui
from oshc import llm
from oshc.policy_source import PolicyChunk, PolicyCorpus, SourceError

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def source(monkeypatch):
    monkeypatch.setattr("oshc.student_chat.CURATED_CARDS", {})
    monkeypatch.setenv("OSHC_OFFLINE", "1")
    monkeypatch.setenv("OSHC_ENABLE_LIVE", "0")
    corpus = PolicyCorpus((
        PolicyChunk("waiting", 21, "left", "Waiting periods. SYNTHETIC WAITING TEXT", ()),
        PolicyChunk("claims", 28, "right", "Making a claim. SYNTHETIC CLAIM TEXT", ()),
        PolicyChunk("card", 8, "left", "Membership card. SYNTHETIC CARD TEXT", ()),
    ), "synthetic")
    loader = Mock(return_value=(corpus, b"synthetic source"))
    monkeypatch.setattr(ui, "load_source", loader)
    monkeypatch.setattr(ui, "_history_source_valid", lambda: True)
    provider = Mock(side_effect=AssertionError("No provider may be used"))
    monkeypatch.setattr(llm, "_client", provider)
    composer = Mock(side_effect=AssertionError("No generated answers"))
    monkeypatch.setattr("oshc.composer.compose", composer)
    yield loader
    provider.assert_not_called()
    composer.assert_not_called()


def app():
    at = AppTest.from_file(str(ROOT / "app/Home.py"), default_timeout=30).run()
    at.switch_page("views/4_Ask.py").run()
    assert not at.exception
    return at


def submit(at, question):
    at.chat_input(key="ask_box").set_value(question).run()
    assert not at.exception
    return at


def text(at):
    return " ".join(str(item.value) for kind in ("text", "markdown", "caption", "error", "warning")
                    for item in at.get(kind))


def test_empty_chat_never_reads_source(source):
    at = app()
    source.assert_not_called()
    assert at.chat_input and not at.get("chat_message")


def test_transcript_survives_rerun_and_counts_only_submissions(source):
    at = submit(app(), "What are waiting periods?")
    assert "SYNTHETIC WAITING TEXT" in text(at)
    assert len(at.session_state["ask_history"]) == 1
    calls = source.call_count
    at.run()
    assert not at.exception
    assert len(at.session_state["ask_history"]) == 1
    assert source.call_count == calls
    submit(at, "How do I make a claim?")
    assert len(at.session_state["ask_history"]) == 2
    assert "SYNTHETIC CLAIM TEXT" in text(at)


@pytest.mark.parametrize("question", [
    "I have chest pain", "am I covered for physio", "what is wrong with me",
])
def test_blocked_message_never_reads_source_even_when_unavailable(source, question):
    source.side_effect = SourceError("missing guide")
    at = submit(app(), question)
    source.assert_not_called()
    assert at.error
    assert "SYNTHETIC" not in text(at)
    assert not any("covered, rather" in item.label for item in at.expander)


def test_clear_chat_removes_transcript(source):
    at = submit(app(), "What are waiting periods?")
    at.button(key="ask_clear").click().run()
    assert not at.exception
    assert at.session_state["ask_history"] == []
    assert "SYNTHETIC WAITING TEXT" not in text(at)


def test_source_failure_is_a_visible_abstention(source):
    source.side_effect = SourceError("missing guide")
    at = submit(app(), "What are waiting periods?")
    assert at.error or at.warning
    assert "SYNTHETIC" not in text(at)


def test_starters_use_same_submission_path(source):
    at = app()
    at.button(key="ask_s1").click().run()
    assert not at.exception
    assert len(at.session_state["ask_history"]) == 1
    assert source.called


def test_changed_source_hides_saved_excerpts(source, monkeypatch):
    at = submit(app(), "What are waiting periods?")
    monkeypatch.setattr(ui, "_history_source_valid", lambda: False)
    at.run()
    assert not at.exception
    assert "SYNTHETIC WAITING TEXT" not in text(at)
    assert at.warning


def test_offline_flags_disable_question_box_before_source_access(source, monkeypatch):
    monkeypatch.setenv("OSHC_ENABLE_LIVE", "1")
    at = app()
    source.assert_not_called()
    assert at.error and not at.chat_input


def test_plain_entrypoint_defaults_to_live_chat_without_source_access(source, monkeypatch):
    monkeypatch.delenv("OSHC_OFFLINE", raising=False)
    monkeypatch.delenv("OSHC_ENABLE_LIVE", raising=False)
    monkeypatch.delenv("OSHC_MODEL", raising=False)
    monkeypatch.setattr(ui, "api_key_configured", lambda: False)
    at = app()
    source.assert_not_called()
    assert at.chat_input and not at.error
    assert "Haiku is not connected yet" in text(at)


def test_live_custom_answer_is_checked_once_and_survives_rerun(source, monkeypatch):
    from dataclasses import replace
    from oshc.student_chat import answer_question
    response = answer_question("How do I make a claim?", source_loader=lambda: source.return_value[0])
    response = replace(response, answer="Use the member account. [1]", answer_title="Your answer",
                       answer_id="haiku-grounded", response_mode="haiku")
    live = Mock(return_value=response)
    monkeypatch.setattr("oshc.live_chat.answer_live", live)
    monkeypatch.setattr(ui, "api_key_configured", lambda: True)
    monkeypatch.setenv("OSHC_OFFLINE", "0")
    monkeypatch.setenv("OSHC_ENABLE_LIVE", "1")
    at = submit(app(), "Could you walk me through making a claim online?")
    assert "Use the member account" in text(at) and "input and output checked" in text(at)
    assert len(at.session_state["ask_history"]) == 1
    at.run()
    assert live.call_count == 1
    at.button(key="ask_clear").click().run()
    assert at.session_state["ask_history"] == []


def test_clarification_does_not_claim_a_privacy_rejection(source):
    at = submit(app(), "and for me?")
    assert "[Question not retained]" in text(at)
    assert "withheld for privacy" not in text(at)


def test_private_question_not_retained_in_transcript(source):
    at = submit(app(), "My membership number is 123456789, how do I claim?")
    source.assert_not_called()
    assert "123456789" not in repr(at.session_state["ask_history"])
    assert "123456789" not in text(at)


def test_history_is_bounded_and_clearing_does_not_repeat_submission(source):
    at = app()
    for _ in range(ui.MAX_TURNS + 1):
        submit(at, "What are waiting periods?")
    assert len(at.session_state["ask_history"]) == ui.MAX_TURNS
    calls = source.call_count
    at.button(key="ask_clear").click().run()
    at.run()
    assert not at.exception
    assert at.session_state["ask_history"] == [] and source.call_count == calls


def test_source_page_number_parser():
    class Hit:
        section = "PDF page 28, right column"

    assert ui._page_of(Hit()) == 28
    assert ui._page_of(None) == 0
