"""Session-only Journey Coach practice, with fixed source-grounded lessons."""
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from oshc.coach_lessons import LESSONS, verified_sources
from oshc.policy_source import CAPTURED_ON, SOURCE_DOC, SOURCE_URL, SourceError

ROOT = Path(__file__).resolve().parents[1]


def _reset():
    for key in list(st.session_state):
        if key.startswith("jc_"):
            del st.session_state[key]


def render():
    st.title("Journey Coach")
    st.caption("One useful idea before you need it | English demo lessons")
    if os.getenv("OSHC_OFFLINE") != "1" or os.getenv("OSHC_ENABLE_LIVE") != "0":
        st.error("Start this prototype in offline mode before practising.")
        return
    try:
        sources = verified_sources(ROOT)
    except SourceError:
        st.error("The saved lesson sources could not be verified. Restore the frozen guide first.")
        return

    st.caption("Based on the Medibank OSHC Member Guide, effective May 2026. "
               "These lessons explain general information, not your entitlement to benefits.")
    st.button("Start again", key="jc_reset", on_click=_reset)
    moment = st.selectbox("Choose a moment", [lesson.moment for lesson in LESSONS], key="jc_moment")
    lesson = next(item for item in LESSONS if item.moment == moment)
    if st.session_state.get("jc_active") != lesson.ident:
        st.session_state.pop("jc_choice", None)
        st.session_state.pop("jc_checked", None)
        st.session_state["jc_active"] = lesson.ident

    st.subheader(lesson.title)
    for point in lesson.points:
        st.markdown(f"- {point}")
    st.info("Your next step: " + lesson.action)
    st.subheader("Quick practice")
    choice = st.radio(lesson.question, list(lesson.options), index=None, key="jc_choice")
    if st.button("Check my answer", key="jc_check", disabled=choice is None):
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

    if choice is not None and st.session_state.get("jc_checked") == (lesson.ident, choice):
        if choice == lesson.options[lesson.correct]:
            st.success("Correct. " + lesson.explanation)
        else:
            st.warning("Try again. " + lesson.explanation)

    progress = st.session_state.get("jc_progress", {})
    practised = len(progress)
    passed = sum(bool(item["passed"]) for item in progress.values())
    st.progress(practised / len(LESSONS), text=f"Practised {practised} of {len(LESSONS)} lessons")
    st.caption(f"Correct at least once: {passed} of {len(LESSONS)}. "
               "Practice progress stays in this browser session and is not a learning-impact score.")

    st.divider()
    st.caption(f"Source: {SOURCE_DOC}, PDF page {lesson.page}, {lesson.column} column. "
               f"Saved {CAPTURED_ON}.")
    if st.button("Read the original page in Navigator", key="jc_source"):
        st.session_state["nv_requested_page"] = lesson.page
        st.switch_page("pages/2_Navigator.py")
    with st.expander("Read the source excerpt"):
        st.text(sources[lesson.ident].text)
        st.markdown(f"[Publisher PDF, page {lesson.page}]({SOURCE_URL}#page={lesson.page})")
        st.caption("The publisher link may show a newer edition. Navigator displays the saved guide.")
