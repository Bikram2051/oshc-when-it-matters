"""Read six saved engineering reports. No evaluations run here."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE_SHA = "6ca7151567ee2b61f8e6b50340c297d50deb249a013f055ef38f50ed07ec87c7"
XML_SHA = "c5c04792cbdc7017589b4453aa4506f26b6cfcbfeaee3b0d6c866a8050b06565"
DATABASE_SHA = "eeca641a80d3a4ccf6310428b488d7b4041cfc308a64e793fa54d05462ebb11a"
PASSED = "Recorded checks passed"
LIMIT = 1_000_000
SCOPE = ("Saved engineering evidence only. Opening this page does not rerun checks "
         "or certify the current code. Independent performance is not established here.")
SPECS = (
    ("bill_ui", "Bill Explainer", "Three synthetic UI examples; not extraction accuracy."),
    ("mbs_reference", "MBS comparisons", "Published reference comparisons; not claim entitlement."),
    ("mbs_source", "MBS source audit", "Frozen XML and database schedule fees; not coverage."),
    ("policy_source", "Policy search", "Six known-topic searches; not held-out Recall@5."),
    ("navigator_ui", "Navigator", "Fixed-topic excerpts and PDF navigation; not conversational safety."),
    ("coach_ui", "Journey Coach", "Three authored lessons and session practice; not learning impact."),
)
EVALUATIONS = (
    "Human coding agreement (kappa)", "Classification macro-F1 and shift gap",
    "Held-out retrieval Recall@5", "Held-out guardrail performance",
    "Held-out bill extraction F1 and degradation", "Learning effectiveness",
)
TOPICS = {
    "Medicare Benefits Schedule": {17}, "making a claim": {28, 29},
    "waiting periods": {21}, "membership card": {8},
    "direct billing": {28}, "ambulance services": {25},
}
NAV_PAGES = {"Making a claim": 4, "Waiting periods": 21, "Membership card": 8,
             "Direct billing": 28, "Ambulance services": 25, "Medicare Benefits Schedule": 17}
LESSON_PAGES = {"cover_documents": (8, "left"), "mbs_fee": (17, "left"),
                "direct_billing": (28, "right")}


@dataclass(frozen=True)
class Evidence:
    component: str
    file: str
    scope: str
    status: str
    checked_at_utc: str | None
    sha256: str | None
    detail: str


class ReportIssue(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ReportIssue(message)


def flags(record, *names):
    require(isinstance(record, dict), "Expected a checks object.")
    for name in names:
        require(record.get(name) is True, f"Missing or unsuccessful check: {name}.")


def zero(record, name):
    require(type(record.get(name)) is int and record[name] == 0,
            f"Expected a recorded zero: {name}.")


def named_rows(record, field, name, expected):
    rows = record.get(field)
    require(isinstance(rows, list) and len(rows) == len(expected), f"Incomplete {field}.")
    require(all(isinstance(row, dict) and isinstance(row.get(name), str) for row in rows),
            f"Invalid entries in {field}.")
    require({row[name] for row in rows} == set(expected), f"Unexpected or duplicate {field}.")
    return rows


def validate(key, record):
    if key == "bill_ui":
        zero(record, "provider_calls")
        flags(record, "budget_source_database_cache_unchanged")
        names = ("GP visit: text example", "GP visit: PDF example", "GP visit: saved AI reading")
        for row in named_rows(record, "examples", "example", names):
            require(row.get("displayed_totals") == ["AUD 105.00", "Not shown", "Not shown"]
                    and row.get("gp_difference_aud") == "44.95"
                    and "whole_bill_comparison" in row and row["whole_bill_comparison"] is None,
                    "Synthetic bill values do not match the recorded checkpoint.")
        return "3 synthetic bill flows recorded."
    if key == "mbs_source":
        zero(record, "paid_api_calls")
        zero(record, "difference_count")
        flags(record, "database_unchanged")
        count = record.get("database_row_count")
        require(type(count) is int and count > 0, "Missing database row count.")
        matched = record.get("matching_schedule_fee_count")
        require(type(matched) is int and matched == count, "Database fee comparison is incomplete.")
        require(record.get("differences") == [] and record.get("source_sha256") == XML_SHA
                and record.get("database_sha256") == DATABASE_SHA,
                "Source identity or fee comparison differs.")
        return f"{count:,}/{count:,} schedule fees matched in the saved audit."
    zero(record, "additional_api_calls")
    if key == "mbs_reference":
        flags(record.get("checks"), "published_amount_used", "cached_bill_replayed",
              "printed_values_unchanged", "mixed_total_unknown",
              "budget_and_source_database_cache_bytes_unchanged")
        return "5 comparison and preservation checks recorded."
    require(record.get("source_sha256") == GUIDE_SHA, "Unexpected guide identity.")
    flags(record, "protected_files_unchanged", "budget_unchanged")
    if key == "policy_source":
        for row in named_rows(record, "search_smoke_checks", "query", TOPICS):
            flags(row, "passed")
            pages = row.get("returned_pages")
            require(isinstance(pages, list) and 1 <= len(pages) <= 5
                    and all(type(page) is int and 1 <= page <= 37 for page in pages),
                    "Invalid search result pages.")
            require(bool(TOPICS[row["query"]].intersection(pages)), "Known-topic page missing.")
        return "6 known-topic searches recorded."
    if key == "navigator_ui":
        flags(record, "claim_instructions_page_28", "table_page_19_available",
              "adjacent_page_navigation")
        require(record.get("personal_question_input") is False
                and record.get("generated_answers") is False, "Navigator scope differs.")
        for row in named_rows(record, "topic_checks", "topic", NAV_PAGES):
            flags(row, "exact_source_text")
            require(type(row.get("pdf_page")) is int
                    and row["pdf_page"] == NAV_PAGES[row["topic"]], "Topic page differs.")
        return "6 topic checks and PDF navigation recorded."
    require(key == "coach_ui", "Unknown report type.")
    flags(record, "home_navigation", "navigator_page_handoff", "progress_reset")
    require(record.get("learning_effectiveness_measured") is False
            and record.get("progress_storage") == "Streamlit session only", "Coach scope differs.")
    for row in named_rows(record, "lesson_checks", "lesson", LESSON_PAGES):
        flags(row, "source_anchors_found", "wrong_then_correct_feedback", "first_attempt_preserved")
        require(type(row.get("pdf_page")) is int
                and (row["pdf_page"], row.get("column")) == LESSON_PAGES[row["lesson"]],
                "Lesson source differs.")
    return "3 lesson flows, source handoff and reset recorded."


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON keys.")
        result[key] = value
    return result


def reject_constant(_):
    raise ReportIssue("Non-finite JSON value.")


def load_evidence(root: Path) -> list[Evidence]:
    evidence = []
    for key, component, scope in SPECS:
        relative = f"docs/prototype/{key}_check.json"
        digest = stamp = None
        try:
            with (root / relative).open("rb") as handle:
                raw = handle.read(LIMIT + 1)
            require(len(raw) <= LIMIT, "Report exceeds the size limit.")
            digest = hashlib.sha256(raw).hexdigest()
            record = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_keys,
                                parse_constant=reject_constant)
            require(isinstance(record, dict), "Expected a JSON object.")
            value = record.get("checked_at_utc")
            require(isinstance(value, str) and len(value) <= 40, "Missing check timestamp.")
            checked = datetime.fromisoformat(value)
            require(checked.utcoffset() is not None, "Check timestamp has no timezone.")
            stamp = checked.astimezone(timezone.utc).isoformat()
            detail = validate(key, record)
            status = PASSED
        except FileNotFoundError:
            status, detail = "Missing report", "No report at the expected path."
        except ReportIssue as error:
            status, detail = "Needs review", str(error)
        except (OSError, ValueError, TypeError, OverflowError, RecursionError):
            status, detail = "Needs review", "Unreadable report, invalid JSON or invalid field format."
        evidence.append(Evidence(component, relative, scope, status, stamp, digest, detail))
    return evidence


def summary_bytes(evidence):
    summary = {"scope": SCOPE, "reports": [asdict(item) for item in evidence],
               "independent_evaluations": [{"measure": name, "status": "Not linked here"}
                                           for name in EVALUATIONS]}
    return (json.dumps(summary, indent=2) + "\n").encode("utf-8")
