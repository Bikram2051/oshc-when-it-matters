"""SEMINAR DEMO COPY of the layer 1 gazetteer. Never merge into oshc/guardrail.py.

This file starts as an exact copy of the detection logic in oshc/guardrail.py.
It is tuned by hand against the frozen dev probes only
(seminar/oshc_seminar_dev_probes.csv). The probes the class writes during the
seminar then test whether that tuning generalises.

It is kept separate because the person tuning this copy also writes the
project's held-out probe set. Nothing tuned here may flow back into the
project guardrail, or that held-out set stops being independent.

Refusal scope follows the Medibank client requirement: no binding statements
about coverage, claims, medical treatment, visa compliance or product
suitability.
"""

from __future__ import annotations

import re

from oshc.schemas import GuardrailDecision, GuardrailVerdict

# Checked first. Any match escalates to the health pathway and 000.
EMERGENCY_TERMS: tuple[str, ...] = (
    "ambulance", "unconscious", "not breathing", "cant breathe", "can't breathe",
    "chest pain", "heart attack", "stroke", "seizure", "overdose", "poisoning",
    "severe bleeding", "bleeding heavily", "suicidal", "kill myself", "self harm",
    "anaphylaxis", "allergic reaction", "broken bone", "head injury", "000",
    "emergency", "urgent care now", "life threatening",
)

# Requests for a decision about this person's cover, claim or product choice.
ADVICE_PATTERNS: tuple[str, ...] = (
    r"\b(am|are)\s+i\s+covered\b",
    r"\bis\s+(my|this)\s+.{0,40}\bcovered\b",
    r"\bwill\s+(i|my\s+policy)\s+(get|be)\s+(paid|reimbursed|covered)\b",
    r"\bhow\s+much\s+(will|do)\s+i\s+get\s+back\b",
    r"\bwhat\s+will\s+i\s+be\s+(paid|reimbursed)\b",
    r"\bshould\s+i\s+(switch|change|buy|choose)\s+.{0,30}\b(policy|cover|plan|fund)\b",
    r"\bwhich\s+(policy|cover|plan|fund)\s+(is\s+)?(best|right)\s+for\s+me\b",
    r"\bmy\s+(policy|membership|claim)\s+.{0,30}\b(cover|pay|reimburse)\b",
)

# Requests to assess symptoms, diagnose or decide treatment.
CLINICAL_PATTERNS: tuple[str, ...] = (
    r"\bi\s+(have|feel|am\s+feeling|got)\s+.{0,40}\b(pain|ache|fever|rash|sick|nausea|dizzy)\b",
    r"\bwhat\s+(is\s+)?wrong\s+with\s+me\b",
    r"\bdo\s+i\s+(have|need)\s+.{0,30}\b(covid|flu|infection|antibiotics|surgery|x-?ray|mri)\b",
    r"\bshould\s+i\s+(see|go\s+to)\s+a\s+doctor\s+(for|about)\s+my\b",
    r"\bis\s+(this|it)\s+serious\b",
    r"\bmy\s+symptoms?\b",
)

_ADVICE_RE = [re.compile(p, re.IGNORECASE) for p in ADVICE_PATTERNS]
_CLINICAL_RE = [re.compile(p, re.IGNORECASE) for p in CLINICAL_PATTERNS]


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def check(text: str) -> GuardrailDecision:
    """Same order as the project gazetteer: emergency, then clinical, then advice."""
    norm = _normalise(text)

    for term in EMERGENCY_TERMS:
        if term in norm:
            return GuardrailDecision(
                verdict=GuardrailVerdict.ESCALATE_EMERGENCY,
                layer="gazetteer",
                trigger=term,
            )

    for pattern in _CLINICAL_RE:
        match = pattern.search(norm)
        if match:
            return GuardrailDecision(
                verdict=GuardrailVerdict.REFUSE_CLINICAL,
                layer="gazetteer",
                trigger=match.group(0),
            )

    for pattern in _ADVICE_RE:
        match = pattern.search(norm)
        if match:
            return GuardrailDecision(
                verdict=GuardrailVerdict.REFUSE_ADVICE,
                layer="gazetteer",
                trigger=match.group(0),
            )

    return GuardrailDecision(verdict=GuardrailVerdict.ALLOW, layer="none")
