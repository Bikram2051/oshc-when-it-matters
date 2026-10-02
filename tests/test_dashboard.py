"""Synthetic report fixtures only; these are not project evaluation results."""
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

import oshc.dashboard_ui as ui
import oshc.evidence_dashboard as reports
import oshc.llm as adapter

ROOT = Path(__file__).resolve().parents[1]


def examples():
    base = {"checked_at_utc": "2026-10-01T00:00:00+00:00", "additional_api_calls": 0,
            "protected_files_unchanged": True, "budget_unchanged": True,
            "source_sha256": reports.GUIDE_SHA}
    values = {key: dict(base) for key, _, _ in reports.SPECS}
    values["bill_ui"].update(provider_calls=0, budget_source_database_cache_unchanged=True,
        examples=[{"example": name, "displayed_totals": ["AUD 105.00", "Not shown", "Not shown"],
                   "gp_difference_aud": "44.95", "whole_bill_comparison": None}
                  for name in ("GP visit: text example", "GP visit: PDF example",
                               "GP visit: saved AI reading")])
    values["mbs_reference"]["checks"] = dict.fromkeys(("published_amount_used",
        "cached_bill_replayed", "printed_values_unchanged", "mixed_total_unknown",
        "budget_and_source_database_cache_bytes_unchanged"), True)
    values["mbs_source"].update(source_sha256=reports.XML_SHA, database_sha256=reports.DATABASE_SHA,
        paid_api_calls=0,
        difference_count=0, xml_duplicate_item_count=0, database_unchanged=True,
        database_row_count=2, matching_schedule_fee_count=2, xml_unique_item_count=2, differences=[])
    values["policy_source"]["search_smoke_checks"] = [
        {"query": name, "returned_pages": sorted(pages), "passed": True}
        for name, pages in reports.TOPICS.items()]
    values["navigator_ui"].update(claim_instructions_page_28=True, table_page_19_available=True,
        adjacent_page_navigation=True, personal_question_input=False, generated_answers=False,
        topic_checks=[{"topic": name, "pdf_page": page, "exact_source_text": True}
                      for name, page in reports.NAV_PAGES.items()])
    values["coach_ui"].update(home_navigation=True, navigator_page_handoff=True, progress_reset=True,
        learning_effectiveness_measured=False, progress_storage="Streamlit session only",
        lesson_checks=[{"lesson": name, "pdf_page": page, "column": column,
                        "source_anchors_found": True, "wrong_then_correct_feedback": True,
                        "first_attempt_preserved": True}
                       for name, (page, column) in reports.LESSON_PAGES.items()])
    return values


def save(root, key, value):
    path = root / f"docs/prototype/{key}_check.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    provider = Mock(side_effect=AssertionError("Unexpected provider access"))
    monkeypatch.setattr(adapter, "_client", provider)
    yield
    provider.assert_not_called()


@pytest.mark.parametrize("key", [item[0] for item in reports.SPECS])
def test_each_report_is_recognised(tmp_path, key):
    save(tmp_path, key, examples()[key])
    evidence = reports.load_evidence(tmp_path)
    assert sum(item.status == reports.PASSED for item in evidence) == 1
    item = next(item for item in evidence if item.status == reports.PASSED)
    assert item.file.endswith(f"/{key}_check.json") and len(item.sha256) == 64


@pytest.mark.parametrize("key,field", [
    ("bill_ui", "budget_source_database_cache_unchanged"),
    ("mbs_reference", "checks"), ("mbs_source", "database_unchanged"),
    ("policy_source", "budget_unchanged"), ("navigator_ui", "adjacent_page_navigation"),
    ("coach_ui", "navigator_page_handoff")])
def test_truthy_strings_do_not_count_as_passing(tmp_path, key, field):
    value = examples()[key]
    value[field] = "true"
    save(tmp_path, key, value)
    assert any(item.status == "Needs review" for item in reports.load_evidence(tmp_path))
    assert not any(item.status == reports.PASSED for item in reports.load_evidence(tmp_path))


@pytest.mark.parametrize("raw", ['{"x":1,"x":2}', '{"x":NaN}', '{broken'],
                         ids=["duplicate", "nonfinite", "syntax"])
def test_invalid_json_is_unknown(tmp_path, raw):
    path = save(tmp_path, "bill_ui", {})
    path.write_text(raw, encoding="utf-8")
    assert reports.load_evidence(tmp_path)[0].status == "Needs review"


def test_source_mismatch_is_not_hidden_by_passed_flags(tmp_path):
    value = examples()["policy_source"]
    value["source_sha256"] = "0" * 64
    save(tmp_path, "policy_source", value)
    assert reports.load_evidence(tmp_path)[3].status == "Needs review"


def test_count_mismatch_is_not_a_successful_audit(tmp_path):
    value = examples()["mbs_source"]
    value["matching_schedule_fee_count"] = 1
    save(tmp_path, "mbs_source", value)
    assert reports.load_evidence(tmp_path)[2].status == "Needs review"


def test_xml_can_contain_items_outside_the_database(tmp_path):
    value = examples()["mbs_source"]
    value["xml_unique_item_count"] = 3
    save(tmp_path, "mbs_source", value)
    assert reports.load_evidence(tmp_path)[2].status == reports.PASSED


def test_search_pass_flag_cannot_hide_missing_expected_page(tmp_path):
    value = examples()["policy_source"]
    value["search_smoke_checks"][0]["returned_pages"] = [1]
    save(tmp_path, "policy_source", value)
    assert reports.load_evidence(tmp_path)[3].status == "Needs review"


def test_export_excludes_arbitrary_report_fields(tmp_path):
    for key, value in examples().items():
        value["untrusted_content"] = "DO-NOT-EXPORT-BILL-TEXT"
        save(tmp_path, key, value)
    exported = reports.summary_bytes(reports.load_evidence(tmp_path))
    assert b"DO-NOT-EXPORT" not in exported
    assert all(item["status"] == "Not linked here"
               for item in json.loads(exported)["independent_evaluations"])


def app():
    at = AppTest.from_file(str(ROOT / "app/Home.py"), default_timeout=15).run()
    at.switch_page("pages/4_Dashboard.py").run()
    assert not at.exception
    return at


def test_missing_reports_remain_unknown_in_ui(tmp_path, monkeypatch):
    monkeypatch.setattr(ui, "ROOT", tmp_path)
    at = app()
    assert at.metric[0].value == "0 of 6" and at.warning
    assert set(at.dataframe[0].value["Status"]) == {"Missing report"}
    assert set(at.dataframe[1].value["Status"]) == {"Not linked here"}


def test_ui_rerun_drops_stale_pass_and_download_remains_available(tmp_path, monkeypatch):
    monkeypatch.setattr(ui, "ROOT", tmp_path)
    for key, value in examples().items():
        save(tmp_path, key, value)
    at = app()
    assert at.metric[0].value == "6 of 6" and not at.warning
    assert len(at.get("download_button")) == 1
    save(tmp_path, "coach_ui", {})
    at.run()
    assert not at.exception and at.metric[0].value == "5 of 6" and at.warning
    assert at.dataframe[0].value.iloc[5]["Status"] == "Needs review"
