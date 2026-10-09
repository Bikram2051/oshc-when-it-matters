# Held-out bill extraction: evaluation protocol

Fixed before any held-out input is released. A change after the first scored run
needs a new independent set before any new performance claim.

## Roles

- Custodian (Minhaj): renders the evaluation invoices from the frozen family
  parameters with the frozen generator, writes the expected outputs, and keeps the
  parameters and the generator away from the extractor side.
- Evaluator (Bikram): runs the frozen extractors once and scores the saved outputs.
- Reviewer (Aayush): checks this protocol and the scorer before they are frozen.

## What is frozen

- Extraction code: commit 40e04f8 (PR #11). `oshc/billexplainer`, `oshc/llm.py`,
  `oshc/llm_budget.py` and `oshc/schemas.py` have not changed since 1 October 2026.
  `scripts/run_heldout_extraction.py` refuses any other version, and a test fails
  if these files change before the run is recorded.
- Scorer and this protocol: the commit that adds them, tagged `eval-extraction-v1`
  before the inputs are released.

## Order of work

1. The custodian checks the expected outputs and the file map with the tagged scorer,
   on the custodian's own computer:
   `python -m eval.extraction --check --map MAP.csv --gold GOLD --inputs INPUTS`
   then sends the inputs and the file map, and posts the file map's SHA-256 in the
   group chat. The map holds the SHA-256 of every expected output; the expected
   outputs stay with the custodian.
2. The evaluator runs both pipelines once:
   `python scripts/run_heldout_extraction.py --map MAP.csv --inputs INPUTS --out RUN`
   The llm pipeline makes paid calls, so the run sets `OSHC_OFFLINE=0` and
   `OSHC_ENABLE_LIVE=1` for that run only. Before writing anything, the runner checks
   the input hashes, the frozen code, the API key setting and that the spending
   allowance covers the largest possible cost of every llm call. Every output,
   including failures, is saved once and never overwritten. The llm responses are
   cached in `RUN/llm_cache`, not in the committed `cache/llm` folder, and their
   hashes are recorded too.
3. The evaluator posts the SHA-256 of `RUN/run_record.json` in the group chat.
4. The custodian then sends the expected outputs. The scorer checks each one against
   the file map.
5. The evaluator scores once:
   `python -m eval.extraction --map MAP.csv --gold GOLD --outputs RUN --report REPORT.json`
6. A rerun or correction is recorded with its reason and never replaces the first result.

## Inputs and file map

- One file per document: a PDF with selectable text, or UTF-8 text. No scans or images.
- File map: CSV with the columns
  `document_id, family, input_file, input_sha256, gold_file, gold_sha256`.
  Document IDs use letters, digits, `-` and `_` only. File names are plain names
  (letters, digits, `.`, `-` and `_`), and inputs end in `.pdf` or `.txt`.
- Inputs, the file map, run folders and expected outputs stay outside the repository,
  or under `data/heldout/`, which git ignores and CI blocks. The runner and the scorer
  refuse any other folder inside the repository. Only the aggregate report, which
  holds counts and rates but no document values, may be committed.

## Expected-output format

One JSON file per document, using the fields of the frozen `ExtractionResult`:

```json
{
  "document_id": "DEV-001",
  "family": "dev_example",
  "provider": "Demonstration Clinic",
  "service_date": "2026-09-01",
  "total_charged": "105.00",
  "total_benefit": null,
  "total_gap": null,
  "line_items": [
    {"raw_description": "Short consultation", "item_number": "23", "charged": "90.00",
     "benefit_paid": null, "gap": null},
    {"raw_description": "Administration fee", "item_number": null, "charged": "15.00",
     "benefit_paid": null, "gap": null}
  ]
}
```

(This is the synthetic development example in `data/demo_dev`, not a held-out document.)

- Write each expected output from the generator's own record of what it printed, or by
  reading the invoice. Never run or consult the project's extractors to produce it.
- Record what is printed. Not printed: `null`. Printed as zero: `"0.00"`.
- Never derive a value that is not printed, such as a gap calculated from a charge
  and a benefit.
- Money as a string with two decimals and no currency sign. Dates as `YYYY-MM-DD`.
- One entry per printed line, in printed order, with the description as printed.
- A field printed more than once with different values: `null`, with the reason in
  `"notes"`.
- Other keys, such as `"notes"`, are allowed and ignored.

## Scoring

- The rules and llm pipelines are scored separately.
- Scored fields: per document `provider`, `service_date`, `total_charged`,
  `total_benefit`, `total_gap`; per line `item_number`, `charged`, `benefit_paid`, `gap`.
- `raw_description` helps match rows and is reported separately, not in the headline.
- Comparison: money equal to the cent; item numbers equal after removing spaces;
  text equal after case-folding and collapsing spaces; dates equal as calendar dates
  (outputs may use `YYYY-MM-DD`, `DD/MM/YYYY` or `DD-MM-YYYY`).
- Row matching: one-to-one, maximising the number of agreeing fields; pairs with no
  agreeing field stay unmatched.
- Counting: a correct value is a true positive; a wrong value is a false positive and
  a false negative; a value where nothing is printed is a false positive and an
  invented value; a missing value is a false negative; `null` where nothing is printed
  is a correct abstention, reported but not part of F1. Unmatched expected rows count
  a false negative for each printed value; unmatched output rows count a false
  positive for each value.
- A failure (an error, or an empty result) counts a false negative for every printed
  value and is reported separately. The run record also counts llm documents that
  returned no values because the call did not complete, by error type.

## Reporting

For each pipeline: micro-averaged F1 with a 95% bootstrap interval over documents
(2,000 resamples, seed 2026), per-family F1 with intervals, per-field precision,
recall and F1, invented values, row counts, description accuracy, failures, and the
document exact-match rate with a Wilson 95% interval. Report the number of documents
per family. A synthetic-to-real comparison is not measured: no public sample with
independently established expected outputs is available.

## Exposure record

On 9 October 2026 the custodian pushed both parameter files to a public branch
(PR #16, closed without merging), and the specialist_gap parameters were sent to the
evaluator and opened in a development tool session. Both events came after the
extraction code was fixed on 1 October. This protocol was written after that
exposure; it contains no family-specific rule and is defined only over the frozen
`ExtractionResult` fields.
