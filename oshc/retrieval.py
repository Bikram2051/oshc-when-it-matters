"""retrieval. Skeleton only. See D5_technical_architecture_plan_v2.md section 5 and 6.

Fill the bodies against the frozen types in oshc/schemas.py. Do not change the
signatures without agreement recorded in the minutes.
"""
from __future__ import annotations

from oshc.schemas import RetrievalHit


def search(query: str, *, k: int = 5) -> list[RetrievalHit]:
    """Hybrid BM25 plus dense cosine, reciprocal rank fusion. No reranker.

    Owner: Aayush Khade. Reviewer: Bikram Bhattarai.
    """
    raise NotImplementedError("Week 7 gate. Recall@5 measured on data/gold/retrieval.json.")
