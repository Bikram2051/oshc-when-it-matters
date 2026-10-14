"""One guarded, offline guide question in; fixed wording and bound excerpts out.

Never compose an answer, infer personal cover, assess health, or reuse chat context.
The baseline guardrail runs before source access on every call. A conservative
channel scope check closes uncertain cases without changing that measured contract.
See docs/prototype/student_chat.md for the specification and deliberate limitations.
"""
from __future__ import annotations

import math
import os
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from oshc.guardrail import REFUSAL_TEXT, check
from oshc.policy_search import PolicySearch
from oshc.policy_source import (
    CAPTURED_ON,
    ROOT,
    SOURCE_DOC,
    SOURCE_SHA256,
    SOURCE_URL,
    PolicyCorpus,
    SourceError,
    build_corpus,
)
from oshc.schemas import GuardrailDecision, RetrievalHit

MAX_QUESTION_CHARS = 500
RESULT_COUNT = 5
ChatStatus = Literal[
    "answered", "blocked", "clarify", "out_of_scope", "privacy", "invalid",
    "offline_required", "source_unavailable", "no_match",
]


@dataclass(frozen=True)
class ChatResponse:
    """A submission result. Hits contain only unchanged, checked source columns."""

    status: ChatStatus
    decision: GuardrailDecision
    message: str
    hits: tuple[RetrievalHit, ...] = ()
    source_sha256: str | None = None
    safe_to_echo: bool = False


# This is an intentionally narrow channel vocabulary, not an expanded clinical
# gazetteer. Unknown language abstains rather than interpreting a medical narrative.
_WORDS = frozenset("""
a about access accessing add after all an and another any apply applies are as at
australia australian back be before benefits benefit between bill billed billing bills
bulk by can cancellation cancel card cards change changing charges charge charged
claim claimed claiming claims clinic clinics conditions contact cost costs cover
coverage covered covers dependant dependants dependent dependents difference direct
do does doctor doctors document documents eligibility eligible except exclude excluded
exclusion exclusions explain family find for form forms from fund general get getting
give gp guide has have healthcare health help hospital hospitals how husband i if in
include included includes information insurance international is it item items join
joining levy limit limits make making manage managing mean means medicare medical
medicine medicines medibank member members membership mbs money much must my need new
not number numbers of on online or oshc other out over overseas paid partner pay
paying payment payments period periods pharmacy pharmacies policy policies prescription
prescriptions premium premiums process provider providers receipt receipts reimbursement
renew renewing rules schedule service services should single spouse student students
seeing submit submitting tax term terms than that the their them there these this to treatment
under understand use using waiting wait website what when where which who why wife will
with without work works year years your you refund refunds renewal reimburse reimbursed
have to before husband wife couple both not at all also for example when does
""".split())  # noqa: SIM905 -- grouped words keep the scope vocabulary reviewable.

_TOPIC = re.compile(
    r"\b(?:oshc|medibank|insurance|policy|policies|cover|coverage|covered|claim|claims|"
    r"claiming|billing|bill|bills|gap|waiting|membership|member|medicare|mbs|"
    r"prescription|prescriptions|medicine|medicines|pharmacy|pharmacies|premium|premiums|"
    r"reimbursement|benefit|benefits|exclusion|exclusions|healthcare)\b"
)
# Gap is safe educational vocabulary; keep it explicit in both the topic and word gate.
_WORDS = _WORDS | {"gap"}

