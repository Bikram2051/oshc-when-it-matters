# LLM bill extractor

Uses the existing frozen
ExtractionResult and LineItem interfaces and the existing budgeted LLM adapter.

## Behaviour

- Input is pasted text or BillText from the local PDF reader. No OCR or images.
- The model selects source ranges and copies complete printed field strings.
- Supported evidence is a labelled table row with its nearest header, or a
  complete block starting with Description:, Service: or Service description:.
- Local checks bind each copied field to its source row and column or label.
  Matching a number somewhere in the bill is insufficient evidence.
- Money/item/date parsing and amount consistency checks reuse the rules parser.
- Amount paid, Paid, estimated benefits and unlabelled Benefit are not accepted
  as insurer benefits. Missing values stay unknown. Printed zero stays zero.
- Conflicting totals are unknown. Printed totals are never invented by summing.
- No MBS matching, benefit estimates, coverage decisions or clinical advice.
- Unsupported model fields are omitted with warnings. Unsupported rows, overlapping
  rows and partial or combined blocks are rejected. Totals require their own evidence.
- Cache, provider, budget or output-schema failures return an empty result with
  an explicit warning. There is no automatic rules fallback or repair request.

## Operation

Call `oshc.billexplainer.extract_llm.extract(text_or_billtext)`.
Offline is the default. The existing adapter requires both OSHC_OFFLINE=0 and
OSHC_ENABLE_LIVE=1 to make a paid request. Use synthetic development bills only
for the prototype's paid requests and committed cache examples.

Input limit: 18,000 UTF-8 bytes and 500 lines. At most 20 proposed rows.
Output token limit: 3,072. Oversized inputs are rejected, never silently truncated.
The adapter also checks the complete prompt size and token count before spending.

## Evidence and limitations

The model interprets layout; deterministic checks constrain the financial output
to supported printed fields. The supported-format list is intentionally limited.
This is an LLM-assisted pipeline sharing validators with the rules baseline;
comparisons measure the complete pipelines, not an unconstrained model alone.
Source checks cannot establish document authenticity, correct source PDF layout,
complete extraction or the meaning of ambiguous invoice terminology. The model
can omit rows, and unsupported formats may return no usable rows.

Tests use synthetic development inputs and mocked model responses, plus a real
adapter offline cache-miss check. They verify software behaviour, not model
accuracy, clinical safety or independent evaluation performance.

A controlled synthetic API extraction and cached replay remain to be verified.
Held-out invoice families have not been opened or used for this implementation.
