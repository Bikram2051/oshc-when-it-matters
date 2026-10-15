"""Bounded synthetic connection smoke check; never an unseen safety evaluation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from oshc.llm import api_key_configured
from oshc.llm_budget import Budget, MODEL
from oshc.student_chat import answer_question


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Permit the bounded synthetic Haiku request")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit("Choose a new report path; previous connection results are preserved.")
    configured = api_key_configured()
    record = {"kind": "synthetic live connection smoke check", "created_at_utc": datetime.now(UTC).isoformat(),
              "model": MODEL, "api_key_configured": configured,
              "independent_safety_evaluation": False, "live_request_attempted": False,
              "files": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in
                        ("oshc/live_chat.py", "oshc/student_chat.py", "oshc/guardrail.py", "oshc/llm.py")}}
    if not configured:
        record.update(status="not_run", reason="OSHC_API_KEY is not configured in this running checkout or server secrets.")
    elif not args.live:
        record.update(status="not_run", reason="Use --live to permit the bounded synthetic request.")
    else:
        os.environ.update(OSHC_OFFLINE="0", OSHC_ENABLE_LIVE="1", OSHC_MODEL=MODEL)
        try:
            budget = Budget()
            before = budget.status()["spent_or_reserved"]
            record["live_request_attempted"] = True
            response = answer_question("What documents are generally required to submit a medical claim online?")
            after = budget.status()["spent_or_reserved"]
            record.update(status="passed" if response.answer and response.answer_id == "haiku-grounded" else "abstained",
                          response_status=response.status, cited_passages=len(response.hits),
                          checked_answer_released=bool(response.answer), cost_usd=round(after - before, 6))
        except Exception as exc:
            record.update(status="blocked", error_type=type(exc).__name__)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2)
        handle.write("\n")
    print(json.dumps({k: v for k, v in record.items() if k != "files"}, indent=2))
    if record["status"] != "passed":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
