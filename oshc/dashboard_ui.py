"""Present saved project evidence without rerunning checks or calling providers."""
from pathlib import Path

import streamlit as st

from oshc.evidence_dashboard import PASSED, SCOPE, load_evidence, summary_bytes
from oshc.project_progress import RECORDED, evaluation_rows, load_measurements

ROOT = Path(__file__).resolve().parents[1]
STATUS_MARK = {PASSED: "recorded pass", "Missing report": "missing", "Needs review": "review"}


def _overview(evidence, measurements):
    passing = sum(item.status == PASSED for item in evidence)
    results = evaluation_rows(measurements)
    linked = sum(row["Status"] == RECORDED for row in results)
    with st.container(horizontal=True):
        st.metric("Saved checks with recorded passes", f"{passing} of {len(evidence)}",
                  border=True, help="Saved checkpoint reports, not a fresh test of today's code.")
        st.metric("Evaluation groups with linked results", f"{linked} of {len(results)}",
                  border=True, help="Includes coding agreement; does not establish product safety.")
        st.metric("Independent chat safety result", "Pending", border=True,
                  help="No held-out evaluation of the current chat is linked here.")

    if passing != len(evidence):
        st.warning("Some saved reports are missing or need review. Their outcomes remain unknown.")

    st.subheader("Demonstrated workflow")
    with st.container(horizontal=True):
        for title, icon, text in (
            ("Learn", "school", "Three sourced lessons, practice feedback and session progress."),
            ("Find", "travel_explore", "Official guide passages with the original PDF page."),
            ("Understand", "receipt_long", "Synthetic bills, saved AI reading and MBS references."),
        ):
            with st.container(border=True):
                st.markdown(f"### :material/{icon}: {title}")
                st.caption(text)
    st.caption("These descriptions are supported by saved demonstrations. Current chat "
               "development checks are separate; the historical Ask report covers retrieval.")

    st.subheader("Saved engineering checks")
    st.dataframe(
        [{"Component": item.component, "Status": item.status,
          "Recorded evidence": item.detail} for item in evidence],
        hide_index=True, width="stretch",
    )
    st.caption("Report validation checks expected fields and source identities. "
               "Passing does not establish unseen-document accuracy or learning impact.")

    with st.container(border=True):
        st.markdown("### :material/flag: Remaining evaluation work")
        st.markdown(
            "1. **Freeze and evaluate the current chat.** Keep unseen probes separate and "
            "report refusal recall alongside false refusals.\n"
            "2. **Complete the bill handoff.** Evaluation invoices, separate expected outputs "
            "and their file map are still required by the recorded protocol.\n"
            "3. **Finish research evaluation.** Resolve coding disagreements, complete "
            "classifier baselines and obtain independent retrieval labels.\n"
            "4. **Package the final demonstration.** Rehearse offline using the final version "
            "and carry the measured limitations into the pitch."
        )


def _agreement(measurement):
    with st.container(border=True):
        st.subheader("Human coding agreement")
        if measurement.status != RECORDED:
            st.info(f"{measurement.status}: {measurement.detail}")
            return
        with st.container(horizontal=True):
            for name, label in (("Gap", "Comprehension gap: kappa"),
                                ("Code 1", "Primary category: kappa")):
                row = measurement.values[name]
                with st.container():
                    st.metric(label, f"{row['kappa']:.3f}", border=True,
                              help=f"n={row['n']}; bootstrap 95% interval "
                                   f"{row['ci_low']:.3f} to {row['ci_high']:.3f}.")
                    st.caption(f"n = {row['n']} · 95% interval "
                               f"{row['ci_low']:.3f}–{row['ci_high']:.3f}")
        st.markdown("Agreement is recorded, with substantial uncertainty and unresolved "
                    "disagreements. It does not validate a classifier or the chatbot.")
        st.caption(f"Source: {measurement.file} · {measurement.checked_at_utc}")


def _retrieval(measurement):
    with st.container(border=True):
        st.subheader("How wording changes source retrieval")
        if measurement.status != RECORDED:
            st.info(f"{measurement.status}: {measurement.detail}")
            return
        rows = measurement.values
        gold, dev = rows["gold_guide_wording"], rows["dev_student_wording"]
        with st.container(horizontal=True):
            st.metric("Guide wording: Recall@5", f"{gold['recall_at_5']:.1%}", border=True,
                      help=f"Expected source page in the top five; {gold['n']} scored questions.")
            st.metric("Student wording: Recall@5", f"{dev['recall_at_5']:.1%}", border=True,
                      help=f"{dev['n']} in-house development questions were scored.")
            st.metric("Wording gap", f"{rows['gap'] * 100:.1f} pp", border=True,
                      help="Guide-wording score minus student-wording score, in percentage points.")
        st.bar_chart(
            [{"Question wording": "Guide", "Recall@5 (%)": gold["recall_at_5"] * 100},
             {"Question wording": "Student", "Recall@5 (%)": dev["recall_at_5"] * 100}],
            x="Question wording", y="Recall@5 (%)", horizontal=True, height=210,
        )
        st.caption(f"Scored after the historical gate: {gold['n']}/{gold['probes']} guide "
                   f"questions and {dev['n']}/{dev['probes']} student questions. "
                   "Both sets were written and labelled in-house; neither is held out.")
        st.markdown("The wording gap points to a search limitation. This result measures "
                    "page retrieval, rather than answer accuracy or student understanding.")
        st.caption(f"Source: {measurement.file} · {measurement.checked_at_utc}")


