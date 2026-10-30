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


@dataclass(frozen=True)
class Activity:
    scenario: str
    checklist: tuple[str, ...]


# These fixed activities rehearse the same claims as the verified lesson above.
# They collect no health history, policy details or personal document contents.
ACTIVITIES = {
    "cover_documents": Activity(
        "Mina has received her welcome pack. She wants to understand the cover documents "
        "before she needs to use them.",
        ("I know where to find my Cover Summary.",
         "I know where to find the Member Guide.",
         "I know to read the Cover Summary and Member Guide together."),
    ),
    "mbs_fee": Activity(
        "Arun finds a service in the MBS fee list while preparing to book an appointment. "
        "The clinic has not yet told him what it charges.",
        ("I can tell an MBS reference fee apart from a provider's charge.",
         "I know to ask the clinic for its fee before booking.",
         "I know an MBS fee alone does not confirm the clinic's full price."),
    ),
    "direct_billing": Activity(
        "Linh finds a clinic that offers Medibank OSHC Direct Billing. "
        "She is preparing the questions to ask before booking.",
        ("I know to check the clinic is still a Direct Billing provider.",
         "I know to ask whether any out-of-pocket expense may apply.",
         "I know to take my membership card and photo identification."),
    ),
}


def action_card(lesson: Lesson, checked: tuple[bool, ...] = ()) -> bytes:
    """Make a fixed-content reminder; never include learner-entered free text."""
    activity = ACTIVITIES[lesson.ident]
    lines = ["NextBest | My next-step card", lesson.moment, lesson.title, "",
             "My next step", lesson.action, "", "Preparation self-check"]
    for index, item in enumerate(activity.checklist):
        done = index < len(checked) and checked[index] is True
        lines.append(f"[{'x' if done else ' '}] {item}")
    lines.extend(["", f"Source: Medibank OSHC Member Guide, May 2026, PDF page {lesson.page}, "
                  f"{lesson.column} column.",
                  "General education only. This card does not confirm cover, claim payments "
                  "or clinical readiness.",
                  "Checklist ticks are self-reported preparation, not a learning-impact score."])
    return ("\n".join(lines) + "\n").encode("utf-8")


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
