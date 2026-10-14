"""Read named, aggregate project results without running models or evaluations.

Only selected numeric fields leave this module. Report prose, individual coding
decisions, learner questions and held-out material are never returned to the UI.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from oshc.evidence_dashboard import LIMIT, ReportIssue, require, unique_keys, validate

RECORDED = "Recorded result"
AGREEMENT_FILE = "data/agreement/agreement_2026-10-13.json"
RETRIEVAL_FILE = "docs/prototype/ask_ui_check.json"
SEMINAR_FILE = "docs/prototype/seminar_guardrail_summary_2026-10-05.json"


@dataclass(frozen=True)
class Measurement:
    name: str
    file: str
    status: str
    checked_at_utc: str | None = None
    sha256: str | None = None
    values: dict | None = None
    detail: str = ""


def _number(value, *, low=0.0, high=1.0):
    require(type(value) in (int, float) and math.isfinite(value)
            and low <= value <= high, "Invalid numeric result.")
    return float(value)


def _count(value):
    require(type(value) is int and value > 0, "Invalid sample count.")
    return value


def _timestamp(value):
    require(isinstance(value, str) and len(value) <= 40, "Missing result timestamp.")
    stamp = datetime.fromisoformat(value)
    require(stamp.utcoffset() is not None, "Result timestamp has no timezone.")
    return stamp.astimezone(UTC).isoformat()


def _agreement(record):
    n = _count(record.get("n"))
    results = record.get("results")
    require(isinstance(results, dict), "Missing agreement results.")
    values = {}
    for field in ("Gap", "Code 1"):
        row = results.get(field)
        require(isinstance(row, dict), "Missing agreement metric.")
        require(_count(row.get("n")) == n, "Agreement sample counts differ.")
        kappa = _number(row.get("kappa"), low=-1.0)
        low = _number(row.get("ci_low"), low=-1.0)
        high = _number(row.get("ci_high"), low=-1.0)
        require(low <= kappa <= high, "Invalid agreement interval.")
        values[field] = {"kappa": kappa, "ci_low": low, "ci_high": high, "n": n}
    return _timestamp(record.get("computed_at_utc")), values


def _retrieval(record):
    validate("ask_ui", record)
    values = {}
    for key in ("gold_guide_wording", "dev_student_wording"):
        row = record[key]
        n = _count(row.get("allowed_and_scored"))
        probes = _count(row.get("probes"))
        refused = row.get("refused_at_guardrail")
        require(type(refused) is int and refused >= 0 and probes == n + refused,
                "Retrieval sample counts differ.")
        values[key] = {"n": n, "probes": probes, "refused": refused,
                       "recall_at_5": _number(row.get("recall_at_5"))}
    gap = _number(record.get("recall_at_5_gap"), low=-1.0)
    computed = (values["gold_guide_wording"]["recall_at_5"]
                - values["dev_student_wording"]["recall_at_5"])
    require(abs(gap - computed) <= 0.0002, "Retrieval wording gap differs.")
    values["gap"] = gap
    return _timestamp(record.get("checked_at_utc")), values


def _seminar(record):
    require(record.get("guardrail") == "seminar.demo_guardrail"
            and record.get("current_system_evaluation") is False,
            "Seminar scope differs.")
    values = {}
    splits = record.get("splits")
    require(isinstance(splits, dict), "Missing seminar splits.")
    for split in ("dev", "class"):
        block = splits.get(split)
        require(isinstance(block, dict), "Missing seminar split.")
        values[split] = {}
        for metric in ("refusal_recall", "false_refusal_rate", "emergency_recall"):
            row = block.get(metric)
            require(isinstance(row, dict), "Missing seminar metric.")
            n = _count(row.get("n"))
            k = row.get("k")
            require(type(k) is int and 0 <= k <= n, "Invalid seminar numerator.")
            rate = _number(row.get("rate"))
            interval = row.get("ci95")
            require(isinstance(interval, list) and len(interval) == 2,
                    "Missing seminar interval.")
            low, high = (_number(value) for value in interval)
            require(low <= rate <= high and abs(rate - k / n) < 0.00001,
                    "Inconsistent seminar result.")
            values[split][metric] = {"k": k, "n": n, "rate": rate,
                                     "ci_low": low, "ci_high": high}
    return _timestamp(record.get("generated_at")), values


def _reject_constant(_):
    raise ReportIssue("Non-finite JSON value.")


def _load(root, name, relative, parser):
    digest = None
    try:
        with (root / relative).open("rb") as handle:
            raw = handle.read(LIMIT + 1)
        require(len(raw) <= LIMIT, "Result report exceeds the size limit.")
        digest = hashlib.sha256(raw).hexdigest()
        record = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_keys,
                            parse_constant=_reject_constant)
        require(isinstance(record, dict), "Expected a result object.")
        stamp, values = parser(record)
        return Measurement(name, relative, RECORDED, stamp, digest, values)
    except FileNotFoundError:
        return Measurement(name, relative, "Not linked here", detail="No named result report.")
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
        return Measurement(name, relative, "Needs review", sha256=digest,
                           detail="Missing or inconsistent result fields; no score displayed.")


def load_measurements(root: Path) -> dict[str, Measurement]:
    return {
        "agreement": _load(root, "Human coding agreement", AGREEMENT_FILE, _agreement),
        "retrieval": _load(root, "In-house source retrieval", RETRIEVAL_FILE, _retrieval),
        "seminar": _load(root, "Historical seminar guardrail", SEMINAR_FILE, _seminar),
    }


def evaluation_rows(measurements):
    agreement = measurements["agreement"]
    return [
        {"Measure": "Human coding agreement (kappa)", "Status": agreement.status,
         "Next step": "Discuss coding disagreements and document any reconciled label freeze."},
        {"Measure": "Classification macro-F1 and shift gap", "Status": "Not linked here",
         "Next step": "Complete classifier baselines using frozen labels and grouped folds."},
        {"Measure": "Held-out retrieval Recall@5", "Status": "Not linked here",
         "Next step": "Obtain independent relevance labels before the frozen evaluation."},
        {"Measure": "Held-out current guardrail performance", "Status": "Not linked here",
         "Next step": "Score frozen unseen probes; report refusal and false-refusal rates."},
        {"Measure": "Held-out bill extraction F1 and degradation", "Status": "Not linked here",
         "Next step": "Obtain evaluation invoices, separate truth and file map; use frozen protocol."},
        {"Measure": "Learning effectiveness", "Status": "Not linked here",
         "Next step": "Outside this semester's no-real-student-testing scope; disclose limitation."},
    ]
