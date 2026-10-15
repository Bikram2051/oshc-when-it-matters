"""Present saved project evidence without rerunning checks or calling providers."""
from pathlib import Path

import streamlit as st

from oshc.evidence_dashboard import PASSED, load_evidence, summary_bytes
from oshc.project_progress import RECORDED, evaluation_rows, load_measurements
from oshc.final_results import load_final

ROOT = Path(__file__).resolve().parents[1]
STATUS_MARK = {PASSED: "recorded pass", "Missing report": "missing", "Needs review": "review"}


def _overview(evidence, measurements):
    passing = sum(item.status == PASSED for item in evidence)
    results = evaluation_rows(measurements)
    linked = sum(row["Status"] == RECORDED for row in results)
    final = load_final(ROOT)
    with st.container(horizontal=True):
        st.metric("Saved checks with recorded passes", f"{passing} of {len(evidence)}",
                  border=True, help="Saved checkpoint reports, not a fresh test of today's code.")
        st.metric("Historical result groups linked", f"{linked} of {len(results)}",
                  border=True, help="Earlier report linkage only. Final chat, retrieval, classifier and bill scores appear in Results.")
        st.metric("Historical source-only chat",
                  (f"{final['release_chat']['refusal_recall']['k']}/{final['release_chat']['refusal_recall']['n']} refusals"
                   if final else "Unavailable"), border=True,
                  help="Historical source-only implementation. These scores do not validate live Haiku generation.")

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
        st.markdown("### :material/flag: Final demo checkpoint")
        st.markdown(
            "**Implemented:** Haiku answers with input/output checks, interactive learning checklists, "
            "dated invoice-table reading and privacy minimisation.\n\n"
            "**Evaluation:** current development checks, local classifier baselines and a "
            "separately authored synthetic invoice handoff are recorded in Results when verified.\n\n"
            "**Historical automated checks:** source-only chat probes and retrieval labels. "
            "**Unmeasured:** live model performance, human safety validation, real-student learning impact and production security."
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
    _final_results()


def _final_results():
    st.subheader("Historical source-only prototype evaluation")
    saved = load_final(ROOT)
    if saved is None:
        st.info("The final evaluation reports are missing or do not match their manifest.")
        return
    st.caption("Earlier source-only implementation · independent automated assessors · does not evaluate live Haiku")
    st.markdown("**Recorded unseen check of the source-only chat**")
    with st.container(horizontal=True):
        for key, label in (("refusal_recall", "Unseen refusal recall"),
                           ("false_refusal_rate", "Unseen false refusals"),
                           ("emergency_recall", "Unseen emergency recall")):
            value = saved["release_chat"][key]
            st.metric(label, f"{value['k']}/{value['n']} ({value['rate']:.1%})", border=True,
                      help=f"Wilson 95% interval {value['ci95'][0]:.1%} to {value['ci95'][1]:.1%}; automated assessor, selected probes only.")
    st.caption("Earlier candidate failures are retained in the release record. These finite probes "
               "do not establish clinical safety; unsupported wording can still abstain.")
    independent = saved["independent_retrieval"]
    st.markdown(f"**Independent source labels:** correct column in the top five for "
                f"{independent['k']}/{independent['n']} guide questions; "
                f"MRR@5 {saved['independent_retrieval_mrr']:.2f}. "
                "One source-only automated assessor; known queries, ambiguity and duplicates retained. "
                f"Including unsupported MBS questions: {saved['all_50_retrieval']['k']}/50.")
    with st.expander("Visible development checks"):
        st.caption("These cases were visible during development and remain separate from unseen probes.")
        _development_metrics(saved)
    _other_final_metrics(saved)


def _development_metrics(saved):
    with st.container(horizontal=True):
        for key, label in (("refusal_recall", "Development refusal recall"),
                           ("false_refusal_rate", "Development false refusals"),
                           ("emergency_recall", "Development emergency recall")):
            value = saved["chat"][key]
            st.metric(label, f"{value['k']}/{value['n']} ({value['rate']:.1%})", border=True,
                      help=f"Wilson 95% interval {value['ci95'][0]:.1%} to {value['ci95'][1]:.1%}; selected probes only.")


def _other_final_metrics(saved):
    st.markdown("**Bill extraction exposes a format limitation.** The separate automated custodian "
                f"provided {saved['bill_n']} synthetic invoices; field micro-F1 was {saved['bill_f1']:.3f}. "
                "Many narrative layouts are unsupported. Use labelled tables and check the retained numbers.")
    with st.container(horizontal=True):
        st.metric("Majority classifier: macro-F1", f"{saved['classifier']['majority']:.3f}", border=True)
        st.metric("TF-IDF + logistic regression", f"{saved['classifier']['tfidf_logreg']:.3f}", border=True)
        st.metric("Guide page hit@5", f"{saved['retrieval']['k']}/{saved['retrieval']['n']}", border=True)
    st.caption(f"Classifier: {saved['classifier_n']} first-person records, automated adjudication, "
               "grouped five-fold predictions; seven classes retained, rare-class uncertainty. "
               "Retrieval uses in-house labels; 25 MBS questions are outside the guide-only pipeline.")


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
    st.info("Live Haiku checks each input and complete draft before display. Its model performance "
            "has not been measured by the historical source-only chat scores in Results. "
            "Small synthetic rule tests do not establish clinical or production safety.")

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
        st.markdown("Bill processing stays on this computer. The displayed/downloaded result "
                    "omits names, identifiers, provider identities and original descriptions. "
                    "Uploads temporarily occupy session memory; Clear removes the app result and upload widget. "
                    "There is no bill database or bill-content logging, and telemetry is disabled.")
        st.caption("Bound to 127.0.0.1; CORS/XSRF enabled; 10 MiB/20-page bounds; image-only PDFs rejected. "
                   "No OCR or cloud transfer. Real-patient use would need authenticated hosting, transport encryption, "
                   "access controls, retention controls and independent security review.")


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
    st.caption("Current live specification: docs/prototype/live_chat.md. Historical review: docs/prototype/project_progress_2026-10-14.md. "
               "Raw review snippets, question text and held-out materials are not displayed.")


def render():
    st.title("Project dashboard")
    st.caption("NEXTBEST · Evidence and project progress")
    st.info("Saved project evidence and frozen automated evaluations. Opening this page does not "
            "rerun checks. Each result retains its scope, uncertainty and limitations.")

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
