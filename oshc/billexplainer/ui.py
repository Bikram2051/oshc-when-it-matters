"""Local teaching screen. Never sends a bill to a provider or infers cover."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

import streamlit as st

from oshc.billexplainer.extract_llm import extract as extract_saved
from oshc.billexplainer.extract_document import ReceiptFacts, extract as extract_local, read_document
from oshc.billexplainer.explanation import explain
from oshc.billexplainer.privacy import minimise, retained_fields
from oshc.billexplainer.mbs_reference import SourceError, compare_bill, load_snapshot
from oshc.billexplainer.read import MAX_BYTES, MAX_CHARS, read_pdf, read_text
from oshc.schemas import EventName, ExtractionResult
from oshc.telemetry import track
from oshc.ui_style import lead

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = {
    "GP visit: text example": ("rules_reader_example.txt", "text", "rules"),
    "GP visit: PDF example": ("rules_reader_example.pdf", "pdf", "rules"),
    "GP visit: saved AI reading": ("llm_reader_example.txt", "text", "llm"),
    "Paid receipt: dated service lines": ("receipt_reader_example.txt", "text", "rules"),
}
CUSTOM = "Try an invented bill"
BASES = {"No comparison": None, "MBS schedule fee": "ScheduleFee",
         "Published 85% benefit": "Benefit85", "Published 100% benefit": "Benefit100"}


def read_bill(data: bytes, kind: str, reader: str) -> tuple[ExtractionResult, ReceiptFacts]:
    if kind not in ("text", "pdf") or reader not in ("rules", "llm"):
        raise ValueError("Unsupported bill input.")
    source = read_pdf(data) if kind == "pdf" else read_text(data.decode("utf-8-sig"))
    if reader == "llm":
        if kind != "text":
            raise ValueError("The saved AI example is text only.")
        # Bills cannot reach a provider, even when the chat enables live requests.
        result = extract_saved(source, cache_only=True)
        _, receipt = read_document(source)
    else:
        result, receipt = read_document(source)
    return minimise(result), receipt


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
        if key in ("be_result", "be_line", "be_check_amounts", "be_check_gap") or key.startswith("be_basis_"):
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
        st.caption("Invented example. Replays a saved AI reading of it." if reader == "llm"
                   else "Invented example. Read on this computer, with no AI request.")
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
                                  max_upload_size=10, key=f"be_pdf_{st.session_state.get('be_upload_epoch', 0)}")
        if upload is not None and upload.size > MAX_BYTES:
            st.error("The PDF must be 10 MiB or smaller.")
            data = b""
        else:
            data = upload.getvalue() if upload is not None else b""
        st.caption("Photos, scanned pages and handwriting are not supported.")
    confirmed = st.checkbox("This is invented data with no personal details.", key="be_synthetic")
    return data, kind.lower(), "rules", choice, confirmed


def render():
    track(st.session_state, "explainer", EventName.OPEN, once_key="telemetry_explainer_open")
    st.title("Bill Explainer")
    lead("See what a bill shows, what it doesn't, and what to ask before you claim.")
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
    with st.container(horizontal=True):
        run = st.button("Read this bill", type="primary", disabled=not confirmed or not data.strip(),
                        key="be_read")
        st.button("Clear", on_click=clear_all, key="be_clear")
    if run:
        clear_result()
        try:
            with st.spinner("Reading the bill..."):
                result, receipt = read_bill(data, kind, reader)
            st.session_state["be_result"] = {"identity": identity, "result": result.model_dump(),
                                            "receipt": asdict(receipt), "label": label, "reader": reader}
            track(st.session_state, "explainer", EventName.DECODE_RUN)
        except (OSError, ValueError, RuntimeError):
            st.error("This bill could not be read. Check the file, or try the text example.")
            return
    stored = st.session_state.get("be_result")
    if not stored:
        _protection()
        return
    result = ExtractionResult.model_validate(stored["result"])
    # Old sessions from an earlier app version must not retain their original text.
    stored.pop("text", None)
    result = minimise(result)
    stored["result"] = result.model_dump()
    receipt = ReceiptFacts(**stored.get("receipt", {}))

    st.header("What this bill shows")
    st.caption(f"{stored['label']}. Service date: {result.service_date or 'not shown'}.")
    if result.warnings:
        with st.expander("Reading notes", expanded=not result.line_items):
            for warning in result.warnings:
                st.write(warning)
    if not result.line_items:
        st.warning("No bill rows were accepted. Try the text example or check the reading notes.")
        return

    with st.container(horizontal=True):
        st.metric("Total charge shown", money(result.total_charged), border=True)
        st.metric("Insurer benefit shown", money(result.total_benefit), border=True)
        st.metric("Gap shown", money(result.total_gap), border=True)
    st.markdown("**Not shown means unknown.** It does not mean zero, and it does not mean a "
                "claim was refused.")
    st.subheader("In plain words")
    st.markdown("\n".join(f"- {message}" for message in explain(result, receipt)))
    st.dataframe([{"Line": i, "Description": line.raw_description,
                   "MBS item": line.item_number or "Not shown", "Charge": money(line.charged),
                   "Insurer benefit": money(line.benefit_paid), "Gap": money(line.gap)}
                  for i, line in enumerate(result.line_items, 1)], hide_index=True, width="stretch")
    if receipt.amount_settled is not None or receipt.balance_remaining is not None:
        st.caption(f"Receipt: settled {money(receipt.amount_settled)}, balance "
                   f"{money(receipt.balance_remaining)}, GST {money(receipt.total_gst)}.")

    st.header("Compare with the MBS fee")
    st.markdown("A provider's charge and the government's MBS reference fee can differ. "
                "This shows why a gap can exist. It does not show what an insurer will pay.")
    comparison = None
    if st.toggle("Show a reference comparison", key="be_compare"):
        try:
            snapshot = load_snapshot(ROOT / "corpus/MBS-XML-20260801.XML")
        except (OSError, SourceError):
            st.error("Verified MBS reference data is unavailable. The bill reading above is unaffected.")
        else:
            bases = []
            for i, line in enumerate(result.line_items, 1):
                if not line.item_number:
                    st.caption(f"Line {i} has no MBS item number, so there is nothing to compare.")
                    bases.append(None)
                else:
                    selected = st.selectbox(f"Line {i}, MBS item {line.item_number}: compare with",
                                            list(BASES), key=f"be_basis_{i}")
                    bases.append(BASES[selected])
            comparison = compare_bill(result, snapshot, bases)
            st.dataframe([{"Line": line.line_number, "Published amount": money(line.reference_amount, "Not available"),
                           "Amount used (capped at charge)": money(line.amount_used, "Not available"),
                           "Illustrative difference": money(line.difference, "Not available")}
                          for line in comparison.lines], hide_index=True, width="stretch")
            if comparison.total_difference is None:
                st.info(comparison.total_note)
            else:
                st.metric("Total illustrative difference", money(comparison.total_difference))
            st.caption(comparison.scope + " MBS August 2026 release, captured 28 September 2026.")
            st.link_button("Open the MBS source page", comparison.source_page)

    st.header("Before you claim")
    st.checkbox("I have checked these amounts against the original invoice.", key="be_check_amounts")
    st.checkbox("I understand the receipt balance and the insurance gap are different.", key="be_check_gap")
    st.markdown("Questions to ask Medibank:\n"
                "- Which documents should I provide with this claim?\n"
                "- Which policy conditions affect these charges?\n"
                "- Does this document show an insurer payment, or only a payment to the provider?")
    summary = {"purpose": "Synthetic teaching example; not a claim or eligibility decision",
               "reading_method": "saved AI response" if stored["reader"] == "llm" else "local rules",
               **retained_fields(result, receipt),
               "explanation": explain(result, receipt),
               "mbs_comparison": asdict(comparison) if comparison else None}
    st.download_button("Download this summary", json.dumps(summary, indent=2, default=str),
                       file_name="synthetic_bill_summary.json", mime="application/json",
                       key="be_download", icon=":material/download:")
    with st.expander("See exactly what the app kept"):
        st.json(retained_fields(result, receipt), expanded=False)
    _protection()


def _protection():
    with st.expander("How your bill is protected"):
        st.markdown("The bill is read on this computer and never sent to an AI provider. The app "
                    "keeps only service dates, item numbers and amounts for this session. Names, "
                    "contact and membership details, provider identities and descriptions are "
                    "removed from the result and the download.")
        st.caption("The upload stays in memory until you select Clear. There is no bill database, "
                   "file storage or logging of bill content. This prototype is for invented "
                   "bills; it is not approved for real patient records or public hosting.")
