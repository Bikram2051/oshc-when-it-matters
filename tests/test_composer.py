from oshc.composer import compose
from oshc.schemas import RetrievalHit


def make_hit(text: str, *, rank: int = 1) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=f"synthetic-{rank}",
        text=text,
        source_doc="synthetic-guide.pdf",
        source_url="https://example.com/synthetic-guide",
        section="Section 1",
        captured_on="2026-10-01",
        score=0.9,
        rank=rank,
    )


def test_compose_returns_relevant_source_text_and_citation():
    hit = make_hit(
        "The PDS states that eligible medical services may receive benefits."
    )

    result = compose("What does the PDS say about benefits?", [hit])

    assert not result.abstained
    assert "The PDS states that eligible medical services may receive benefits." in result.text
    assert result.citations[0].source_doc == "synthetic-guide.pdf"
    assert result.citations[0].source_url == "https://example.com/synthetic-guide"


def test_compose_abstains_when_no_hits_are_available():
    result = compose("What benefits can I claim?", [])

    assert result.abstained
    assert "PDS" in result.text or "document" in result.text.lower()
    assert result.citations == []


def test_compose_does_not_claim_personal_coverage():
    hit = make_hit(
        "The PDS states that benefits depend on the applicable terms and conditions."
    )

    result = compose("Am I covered?", [hit])

    assert "you are covered" not in result.text.lower()
    assert "your exact benefit is confirmed" not in result.text.lower()


def test_compose_does_not_repeat_duplicate_source_sentences():
    sentence = "This document shows the relevant eligibility conditions."
    hits = [
        make_hit(sentence, rank=1),
        make_hit(sentence, rank=2),
    ]

    result = compose("What does the document show?", hits)

    assert result.text.count(sentence) == 1
