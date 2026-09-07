"""Provider-agnostic LLM adapter with an on-disk cache.

Every call is keyed by sha256(model + prompt + params) and written to
cache/llm/. The cache directory IS committed. That is what makes evaluation
numbers reproducible and lets the demo run with the network off.

Demo mode: set OSHC_OFFLINE=1. A cache miss then raises instead of calling out,
so a missing cache entry is discovered in rehearsal, not in front of the class.

Owner: Aayush Khade. Reviewer: Minhaj Rahman.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache" / "llm"


class CacheMiss(RuntimeError):
    pass


def _key(model: str, prompt: str, params: dict[str, Any]) -> str:
    blob = json.dumps(
        {"model": model, "prompt": prompt, "params": params}, sort_keys=True
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def complete(
    prompt: str,
    *,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
    image_path: str | None = None,
) -> str:
    """Return a completion, from cache when possible.

    Temperature defaults to 0 and should stay there. A non-zero temperature
    makes the cache key honest but the evaluation irreproducible.
    """
    model = model or os.getenv("OSHC_MODEL", "unset-model")
    params = {"temperature": temperature, "max_tokens": max_tokens, "image": image_path}
    key = _key(model, prompt, params)
    path = _path(key)

    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["response"]

    if os.getenv("OSHC_OFFLINE") == "1":
        raise CacheMiss(f"offline mode and no cached response for {key[:12]}")

    response = _call_provider(prompt, model, temperature, max_tokens, image_path)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"model": model, "params": params, "prompt": prompt, "response": response},
            indent=2,
        ),
        encoding="utf-8",
    )
    return response


def _call_provider(
    prompt: str, model: str, temperature: float, max_tokens: int, image_path: str | None
) -> str:
    """Single place that talks to a network. Implemented in Week 6, day 1.

    Keep every provider detail inside this function. Nothing else in the
    codebase may import a provider SDK.
    """
    raise NotImplementedError(
        "Implement the provider call here. Owner: Aayush. "
        "Read the key from OSHC_API_KEY. Never commit .env."
    )
