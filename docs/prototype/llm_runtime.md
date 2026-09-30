# Prototype LLM runtime

Test responses are fabricated engineering fixtures,
not independent evaluation labels or held-out cases.

- Model: claude-haiku-4-5-20251001, text input, temperature 0.
- Price basis checked 2026-10-01: USD 1 per million input tokens and USD 5
  per million output tokens. No provider tools, prompt caching or thinking.
- Local allowance: USD 8 for calls recorded by this ledger. The AUD 20 project
  budget uses a planning conversion of AUD 2 per USD, allocating AUD 16 plus
  AUD 4 contingency. This planning factor is not a quoted exchange rate.
- This is not an account-wide billing cap. Other clients, previous usage,
  currency conversion and fees are outside the ledger. Check provider billing
  before enabling paid calls. Preserve data/private_runtime/llm_budget.sqlite;
  it is deliberately untracked. Never delete it to reset the allowance.
- Live calls require BOTH OSHC_OFFLINE=0 and OSHC_ENABLE_LIVE=1.
- Free token counting precedes each paid call. Reservations include input
  padding and the requested maximum output. Concurrent reservations serialize
  through SQLite. Unknown usage retains the full reservation. An overrun
  records actual usage and blocks further paid calls for review.
- SDK retries are disabled. JSON repair is off by default; repair=True allows
  one separately budgeted attempt. Validation failure is never a success.
- Version 2 response caches live in cache/llm/v2. They include usage and
  response hashes, but not API keys or full prompts. Only reviewed synthetic
  demo caches should be committed. Old cache records remain historical.
- Offline replay needs a matching version 2 cache. A cache miss or corrupt
  record raises an explicit error. It never silently calls the API.
- These controls do not validate medical or coverage claims. Grounding,
  guardrails and application validation are separate implementation stages.

Check allowance: `python -m oshc.llm_budget status`

References:
- https://platform.claude.com/docs/en/about-claude/pricing
- https://platform.claude.com/docs/en/build-with-claude/token-counting
- https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python
