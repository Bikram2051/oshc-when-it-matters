"""Presenter evidence browser. Reads reports without running the prototype."""
from pathlib import Path

import streamlit as st

from oshc.evidence_dashboard import EVALUATIONS, PASSED, SCOPE, load_evidence, summary_bytes

ROOT = Path(__file__).resolve().parents[1]


def render():
    st.title("Prototype evidence")
    st.caption("Presenter view | Saved engineering checks")
    st.info(SCOPE)
    evidence = load_evidence(ROOT)
    count = sum(item.status == PASSED for item in evidence)
    st.metric("Reports with recorded passing checks", f"{count} of {len(evidence)}")
    if count != len(evidence):
        st.warning("Some reports are missing or need review. Their outcomes remain unknown.")
    st.dataframe([{"Component": item.component, "Status": item.status,
                   "Recorded evidence": item.detail} for item in evidence],
                 hide_index=True, width="stretch")
    st.subheader("Independent evaluation")
    st.write("These measures are not linked in this view. Engineering rehearsals and "
             "practice attempts do not establish independent accuracy or learning impact.")
    st.dataframe([{"Measure": name, "Status": "Not linked here"} for name in EVALUATIONS],
                 hide_index=True, width="stretch")
    st.subheader("Report provenance and scope")
    for item in evidence:
        with st.expander(item.component):
            st.write(item.scope)
            st.text(f"Status: {item.status}\nChecked: {item.checked_at_utc or 'Unknown'}\n"
                    f"File: {item.file}\nSHA-256: {item.sha256 or 'Unavailable'}")
    st.download_button("Download evidence summary", summary_bytes(evidence),
                       file_name="prototype_evidence_summary.json", mime="application/json",
                       key="dashboard_download")
    st.caption("This view reads six named report files. It does not collect usage telemetry "
               "or include bill text, question text, API credentials or learner records.")
