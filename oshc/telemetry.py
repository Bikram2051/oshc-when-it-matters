"""telemetry. Skeleton only. See D5_technical_architecture_plan_v2.md section 5 and 6.

Fill the bodies against the frozen types in oshc/schemas.py. Do not change the
signatures without agreement recorded in the minutes.
"""
from __future__ import annotations

from oshc.schemas import Event


def record(event: Event) -> None:
    """Append one event to SQLite. Never writes raw question text in a real session.

    Owner: Minhaj Rahman. Reviewer: Aayush Khade.
    """
    raise NotImplementedError("Week 6 gate: schema. Week 9 gate: wiring.")