_INJECTION = re.compile(
    r"\b(?:ignore|disregard|bypass|override|disable|jailbreak|pretend)\b|"
    r"\b(?:system|developer)\s+(?:prompt|message|instructions?)\b|"
    r"\bact\s+as\b|[<>]|```"
)
_IDENTIFYING = re.compile(
    r"[\w.+-]+@[\w.-]+\.[a-z]{2,}|"
    r"\b(?:\d[\s().+-]*){7,}\b|"
    r"\b(?:dob|date\s+of\s+birth|passport|address)\s*(?:is\b|[:=])|"
    r"\b(?:membership|member|policy|student|claim)\s+(?:number|id)\s*(?:is\b|[:=])|"
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"
)
_PERSONAL_STATE = re.compile(
    r"\bi\s+(?:have|had|got|feel|felt|am|think|developed|need)\b|"
    r"\bmy\s+(?:child|friend|partner|husband|wife)\s+(?:has|had|is|feels|needs)\b|"
    r"\b(?:for\s+me|diagnos\w*|symptom\w*|recommend\w*)\b"
)
_FIRST_PERSON = re.compile(r"\b(?:i|my|me|we|our)\b")
_THIRD_PERSON = re.compile(r"\b(?:they|them|their|he|him|his|she|her|hers)\b")
_GENERAL_QUESTION = re.compile(r"^(?:what|when|how|why|where|which|explain)\b")
_PUBLIC_NAMES = frozenset({
    "Australia", "Australian", "Medibank", "Medicare", "Benefits", "Schedule", "Member", "Guide",
})
_CARE_DECISION = re.compile(r"\b(?:should|need|needs|must)\b|"
                            r"\bhow\s+(?:much|many)\s+(?:medicine|medicines|treatment)\b")
# Personal pronouns are allowed only in a few administrative formulations. Each
# word must still pass the educational vocabulary gate; tails are not unrestricted.
_ADMIN_QUESTION = re.compile(
    r"^(?:how\s+(?:do|can)\s+i\s+(?:"
    r"claim(?:\s+money\s+back)?(?:\s+(?:after|for)(?:\s+seeing)?\s+(?:a\s+)?"
    r"(?:doctor|gp|bill|receipt|hospital|medicine|medicines|prescriptions))?|"
    r"(?:make|submit)\s+a\s+claim|"
    r"get\s+(?:my\s+)?membership\s+card|"
    r"(?:find|contact)\s+(?:a\s+)?(?:gp|doctor|medibank))"
    r"(?:\s+(?:under|with)\s+(?:oshc|medibank))?|"
    r"can\s+my\s+(?:husband|wife|partner|spouse)\s+be\s+on\s+my\s+policy)\s*[?!.]*$"
)

_MESSAGES: dict[str, str] = {
    "invalid": "Write one complete question of up to 500 characters. Do not include personal details.",
    "offline_required": "Student questions are available only in the offline demonstration mode.",
    "privacy": "Please remove names, contact details, identification numbers and dates of birth, then ask a general question.",
    "clarify": "Please write a complete, general question about OSHC or the healthcare process and name the topic. Each message is checked separately; earlier messages are not used as context.",
    "out_of_scope": "I can find general information in the saved OSHC guide. Please use a complete general question about topics such as claiming, waiting periods, membership cards or billing. I cannot assess health, decide personal benefits or follow requests to change the safety rules.",
    "source_unavailable": "The saved guide or its search results could not be verified. No excerpts are shown. Restore the frozen source before trying again.",
    "no_match": "No matching passage was found in the saved guide. Try a named guide topic or read the original document in Navigator.",
    "answered": "These are matching passages from the saved guide, not a written answer or a personal coverage decision. Word overlap is not confidence; check the original page and surrounding conditions.",
}


def _normalise(question: str) -> str:
    # Normalise compatibility characters before applying the unchanged gazetteer.
    text = unicodedata.normalize("NFKC", question).casefold()
    text = "".join(char for char in text if unicodedata.category(char) != "Cf")
    return " ".join(text.split())


