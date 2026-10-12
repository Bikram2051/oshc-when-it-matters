'''Regression tests for response formatting. All responses are local fixtures.'''

from typing import Literal
from unittest.mock import Mock

import pytest
from pydantic import BaseModel, ConfigDict

from oshc import llm


class Check(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ok"]
    count: int = 0


@pytest.mark.parametrize("text", [
    '{"status":"ok"}',
    '```json\n{"status":"ok"}\n```',
    '```\n{"status":"ok"}\n```',
    ' \n```JSON\r\n{"status":"ok"}\r\n```\n ',
])
def test_json_wrapper_is_accepted(monkeypatch, text):
    provider = Mock(return_value=text)
    monkeypatch.setattr(llm, "complete", provider)
    assert llm.complete_json("format check", Check).status == "ok"
    provider.assert_called_once()


@pytest.mark.parametrize("text", [
    'Here it is:\n```json\n{"status":"ok"}\n```',
    '```json\n{"status":"ok"}\n```\nDone.',
    '```python\n{"status":"ok"}\n```',
    '```json\n{"status":"wrong"}\n```',
    '```json\n{"status":"ok","extra":1}\n```',
    '```json\n{"status":"ok","count":"7"}\n```',
    '```json\n{"status":"ok"}\n',
    '```json\n{"status":"ok"}\n```\n```json\n{"status":"ok"}\n```',
    '```json\nnot-json\n```',
    '```json\n{"status":"ok"} {"status":"ok"}\n```',
])
def test_other_content_is_still_rejected(monkeypatch, text):
    provider = Mock(return_value=text)
    monkeypatch.setattr(llm, "complete", provider)
    with pytest.raises(llm.OutputValidationError):
        llm.complete_json("format check", Check)
    provider.assert_called_once()
