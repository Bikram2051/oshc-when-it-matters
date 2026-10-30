# Project dashboard

Open **For partners** in the sidebar, then **Research evidence and evaluation results**
(or go to `/Dashboard`). It is a presenter view of
saved evidence and remaining work, rather than a live usage-telemetry system.

## Four views

- **Overview:** recorded engineering checks, demonstrated workflow and the
  remaining evaluation/delivery tasks.
- **Results:** the recorded 53-record coding-agreement study, its bootstrap
  intervals, the historical in-house source-retrieval wording gap, and an explicit
  evaluation-status table. Missing results remain unclaimed.
- **Safety:** response-boundary requirements and the separate historical seminar
  experiment, including denominators and Wilson intervals. Neither validates the
  current chat's safety.
- **Evidence & sources:** named report paths, timestamps, byte hashes and scope.

Engineering reports are defined by `SPECS` in `oshc/evidence_dashboard.py`.
Currently these cover Bill Explainer, MBS comparisons, MBS source audit, policy
search, Navigator, Journey Coach and the historical Ask page. Their paths are
fixed under `docs/prototype`, with the suffix `_check.json`; their count is read
from that specification rather than hardcoded by the dashboard.

Recorded checks passed means that a saved report contains the expected successful
checkpoint fields and source identities. It does not certify the current code or
prove independent accuracy. Missing/inconsistent reports remain unknown. Hashes
identify bytes; they are not signatures or proof of correctness.

Aggregate research reports are loaded through `oshc/project_progress.py`. Only
selected numeric fields, scope and metadata reach the UI. Raw review snippets,
individual coding disagreements and classroom questions are not displayed. The
seminar summary records a separate frozen module, not the current application.
See `project_progress_2026-10-14.md` for the evidence review and pending work.

The engineering JSON download preserves its selected-metadata contract. It
contains no bill contents, learner questions, credentials or learner records.
The dashboard does not read held-out data, make model calls or collect telemetry.
Its current chat-safety result remains pending rather than borrowing a score
from the earlier retrieval or seminar experiment.

## Recheck the current dashboard

From the repository root, using the project virtual environment:

```powershell
$env:OSHC_OFFLINE = "1"
$env:OSHC_ENABLE_LIVE = "0"
python scripts/prototype_check_dashboard_ui.py --out docs/prototype/dashboard_refresh_check_2026-10-14.json
```

Use a new `--out` path for every run. The script refuses to overwrite any existing
report, including the historical `dashboard_ui_check.json` default. It follows the
current `views/5_Dashboard.py` route, checks tabs and displayed statuses against
validated inputs, and verifies that source reports remain unchanged.

The integration check blocks provider calls, model calls and budget construction.
It fingerprints only an explicit list of public source files and the replay-cache
directory; it does not initialise or inspect the private spending ledger, read
held-out parameters, or rerun any historical engineering/evaluation experiment.
Its output is a new dashboard check and is not added to the input-report set.

Unit tests use synthetic report fixtures and also check the real aggregate-report
display. Independent accuracy, current conversational safety and learning
effectiveness still require their own evidence.
