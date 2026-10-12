# Journey Coach: authored lesson baseline

Three fixed English lessons cover finding cover documents, understanding an MBS
reference fee, and checking direct billing costs. A student selects a moment; this
is explicit navigation, not inferred personalisation. The lesson selection is
editorial. `oshc/coach.py` and its corpus-keyness contract are unchanged.

Each lesson cites a column of the verified May 2026 Medibank guide. On every
rerun, the source loader checks the manifest and PDF, then checks that supporting
spans occur in the cited column. Span presence is a provenance check, not an
automatic proof of entailment. Lesson wording was reviewed against those columns.

Practice starts with no selected answer. Feedback follows an explicit check.
Retries preserve the first answer, last answer, attempt count and whether the
question has been correct at least once. These values remain in Streamlit session
state only. Start again clears them. No learner dataset, event log or API call is
created. Practice progress does not measure learning effectiveness.

The source button opens the cited physical page in Navigator through a one-time
session request. Navigator accepts only integer pages 1 through 37 and rechecks
the source before showing a page. Home now describes implemented features and
removes the inactive Hindi selector. Translation remains unimplemented.

Rehearse with `python scripts/prototype_check_coach_ui.py`. The report contains
engineering checks using authored lessons, not independent learner results.
This checkpoint does not complete adaptive learning, corpus-driven lesson
selection, general service-navigation content or evaluation with held-out data.
