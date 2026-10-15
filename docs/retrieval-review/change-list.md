# Retrieval freeze and pre-audit change list

Date recorded: 2026-10-15  
Branch: `aayush/50questions/main`

## Freeze scope

- The current candidate gold set is `data/gold/retrieval.json` (50 query IDs).
- An independent blind review packet is in `docs/retrieval-review/blind_review_queries.json` with instructions in `docs/retrieval-review/REVIEW_INSTRUCTIONS.md`.
- Do not edit `oshc/retrieval.py`, `oshc/chunker.py`, or `data/gold/retrieval.json` while independent labels are pending.
- Do not run the Recall@5 evaluator until the independent annotations are returned and recorded separately.
- Preserve the pre-audit file as a separate immutable artifact; do not replace it with the current candidate gold set.

## Pre-audit snapshot location

The pre-audit copy was recorded locally at `D:\retrieval_handoff\retrieval_original.json`, associated with commit `94ced50`. This file is not currently present in this branch.

Before declaring the snapshot fully archived, verify its existence and record its SHA-256 with:

```powershell
Get-Item D:\retrieval_handoff\retrieval_original.json
Get-FileHash D:\retrieval_handoff\retrieval_original.json -Algorithm SHA256
```

Keep the original bytes unchanged. If the file is later added to the repository, add it under a distinct name such as `data/gold/retrieval_pre_audit.json` and verify its hash matches the local copy.

### Verification record (2026-10-15)

The local pre-audit file was verified against the Git blob `94ced50:data/gold/retrieval.json`.

Both files have a size of 8,359 bytes and the same SHA-256 hash:

`EFC3332D5631047A9C6B7732559A1AEF06ECBAC6EA4A9DC215D5A9AAE7DB8E60`

The original local file at `D:\retrieval_handoff\retrieval_original.json` remains unchanged. The Git blob was extracted byte-for-byte to a separate temporary comparison file on the D: drive.

This verifies that the local snapshot matches the historical Git version. **The snapshot has not yet been archived in the repository.**

## Change-list record

1. The candidate set contains 50 queries: IDs 1–25 target the Medibank OSHC Member Guide; IDs 26–50 are MBS XML item/service lookups.
2. These are two different evaluation tasks. The MBS XML lookups belong to Bill Explainer item matching, not Member Guide document retrieval. One Recall@5 across all 50 mixes task types and must not be presented as a single retrieval-quality result.
3. Report Member Guide retrieval separately using an independently reviewed guide-only gold subset and a clearly stated retrieval metric.
4. Evaluate MBS item lookups separately using a Bill Explainer/MBS matcher evaluation appropriate to item identification; do not score those queries as hybrid document retrieval.
5. Existing candidate labels and diagnostic scores are not independent ground truth. The blind reviewer must annotate from query text and frozen source chunks without inspecting the current labels, rankings, or prior diagnostic results.
6. Record any subsequent gold-label changes in a new dated entry; retain the pre-audit artifact and explain each change. Do not tune retrieval code to the independent review labels.

## Current status

- [x] Blind review query packet committed.
- [x] Review instructions committed.
- [x] Task-mix limitation recorded.
- [x] Pre-audit snapshot hash verified and recorded.
- [ ] Independent annotations received as a separate file.
- [ ] Final task-specific gold subsets and evaluation protocol frozen.
- [ ] Evaluation rerun only after the independent review is complete.