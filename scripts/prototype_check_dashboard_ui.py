"""Check the current dashboard while preserving every saved evidence report."""
import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

from oshc.evidence_dashboard import PASSED, load_evidence, summary_bytes
from oshc.policy_source import SOURCE_DOC
from oshc.project_progress import RECORDED, evaluation_rows, load_measurements


def source_fingerprints():
    """Hash an explicit public-source/cache allowlist; never inspect private runtime."""
    names = ("corpus/MANIFEST.csv", f"corpus/{SOURCE_DOC}",
             "corpus/MBS-XML-20260801.XML", "data/mbs/mbs.sqlite",
             "data/rules/benefit_rules.csv", "data/rules/SOURCES.md")
    paths = [ROOT / name for name in names]
    paths.extend(sorted((ROOT / "cache/llm/v2").glob("*.json")))
    return {path.relative_to(ROOT).as_posix():
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
            for path in paths}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("docs/prototype/dashboard_ui_check.json"),
                        help="New JSON report path, relative to the repository or absolute.")
    args = parser.parse_args(argv)
    output = args.out if args.out.is_absolute() else ROOT / args.out
    if output.exists():
        raise SystemExit(f"Report already exists: {output}. Preserve it and choose a new --out.")
    if os.getenv("OSHC_OFFLINE") != "1" or os.getenv("OSHC_ENABLE_LIVE") != "0":
        raise SystemExit("Run with OSHC_OFFLINE=1 and OSHC_ENABLE_LIVE=0.")

    before_files = source_fingerprints()
    evidence = load_evidence(ROOT)
    measurements = load_measurements(ROOT)
    before_reports = summary_bytes(evidence)
    before_measurements = {key: item.sha256 for key, item in measurements.items()}
    from oshc.dashboard_ui import NOT_MEASURED, status_rows
    from oshc.final_results import load_final
    expected_rows = status_rows(measurements, load_final(ROOT))
    passing = sum(item.status == PASSED for item in evidence)
    linked = sum(row["Status"] not in (NOT_MEASURED, "Not linked here") for row in expected_rows)

    with (
        patch("oshc.llm._client", side_effect=AssertionError("Unexpected provider access"))
        as provider,
        patch("oshc.llm.complete", side_effect=AssertionError("Unexpected model call"))
        as complete,
        patch("oshc.llm_budget.Budget.__init__",
              side_effect=AssertionError("Unexpected budget/ledger access")) as budget,
    ):
        at = AppTest.from_file(str(ROOT / "app/Home.py"), default_timeout=25).run()
        at.switch_page("views/5_Dashboard.py").run()
        assert not at.exception and not at.error
        assert at.title[0].value == "Project dashboard"
        assert [tab.label for tab in at.tabs] == [
            "Overview", "Results", "Safety", "Evidence & sources"]
        assert at.metric[0].value == f"{passing} of {len(evidence)}"
        assert at.metric[1].value == f"{linked} of {len(expected_rows)}"
        assert list(at.dataframe[0].value["Status"]) == [item.status for item in evidence]
        assert list(at.dataframe[1].value["Status"]) == [row["Status"] for row in expected_rows]
        assert bool(at.warning) == (passing != len(evidence))
        assert len(at.get("download_button")) == 1
        assert len(json.loads(before_reports)["reports"]) == len(evidence)
        provider.assert_not_called()
        complete.assert_not_called()
        budget.assert_not_called()

    after_measurements = {key: item.sha256 for key, item in load_measurements(ROOT).items()}
    if before_reports != summary_bytes(load_evidence(ROOT)):
        raise AssertionError("An engineering input report changed.")
    if before_measurements != after_measurements:
        raise AssertionError("An aggregate measurement report changed.")
    if before_files != source_fingerprints():
        raise AssertionError("An allowlisted public source or replay cache changed.")
    result = {
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "scope": "Current dashboard integration; historical checks and evaluations not rerun.",
        "dashboard_page": "views/5_Dashboard.py",
        "tabs": [tab.label for tab in at.tabs],
        "engineering_report_count": len(evidence),
        "recorded_passing_report_count": passing,
        "evaluation_group_count": len(expected_rows),
        "linked_result_group_count": linked,
        "input_report_sha256": {item.file: item.sha256 for item in evidence},
        "measurement_report_sha256": {
            item.file: item.sha256 for item in measurements.values()},
        "source_cache_sha256": before_files,
        "report_statuses_match_validated_inputs": True,
        "missing_results_not_fabricated": True,
        "summary_export_available": True,
        "input_reports_unchanged": True,
        "measurement_reports_unchanged": True,
        "allowlisted_public_sources_and_cache_unchanged": True,
        "provider_calls": provider.call_count,
        "llm_calls": complete.call_count,
        "budget_initializations": budget.call_count,
        "private_runtime_inspected": False,
        "additional_api_calls": 0,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(f"Dashboard: PASS; {len(evidence)} saved reports, {linked} linked result groups.")
    print("Provider calls: 0; model calls: 0; budget initializations: 0.")
    print("Saved reports, allowlisted sources and cache unchanged. Private runtime not inspected.")
    print("Wrote:", output)


if __name__ == "__main__":
    main()
