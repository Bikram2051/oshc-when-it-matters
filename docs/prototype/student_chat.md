# Guarded guide chat

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

The default loader calls `build_corpus(root)`, which verifies the frozen guide hash.
The injectable `source_loader` is trusted application/test code and must fulfill
the same verified corpus contract. UI uses `load_source(ROOT)[0]`, which also checks
the preview bytes. After local BM25 retrieval, every hit must match a loaded chunk's
exact text, identity, document, publisher URL, page/column and capture date. An
invalid hit rejects the entire result; a missing source or empty search returns
fixed abstention wording with no excerpts. A pinned source hash accompanies only
validated excerpts. No composer, rubric provider or conversation-context shortcut
is available on this path.
