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


@pytest.fixture(params=[("1", "0"), ("0", "1")], ids=["source-mode", "live-mode"])
def sandbox(tmp_path, monkeypatch, request):
    offline, live = request.param
    monkeypatch.setenv("OSHC_OFFLINE", offline)
    monkeypatch.setenv("OSHC_ENABLE_LIVE", live)
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
    at.switch_page("views/1_Journey_Coach.py").run()
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


def test_checklist_is_saved_and_reset_without_identity(sandbox):
    at = app()
    lesson = lessons.LESSONS[0]
    # One vertical flow, no tabs: the lesson, then Try it, then Keep a next step.
    assert not at.tabs
    assert [item.value for item in at.header] == [lesson.title]
    assert [item.value for item in at.subheader] == ["Try it", "Keep a next step"]
    for index in range(len(lessons.ACTIVITIES[lesson.ident].checklist)):
        at.checkbox(key=f"jc_task_{lesson.ident}_{index}").check()
    at.button(key="jc_save_checklist").click().run()
    assert all(at.session_state["jc_checklists"][lesson.ident])
    at.button(key="jc_next").click().run()
    assert at.segmented_control(key="jc_moment").value == lessons.LESSONS[1].moment
    at.button(key="jc_reset").click().run()
    assert not at.exception and "jc_checklists" not in at.session_state


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
    at.segmented_control(key="jc_moment").select(second.moment).run()
    assert not at.success and not at.warning
    assert at.radio(key="jc_choice").value is None
    answer(at, second.options[second.correct])
    assert len(at.session_state["jc_progress"]) == 2
    at.segmented_control(key="jc_moment").select(first.moment).run()
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


def test_lessons_are_available_in_both_runtime_modes(sandbox):
    at = app()
    assert sandbox.called
    assert not at.error and at.radio
    assert any("No lesson or checklist details are sent" in item.value for item in at.caption)


def test_resume_chooses_first_unfinished_moment(sandbox):
    at = app()
    first = lessons.LESSONS[0]
    answer(at, first.options[first.correct])
    for index in range(len(lessons.ACTIVITIES[first.ident].checklist)):
        at.checkbox(key=f"jc_task_{first.ident}_{index}").check()
    at.button(key="jc_save_checklist").click().run()
    assert any("This moment is complete" in item.value for item in at.success)
    at.button(key="jc_resume").click().run()
    assert not at.exception
    assert at.segmented_control(key="jc_moment").value == lessons.LESSONS[1].moment
    assert at.radio(key="jc_choice").value is None


def test_saved_checklist_returns_after_switching_moments(sandbox):
    at = app()
    first = lessons.LESSONS[0]
    at.checkbox(key=f"jc_task_{first.ident}_0").check()
    at.button(key="jc_save_checklist").click().run()
    at.button(key="jc_next").click().run()
    at.button(key="jc_previous").click().run()
    assert at.checkbox(key=f"jc_task_{first.ident}_0").value is True
    assert at.checkbox(key=f"jc_task_{first.ident}_1").value is False


def test_full_journey_completion_and_reset(sandbox):
    at = app()
    for lesson in lessons.LESSONS:
        at.segmented_control(key="jc_moment").select(lesson.moment).run()
        answer(at, lesson.options[lesson.correct])
        for index in range(len(lessons.ACTIVITIES[lesson.ident].checklist)):
            at.checkbox(key=f"jc_task_{lesson.ident}_{index}").check()
        at.button(key="jc_save_checklist").click().run()
    assert not at.exception
    assert any("Your three preparation moments are complete" in item.value for item in at.success)
    assert at.button(key="jc_resume").disabled
    at.button(key="jc_reset").click().run()
    assert not at.exception and not at.success
    assert "jc_progress" not in at.session_state
    assert "jc_checklists" not in at.session_state
    assert at.segmented_control(key="jc_moment").value == lessons.LESSONS[0].moment


def test_missing_supporting_span_is_rejected(sandbox):
    sandbox.return_value = PolicyCorpus((PolicyChunk("unrelated", 8, "left", "Unrelated text", ()),), "test")
    with pytest.raises(SourceError):
        lessons.verified_sources(ROOT)


def test_original_page_navigation_preserves_practice(sandbox):
    at = app()
    lesson = lessons.LESSONS[2]
    at.segmented_control(key="jc_moment").select(lesson.moment).run()
    answer(at, lesson.options[lesson.correct])
    at.button(key="jc_source").click().run()
    assert not at.exception and not at.error
    assert at.title[0].value == "Navigator"
    assert at.number_input(key="nv_page").value == 28
    at.switch_page("views/1_Journey_Coach.py").run()
    assert at.session_state["jc_progress"][lesson.ident]["passed"]


def test_new_session_has_no_previous_progress(sandbox):
    first = app()
    answer(first, lessons.LESSONS[0].options[1])
    second = app()
    assert "jc_progress" not in second.session_state


def test_hindi_toggle_changes_interface_labels_only(sandbox):
    at = app()
    english_points = [item.value for item in at.markdown]
    at.selectbox(key="coach_language").set_value("hi").run()
    assert not at.exception
    assert at.button(key="jc_check").label == "मेरा उत्तर जाँचें"
    assert any("Lessons and sources stay in English" in item.value for item in at.caption)
    assert [item.value for item in at.markdown] == english_points


def test_practice_records_events_without_content(sandbox, isolated_events):
    import sqlite3
    at = app()
    lesson = lessons.LESSONS[0]
    answer(at, lesson.options[lesson.correct])
    answer(at, lesson.options[lesson.correct])
    with sqlite3.connect(isolated_events) as db:
        names = [row[0] for row in db.execute("SELECT name FROM events WHERE page='coach'")]
        text = db.execute("SELECT code, detail FROM events").fetchall()
    assert names.count("open") == 1
    assert names.count("scenario_start") == 1
    assert names.count("scenario_complete") == 1
    assert all(row == (None, None) for row in text)


@pytest.mark.parametrize("slug,index", [("before-you-arrive", 0), ("settling-in", 1),
                                        ("before-an-appointment", 2)])
def test_deep_link_opens_the_named_moment_once(sandbox, slug, index):
    at = AppTest.from_file(str(ROOT / "app/Home.py"), default_timeout=15)
    at.query_params["moment"] = slug
    at.run()
    at.switch_page("views/1_Journey_Coach.py").run()
    assert not at.exception
    assert at.segmented_control(key="jc_moment").value == lessons.LESSONS[index].moment
    other = lessons.LESSONS[(index + 1) % len(lessons.LESSONS)]
    at.segmented_control(key="jc_moment").select(other.moment).run()
    assert at.segmented_control(key="jc_moment").value == other.moment


def test_unknown_deep_link_falls_back_to_the_first_moment(sandbox):
    at = AppTest.from_file(str(ROOT / "app/Home.py"), default_timeout=15)
    at.query_params["moment"] = "not-a-moment"
    at.run()
    at.switch_page("views/1_Journey_Coach.py").run()
    assert not at.exception and not at.error
    assert at.segmented_control(key="jc_moment").value == lessons.LESSONS[0].moment
