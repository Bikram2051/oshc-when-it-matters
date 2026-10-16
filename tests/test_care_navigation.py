"""Personal symptoms get a fixed handoff before live processing, never a triage answer."""
from unittest.mock import Mock

import pytest

from oshc.care_navigation import SERVICE_FINDER_URL, SYMPTOM_CHECKER_URL, personal_symptom_request
from oshc.schemas import GuardrailVerdict
from oshc.student_chat import answer_question


@pytest.mark.parametrize("question", [
    "I am having caught and mild headache where should I go?",
    "I have a cough, where should I go?",
    "I'm feeling dizzy and have a headache",
    "I've got a sore throat",
    "My roommate has a fever",
    "I am unwell",
])
def test_personal_symptoms_stop_before_provider_and_source(monkeypatch, question):
    monkeypatch.setenv("OSHC_OFFLINE", "0")
    monkeypatch.setenv("OSHC_ENABLE_LIVE", "1")
    provider = Mock(side_effect=AssertionError("No provider access for this disclosure"))
    loader = Mock(side_effect=AssertionError("No source lookup for symptoms"))
    monkeypatch.setattr("oshc.live_chat.answer_live", provider)
    response = answer_question(question, source_loader=loader)
    assert response.decision.verdict == GuardrailVerdict.REFUSE_CLINICAL
    assert "1800 022 222" in response.message
    assert not response.answer and not response.hits and not response.safe_to_echo
    assert question not in repr(response)
    provider.assert_not_called()
    loader.assert_not_called()


def test_emergency_precedes_symptom_handoff(monkeypatch):
    monkeypatch.setenv("OSHC_OFFLINE", "0")
    monkeypatch.setenv("OSHC_ENABLE_LIVE", "1")
    response = answer_question("I have a headache and can't breathe")
    assert response.decision.verdict == GuardrailVerdict.ESCALATE_EMERGENCY
    assert "000" in response.message and not response.answer


@pytest.mark.parametrize("question", [
    "How do I book a GP appointment?",
    "I have a membership card; how do I submit a claim?",
    "What documents should I bring to a GP appointment?",
])
def test_general_administration_is_not_a_symptom_disclosure(question):
    assert not personal_symptom_request(question)


def test_handoff_urls_never_include_private_question_parameters():
    for url in (SERVICE_FINDER_URL, SYMPTOM_CHECKER_URL):
        assert url.startswith("https://www.healthdirect.gov.au/")
        assert "?" not in url and "#" not in url
