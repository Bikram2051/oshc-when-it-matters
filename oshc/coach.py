"""coach. Skeleton only. See D5_technical_architecture_plan_v2.md section 5 and 6.

Fill the bodies against the frozen types in oshc/schemas.py. Do not change the
signatures without agreement recorded in the minutes.
"""
from __future__ import annotations


def keyness_ranked_terms(top_k: int = 30) -> list[tuple[str, float]]:
    """Rank OSHC jargon in the 87-record corpus against wordfreq general frequencies.

    This ranked list decides which glossary cards exist and in what order. It is
    corpus-driven term selection, not a learning system, and is labelled that way.

    Owner: Minhaj Rahman. Reviewer: Bikram Bhattarai.
    """
    raise NotImplementedError("Week 8 gate.")
