"""Interactive, session-only practice around fixed source-grounded lessons."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from oshc.coach_lessons import ACTIVITIES, LESSONS, action_card, verified_sources
from oshc.coach_strings import LANGUAGE_LABELS, get_strings
from oshc.config import LANGUAGES
from oshc.policy_source import CAPTURED_ON, SOURCE_DOC, SOURCE_URL, SourceError
from oshc.schemas import EventName
from oshc.telemetry import track
from oshc.ui_style import lead

ROOT = Path(__file__).resolve().parents[1]
# Deep links such as ?moment=before-you-arrive let a partner channel open one moment.
MOMENT_SLUGS = {lesson.moment.lower().replace(" ", "-"): lesson.moment for lesson in LESSONS}


def _s():
    """Static interface strings for the selected language; lessons stay in English."""
    return get_strings(st.session_state.get("coach_language", "en"))


def _reset():
    for key in list(st.session_state):
        if key.startswith("jc_"):
            del st.session_state[key]


def _select_moment(moment):
    if moment in {lesson.moment for lesson in LESSONS}:
        st.session_state["jc_moment"] = moment


def _check_answer(ident):
    lesson = next(item for item in LESSONS if item.ident == ident)
    choice = st.session_state.get("jc_choice")
    if choice not in lesson.options:
        return
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
    if selected == lesson.correct and not (old and old["passed"]):
        track(st.session_state, "coach", EventName.SCENARIO_COMPLETE)


def _save_checklist(ident):
    activity = ACTIVITIES[ident]
    plans = dict(st.session_state.get("jc_checklists", {}))
    plans[ident] = tuple(st.session_state.get(f"jc_task_{ident}_{index}") is True
                         for index in range(len(activity.checklist)))
    st.session_state["jc_checklists"] = plans
    st.session_state["jc_saved_checklist"] = ident


def _moment_complete(lesson):
    """Combine explicit practice and saved self-checks; never infer readiness."""
    passed = st.session_state.get("jc_progress", {}).get(lesson.ident, {}).get("passed")
    saved = st.session_state.get("jc_checklists", {}).get(lesson.ident, ())
    return bool(passed) and len(saved) == len(ACTIVITIES[lesson.ident].checklist) and all(saved)


def _apply_deep_link():
    """Open the moment named in the URL once, then drop the parameter so clicks win."""
    slug = st.query_params.get("moment")
    if slug is None:
        return
    if slug in MOMENT_SLUGS:
        st.session_state["jc_moment"] = MOMENT_SLUGS[slug]
    del st.query_params["moment"]


def _progress():
    """One quiet line of progress; resume appears only once there is something to resume."""
    progress = st.session_state.get("jc_progress", {})
    checklists = st.session_state.get("jc_checklists", {})
    complete = sum(_moment_complete(item) for item in LESSONS)
    unfinished = next((lesson for lesson in LESSONS if not _moment_complete(lesson)), None)
    if unfinished is None:
        st.success("Your three preparation moments are complete. Keep your next-step cards "
                   "and revisit a moment whenever you need a reminder.")
    left, right = st.columns([3, 2], vertical_alignment="center")
    left.progress(complete / len(LESSONS),
                  text=f"{complete} of {len(LESSONS)} moments complete")
    if progress or checklists:
        right.button("Continue where I left off", key="jc_resume",
                     disabled=unfinished is None, on_click=_select_moment,
                     args=((unfinished or LESSONS[0]).moment,), width="stretch")


def _learn(lesson, strings):
    st.header(lesson.title)
    st.markdown("\n".join(f"- {point}" for point in lesson.points))
    st.info(strings["next_step"] + lesson.action, icon=":material/arrow_forward:")
    if st.button(strings["read_original"], key="jc_source", icon=":material/menu_book:"):
        st.session_state["nv_requested_page"] = lesson.page
        st.switch_page("views/2_Navigator.py")


def _practice(lesson, strings):
    st.subheader("Try it")
    st.markdown(ACTIVITIES[lesson.ident].scenario)
    choice = st.radio(lesson.question, list(lesson.options), index=None, key="jc_choice")
    st.button(strings["check_answer"], key="jc_check", disabled=choice is None,
              on_click=_check_answer, args=(lesson.ident,), type="primary")
    if choice is not None and st.session_state.get("jc_checked") == (lesson.ident, choice):
        if choice == lesson.options[lesson.correct]:
            st.success(strings["correct"] + lesson.explanation)
        else:
            st.warning(strings["try_again"] + lesson.explanation)


def _action(lesson):
    activity = ACTIVITIES[lesson.ident]
    saved = st.session_state.get("jc_checklists", {}).get(lesson.ident, ())
    st.subheader("Keep a next step")
    with st.form(f"jc_checklist_form_{lesson.ident}", border=False):
        for index, task in enumerate(activity.checklist):
            key = f"jc_task_{lesson.ident}_{index}"
            if key not in st.session_state:
                st.session_state[key] = index < len(saved) and saved[index] is True
            st.checkbox(task, key=key, persist_state="session")
        st.form_submit_button("Save my checklist", key="jc_save_checklist",
                              on_click=_save_checklist, args=(lesson.ident,))
    st.download_button("Download my next-step card", action_card(lesson, saved),
                       file_name=f"nextbest_{lesson.ident}_reminder.txt", mime="text/plain",
                       key="jc_card", icon=":material/download:")
    if _moment_complete(lesson):
        st.success("This moment is complete. Move on to another moment when you are ready.")
    elif saved:
        st.caption(f"Saved: {sum(saved)} of {len(activity.checklist)} ticked. To finish this "
                   "moment, answer the scenario correctly and tick all three.")


def _about(lesson, sources, strings):
    with st.expander("Where this comes from"):
        st.caption(strings["guide_note"])
        st.caption(f"Source: {SOURCE_DOC}, PDF page {lesson.page}, {lesson.column} column. "
                   f"Saved {CAPTURED_ON}.")
        st.text(sources[lesson.ident].text)
        st.markdown(f"[Publisher PDF, page {lesson.page}]({SOURCE_URL}#page={lesson.page})")
        st.caption(strings["publisher_note"])
        st.caption("No lesson or checklist details are sent to the AI provider. Your progress "
                   "stays in this browser session, and Start again clears it. The card holds "
                   "no identity, policy number or medical information.")


def render():
    track(st.session_state, "coach", EventName.OPEN, once_key="telemetry_coach_open")
    st.title("Journey Coach")
    try:
        sources = verified_sources(ROOT)
    except SourceError:
        st.error(_s()["source_error"])
        return
    _apply_deep_link()

    intro, language = st.columns([3, 1], vertical_alignment="bottom")
    language.selectbox("Language / भाषा", LANGUAGES, format_func=lambda code: LANGUAGE_LABELS[code],
                       key="coach_language")
    strings = _s()
    with intro:
        lead(strings["caption"])
    if st.session_state.get("coach_language", "en") != "en":
        st.caption("Interface labels only. Lessons and sources stay in English until a "
                   "reviewed translation exists.")

    st.session_state.setdefault("jc_moment", LESSONS[0].moment)
    moment = st.segmented_control(
        strings["choose_moment"], [lesson.moment for lesson in LESSONS],
        required=True, key="jc_moment", persist_state="session",
    )
    if moment not in {item.moment for item in LESSONS}:
        st.error("Choose one of the available moments.")
        return
    lesson = next(item for item in LESSONS if item.moment == moment)
    if st.session_state.get("jc_active") != lesson.ident:
        st.session_state.pop("jc_choice", None)
        st.session_state.pop("jc_checked", None)
        st.session_state["jc_active"] = lesson.ident
        track(st.session_state, "coach", EventName.SCENARIO_START)
    _progress()

    _learn(lesson, strings)
    _practice(lesson, strings)
    _action(lesson)

    st.divider()
    index = LESSONS.index(lesson)
    next_lesson = LESSONS[(index + 1) % len(LESSONS)]
    with st.container(horizontal=True):
        st.button("Previous moment", key="jc_previous", disabled=index == 0,
                  on_click=_select_moment, args=(LESSONS[max(0, index - 1)].moment,),
                  icon=":material/arrow_back:")
        st.button(f"Next: {next_lesson.moment}", key="jc_next", on_click=_select_moment,
                  args=(next_lesson.moment,), icon=":material/arrow_forward:")
        st.button(strings["start_again"], key="jc_reset", on_click=_reset,
                  icon=":material/restart_alt:")
    _about(lesson, sources, strings)
