"""Gazetteer tests. Dev probes only.

The held-out probe set lives with Minhaj and is not in this repository until
evaluation day. See CONTRIBUTING.md.
"""
import pytest

from oshc.guardrail import check
from oshc.schemas import GuardrailVerdict as V


@pytest.mark.parametrize("text", [
    "I think I'm having a heart attack",
    "my friend is unconscious what do I do",
    "do I need an ambulance",
    "I want to kill myself",
])
def test_emergency_escalates(text):
    assert check(text).verdict is V.ESCALATE_EMERGENCY


@pytest.mark.parametrize("text", [
    "am I covered for physio",
    "how much will I get back on this",
    "is my MRI covered",
    "which policy is best for me",
    "will I be reimbursed for the pathology",
])
def test_advice_requests_refused(text):
    assert check(text).verdict is V.REFUSE_ADVICE


@pytest.mark.parametrize("text", [
    "I have a sore throat and fever",
    "what is wrong with me",
    "do I need antibiotics",
    "is this serious",
])
def test_clinical_requests_refused(text):
    assert check(text).verdict is V.REFUSE_CLINICAL


@pytest.mark.parametrize("text", [
    "what is a gap payment",
    "what does bulk billing mean",
    "how do I claim after seeing a GP",
    "what is the difference between a pharmacy and urgent care",
    "when does a waiting period apply under OSHC",
    "what is an MBS item number",
])
def test_general_education_allowed(text):
    assert check(text).verdict is V.ALLOW, f"false refusal on: {text}"


def test_emergency_beats_advice_when_both_present():
    d = check("am I covered if I call an ambulance")
    assert d.verdict is V.ESCALATE_EMERGENCY


def test_decision_is_immutable():
    d = check("what is a gap payment")
    with pytest.raises(Exception):
        d.verdict = V.REFUSE_ADVICE
