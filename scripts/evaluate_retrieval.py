"""Evaluate hybrid retrieval against the frozen 50-pair gold set.

Owner: Aayush Khade.
Metrics:
- Recall@5: fraction of gold queries with at least one relevant chunk in top 5.
- MRR: mean reciprocal rank of the first relevant chunk.
"""

from __future__ import annotations

import json
from pathlib import Path

from oshc.retrieval import search

ROOT = Path(__file__).resolve().parents[1]
GOLD_FILE = ROOT / "data" / "gold" / "retrieval.json"


def load_gold() -> list[dict]:
    with GOLD_FILE.open(encoding="utf-8") as file:
        return json.load(file)


def evaluate() -> tuple[float, float]:
    gold = load_gold()

    if not gold:
        raise RuntimeError("Gold set is empty.")

    recall_hits = 0
    reciprocal_ranks: list[float] = []

    for entry in gold:
        query = entry["query"]
        relevant_ids = set(entry["relevant_chunk_ids"])

        hits = search(query, k=5)
        retrieved_ids = [hit.chunk_id for hit in hits]

        first_relevant_rank = None

        for rank, chunk_id in enumerate(retrieved_ids, start=1):
            if chunk_id in relevant_ids:
                first_relevant_rank = rank
                break

        if first_relevant_rank is not None:
            recall_hits += 1
            reciprocal_ranks.append(1.0 / first_relevant_rank)
        else:
            reciprocal_ranks.append(0.0)

    recall_at_5 = recall_hits / len(gold)
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)

    return recall_at_5, mrr


def main() -> None:
    recall_at_5, mrr = evaluate()

    print(f"Gold queries: {len(load_gold())}")
    print(f"Recall@5: {recall_at_5:.4f}")
    print(f"MRR: {mrr:.4f}")


if __name__ == "__main__":
    main()