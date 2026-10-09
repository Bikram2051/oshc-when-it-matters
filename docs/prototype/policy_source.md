# Verified policy source and keyword-search baseline

Engineering checks only. No independent accuracy claim.

The source is the frozen Medibank OSHC Member Guide, SHA-256
`6ca7151567ee2b61f8e6b50340c297d50deb249a013f055ef38f50ed07ec87c7`.
The cover says effective May 2026. The snapshot was captured 28 September 2026;
the March PDF creation date is not the policy effective date.

`oshc.policy_source.build_corpus()` verifies the manifest and raw PDF before
extracting. The layout profile is restricted to this exact document. It keeps
left and right columns separate, retains line geometry, and cites physical PDF
pages starting at 1. It copies a shared page title into each applicable column.
Whitespace within a line is normalised; line breaks and policy wording remain.

There are 61 column excerpts across 31 physical pages. Pages 1, 2, 6, 7 and 37
are front/back matter or contents. Page 19 is a hospital-benefits table; its cells
are deliberately excluded from prose retrieval and must be viewed in the PDF.
An excerpt can depend on another column, page, definition or Cover Summary.
It is not complete policy interpretation or an eligibility decision.

`oshc.policy_search.PolicySearch` is a BM25Okapi development baseline. It returns
the existing frozen RetrievalHit type. Scores rank matches and are not confidence
values. Unmatched queries return no hits. The planned dense/hybrid retrieval,
grounded composer and conversational safety gate remain separate work.
The original `oshc/retrieval.py` contract is unchanged.

Derived text is written only under ignored `corpus/index/`. Do not commit the PDF
or that index. Search uses a freshly verified in-memory corpus, not an unchecked
JSON artifact. A differing existing artifact is kept for review, not overwritten.
Only code, engineering tests, this note and the metadata-only check report belong
in the commit. No paid model or embedding calls are used in this checkpoint.

Run `python scripts/prototype_check_policy_source.py` with paid calls disabled.
Its six known-topic searches are development smoke checks, not the frozen gold
evaluation or held-out Recall@5. The safety gate is not implemented by this search
module, and this checkpoint does not enable the conversational Navigator UI.
