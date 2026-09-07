"""classifier. Skeleton only. See D5_technical_architecture_plan_v2.md section 5 and 6.

Fill the bodies against the frozen types in oshc/schemas.py. Do not change the
signatures without agreement recorded in the minutes.
"""
from __future__ import annotations

from oshc.schemas import Code

LADDER = ("majority", "tfidf_logreg", "embed_knn", "llm_zeroshot")


def predict(text: str, *, step: str = "tfidf_logreg") -> Code:
    """Route a question to one of C1..C6 or S. Analytics and routing only.

    Never used for a safety decision. The guardrail runs first and independently.
    Owner: Bikram Bhattarai. Reviewer: Minhaj Rahman.
    """
    raise NotImplementedError("Week 7 gate. Steps 1 to 3 are local and must run without an API key.")
