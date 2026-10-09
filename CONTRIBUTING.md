# Contributing

Three people, six weeks, 8 to 10 hours each per week. This document is how that arithmetic works. It is short on purpose.

---

## Branch and merge

- `main` is always green. Never push to it directly.
- Branch as `<initials>/<area>`, e.g. `bb/mbs-matcher`, `ak/guardrail-rubric`, `mr/invoice-generator`.
- One pull request per area, reviewed by the named reviewer in the README ownership table, merged by the reviewer, not the author.
- CI must pass. A red build is fixed before anything else is started.

---

## Development discipline

These rules keep the work checkable. They apply to every contributor and every tool.

**1. Write the spec first, in the repository.** Every module begins as a pydantic type in `oshc/schemas.py` plus a docstring stating inputs, outputs, and the one thing the function must never do. If you cannot write that docstring, you do not yet understand the task.

**2. Tests before code for anything deterministic.** Benefit arithmetic, the guardrail gazetteer, the MBS matcher: write the pytest cases first, then write the code that makes them pass. This catches code that looks right and is not. `tests/test_arithmetic.py` and `tests/test_guardrail.py` are the worked examples.

**3. Every diff is reviewed line by line.** The named reviewer reads it before merge. Reading a diff costs a tenth of writing one and catches the most common error: silently handling the case the code was meant to refuse.

**4. Held-out material stays with its custodian.** Not the frozen layout parameters, not the held-out probe set. Do not paste them into any tool or chat. The separation is worthless the moment it leaks.

**5. Never paste a real document into any tool.** Synthetic only.

**6. Name the source of every number.** Before anything goes in a slide, report or the tracker, it must name the number and the file that produced it. A number without a file is not a result.

---

## Evaluation separation

Read the README section of the same name before you touch `scripts/make_invoices.py`, `oshc/guardrail.py` or anything under `eval/`. The short version:

- Bikram never reads or reviews the invoice generator.
- Aayush never sees the held-out guardrail probes.
- Held-out material lives in `data/heldout/`, gitignored, released on evaluation day.

If you think you have accidentally seen held-out material, say so in the group chat the same day. It is recoverable if declared and not if discovered later.

---

## Changing a frozen interface

`oshc/schemas.py` is frozen. Changing a field there breaks someone else's branch. Process: raise it in the group chat, agree it in a meeting, record it in the minutes with the date, then change it in one pull request that updates every caller. Not in a comment thread.

---

## Definition of done

A task is done when all five are true:

1. Tests pass locally and in CI.
2. The named reviewer has approved and merged.
3. It runs from a clean clone through `setup.ps1` or `setup.sh`.
4. If it produces a number, the number is written into `eval/` output, not into a chat message.
5. It is logged in the contribution tracker the same day with the artefact filename.

---

## Weekly rhythm

- **Monday:** meeting, gate from last week confirmed or declared missed, week's tasks confirmed.
- **Wednesday:** mid-week check in the group chat. Anyone blocked says so on Wednesday, not on Sunday.
- **Friday:** merge deadline for the week's gate. Tracker updated by each member with their own artefacts.

A missed gate is declared, not absorbed. Absorbing it is what turns one bad week into three.
