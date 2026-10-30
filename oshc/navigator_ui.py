"""Fixed service navigation and verified guide browsing; never assess symptoms."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pymupdf
import streamlit as st

from oshc.care_navigation import SERVICE_FINDER_URL, SYMPTOM_CHECKER_URL
from oshc.policy_search import PolicySearch
from oshc.schemas import EventName
from oshc.telemetry import track
from oshc.ui_style import lead, safety_line
from oshc.policy_source import (
    CAPTURED_ON, OMITTED_PAGES, SOURCE_DOC, SOURCE_SHA256, SOURCE_URL,
    SourceError, build_corpus,
)

ROOT = Path(__file__).resolve().parents[1]
TOPICS = {
    "Making a claim": "making a claim",
    "Waiting periods": "waiting periods",
    "Membership card": "membership card",
    "Direct billing": "direct billing",
    "Ambulance services": "ambulance services",
    "Medicare Benefits Schedule": "Medicare Benefits Schedule",
    "GP services": "general practitioner",
    "Medicines": "prescription medicines",
}
# Authored navigation anchors for this pinned PDF, independent of BM25 ranking.
# Keeping a full source column preserves conditions around each starting section.
TOPIC_STARTS = {
    "Making a claim": (28, "right", (
        "Making a claim.", "There are a number of ways you can make a claim",
    )),
    "Waiting periods": (21, "right", (
        "Waiting periods.", "A Waiting period is a set amount of time",
    )),
    "Membership card": (8, "left", (
        "Your membership card.", "You will also receive a membership card",
    )),
    "Direct billing": (28, "right", (
        "Direct Billing providers", "an agreement with Medibank to send the bill directly to us",
    )),
    "Ambulance services": (25, "left", (
        "Ambulance services.", "When are Benefits payable?",
    )),
    "Medicare Benefits Schedule": (17, "left", (
        "Medicare Benefits Schedule (MBS).", "purpose of calculating the Medicare benefit",
    )),
    "GP services": (17, "right", (
        "Out-of-hospital medical services.", "general practitioner (GP) consultations",
    )),
    "Medicines": (24, "left", (
        "Prescription medicines.", "What Benefits are payable?", "Refer to your Cover Summary",
    )),
}
TOPIC_VIEW = "Find a topic"
PAGE_VIEW = "Read a page"
SERVICES = {
    "GP appointment": {
        "icon": ":material/stethoscope:",
        "title": "Prepare to contact a general practice",
        "steps": (
            "Open the official Service Finder and choose a GP service and location there.",
            "Ask the clinic about new-patient bookings, opening hours and appointment options.",
            "Ask about the consultation fee, direct billing and any amount you may need to pay. "
            "A directory listing does not confirm OSHC cover.",
        ),
        "topic": "GP services",
    },
    "Phone or video appointment": {
        "icon": ":material/video_call:",
        "title": "Ask about a phone or video appointment",
        "steps": (
            "Contact a practice or your existing provider to ask whether they offer telehealth.",
            "Let the provider explain appointment requirements and whether that format is appropriate.",
            "Confirm fees, billing arrangements and any OSHC requirements before booking.",
        ),
        "topic": "GP services",
        "note": "The saved guide has no dedicated telehealth section. The related GP excerpt "
                "does not establish telehealth cover; check directly with Medibank and the provider.",
    },
    "Pharmacy": {
        "icon": ":material/local_pharmacy:",
        "title": "Find a pharmacy and check its services",
        "steps": (
            "Open the official Service Finder and search for a pharmacy in your chosen location.",
            "Ask the pharmacist about their services, opening hours and medicine costs.",
            "Ask Medibank about applicable medicine benefits and required documents. "
            "This page cannot confirm whether a medicine is covered.",
        ),
        "topic": "Medicines",
    },
    "Making a claim": {
        "icon": ":material/receipt_long:",
        "title": "Get ready to check the claim process",
        "steps": (
            "Keep an itemised invoice and any receipt; check what Medibank asks you to submit.",
            "Read the guide's claim instructions and use your official Medibank member account.",
            "Only Medibank can confirm the claim outcome and benefit. "
            "Do not upload a real bill or identifying details to this research prototype.",
        ),
        "topic": "Making a claim",
    },
    "Membership card": {
        "icon": ":material/badge:",
        "title": "Prepare your membership details",
        "steps": (
            "Read the membership-card instructions in the guide.",
            "Use your official Medibank member account or contact Medibank to manage your card.",
            "Ask your provider which membership details they need. "
            "Do not enter your member number or identity details here.",
        ),
        "topic": "Membership card",
    },
}


# Deep links such as ?task=gp let a partner page open one task directly.
TASK_SLUGS = {"gp": "GP appointment", "telehealth": "Phone or video appointment",
              "pharmacy": "Pharmacy", "claim": "Making a claim", "card": "Membership card"}


def _apply_deep_link():
    slug = st.query_params.get("task")
    if slug is None:
        return
    if slug in TASK_SLUGS:
        st.session_state["nv_service"] = TASK_SLUGS[slug]
    del st.query_params["task"]


def _select_topic(topic):
    if topic in TOPICS:
        st.session_state["nv_view"] = TOPIC_VIEW
        st.session_state["nv_topic"] = topic
        st.session_state.pop("nv_match", None)


def _service_navigation():
    """Show fixed options and official handoffs without collecting a location or symptoms."""
    selected = st.selectbox("What do you need help with?", list(SERVICES), key="nv_service")
    service = SERVICES[selected]
    st.header(service["title"])
    st.markdown("\n".join(f"{number}. {step}" for number, step in enumerate(service["steps"], 1)))
    if service.get("note"):
        st.caption(service["note"])
    with st.container(horizontal=True):
        st.link_button("Find a service near you", SERVICE_FINDER_URL, type="primary",
                       icon=":material/location_on:")
        st.link_button("Check symptoms with healthdirect", SYMPTOM_CHECKER_URL,
                       icon=":material/open_in_new:")
        st.button("Read the guide on this topic", key="nv_related_topic",
                  on_click=_select_topic, args=(service["topic"],), icon=":material/menu_book:")
    st.caption("healthdirect links open in a new tab, and this app sends them nothing. "
               "Navigator does not assess symptoms, choose how urgently you need care or "
               "confirm your cover.")
    safety_line()


def load_source(root: Path):
    # Recheck on every UI rerun. A stale session must not bypass source integrity.
    corpus = build_corpus(root)
    try:
        with (root / "corpus" / SOURCE_DOC).open("rb") as handle:
            raw = handle.read(64 * 1024 * 1024 + 1)
    except OSError as error:
        raise SourceError("The saved guide is unavailable.") from error
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise SourceError("The saved guide changed before previewing.")
    return corpus, raw


def topic_sources(corpus, topic):
    """Verify an authored starting section; BM25 can only supply related columns."""
    if topic not in TOPICS or topic not in TOPIC_STARTS:
        raise SourceError("Choose a known guide topic.")
    page, column, anchors = TOPIC_STARTS[topic]
    primary = next((chunk for chunk in corpus.chunks
                    if (chunk.page, chunk.column) == (page, column)), None)
    if primary is None or any(anchor not in " ".join(primary.text.split()) for anchor in anchors):
        raise SourceError("The topic's starting section could not be verified.")
    by_id = {primary.chunk_id: primary}
    chunks = {chunk.chunk_id: chunk for chunk in corpus.chunks}
    hits = PolicySearch(corpus).search(TOPICS[topic], k=5)
    for hit in hits:
        by_id.setdefault(hit.chunk_id, chunks[hit.chunk_id])
    return primary, by_id, {hit.chunk_id: hit.rank for hit in hits}


def page_png(verified_pdf: bytes, number: int) -> bytes:
    """Render a physical page from bytes already checked by load_source."""
    if type(number) is not int or not 1 <= number <= 37:
        raise SourceError("Choose a physical PDF page from 1 to 37.")
    try:
        with pymupdf.open(stream=verified_pdf, filetype="pdf") as book:
            return book[number - 1].get_pixmap(
                matrix=pymupdf.Matrix(2.4, 2.4), colorspace=pymupdf.csRGB, alpha=False
            ).tobytes("png")
    except (RuntimeError, ValueError, IndexError) as error:
        raise SourceError("The original page could not be rendered.") from error


def _preview(raw: bytes, page: int, *, width):
    st.image(io.BytesIO(page_png(raw, page)), width=width,
             caption=f"Saved guide, page {page} of 37",
             alt=f"Page {page} of the Medibank OSHC Member Guide, May 2026 edition")
    st.markdown(f"[Open this page in the publisher's PDF]({SOURCE_URL}#page={page})")


def render():
    track(st.session_state, "navigator", EventName.OPEN, once_key="telemetry_navigator_open")
    st.title("Navigator")
    lead("Get ready to see a doctor, then check what the member guide says.")
    _apply_deep_link()
    _service_navigation()
    try:
        corpus, raw = load_source(ROOT)
    except SourceError:
        st.error("The saved guide could not be verified. Restore the frozen source before browsing.")
        return

    requested_page = st.session_state.pop("nv_requested_page", None)
    if type(requested_page) is int and 1 <= requested_page <= 37:
        st.session_state["nv_view"] = PAGE_VIEW
        st.session_state["nv_page"] = requested_page

    st.divider()
    st.header("Check the member guide")
    st.caption("Medibank OSHC Member Guide, effective May 2026, saved 28 September 2026. "
               "A passage explains general rules. It does not decide your cover.")
    mode = st.radio("Browse the guide", [TOPIC_VIEW, PAGE_VIEW], horizontal=True, key="nv_view")
    try:
        if mode == TOPIC_VIEW:
            topic = st.selectbox("Topic", list(TOPICS), key="nv_topic")
            if st.session_state.get("nv_previous_topic") != topic:
                st.session_state.pop("nv_match", None)
                st.session_state["nv_previous_topic"] = topic
            primary, by_id, ranks = topic_sources(corpus, topic)
            starting_section = (topic, primary.chunk_id)
            if st.session_state.get("nv_starting_section") != starting_section:
                # Existing sessions may still have selected an old passing mention.
                st.session_state.pop("nv_match", None)
                st.session_state["nv_starting_section"] = starting_section
            selected = st.selectbox(
                "Section", list(by_id), key="nv_match",
                format_func=lambda ident: (
                    "Start here" if ident == primary.chunk_id else f"Related match {ranks[ident]}"
                ) + f", page {by_id[ident].page}, {by_id[ident].column} column",
                help="Start here is a checked starting section. Related matches are found by "
                     "word overlap and may only mention the topic in passing.",
            )
            chunk = by_id[selected]
            with st.expander(f"Read the text of page {chunk.page}, {chunk.column} column"):
                st.text(chunk.text)
                st.caption("The wording and line breaks are the guide's own. A condition may "
                           "continue in the other column or on another page.")
            _preview(raw, chunk.page, width="stretch")
        else:
            st.caption("All 37 pages are here. Page 19 holds the hospital benefits table, "
                       "which text search does not cover.")
            page = st.number_input("Page", min_value=1, max_value=37, value=19,
                                   step=1, key="nv_page")
            _preview(raw, page, width="stretch")
    except SourceError:
        st.error("The selected guide section could not be verified or displayed. "
                 "Use Read a page or download the saved guide to inspect it.")

    with st.expander("About this copy of the guide"):
        st.caption("The publisher's link may show a newer edition. The pages and download "
                   "here use the saved copy.")
        st.download_button("Download the saved guide (PDF)", raw, file_name=SOURCE_DOC,
                           mime="application/pdf", key="nv_download", on_click="ignore")
        st.text(f"Source: {SOURCE_DOC}\nSaved: {CAPTURED_ON}\nSHA-256: {SOURCE_SHA256}")
        st.caption(f"Starting sections are checked against exact source wording. Related "
                   f"matches use BM25 across {len(corpus.chunks)} column excerpts; ranking is "
                   "not confidence, and no generated answer is produced.")
        st.text("Pages excluded from text search: " + ", ".join(str(p) for p, _ in OMITTED_PAGES))
