# Live NextBest demonstration

The [campus demo verification](campus_demo_verification_2026-10-15.json) records
662 passing software tests and the final three-topic live rehearsal. Earlier
development abstentions are retained in that report; this is not an unseen evaluation.

## Before presenting

1. Complete setup and source verification as described in the repository README.
   While PR #23 awaits review, use its `bb/student-chat-dashboard` branch.
2. Configure the private value of `OSHC_API_KEY` in the ignored root `.env` or
   server secrets. Keep `OSHC_OFFLINE=0` and `OSHC_ENABLE_LIVE=1`.
3. Select the existing budget ledger using `OSHC_BUDGET_LEDGER`. Do not reset it.
4. Run `python scripts/check_live_chat.py --live --out NEW_REPORT.json` using a
   new report filename. A successful check exits with code 0. Missing credentials,
   an abstention or a failed check exits with code 2; resolve that before promising
   a live answer. This synthetic check is not an unseen safety evaluation.
5. Start `./Start_NextBest.ps1` on Windows and open `http://127.0.0.1:8502`.
   The Ask page must no longer show the missing-key warning. Use invented
   questions and invoices throughout the presentation.

In VS Code, activate the environment that has the installed project dependencies,
then run `python -m streamlit run app/Home.py --server.port 8502` from the repository
root. Keep that terminal running throughout the demo. If the new clone's `.venv`
is incomplete, use `./Start_NextBest.ps1 -Python 'path/to/working/python.exe'`.
Journey Coach and Navigator work with live chat enabled; they do not require an
offline-mode restart and do not make model calls for lessons, checklists or browsing.

## Demonstration sequence

- **Home:** introduce the student's three tasks: understand healthcare, understand
  a receipt and ask a general question.
- **Journey Coach:** choose a lesson, answer its practice scenario and tick an
  action in the checklist. Save the checklist, return to My journey plan and
  resume the next unfinished moment. Explain the reason shown after the answer.
- **Navigator:** select GP appointment, phone/video, pharmacy, claiming or card
  preparation. Open the related verified guide topic and its original PDF page.
  Service Finder opens healthdirect; it does not send a question or location.
  Directory information does not confirm personal OSHC cover or appointment availability.
- **Bill Explainer:** upload a labelled synthetic invoice. Explain the printed
  charges, paid amount and outstanding balance. Receipt settlement does not tell
  us the insurer's benefit or the student's final out-of-pocket cost. Show an MBS
  comparison only when the printed item supports it.
- **Ask NextBest:** type a general custom question, such as “What documents are
  generally required to submit a medical claim online?” Wait for the complete
  checked answer, then open its cited passages and Response checks. Every answer
  requires local checks, a model input review, grounded generation and a separate
  model output review. A failed check returns fixed wording instead of a draft.
- **Symptom handoff:** use the fictional prompt “I have a cough and a mild headache.
  Where should I go?” Explain that the fixed handoff offers healthdirect, the
  official Symptom Checker and Service Finder. It does not assess severity or
  select a healthcare service from symptoms. Clear personal symptom disclosures
  stop locally before model or policy-source access; emergency rules take priority.
- **Project dashboard:** distinguish historical source-only evaluation results
  from the new live service. Report refusal recall alongside false refusals;
  mocked regression tests do not measure live model accuracy.

## Data security explanation

“Bill files are processed locally and their names, identifiers and original
descriptions are excluded from retained results. For live chat, the current
locally screened question and relevant public guide passages go to Anthropic.
We do not send bill uploads or earlier chat turns. Questions and drafts bypass
the disk cache, and Clear removes the session transcript. Privacy screening is
best effort, so personal information must be removed before submitting.”

This is a local prototype, not an approved service for real patient data. Do not
claim zero provider retention, certified security or completed independent human
validation. See [the implemented security controls](security.md) and
[the live chat specification](live_chat.md).

## Honest readiness statement

This is a local educational prototype for a supervised group demonstration.
The live connection smoke check and software regressions do not establish clinical
accuracy, real-student learning outcomes or independent human validation. Historical
source-only evaluation figures remain labelled with their original runtime.
