"""Behaviour checks using synthetic lesson sources and a synthetic PDF."""
from pathlib import Path
from unittest.mock import Mock

import pymupdf
import pytest
from streamlit.testing.v1 import AppTest

import oshc.coach_lessons as lessons
import oshc.coach_ui as ui
import oshc.llm as adapter
import oshc.navigator_ui as navigator
from oshc.policy_source import PolicyChunk, PolicyCorpus, SourceError

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("OSHC_OFFLINE", "1")
    monkeypatch.setenv("OSHC_ENABLE_LIVE", "0")
    provider = Mock(side_effect=AssertionError("Unexpected provider access"))
    monkeypatch.setattr(adapter, "_client", provider)
    chunks = tuple(PolicyChunk(item.ident, item.page, item.column,
                               "\n".join(item.anchors), ()) for item in lessons.LESSONS)
    corpus = PolicyCorpus(chunks, "synthetic")
    source = Mock(return_value=corpus)
    monkeypatch.setattr(lessons, "build_corpus", source)
    monkeypatch.setattr(ui, "ROOT", tmp_path)
    with pymupdf.open() as document:
        for number in range(1, 38):
            document.new_page(width=420, height=595).insert_text((25, 35), f"TEST PAGE {number}")
        raw = document.tobytes()
    monkeypatch.setattr(navigator, "load_source", Mock(return_value=(corpus, raw)))
    yield source
    provider.assert_not_called()


def app():
    at = AppTest.from_file(str(ROOT / "app/Home.py"), default_timeout=15).run()
    at.switch_page("pages/1_Journey_Coach.py").run()
    assert not at.exception
    return at


def answer(at, option):
    at.radio(key="jc_choice").set_value(option).run()
    at.button(key="jc_check").click().run()
    assert not at.exception


def test_no_automatic_answer_or_completion(sandbox):
    at = app()
    assert at.radio(key="jc_choice").value is None
    assert at.button(key="jc_check").disabled
    assert not at.success and not at.warning
    assert "jc_progress" not in at.session_state


def test_retry_preserves_first_attempt_and_rerun_does_not_add_attempts(sandbox):
    at = app()
    lesson = lessons.LESSONS[0]
    answer(at, lesson.options[0])
    assert at.warning
    answer(at, lesson.options[lesson.correct])
    assert at.success
    record = dict(at.session_state["jc_progress"][lesson.ident])
    assert record == {"first": 0, "last": 1, "attempts": 2, "passed": True}
    at.run()
    assert at.session_state["jc_progress"][lesson.ident] == record


def test_topic_change_clears_stale_feedback_but_keeps_progress(sandbox):
    at = app()
    first, second = lessons.LESSONS[:2]
    answer(at, first.options[first.correct])
    at.selectbox(key="jc_moment").select(second.moment).run()
    assert not at.success and not at.warning
    assert at.radio(key="jc_choice").value is None
    answer(at, second.options[second.correct])
    assert len(at.session_state["jc_progress"]) == 2
    at.selectbox(key="jc_moment").select(first.moment).run()
    assert at.session_state["jc_progress"][first.ident]["passed"]
    assert not at.success


def test_reset_clears_practice(sandbox):
    at = app()
    answer(at, lessons.LESSONS[0].options[1])
    at.button(key="jc_reset").click().run()
    assert not at.exception and not at.success
    assert "jc_progress" not in at.session_state
    assert at.radio(key="jc_choice").value is None


def test_invalid_source_hides_previously_shown_lesson(sandbox):
    at = app()
    sandbox.side_effect = SourceError("changed source")
    at.run()
    assert not at.exception and at.error
    assert not at.radio and not at.selectbox and not at.button


@pytest.mark.parametrize("name,value", [("OSHC_OFFLINE", "0"), ("OSHC_ENABLE_LIVE", "1")])
def test_offline_flags_checked_before_loading(sandbox, monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    at = app()
    sandbox.assert_not_called()
    assert at.error and not at.radio


def test_missing_supporting_span_is_rejected(sandbox):
    sandbox.return_value = PolicyCorpus((PolicyChunk("unrelated", 8, "left", "Unrelated text", ()),), "test")
    with pytest.raises(SourceError):
        lessons.verified_sources(ROOT)


def test_original_page_navigation_preserves_practice(sandbox):
    at = app()
    lesson = lessons.LESSONS[2]
    at.selectbox(key="jc_moment").select(lesson.moment).run()
    answer(at, lesson.options[lesson.correct])
    at.button(key="jc_source").click().run()
    assert not at.exception and not at.error
    assert at.title[0].value == "Navigator"
    assert at.number_input(key="nv_page").value == 28
    at.switch_page("pages/1_Journey_Coach.py").run()
    assert at.session_state["jc_progress"][lesson.ident]["passed"]


def test_new_session_has_no_previous_progress(sandbox):
    first = app()
    answer(first, lessons.LESSONS[0].options[1])
    second = app()
    assert "jc_progress" not in second.session_state
