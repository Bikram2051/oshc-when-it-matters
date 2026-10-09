"""Verify the actual frozen guide and development searches without provider access."""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from oshc.llm_budget import Budget  # noqa: E402
from oshc.policy_source import (  # noqa: E402
    CAPTURED_ON, EFFECTIVE_MONTH, OMITTED_PAGES, PROFILE, SOURCE_DOC, SOURCE_SHA256,
    build_corpus, index_bytes, save_index,
)
from oshc.policy_search import PolicySearch  # noqa: E402


def fingerprints():
    names = ["oshc/schemas.py", "oshc/arithmetic.py", "oshc/billexplainer/mbs.py",
             "seminar/demo_guardrail.py", "data/mbs/mbs.sqlite",
             "corpus/MBS-XML-20260801.XML", "corpus/MANIFEST.csv", f"corpus/{SOURCE_DOC}"]
    paths = [ROOT / name for name in names]
    paths.extend((ROOT / "cache/llm/v2").glob("*.json"))
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths if p.is_file()}


def main():
    if os.getenv("OSHC_OFFLINE") != "1" or os.getenv("OSHC_ENABLE_LIVE") != "0":
        raise SystemExit("Run with OSHC_OFFLINE=1 and OSHC_ENABLE_LIVE=0.")
    output = ROOT / "docs/prototype/policy_source_check.json"
    if output.exists():
        raise SystemExit("The source-check report already exists. Keep it for review.")
    budget = Budget()
    before_budget, before_files = budget.status(), fingerprints()
    with patch("oshc.llm._client", side_effect=AssertionError("Unexpected provider access")):
        source = build_corpus(ROOT)
        if index_bytes(source) != index_bytes(build_corpus(ROOT)):
            raise AssertionError("Source index was not repeatable.")
        columns = {(chunk.page, chunk.column): chunk.text for chunk in source.chunks}
        assert len(columns) == len(source.chunks) == 61
        assert "85%" not in columns[17, "left"]
        assert "100%" in columns[17, "left"] and "85%" in columns[17, "right"]
        assert columns[28, "left"].startswith("Benefit exclusions.")
        assert columns[28, "right"].startswith("Making a claim.")
        assert "Making a claim." not in columns[28, "left"]
        assert "Optical items" not in columns[28, "right"]
        assert not any(page == 19 for page, _ in columns)
        print("Source integrity and page-column checks: PASS")
        index = PolicySearch(source)
        cases = [("Medicare Benefits Schedule", {17}), ("making a claim", {28, 29}),
                 ("waiting periods", {21}), ("membership card", {8}),
                 ("direct billing", {28}), ("ambulance services", {25})]
        checks = []
        for query, expected_pages in cases:
            hits = index.search(query, k=5)
            pages = [int(hit.source_url.rsplit("=", 1)[1]) for hit in hits]
            assert expected_pages.intersection(pages), f"Search smoke check failed: {query}"
            assert all(hit.text == columns[pages[i], hit.section.split(", ")[1].split()[0]]
                       for i, hit in enumerate(hits))
            checks.append({"query": query, "expected_any_page": sorted(expected_pages),
                           "returned_pages": pages, "passed": True})
            print(f"{query}: PASS; top-five PDF pages {pages}")
        assert index.search("zzxxqqvv") == []
        checksum = save_index(source, ROOT / "corpus/index/medibank_policy_v1.json")
    if before_budget != budget.status() or before_files != fingerprints():
        raise AssertionError("A protected file or the spending ledger changed.")
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Engineering checks using known source topics; not held-out Recall@5.",
        "source_sha256": SOURCE_SHA256, "captured_on": CAPTURED_ON,
        "effective_month": EFFECTIVE_MONTH, "physical_pages": 37,
        "profile": PROFILE, "pymupdf_version": source.parser_version,
        "index_sha256": checksum, "chunk_count": len(source.chunks),
        "indexed_pages": sorted({chunk.page for chunk in source.chunks}),
        "omitted_pages": dict(OMITTED_PAGES), "search_method": "BM25Okapi baseline",
        "search_smoke_checks": checks, "protected_files_unchanged": True,
        "budget_unchanged": True, "additional_api_calls": 0,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print("Chunks:", len(source.chunks), "| Indexed pages:", len(report["indexed_pages"]))
    print("Omitted physical pages:", [page for page, _ in OMITTED_PAGES])
    print("Index SHA-256:", checksum)
    print("Additional API calls: 0; protected files and budget unchanged.")
    print("Budget:", json.dumps(budget.status(), indent=2))
    print("Wrote:", output)


if __name__ == "__main__":
    main()
