"""UI integration tests with synthetic fixtures; provider access is forbidden."""
from pathlib import Path
from unittest.mock import Mock

import pymupdf
import pytest
from streamlit.testing.v1 import AppTest

import oshc.llm as adapter
from oshc.billexplainer import ui
from oshc.billexplainer.mbs_reference import FIELDS, Snapshot, SourceError
from oshc.llm_budget import MODEL

ROOT = Path(__file__).resolve().parents[1]
TEXT = ("SYNTHETIC TEST ONLY\nService date: 01/09/2026\n"
        "Item | Description | Charge\n23 | Short consultation | $90.00\n"
        "- | Administration fee | $15.00\nTotal charged: $105.00\n")


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("OSHC_OFFLINE", "1")
    monkeypatch.setenv("OSHC_ENABLE_LIVE", "0")
    monkeypatch.setenv("OSHC_MODEL", MODEL)
    provider = Mock(side_effect=AssertionError("Unexpected provider access"))
    monkeypatch.setattr(adapter, "_client", provider)
    monkeypatch.setattr(adapter, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(ui, "ROOT", tmp_path)
    data = tmp_path / "data/demo_dev"
    data.mkdir(parents=True)
    for filename in ("rules_reader_example.txt", "llm_reader_example.txt"):
        (data / filename).write_text(TEXT, encoding="utf-8")
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((30, 40), TEXT, fontname="cour", fontsize=10)
        document.save(data / "rules_reader_example.pdf")
    row = {field: "" for field in FIELDS}
    row.update(ItemNum="23", Description="Synthetic GP reference", FeeType="N",
               ScheduleFee="45.05", Benefit100="45.05", BenefitType="E",
               ItemStartDate="01.01.2020", FeeStartDate="01.07.2026",
               BenefitStartDate="01.01.2020")
    monkeypatch.setattr(ui, "load_snapshot", lambda path: Snapshot("synthetic-test-source", {"23": row}))
    yield provider
    provider.assert_not_called()


def app():
    at = AppTest.from_file(str(ROOT / "app/Home.py"), default_timeout=15).run()
    at.switch_page("pages/3_Bill_Explainer.py").run()
    assert not at.exception
    return at


@pytest.mark.parametrize("choice", ["GP visit: text example", "GP visit: PDF example"])
def test_reading_and_reference_keep_unknown_benefits(sandbox, choice):
    at = app()
    assert not at.metric
    at.selectbox(key="be_example").select(choice).run()
    at.button(key="be_read").click().run()
    assert not at.exception
    assert [metric.value for metric in at.metric] == ["AUD 105.00", "Not shown", "Not shown"]
    at.toggle(key="be_compare").set_value(True).run()
    at.selectbox(key="be_basis_1").select("Published 100% benefit").run()
    assert not at.exception
    assert at.dataframe[1].value.iloc[0]["Illustrative difference"] == "AUD 44.95"
    assert at.dataframe[1].value.iloc[1]["Published amount"] == "Not available"
    assert len(at.metric) == 3
    assert any("Total unavailable" in message.value for message in at.info)


def test_changing_example_and_clear_remove_old_results(sandbox):
    at = app()
    at.button(key="be_read").click().run()
    at.toggle(key="be_compare").set_value(True).run()
    at.selectbox(key="be_basis_1").select("Published 100% benefit").run()
    at.selectbox(key="be_example").select("GP visit: PDF example").run()
    assert not at.metric and not at.dataframe and not at.get("download_button")
    at.button(key="be_read").click().run()
    assert not at.toggle(key="be_compare").value
    at.toggle(key="be_compare").set_value(True).run()
    assert at.selectbox(key="be_basis_1").value == "No comparison"
    at.button(key="be_clear").click().run()
    assert not at.exception and not at.metric and not at.get("download_button")


def test_custom_input_and_confirmation_changes_invalidate_results(sandbox):
    at = app()
    at.selectbox(key="be_example").select(ui.CUSTOM).run()
    at.text_area(key="be_text").set_value(TEXT).run()
    assert at.button(key="be_read").disabled
    at.checkbox(key="be_synthetic").check().run()
    at.button(key="be_read").click().run()
    assert at.metric[0].value == "AUD 105.00"
    at.text_area(key="be_text").set_value(TEXT.replace("90.00", "91.00")).run()
    assert not at.metric and not at.get("download_button")
    at.button(key="be_read").click().run()
    at.checkbox(key="be_synthetic").uncheck().run()
    assert at.button(key="be_read").disabled and not at.metric
    assert not at.exception


def test_cache_miss_stays_offline_and_shows_no_amounts(sandbox):
    at = app()
    at.selectbox(key="be_example").select("GP visit: saved AI reading").run()
    at.button(key="be_read").click().run()
    assert not at.exception and not at.metric
    assert any("No bill rows" in warning.value for warning in at.warning)


def test_saved_result_is_not_reextracted_when_reference_changes(sandbox, monkeypatch):
    saved = Mock(return_value=ui.extract_local(TEXT))
    monkeypatch.setattr(ui, "extract_saved", saved)
    at = app()
    at.selectbox(key="be_example").select("GP visit: saved AI reading").run()
    at.button(key="be_read").click().run()
    at.toggle(key="be_compare").set_value(True).run()
    at.selectbox(key="be_basis_1").select("Published 100% benefit").run()
    saved.assert_called_once()
    assert not at.exception
    assert at.metric[1].value == "Not shown"


def test_unverified_reference_preserves_only_document_readings(sandbox, monkeypatch):
    monkeypatch.setattr(ui, "load_snapshot", Mock(side_effect=SourceError("hash mismatch")))
    at = app()
    at.button(key="be_read").click().run()
    at.toggle(key="be_compare").set_value(True).run()
    assert not at.exception and len(at.dataframe) == 1
    assert at.metric[0].value == "AUD 105.00"
    assert any("reference data is unavailable" in error.value for error in at.error)


@pytest.mark.parametrize("name,value", [("OSHC_OFFLINE", "0"), ("OSHC_ENABLE_LIVE", "1")])
def test_unsafe_runtime_is_blocked_before_reading(sandbox, monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    at = app()
    assert at.error and not at.metric and not at.button
