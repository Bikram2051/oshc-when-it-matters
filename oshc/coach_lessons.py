"""Authored English demo lessons grounded in the frozen guide.

This editorial baseline does not implement corpus keyness or adaptive learning.
Source-span checks establish provenance, not proof of educational effectiveness.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from oshc.policy_source import ROOT, PolicyChunk, SourceError, build_corpus


@dataclass(frozen=True)
class Lesson:
    ident: str
    moment: str
    title: str
    points: tuple[str, ...]
    action: str
    question: str
    options: tuple[str, ...]
    correct: int
    explanation: str
    page: int
    column: str
    anchors: tuple[str, ...]


LESSONS = (
    Lesson(
        "cover_documents", "Before you arrive", "Find your cover details",
        ("The welcome pack includes a Member Guide and a Cover Summary.",
         "The Cover Summary sets out what is included under your cover.",
         "Read the two documents together to understand the cover."),
        "Find your Cover Summary and Member Guide, and keep them together.",
        "Which document sets out what is included under your cover?",
        ("A doctor's invoice.", "The Cover Summary.", "The MBS fee list."), 1,
        "The Cover Summary sets out what is included. The guide says to read it together "
        "with the Member Guide.", 8, "left",
        ("A Cover Summary, which sets out", "read your Cover Summary and this Guide"),
    ),
    Lesson(
        "mbs_fee", "Settling in", "A reference fee and a doctor's price can differ",
        ("The Medicare Benefits Schedule (MBS) lists services and government fees used "
         "to calculate Medicare benefits.",
         "Doctors and other providers can charge more than the MBS fee.",
         "The MBS fee alone does not tell you the price of an appointment."),
        "Ask the clinic what it charges before booking.",
        "You find an MBS fee for a service. Does that confirm the clinic's full price?",
        ("Yes. Every clinic must charge exactly the MBS fee.",
         "Yes. OSHC always pays anything above that fee.",
         "No. The provider can charge more; ask the clinic for its fee."), 2,
        "The guide says providers are not restricted to the MBS fee. Confirm the clinic's "
        "charge separately; this lesson does not calculate your benefit.", 17, "left",
        ("for the purpose of calculating the Medicare benefit payable",
         "Doctors and providers are not restricted to charging the MBS fee"),
    ),
    Lesson(
        "direct_billing", "Before an appointment", "Check direct billing and possible costs",
        ("A Medibank OSHC Direct Billing provider has an agreement to send the bill "
         "directly to Medibank.",
         "This can reduce or remove an upfront payment. An out-of-pocket expense may "
         "still apply.",
         "Before booking, check possible costs and whether the provider is still in "
         "the Direct Billing network."),
        "Ask: 'Are you a Medibank OSHC Direct Billing provider, and could I have an "
        "out-of-pocket expense?' Take your membership card and photo ID.",
        "A clinic offers Medibank OSHC Direct Billing. What should you check before booking?",
        ("Whether any out-of-pocket expenses may apply.",
         "Nothing. Direct billing guarantees every charge is paid in full.",
         "Only whether the clinic accepts cash."), 0,
        "Direct billing can reduce or remove an upfront payment, but the guide says "
        "an out-of-pocket expense may still apply. Ask the provider before booking.", 28, "right",
        ("an agreement with Medibank to send the bill directly to us",
         "Before booking your consultation, check with the Direct Billing provider "
         "whether any out-of-pocket expenses may apply.",
         "Remember to take your membership card and photo identification."),
    ),
)


def verified_sources(root: Path = ROOT) -> dict[str, PolicyChunk]:
    corpus = build_corpus(root)
    columns = {(chunk.page, chunk.column): chunk for chunk in corpus.chunks}
    sources = {}
    for lesson in LESSONS:
        chunk = columns.get((lesson.page, lesson.column))
        if chunk is None or any(anchor not in " ".join(chunk.text.split())
                                for anchor in lesson.anchors):
            raise SourceError(f"Lesson source could not be verified: {lesson.ident}")
        sources[lesson.ident] = chunk
    return sources
