"""Cache replay test (Aayush Khade), adapted to the offline-by-default adapter.

The adapter now refuses live calls unless OSHC_OFFLINE=0 and OSHC_ENABLE_LIVE=1,
and every live call is charged to a spending ledger. The test therefore enables
live mode explicitly for the first call, uses a temporary ledger and a fake
client, and keeps the original checks: one provider call, then an identical
offline replay with no API key, and exactly one cache file.
"""

from types import SimpleNamespace as NS

import oshc.llm as llm
from oshc.llm_budget import MODEL, Budget


class FakeClient:
    """Stands in for the Anthropic client and counts provider calls."""

    def __init__(self, text):
        self.messages = self
        self.text = text
        self.calls = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def count_tokens(self, **kwargs):
        return NS(input_tokens=10)

    def create(self, **kwargs):
        self.calls += 1
        return NS(
            id="test-message",
            model=MODEL,
            stop_reason="end_turn",
            content=[NS(type="text", text=self.text)],
            usage=NS(input_tokens=10, output_tokens=5),
        )


def test_cache_replay_without_api_key(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path)

    prompt = "Reply with exactly: cache replay works"
    expected = "cache replay works"

    budget = Budget(tmp_path / "budget.sqlite")
    budget.initialize()
    fake = FakeClient(expected)
    monkeypatch.setattr(llm, "Budget", lambda: budget)
    monkeypatch.setattr(llm, "_client", lambda: fake)
    monkeypatch.setenv("OSHC_MODEL", MODEL)

    # First call: live mode must now be enabled explicitly.
    monkeypatch.setenv("OSHC_OFFLINE", "0")
    monkeypatch.setenv("OSHC_ENABLE_LIVE", "1")
    first = llm.complete(prompt)

    # Second call: offline and with no API key, it must replay from the cache.
    monkeypatch.delenv("OSHC_API_KEY", raising=False)
    monkeypatch.setenv("OSHC_OFFLINE", "1")
    second = llm.complete(prompt)

    assert first == expected
    assert second == first
    assert fake.calls == 1
    assert len(list(tmp_path.glob("*.json"))) == 1
