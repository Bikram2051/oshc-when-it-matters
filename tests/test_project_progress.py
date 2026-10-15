"""Evidence integrity checks; fixture scores are synthetic, not project findings."""
import json
from dataclasses import asdict
from pathlib import Path
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

import oshc.dashboard_ui as ui
import oshc.llm as adapter
from oshc.project_progress import AGREEMENT_FILE, RECORDED, RETRIEVAL_FILE, load_measurements

ROOT = Path(__file__).resolve().parents[1]


def agreement():
    metric = {"kappa": 0.4, "ci_low": 0.2, "ci_high": 0.6, "n": 53}
    return {"computed_at_utc": "2026-10-13T01:00:00+00:00", "n": 53,
            "results": {"Gap": dict(metric), "Code 1": dict(metric)}}


def save_agreement(root, record):
    target = root / AGREEMENT_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record), encoding="utf-8")
    return target


def test_raw_coding_material_does_not_reach_display_data(tmp_path):
    record = agreement()
    record["disagreements"] = [{"snippet": "PRIVATE-SNIPPET", "id": "PRIVATE-ID"}]
    record["note"] = "DO-NOT-PUBLISH-ARBITRARY-PROSE"
    save_agreement(tmp_path, record)
    result = load_measurements(tmp_path)["agreement"]
    assert result.status == RECORDED and result.values["Gap"]["n"] == 53
    assert "PRIVATE" not in json.dumps(asdict(result))
    assert "DO-NOT-PUBLISH" not in json.dumps(asdict(result))


@pytest.mark.parametrize("failure", ["count", "interval", "boolean", "nonfinite", "timestamp"])
def test_inconsistent_agreement_is_unknown_instead_of_a_score(tmp_path, failure):
    record = agreement()
    if failure == "count":
        record["results"]["Gap"]["n"] = 52
    elif failure == "interval":
        record["results"]["Gap"]["ci_low"] = 0.5
    elif failure == "boolean":
        record["results"]["Gap"]["kappa"] = True
    elif failure == "nonfinite":
        record["results"]["Gap"]["kappa"] = float("nan")
    else:
        record["computed_at_utc"] = "2026-10-13T01:00:00"
    save_agreement(tmp_path, record)
    result = load_measurements(tmp_path)["agreement"]
    assert result.status == "Needs review" and result.values is None


def test_duplicate_keys_do_not_produce_an_ambiguous_score(tmp_path):
    target = save_agreement(tmp_path, {})
    target.write_text('{"n":53,"n":54}', encoding="utf-8")
    assert load_measurements(tmp_path)["agreement"].status == "Needs review"


def test_missing_result_is_not_zero(tmp_path):
    assert all(item.values is None and item.status == "Not linked here"
               for item in load_measurements(tmp_path).values())


@pytest.mark.parametrize("failure", ["count", "gap"])
def test_retrieval_does_not_display_inconsistent_denominators_or_gap(tmp_path, failure):
    record = json.loads((ROOT / RETRIEVAL_FILE).read_text(encoding="utf-8"))
    if failure == "count":
        record["dev_student_wording"]["probes"] += 1
    else:
        record["recall_at_5_gap"] = 0.9
    target = tmp_path / RETRIEVAL_FILE
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(record), encoding="utf-8")
    result = load_measurements(tmp_path)["retrieval"]
    assert result.status == "Needs review" and result.values is None


def test_dashboard_separates_historical_results_and_final_automated_safety(monkeypatch):
    provider = Mock(side_effect=AssertionError("Unexpected provider access"))
    monkeypatch.setattr(adapter, "_client", provider)
    monkeypatch.setattr(ui, "ROOT", ROOT)
    at = AppTest.from_string("from oshc.dashboard_ui import render\nrender()",
                             default_timeout=15).run()
    assert not at.exception
    assert [tab.label for tab in at.tabs] == [
        "Overview", "Results", "Safety", "Evidence & sources"]
    labels = {metric.label: metric.value for metric in at.metric}
    assert labels["Historical result groups linked"] == "1 of 6"
    assert labels["Independent automated chat check"] == "24/24 refusals"
    assert labels["Unseen false refusals"] == "6/20 (30.0%)"
    status = at.dataframe[1].value
    assert status.iloc[0]["Status"] == RECORDED
    assert set(status.iloc[1:]["Status"]) == {"Not linked here"}
    assert labels["Comprehension gap: kappa"] == "0.418"
    assert labels["Guide wording: Recall@5"] == "95.8%"
    assert labels["Student wording: Recall@5"] == "78.6%"
    provider.assert_not_called()


def test_dashboard_check_never_overwrites_a_report(tmp_path):
    from scripts.prototype_check_dashboard_ui import main

    report = tmp_path / "existing.json"
    report.write_text("preserved-checkpoint", encoding="utf-8")
    with pytest.raises(SystemExit, match="Preserve it"):
        main(["--out", str(report)])
    assert report.read_text(encoding="utf-8") == "preserved-checkpoint"


def test_dashboard_check_requires_offline_settings_before_writing(tmp_path, monkeypatch):
    from scripts.prototype_check_dashboard_ui import main

    monkeypatch.delenv("OSHC_OFFLINE", raising=False)
    monkeypatch.delenv("OSHC_ENABLE_LIVE", raising=False)
    report = tmp_path / "new.json"
    with pytest.raises(SystemExit, match="OSHC_OFFLINE=1"):
        main(["--out", str(report)])
    assert not report.exists()
