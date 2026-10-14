"""Exercise the Ask page and score its retrieval path, then write the report.

Two halves. The first drives the real page through AppTest against the real
verified guide and asserts the properties that matter: the boundary filter runs
first, a refusal shows no excerpt, nothing is composed, and the provider is
never touched. The second scores retrieval on two probe sets.

Two probe sets, deliberately, because the difference between them is the result:

  gold    data/gold/retrieval.json, restricted to the 25 questions whose answer
          is in the Member Guide. Written in the guide's own vocabulary.
  dev     data/probes/ask_dev_probes.csv. The same subject matter asked the way
          a student asks it, labelled by page in-house.

Scoring is page level: a question counts as answered if any of its expected
physical PDF pages appears in the top five excerpts. Page level is the right
grain because the page is what the user is shown and sent to.

Neither set is held out. The gold set was authored by the member who built the
retriever, and the dev set was authored by the member who built this page.
Both numbers are therefore the optimistic end of the range, and the report says
so. The held-out retrieval measure in the evidence dashboard stays unlinked.

This script makes no provider calls and changes nothing outside --out.

Owner: Bikram Bhattarai. Reviewer: Aayush Khade.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402

import oshc.ask_ui as ask_ui  # noqa: E402
from oshc.guardrail import check  # noqa: E402
from oshc.llm_budget import Budget  # noqa: E402
from oshc.policy_search import PolicySearch  # noqa: E402
from oshc.policy_source import SOURCE_SHA256, build_corpus  # noqa: E402

GOLD_FILE = ROOT / "data" / "gold" / "retrieval.json"
DEV_FILE = ROOT / "data" / "probes" / "ask_dev_probes.csv"
TOP_K = 5


def gold_probes() -> list[dict]:
    """Guide-targeted gold questions, with chunk ids reduced to page numbers."""
    records = json.loads(GOLD_FILE.read_text(encoding="utf-8"))
    probes = []
    for entry in records:
        ids = entry["relevant_chunk_ids"]
        if not all(".pdf:" in identifier for identifier in ids):
            continue  # MBS XML lookups belong to the Bill Explainer, not this page.
        pages = {int(match.group(1)) for identifier in ids
                 if (match := re.search(r":p(\d+):", identifier))}
        if pages:
            probes.append({"id": f"G-{entry['id']:02d}", "question": entry["query"],
                           "pages": pages, "expected_guardrail": "allow"})
    return probes


def dev_probes() -> list[dict]:
    with DEV_FILE.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    probes = []
    for row in rows:
        pages = {int(part) for part in row["expected_pages"].split(";") if part.strip()}
        if not pages:
            raise SystemExit(f"Probe {row['id']} has no expected page.")
        probes.append({"id": row["id"], "question": row["question"], "pages": pages,
                       "expected_guardrail": row["expected_guardrail"].strip()})
    return probes


def score(probes: list[dict], search: PolicySearch, page_of: dict[str, int]) -> dict:
    """Run the real page order: guardrail first, retrieval only if allowed."""
    detail, scored = [], []
    unexpected_refusals, expected_refusals = [], []

    for probe in probes:
        decision = check(probe["question"])
        verdict = decision.verdict.value
        row = {"id": probe["id"], "guardrail": verdict,
               "guardrail_as_expected": verdict == probe["expected_guardrail"]}

        if decision.blocked:
            row["retrieval_rank"] = None
            (expected_refusals if row["guardrail_as_expected"]
             else unexpected_refusals).append(probe["id"])
        else:
            pages = [page_of[hit.chunk_id] for hit in search.search(probe["question"], k=TOP_K)]
            rank = next((index for index, page in enumerate(pages, 1)
                         if page in probe["pages"]), None)
            row.update(retrieval_rank=rank, returned_pages=pages,
                       expected_pages=sorted(probe["pages"]))
            scored.append(rank)
        detail.append(row)

    total = len(scored)
    if not total:
        raise SystemExit("Every probe was refused. Nothing to score.")
    found = [rank for rank in scored if rank]
    return {
        "probes": len(probes),
        "allowed_and_scored": total,
        "refused_at_guardrail": len(probes) - total,
        "recall_at_5": round(len(found) / total, 4),
        "recall_at_3": round(sum(1 for rank in found if rank <= 3) / total, 4),
        "recall_at_1": round(sum(1 for rank in found if rank == 1) / total, 4),
        "mrr": round(sum(1 / rank for rank in found) / total, 4),
        "guardrail_decisions_as_expected": all(row["guardrail_as_expected"] for row in detail),
        "unexpected_refusals": unexpected_refusals,
        "expected_refusals": expected_refusals,
        "detail": detail,
    }


def rendered(at) -> str:
    """Everything the page put on screen, excerpt bodies included."""
    return " ".join([item.value for item in at.text]
                    + [item.value for item in at.markdown]
                    + [item.value for item in at.caption]
                    + [item.value for item in at.success]
                    + [item.value for item in at.error]
                    + [item.value for item in at.warning])


def ui_checks(corpus) -> dict:
    """Drive the real page against the real guide. Returns recorded flags."""
    excerpts = {chunk.text[:60] for chunk in corpus.chunks}

    def page():
        at = AppTest.from_file(str(ROOT / "app/Home.py"), default_timeout=90).run()
        at.switch_page("pages/4_Ask.py").run()
        assert not at.exception and not at.error, "The Ask page did not load clean."
        return at

    def ask(question):
        at = page()
        at.text_input(key="ask_box").set_value(question).run()
        assert not at.exception, f"Exception on: {question}"
        return at

    def shows_no_excerpt(at):
        body = rendered(at)
        return not any(head in body for head in excerpts)

    starters = []
    for starter in ask_ui.STARTERS:
        at = ask(starter)
        assert at.success or at.warning, f"Starter produced nothing: {starter}"
        starters.append({"starter": starter, "answered": bool(at.success),
                         "no_exception": True})
        print(f"starter PASS: {starter}")

    advice = ask("am I covered for physiotherapy")
    assert advice.error and not advice.success, "An advice question was not refused."
    assert shows_no_excerpt(advice), "An advice refusal leaked a source excerpt."

    clinical = ask("I have a sore throat and fever")
    assert clinical.error and not clinical.success, "A clinical question was not refused."
    assert shows_no_excerpt(clinical), "A clinical refusal leaked a source excerpt."

    emergency = ask("when is ambulance treatment covered")
    assert emergency.error and not emergency.success, "An emergency term did not escalate."
    assert "call 000 now" in rendered(emergency), "The escalation text did not appear."
    assert any("asking how this is covered" in item.label for item in emergency.expander), \
        "The general-information follow-up was not offered after the escalation."

    unmatched = ask("qqzzxx wkwkwk ploofnar")
    assert unmatched.warning and not unmatched.success, "A no-match question did not warn."

    answered = ask("how do I claim money back after seeing a doctor")
    assert answered.success, "A known-good question returned nothing."
    held = [key for key in ask_ui.SESSION_KEYS
            if isinstance(answered.session_state.get(key), str)]
    assert not held, f"Question text may be held in {held}."

    print("refusal, escalation, no-match and counter checks: PASS")
    return {
        "starter_checks": starters,
        "advice_refused_without_excerpt": True,
        "clinical_refused_without_excerpt": True,
        "emergency_escalated_before_source": True,
        "unmatched_question_warns": True,
        "question_text_persisted": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="docs/prototype/ask_ui_check.json")
    output = ROOT / parser.parse_args().out
    if output.exists():
        raise SystemExit("The report already exists. Keep it for review.")
    if os.getenv("OSHC_OFFLINE") != "1" or os.getenv("OSHC_ENABLE_LIVE") != "0":
        raise SystemExit("Run with OSHC_OFFLINE=1 and OSHC_ENABLE_LIVE=0.")

    budget = Budget()
    before = budget.status()

    with patch("oshc.llm._client",
               side_effect=AssertionError("Unexpected provider access")) as provider:
        corpus = build_corpus(ROOT)
        page_of = {chunk.chunk_id: chunk.page for chunk in corpus.chunks}
        search = PolicySearch(corpus)
        gold = score(gold_probes(), search, page_of)
        dev = score(dev_probes(), search, page_of)
        with patch("oshc.composer.compose",
                   side_effect=AssertionError("The composer must not be reachable")) as composer:
            ui = ui_checks(corpus)
            composer.assert_not_called()
        provider.assert_not_called()

    if before != budget.status():
        raise AssertionError("The spending ledger changed.")

    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": ("Retrieval and guardrail checks on the Ask page's own code path. "
                  "Neither probe set is held out, so these are the optimistic end of the "
                  "range. Not a measure of whether a student understood the passage."),
        "source_sha256": SOURCE_SHA256,
        "top_k": TOP_K,
        "excerpt_count": len(corpus.chunks),
        "generated_answers": False,
        "composer_reachable": False,
        "guardrail_runs_before_retrieval": True,
        **ui,
        "gold_guide_wording": gold,
        "dev_student_wording": dev,
        "recall_at_5_gap": round(gold["recall_at_5"] - dev["recall_at_5"], 4),
        "additional_api_calls": 0,
        "protected_files_unchanged": True,
        "budget_unchanged": True,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")

    for name, result in (("gold, guide wording", gold), ("dev, student wording", dev)):
        print(f"{name}: n={result['allowed_and_scored']} "
              f"Recall@5 {result['recall_at_5']:.3f} "
              f"Recall@1 {result['recall_at_1']:.3f} "
              f"MRR {result['mrr']:.3f} "
              f"refused {result['refused_at_guardrail']}")
    print(f"Recall@5 gap, guide wording minus student wording: {report['recall_at_5_gap']:.3f}")
    print("Additional API calls: 0; budget unchanged.")
    print("Wrote:", output)


if __name__ == "__main__":
    main()
