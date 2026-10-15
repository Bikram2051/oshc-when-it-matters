# Journey Coach: authored lesson baseline

Journey Coach works while Ask NextBest uses live Haiku mode
(`OSHC_OFFLINE=0`, `OSHC_ENABLE_LIVE=1`). It also works in source-only mode.
The coach does not need an API key and does not call the model: lessons remain
fixed, source-checked learning activities rather than generated clinical advice.

Three fixed English lessons cover finding cover documents, understanding an MBS
reference fee, and checking direct billing costs. A student selects a moment; this
is explicit navigation, not inferred personalisation. The lesson selection is
editorial. `oshc/coach.py` and its corpus-keyness contract are unchanged.

The moment selector opens Learn, Practise and Take action tabs. Each moment has a
fictional scenario and three fixed next-step checks. Students can save a checklist,
download a reminder and move between moments. These controls do not collect names,
health histories or policy identifiers. Reset clears practice and checklist state.
The journey plan shows the saved preparation ticks and practice status for each
moment. Continue my next unfinished moment opens the first moment whose scenario
has not yet been checked correctly or whose checklist has not been fully saved.
Completion requires both; it does not confirm clinical readiness or cover.

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
That historical rehearsal script deliberately retains its source-only settings.
For the current coach, `python -m pytest tests/test_coach_ui.py -q` exercises both
runtime modes with provider access trapped, including the complete journey,
resuming an unfinished moment, saved checklist restoration and reset.
This checkpoint does not complete adaptive learning, corpus-driven lesson
selection, general service-navigation content or evaluation with held-out data.
