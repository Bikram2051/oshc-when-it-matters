# NextBest final demo checkpoint

Historical checkpoint. The [15 October frozen release](final_demo_2026-10-15.md)
supersedes the pending-work status below and preserves the failed candidate scores.

## What is implemented

- Ask NextBest screens every complete message before source access. Eight curated
  general answers are bound to specific passages in the verified Member Guide.
  Personal cover decisions, clinical questions, prompt overrides and identifying
  input cannot select a curated answer. No generative model is called.
- Journey Coach provides Learn, Practise and Take action tabs, three moments,
  fictional scenarios, first-attempt tracking, saved checklists and a downloadable
  reminder. Checklist completion is not a measured learning outcome.
- Bill Explainer reads labelled text/PDF tables, including dated Fee/GST rows and
  receipt footers. It explains charges, provider settlement and remaining balance
  separately from insurer benefits and actual insurance gaps. The frozen research
  extractor remains unchanged; the prototype uses extract_document.py.
- The dashboard shows final selected results alongside historical evidence,
  uncertainty and scope. Changed report bytes suppress the final numeric cards.

## User-supplied invoice finding

The selectable-text test invoice contained two rows: item 23 at AUD 95 and item 36
at AUD 150. The initial reader found these charges but missed row service dates,
the total-gross label and receipt footer. The current reader obtains a service
date of 14 October 2026, total charge AUD 245, amount settled AUD 245, remaining
balance AUD 0 and GST AUD 0. It does not invent insurer benefits or an insurance
gap. Provider identity and invoice narrative are removed from retained UI data.
The original attachment is not copied into the repository or demo archive.

The service date is after the MBS snapshot's verified comparison window ending
28 September 2026. The app therefore declines a dated fee comparison, rather
than asserting that an older reference is current.

## Recorded evaluation

| Measure | Result | Interpretation |
| --- | --- | --- |
| Current chat refusal recall | 18/18; Wilson 95% CI 82.41–100% | Visible development probes, not unseen validation |
| Current chat false refusals | 1/16; 6.25%; CI 1.11–28.33% | All designated general questions remain in denominator |
| Emergency escalation | 6/6; CI 60.97–100% | Selected development emergencies only |
| Privacy boundary | 4/4; CI 51.01–100% | No source access on these cases |
| Guide source-page hit@5 | 24/25; 96%; CI 80.46–99.29% | Existing in-house page labels; 25 MBS queries outside this pipeline |
| Majority classifier macro-F1 | 0.0964; grouped bootstrap CI 0.0783–0.1117 | 53 first-person records, fixed seven-class average |
| TF-IDF/logistic classifier macro-F1 | 0.3012; CI 0.2169–0.3522 | Automated adjudication; grouped five-fold predictions |
| New synthetic invoice field micro-F1 | 0.3226; bootstrap CI 0.2768–0.3729 | 20 independently authored automated-custodian invoices; zero invented values |

The invoice evaluation is a real negative finding. Its four families mostly use
narrative service blocks, which the labelled-table reader does not support.
Both the original extractor and current prototype obtained the same score. The
first outputs were saved and hashed before truth was loaded; no tuning on these
invoices or replacement of the first report occurred. This prevents a successful
demo invoice from being presented as general extraction accuracy.

Historical human coding agreement (n=53, primary-category kappa 0.4173) is retained.
The separate automated reviewer made 87 derived coding decisions, including all
22 previously recorded primary-code disagreements. They are automated
adjudication, not agreement or consensus attributed to Bikram, Minhaj or Aayush.
Original workbook values remain untouched. Seven previously used example records
are excluded from evaluation; two belong to the 55 first-person records, leaving
53. Repeated snippets and thread IDs stay in one fold. Rare classes are retained,
so some folds cannot include every class. No hyperparameter search was performed.

## What cannot be claimed

Independent safety and retrieval assessors stopped at the account usage limit
before completing frozen labels. No independent unseen chat score or independent
retrieval relevance score was produced. The chat implementation freeze is saved,
but visible development probes cannot satisfy the original unseen release gate.
The existing in-house retrieval labels were not relabelled as independent.

Human consensus, a review-to-real-student-question shift gap, embedding/LLM
classifier comparisons, the historical custodian's original held-out extraction
study, synthetic-to-real accuracy and learning impact remain unmeasured. The new
automated invoice handoff is a distinct experiment, not a backdated substitute
for the historical protocol. Real-student testing remains outside scope.

## Reproduction and evidence

- `python -m eval.run_all --out NEW_REPORT.json` checks the chat freeze and runs
  current development chat/source-page evaluation without provider calls.
- `python -m eval.classification --dataset FROZEN_DATASET --out NEW_REPORT.json`
  runs grouped local baselines. Raw workbook text and the frozen dataset stay
  outside the repo. `scripts/prepare_classifier_data.py` reconstructs the dataset
  from the original workbooks and the frozen decisions.
- `scripts/evaluate_current_bills.py --handoff HANDOFF --out NEW_RUN --report NEW_REPORT`
  writes and hashes all predictions before the scorer loads separate truth.
- Named result files are bound by `final_results_manifest.json`; aggregate fields
  only are displayed. Original first reports are retained.
- The source code, cached examples and verified source snapshots are packaged
  separately from raw research records, evaluation inputs and expected outputs.

## Demo sequence

1. Home → Journey Coach: choose a moment, answer a scenario, save a checklist,
   download the reminder and open its source page.
2. Ask NextBest: ask how to claim; read the direct answer and supporting pages.
   Submit a personal coverage question to demonstrate the refusal boundary.
3. Bill Explainer: use “Paid receipt: dated service lines”. Explain the AUD 245
   settlement versus the unknown insurer benefit. Show retained fields and Clear.
4. Use the September GP example for the explicitly selected MBS comparison.
5. Dashboard → Results and Safety: present the measured limitations and privacy
   controls. Do not describe the prototype as production-ready medical software.
