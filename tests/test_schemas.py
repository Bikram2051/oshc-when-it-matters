"""Contract tests. These fail loudly if a frozen interface drifts."""
import pytest
from pydantic import ValidationError

from oshc.schemas import (
    CODE_LABELS, Code, Event, EventName, ExtractionResult, GuardrailDecision,
    GuardrailVerdict, LineItem,
)


def test_every_code_has_a_label():
    assert set(CODE_LABELS) == set(Code)


def test_code_labels_match_the_coding_frame():
    assert CODE_LABELS[Code.C2] == "What is covered"
    assert CODE_LABELS[Code.C4] == "Claiming process"


def test_guardrail_blocked_property():
    assert not GuardrailDecision(verdict=GuardrailVerdict.ALLOW, layer="none").blocked
    assert GuardrailDecision(verdict=GuardrailVerdict.REFUSE_ADVICE, layer="gazetteer").blocked


def test_extraction_result_requires_known_extractor():
    with pytest.raises(ValidationError):
        ExtractionResult(extractor="magic", source_kind="pdf_text")


def test_line_item_defaults_to_unmatched():
    assert LineItem(raw_description="Bed day charge").matched is False


def test_event_rejects_unknown_page():
    with pytest.raises(ValidationError):
        Event(session_id="x", name=EventName.OPEN, at="2026-09-07T00:00:00", page="settings")
