# OSHC When It Matters

Team D5 prototype. COS70008 Technology Innovation Research and Project, Swinburne University of Technology. Industry partner: Medibank.

Bikram Bhattarai, Md Minhaj Rahman, Aayush Khade. Supervisor: Dr Eureka Priyadarshini.

**NextBest** is a Streamlit learning prototype with guarded live Haiku chat:

- **Journey Coach:** three sourced lessons, practice scenarios, resumable progress and saved action checklists.
- **Navigator:** practical service-navigation steps and official links, plus guide passages alongside original PDF pages.
- **Bill Explainer:** labelled synthetic invoice tables, receipt explanations, privacy minimisation and MBS comparisons.
- **Ask NextBest:** custom Haiku answers with input screening, verified citations and output safety review.
- **Project dashboard:** Overview, Results, Safety, and Evidence & sources tabs.

The [live chat specification](docs/prototype/live_chat.md) describes the current
three-stage model path. The [earlier frozen source-only release](docs/prototype/final_demo_2026-10-15.md)
records historical evaluation results; those scores do not validate live generation.
Read the [security controls](docs/prototype/security.md) before demonstrating uploads.

## Live configuration

Run the setup for your platform below. It restores official public sources only
when their hashes match the pinned snapshots and runs tests with live calls disabled.
Source files stay outside Git. Restore them later with `python scripts/bootstrap_sources.py`.

Set `OSHC_API_KEY` in the ignored repository-root `.env`, the server environment,
or `.streamlit/secrets.toml`. Never put the value in source code or GitHub. Normal
application mode uses `OSHC_OFFLINE=0` and `OSHC_ENABLE_LIVE=1`.
Use the existing budget ledger by setting `OSHC_BUDGET_LEDGER` to its absolute path.
For a genuinely new installation only, initialise the USD 8 allowance once with
`python -m oshc.llm_budget init`. Do not delete or reset an existing ledger.

Start Windows with `./Start_NextBest.ps1`; on other platforms run
`streamlit run app/Home.py`. Each accepted answer requires an input review,
grounded generation and output review. API or safety failures return a fixed
abstention. Student questions and drafts bypass disk caching. Bills are read
locally regardless of chat mode. Keep using invented invoices for this prototype.

---

## Setup

Windows:

```powershell
git clone https://github.com/Bikram2051/oshc-when-it-matters.git
cd oshc-when-it-matters
.\setup.ps1
```

macOS or Linux:

```bash
git clone https://github.com/Bikram2051/oshc-when-it-matters.git
cd oshc-when-it-matters
./setup.sh
```

Then:

```bash
streamlit run app/Home.py
python -m pytest
```

On Windows, `./Start_NextBest.ps1` launches the live application on port 8502.
Use `-Python 'path/to/environment/Scripts/python.exe'` to reuse an existing project
environment. The entry point defaults to `OSHC_OFFLINE=0`, `OSHC_ENABLE_LIVE=1`, and
`claude-haiku-4-5-20251001`. A configured API key and existing budget ledger are
required for paid calls; a missing connection returns a fixed explanation.

The pinned Member Guide PDF and MBS XML are deliberately gitignored. Restore them
with `python scripts/bootstrap_sources.py`, which downloads only the official
snapshots matching `corpus/MANIFEST.csv`. The guide-backed pages abstain when source verification
fails; emergency responses do not require the guide.

Development smoke checks, with offline flags set:

```powershell
$env:OSHC_OFFLINE = "1"
$env:OSHC_ENABLE_LIVE = "0"
python scripts/prototype_check_student_chat.py --out chat_check.json
python scripts/prototype_check_dashboard_ui.py --out dashboard_check.json
```

Each check refuses to overwrite an existing report. For a bounded synthetic live
connection check, run `python scripts/check_live_chat.py --live --out NEW_REPORT.json`
after configuring the key. This checks the connection and answer release path; it
does not measure unseen safety or model accuracy. The final source-only reports
are linked from the historical release above. `python -m eval.run_all` remains an
unfinished research entry point. Independent human consensus and the original
controlled extraction study must not be presented as complete.

## Student questions and response boundaries

Every submitted message, including starter questions and later turns, goes through
the same guardrail service **before** loading the guide or searching. Emergency,
clinical and personal-benefit requests stop. Sensitive, unsupported or ambiguous
requests receive a fixed clarification. There is no refusal-to-search shortcut.

Allowed live responses contain a short Haiku answer with citations and supporting
passages checked against the verified guide and linked to physical PDF pages.
The semantic input review, grounded draft and final output audit are separate
mandatory calls; local safety and exact-quotation checks also apply.
Earlier messages are not silently reused as context; each follow-up names its topic.
The original baseline guardrail remains frozen. Passing mocked regression tests
does not establish the accuracy of the live model or its safety decisions.

