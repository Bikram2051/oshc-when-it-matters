'''Synthetic engineering fixtures only. No independent or held-out invoices.'''

import pymupdf
import pytest

from oshc.billexplainer.extract_rules import extract
from oshc.billexplainer.read import MAX_BYTES, MAX_CHARS, read_pdf, read_text

EXAMPLE = '''SYNTHETIC DEVELOPMENT EXAMPLE
Provider: Demonstration Clinic
Service date: 01/09/2026
Item | Description | Charge
23 | Short consultation | $90.00
- | Administration fee | $15.00
Total charged: $105.00
'''


def table(row, header="Item | Description | Charge"):
    return extract(header + "\n" + row)


def pdf_bytes(rows=None, pages=1, encrypted=False):
    with pymupdf.open() as document:
        for _ in range(pages):
            page = document.new_page()
            if rows:
                # Deliberately reverse content-stream order.
                for index in reversed(range(len(rows))):
                    for x, text in zip((40, 100, 390), rows[index]):
                        page.insert_text((x, 60 + index * 20), text, fontsize=10)
        options = {"encryption": pymupdf.PDF_ENCRYPT_AES_256,
                   "owner_pw": "test-owner", "user_pw": "test-reader"} if encrypted else {}
        return document.tobytes(**options)


def test_preclaim_invoice_does_not_invent_benefits_or_gaps():
    result = extract(EXAMPLE)
    assert result.provider == "Demonstration Clinic"
    assert result.service_date == "2026-09-01"
    assert result.total_charged == 105
    assert result.total_benefit is None and result.total_gap is None
    assert [item.charged for item in result.line_items] == [90, 15]
    assert [item.item_number for item in result.line_items] == ["23", None]
    assert all(item.benefit_paid is None and item.gap is None for item in result.line_items)
    assert all(not item.matched for item in result.line_items)
    assert result.warnings == []


@pytest.mark.parametrize("money,expected", [("0", 0), ("$0.00", 0),
                                           ("AUD 1,234.56", 1234.56), ("A$12.3", 12.3)])
def test_unambiguous_amounts(money, expected):
    assert table(f"23 | Visit | {money}").line_items[0].charged == expected


@pytest.mark.parametrize("money", ["-$2.00", "(20.00)", "NaN", "inf", "1,23.45", "12.345", "1000000.01"])
def test_unsupported_amounts_remain_unknown(money):
    result = table(f"23 | Visit | {money}")
    assert result.line_items[0].charged is None
    assert any("unsupported money" in warning for warning in result.warnings)


def test_reordered_columns_and_explicit_zero_benefit():
    result = table("Visit | 90.00 | 90.00 | 23 | 0.00",
                   "Description | Gap | Charge | MBS item | Benefit paid")
    item = result.line_items[0]
    assert (item.charged, item.benefit_paid, item.gap) == (90, 0, 90)


@pytest.mark.parametrize("ambiguous", ["Paid", "Amount paid", "Benefit", "Estimated benefit"])
def test_patient_or_estimated_payment_is_not_a_paid_insurer_benefit(ambiguous):
    result = table("23 | Visit | 90.00 | 90.00", "Item | Description | Charge | " + ambiguous)
    assert result.line_items[0].benefit_paid is None
    assert result.line_items[0].gap is None
    assert result.warnings


def test_blank_tab_columns_do_not_shift_amounts():
    result = table("23\tVisit\t90.00\t\t", "Item\tDescription\tCharge\tBenefit paid\tGap")
    assert result.line_items[0].charged == 90
    assert result.line_items[0].benefit_paid is None
    assert result.line_items[0].gap is None


def test_outer_pipes_and_missing_item_column():
    result = table("| | Administration | 15.00 |", "| Item | Description | Charge |")
    assert result.line_items[0].item_number is None
    assert result.line_items[0].charged == 15


def test_numbers_without_a_table_header_are_not_guessed():
    result = extract("Invoice number: 1234\n23 Consultation 90.00 65.00 25.00")
    assert not result.line_items
    assert result.warnings


def test_bad_row_width_is_skipped_without_shifting_columns():
    result = extract("Item | Description | Charge\n23 | Visit\n36 | Another visit | 50.00")
    assert len(result.line_items) == 1
    assert result.line_items[0].item_number == "36"
    assert any("row does not match" in warning for warning in result.warnings)


