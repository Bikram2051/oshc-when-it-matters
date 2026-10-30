# NextBest frozen demo — 15 October 2026

Historical source-only release. The subsequent [live Haiku path](live_chat.md)
supersedes normal chat behavior. This document and its evaluation artifacts are
retained without attributing their scores to the new generated-answer version.

The demo includes six connected pages, direct source-bound answers, interactive
Journey Coach activities, a numeric bill explanation and a results dashboard.
The final chat implementation is bound by `chat_freeze_release_final_2026-10-15.json`.
The release package verifies those exact runtime bytes before accepting its proof.

## What is ready to demonstrate

- Ask NextBest accepts a student's general OSHC question. Eight fixed explanation
  topics show a direct answer and supporting guide columns. Every message passes
  emergency, clinical/personal-advice, privacy and scope checks before source access.
  Curated sentences and excerpts must bind to the verified source. No model call.
- Journey Coach has Learn, Practise and Take action tabs, fictional scenarios,
  first-attempt tracking, session progress, saved checklists, reminder downloads,
  previous/next moments and a direct link to each source page.
- Bill Explainer reads labelled tables, shows how line charges form the total,
  explains provider payment and balance separately from insurer benefits, and
  offers a line walkthrough and checklists. It retains numeric/date/item fields
  with generic descriptions; names and original narrative are omitted.
- The dashboard separates historical evidence, development checks, fresh automated
  evaluation, measured failures and controls that still need production work.

The supplied test receipt now reads two charges (AUD 95 and AUD 150), service date
14 October 2026, total AUD 245, settled AUD 245, remaining balance AUD 0 and GST
AUD 0. Insurer benefit and actual insurance gap stay unknown. Its date falls after
the verified MBS comparison window, so no current fee comparison is asserted.
The original attachment is excluded from the repo and demo archive.

## Evaluation completed

| Final experiment | Recorded result | Interpretation |
| --- | --- | --- |
| Fresh unseen chat: required refusals | 24/24; 95% Wilson CI 86.20–100% | Separate automated assessor; no source access on refused cases |
| Fresh unseen chat: false refusals | 6/20; 30%; CI 14.55–51.90% | All valid general questions remain in the denominator |
| Fresh unseen chat: emergencies | 6/6; CI 60.97–100% | Explicit emergency route, scored separately |
| Independent guide-column hit@5 | 23/25; 92%; CI 75.03–97.78% | Source-only automated labels; MRR@5 0.80 |
| All 50 retrieval questions | 23/50; 46% | Includes 25 unsupported MBS questions as misses |
| Majority classifier macro-F1 | 0.0964; bootstrap CI 0.0783–0.1117 | 53 first-person records; seven classes |
| TF-IDF/logistic classifier macro-F1 | 0.3012; CI 0.2169–0.3522 | Grouped five-fold predictions; automated adjudication |
| New synthetic invoice micro-F1 | 0.3226; CI 0.2768–0.3729 | 20 separate automated-custodian invoices; zero invented fields |

The chat had two failed candidates before this final version. Their first scores
are retained: candidate 1 had 15/20 false refusals and 3/6 emergencies; candidate 2
had 17/20 false refusals and 6/6 emergencies. Both refused 24/24 unsafe requests.
Those packs were retired after inspection. A fresh assessor wrote the final pack
without seeing implementation, tests or previous probes. A separate code review
then found and fixed an informational-prefix clinical bypass and typographic
apostrophe emergency miss before the final pack was executed. The last freeze
precedes execution; it does not claim to precede all assessor authoring. Different
packs are not a paired experiment and cannot establish an improvement effect.

The final implementation was not changed after its first final-pack score.
The final 42 visible development probes remain separate: 18/18 refusal recall,
1/16 false refusals and 6/6 emergency escalation. No provider or composer call was
made in either evaluation. Finite selected probes do not certify clinical safety.

The retrieval assessor used only the source PDF/XML and known questions before
freezing labels. Ambiguity on 31 queries, two exact duplicate groups (48 distinct
question texts) and unsupported MBS questions remain reported. Queries themselves
were previously known. The research hybrid retriever was not scored: its dense
model was not provisioned locally, and source-item locators do not uniquely map
to the research XML chunking without a new mapping protocol. No hybrid score is
invented or substituted with a guide-only result.

The invoice set has 20 inputs, 20 separate expected outputs, a file map, a manifest,
source/generator hashes and a custodian authoring record. Predictions were saved
before truth was loaded. Its narrative service layouts expose an actual reader
limitation: the original and current table readers scored the same low F1. This
set is a new automated experiment, not the historical human custodian's missing
held-out set. No tuning on its truth or replacement of its first score occurred.

87 derived coding decisions were made by an automated reviewer, covering the
recorded disagreement IDs. Original workbook labels are untouched. Seven used
examples are excluded; two are first-person records, leaving 53 for evaluation.
Duplicate/thread groups stay in one fold, and rare classes remain in the fixed
seven-class macro average. Historical human primary kappa remains 0.4173.
Automated adjudication is not consensus attributed to Bikram, Minhaj or Aayush.

## Data security answer for the presentation

“The prototype processes invented invoices locally and in memory. It does not
upload bill content to a model or store it in a bill database. Retained results
and downloads omit names, identifiers, provider identities and original service
descriptions. Upload size/page bounds, local binding, XSRF/CORS checks, disabled
telemetry, offline operation and Clear controls reduce exposure. Original input
temporarily occupies browser/server memory; we do not claim secure RAM erasure.
Real-patient deployment would require authenticated hosting, transport encryption,
access and retention controls, and an independent security/privacy review.”

See `security.md` for implemented controls and their verification. No production
security certification, insurer approval or legal compliance sign-off is claimed.

## Demo order and reproducibility

1. Journey Coach: choose a moment, try a scenario, save a checklist and open its
   source page. Session completion is not a measured learning outcome.
2. Ask NextBest: ask how to make a claim; read the direct answer and supporting
   passage. Try a personal coverage question to show the refusal boundary.
3. Bill Explainer: choose “Paid receipt: dated service lines”; explain settlement
   versus unknown insurer benefit. Show retained fields and Clear.
4. Use the September GP example for the explicitly selected historical MBS reference.
5. Dashboard: show final unseen refusal recall alongside false refusals, retrieval,
   classifier and invoice findings, then the privacy controls and remaining limits.

`scripts/evaluate_unseen_chat.py` requires the frozen external pack hash and a new
output path; `--freeze` selects an exact implementation freeze. Probe packs remain
external and separate from the visible development set. `eval.run_all` runs the
current visible development checks. Independent retrieval uses
`scripts/evaluate_independent_retrieval.py` and its recorded label hash. Classifier
and bill reproduction commands are in the earlier checkpoint and their protocols.
First reports are immutable by the runners. Dashboard files are bound by
`final_results_manifest.json`; only selected aggregate fields are displayed.

The final demo archive excludes raw research text, private workbooks, personal
invoices, evaluation inputs/truth, credentials, provider ledger and Git metadata.
The synthetic bill evaluation handoff is a separate archive with inputs and
expected outputs kept in separate folders.

Human coding consensus, independent real-student questions/shift gap, embedding/LLM
classifier comparisons, the original historical bill handoff, real-invoice accuracy,
learning impact and production security remain unmeasured. The app is a scoped
educational demonstration, with conservative abstention and unsupported invoice
formats clearly visible.
