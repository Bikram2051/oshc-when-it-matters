"""Produce the five headline numbers. One command, reproducible from cache.

    python -m eval.run_all

Numbers, fixed in the architecture plan so that "done" has a definition:
  1. kappa            Cohen's kappa on the coding frame, 55 first-person records
  2. macro_f1         classifier ladder, stratified 5-fold, plus the shift gap
  3. recall_at_5      retrieval on the frozen gold set
  4. refusal_recall   guardrail on the held-out probe set, plus false-refusal rate
  5. extraction_f1    held-out synthetic families, and the synthetic-to-real drop

Rules enforced here, not by promise:
  - few-shot exemplars are excluded from every test fold
  - the 38 gap records never appear in retrieval, refusal or extraction scoring
  - held-out material is loaded from data/heldout/ which is gitignored until
    evaluation day
"""
from __future__ import annotations


def main() -> None:
    raise NotImplementedError(
        "Week 10 gate: all five numbers produced. Build incrementally from Week 7."
    )


if __name__ == "__main__":
    main()
