# Frozen source-only retrieval scoring

The 50 query texts were already available to the project. Relevance labels were
derived by one separate automated assessor from the frozen guide and raw MBS XML
without access to implementation, existing gold, rankings or previous scores.
This is independence of annotation, not unseen queries, human consensus or a
blinded inter-rater study. Labels are frozen at SHA-256
`a97a5105fd99a3d7f0a1c9c21e0e5a254fbfe0d8f03f5f9129b1e024349f24b1`.

This protocol is recorded before its first scoring run. Do not change the labels
or deployed implementation based on results. Keep first outputs and reports.

1. Verify the label hash and assessor freeze. Build the existing verified guide
   corpus and use its deployed `PolicySearch` BM25 unchanged, at `k=5`.
2. Map guide chunks to `guide:pNNN:left/right` using physical page and column
   metadata only. Save the complete one-to-one map and implementation hashes.
3. Run every original query and save ranked chunk IDs, locators and errors outside
   the repository before consulting any relevance field. Record no question text,
   source passage, annotation rationale or learner information in predictions.
4. The primary metric is any relevant **exact physical page and column** in the
   first five hits for all 25 guide queries. Report hit@1, hit@5 and MRR@5. An
   absent hit contributes zero reciprocal rank. Page-only relaxation is secondary.
5. All 25 MBS queries are outside the deployed guide-only pipeline. Report their
   count explicitly and retain them as misses in an additional all-50 denominator.
   Never present guide-only performance as whole-corpus performance.
6. Keep ambiguous annotations, duplicates, errors and source locators omitted by
   the deployed index in their original denominators. Report ambiguity and
   duplicate counts. Report Wilson 95% intervals for hit proportions, with the
   limitation that this selected set and repeated questions are not a population
   sample. MRR is a descriptive point estimate for this set.
7. Save aggregate metrics plus safe query IDs/ranks and hashes to the repository.
   Save full frozen labels and first rankings separately. Use exclusive creation;
   a subsequent run must use a new output path and preserve the first result.

The separate research hybrid uses `BAAI/bge-small-en-v1.5`, which is not provisioned
locally. No model download, model inference or provider call is part of this run.
Do not substitute the deployed guide browser for the research hybrid score. The
full-corpus BM25 baseline is also unmeasured here: MBS item locators have not been
bound uniquely to the research chunker's flattened XML chunks. These blockers are
recorded explicitly rather than assigning an invented metric.

Run from the project root with the existing local Python environment:

```powershell
python scripts/evaluate_independent_retrieval.py --labels <external-labels.json> --freeze <external-freeze_manifest.json> --run-dir <new-external-first-run-directory> --report docs/prototype/independent_retrieval_2026-10-15.json
```
