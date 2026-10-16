"""New prototype fixtures, separate from the frozen research extractor and evaluation set."""
from oshc.billexplainer.extract_document import read_document
from oshc.billexplainer.privacy import retained_fields
from oshc.billexplainer.explanation import explain


INVOICE = """Name: Synthetic Person
DOB: 01/01/1990
Medicare No: 9999 99999 9
Date\tMBS Item\tDescription\tFee\tGST
14/10/2026\t23\tVisit for Synthetic Person\t$95.00\t$0.00
14/10/2026\t36\tAnother visit\t$150.00\t$0.00
Total Gross Amount:\t$245.00\t$0.00
Total GST:\t$0.00
Amount Settled:\t$245.00
Balance Remaining:\t$0.00
"""


def test_dated_receipt_table_keeps_payments_separate():
    result, receipt = read_document(INVOICE)
    assert result.service_date == "2026-10-14"
    assert result.total_charged == 245
    assert [r.charged for r in result.line_items] == [95, 150]
    assert result.total_benefit is None and result.total_gap is None
    assert receipt.amount_settled == 245 and receipt.balance_remaining == 0
    assert receipt.total_gst == 0
    assert not result.warnings
    assert "not your final insurance gap" in " ".join(explain(result, receipt))


def test_different_row_dates_do_not_become_one_service_date():
    result, receipt = read_document(INVOICE.replace("14/10/2026\t36", "15/10/2026\t36"))
    assert result.service_date is None
    assert receipt.service_dates == ("2026-10-14", "2026-10-15")
    assert any("different" in warning for warning in result.warnings)


def test_unlabelled_multiple_totals_cannot_shift_into_a_charge():
    result, _ = read_document("Item | Description | Charge\n23 | Visit | 95.00\nGrand total: 95.00\t10.00")
    assert result.total_charged is None
    assert result.warnings


def test_conflicting_receipt_payments_stay_unknown():
    result, receipt = read_document(INVOICE + "Amount settled: $200.00")
    assert receipt.amount_settled is None
    assert result.total_benefit is None and result.total_gap is None


def test_retained_data_suppresses_identity_and_arbitrary_descriptions():
    result, receipt = read_document(INVOICE)
    retained = repr(retained_fields(result, receipt))
    for secret in ("Synthetic Person", "9999 99999 9", "01/01/1990", "Another visit"):
        assert secret not in retained
    assert "Service line 1" in retained
    assert "245" in retained


def test_quantity_ambiguity_remains_rejected():
    result, _ = read_document("Date | Item | Description | Quantity | Fee | GST\n01/09/2026 | 23 | Visit | 2 | 50.00 | 0.00")
    assert not result.line_items
