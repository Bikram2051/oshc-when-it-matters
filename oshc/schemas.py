"""Frozen interfaces for OSHC When It Matters.

FROZEN 2026-09-07. Team D5.

Everything in this file is a contract between members. Changing any field here
breaks someone else's branch, so changes require agreement from all three
members recorded in the meeting minutes, not a pull request comment.

Everything else in the codebase integrates against these types, not against
another member's implementation.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# --------------------------------------------------------------------------
# Coding frame. Definitions are the ones used to code the review corpus and
# must not drift from the Friction Analysis Dashboard in the master workbook.
# --------------------------------------------------------------------------


class Code(str, Enum):
    C1 = "C1"  # Purpose of cover
    C2 = "C2"  # What is covered
    C3 = "C3"  # Accessing healthcare
    C4 = "C4"  # Claiming process
    C5 = "C5"  # Choosing the right service
    C6 = "C6"  # Emergency and urgent help
    S = "S"  # Service complaint only, not a comprehension gap


CODE_LABELS: dict[Code, str] = {
    Code.C1: "Purpose of cover",
    Code.C2: "What is covered",
    Code.C3: "Accessing healthcare",
    Code.C4: "Claiming process",
    Code.C5: "Choosing the right service",
    Code.C6: "Emergency and urgent help",
    Code.S: "Service complaint only",
}


# --------------------------------------------------------------------------
# Safety gates. These run before retrieval and generation, every time.
# --------------------------------------------------------------------------


class GuardrailVerdict(str, Enum):
    ALLOW = "allow"
    REFUSE_ADVICE = "refuse_advice"  # s 766B personal financial product advice
    REFUSE_CLINICAL = "refuse_clinical"  # symptom or diagnosis request
    ESCALATE_EMERGENCY = "escalate_emergency"  # exits to health pathway and 000


class GuardrailDecision(BaseModel):
    """Output of the advice and clinical boundary filter.

    `verdict` is the only field the caller may branch on. `layer` and `trigger`
    exist for evaluation and error analysis, never for control flow.
    """

    model_config = ConfigDict(frozen=True)

    verdict: GuardrailVerdict
    layer: Literal["gazetteer", "llm_rubric", "embedding", "none"]
    trigger: str | None = Field(
        default=None, description="Matched term or rubric reason. For analysis only."
    )
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @property
    def blocked(self) -> bool:
        return self.verdict is not GuardrailVerdict.ALLOW


# --------------------------------------------------------------------------
# Retrieval and grounded composition.
# --------------------------------------------------------------------------


class RetrievalHit(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    text: str
    source_doc: str = Field(description="Filename as snapshotted in corpus/")
    source_url: str
    section: str | None = None
    captured_on: str = Field(description="ISO date the snapshot was taken")
    score: float
    rank: int = Field(ge=1)


class Citation(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_doc: str
    section: str | None
    source_url: str
    captured_on: str


class ComposedAnswer(BaseModel):
    """Answer returned to the user.

    Invariant enforced in the composer, not here: every sentence in `text` is
    either bound to a span in `citations` or is a number produced by
    deterministic arithmetic. If that cannot be satisfied, `abstained` is True
    and `text` carries the refer-to-source wording.
    """

    model_config = ConfigDict(frozen=True)

    text: str
    citations: list[Citation] = Field(default_factory=list)
    abstained: bool = False
    unsupported_dropped: int = Field(
        default=0, description="Sentences removed by the faithfulness check"
    )


# --------------------------------------------------------------------------
# Bill Explainer.
# --------------------------------------------------------------------------


class LineItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    raw_description: str
    item_number: str | None = None
    charged: float | None = None
    benefit_paid: float | None = None
    gap: float | None = None
    mbs_descriptor: str | None = None
    mbs_match_score: float | None = Field(default=None, ge=0.0, le=1.0)
    matched: bool = False
    note: str | None = Field(
        default=None,
        description=(
            "Set to 'not an MBS item, check the PDS' for accommodation, "
            "consumables and anything the matcher abstained on. Never a guess."
        ),
    )


class ExtractionResult(BaseModel):
    """Output of either extractor. Both must return this exact type."""

    model_config = ConfigDict(frozen=True)

    extractor: Literal["rules", "llm"]
    source_kind: Literal["pdf_text", "image", "pasted_text"]
    line_items: list[LineItem] = Field(default_factory=list)
    provider: str | None = None
    service_date: str | None = None
    total_charged: float | None = None
    total_benefit: float | None = None
    total_gap: float | None = None
    warnings: list[str] = Field(default_factory=list)


class BenefitRule(BaseModel):
    """One row of the benefit rules table.

    Every rule carries the PDS page it came from. A category with no rule
    resolves to abstain. No percentage is ever typed from memory.
    """

    model_config = ConfigDict(frozen=True)

    category: str
    description: str
    benefit_basis: Literal["percent_of_mbs", "percent_of_charge", "fixed", "abstain"]
    value: float | None = None
    pds_page: str
    captured_on: str


# --------------------------------------------------------------------------
# Telemetry. No identity, ever. Session id is a random UUID per visit.
# --------------------------------------------------------------------------


class EventName(str, Enum):
    OPEN = "open"
    SCENARIO_START = "scenario_start"
    SCENARIO_COMPLETE = "scenario_complete"
    QUESTION_ASKED = "question_asked"
    REFUSAL_FIRED = "refusal_fired"
    DECODE_RUN = "decode_run"
    DROP_OFF = "drop_off"


class Event(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str = Field(description="Random UUID4 per visit. Not a user id.")
    name: EventName
    at: datetime
    page: Literal["coach", "navigator", "explainer", "dashboard"]
    code: Code | None = Field(
        default=None, description="Category id only. Never the raw question text."
    )
    detail: str | None = Field(
        default=None,
        description="Synthetic demo runs only. Must be None in any real session.",
    )