def _results(measurements):
    st.subheader("Evaluation status")
    st.caption("A linked result is evidence for its stated experiment. Missing results remain "
               "unclaimed, and a successful demo does not replace an evaluation.")
    st.dataframe(evaluation_rows(measurements), hide_index=True, width="stretch")
    _agreement(measurements["agreement"])
    _retrieval(measurements["retrieval"])


def _safety(measurement):
    st.subheader("Every response needs a checked path")
    with st.container(horizontal=True):
        for title, text in (
            ("1 · Screen the request", ("Check emergency, clinical, personal-policy and privacy "
                                       "boundaries before retrieving source material.")),
            ("2 · Stay within evidence", ("Use the verified guide for general education. "
                                         "A source passage cannot establish an individual's "
                                         "entitlement.")),
            ("3 · Check the response", ("Block unsupported claims and personal advice. "
                                       "When evidence or a safety decision is unavailable, "
                                       "abstain.")),
        ):
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.caption(text)
    st.info("The current conversational safety score is pending. Historical retrieval checks "
            "and tests of individual rules do not establish a safe chatbot.")

    with st.expander("What the earlier seminar experiment showed"):
        st.markdown("This experiment used **seminar.demo_guardrail**, a separate frozen rules "
                    "demonstration. It provides a lesson about test independence, rather than "
                    "a safety score for the current application.")
        if measurement.status != RECORDED:
            st.info(f"{measurement.status}: {measurement.detail}")
        else:
            rows = []
            for split, label in (("dev", "Development"), ("class", "Classroom")):
                for key, metric in (("refusal_recall", "Refusal recall"),
                                    ("false_refusal_rate", "False-refusal rate"),
                                    ("emergency_recall", "Emergency recall")):
                    row = measurement.values[split][key]
                    rows.append({"Set": label, "Metric": metric,
                                 "Result": f"{row['k']}/{row['n']} ({row['rate']:.0%})",
                                 "95% Wilson interval":
                                     f"{row['ci_low']:.0%}–{row['ci_high']:.0%}"})
            st.dataframe(rows, hide_index=True, width="stretch")
            st.caption("Classroom rates each have n=1. Those results expose failures but "
                       "cannot estimate general performance reliably.")
            st.caption(f"Source: {measurement.file} · {measurement.checked_at_utc}")

    with st.container(border=True):
        st.markdown("**Prototype privacy and scope**")
        st.markdown("Synthetic bills and public sources only. No clinical assessment, "
                    "personal coverage decisions, product recommendations or visa advice. "
                    "Practice completion is session progress, rather than a learning outcome.")


def _provenance(evidence, measurements):
    st.subheader("Trace each claim to its saved report")
    st.caption("Hashes identify report bytes. They are not signatures or proof that a claim "
               "is correct. The dashboard reads named reports and does not run evaluations.")
    for item in evidence:
        label = f"{item.component} · {STATUS_MARK.get(item.status, 'unknown')}"
        with st.expander(label):
            st.markdown(item.scope)
            st.text(f"Status: {item.status}\nChecked (UTC): {item.checked_at_utc or 'Unknown'}\n"
                    f"File: {item.file}\nSHA-256: {item.sha256 or 'Unavailable'}")
    for item in measurements.values():
        with st.expander(f"{item.name} · {item.status}"):
            st.text(f"File: {item.file}\nRecorded (UTC): {item.checked_at_utc or 'Unknown'}\n"
                    f"SHA-256: {item.sha256 or 'Unavailable'}")
    st.caption("Project review: docs/prototype/project_progress_2026-10-14.md. "
               "Raw review snippets, question text and held-out materials are not displayed.")


def render():
    st.title("Project dashboard")
    st.caption("NEXTBEST · Evidence and project progress")
    st.info(SCOPE)

    evidence = load_evidence(ROOT)
    measurements = load_measurements(ROOT)
    overview, results, safety, provenance = st.tabs(
        ["Overview", "Results", "Safety", "Evidence & sources"]
    )
    with overview:
        _overview(evidence, measurements)
    with results:
        _results(measurements)
    with safety:
        _safety(measurements["seminar"])
    with provenance:
        _provenance(evidence, measurements)

    st.divider()
    st.download_button("Download saved engineering summary", summary_bytes(evidence),
                       file_name="prototype_evidence_summary.json", mime="application/json",
                       key="dashboard_download", icon=":material/download:")
    st.caption("Selected engineering metadata only. No model calls, learner telemetry, "
               "bill contents, question text or held-out inputs are accessed by this view.")
