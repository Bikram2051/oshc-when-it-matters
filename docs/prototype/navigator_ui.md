# Navigator source browser

This checkpoint adds a source
browser to the Navigator page. It is not a conversational Navigator or a claim decision.

- Six fixed topics use the existing BM25 baseline, preserving its ranking.
- The selected full column is shown beside its original physical PDF page.
- Page 19 stays out of text search; Read a page opens its original hospital table.
- All 37 physical pages can be inspected, including adjacent pages and excluded pages.
- Citations identify physical page, column and capture date. The publisher link may
  change; previews and downloads use the verified local May 2026 guide.
- Each UI rerun checks the manifest and PDF again. An invalid source clears visible
  excerpts, previews and the download. No saved search result bypasses that check.
- No free-text question field, generated answer, translation, telemetry, LLM request
  or disk cache is added. The runtime must remain in offline mode.

Run `python -m streamlit run app/Home.py` and open Navigator. Select Making a claim,
choose PDF page 28, right column, then use Read a page to inspect page 19.

`tests/test_navigator_ui.py` uses synthetic documents. The actual-source rehearsal
is `python scripts/prototype_check_navigator_ui.py`; its report contains metadata,
not copied guide text. To preserve a previous report, pass a new `--out` path.

These are engineering checks. They do not establish held-out Recall@5, refusal
recall, clinical safety or accurate personal coverage advice. Free-form interaction,
hybrid retrieval and citation-checked composition remain separate work. Do not
treat this checkpoint as satisfying the project's conversational safety gate.
