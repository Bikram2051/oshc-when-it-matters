"""Presenter evidence browser. Reads reports without running the prototype.

Three tiers, kept apart on purpose, because collapsing them is how a prototype
starts overclaiming:

  recorded engineering checks   this code did what we said, on a recorded date
  in-house measurements         a real number, on probes we wrote ourselves
  independent evaluation        none of it established yet

Opening this page reruns nothing.
"""
import json
from pathlib import Path

import streamlit as st

from oshc.evidence_dashboard import (
    EVALUATIONS, PASSED, SCOPE, SPECS, load_evidence, summary_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
ASK_REPORT = ROOT / "docs" / "prototype" / "ask_ui_check.json"

STATUS_MARK = {PASSED: "pass", "Missing report": "missing", "Needs review": "review"}


def _ask_measurements():
    try:
        record = json.loads(ASK_REPORT.read_text(encoding="utf-8"))
        return record["gold_guide_wording"], record["dev_student_wording"], record
    except (OSError, ValueError, KeyError, TypeError):
        return None, None, None


def _engineering(evidence):
    passing = sum(item.status == PASSED for item in evidence)
    first, second, third = st.columns(3)
    first.metric("Reports with recorded passing checks", f"{passing} of {len(evidence)}")
    second.metric("Measures independently established", f"0 of {len(EVALUATIONS)}")
    third.metric("Modules in the prototype", len(SPECS))

    if passing != len(evidence):
        st.warning(
            "Some reports are missing or need review. Those components' outcomes are "
            "unknown, not failing."
        )

    st.dataframe(
        [{"Component": item.component, "Status": item.status,
          "Recorded evidence": item.detail} for item in evidence],
        hide_index=True, width="stretch",
    )
    st.caption(
        "A recorded check means the code behaved as described on the date in the report. "
        "It is not a measure of accuracy, and it does not certify today's working tree."
    )


def _measured():
    gold, dev, record = _ask_measurements()
    st.subheader("Measured in-house")
    if gold is None:
        st.info(
            "No in-house measurement is recorded yet. Run "
            "scripts/prototype_check_ask_ui.py to produce one."
        )
        return

    st.write(
        "Real numbers, on probe sets the team wrote and labelled itself. They are the "
        "optimistic end of the range and they are not a substitute for the held-out "
        "evaluations below."
    )
    left, middle, right = st.columns(3)
    left.metric("Right page in top 5, guide wording", f"{gold['recall_at_5']:.0%}",
                help=f"{gold['allowed_and_scored']} questions from the project gold set.")
    middle.metric("Right page in top 5, student wording", f"{dev['recall_at_5']:.0%}",
                  delta=f"{-record['recall_at_5_gap']:.0%} against guide wording",
                  delta_color="inverse",
                  help=f"{dev['allowed_and_scored']} dev probes in students' own phrasing.")
    refused = gold["refused_at_guardrail"] + dev["refused_at_guardrail"]
    right.metric("Questions refused at the boundary", f"{refused} of {gold['probes'] + dev['probes']}",
                 help="General-information questions caught by the emergency word list.")
    st.caption(
        "The gap between the first two is the finding: word-overlap search rewards people "
        "who already know the document's vocabulary. The third is the measured cost of "
        "keeping the emergency word list deliberately wide."
    )


def _independent():
    st.subheader("Independent evaluation")
    st.write(
        "None of these is established. Engineering rehearsals, practice attempts and "
        "in-house probe sets do not establish independent accuracy or learning impact."
    )
    st.dataframe(
        [{"Measure": name, "Status": "Not linked here"} for name in EVALUATIONS],
        hide_index=True, width="stretch",
    )


def _provenance(evidence):
    st.subheader("Report provenance and scope")
    for item in evidence:
        label = f"{item.component} | {STATUS_MARK.get(item.status, 'unknown')}"
        with st.expander(label):
            st.write(item.scope)
            st.text(f"Status: {item.status}\nChecked: {item.checked_at_utc or 'Unknown'}\n"
                    f"File: {item.file}\nSHA-256: {item.sha256 or 'Unavailable'}")


def render():
    st.title("Prototype evidence")
    st.caption("Presenter view | Saved engineering checks | Nothing is rerun by opening this")
    st.info(SCOPE)

    evidence = load_evidence(ROOT)
    engineering, measured, independent, provenance = st.tabs(
        ["Recorded checks", "Measured in-house", "Independent evaluation", "Provenance"]
    )
    with engineering:
        _engineering(evidence)
    with measured:
        _measured()
    with independent:
        _independent()
    with provenance:
        _provenance(evidence)

    st.divider()
    st.download_button("Download evidence summary", summary_bytes(evidence),
                       file_name="prototype_evidence_summary.json", mime="application/json",
                       key="dashboard_download")
    st.caption(
        f"This view reads {len(SPECS)} named report files. It does not collect usage "
        "telemetry or include bill text, question text, API credentials or learner records."
    )
