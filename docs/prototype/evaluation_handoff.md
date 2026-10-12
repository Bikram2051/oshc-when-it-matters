# Frozen bill evaluation handoff

Evaluation has not been run.

## Request to Minhaj

Please supply the original frozen files below, without re-saving their contents:

| File | Expected SHA-256 |
| --- | --- |
| specialist_gap.json | 4da51538222dc7ba257e3ac108d1c370949c2010a7bf416c8c92ba1584369349 |
| hospital_mixed.json | 54c22002acf9e0bc33a6b3f6405e4ce94dd5fc49fc1be39f6b944339922979a7 |

Please also supply:

1. The generated synthetic invoice inputs for evaluation, with stable document IDs.
2. Their expected extracted fields, including line items and printed totals. Identify
   which fields are absent, unknown or explicitly zero. Keep truth separate from inputs.
3. A file map linking each document ID to its input, ground truth and layout family,
   plus SHA-256 checksums for the supplied inputs and ground-truth files.
4. A short description of the ground-truth format, or a development-only example
   using the same structure. State the number of documents per family and formats.
5. The original freeze record, generator version/commit and generation settings or
   seed record held by the custodian. Confirm whether anything changed after freezing.
   Report missing records honestly; do not recreate or backdate a freeze record.

Please confirm a delivery time. If the JSON files contain layout parameters,
render the evaluation invoices yourself from that frozen version. The extractor
developer must not inspect those parameters or generator code, and they must not be
entered into any development tool.
No real personal invoices are requested.

## Evaluation sequence

- Verify the original hashes without displaying parameter contents.
- Agree on the ground-truth interface and scoring protocol before the first scored
  run: scored fields, row matching, text normalisation, money tolerance, treatment
  of unknown values, extra/missing rows, abstentions and failed extractions.
- Test the scoring implementation on separate development fixtures.
- Freeze the protocol, scorer and extractor commits before releasing the test inputs.
- Run each agreed pipeline on the same inputs; save every outcome and failure.
  A rerun or correction must be documented and must not replace the first result silently.
- Any later extractor tuning requires a new independent set for a fresh performance claim.

## Current limitation

The two files were not found in the checked data/heldout and Downloads folders.
This does not establish that they are absent elsewhere. Hashes alone do not provide
evaluation inputs, ground truth or proof of when the files were frozen.

If the handoff remains unavailable, present held-out extraction accuracy as pending.
New examples authored during development remain development evidence.
A synthetic-to-public-sample comparison also needs an eligible public sample and
separately established ground truth; it has not been measured in this workflow.