def _bound_hits(corpus: PolicyCorpus, hits: list[RetrievalHit]) -> tuple[RetrievalHit, ...]:
    """Output guard: every displayed byte of excerpt text must belong to its cited column."""
    chunks = {chunk.chunk_id: chunk for chunk in corpus.chunks}
    if len(chunks) != len(corpus.chunks) or len(hits) > RESULT_COUNT:
        raise SourceError("Invalid source or result identity.")
    seen = set()
    for rank, hit in enumerate(hits, 1):
        chunk = chunks.get(hit.chunk_id)
        if (chunk is None or hit.chunk_id in seen or hit.text != chunk.text
                or not hit.text.strip() or hit.source_doc != SOURCE_DOC
                or hit.source_url != f"{SOURCE_URL}#page={chunk.page}"
                or hit.captured_on != CAPTURED_ON
                or hit.section != f"PDF page {chunk.page}, {chunk.column} column"
                or hit.rank != rank or not math.isfinite(hit.score) or hit.score <= 0):
            raise SourceError("An excerpt does not bind to the verified guide.")
        seen.add(hit.chunk_id)
    return tuple(hits)


def answer_question(
    question: str,
    *,
    root: Path = ROOT,
    source_loader: Callable[[], PolicyCorpus] | None = None,
) -> ChatResponse:
    """Check one submission before source access; return only fixed wording and bound text.

    The injectable loader is trusted application code and must verify the frozen
    guide, as the default build_corpus implementation does. Never pass user code.
    This function holds no conversation state and performs no logging or network IO.
    """
    normal = _normalise(question) if isinstance(question, str) else ""
    # A matched regex span may contain identity or health details. Public/session
    # responses retain the verdict, never the evaluation-only matched input.
    decision = check(normal).model_copy(update={"trigger": None, "confidence": None})
    if decision.blocked:
        return ChatResponse("blocked", decision, REFUSAL_TEXT[decision.verdict])

    def stop(status: ChatStatus) -> ChatResponse:
        return ChatResponse(status, decision, _MESSAGES[status])

    if not isinstance(question, str) or not normal or len(question) > MAX_QUESTION_CHARS:
        return stop("invalid")
    if os.getenv("OSHC_OFFLINE") != "1" or os.getenv("OSHC_ENABLE_LIVE") != "0":
        return stop("offline_required")
    if _IDENTIFYING.search(normal):
        return stop("privacy")
    if _INJECTION.search(normal):
        return stop("out_of_scope")
    if _PERSONAL_STATE.search(normal) or _CARE_DECISION.search(normal):
        return stop("clarify")
    # Common dictionary words can also be names. Unrecognised title-case words
    # inside a sentence abstain rather than retaining a possible personal name.
    possible_name = any(match.start() > 0 and match.group() not in _PUBLIC_NAMES
                        for match in re.finditer(r"\b[A-Z][a-z]+\b", question))
    if (_THIRD_PERSON.search(normal) or re.search(r"[.!?]\s+\S", normal) or possible_name):
        return stop("clarify")
    if not _TOPIC.search(normal):
        return stop("clarify")
    words = re.findall(r"[a-z]+", normal)
    # Unrecognised characters, numbers, non-English text and unknown terms abstain.
    if (any(word not in _WORDS for word in words)
            or re.search(r"[^a-z\s?'’.,!()/:-]", normal)):
        return stop("out_of_scope")
    if _FIRST_PERSON.search(normal) and not _ADMIN_QUESTION.search(normal):
        return stop("clarify")
    if not _GENERAL_QUESTION.search(normal) and not _ADMIN_QUESTION.search(normal):
        return stop("clarify")
    try:
        corpus = source_loader() if source_loader is not None else build_corpus(Path(root))
        hits = _bound_hits(corpus, PolicySearch(corpus).search(normal, k=RESULT_COUNT))
    except (RuntimeError, OSError, ValueError, TypeError, AttributeError, ArithmeticError, IndexError):
        return stop("source_unavailable")
    if not hits:
        return ChatResponse("no_match", decision, _MESSAGES["no_match"], safe_to_echo=True)
    return ChatResponse("answered", decision, _MESSAGES["answered"], hits, SOURCE_SHA256,
                        safe_to_echo=True)
