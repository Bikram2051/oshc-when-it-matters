"""Session-only guide chat. Every new turn uses the same guarded service.

No source lookup runs on opening the page. Refusals never offer a search bypass.
Previously checked responses live only in bounded session memory. Live questions
and selected public passages go to Haiku; transcripts are not logged or cached.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import streamlit as st

from oshc.navigator_ui import load_source
from oshc.policy_source import CAPTURED_ON, SOURCE_DOC, SOURCE_SHA256
from oshc.student_chat import MAX_QUESTION_CHARS, answer_question
from oshc.llm import api_key_configured
from oshc.schemas import GuardrailVerdict
from oshc.care_navigation import (
    CLINICAL_HANDOFF, SERVICE_FINDER_URL, SYMPTOM_CHECKER_URL,
)
from oshc.ui_style import lead, safety_line

ROOT = Path(__file__).resolve().parents[1]
MAX_TURNS = 10
RESULT_COUNT = 5
SESSION_KEYS = ("ask_history",)
STARTERS = (
    "How do I make a claim?",
    "What is Direct Billing?",
    "What is the Medicare Benefits Schedule?",
    "How do I get my membership card?",
)


def _page_of(hit) -> int:
    try:
        return int(hit.section.split()[2].rstrip(","))
    except (AttributeError, IndexError, ValueError):
        return 0


def _history_source_valid() -> bool:
    """Check source identity without a search or PDF parsing on transcript replay."""
    try:
        path = ROOT / "corpus" / SOURCE_DOC
        if path.stat().st_size > 64 * 1024 * 1024:
            return False
        return hashlib.sha256(path.read_bytes()).hexdigest() == SOURCE_SHA256
    except OSError:
        return False


def _clear() -> None:
    st.session_state["ask_history"] = []
    st.session_state.pop("ask_pending", None)


def _render_response(response, turn: int, *, source_valid: bool) -> None:
    with st.chat_message("assistant", avatar=":material/health_and_safety:"):
        status = response.status
        if response.decision.verdict == GuardrailVerdict.REFUSE_CLINICAL:
            st.warning(CLINICAL_HANDOFF, icon=":material/health_and_safety:")
            st.markdown("**Your next step**")
            with st.container(horizontal=True):
                st.link_button("Open healthdirect Symptom Checker", SYMPTOM_CHECKER_URL,
                               icon=":material/open_in_new:")
                st.link_button("Find a health service", SERVICE_FINDER_URL,
                               icon=":material/location_on:")
            st.caption("These open official external services. Your message is not included in the links. "
                       "Their privacy policies apply after you open them.")
            if st.button("Understand GP, pharmacy and telehealth options", key=f"ask_care_{turn}",
                         icon=":material/map:"):
                st.switch_page("views/2_Navigator.py")
        elif response.decision.blocked:
            st.error(response.message, icon=":material/health_and_safety:")
        elif status in ("source_unavailable", "offline_required"):
            st.error(response.message, icon=":material/error:")
        elif not response.hits:
            st.warning(response.message, icon=":material/info:")
        else:
            if not source_valid:
                st.warning("The saved guide has changed or is unavailable. Earlier excerpts "
                           "are hidden. Restore the verified guide and ask again.")
                return
            if response.answer:
                st.markdown(f"**{response.answer_title}**")
                # No unreviewed draft is ever streamed. The service returns only
                # complete answers that passed its input and output checks.
                st.text(response.answer)
                st.caption("Written by Haiku from the guide passages below, with input and output checked."
                           if response.response_mode == "haiku" else
                           "A fixed explanation, checked against the guide passages below. "
                           "It does not assess your own benefits.")
            else:
                st.markdown(response.message)
                st.caption("Possible matches, ranked by wording rather than confidence. "
                           "Read the conditions on the full page.")
            for hit in response.hits:
                page = _page_of(hit)
                with st.expander(f"Source {hit.rank}: {hit.section}", expanded=hit.rank == 1):
                    st.text(hit.text[:900])
                    if len(hit.text) > 900:
                        st.caption("This passage continues. Open the full page to read all conditions.")
                    st.caption(f"{SOURCE_DOC}, saved {hit.captured_on}")
                    with st.container(horizontal=True):
                        if st.button("Read full page", key=f"ask_goto_{turn}_{hit.chunk_id}",
                                     icon=":material/menu_book:"):
                            st.session_state["nv_requested_page"] = page
                            st.switch_page("views/2_Navigator.py")
                        st.link_button("Publisher PDF", hit.source_url,
                                       icon=":material/open_in_new:")
        with st.expander("Response checks"):
            st.caption(
                f"Safety boundary: {response.decision.verdict.value.replace('_', ' ')}. "
                f"Response: {status.replace('_', ' ')}. "
                + ("Checked by Haiku: input screening, cited evidence and output review."
                   if response.response_mode == "haiku" else "Checked by local rules against verified guide passages.")
            )
            if response.hits:
                st.caption("Source passages checked against the verified guide. "
                           "These passages cannot confirm personal benefits.")


def render():
    live = os.getenv("OSHC_OFFLINE") == "0" and os.getenv("OSHC_ENABLE_LIVE") == "1"
    source_mode = os.getenv("OSHC_OFFLINE") == "1" and os.getenv("OSHC_ENABLE_LIVE") == "0"
    st.title("Ask NextBest")
    lead("Ask a general question about OSHC. Each answer comes from the Medibank member guide, "
         "with the page to check.")

    if not live and not source_mode:
        _clear()
        st.error("The chat mode is inconsistent. Set OSHC_OFFLINE=0 and OSHC_ENABLE_LIVE=1 for Haiku.")
        return

    st.caption("It can't check your own cover, confirm a claim or assess symptoms. "
               "Please leave out personal details.")
    if live and not api_key_configured():
        st.warning("Haiku is not connected yet. Configure OSHC_API_KEY in the server environment or "
                   "Streamlit secrets. Emergency and privacy checks remain available.")
    history = st.session_state.setdefault("ask_history", [])

    pending = None
    if not history:
        st.markdown("**Try one of these**")
        columns = st.columns(2)
        for index, starter in enumerate(STARTERS):
            if columns[index % 2].button(starter, key=f"ask_s{index}", width="stretch"):
                pending = starter

    submitted = st.chat_input("Ask a general OSHC question", key="ask_box",
                              max_chars=2000 if live else MAX_QUESTION_CHARS, submit_mode="disable")
    question = submitted if submitted is not None else pending
    if question is not None and question.strip():
        # The service checks this complete message before invoking the loader.
        with st.spinner("Checking your question, finding the guide passage and checking the answer…"):
            response = answer_question(question, root=ROOT, source_loader=lambda: load_source(ROOT)[0])
        safe_to_echo = response.safe_to_echo
        history = [*st.session_state["ask_history"], {
            "question": question if safe_to_echo else (
                "[Personal details removed]" if response.status == "privacy" else "[Question not retained]"),
            "response": response,
        }][-MAX_TURNS:]
        st.session_state["ask_history"] = history

    # Hash checking does not search, parse or invoke a provider. Historical source text
    # disappears if its saved source has changed, without resubmitting previous turns.
    source_valid = _history_source_valid() if any(t["response"].hits for t in history) else True
    for index, turn in enumerate(history):
        with st.chat_message("user"):
            st.text(turn["question"])
        _render_response(turn["response"], index, source_valid=source_valid)
    if history:
        st.button("Clear chat", key="ask_clear", icon=":material/delete_sweep:", on_click=_clear)

    st.space("small")
    safety_line()
    with st.expander("How answers are checked"):
        st.caption(f"Answers use the Medibank OSHC Member Guide, effective May 2026, saved {CAPTURED_ON}. "
                   "Each message is checked on its own, so name the topic in a follow-up; earlier "
                   "messages are not used to guess your circumstances.")
        if live:
            st.caption("Your general question and the relevant public guide passages are sent to "
                       "Anthropic's Haiku API for safety checks and an answer. Bill uploads and chat "
                       "history are not sent, and questions and drafts are not saved to disk.")
        else:
            st.caption("This session uses fixed explanations bound to guide passages. No AI provider "
                       "is called.")
        st.caption(f"The chat keeps up to {MAX_TURNS} turns in this browser session. Clear chat "
                   "removes them.")
