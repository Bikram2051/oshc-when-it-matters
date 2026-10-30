"""For partners: link any moment from an existing channel, and see how a pilot is measured.

Counts come from content-free page events on this computer. Nothing here calls a
model, reads a bill or shows any student text.
"""
from __future__ import annotations

from urllib.parse import urlencode, urlsplit

import streamlit as st

from oshc import telemetry
from oshc.home_ui import ASK, journey_stops
from oshc.ui_style import lead

CHANNELS = (
    "Offer letter or pre-departure email",
    "Orientation week and welcome messages",
    "Appointment reminders",
    "Find-a-doctor pages",
    "Claims help page",
)
PATHS = {
    "views/1_Journey_Coach.py": "Journey_Coach",
    "views/2_Navigator.py": "Navigator",
    "views/3_Bill_Explainer.py": "Bill_Explainer",
    "views/4_Ask.py": "Ask",
}


def _origin() -> str:
    try:
        parts = urlsplit(st.context.url or "")
    except (AttributeError, ValueError):
        return ""
    return f"{parts.scheme}://{parts.netloc}" if parts.scheme and parts.netloc else ""


def link_rows(origin: str = "") -> list[tuple[str, str, str]]:
    """(where it fits, what opens, link) for every moment, in journey order."""
    rows = []
    for channel, (moment, _label, page, params, _text) in zip(CHANNELS, journey_stops()):
        query = f"?{urlencode(params)}" if params else ""
        rows.append((channel, moment, f"{origin}/{PATHS[page]}{query}"))
    rows.append(("Member help centre", "A question of your own", f"{origin}/{PATHS[ASK]}"))
    return rows


def _links():
    st.header("Link a moment from your channels")
    st.markdown("Each moment has its own address, so a student lands exactly where they need "
                "to be. No login, and nothing to install.")
    origin = _origin()
    items = []
    for channel, moment, url in link_rows(origin):
        path = url[len(origin):]
        items.append(f"- **{moment}.** {channel}.  \n  [{path}]({url})")
    with st.container(key="partner_links"):
        st.markdown("\n".join(items))
    st.caption("Paths work on whichever address hosts OSHC When It Matters. To show a moment inside your "
               "own page, add embed=true (for example ?embed=true, or &embed=true after "
               "another parameter).")


def _measures():
    st.header("How a pilot would be measured")
    counts = telemetry.summary()
    coach, explainer = counts.get("coach", {}), counts.get("explainer", {})
    with st.container(horizontal=True):
        st.metric("Coach visits", coach.get("open", 0), border=True)
        st.metric("Started a scenario", coach.get("scenario_start", 0), border=True)
        st.metric("Answered correctly", coach.get("scenario_complete", 0), border=True,
                  help="Counted once per lesson per visit, at the first correct answer.")
        st.metric("Read a bill", explainer.get("decode_run", 0), border=True)
    st.caption("Counted on this computer. Each event is a random visit number, an event name "
               "and a page: no question, bill content or name is stored.")
    st.markdown("A pilot would add a short scenario quiz before and after, one confidence "
                "question, and the point where students stop. The measure that matters to "
                "Medibank is fewer basic OSHC queries in a student's first six weeks.")


def _yours():
    st.header("Make it yours")
    st.markdown("Colours and fonts live in one theme file, so your brand drops in without code "
                "changes. Each lesson is a few lines of plain text that your OSHC team can "
                "review and edit. Questions about a student's own cover, claims or health "
                "always go to Medibank or healthdirect, never to a generated answer.")


def render():
    st.title("For partners")
    lead("OSHC When It Matters is built to sit inside the channels you already run.")
    _links()
    _measures()
    _yours()
    st.divider()
    st.page_link("views/5_Dashboard.py", label="Research evidence and evaluation results")
