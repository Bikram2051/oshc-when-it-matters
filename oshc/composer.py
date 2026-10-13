from __future__ import annotations

import re

from oshc.schemas import Citation, ComposedAnswer, RetrievalHit


_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "can", "do", "does",
    "for", "from", "how", "i", "in", "is", "it", "me", "my", "of",
    "on", "or", "please", "say", "the", "to", "under", "was", "what",
    "when", "where", "which", "who", "why", "with", "you", "your",
    "am", "about", "tell", "explain", "show", "that", "this", "may",
    "receive", "states",
}

_ABSTAIN_TEXT = (
    "I can't confirm this from the retrieved documents. "
    "Please check the relevant PDS or contact Medibank."
)


def _normalise_token(token: str) -> str:
    if len(token) > 5 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith("s"):
        return token[:-1]
    if len(token) > 5 and token.endswith("ed"):
        return token[:-2]
    if len(token) > 6 and token.endswith("ing"):
        return token[:-3]
    return token


def _keywords(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z]+", text.lower())
    return {
        _normalise_token(word)
        for word in words
        if word not in _STOP_WORDS and len(word) > 1
    }


def _sentences(text: str) -> list[str]:
    return [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+|\n+", text.strip())
        if part.strip()
    ]


def compose(question: str, hits: list[RetrievalHit]) -> ComposedAnswer:
    """Build an extractive answer from relevant retrieved source sentences."""
    question_keywords = _keywords(question)
    selected_sentences: list[str] = []
    citations: list[Citation] = []
    seen_sentences: set[str] = set()
    seen_citations: set[tuple[str, str | None, str, str]] = set()

    for hit in sorted(hits, key=lambda item: item.rank):
        for sentence in _sentences(hit.text):
            sentence_key = " ".join(sentence.lower().split())

            if sentence_key in seen_sentences:
                continue

            sentence_keywords = _keywords(sentence)
            if not question_keywords.intersection(sentence_keywords):
                continue

            seen_sentences.add(sentence_key)
            selected_sentences.append(sentence)

            citation_key = (
                hit.source_doc,
                hit.section,
                hit.source_url,
                hit.captured_on,
            )
            if citation_key not in seen_citations:
                citations.append(
                    Citation(
                        source_doc=hit.source_doc,
                        section=hit.section,
                        source_url=hit.source_url,
                        captured_on=hit.captured_on,
                    )
                )
                seen_citations.add(citation_key)

    if not selected_sentences:
        return ComposedAnswer(
            text=_ABSTAIN_TEXT,
            citations=[],
            abstained=True,
            unsupported_dropped=0,
        )

    return ComposedAnswer(
        text=" ".join(selected_sentences),
        citations=citations,
        abstained=False,
        unsupported_dropped=0,
    )
