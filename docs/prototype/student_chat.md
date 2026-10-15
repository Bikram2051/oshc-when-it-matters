# Guarded guide chat

Historical source-only specification. Normal application startup now selects
[live grounded Haiku chat](live_chat.md). The source-only path remains available
for explicit offline research and regression tests. Its recorded scores do not
measure the live generated-answer surface.

## Curated direct answers (implementation specification)

The supported general topics now receive a short authored answer above their exact
source passages: claims, waiting periods, membership cards, the MBS, gap payments,
direct billing, prescription medicines and exclusions. These are fixed editorial
cards, not model-written responses. Every sentence has a physical PDF page/column
and an exact source-text anchor. Before returning a card, the service verifies all
anchors in the hash-verified corpus and validates every displayed source excerpt.
A missing or changed anchor fails closed; no card is returned. The UI also hides
the authored answer when the saved source changes during transcript replay.

`ChatResponse` adds optional `answer`, `answer_title`, `answer_id`, and
`answer_source_ids`. Existing callers can continue using `status`, `message`, and
`hits`. Emergency-first screening, privacy/instruction checks, bounded inputs,
offline-only operation and no implicit conversation context remain required.
Administrative wording and courtesy forms can vary, but personalised medical or
benefit decisions cannot select a card. Unknown supported-language questions may
still return passages without an authored answer; uncertain or mixed requests
abstain. This finite set is not an open-domain assistant or a measured clinical
classifier. Development checks do not establish held-out safety performance.

The student can submit their own general OSHC question and continue asking questions
in a session-only transcript. Each submitted message, including starter questions,
runs through the same service before any source loading or search. A refusal has no
retrieval follow-up, including inside collapsed UI panels.

The service returns fixed boundary/clarification messages or exact passages from the
hash-verified Member Guide. It never calls a language model or the unfinished composer.
Passages remain source excerpts, not a determination of personal cover. Unsupported
questions abstain. Follow-ups must name their topic; previous personal circumstances
are never implicitly combined into an answer.

The transcript is bounded to the latest 10 turns in Streamlit session memory, with a
Clear chat control. It is not logged, exported, cached or sent to a provider. Personal
details detected by the privacy gate are replaced in the transcript. Source changes
suppress saved excerpts until the source is restored. Emergency messages are processed
even when the guide is absent.

This supplements the unchanged baseline gazetteer with a conservative chat scope
boundary. Regression tests are development checks, not held-out refusal recall. The
baseline clinical review and the 0.90 held-out release threshold still apply to a future
generated answer surface.

`answer_question(question, *, root=ROOT, source_loader=None)` returns the immutable
`ChatResponse` without changing the frozen `GuardrailDecision` or `RetrievalHit`
schemas. Its fields are `status`, `decision`, fixed `message`, tuple `hits`,
`source_sha256`, and `safe_to_echo`. The last flag is true only for accepted
questions and empty search results. All rejected questions are withheld from the
transcript. The public decision removes analysis-only trigger/confidence fields,
because a matched input span can itself contain personal information.

Unicode normalisation and the unchanged emergency-first boundary check precede all
source access. The extra scope gate uses a narrow educational vocabulary and
administrative first-person forms. Unknown words, mixed requests and ambiguous
followups deliberately abstain; these restrictions are not a measured clinical
classifier. Explicit offline configuration is required. Input is never truncated
before checking, so an unsafe tail cannot be silently removed.

The final chat adds deterministic immediate-danger descriptions and normalises
typographic apostrophes before emergency screening. Polite informational requests
do not bypass the clinical-care check. Administrative exceptions are anchored
forms, and unknown vocabulary still abstains. Final separate automated probes
recorded 24/24 required refusals, 6/6 emergencies and 6/20 false refusals. See the
15 October release record for earlier failed candidates and uncertainty intervals.

The default loader calls `build_corpus(root)`, which verifies the frozen guide hash.
The injectable `source_loader` is trusted application/test code and must fulfill
the same verified corpus contract. UI uses `load_source(ROOT)[0]`, which also checks
the preview bytes. After local BM25 retrieval, every hit must match a loaded chunk's
exact text, identity, document, publisher URL, page/column and capture date. An
invalid hit rejects the entire result; a missing source or empty search returns
fixed abstention wording with no excerpts. A pinned source hash accompanies only
validated excerpts. No composer, rubric provider or conversation-context shortcut
is available on this path.
