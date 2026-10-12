"""Exercise the local UI examples with provider access forbidden."""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["STREAMLIT_LOGGER_LEVEL"] = "error"

import streamlit
from streamlit.testing.v1 import AppTest
from oshc.billexplainer import ui
from oshc.llm_budget import Budget


def fingerprints():
    paths = [ROOT / "data/mbs/mbs.sqlite", ROOT / "corpus/MBS-XML-20260801.XML"]
    paths += list((ROOT / "cache/llm/v2").glob("*.json"))
    return {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths}


def main(output):
    if Path.cwd().resolve() != ROOT:
        raise SystemExit("Run from the repository root.")
    if output.exists():
        raise SystemExit("The UI check report already exists. Choose a new --out path.")
    ui.require_offline()
    before_budget, before_files = Budget().status(), fingerprints()
    readings = []
    with patch("oshc.llm._client", side_effect=AssertionError("Unexpected provider access")) as provider:
        at = AppTest.from_file(str(ROOT / "app/Home.py"), default_timeout=20).run()
        at.switch_page("pages/3_Bill_Explainer.py").run()
        for label in ui.EXAMPLES:
            at.selectbox(key="be_example").select(label).run()
            at.button(key="be_read").click().run()
            assert not at.exception and not at.error, "The UI reported an error."
            values = [metric.value for metric in at.metric]
            assert values == ["AUD 105.00", "Not shown", "Not shown"], values
            at.toggle(key="be_compare").set_value(True).run()
            at.selectbox(key="be_basis_1").select("Published 100% benefit").run()
            assert not at.exception and not at.error
            assert len(at.metric) == 3, "A total comparison appeared for the mixed bill."
            assert at.dataframe[1].value.iloc[0]["Illustrative difference"] == "AUD 44.95"
            assert at.dataframe[1].value.iloc[1]["Published amount"] == "Not available"
            assert any("Total unavailable" in message.value for message in at.info)
            assert len(at.get("download_button")) == 1
            readings.append({"example": label, "displayed_totals": values,
                             "gp_difference_aud": "44.95", "whole_bill_comparison": None})
            at.button(key="be_clear").click().run()
            assert not at.exception and not at.metric and not at.get("download_button")
            print(label + ": PASS")
        provider.assert_not_called()
    if Budget().status() != before_budget or fingerprints() != before_files:
        raise SystemExit("Budget, database, source or cache changed. Stop here.")
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "parent_commit": "e420e72", "streamlit_version": streamlit.__version__,
              "data_role": "Synthetic UI integration checks, not independent evaluation",
              "examples": readings, "provider_calls": 0,
              "budget_source_database_cache_unchanged": True,
              "budget_after": Budget().status()}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print("Clear removes the displayed bill: PASS")
    print("Additional API calls: 0")
    print("Budget:", json.dumps(Budget().status(), indent=2))
    print("Wrote:", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "docs/prototype/bill_ui_check.json")
    main(parser.parse_args().out)
