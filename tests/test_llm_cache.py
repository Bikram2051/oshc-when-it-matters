import os

import oshc.llm as llm


def test_cache_replay_without_api_key(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path)

    prompt = "Reply with exactly: cache replay works"
    expected = "cache replay works"

    calls = []

    def fake_provider(prompt, model, temperature, max_tokens, image_path):
        calls.append(1)
        return expected

    monkeypatch.setattr(llm, "_call_provider", fake_provider)

    monkeypatch.delenv("OSHC_API_KEY", raising=False)
    monkeypatch.delenv("OSHC_OFFLINE", raising=False)

    first = llm.complete(prompt)

    monkeypatch.setenv("OSHC_OFFLINE", "1")

    second = llm.complete(prompt)

    assert first == expected
    assert second == first
    assert len(calls) == 1
    assert len(list(tmp_path.glob("*.json"))) == 1
