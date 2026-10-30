"""Student landing page: the journey in the order a student meets it.

Each stop links straight into the right moment, so the same links can be placed in
an offer letter, a pre-departure email or a claims help page.
"""
from html import escape

import streamlit as st

from oshc.coach_lessons import LESSONS
from oshc.ui_style import hero, lead, safety_line

COACH = "views/1_Journey_Coach.py"
NAVIGATOR = "views/2_Navigator.py"
BILL = "views/3_Bill_Explainer.py"
ASK = "views/4_Ask.py"


def _slug(moment: str) -> str:
    return moment.lower().replace(" ", "-")


def journey_stops():
    """(moment, link label, page, query params, one-line description), in journey order."""
    describe = {
        0: "Which document sets out what your cover includes, and where to find it.",
        1: "Why an MBS fee doesn't tell you what a clinic will charge.",
        2: "What to ask a clinic that offers Direct Billing, before you book.",
    }
    stops = [(lesson.moment, lesson.title, COACH, {"moment": _slug(lesson.moment)}, describe[i])
             for i, lesson in enumerate(LESSONS)]
    stops.append(("Seeing a doctor", "Get ready for a GP, pharmacy or phone appointment",
                  NAVIGATOR, {"task": "gp"},
                  "Practical steps, and healthdirect's official finder for services near you."))
    stops.append(("Holding a bill", "Make sense of a bill",
                  BILL, None,
                  "See what a receipt shows, what it doesn't, and what to ask before you claim."))
    return stops


def render():
    with st.container(key="hero"):
        hero("Your OSHC,", "one step at a time.")
        lead("Find the moment you're in. Each one takes about three minutes, "
             "and none of them asks for your personal details.")

    stops = journey_stops()
    with st.container(key="journey"):
        for index, (moment, label, page, params, text) in enumerate(stops):
            key = "stop_last" if index == len(stops) - 1 else f"stop_{index}"
            with st.container(key=key):
                st.html(f"<p class='nb-moment'>{escape(moment)}</p>")
                st.page_link(page, label=label, query_params=params)
                st.caption(text)

    st.header("Something else on your mind?")
    st.markdown("Ask a general question in your own words. Answers come from the Medibank "
                "OSHC Member Guide, with the page to check.")
    st.page_link(ASK, label="Ask a question", icon=":material/forum:")

    st.space("medium")
    safety_line()
    st.divider()
    st.caption("OSHC When It Matters is a student prototype from Swinburne University of Technology, built "
               "with Medibank as industry partner. It explains general information from the "
               "public Medibank OSHC Member Guide (May 2026) and uses invented bills only. It "
               "cannot assess symptoms, decide your cover or confirm a claim.")