def test_fee_with_quantity_is_not_assumed_to_be_the_line_charge():
    result = table("23 | Visit | 2 | 50.00", "Item | Description | Quantity | Fee")
    assert not result.line_items
    assert any("explicit line charge" in warning for warning in result.warnings)


def test_total_ends_table_before_payment_instructions():
    result = extract(EXAMPLE + "Account | Transfer | 123456\n")
    assert len(result.line_items) == 2
    assert result.total_charged == 105


def test_duplicate_columns_are_rejected():
    result = table("23 | Visit | 90.00 | 100.00", "Item | Description | Charge | Charged")
    assert not result.line_items
    assert any("duplicate" in warning for warning in result.warnings)


def test_repeated_rows_are_not_deduplicated():
    result = table("23 | Visit | 90.00\n23 | Visit | 90.00")
    assert len(result.line_items) == 2


def test_contradictory_totals_stay_unknown():
    result = extract(EXAMPLE + "Total charged: $106.00\nTotal charged: $105.00")
    assert result.total_charged is None
    assert any("conflicting" in warning for warning in result.warnings)


def test_printed_total_mismatch_is_reported_not_silently_corrected():
    result = extract(EXAMPLE.replace("$105.00", "$100.00"))
    assert result.total_charged == 100
    assert any("differs from extracted rows" in warning for warning in result.warnings)


def test_impossible_paid_benefit_is_not_forwarded():
    result = table("23 | Visit | 90.00 | 100.00 | 0.00", "Item | Description | Charge | Benefit paid | Gap")
    assert result.line_items[0].benefit_paid is None
    assert result.line_items[0].gap is None
    assert any("exceeds charge" in warning for warning in result.warnings)


def test_inconsistent_gap_is_not_forwarded():
    result = table("23 | Visit | 90.00 | 60.00 | 25.00", "Item | Description | Charge | Benefit paid | Gap")
    assert result.line_items[0].benefit_paid == 60
    assert result.line_items[0].gap is None
    assert result.warnings


def test_foreign_currency_is_not_treated_as_aud():
    result = table("23 | Visit | USD 90.00")
    assert not result.line_items
    assert any("Non-AUD" in warning for warning in result.warnings)


def test_invalid_date_is_unknown():
    result = extract(EXAMPLE.replace("01/09/2026", "31/02/2026"))
    assert result.service_date is None
    assert result.warnings


@pytest.mark.parametrize("text", ["", "\x00", "x" * (MAX_CHARS + 1)], ids=["empty", "binary", "oversized"])
def test_unusable_text_returns_warnings(text):
    result = extract(read_text(text))
    assert not result.line_items
    assert result.warnings


def test_pdf_columns_and_reading_order(tmp_path):
    data = pdf_bytes([("Item", "Description", "Charge"),
                      ("23", "Short consultation", "$90.00"),
                      ("-", "Administration fee", "$15.00")])
    path = tmp_path / "synthetic.pdf"
    path.write_bytes(data)
    for source in (data, path):
        bill = read_pdf(source)
        assert bill.page_count == 1
        result = extract(bill)
        assert result.source_kind == "pdf_text"
        assert [item.charged for item in result.line_items] == [90, 15]
        assert [item.item_number for item in result.line_items] == ["23", None]


@pytest.mark.parametrize("data", [b"", b"not a PDF", b"%PDF-broken", b"%PDF-" + b"x" * MAX_BYTES], ids=["empty", "not-pdf", "malformed", "oversized"])
def test_invalid_pdf_is_not_partially_extracted(data):
    bill = read_pdf(data)
    assert not bill.text
    assert bill.warnings


def test_missing_pdf_returns_warning(tmp_path):
    assert read_pdf(tmp_path / "missing.pdf").warnings


def test_password_protected_pdf_is_rejected():
    bill = read_pdf(pdf_bytes([("Item", "Description", "Charge")], encrypted=True))
    assert not bill.text
    assert "password" in bill.warnings[0]


def test_page_limit_is_enforced():
    bill = read_pdf(pdf_bytes(pages=21))
    assert not bill.text
    assert "20 pages" in bill.warnings[0]


def test_a_blank_page_prevents_silent_partial_extraction():
    with pymupdf.open() as document:
        document.new_page().insert_text((40, 60), "Item   Description   Charge")
        document.new_page()
        bill = read_pdf(document.tobytes())
    assert not bill.text
    assert "Page 2" in bill.warnings[0]
