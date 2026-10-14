"""Session-only Journey Coach practice, with fixed source-grounded lessons."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from oshc.coach_lessons import LESSONS, verified_sources
from oshc.coach_strings import get_strings
from oshc.config import LANGUAGES
from oshc.policy_source import CAPTURED_ON, SOURCE_DOC, SOURCE_URL, SourceError
from oshc.schemas import Event, EventName
from oshc.telemetry import record

ROOT = Path(__file__).resolve().parents[1]


def _reset():
    for key in list(st.session_state):
        if key.startswith("jc_"):
            del st.session_state[key]


def render():
    if "telemetry_session_id" not in st.session_state:
        st.session_state["telemetry_session_id"] = str(uuid.uuid4())

    if not st.session_state.get("telemetry_coach_open"):
        record(
            Event(
                session_id=st.session_state["telemetry_session_id"],
                name=EventName.OPEN,
                at=datetime.now(timezone.utc),
                page="coach",
                code=None,
                detail=None,
            )
        )
        st.session_state["telemetry_coach_open"] = True

    language_labels = {"en": "English", "hi": "हिन्दी"}
    language = st.selectbox(
        "Language / भाषा",
        LANGUAGES,
        format_func=lambda code: language_labels[code],
        key="coach_language",
    )
    strings = get_strings(language)

    st.title("Journey Coach")
    st.caption(strings["caption"])
    if os.getenv("OSHC_OFFLINE") != "1" or os.getenv("OSHC_ENABLE_LIVE") != "0":
        st.error(strings["offline_error"])
        return
    try:
        sources = verified_sources(ROOT)
    except SourceError:
        st.error(strings["source_error"])
        return

    st.caption(strings["guide_note"])
    st.button(strings["start_again"], key="jc_reset", on_click=_reset)
    moment = st.selectbox(strings["choose_moment"], [lesson.moment for lesson in LESSONS], key="jc_moment")
    lesson = next(item for item in LESSONS if item.moment == moment)
    if st.session_state.get("jc_active") != lesson.ident:
        st.session_state.pop("jc_choice", None)
        st.session_state.pop("jc_checked", None)
        st.session_state["jc_active"] = lesson.ident

        record(
            Event(
                session_id=st.session_state["telemetry_session_id"],
                name=EventName.SCENARIO_START,
                at=datetime.now(timezone.utc),
                page="coach",
                code=None,
                detail=None,
            )
        )

    st.subheader(lesson.title)
    for point in lesson.points:
        st.markdown(f"- {point}")
    st.info(strings["next_step"] + lesson.action)
    st.subheader(strings["quick_practice"])
    choice = st.radio(lesson.question, list(lesson.options), index=None, key="jc_choice")
    if st.button(strings["check_answer"], key="jc_check", disabled=choice is None):
        selected = lesson.options.index(choice)
        progress = dict(st.session_state.get("jc_progress", {}))
        old = progress.get(lesson.ident)
        progress[lesson.ident] = {
            "first": selected if old is None else old["first"],
            "last": selected, "attempts": 1 if old is None else old["attempts"] + 1,
            "passed": selected == lesson.correct or bool(old and old["passed"]),
        }
        st.session_state["jc_progress"] = progress
        st.session_state["jc_checked"] = (lesson.ident, choice)

        if selected == lesson.correct and not bool(old and old["passed"]):
            record(
                Event(
                    session_id=st.session_state["telemetry_session_id"],
                    name=EventName.SCENARIO_COMPLETE,
                    at=datetime.now(timezone.utc),
                    page="coach",
                    code=None,
                    detail=None,
                )
            )

    if choice is not None and st.session_state.get("jc_checked") == (lesson.ident, choice):
        if choice == lesson.options[lesson.correct]:
            st.success(strings["correct"] + lesson.explanation)
        else:
            st.warning(strings["try_again"] + lesson.explanation)

    progress = st.session_state.get("jc_progress", {})
    practised = len(progress)
    passed = sum(bool(item["passed"]) for item in progress.values())
    st.progress(practised / len(LESSONS), text=f"Practised {practised} of {len(LESSONS)} lessons")
    st.caption(f"Correct at least once: {passed} of {len(LESSONS)}. "
               "Practice progress stays in this browser session and is not a learning-impact score.")

    st.divider()
    st.caption(f"Source: {SOURCE_DOC}, PDF page {lesson.page}, {lesson.column} column. "
               f"Saved {CAPTURED_ON}.")
    if st.button(strings["read_original"], key="jc_source"):
        st.session_state["nv_requested_page"] = lesson.page
        st.switch_page("pages/2_Navigator.py")
    with st.expander(strings["read_source"]):
        st.text(sources[lesson.ident].text)
        st.markdown(f"[Publisher PDF, page {lesson.page}]({SOURCE_URL}#page={lesson.page})")
        st.caption(strings["publisher_note"])