The latest ten turns stay in Streamlit session memory until cleared or the session
ends. Rejected messages are withheld, and raw rule matches are removed from response
metadata. The accepted current question and selected public passages are sent to
Anthropic; previous turns and bill uploads are not. Live questions and answers
bypass the local disk cache. Privacy screening is best effort, and the interface
asks students to remove personal details before submitting. See
[the live chat specification](docs/prototype/live_chat.md) and the
[historical source-only specification](docs/prototype/student_chat.md).

---

## Four rules that are not negotiable

**1. No real document, ever.** No real invoice, statement, policy number, member number or student. Synthetic documents from `scripts/make_invoices.py` and public sample images only. This is the Privacy Act control and it is also why the build is small enough to finish.

**2. Never commit a secret.** `.env` is gitignored and CI fails the build if it becomes tracked. The API key is held by Bikram; copy `.env.example` to `.env` and paste it there.

**3. Public sources and private runtime data stay outside Git.** `corpus/` contains pinned third-party snapshots restored during setup. Only the three existing synthetic research cache records are retained in Git. New runtime caches, student questions, generated answers and the private budget ledger are excluded; live chat bypasses the response cache entirely.

**4. Money and safety code is tested before it is written.** `oshc/arithmetic.py` and `oshc/guardrail.py` had their tests written first. If you change either, change the test first. Never relax a failing test in these two files.

---

## Ownership

| Area | Owner | Reviewer |
|---|---|---|
| `oshc/schemas.py` (frozen interfaces) | All three, by agreement | Change requires minutes entry |
| `oshc/arithmetic.py`, benefit rules table, MBS table | Bikram | Aayush |
| `oshc/classifier.py`, `eval/` | Bikram | Minhaj |
| `oshc/billexplainer/extract_rules.py`, `extract_llm.py`, `mbs.py` | Bikram | Aayush |
| `oshc/guardrail.py`, LLM rubric layer | Aayush | Bikram |
| `oshc/llm.py`, `oshc/retrieval.py`, `oshc/composer.py` | Aayush | Minhaj |
| Corpus snapshot, chunker, retrieval gold set | Aayush | Bikram |
| `scripts/make_invoices.py` | Minhaj | **Aayush, never Bikram** |
| `oshc/telemetry.py`, dashboard, host pages, Coach copy | Minhaj | Aayush |
| Setup scripts, lock file, CI | Minhaj | Aayush |

The generator reviewer rule is not a preference. Bikram writes the extractor that the generator's held-out families score; if he reads the generator he sees the held-out parameters and the evaluation stops meaning anything.

---

## Planned research evaluation separation

The original study protocol requires these separations. This describes the
protocol, not a claim that its human coding or original held-out study is complete:

1. **Invoice layout families.** Four families. `specialist_gap` and `hospital_mixed` are frozen held-out. Their parameters live in `data/heldout/`, gitignored, released on evaluation day. Minhaj freezes them before Bikram writes extraction code.
2. **Guardrail probes.** The dev probe set is in `tests/test_guardrail.py` and is visible to Aayush, who builds the gate. The held-out probe set is authored by Bikram, kept out of the repository, and run once at evaluation. Building against the set you are scored on is not a measurement.
3. **Coding frame.** All 55 first-person records are coded independently by Bikram and Minhaj, kappa reported, disagreements resolved by discussion, consensus labels frozen before any classifier is trained.

The same separation applies to every tool used in development: held-out layout parameters and the held-out probe set are never entered into any of them.

---

## Planned research headline numbers

Fixed in advance so that "done" has a definition.

| Number | Where from | Ship condition |
|---|---|---|
| Cohen's kappa | Coding frame, 55 records, two coders | Reported. Below 0.6, per-class F1 is not claimed |
| Macro-F1 and shift gap | Classifier ladder, stratified 5-fold | Reported against the majority baseline |
| Recall@5 | Retrieval, frozen gold set | Reported |
| Refusal recall, false-refusal rate | Guardrail, held-out probes | **At or above 0.90 or the conversational surface does not ship** |
| Extraction F1 and synthetic-to-real drop | Held-out families and the public sample | The drop is the headline, not the synthetic score |

---

## What this prototype refuses to do

Stated as design decisions, not gaps. Each removes a risk from the Week 5 NIST assessment or a regulatory exposure.

- No user accounts, profiles or persistence of identity.
- No symptom assessment. There is no symptom-to-service code path in this repository.
- No statement about what a particular person's policy will pay. Medibank requires that coverage, claims, medical, visa and product-suitability questions are referred to Medibank, so the wording is always "the PDS states" or "this document shows", never "you are covered". (Earlier project documents cited s 766B of the *Corporations Act 2001* (Cth); that section does not apply, because reg 7.1.07C of the *Corporations Regulations 2001* (Cth) provides that insurance under an overseas student health insurance contract is not a financial product. The rule stands as a client requirement and a safety rule.)
- No real invoice handling.
- No model fine-tuning.
- No native app, and no script tag embedded in a third-party page.

See `D5_technical_architecture_plan_v2.md` for the full plan, and `CONTRIBUTING.md` for the development workflow.
