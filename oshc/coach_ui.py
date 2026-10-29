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

ROOT = Path(__file__).resolve().parents[1]


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


def _journey_plan():
    unfinished = next((lesson for lesson in LESSONS if not _moment_complete(lesson)), None)
    if unfinished is None:
        st.success("Your three preparation moments are complete. Keep your next-step cards "
                   "and revisit a moment whenever you need a reminder.")
    with st.expander("My journey plan"):
        for lesson in LESSONS:
            practice = st.session_state.get("jc_progress", {}).get(lesson.ident, {}).get("passed")
            saved = st.session_state.get("jc_checklists", {}).get(lesson.ident, ())
            st.markdown(f"**{lesson.moment}** — {lesson.title}")
            st.caption(f"Practice: {'checked correctly' if practice else 'to do'} · "
                       f"Saved preparation ticks: {sum(saved)} of "
                       f"{len(ACTIVITIES[lesson.ident].checklist)}")
        st.button("Continue my next unfinished moment", key="jc_resume",
                  disabled=unfinished is None, on_click=_select_moment,
                  args=((unfinished or LESSONS[0]).moment,),
                  icon=":material/arrow_forward:")


def _progress():
    progress = st.session_state.get("jc_progress", {})
    checklists = st.session_state.get("jc_checklists", {})
    practised = len(progress)
    passed = sum(bool(item["passed"]) for item in progress.values())
    checked = sum(all(checklists.get(item.ident, (False,))) for item in LESSONS)
    complete = sum(_moment_complete(item) for item in LESSONS)
    with st.container(horizontal=True):
        st.metric("Lessons practised", f"{practised} of {len(LESSONS)}", border=True)
        st.metric("Correct at least once", f"{passed} of {len(LESSONS)}", border=True)
        st.metric("Self-checklists completed", f"{checked} of {len(LESSONS)}", border=True)
    st.progress(complete / len(LESSONS),
                text=f"Practice + checklist finished: {complete} of {len(LESSONS)} moments")
    st.caption("These ticks record your own preparation in this session. They do not "
               "measure learning impact or confirm that a service is covered.")


def _learn(lesson):
    st.subheader(lesson.title)
    for index, point in enumerate(lesson.points, start=1):
        with st.container(border=True):
            st.markdown(f"**{index}.** {point}")
    st.info(_s()["next_step"] + lesson.action, icon=":material/arrow_forward:")
    st.caption("Try the scenario in Practise, then make a reminder in Take action.")


def _practice(lesson):
    with st.container(border=True):
        st.badge("A fictional student scenario", icon=":material/psychology:")
        st.markdown(ACTIVITIES[lesson.ident].scenario)
        choice = st.radio(lesson.question, list(lesson.options), index=None, key="jc_choice")
        st.button(_s()["check_answer"], key="jc_check", disabled=choice is None,
                  on_click=_check_answer, args=(lesson.ident,),
                  type="primary", icon=":material/check:")
        if choice is not None and st.session_state.get("jc_checked") == (lesson.ident, choice):
            if choice == lesson.options[lesson.correct]:
                st.success(_s()["correct"] + lesson.explanation)
            else:
                st.warning(_s()["try_again"] + lesson.explanation)
        result = st.session_state.get("jc_progress", {}).get(lesson.ident)
        if result:
            st.caption(f"Checked attempts: {result['attempts']}. Your first answer is preserved "
                       "when you retry. Changing a choice does not submit another attempt.")


