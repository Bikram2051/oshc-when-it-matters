"""Current prototype reader; the frozen research extractor stays unchanged.

Normalise explicitly labelled invoice tables and keep provider settlements separate
from insurer benefits. No description matching, instruction execution or model calls.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from oshc.billexplainer import extract_rules as baseline
from oshc.billexplainer.read import BillText, read_text
from oshc.schemas import ExtractionResult

TOTAL_LABELS = {"total gross amount", "grand total", "total amount charged"}
RECEIPT_LABELS = {
    "amount settled": "amount_settled", "amount paid": "amount_settled",
    "payment received": "amount_settled", "balance remaining": "balance_remaining",
    "balance due": "balance_remaining", "amount owing": "balance_remaining",
    "total gst": "total_gst",
}
DATE_COLUMNS = {"date", "service date", "date of service"}


@dataclass(frozen=True)
class ReceiptFacts:
    amount_settled: float | None = None
    balance_remaining: float | None = None
    total_gst: float | None = None
    service_dates: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def _labelled_value(raw, allow_tax_tail=False):
    """A second amount is only a GST column in a known Fee/GST table footer."""
    cells, _ = baseline._cells(raw)
    if len(cells) == 1:
        return cells[0]
    if (allow_tax_tail and len(cells) == 2
            and baseline.MONEY.fullmatch(cells[0])
            and baseline.MONEY.fullmatch(cells[1])):
        return cells[0]
    return "unsupported multiple values"


def read_document(source: str | BillText) -> tuple[ExtractionResult, ReceiptFacts]:
    bill = read_text(source) if isinstance(source, str) else source
    # Preserve baseline limits and currency rejection before normalisation.
    if (not bill.text.strip() or bill.source_kind == "image"
            or baseline.FOREIGN.search(bill.text) or len(bill.text.splitlines()) > 2000):
        return baseline.extract(bill), ReceiptFacts()
    normalised, notes, dates = [], [], []
    receipt, conflicts = {}, set()
    header, style, tax_tail = None, None, False
    date_column_seen, invalid_date = False, False

    for number, raw in enumerate(bill.text.splitlines(), 1):
        where = f"Line {number}"
        label = re.fullmatch(r"\s*([^:]{1,60}):\s*(.*)", raw)
        name = baseline._name(label[1]) if label else ""
        if name in TOTAL_LABELS or name in baseline.LABELS or name in RECEIPT_LABELS:
            value = _labelled_value(label[2], allow_tax_tail=tax_tail)
            if name in RECEIPT_LABELS:
                key = RECEIPT_LABELS[name]
                amount = baseline._money(value, notes, where)
                if key in receipt and receipt[key] != amount:
                    conflicts.add(key)
                    notes.append(f"{where}: conflicting receipt amount; left unknown.")
                receipt[key] = None if key in conflicts else amount
                normalised.append("")
            else:
                target = "Total charged" if name in TOTAL_LABELS else label[1]
                normalised.append(f"{target}: {value}")
            header, style = None, None
            continue

        cells, candidate_style = baseline._cells(raw)
        names = [baseline._name(cell) for cell in cells]
        mapped = [baseline.COLUMNS.get(name) for name in names]
        if "raw_description" in mapped and "charged" in mapped:
            # Let the frozen reader reject ambiguous quantity/fee and duplicate columns.
            header, style = names, candidate_style
            tax_tail = len(names) >= 2 and mapped[-2:] == ["charged", None] and names[-1] == "gst"
            normalised.append(" | ".join(cell for cell, name in zip(cells, names)
                                         if name not in DATE_COLUMNS and name != "gst"))
            continue
        cells, _ = baseline._cells(raw, style)
        if header is not None and len(cells) == len(header):
            for name, cell in zip(header, cells):
                if name in DATE_COLUMNS:
                    date_column_seen = True
                    parsed = baseline._date(cell, notes, where)
                    invalid_date |= parsed is None
                    if parsed:
                        dates.append(parsed)
            normalised.append(" | ".join(cell for cell, name in zip(cells, header)
                                         if name not in DATE_COLUMNS and name != "gst"))
        else:
            normalised.append(raw)

    result = baseline.extract(BillText("\n".join(normalised), bill.source_kind,
                                      bill.warnings, bill.page_count))
    distinct_dates = tuple(sorted(set(dates)))
    if date_column_seen and result.line_items:
        if invalid_date or len(distinct_dates) != 1:
            notes.append("Service rows have different or unreadable dates; no single service date used.")
            result = result.model_copy(update={"service_date": None})
        elif result.service_date is not None and result.service_date != distinct_dates[0]:
            notes.append("Service-row dates conflict with the labelled service date; left unknown.")
            result = result.model_copy(update={"service_date": None})
        elif not any("service_date" in note or "service date" in note for note in result.warnings):
            result = result.model_copy(update={"service_date": distinct_dates[0]})
    result = result.model_copy(update={"warnings": list(dict.fromkeys([*result.warnings, *notes]))})
    return result, ReceiptFacts(**receipt, service_dates=distinct_dates, warnings=tuple(notes))


def extract(source: str | BillText) -> ExtractionResult:
    return read_document(source)[0]
