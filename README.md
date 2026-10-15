# OSHC When It Matters

Team D5 prototype. COS70008 Technology Innovation Research and Project, Swinburne University of Technology. Industry partner: Medibank.

Bikram Bhattarai, Md Minhaj Rahman, Aayush Khade. Supervisor: Dr Eureka Priyadarshini.

**NextBest** is an offline Streamlit learning prototype with top navigation:

- **Journey Coach:** three sourced lessons, practice scenarios and saved action checklists.
- **Navigator:** saved guide passages alongside the original PDF pages.
- **Bill Explainer:** labelled synthetic invoice tables, receipt explanations, privacy minimisation and MBS comparisons.
- **Ask NextBest:** guarded general questions, curated answers and verified supporting passages.
- **Project dashboard:** Overview, Results, Safety, and Evidence & sources tabs.

The [frozen demo release](docs/prototype/final_demo_2026-10-15.md) records the
features, measured results, reproduction steps and research limitations. Read the
[implemented security controls](docs/prototype/security.md) before demonstrating
bill uploads. Visible development tests do not replace independent validation.

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

On Windows, `./Start_NextBest.ps1` launches the offline demonstration on port 8502.
Use `-Python 'path/to/environment/Scripts/python.exe'` to reuse an existing project
environment. The entry point defaults to `OSHC_OFFLINE=1`, `OSHC_ENABLE_LIVE=0`, and
the model used for the saved bill example. It does not enable paid calls.

The pinned Member Guide PDF and MBS XML are deliberately gitignored. Restore the
privately shared public-source snapshots into `corpus/`, with hashes matching
`corpus/MANIFEST.csv`. The guide-backed pages visibly abstain when source verification
fails; emergency responses do not require the guide.

Development smoke checks, with offline flags set:

```powershell
$env:OSHC_OFFLINE = "1"
$env:OSHC_ENABLE_LIVE = "0"
python scripts/prototype_check_student_chat.py --out chat_check.json
python scripts/prototype_check_dashboard_ui.py --out dashboard_check.json
```

Each check refuses to overwrite an existing report. `python -m eval.run_all` remains
an unfinished evaluation entry point; it does not currently produce five results.
See the project review for the missing independent labels, extraction handoff and
guardrail evaluation. Existing historical reports remain unchanged.

## Student questions and response boundaries

Every submitted message, including starter questions and later turns, goes through
the same guardrail service **before** loading the guide or searching. Emergency,
clinical and personal-benefit requests stop. Sensitive, unsupported or ambiguous
requests receive a fixed clarification. There is no refusal-to-search shortcut.

Allowed responses contain exact passages checked against the verified guide and
linked to physical PDF pages. No language model or composer writes a policy answer.
Earlier messages are not silently reused as context; each follow-up names its topic.
The original baseline guardrail remains frozen, with a conservative additional scope
boundary for this chat. The known baseline clinical limitations are recorded rather
than presented as solved by a passing development suite.

The latest ten turns stay in Streamlit session memory until cleared or the session
ends. Rejected messages are withheld, and raw rule matches are removed from response
metadata. Chat is never logged, exported, persisted to disk or sent to a provider.
Free-form generated policy answers remain disabled pending the held-out safety gate.
See [the chat specification](docs/prototype/student_chat.md).

---

## Four rules that are not negotiable

**1. No real document, ever.** No real invoice, statement, policy number, member number or student. Synthetic documents from `scripts/make_invoices.py` and public sample images only. This is the Privacy Act control and it is also why the build is small enough to finish.

**2. Never commit a secret.** `.env` is gitignored and CI fails the build if it becomes tracked. The API key is held by Bikram; copy `.env.example` to `.env` and paste it there.

**3. `corpus/` is gitignored, `cache/llm/` is committed.** The corpus holds third-party material we may store for research but must not republish. The cache holds every model response, which is what makes the numbers reproducible and the demo network-independent.

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

## Evaluation separation

Three separations, all of which exist so a number can come out badly:

1. **Invoice layout families.** Four families. `specialist_gap` and `hospital_mixed` are frozen held-out. Their parameters live in `data/heldout/`, gitignored, released on evaluation day. Minhaj freezes them before Bikram writes extraction code.
2. **Guardrail probes.** The dev probe set is in `tests/test_guardrail.py` and is visible to Aayush, who builds the gate. The held-out probe set is authored by Bikram, kept out of the repository, and run once at evaluation. Building against the set you are scored on is not a measurement.
3. **Coding frame.** All 55 first-person records are coded independently by Bikram and Minhaj, kappa reported, disagreements resolved by discussion, consensus labels frozen before any classifier is trained.

The same separation applies to every tool used in development: held-out layout parameters and the held-out probe set are never entered into any of them.

---

## The five headline numbers

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
- No statement about what a particular person's policy will pay. That is personal financial product advice under s 766B of the *Corporations Act 2001* (Cth), and the wording is always "the PDS states" or "this document shows", never "you are covered".
- No real invoice handling.
- No model fine-tuning.
- No native app, and no script tag embedded in a third-party page.

See `D5_technical_architecture_plan_v2.md` for the full plan, and `CONTRIBUTING.md` for the development workflow.
