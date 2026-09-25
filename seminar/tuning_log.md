# Demo gazetteer tuning log (dev probes only, SHA-256 e9d96781)

Scope: `seminar/demo_guardrail.py`, tuned against the 44 frozen development probes in `seminar/oshc_seminar_dev_probes.csv`. The development set contains 17 answer, 17 refuse and 10 escalate examples. This tuning belongs only in the seminar copy and must not flow back into `oshc/guardrail.py`.

Full probe SHA-256: `e9d96781764a208ac61939ef3045ef1cdcbd9bb3067bf04c0eae33c54d1e20c5`.

Starting branch: `seminar/eval-demo`. Starting commit: `43a691f`.

The archive names below are relative to `seminar/results/tuning/`. Counts are from the scorer outputs recorded during development.

| Iter | File | What changed | Dev after (refusal / false refusals / emergency) |
| --- | --- | --- | --- |
| 0 | iter0_untuned.json | Nothing: exact copy of the project detection lists and logic. | 0/17, 2/17, 3/10 |
| 1 | iter1_terms_dropped.json | Replaced the term loop with three emergency regexes; original emergency terms were no longer checked. This introduced regressions. | 0/17, 0/17, 3/10 |
| 2 | iter2_terms_restored.json | Restored the original emergency term loop alongside the three regexes for choking, collapse and bleeding that does not stop. Kept emergency checks ahead of clinical and advice checks. | 0/17, 2/17, 6/10 |
| 3 | iter3_emergency.json | Added four emergency patterns for combined face, arm and speech changes; airway swelling with breathing difficulty; excess medication with drowsiness; and inability to stay safe. | 0/17, 2/17, 10/10 |
| 4 | iter4_clinical.json | Added patterns for personal procedure decisions, clinician choice, dose calculation, antibiotic selection, diagnosis from results or symptoms, and medication changes. | 7/17, 2/17, 10/10 |
| 5 | iter5_advice.json | Added patterns for guaranteed reimbursement, personal policy selection, pre-existing condition decisions, waiting periods, visa compliance, impersonated claim approval, definite coverage and forced coverage statements. | 17/17, 2/17, 10/10 |
| 6 | iter6_false_refusals.json | Added narrow context checks that skip only the generic word "emergency" for qualifying post-care billing or contact-preparation questions. All other checks still run. | 17/17, 0/17, 10/10 |

Decisions:

- False escalations on "emergency" (B012 and B031): retained the word in the term list. For B012, the exception requires past treatment or discharge, a billing or claim context, and an explicit statement of no symptoms now. For B031, it requires saving a contact number and an explicit statement that nobody needs help now. Recognised active requests for emergency help disable the exception. The helper skips only this one keyword; it does not immediately allow the question. Emergency regexes, other emergency terms, clinical checks and advice checks remain active.
- Additional emergency regex layer: some development examples describe an emergency without using the original keywords. Added seven patterns alongside the original terms, rather than replacing them. This changes the demo's detection structure beyond editing the original three lists. The order remains emergency checks first, then clinical refusal, then advice refusal. The separate demo copy keeps this development work out of the project guardrail.

Regression story for the talk:

Iteration 1 still scored 3/10 on emergency recall, but it passed different probes. The new regexes caught B004, B008 and B024 while the dropped term loop broke B010, B015 and B029. Chest pain was routed to clinical refusal; "can't breathe" and "seizure" were allowed. The aggregate recall alone hid these regressions. Inspecting the per-probe results exposed them. Restoring the term loop raised emergency recall to 6/10 before any further emergency patterns were added.

The emergencies-allowed metric was 7/10 at iteration 0, 6/10 at iteration 1, 4/10 at iteration 2 and 0/10 from iteration 3 onward. At iteration 1, the clinical refusal explains why 3/10 escalated plus 6/10 allowed did not account for all ten emergency probes.

Authorship and disclosure:

The demo rules were edited by hand using AI-proposed patterns. ChatGPT proposed the regex additions and context helper and assisted with debugging and checks. Bikram manually applied the changes, ran the scorer and reviewed the results. This log was also drafted with ChatGPT assistance. "By hand" describes how the edits were applied, not independent human authorship of every rule.

Disclosure slide wording: "Demo rules edited by hand using AI-proposed patterns, then iteratively tested on 44 frozen development probes. ChatGPT assisted with rule design, debugging and documentation; Bikram applied the edits and ran the scorer."

Interpretation:

The final development result is 44/44 matching the expected class: 17/17 refusals, 0/17 false refusals and 10/10 emergency escalations, with 0/10 emergencies allowed. In this scorer, false refusals include any blocked answer probe, including a false emergency escalation.

The displayed nominal 95% Wilson intervals are [0.82, 1.00] for refusal recall, [0.00, 0.18] for false refusals, [0.72, 1.00] for emergency recall and [0.00, 0.28] for emergencies allowed. The lower endpoints are not guaranteed minimum performance. These same development probes were repeatedly used to choose rules, so the intervals do not establish performance bounds on independent questions. The class set will test the frozen rules on new examples.

Freeze convention:

- Iterations 0-6 record development history. They are not the talk's rungs.
- Talk rung 1 is the final tuned demo, rerun into `seminar/results/rung1_demo_dev.json` and frozen at Git tag `seminar-rung1`.
- Talk rung 2 is the class set evaluated against that same frozen version.
- Create the tag only after the final rerun still reports zero misses and the staged changes have been reviewed. After tagging, do not retune the rules for the class set.
