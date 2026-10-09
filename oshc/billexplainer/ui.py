"""Offline teaching screen. Never sends a bill to a provider or infers cover."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

import streamlit as st

from oshc.billexplainer.extract_llm import extract as extract_saved
from oshc.billexplainer.extract_rules import extract as extract_local
from oshc.billexplainer.mbs_reference import SourceError, compare_bill, load_snapshot
from oshc.billexplainer.read import MAX_BYTES, MAX_CHARS, read_pdf, read_text
from oshc.llm_budget import MODEL
from oshc.schemas import ExtractionResult

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = {
    "GP visit: text example": ("rules_reader_example.txt", "text", "rules"),
    "GP visit: PDF example": ("rules_reader_example.pdf", "pdf", "rules"),
    "GP visit: saved AI reading": ("llm_reader_example.txt", "text", "llm"),
}
CUSTOM = "Try an invented bill"
BASES = {"No comparison": None, "MBS schedule fee": "ScheduleFee",
         "Published 85% benefit": "Benefit85", "Published 100% benefit": "Benefit100"}


def require_offline():
    if os.getenv("OSHC_OFFLINE") != "1" or os.getenv("OSHC_ENABLE_LIVE") != "0":
        raise RuntimeError("Start the demo with OSHC_OFFLINE=1 and OSHC_ENABLE_LIVE=0.")
    if os.getenv("OSHC_MODEL") != MODEL:
        raise RuntimeError("Start the demo with the model used for the saved examples.")


def read_bill(data: bytes, kind: str, reader: str) -> tuple[ExtractionResult, str]:
    require_offline()
    if kind not in ("text", "pdf") or reader not in ("rules", "llm"):
        raise ValueError("Unsupported bill input.")
    source = read_pdf(data) if kind == "pdf" else read_text(data.decode("utf-8-sig"))
    if reader == "llm":
        if kind != "text":
            raise ValueError("The saved AI example is text only.")
        # Offline adapter returns a cache hit or a visible abstention, never a live call.
        result = extract_saved(source)
    else:
        result = extract_local(source)
    return result, source.text


def money(value, missing="Not shown"):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0:
            return missing
        return f"AUD {amount:,.2f}"
    except (InvalidOperation, ValueError):
        return missing


def clear_result():
    for key in list(st.session_state):
        if key == "be_result" or key.startswith("be_basis_"):
            del st.session_state[key]


def clear_all():
    for key in list(st.session_state):
        if key.startswith("be_"):
            del st.session_state[key]


def _input():
    choice = st.selectbox("Choose a bill", [*EXAMPLES, CUSTOM], key="be_example")
    if choice in EXAMPLES:
        filename, kind, reader = EXAMPLES[choice]
        data = (ROOT / "data/demo_dev" / filename).read_bytes()
        st.caption("Saved AI reading: replays an earlier result." if reader == "llm"
                   else "Local reading: works without an AI request.")
        return data, kind, reader, choice, True
    st.caption("Use invented data only. Do not include real invoices, names or member details.")
    kind = st.radio("Input format", ["Text", "PDF"], horizontal=True, key="be_format")
    if kind == "Text":
        text = st.text_area("Invented bill text", height=180, max_chars=MAX_CHARS,
                            placeholder="Service date: 01/09/2026\nItem | Description | Charge\n23 | Short consultation | $90.00\nTotal charged: $90.00",
                            key="be_text")
        data = text.encode("utf-8")
    else:
        upload = st.file_uploader("Synthetic PDF with selectable text", type=["pdf"],
                                  max_upload_size=10, key="be_pdf")
        if upload is not None and upload.size > MAX_BYTES:
            st.error("The PDF must be 10 MiB or smaller.")
            data = b""
        else:
            data = upload.getvalue() if upload is not None else b""
        st.caption("Photos, scanned pages and handwriting are not supported.")
    confirmed = st.checkbox("This is invented data with no personal details.", key="be_synthetic")
    return data, kind.lower(), "rules", choice, confirmed


def render():
    st.caption("NEXTBEST / AT THE MOMENT OF NEED")
    st.title("Make sense of a bill")
    st.write("See what the document says, understand the numbers, and identify what still needs checking.")
    st.caption("University prototype | Synthetic bills only | Offline demonstration")
    if st.session_state.get("lang") == "hi":
        st.info("This prototype screen currently uses English.")
    try:
        require_offline()
    except RuntimeError as error:
        clear_result()
        st.error(str(error))
        return

    st.subheader("1. Choose your example")
    try:
        data, kind, reader, label, confirmed = _input()
    except OSError:
        clear_result()
        st.error("This example file is missing. Restore the development examples before continuing.")
        return
    identity = hashlib.sha256(kind.encode() + reader.encode() + label.encode() + b"\0" + data).hexdigest()
    stored = st.session_state.get("be_result")
    if not confirmed or (stored and stored["identity"] != identity):
        clear_result()
    left, right = st.columns([3, 1])
    run = left.button("Read this bill", type="primary", disabled=not confirmed or not data.strip(),
                      key="be_read", width="stretch")
    right.button("Clear", on_click=clear_all, key="be_clear", width="stretch")
    if run:
        clear_result()
        try:
            with st.spinner("Reading the example..."):
                result, source_text = read_bill(data, kind, reader)
            st.session_state["be_result"] = {"identity": identity, "result": result.model_dump(),
                                            "text": source_text, "label": label, "reader": reader}
        except (OSError, ValueError, RuntimeError):
            st.error("This example could not be read. Check the file and use the local text example.")
            return
    stored = st.session_state.get("be_result")
    if not stored:
        return
    result = ExtractionResult.model_validate(stored["result"])
    st.divider()
    st.subheader("2. Check what was read")
    st.caption(stored["label"] + " | Service date: " + (result.service_date or "Not shown"))
    with st.expander("View source text"):
        st.code(stored["text"], language=None)
    if result.warnings:
        with st.expander("Reading notes", expanded=not result.line_items):
            for warning in result.warnings:
                st.write(warning)
    if not result.line_items:
        st.warning("No bill rows were accepted. Try the text example or check the reading notes.")
        return

    columns = st.columns(3)
    columns[0].metric("Total charge shown", money(result.total_charged))
    columns[1].metric("Insurer benefit shown", money(result.total_benefit))
    columns[2].metric("Gap shown", money(result.total_gap))
    st.caption("Not shown means unknown. It does not mean zero or that a claim was refused.")
    st.dataframe([{"Line": i, "Description": line.raw_description,
                   "MBS item shown": line.item_number or "Not shown", "Charge": money(line.charged),
                   "Insurer benefit shown": money(line.benefit_paid), "Gap shown": money(line.gap)}
                  for i, line in enumerate(result.line_items, 1)], hide_index=True, width="stretch")

    st.subheader("3. Explore an MBS comparison")
    st.write("An MBS reference and a provider's charge can be different amounts. "
             "This learning exercise does not establish what an insurer will pay.")
    comparison = None
    if st.toggle("Show a reference comparison", key="be_compare"):
        st.caption("Choose a reference explicitly for each line. Available source window: 1 Aug to 28 Sep 2026.")
        try:
            snapshot = load_snapshot(ROOT / "corpus/MBS-XML-20260801.XML")
        except (OSError, SourceError):
            st.error("Verified MBS reference data is unavailable. The document readings above are still separate.")
        else:
            bases = []
            for i, line in enumerate(result.line_items, 1):
                if not line.item_number:
                    st.caption(f"Line {i}: no printed MBS item number; comparison unavailable.")
                    bases.append(None)
                else:
                    selected = st.selectbox(f"Line {i}, item {line.item_number}: reference for this exercise",
                                            list(BASES), key=f"be_basis_{i}")
                    bases.append(BASES[selected])
            comparison = compare_bill(result, snapshot, bases)
            st.dataframe([{"Line": line.line_number, "Published amount": money(line.reference_amount, "Not available"),
                           "Amount used (capped at charge)": money(line.amount_used, "Not available"),
                           "Illustrative difference": money(line.difference, "Not available"),
                           "Reading": line.reason} for line in comparison.lines], hide_index=True, width="stretch")
            if comparison.total_difference is None:
                st.info(comparison.total_note)
            else:
                st.metric("Total illustrative difference", money(comparison.total_difference))
            st.caption(comparison.scope)
            st.caption("MBS August 2026 snapshot | Captured 28 Sep 2026 | Later revisions are not checked")
            st.link_button("Open the MBS source page", comparison.source_page)

    with st.expander("Questions to take to your insurer"):
        st.write("Which documents should I provide with this claim?")
        st.write("Which policy conditions affect these charges?")
        st.write("Does this document show an insurer payment, or only a payment made to the provider?")
    summary = {"purpose": "Synthetic teaching example; not a claim or eligibility decision",
               "reading_method": "saved AI response" if stored["reader"] == "llm" else "local rules",
               "document_reading": result.model_dump(mode="json"),
               "mbs_comparison": asdict(comparison) if comparison else None}
    st.download_button("Download this teaching summary", json.dumps(summary, indent=2, default=str),
                       file_name="synthetic_bill_summary.json", mime="application/json", key="be_download")
