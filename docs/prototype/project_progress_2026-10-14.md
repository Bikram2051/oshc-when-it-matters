# Project review, 14 October 2026

This review starts from local checkpoint `e71cf18`. Repository files and saved
reports take precedence over earlier walkthrough scripts. The dashboard reads
saved evidence; opening it does not rerun a test, spend API credit or certify the
current working tree.

Delivery update: the refreshed prototype is implemented at `d9a2737`. All 463
repository tests passed after the routing change, and the offline package passed
fresh-environment workflow verification with zero provider calls. See
[the delivery checkpoint](delivery_2026-10-14.md) and
`demo_package_final_check_2026-10-14.json`. The research evaluation gaps below remain.

## Working prototype

- Journey Coach has three sourced English lessons, practice feedback, first-attempt
  tracking, source-page handoff and session-only reset. This is authored learning
  content; adaptive sequencing, translation and measured learning impact are absent.
- Navigator displays fixed-topic guide text and the original physical PDF page.
- Bill Explainer demonstrates text, PDF and cached AI extraction of synthetic
  examples. Missing insurer amounts remain unknown. MBS references are educational
  comparisons and do not determine personal entitlement.
- The 13 October Ask checkpoint accepts free text, checks a guardrail and returns
  source excerpts. It does not compose answers. Its saved report cannot validate a
  later conversational implementation.
- The dashboard now separates Overview, Results, Safety, and Evidence & sources.
  It presents validated engineering metadata, recorded research aggregates and
  remaining work without substituting one type of evidence for another.

## Results actually linked

| Evidence | Recorded finding | Limit |
| --- | --- | --- |
| `data/agreement/agreement_2026-10-13.json` | Gap kappa 0.4176, bootstrap 95% CI 0.2464–0.6015; primary-category kappa 0.4173, CI 0.2542–0.5842; n=53 | Coding disagreements remain; this is not classifier performance |
| `docs/prototype/ask_ui_check.json` | Guide wording Recall@5 0.9583 on 24 scored questions; student wording 0.7857 on 14; gap 0.1726 | Both sets written and labelled in-house; historical retrieval path, not held out |
| `docs/prototype/seminar_guardrail_summary_2026-10-05.json` | Separate seminar rules: dev refusal 17/17 and emergency 10/10; classroom refusal 0/1 and emergency 0/1 | Current application not evaluated; classroom denominators are too small for general estimates |

The seminar summary was derived from the original checkout's
`seminar/results/class_raw_live.json`, keeping only the recorded timestamp,
module identity, aggregate split metrics and original file SHA-256. Raw classroom
questions and per-question outputs were not copied or displayed. The dashboard
shows each rate's existing Wilson interval rather than treating these small
denominators as reliable performance estimates.

The seven named engineering reports retain their existing validation rules in
`oshc/evidence_dashboard.py`. They describe historical checkpoints, including
source audits, sample bill flows and authored lesson navigation. Their hashes
identify saved bytes, rather than proving current-code correctness. The JSON
download preserves that existing engineering-only export contract.

## Remaining evaluation and delivery work

1. **Current conversational safety:** freeze the implementation before an unseen
   evaluation. Report refusal recall, false-refusal rate, emergency performance,
   denominators and uncertainty. Development regression tests are separate evidence.
   The original `oshc/guardrail.py` clinical-rule review is a white-box development
   finding, not a refusal-recall estimate.
2. **Extraction:** the 10 October handoff still requests synthetic invoice inputs,
   separate truth and a document-to-family file map. The scoring protocol and scorer
   exist, but no scored held-out extraction report was found. Hash verification of
   two parameter files does not supply the missing evaluation inputs. The freeze
   record also documents parameter exposure; any independence claim must disclose it.
3. **Retrieval:** the independent review instructions require returned relevance
   labels before the frozen evaluation. No completed independent result was found
   in the workspace or the original checkout's `eval` directory. The historical
   Ask page-level scores do not validate the separate hybrid retrieval pipeline.
4. **Classification:** `oshc/classifier.py` and `eval/run_all.py` remain skeletons.
   Macro-F1 and the review-to-question shift gap are unreported. Resolve/document
   coding disagreements, freeze labels and apply the rare-class policy before
   attempting grouped cross-validation. Do not train or tune on held-out material.
5. **Learning impact:** no real-student testing is authorised this semester.
   Report this limitation; practice completion and functional tests cannot replace
   a learning-outcome study.
6. **Demonstration:** build a new offline package from the final version, rehearse
   the full student journey, retain its checksum and prepare the pitch using the
   actual saved results. The existing package/checkpoint predates today's changes.

No held-out parameters, extractor generator, private probe text or real student
records were inspected for this review. No evaluation score was generated by
running new development examples. The latest request brings prototype delivery
forward to 14 October; the earlier walkthrough planned a freeze on 15 October and
a pitch on 19 October.
