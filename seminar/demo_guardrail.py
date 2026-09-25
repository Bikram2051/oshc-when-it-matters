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
        # Personal cover, claim, product-choice and visa decisions.
    r"\b(?:tell me|confirm|calculate|guarantee)\b.{0,80}"
    r"\b(?:i|my)\b.{0,30}\b(?:guaranteed|definitely|will)\b"
    r".{0,40}\b(?:get back|be reimbursed|be paid)\b",

    r"\bwill\s+(?:medibank|my insurer|my policy)\b.{0,35}"
    r"\b(?:definitely|fully|completely)\b.{0,30}"
    r"\b(?:cover|pay|reimburse)\b",

    r"\b(?:pick|choose|recommend|select|tell me)\b.{0,100}"
    r"\b(?:policy|insurer|cover|plan|fund)\b.{0,100}"
    r"\b(?:for me|for my|my needs|my personal circumstances)\b",

    r"^(?=.*\bpre[- ]existing\b)(?=.*\b(?:my|i)\b)"
    r".*\b(?:decide|determine|confirm)\b.{0,80}\b(?:whether|if)\b",

    r"\b(?:tell me|confirm|decide|determine)\b.{0,80}\bwaiting period\b"
    r".{0,80}\b(?:apply|applies|waived|exempt)\b.{0,30}\b(?:me|my)\b",

    r"^(?=.*\bvisa\b)(?=.*\b(?:oshc|insurance|cover)\b)"
    r".*\bcan\s+i\b.{0,40}\b(?:cancel|stop|end)\b.{0,100}"
    r"\b(?:meet|comply|satisfy|breach)\b",

    r"\b(?:confirm|guarantee|decide|tell me)\b.{0,140}"
    r"\b(?:meet|comply|satisfy|breach|violate)\b.{0,40}"
    r"\b(?:my visa|visa conditions|visa requirements)\b",

    r"\b(?:act as|pretend to be|impersonate)\b.{0,80}"
    r"\b(?:approve|authorise|authorize|accept)\b.{0,60}\bclaim\b",

    r"\b(?:reply|respond|say|write)\s+(?:only|exactly)\b"
    r".{0,100}\b(?:my|your)\b.{0,60}"
    r"\b(?:fully covered|guaranteed|approved)\b",
)

