'''Offline tests using fabricated responses, not evaluation or held-out data.'''

import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace as NS

import pytest
from pydantic import BaseModel, ConfigDict

from oshc import llm
from oshc.llm_budget import Budget, BudgetError, LIMIT, MODEL


def response(text="hello", stop="end_turn"):
    return NS(id="test-message", model=MODEL, stop_reason=stop,
              content=[NS(type="text", text=text)],
              usage=NS(input_tokens=100, output_tokens=20))


class FakeClient:
    def __init__(self):
        self.messages = self
        self.responses = [response()]
        self.requests = []
        self.count_requests = []
        self.count = 100

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def count_tokens(self, **kwargs):
        self.count_requests.append(kwargs)
        return NS(input_tokens=self.count)

    def create(self, **kwargs):
        self.requests.append(kwargs)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture
def runtime(monkeypatch, tmp_path):
    budget = Budget(tmp_path / "budget.sqlite")
    budget.initialize()
    fake = FakeClient()
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(llm, "Budget", lambda: budget)
    monkeypatch.setattr(llm, "_client", lambda: fake)
    monkeypatch.setenv("OSHC_MODEL", MODEL)
    monkeypatch.setenv("OSHC_OFFLINE", "0")
    monkeypatch.setenv("OSHC_ENABLE_LIVE", "1")
    return fake, budget


@pytest.mark.parametrize("offline,enable", [(None, "1"), ("1", "1"), ("0", None)])
def test_offline_never_contacts_provider(runtime, monkeypatch, offline, enable):
    for key, value in (("OSHC_OFFLINE", offline), ("OSHC_ENABLE_LIVE", enable)):
        monkeypatch.delenv(key, raising=False) if value is None else monkeypatch.setenv(key, value)
    with pytest.raises(llm.CacheMiss):
        llm.complete("offline")
    assert runtime[0].count_requests == []
    assert runtime[0].requests == []


def test_cache_replay_and_usage(runtime, monkeypatch):
    fake, budget = runtime
    assert llm.complete("cache me", system="instruction") == "hello"
    assert fake.requests[0]["extra_body"] == {"temperature": 0}
    assert budget.status()["spent_or_reserved"] == 0.0002
    monkeypatch.setenv("OSHC_OFFLINE", "1")
    assert llm.complete("cache me", system="instruction") == "hello"
    assert len(fake.requests) == 1
    with pytest.raises(llm.CacheMiss):
        llm.complete("cache me", system="changed")
    with pytest.raises(llm.CacheMiss):
        llm.complete("cache me", system="instruction", max_tokens=1025)


@pytest.mark.parametrize("kwargs", [dict(model="other-model"), dict(image_path="x.png"),
                                   dict(max_tokens=4097), dict(temperature=0.5)])
def test_unsupported_requests_are_not_sent(runtime, kwargs):
    with pytest.raises(llm.LLMError):
        llm.complete("test", **kwargs)
    assert runtime[0].count_requests == []


def test_corrupt_cache_fails_without_paid_fallback(runtime):
    llm.complete("test")
    path = next(llm.CACHE_DIR.glob("*.json"))
    item = json.loads(path.read_text())
    item["response"] = "tampered"
    path.write_text(json.dumps(item))
    with pytest.raises(llm.CacheError):
        llm.complete("test")
    assert len(runtime[0].requests) == 1


def test_failed_call_keeps_reservation_across_restart(runtime):
    fake, budget = runtime
    fake.responses = [TimeoutError("simulated")]
    with pytest.raises(llm.ProviderError):
        llm.complete("test", max_tokens=100)
    state = Budget(budget.path).status()
    assert state["spent_or_reserved"] == 0.001624
    assert state["unsettled_calls"] == 1
    assert len(fake.requests) == 1


@pytest.mark.parametrize("stop", ["max_tokens", "refusal", "tool_use"])
def test_incomplete_or_refused_output_is_billed_but_not_cached(runtime, stop):
    runtime[0].responses = [response(stop=stop)]
    with pytest.raises(llm.ProviderError):
        llm.complete("test")
    assert runtime[1].status()["spent_or_reserved"] == 0.0002
    assert list(llm.CACHE_DIR.glob("*.json")) == []


