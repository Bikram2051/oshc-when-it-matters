"""Advice and clinical boundary filter. Layer 1: deterministic gazetteer.

This gate runs BEFORE retrieval and BEFORE generation, every time, on every
page. It is the s 766B control and the clinical control in one place.

Layer 1 (this file) is a blacklist and stays one. Layer 2 is the cached LLM
rubric classifier in llm_rubric.py. The whitelist is the composer, which can
only emit sentences bound to a retrieved span or a computed number.

The held-out probe set is NOT visible to whoever builds this module. See
CONTRIBUTING.md, "Evaluation separation".

Owner: Aayush Khade. Reviewer: Bikram Bhattarai.
"""

from __future__ import annotations

import re

from oshc.schemas import GuardrailDecision, GuardrailVerdict

# Emergency terms exit to the official health pathway and 000 by rule, never
# by model. A false negative here is unacceptable, so this list is generous
# and the false-refusal cost is accepted.
EMERGENCY_TERMS: tuple[str, ...] = (
    "ambulance", "unconscious", "not breathing", "cant breathe", "can't breathe",
    "chest pain", "heart attack", "stroke", "seizure", "overdose", "poisoning",
    "severe bleeding", "bleeding heavily", "suicidal", "kill myself", "self harm",
    "anaphylaxis", "allergic reaction", "broken bone", "head injury", "000",
    "emergency", "urgent care now", "life threatening",
)

# Requests for a determination about THIS person's cover or reimbursement.
# These are personal financial product advice under s 766B.
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

# Requests for assessment of symptoms. Navigator never maps symptoms to a
# service; there is no such code path in this repository.
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
    """Layer 1 gazetteer check. Order matters: emergency wins over everything."""
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


REFUSAL_TEXT: dict[GuardrailVerdict, str] = {
    GuardrailVerdict.ESCALATE_EMERGENCY: (
        "If this is an emergency, call 000 now. For urgent health advice, "
        "call healthdirect on 1800 022 222, any time."
    ),
    GuardrailVerdict.REFUSE_CLINICAL: (
        "This tool explains how OSHC and Australian healthcare work. It does "
        "not assess symptoms. For health advice, call healthdirect on "
        "1800 022 222 or see a GP."
    ),
    GuardrailVerdict.REFUSE_ADVICE: (
        "This tool explains general OSHC rules and what a document shows. It "
        "cannot tell you what your own policy will pay. Medibank confirms "
        "your exact benefit."
    ),
}
