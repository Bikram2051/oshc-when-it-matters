"""Score a frozen source-only annotation set against the deployed guide browser.

Rankings and the mechanical source-locator map are saved before reading relevance
fields. This script does not run the separate research hybrid retriever.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval.extraction import wilson
from oshc.policy_search import PolicySearch
from oshc.policy_source import SOURCE_SHA256, build_corpus

LABEL_SHA256 = "a97a5105fd99a3d7f0a1c9c21e0e5a254fbfe0d8f03f5f9129b1e024349f24b1"
GUIDE_LOCATOR = re.compile(r"guide:p(\d{3}):(left|right)\Z")
MBS_LOCATOR = re.compile(r"mbs:\d+\Z")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=True, indent=2)
        handle.write("\n")


def rate(k: int, n: int) -> dict:
    return {"k": k, "n": n, "rate": k / n if n else None,
            "ci95": list(wilson(k, n)) if n else None}


def metrics(ranks: list[int | None]) -> dict:
    return {"hit_at_1": rate(sum(rank == 1 for rank in ranks), len(ranks)),
            "hit_at_5": rate(sum(rank is not None for rank in ranks), len(ranks)),
            "mrr_at_5": sum(1 / rank if rank else 0 for rank in ranks) / len(ranks)
            if ranks else None}


def evaluate(labels_path: Path, freeze_path: Path, run_dir: Path, report_path: Path) -> dict:
    if report_path.exists() or run_dir.exists():
        raise ValueError("Use new paths: first predictions and scores are never overwritten")
    if digest(labels_path) != LABEL_SHA256:
        raise ValueError("Independent labels differ from their recorded freeze")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    frozen_rows = [row for row in freeze["frozen_outputs"]
                   if Path(row["path"]).name == "labels.json"]
    if len(frozen_rows) != 1 or frozen_rows[0]["sha256"] != LABEL_SHA256:
        raise ValueError("The assessor freeze does not bind the specified labels")
    # Relevance fields are deliberately not consulted until after rankings persist.
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    queries = [(row["id"], row["query"]) for row in labels]
    if len(queries) != 50 or len({ident for ident, _ in queries}) != 50:
        raise ValueError("Expected all 50 unique original query IDs")
    implementation = ["oshc/policy_search.py", "oshc/policy_source.py", "oshc/schemas.py",
                      "scripts/evaluate_independent_retrieval.py",
                      "docs/prototype/independent_retrieval_protocol.md"]
    snapshot = {name: digest(ROOT / name) for name in implementation}
    corpus = build_corpus(ROOT)
    search = PolicySearch(corpus)
    locator_by_chunk = {chunk.chunk_id: f"guide:p{chunk.page:03d}:{chunk.column}"
                        for chunk in corpus.chunks}
    if len(set(locator_by_chunk.values())) != len(corpus.chunks):
        raise ValueError("Source-column mapping must be one to one")
    run_dir.mkdir(parents=True, exist_ok=False)
    map_path = run_dir / "locator_map.json"
    write_new(map_path, {"source_sha256": SOURCE_SHA256,
                         "method": "Exact physical page and column metadata; no semantic remapping.",
                         "chunk_to_source_locator": locator_by_chunk})
    predictions = []
    for ident, query in queries:
        try:
            hits = search.search(query, k=5)
            predictions.append({"id": ident, "error": False,
                                "hits": [{"chunk_id": hit.chunk_id,
                                          "locator": locator_by_chunk[hit.chunk_id],
                                          "rank": hit.rank} for hit in hits]})
        except Exception:
            # Every query, including errors, remains in its declared denominator.
            predictions.append({"id": ident, "error": True, "hits": []})
    prediction_path = run_dir / "predictions.json"
    write_new(prediction_path, {"created_at_utc": datetime.now(timezone.utc).isoformat(),
                                "label_sha256": LABEL_SHA256,
                                "implementation_sha256": snapshot,
                                "locator_map_sha256": digest(map_path),
                                "predictions": predictions})

    # Scoring starts only after the first outputs and source mapping are on disk.
    by_id = {row["id"]: row for row in predictions}
    scored, guide_ranks, page_ranks, unmapped = [], [], [], set()
    ambiguity_counts = Counter()
    supported = []
    unsupported = []
    for row in labels:
        relevant = set(row["relevant_chunk_ids"])
        guide = {loc for loc in relevant if GUIDE_LOCATOR.fullmatch(loc)}
        mbs = {loc for loc in relevant if MBS_LOCATOR.fullmatch(loc)}
        if not relevant or guide | mbs != relevant or bool(guide) == bool(mbs):
            raise ValueError("Every annotation must identify one supported source family")
        family = "guide" if guide else "mbs"
        ambiguity_counts[family] += bool(row["ambiguity_flags"])
        hits = by_id[row["id"]]["hits"]
        exact_rank = next((hit["rank"] for hit in hits if hit["locator"] in relevant), None)
        pages = {GUIDE_LOCATOR.fullmatch(loc).group(1) for loc in guide}
        page_rank = next((hit["rank"] for hit in hits
                          if GUIDE_LOCATOR.fullmatch(hit["locator"]).group(1) in pages), None)
        if guide:
            supported.append(row["id"])
            guide_ranks.append(exact_rank)
            page_ranks.append(page_rank)
            unmapped.update(guide - set(locator_by_chunk.values()))
        else:
            unsupported.append(row["id"])
        scored.append({"id": row["id"], "source_family": family,
                       "exact_column_rank_at_5": exact_rank,
                       "page_rank_at_5": page_rank,
                       "error": by_id[row["id"]]["error"],
                       "ambiguous": bool(row["ambiguity_flags"])})
    normalized = Counter(" ".join(unicodedata.normalize("NFKC", query).casefold().split())
                         for _, query in queries)
    duplicate_groups = [count for count in normalized.values() if count > 1]
    result = {
        "kind": "Frozen automated source-only independent labels; deployed guide-column BM25",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "label_provenance": "One automated assessor, independent of implementation and rankings; not human consensus.",
        "queries_unseen_by_implementation_developers": False,
        "labels_frozen_before_first_scoring": True,
        "label_sha256": LABEL_SHA256, "assessor_freeze_sha256": digest(freeze_path),
        "source_sha256": SOURCE_SHA256, "implementation_sha256": snapshot,
        "first_predictions_sha256": digest(prediction_path),
        "locator_map_sha256": digest(map_path),
        "k": 5, "total_queries": len(queries), "exceptions": sum(row["error"] for row in predictions),
        "guide_queries": len(supported), "mbs_queries_outside_guide_pipeline": len(unsupported),
        "guide_exact_column": metrics(guide_ranks),
        "guide_page_relaxation_secondary": metrics(page_ranks),
        "all_50_exact_column_unsupported_as_misses": metrics(
            [row["exact_column_rank_at_5"] for row in scored]),
        "ambiguity": {"guide_queries": ambiguity_counts["guide"],
                      "mbs_queries": ambiguity_counts["mbs"],
                      "total_queries": sum(ambiguity_counts.values())},
        "duplicates": {"exact_query_groups": len(duplicate_groups),
                       "queries_in_exact_duplicate_groups": sum(duplicate_groups),
                       "distinct_query_texts": len(normalized),
                       "assessor_near_duplicate_groups": len(freeze["near_duplicate_groups"]),
                       "assessor_overlapping_groups": len(freeze["overlapping_groups"])},
        "relevant_source_locators_omitted_from_deployed_index": sorted(unmapped),
        "research_hybrid": {"status": "not_run", "model": "BAAI/bge-small-en-v1.5",
                            "reason": "Dense model was not provisioned locally. No model download or provider call was authorised for this evaluation."},
        "research_full_corpus_bm25": {"status": "not_run",
                                       "reason": "Raw XML item locators are not uniquely bound to the flattened implementation chunks by this scoring protocol."},
        "provider_calls": 0, "model_downloads": 0, "tuning_performed": False,
        "outcomes": scored,
        "limitations": [
            "Queries were previously known; only relevance annotation was independent of implementation and rankings.",
            "One automated assessor is not a blinded human panel or an inter-rater reliability study.",
            "Any labelled answer-bearing column counts as a hit; this does not establish complete answers or semantic correctness.",
            "Ambiguous and duplicate queries remain in the main denominators; annotations were not changed after scoring.",
            "The deployed index deliberately omits tables and some non-body pages; unmapped relevant locators remain misses unless another labelled locator is retrieved.",
            "Wilson intervals describe this selected query set, not a representative population; duplicate queries can be correlated.",
            "The deployed browser searches only the guide. MBS queries are retained as unsupported misses in the all-50 result.",
            "The research hybrid retriever and synthetic-to-public degradation were not evaluated by this run."
        ]}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_new(report_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.labels, args.freeze, args.run_dir, args.report)
    print(json.dumps({key: result[key] for key in (
        "guide_exact_column", "guide_page_relaxation_secondary",
        "all_50_exact_column_unsupported_as_misses", "ambiguity", "duplicates")}, indent=2))


if __name__ == "__main__":
    main()
