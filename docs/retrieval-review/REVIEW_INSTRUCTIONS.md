# Independent Retrieval Gold-Set Review

## Purpose

Independently review all 50 retrieval questions and identify the source
chunk IDs that genuinely contain information needed to answer each query.

## Instructions for the reviewer

Please review the 50 questions in `blind_review_queries.json`.

1. Work from the questions and the frozen source corpus.
2. Inspect source chunk text to decide which chunks are relevant.
3. Do not inspect the existing gold labels, retrieval rankings, or
   diagnostic evaluation results before completing your annotations.
4. Keep all 50 question IDs unchanged.
5. Record the relevant chunk IDs for each question.
6. If a question is ambiguous or no chunk clearly answers it, flag it
   rather than guessing.
7. Return your annotations as a separate JSON file. Do not overwrite
   `data/gold/retrieval.json`.

## Required output

Return a JSON file with 50 entries, each containing:

- `id`: the original question ID
- `query`: the original question text
- `relevant_chunk_ids`: the independently selected chunk IDs

Please also note any ambiguous or duplicated questions.

## Evaluation gate

Do not run `scripts/evaluate_retrieval.py` until the independent labels
have been returned and checked.

The evaluation must then be run exactly once on the independently
reviewed set, and the result must be reported unchanged.

Until then, do not modify `oshc/retrieval.py`, `oshc/chunker.py`, or
the existing gold set as part of this review.
