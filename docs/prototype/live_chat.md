# Live grounded Haiku questions

The live Ask service accepts a complete custom question about general OSHC information or healthcare administration. It uses the configured budgeted Haiku adapter, with the existing explicit live-mode settings and spending ceiling. It does not send bill uploads, chat history or previous turns to the model.

Every submission follows this order:

1. Normalise the current question, then run the deterministic emergency, clinical, personal-advice, privacy and instruction-injection checks. Blocked submissions do not call the provider or load source passages.
2. Ask Haiku for a separate strict semantic input classification. Only an `allow` decision with confidence at least 0.9 can proceed. Uncertain, malformed or unavailable checks stop the request. Emergency classifications always receive the fixed emergency route.
3. Verify the pinned public guide, then retrieve up to five bound columns. The source loader is deliberately delayed until both input gates pass. Complete columns are supplied; an oversized column causes abstention rather than truncating qualifying conditions.
4. Ask Haiku to write up to five short sentences from those passages. Each sentence must carry a known source ID and an exact supporting quotation. Unsupported questions abstain.
5. Validate the draft locally: source IDs, literal quotation containment after whitespace normalisation, output size, plain text, privacy and the deterministic safety checks. No draft is streamed or rendered during this process.
6. Ask Haiku, in a separate request, to audit every sentence for safety, source entailment, preserved conditions, relevance and absence of personal decisions. All dimensions must pass with confidence at least 0.9.
7. Return the complete checked answer with numeric citations and only the verified cited passages. A failed output check discards the entire draft and returns fixed wording.

All three provider calls set `cache=False` and `repair=False`. The service does not write questions, prompts, drafts, quotations or generated answers to the local response cache. The adapter still records its aggregate budget ledger; the provider receives the accepted current question and selected public guide passages. The application must disclose this external processing before the student submits a live question. Provider retention is controlled by the provider account and its terms; this code does not claim zero provider retention.

Local privacy screening is best effort. It recognises explicit identity introductions, labelled identifiers, email addresses, phone-like numbers and dates, but it cannot identify every personal name or sensitive detail in unrestricted language. Students must remove personal information before submitting; the input safety model itself receives any text that passes the local checks. This is not an anonymisation guarantee.

The semantic input review and final audit are separate calls to the same configured model. This is an additional control, not an independent human review or a proof of clinical, legal or policy correctness. Confidence is a model-provided gating value, not calibrated accuracy. The deterministic checks and bound sources remain mandatory. The saved guide has a recorded capture date and may differ from current policy; personal benefits and current eligibility still require Medibank confirmation.

`tests/test_live_chat.py` uses synthetic passages and mocked schemas. It verifies ordering, no retrieval on unsafe input, strict schema failures, no persistent model cache, all-or-nothing output release, citation binding, and provider-error handling without paid calls.
