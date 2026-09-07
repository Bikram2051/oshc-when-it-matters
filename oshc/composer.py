"""composer. Skeleton only. See D5_technical_architecture_plan_v2.md section 5 and 6.

Fill the bodies against the frozen types in oshc/schemas.py. Do not change the
signatures without agreement recorded in the minutes.
"""
from __future__ import annotations

from oshc.schemas import ComposedAnswer, RetrievalHit


def compose(question: str, hits: list[RetrievalHit]) -> ComposedAnswer:
    """The whitelist half of the s 766B boundary.

    A sentence may only appear in the output if it is bound to a span in `hits`
    or is a number produced by oshc.arithmetic. Everything else is dropped. If
    the answer loses its core, abstain and link the source.

    Owner: Aayush Khade. Reviewer: Bikram Bhattarai.
    """
    raise NotImplementedError("Week 8 gate. Faithfulness measured on a 50-sentence sample.")