# Requests to assess symptoms, diagnose or decide treatment.
CLINICAL_PATTERNS: tuple[str, ...] = (
    r"\bi\s+(have|feel|am\s+feeling|got)\s+.{0,40}\b(pain|ache|fever|rash|sick|nausea|dizzy)\b",
    r"\bwhat\s+(is\s+)?wrong\s+with\s+me\b",
    r"\bdo\s+i\s+(have|need)\s+.{0,30}\b(covid|flu|infection|antibiotics|surgery|x-?ray|mri)\b",
    r"\bshould\s+i\s+(see|go\s+to)\s+a\s+doctor\s+(for|about)\s+my\b",
    r"\bis\s+(this|it)\s+serious\b",
    r"\bmy\s+symptoms?\b",
        # Requests for personal medical decisions.
    r"^(?=.*\b(?:procedure|surgery|operation|treatment)\b)"
    r".*\b(?:should i|whether i should)\s+(?:have|undergo|proceed)\b",

    r"\b(?:which|whether)\b.{0,80}\b(?:gp|doctor|physiotherapist|specialist)\b"
    r".{0,80}\b(?:right|best)\b.{0,20}\bfor me\b",

    r"\b(?:can|could|would)\s+you\s+(?:calculate|work out|choose|recommend)\b"
    r".{0,60}\b(?:dose|dosage)\b",

    r"\b(?:which|what)\s+(?:antibiotics?|medicine|medication)\b"
    r".{0,30}\bshould\s+i\s+(?:take|use)\b",

    r"\b(?:decide|determine|tell me)\b.{0,80}"
    r"\b(?:whether|if)\s+i\s+have\s+(?:an?\s+)?"
    r"(?:disease|condition|infection)\b",

    r"\bdiagnose\s+(?:me|my|this|what)\b",

    r"^(?=.*\b(?:medicine|medication|prescription|tablets?|pills?|dose)\b)"
    r".*\bshould\s+i\s+(?:stop|start|change|increase|decrease|reduce|double)\b",
)
# Additional emergency descriptions for the seminar demo.
EMERGENCY_PATTERNS: dict[str, str] = {
    "choking_with_speech_or_breathing_difficulty": (
        r"\bchoking\b.{0,80}\b(?:cannot|can['’]?t|unable to)\s+"
        r"(?:talk|speak|breathe)\b"
    ),
    "collapse_and_not_waking": (
        r"\bcollapsed\b.{0,80}\b(?:won['’]?t|will not|cannot|can['’]?t)"
        r"\s+wake\s+up\b"
    ),
    "bleeding_not_stopping": (
        r"\b(?:blood|bleeding)\b.{0,40}\b"
        r"(?:will not|won['’]?t|does not|doesn['’]?t|cannot|can['’]?t)"
        r"\s+stop\b"
    ),
        "face_arm_and_speech_changes": (
        r"^(?=.*\bface\b.{0,35}\b(?:uneven|droop\w*)\b)"
        r"(?=.*\barm\b.{0,25}\b(?:weak|numb)\b)"
        r"(?=.*\bspeech\b.{0,25}\b(?:slurr\w*|unclear)\b)"
    ),
    "airway_swelling_with_breathing_difficulty": (
        r"^(?=.*\b(?:tongue|throat|lips?)\b.{0,40}\b(?:swelling|swollen)\b)"
        r"(?=.*\b(?:hard to breathe|difficulty breathing|"
        r"struggling to breathe|cannot breathe|can['’]?t breathe)\b)"
    ),
    "excess_medication_with_drowsiness": (
        r"^(?=.*\b(?:took|taken|swallowed)\b.{0,20}"
        r"\b(?:too many|too much|extra)\b.{0,20}"
        r"\b(?:tablets?|pills?|medicine|medication)\b)"
        r"(?=.*\b(?:struggling to stay awake|cannot stay awake|"
        r"can['’]?t stay awake|very drowsy|very sleepy)\b)"
    ),
    "cannot_stay_safe": (
        r"\b(?:cannot|can['’]?t|unable to)\s+"
        r"(?:keep myself|stay)\s+safe\b"
    ),
}
_ADVICE_RE = [re.compile(p, re.IGNORECASE) for p in ADVICE_PATTERNS]
_CLINICAL_RE = [re.compile(p, re.IGNORECASE) for p in CLINICAL_PATTERNS]


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()

def _non_current_emergency_context(norm: str) -> bool:
    """Recognise narrow billing or preparation contexts."""
    active_request = re.search(
        r"\b(?:i|we|someone|my friend|my flatmate|my roommate)\s+"
        r"(?:need|needs)\s+(?:urgent|emergency)\s+help\b"
        r"|\b(?:this|it)\s+is\s+(?:a|an)\s+(?:medical\s+)?emergency\b",
        norm,
    )
    if active_request:
        return False

    past_care = (
        re.search(r"\b(?:discharged|already (?:been )?treated)\b", norm)
        and re.search(r"\b(?:invoice|receipt|billing|claim)\b", norm)
        and re.search(r"\bno\s+(?:current\s+)?symptoms\s+now\b", norm)
    )
    preparation = (
        re.search(r"\b(?:number|contact)\b.{0,40}\b(?:save|keep|store)\b", norm)
        and re.search(
            r"\b(?:nobody|no one)\s+needs?\s+help\s+(?:right\s+)?now\b",
            norm,
        )
    )
    return bool(past_care or preparation)

def check(text: str) -> GuardrailDecision:
    """Same order as the project gazetteer: emergency, then clinical, then advice."""
    norm = _normalise(text)

    for reason, pattern in EMERGENCY_PATTERNS.items():
        if re.search(pattern, norm):
            return GuardrailDecision(
                verdict=GuardrailVerdict.ESCALATE_EMERGENCY,
                layer="gazetteer",
                trigger=reason,
            )
    for term in EMERGENCY_TERMS:
        if term == "emergency" and _non_current_emergency_context(norm):
            continue
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