def _action(lesson):
    activity = ACTIVITIES[lesson.ident]
    saved = st.session_state.get("jc_checklists", {}).get(lesson.ident, ())
    st.subheader("Make this useful outside the lesson")
    st.info(lesson.action, icon=":material/task_alt:")
    st.caption("Tick the preparation steps you feel able to do, then save. "
               "You do not need to upload any documents or personal details.")
    with st.form(f"jc_checklist_form_{lesson.ident}", border=True):
        for index, task in enumerate(activity.checklist):
            key = f"jc_task_{lesson.ident}_{index}"
            if key not in st.session_state:
                st.session_state[key] = index < len(saved) and saved[index] is True
            st.checkbox(task, key=key, persist_state="session")
        st.form_submit_button("Save my checklist", key="jc_save_checklist",
                              on_click=_save_checklist, args=(lesson.ident,),
                              icon=":material/checklist:")
    if st.session_state.get("jc_saved_checklist") == lesson.ident:
        st.caption(f"Saved for this session: {sum(saved)} of {len(activity.checklist)} steps ticked. "
                   "You can change these whenever you need to.")
    st.download_button("Keep my next-step card", action_card(lesson, saved),
                       file_name=f"nextbest_{lesson.ident}_reminder.txt", mime="text/plain",
                       key="jc_card", icon=":material/download:")
    st.caption("The card contains this lesson's fixed reminders and your saved checklist ticks. "
               "It contains no identity, policy number or medical information.")
    if _moment_complete(lesson):
        st.success("This moment is complete: you checked the scenario correctly and saved "
                   "all preparation ticks. Continue to another moment when you are ready.")
    elif saved:
        st.caption("To complete this moment, check the scenario correctly in Practise and "
                   "save all three preparation ticks. You can keep a reminder at any time.")


def render():
    track(st.session_state, "coach", EventName.OPEN, once_key="telemetry_coach_open")
    st.title("Journey Coach")
    try:
        sources = verified_sources(ROOT)
    except SourceError:
        st.error(_s()["source_error"])
        return
    st.selectbox("Language / भाषा", LANGUAGES, format_func=lambda code: LANGUAGE_LABELS[code],
                 key="coach_language", width=220)
    strings = _s()
    if st.session_state.get("coach_language", "en") != "en":
        st.caption("Interface labels only. Lessons and sources stay in English until a "
                   "reviewed translation exists.")
    st.caption(strings["caption"])
    st.badge("Guided preparation", icon=":material/route:")

    st.caption(strings["guide_note"])
    st.caption("No lesson or checklist details are sent to the AI provider. "
               "Your progress stays in this browser session; Start again clears it.")
    _progress()
    _journey_plan()
    moment = st.segmented_control(
        strings["choose_moment"], [lesson.moment for lesson in LESSONS],
        default=LESSONS[0].moment, required=True, key="jc_moment", persist_state="session",
    )
    if moment not in {item.moment for item in LESSONS}:
        st.error("Choose one of the available learning moments.")
        return
    lesson = next(item for item in LESSONS if item.moment == moment)
    if st.session_state.get("jc_active") != lesson.ident:
        st.session_state.pop("jc_choice", None)
        st.session_state.pop("jc_checked", None)
        st.session_state["jc_active"] = lesson.ident
        track(st.session_state, "coach", EventName.SCENARIO_START)

    learn, practise, action = st.tabs(["Learn", "Practise", "Take action"])
    with learn:
        _learn(lesson)
    with practise:
        _practice(lesson)
    with action:
        _action(lesson)

    index = LESSONS.index(lesson)
    with st.container(horizontal=True):
        st.button("Previous moment", key="jc_previous", disabled=index == 0,
                  on_click=_select_moment, args=(LESSONS[max(0, index - 1)].moment,),
                  icon=":material/arrow_back:")
        next_lesson = LESSONS[(index + 1) % len(LESSONS)]
        st.button(f"Next: {next_lesson.moment}", key="jc_next", on_click=_select_moment,
                  args=(next_lesson.moment,), icon=":material/arrow_forward:")
        st.button(strings["start_again"], key="jc_reset", on_click=_reset,
                  icon=":material/restart_alt:")

    st.caption(f"Source: {SOURCE_DOC}, PDF page {lesson.page}, {lesson.column} column. "
               f"Saved {CAPTURED_ON}.")
    if st.button(strings["read_original"], key="jc_source", icon=":material/menu_book:"):
        st.session_state["nv_requested_page"] = lesson.page
        st.switch_page("views/2_Navigator.py")
    with st.expander(strings["read_source"]):
        st.text(sources[lesson.ident].text)
        st.markdown(f"[Publisher PDF, page {lesson.page}]({SOURCE_URL}#page={lesson.page})")
        st.caption(strings["publisher_note"])
