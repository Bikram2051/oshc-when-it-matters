# Presenter evidence Dashboard

Open Dashboard in Streamlit's sidebar.

This page reads six named historical engineering reports: bill_ui, mbs_reference,
mbs_source, policy_source, navigator_ui and coach_ui. Their paths are fixed under
docs/prototype, with the suffix _check.json. Report timestamps, byte hashes and
scope are shown. Nothing is rerun by opening the page.

Recorded checks passed means the required fields in a saved report describe the
expected successful checkpoint. It does not certify the current code or prove
independent performance. A missing or inconsistent report remains unknown.
Hashes identify the report bytes; they are not signatures or proof of correctness.

The JSON download contains selected metadata and explicit evaluation gaps, not
raw report contents. No bills, questions, credentials or learner records are
included. The Dashboard does not read held-out data, make model calls or collect
usage telemetry. Independent evaluations are shown as Not linked here, without
inventing metric values or asserting that no results exist elsewhere.

Tests use synthetic report fixtures in temporary directories. The integration
script checks the six existing project reports, page rendering and unchanged
input report hashes, protected files and budget. Its own output is not one of the
six reports shown by the Dashboard.

This is an evidence browser, not the planned usage-telemetry system. Conversation
safety, held-out accuracy and learning effectiveness require separate evaluation.
