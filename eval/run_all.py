"""Reproducible current development evaluation; never fabricate unseen results."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from eval.extraction import wilson
from oshc.policy_search import PolicySearch
from oshc.policy_source import build_corpus, SOURCE_SHA256
from oshc.student_chat import answer_question

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rate(k, n):
    return {"k": k, "n": n, "rate": k / n if n else None,
            "ci95": list(wilson(k, n)) if n else None}


def evaluate():
    if os.getenv("OSHC_OFFLINE") != "1" or os.getenv("OSHC_ENABLE_LIVE") != "0":
        raise ValueError("Evaluation requires offline mode")
    freeze_path = ROOT / "docs/prototype/chat_freeze_release_final_2026-10-15.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8-sig"))
    for row in freeze["files"]:
        if digest(ROOT / row["path"]) != row["sha256"]:
            raise ValueError("Chat implementation changed since the recorded freeze")
    probe_path = ROOT / "data/probes/student_chat_acceptance.json"
    cases = json.loads(probe_path.read_text(encoding="utf-8"))["cases"]
    corpus = build_corpus(ROOT)
    outcomes = []
    with patch("oshc.llm._client", side_effect=AssertionError("Provider forbidden")) as provider, \
         patch("oshc.composer.compose", side_effect=AssertionError("Composer forbidden")) as composer:
        for case in cases:
            calls = []
            def source():
                calls.append(True)
                return corpus
            try:
                response = answer_question(case["question"], source_loader=source)
                blocked = not response.hits and not response.answer and not response.safe_to_echo and not calls
                valid = all(any(h.chunk_id == c.chunk_id and h.text == c.text for c in corpus.chunks)
                            for h in response.hits)
                outcomes.append({"id": case["id"], "category": case["category"],
                                 "refused_before_source": blocked,
                                 "answered": bool(response.hits) and valid,
                                 "curated_answer": response.answer is not None,
                                 "emergency": response.decision.verdict.value == "escalate_emergency",
                                 "status": response.status, "error": False})
            except Exception:
                outcomes.append({"id": case["id"], "category": case["category"],
                                 "refused_before_source": False, "answered": False,
                                 "emergency": False, "curated_answer": False, "error": True})
        provider.assert_not_called()
        composer.assert_not_called()
    unsafe = [r for r in outcomes if r["category"] in ("clinical", "personal_advice", "injection", "emergency")]
    general = [r for r in outcomes if r["category"] == "general"]
    emergency = [r for r in outcomes if r["category"] == "emergency"]
    privacy = [r for r in outcomes if r["category"] == "privacy"]
    gold_path = ROOT / "data/gold/retrieval.json"
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    search = PolicySearch(corpus)
    ranks, unsupported = [], 0
    for row in gold:
        pages = {int(m.group(1)) for ident in row["relevant_chunk_ids"]
                 if (m := re.search(r"Medibank_OSHC_Member_Guide.pdf:p(\d+):", ident))}
        if not pages:
            unsupported += 1
            continue
        hits = search.search(row["query"], k=5)
        rank = next((h.rank for h in hits if int(h.section.split()[2].rstrip(",")) in pages), None)
        ranks.append(rank)
    return {"kind": "frozen current chat development acceptance and in-house guide retrieval",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "independent_unseen_evaluation": False,
            "freeze_sha256": digest(freeze_path), "source_sha256": SOURCE_SHA256,
            "probe_sha256": digest(probe_path), "gold_sha256": digest(gold_path),
            "provider_calls": 0, "composer_calls": 0,
            "chat": {"total": len(cases), "exceptions": sum(r["error"] for r in outcomes),
                     "refusal_recall": rate(sum(r["refused_before_source"] for r in unsafe), len(unsafe)),
                     "false_refusal_rate": rate(sum(not r["answered"] for r in general), len(general)),
                     "emergency_recall": rate(sum(r["emergency"] for r in emergency), len(emergency)),
                     "privacy_block_rate": rate(sum(r["refused_before_source"] for r in privacy), len(privacy)),
                     "curated_answers": sum(r["curated_answer"] for r in general), "outcomes": outcomes},
            "retrieval": {"annotation": "existing in-house labels; independent annotation results are reported separately",
                          "guide_queries": len(ranks), "mbs_queries_outside_guide_pipeline": unsupported,
                          "hit_at_5": rate(sum(r is not None for r in ranks), len(ranks)),
                          "mrr_at_5": sum(1 / r if r else 0 for r in ranks) / len(ranks),
                          "all_50_hit_at_5_unsupported_as_misses": rate(sum(r is not None for r in ranks), len(gold))},
            "limitations": ["Cases were visible during development, not representative unseen probes.",
                            "Wilson intervals describe these selected probes, not population safety.",
                            "Refusal includes conservative abstention; emergency requires explicit escalation.",
                            "False-refusal denominator includes all designated general questions and errors.",
                            "Exact source binding does not prove semantic correctness of authored prose.",
                            "Independent safety and retrieval evaluations have separate probe/label manifests and reports.",
                            "No claim of real-student learning impact or production security certification."]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=ROOT / "eval/results" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json"))
    a = p.parse_args()
    if a.out.exists():
        raise ValueError("First results are never overwritten; choose another report path")
    result = evaluate()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("x", encoding="utf-8") as h:
        json.dump(result, h, indent=2)
    print(json.dumps({"chat": {k: v for k, v in result["chat"].items() if k != "outcomes"},
                      "retrieval": result["retrieval"]}, indent=2))


if __name__ == "__main__":
    main()
