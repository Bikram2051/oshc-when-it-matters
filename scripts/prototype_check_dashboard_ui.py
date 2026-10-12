"""Check the evidence browser against existing reports without rerunning those checks."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402
from oshc.evidence_dashboard import EVALUATIONS, PASSED, load_evidence, summary_bytes  # noqa: E402
from oshc.llm_budget import Budget  # noqa: E402
from scripts.prototype_check_policy_source import fingerprints  # noqa: E402


def main():
    output = ROOT / "docs/prototype/dashboard_ui_check.json"
    if output.exists():
        raise SystemExit("The Dashboard check report already exists. Keep it for review.")
    if os.getenv("OSHC_OFFLINE") != "1" or os.getenv("OSHC_ENABLE_LIVE") != "0":
        raise SystemExit("Run with OSHC_OFFLINE=1 and OSHC_ENABLE_LIVE=0.")
    budget = Budget()
    before_budget, before_files = budget.status(), fingerprints()
    with patch("oshc.llm._client", side_effect=AssertionError("Unexpected provider access")) as provider:
        evidence = load_evidence(ROOT)
        for item in evidence:
            print(f"{item.component}: {item.status}; {item.detail}")
        if not all(item.status == PASSED for item in evidence):
            raise SystemExit("Some saved reports need review. No Dashboard check report was written.")
        before_reports = summary_bytes(evidence)
        at = AppTest.from_file(str(ROOT / "app/Home.py"), default_timeout=25).run()
        at.switch_page("pages/4_Dashboard.py").run()
        assert not at.exception and not at.error and not at.warning
        assert at.title[0].value == "Prototype evidence"
        assert at.metric[0].value == "6 of 6"
        assert list(at.dataframe[0].value["Status"]) == [PASSED] * 6
        assert len(at.dataframe[1].value) == len(EVALUATIONS)
        assert set(at.dataframe[1].value["Status"]) == {"Not linked here"}
        assert len(at.get("download_button")) == 1
        assert len(json.loads(before_reports)["reports"]) == 6
        provider.assert_not_called()
    if before_reports != summary_bytes(load_evidence(ROOT)):
        raise AssertionError("An input report changed.")
    if before_budget != budget.status() or before_files != fingerprints():
        raise AssertionError("A protected file or spending ledger changed.")
    result = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Dashboard integration check. Historical checks were not rerun.",
        "input_report_sha256": {item.file: item.sha256 for item in evidence},
        "six_reports_displayed": True, "independent_metrics_not_fabricated": True,
        "summary_export_available": True, "input_reports_unchanged": True,
        "protected_files_unchanged": True, "budget_unchanged": True, "additional_api_calls": 0,
    }
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print("Dashboard: PASS; six historical reports and explicit evaluation gaps.")
    print("Additional API calls: 0; reports, protected files and budget unchanged.")
    print("Budget:", json.dumps(budget.status(), indent=2))
    print("Wrote:", output)


if __name__ == "__main__":
    main()
