"""Fixed official care handoffs; never assess symptoms or select a service for them.

Links carry no question, location, identity or session data. The conservative
personal-symptom detector only stops live generation; it never determines urgency.
"""
from __future__ import annotations

import re

HEALTHDIRECT_NUMBER = "1800 022 222"
SERVICE_FINDER_URL = "https://www.healthdirect.gov.au/australian-health-services"
SYMPTOM_CHECKER_URL = "https://www.healthdirect.gov.au/symptom-checker"
HEALTHDIRECT_URL = "https://www.healthdirect.gov.au/"

CLINICAL_HANDOFF = (
    "I can't assess symptoms or decide how urgently you need care. "
    "For advice on what to do next, call healthdirect on 1800 022 222, available 24/7. "
    "You can also use healthdirect's official Symptom Checker or find health services below. "
    "In an emergency, call 000."
)

_PERSONAL = re.compile(
    r"\b(?:i\s+(?:have|had|got|am\s+having|am\s+feeling|feel|am\s+sick|am\s+unwell)|"
    r"i['’]m\s+(?:having|feeling|sick|unwell)|i['’]ve\s+(?:got|had)|"
    r"my\s+(?:child|friend|partner|roommate)\s+(?:has|is\s+having|feels))\b",
    re.I,
)
_SYMPTOM = re.compile(
    r"\b(?:cough(?:ing)?|headache|migraine|fever|rash|nausea|dizz\w*|pain|"
    r"bleed\w*|vomit\w*|diarrh\w*|sore\s+throat|unwell|sick)\b",
    re.I,
)


def personal_symptom_request(text: str) -> bool:
    """Recognise an explicit disclosure; no diagnosis, severity score or care mapping."""
    return bool(_PERSONAL.search(text) and _SYMPTOM.search(text))
