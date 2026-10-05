"""Layer 2 LLM rubric classifier for the OSHC guardrail.

Layer 1 is the deterministic gazetteer in guardrail.py.
Layer 2 handles wording that may not match a fixed keyword or regex.

The classifier returns one of four existing GuardrailVerdict values:
allow, refuse_advice, refuse_clinical, escalate_emergency.

The LLM is never allowed to invent a new safety category. Invalid or
low-confidence classifications fail open to ALLOW; Layer 1 remains the
stronger deterministic emergency gate.

Held-out guardrail probes are not included in this repository.
"""

from __future__ import annotations

import json
import re

from oshc.llm import complete
from oshc.schemas import GuardrailDecision, GuardrailVerdict


RUBRIC_PROMPT = """You are a safety classifier for an Australian OSHC
education tool.

Classify the user's message into exactly one label:

ALLOW
REFUSE_ADVICE
REFUSE_CLINICAL
ESCALATE_EMERGENCY

Definitions:

ALLOW:
- General educational questions about OSHC, Medicare, MBS, claiming,
  healthcare access, waiting periods, billing, or healthcare terminology.
- Questions asking what a document or general OSHC rule says.
- Do not refuse merely because the question mentions a medical service.

REFUSE_ADVICE:
- The user asks what THEIR policy, membership, cover, or claim will pay.
- The user asks whether they personally are covered or reimbursed.
- The user asks which policy, fund, cover, or plan they should choose.
- Do not give personal financial product advice.

REFUSE_CLINICAL:
- The user asks for diagnosis, symptom assessment, treatment advice,
  or whether their symptoms indicate a medical condition.
- The user asks what condition they might have or what treatment they need.
- The tool must not provide a symptom-to-service recommendation.

ESCALATE_EMERGENCY:
- The message indicates an emergency, immediate danger, crisis, or urgent
  situation requiring emergency/urgent health assistance.
- This includes situations such as unconsciousness, inability to breathe,
  severe bleeding, suspected overdose, suicidal intent, or other immediate
  threats to life or safety.
- Emergency/crisis intent takes priority over the other labels.

IMPORTANT:
- Classify the user's intent, not isolated keywords.
- A question mentioning "emergency", "ambulance", "MRI", "doctor", or
  "hospital" is not automatically unsafe.
- General educational questions remain ALLOW unless they contain a genuine
  personal advice, clinical assessment, or emergency/crisis request.

Return ONLY valid JSON in this exact shape:

{"label":"ALLOW","reason":"short reason","confidence":0.95}

Rules:
- label must be exactly one of ALLOW, REFUSE_ADVICE,
  REFUSE_CLINICAL, ESCALATE_EMERGENCY.
- confidence must be a number between 0 and 1.
- reason must be short.
"""


_MIN_CONFIDENCE = 0.80

_LABEL_TO_VERDICT = {
    "ALLOW": GuardrailVerdict.ALLOW,
    "REFUSE_ADVICE": GuardrailVerdict.REFUSE_ADVICE,
    "REFUSE_CLINICAL": GuardrailVerdict.REFUSE_CLINICAL,
    "ESCALATE_EMERGENCY": GuardrailVerdict.ESCALATE_EMERGENCY,
}


def _extract_json(response: str) -> dict:
    """Extract the classifier JSON from an LLM response."""

    response = response.strip()

    try:
        value = json.loads(response)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", response, re.DOTALL)

        if not match:
            raise ValueError("LLM rubric did not return JSON")

        value = json.loads(match.group(0))

    if not isinstance(value, dict):
        raise ValueError("LLM rubric response is not an object")

    return value


def _classify(text: str) -> tuple[str, str, float]:
    """Call the cached LLM and return label, reason, confidence."""

    prompt = f"""{RUBRIC_PROMPT}

USER MESSAGE:
{text}
"""

    response = complete(
        prompt,
        temperature=0.0,
        max_tokens=150,
    )

    result = _extract_json(response)

    label = str(result.get("label", "")).strip().upper()
    reason = str(result.get("reason", "")).strip()
    confidence = float(result.get("confidence", 0.0))

    return label, reason, confidence


def check(text: str) -> GuardrailDecision:
    """Run the Layer 2 LLM rubric.

    Invalid responses and low-confidence classifications fail open to ALLOW.
    Layer 1 in guardrail.py remains responsible for deterministic emergency,
    clinical, and advice matches.
    """

    try:
        label, reason, confidence = _classify(text)

    except (ValueError, TypeError, json.JSONDecodeError):
        return GuardrailDecision(
            verdict=GuardrailVerdict.ALLOW,
            layer="llm_rubric",
            trigger="invalid_rubric_response",
            confidence=0.0,
        )

    if label not in _LABEL_TO_VERDICT:
        return GuardrailDecision(
            verdict=GuardrailVerdict.ALLOW,
            layer="llm_rubric",
            trigger="invalid_rubric_label",
            confidence=confidence,
        )

    if not 0.0 <= confidence <= 1.0:
        return GuardrailDecision(
            verdict=GuardrailVerdict.ALLOW,
            layer="llm_rubric",
            trigger="invalid_rubric_confidence",
            confidence=0.0,
        )

    if confidence < _MIN_CONFIDENCE:
        return GuardrailDecision(
            verdict=GuardrailVerdict.ALLOW,
            layer="llm_rubric",
            trigger="low_confidence",
            confidence=confidence,
        )

    return GuardrailDecision(
        verdict=_LABEL_TO_VERDICT[label],
        layer="llm_rubric",
        trigger=reason or label.lower(),
        confidence=confidence,
    )
