# Ask a question: historical 13 October checkpoint

Superseded on 14 October by [guarded guide chat](student_chat.md). The text below
records the earlier single-question prototype and its historical retrieval report;
it does not describe the current conversation interface. The current transcript
and response-boundary checks live in `tests/test_ask_ui.py` and
`scripts/prototype_check_student_chat.py`. The older check command forwards to the
new development check, and cannot silently replace the historical retrieval scores.

This checkpoint adds a free-text question field to the prototype. It is not a
conversational Navigator, not a chatbot, and not a claim decision.

`docs/prototype/navigator_ui.md` recorded that the Navigator deliberately had
"no free-text question field", and `tests/test_navigator_ui.py` asserts that
still. That remains true of the Navigator. The question field is a separate page
with a separate contract, set out below.

## What it does

- Every question goes through `oshc.guardrail.check` before anything is read.
  Retrieval runs only on an `ALLOW` verdict. There is no path to the corpus that
  skips the gate, and no cached verdict.
- An allowed question is answered by showing up to five column excerpts from the
  verified May 2026 guide, each beside its original physical PDF page, with the
  publisher link anchored to that page.
- Results are labelled as passages that match the question's wording. They are
  never labelled as the answer, because the right page is ranked first only about
  half the time.
- No sentence is generated. `oshc.composer` is not imported by this page and the
  check script asserts it is never called.
- The question text is not written to disk, to a log, or to any provider. The two
  session counters hold integers only; `tests/test_ask_ui.py` asserts that.

## Why there is no written answer

The architecture plan sets a ship condition for the conversational surface:
refusal recall on the held-out probe set at or above
`oshc.config.REFUSAL_RECALL_FLOOR`. That run has not happened. Composing prose is
the step that can state something the source does not, so composition stays
behind the gate.

Retrieval-only output is what lets the question field ship before that run. If
retrieval misses, the reader sees an unhelpful passage. If composition had missed
in the same way, the reader would see a confident wrong statement about their
cover. The failure mode is bounded by construction rather than by measurement,
which is the only reason this is defensible today.

## What it measures

`python scripts/prototype_check_ask_ui.py` drives the real page against the real
guide, then scores retrieval on two probe sets and writes
`docs/prototype/ask_ui_check.json`.

- **Gold, guide wording.** The 25 questions in `data/gold/retrieval.json` whose
  answer is in the Member Guide. The other 25 are MBS item lookups and belong to
  the Bill Explainer, so they are excluded here.
- **Dev, student wording.** `data/probes/ask_dev_probes.csv`. The same subject
  matter asked the way a student asks it, labelled by page in-house.

Scoring is page level: a question counts as answered if any expected physical page
appears in the top five. The page is what the reader is shown and sent to, so the
page is the right grain.

Two results are worth carrying into the report.

1. **Recall@5 falls by about 17 points when the phrasing changes**, from 96% on the
   guide's own wording to 79% on students' wording, on the same corpus and the same
   retriever. Word-overlap search rewards readers who already know the document's
   vocabulary, which is the opposite of the population this prototype is for.
   Named failures: *what is a gap payment* lands on the premium pages because the
   guide uses "gap" for two unrelated things; vague questions land in the glossary;
   a question sharing no words with its answer returns nothing useful.

2. **The emergency word list refuses 2 of 40 probe questions that the guide does
   answer.** One is *when is ambulance treatment covered*, which is one of
   Navigator's six prepared topics. The same question is served by clicking a topic
   and refused by typing it. That is the measured price of keeping the list wide,
   and the list stays wide: a missed emergency is worse than a refused question.

After an emergency escalation the page offers the matching guide passage inside a
collapsed panel labelled as general information, not as help. The escalation itself
is unconditional and first. `oshc.guardrail` is unchanged by this checkpoint, so
the pending held-out refusal-recall run still measures the gate as it stands.

## Limits

Both probe sets were written and labelled in-house. Neither is held out, the dev
set was labelled by the member who built this page, and the gold set was authored
by the member who built the retriever. 79% is the optimistic end of the range.
Neither set measures whether a student understood the passage they were shown.

These are engineering checks and in-house measurements. They do not establish
held-out Recall@5, refusal recall, clinical safety, or accurate personal coverage
advice. Do not treat this checkpoint as satisfying the project's conversational
safety gate.

## Running it

```
$env:OSHC_OFFLINE = "1"
$env:OSHC_ENABLE_LIVE = "0"
python -m streamlit run app/Home.py      # then open Ask a question
python scripts/prototype_check_ask_ui.py # writes the report
```

To preserve a previous report, pass a new `--out` path. `tests/test_ask_ui.py`
uses a synthetic guide and makes no provider calls.
