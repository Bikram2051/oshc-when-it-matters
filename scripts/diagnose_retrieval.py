import json

from oshc.retrieval import search

GOLD_FILE = "data/gold/retrieval.json"

with open(GOLD_FILE, encoding="utf-8") as file:
    data = json.load(file)

print("--- FAILED QUERIES ---")

failed = 0

for entry in data:
    relevant = set(entry["relevant_chunk_ids"])
    hits = search(entry["query"], k=5)
    retrieved = [hit.chunk_id for hit in hits]

    if not any(chunk_id in relevant for chunk_id in retrieved):
        failed += 1
        print(f"{entry['id']}. {entry['query']}")
        print(f"   Relevant:  {entry['relevant_chunk_ids']}")
        print(f"   Retrieved: {retrieved}")
        print()

print(f"Failed queries: {failed}")
print(f"Passed queries: {len(data) - failed}")