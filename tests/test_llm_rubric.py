"""Layer 2 LLM rubric tests.

Dev probes only. Held-out guardrail probes are kept outside the repository.
"""

import oshc.llm_rubric as rubric
from oshc.schemas import GuardrailVerdict as V


def test_emergency_rubric_escalates(monkeypatch):
    monkeypatch.setattr(
        rubric,
        "_classify",
        lambda text: (
            "ESCALATE_EMERGENCY",
            "emergency/crisis request",
            0.99,
        ),
    )

    decision = rubric.check(
        "I think I am having a panic attack and need urgent help"
    )

    assert decision.verdict is V.ESCALATE_EMERGENCY
    assert decision.layer == "llm_rubric"
    assert decision.confidence == 0.99


def test_clinical_rubric_refuses(monkeypatch):
    monkeypatch.setattr(
        rubric,
        "_classify",
        lambda text: (
            "REFUSE_CLINICAL",
            "symptom assessment",
            0.95,
        ),
    )

    decision = rubric.check(
        "Could these symptoms mean I have an infection?"
    )

    assert decision.verdict is V.REFUSE_CLINICAL
    assert decision.layer == "llm_rubric"


def test_advice_rubric_refuses(monkeypatch):
    monkeypatch.setattr(
        rubric,
        "_classify",
        lambda text: (
            "REFUSE_ADVICE",
            "personal coverage advice",
            0.94,
        ),
    )

    decision = rubric.check(
        "Will my policy pay for this treatment?"
    )

    assert decision.verdict is V.REFUSE_ADVICE
    assert decision.layer == "llm_rubric"


def test_educational_question_allowed(monkeypatch):
    monkeypatch.setattr(
        rubric,
        "_classify",
        lambda text: (
            "ALLOW",
            "general OSHC education",
            0.97,
        ),
    )

    decision = rubric.check(
        "What is an MBS item number?"
    )

    assert decision.verdict is V.ALLOW
    assert decision.layer == "llm_rubric"


def test_low_confidence_defaults_to_allow(monkeypatch):
    monkeypatch.setattr(
        rubric,
        "_classify",
        lambda text: (
            "REFUSE_ADVICE",
            "uncertain",
            0.40,
        ),
    )

    decision = rubric.check(
        "Can you explain how OSHC works?"
    )

    assert decision.verdict is V.ALLOW


def test_invalid_llm_label_defaults_to_allow(monkeypatch):
    monkeypatch.setattr(
        rubric,
        "_classify",
        lambda text: (
            "SOMETHING_ELSE",
            "invalid output",
            0.99,
        ),
    )

    decision = rubric.check(
        "What does bulk billing mean?"
    )

    assert decision.verdict is V.ALLOW
