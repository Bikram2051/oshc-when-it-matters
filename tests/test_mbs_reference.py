"""Constructed engineering cases, not independent invoice evaluation."""
import hashlib
from decimal import Decimal
import xml.etree.ElementTree as ET

import pytest

from oshc.billexplainer import mbs_reference as ref
from oshc.schemas import ExtractionResult, LineItem


@pytest.fixture
def source(tmp_path, monkeypatch):
    def make(changes=None, duplicate=False):
        root = ET.Element("MBS_XML")
        for number, kind, field, amount in (
            ("23", "E", "Benefit100", "45.05"),
            ("104", "C", "Benefit85", "88.40"),
        ):
            record = dict(ItemNum=number, Description="Synthetic consultation " + number,
                          Category="1", FeeType="N", BenefitType=kind,
                          ScheduleFee="45.05" if number == "23" else "103.95",
                          ItemStartDate="01.01.2020", ItemEndDate="",
                          FeeStartDate="01.07.2026", BenefitStartDate="01.01.2020")
            record[field] = amount
            if number == "104":
                record.update(changes or {})
            for _ in range(2 if duplicate and number == "104" else 1):
                node = ET.SubElement(root, "Data")
                for name, value in record.items():
                    ET.SubElement(node, name).text = value
        raw = ET.tostring(root)
        path = tmp_path / "synthetic.xml"
        path.write_bytes(raw)
        monkeypatch.setattr(ref, "FROZEN_SHA256", hashlib.sha256(raw).hexdigest())
        return ref.load_snapshot(path)
    return make


def bill(item="104", charge=150.0, when="2026-09-01", **extra):
    return ExtractionResult(
        extractor="rules", source_kind="pasted_text", service_date=when,
        total_charged=charge,
        line_items=[LineItem(raw_description="Synthetic consultation 104",
                             item_number=item, charged=charge, **extra)],
    )


def test_published_amount_and_original_bill_preserved(source):
    original = bill(benefit_paid=12.0, gap=138.0)
    before = original.model_dump_json()
    result = ref.compare_bill(original, source(), ["Benefit85"])
    assert result.lines[0].reference_amount == Decimal("88.40")
    assert result.lines[0].difference == Decimal("61.60")
    assert result.total_difference == Decimal("61.60")
    assert original.model_dump_json() == before


@pytest.mark.parametrize("field", ["ScheduleFee", "Benefit100"])
def test_gp_reference_fields(source, field):
    result = ref.compare_bill(bill("23", 90), source(), [field])
    assert result.lines[0].reference_amount == Decimal("45.05")
    assert result.total_difference == Decimal("44.95")


def test_capping_is_explicit(source):
    line = ref.compare_bill(bill(charge=70), source(), ["Benefit85"]).lines[0]
    assert line.reference_amount == Decimal("88.40")
    assert line.amount_used == Decimal("70.00")
    assert line.difference == Decimal("0.00")


@pytest.mark.parametrize("item", [None, "999999", "2 x 104", "104/23", "about 104", "104.5"])
def test_no_description_fallback_for_missing_or_invalid_item(source, item):
    result = ref.compare_bill(bill(item=item), source(), ["Benefit85"])
    assert result.lines[0].reference_amount is None
    assert result.total_difference is None


@pytest.mark.parametrize("when", [None, "01/09/2026", "2026-07-31", "2026-09-29", "2026-02-30"])
def test_missing_invalid_or_outside_window_date(source, when):
    assert ref.compare_bill(bill(when=when), source(), ["Benefit85"]).total_difference is None


@pytest.mark.parametrize("when", ["2026-08-01", "2026-09-28"])
def test_window_boundaries(source, when):
    assert ref.compare_bill(bill(when=when), source(), ["Benefit85"]).total_difference == Decimal("61.60")


@pytest.mark.parametrize("changes", [
    {"FeeType": "D"}, {"Benefit85": ""}, {"Benefit85": "NaN"},
    {"Benefit85": "200.00"}, {"BenefitType": "E"},
    {"FeeStartDate": "01.10.2026"}, {"ItemStartDate": "02.09.2026"},
    {"BenefitStartDate": "02.09.2026"}, {"ItemEndDate": "31.08.2026"},
    {"FeeStartDate": ""}, {"ItemEndDate": "bad date"},
    {"QFEStartDate": "02.09.2026"}, {"QFEEndDate": "31.08.2026"},
], ids=["derived", "absent", "nan", "above-fee", "wrong-type", "future-fee",
        "future-item", "future-benefit", "ceased", "missing-date", "bad-date",
        "future-listing", "ended-listing"])
def test_source_applicability_failures(source, changes):
    line = ref.compare_bill(bill(), source(changes), ["Benefit85"]).lines[0]
    assert line.status == "unavailable"
    assert line.reference_amount is None and line.difference is None


@pytest.mark.parametrize("charge", [None, -1, float("nan"), float("inf"), 1.001, 1000001],
                         ids=["missing", "negative", "nan", "infinite", "fractional-cent", "too-large"])
def test_invalid_charge(source, charge):
    assert ref.compare_bill(bill(charge=charge), source(), ["Benefit85"]).total_difference is None


def test_no_automatic_percentage_selection(source):
    assert ref.compare_bill(bill(), source()).lines[0].reference_amount is None
    assert ref.compare_bill(bill(), source(), ["85%"]).lines[0].reference_amount is None
    assert ref.compare_bill(bill("23"), source(), ["Benefit85"]).lines[0].reference_amount is None


@pytest.mark.parametrize("total", [None, 149.0])
def test_incomplete_bill_has_no_total(source, total):
    original = bill().model_copy(update={"total_charged": total})
    result = ref.compare_bill(original, source(), ["Benefit85"])
    assert result.lines[0].difference == Decimal("61.60")
    assert result.total_difference is None


def test_mixed_and_empty_bills_have_no_total(source):
    original = bill()
    original = original.model_copy(update={"line_items": original.line_items + [
        LineItem(raw_description="Administration", charged=15)
    ], "total_charged": 165.0})
    result = ref.compare_bill(original, source(), ["Benefit85", "Benefit85"])
    assert result.lines[0].difference == Decimal("61.60")
    assert result.lines[1].reference_amount is None and result.total_difference is None
    empty = original.model_copy(update={"line_items": [], "total_charged": 0.0})
    assert ref.compare_bill(empty, source()).total_difference is None


def test_wrong_number_of_selections_rejected(source):
    with pytest.raises(ValueError):
        ref.compare_bill(bill(), source(), [])


def test_source_hash_and_duplicates_rejected(source, tmp_path, monkeypatch):
    source()
    path = tmp_path / "synthetic.xml"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ref.SourceError, match="hash"):
        ref.load_snapshot(path)
    with pytest.raises(ref.SourceError, match="Duplicate"):
        source(duplicate=True)


def test_snapshot_cannot_be_mutated(source):
    snapshot = source()
    with pytest.raises(TypeError):
        snapshot.items["104"]["Benefit85"] = "1.00"
