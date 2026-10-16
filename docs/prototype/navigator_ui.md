# Navigator: services and policy source

The current Navigator works alongside guarded live Haiku chat. Browsing this page
never calls an AI provider, in either runtime mode. It combines fixed service
navigation with the verified source browser below; it never assesses symptoms,
chooses an urgency level, checks appointment availability or decides personal cover.

- Students choose GP, telehealth, pharmacy, claims or membership tasks. Each task
  shows general preparation questions and a related guide-topic button.
- Official healthdirect Service Finder and Symptom Checker open in a new tab.
  No student question, location or identity is encoded in those links. The student
  enters any details directly with that service, under its privacy terms.
- Fixed external links remain available when the local guide cannot be verified.
  Guide excerpts, page previews and downloads remain hidden after a source failure.
- The expanded guide topics include GP services and medicines. The saved guide has
  no dedicated telehealth entry. That service card links to the related GP text
  and explicitly states that it does not establish telehealth cover.
  Each topic opens an authored starting column verified against exact source
  anchors. Other related sections retain the existing BM25 ranking; that ranking
  is not a confidence score. These display choices do not change shared retrieval.

## Source integrity

- Fixed topic starting columns are: claims28 right, waiting21 right, card8 left,
  direct billing28 right, ambulance25 left, MBS17 left, GP17 right, medicines24 left.
  Missing columns or anchor wording fail closed; a passing mention cannot replace
  the chosen starting section. Related BM25 matches are labelled separately.
- The selected full column is shown beside its original physical PDF page.
- Page 19 stays out of text search; Read a page opens its original hospital table.
- All 37 physical pages can be inspected, including adjacent pages and excluded pages.
- Citations identify physical page, column and capture date. The publisher link may
  change; previews and downloads use the verified local May 2026 guide.
- Each UI rerun checks the manifest and PDF again. An invalid source clears visible
  excerpts, previews and the download. No saved search result bypasses that check.
- No free-text question field, generated answer, translation, telemetry, LLM request
  or disk cache is added. Live chat's global flags do not disable source browsing.

Run `python -m streamlit run app/Home.py` and open Navigator. Select Making a claim,
choose PDF page 28, right column, then use Read a page to inspect page 19.

`tests/test_navigator_ui.py` uses synthetic documents. The actual-source rehearsal
is `python scripts/prototype_check_navigator_ui.py`; its report contains metadata,
not copied guide text. To preserve a previous report, pass a new `--out` path.

The UI tests exercise both runtime modes with provider access trapped, service
selection and the guide-topic handoff. These are engineering checks. They do not
establish held-out Recall@5, refusal recall, clinical safety or accurate personal
coverage advice. They do not evaluate the separate Ask NextBest live model or
satisfy the project's conversational safety gate.
