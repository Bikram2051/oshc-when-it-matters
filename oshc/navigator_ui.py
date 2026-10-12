"""Offline topic browser for the frozen guide; no generated or personal answers."""
from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path

import pymupdf
import streamlit as st

from oshc.policy_search import PolicySearch
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
}
TOPIC_VIEW = "Find a topic"
PAGE_VIEW = "Read a page"


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
             caption=f"Saved guide: physical PDF page {page} of 37")
    st.markdown(f"[Open publisher PDF at page {page}]({SOURCE_URL}#page={page})")


def render():
    st.title("Navigator")
    st.caption("Read the policy source")
    if os.getenv("OSHC_OFFLINE") != "1" or os.getenv("OSHC_ENABLE_LIVE") != "0":
        st.error("Start this prototype in offline mode before browsing.")
        return
    try:
        corpus, raw = load_source(ROOT)
    except SourceError:
        st.error("The saved guide could not be verified. Restore the frozen source before browsing.")
        return

    requested_page = st.session_state.pop("nv_requested_page", None)
    if type(requested_page) is int and 1 <= requested_page <= 37:
        st.session_state["nv_view"] = PAGE_VIEW
        st.session_state["nv_page"] = requested_page

    st.caption("Medibank OSHC Member Guide | Effective May 2026 | Saved 28 September 2026")
    st.info("Browse the guide for general information. Excerpts do not determine your cover. "
            "Read the original page and surrounding conditions before relying on an excerpt.")
    mode = st.radio("Browse the guide", [TOPIC_VIEW, PAGE_VIEW], horizontal=True, key="nv_view")
    try:
        if mode == TOPIC_VIEW:
            topic = st.selectbox("Topic", list(TOPICS), key="nv_topic")
            if st.session_state.get("nv_previous_topic") != topic:
                st.session_state.pop("nv_match", None)
                st.session_state["nv_previous_topic"] = topic
            hits = PolicySearch(corpus).search(TOPICS[topic], k=5)
            if not hits:
                st.warning("No source matches. Use Read a page to inspect the saved guide.")
            else:
                by_id = {hit.chunk_id: hit for hit in hits}
                chunks = {chunk.chunk_id: chunk for chunk in corpus.chunks}
                st.caption("Search matches may include passing mentions. Check the page itself.")
                selected = st.selectbox(
                    "Source match", list(by_id), key="nv_match",
                    format_func=lambda ident: f"{by_id[ident].rank}. {by_id[ident].section}",
                )
                hit, chunk = by_id[selected], chunks[selected]
                left, right = st.columns([1, 1.15])
                with left:
                    st.subheader("Extracted column")
                    st.caption(f"{hit.section} | Source saved {hit.captured_on}")
                    with st.container(height=600, border=True):
                        st.text(hit.text)
                    st.caption("Text keeps its source wording and line breaks. A condition may "
                               "continue in the other column or on another page.")
                with right:
                    st.subheader("Original page")
                    _preview(raw, chunk.page, width="stretch")
        else:
            st.caption("All 37 physical pages are available. Page 19 contains the hospital "
                       "benefits table, which is excluded from text search.")
            page = st.number_input("PDF page", min_value=1, max_value=37, value=19,
                                   step=1, key="nv_page")
            _preview(raw, page, width=900)
    except SourceError:
        st.error("The original page is unavailable. Download the saved guide to inspect it.")

    st.caption("The publisher link may show a newer edition. Previews and the download below "
               "use this saved guide.")
    st.download_button("Download saved guide", raw, file_name=SOURCE_DOC,
                       mime="application/pdf", key="nv_download", on_click="ignore")
    with st.expander("Source details"):
        st.text(f"Source: {SOURCE_DOC}\nSaved: {CAPTURED_ON}\nSHA-256: {SOURCE_SHA256}")
        st.caption(f"Text search: BM25, {len(corpus.chunks)} column excerpts. "
                   "Ranking is not confidence. No generated answer is produced.")
        st.text("Pages excluded from text search: " + ", ".join(str(p) for p, _ in OMITTED_PAGES))