def test_missing_usage_retains_reservation(runtime):
    runtime[0].responses[0].usage = None
    with pytest.raises(llm.ProviderError):
        llm.complete("test")
    assert runtime[1].status()["unsettled_calls"] == 1


def test_oversized_input_never_creates_a_message(runtime):
    runtime[0].count = 12_001
    with pytest.raises(llm.LLMError):
        llm.complete("test")
    assert runtime[0].requests == []


class Result(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: int


def test_json_validation_is_strict_with_no_default_retry(runtime):
    runtime[0].responses = [response('{"value":"7"}')]
    with pytest.raises(llm.OutputValidationError):
        llm.complete_json("test", Result)
    assert len(runtime[0].requests) == 1


def test_one_repair_is_budgeted_and_can_replay_offline(runtime, monkeypatch):
    fake, budget = runtime
    fake.responses = [response("invalid"), response('{"value":7}')]
    assert llm.complete_json("test", Result, repair=True).value == 7
    assert len(fake.requests) == 2
    assert budget.status()["spent_or_reserved"] == 0.0004
    monkeypatch.setenv("OSHC_OFFLINE", "1")
    assert llm.complete_json("test", Result, repair=True).value == 7
    assert len(fake.requests) == 2


def test_bad_repair_stops_after_two_calls(runtime):
    runtime[0].responses = [response("bad"), response("still bad")]
    with pytest.raises(llm.OutputValidationError):
        llm.complete_json("test", Result, repair=True)
    assert len(runtime[0].requests) == 2


def test_budget_reservations_are_atomic(runtime):
    budget = runtime[1]
    def reserve(_):
        try:
            Budget(budget.path).reserve("parallel-test", 100_000)
            return True
        except BudgetError:
            return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        successes = list(pool.map(reserve, range(90)))
    assert sum(successes) == LIMIT // 100_000
    assert budget.status()["spent_or_reserved"] == 8.0


def test_overrun_is_recorded_and_blocks_future_calls(runtime):
    budget = runtime[1]
    ticket = budget.reserve("test", 10)
    with pytest.raises(BudgetError):
        budget.settle(ticket, 20, 0)
    assert budget.status()["spent_or_reserved"] == 0.000020
    assert budget.status()["blocked_for_review"] is True
    with pytest.raises(BudgetError):
        budget.reserve("next", 10)


def test_missing_ledger_does_not_reset_budget(tmp_path):
    with pytest.raises(BudgetError):
        Budget(tmp_path / "missing.sqlite").reserve("test", 10)


def test_real_client_configuration_disables_retries(monkeypatch):
    import anthropic
    captured = {}
    def constructor(**kwargs):
        captured.update(kwargs)
        return object()
    monkeypatch.setattr(anthropic, "Anthropic", constructor)
    monkeypatch.setenv("OSHC_API_KEY", "unit-test-placeholder")
    llm._client()
    assert captured["max_retries"] == 0
    assert captured["timeout"] == 30.0
    assert captured["base_url"] == "https://api.anthropic.com"


def test_installed_sdk_request_and_response_without_network(runtime, monkeypatch):
    import httpx2
    from anthropic import Anthropic
    seen = []

    def handle(request):
        payload = json.loads(request.content)
        seen.append(request.url.path)
        assert payload["model"] == MODEL
        if request.url.path == "/v1/messages/count_tokens":
            return httpx2.Response(200, json={"input_tokens": 100})
        assert request.url.path == "/v1/messages"
        assert payload["temperature"] == 0
        assert payload["max_tokens"] == 1024
        assert payload["service_tier"] == "standard_only"
        return httpx2.Response(200, json={
            "id": "test-sdk", "type": "message", "role": "assistant", "model": MODEL,
            "content": [{"type": "text", "text": "sdk-ok"}],
            "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 100, "output_tokens": 20},
        })

    monkeypatch.setattr(llm, "_client", lambda: Anthropic(
        api_key="unit-test-placeholder", max_retries=0,
        http_client=httpx2.Client(transport=httpx2.MockTransport(handle))))
    assert llm.complete("SDK compatibility") == "sdk-ok"
    assert seen == ["/v1/messages/count_tokens", "/v1/messages"]
