"""Data minimisation at the bill UI boundary; no raw narrative is retained."""
from __future__ import annotations

from dataclasses import asdict
from oshc.schemas import ExtractionResult
from oshc.billexplainer.extract_document import ReceiptFacts


def minimise(result: ExtractionResult) -> ExtractionResult:
    """Keep numeric teaching fields, suppress names and arbitrary invoice narrative.

    Do not try to identify every possible name with a regex. The application does
    not need any free text from an uploaded bill to explain its amounts.
    """
    items = [line.model_copy(update={
        "raw_description": f"Service line {number}", "mbs_descriptor": None,
        "note": None,
    }) for number, line in enumerate(result.line_items, 1)]
    # Reader warnings are fixed templates; never forward arbitrary cached text.
    notes = []
    if result.warnings:
        notes.append("The reader flagged a layout, date or amount issue. Check the retained fields against your original document.")
    return result.model_copy(update={"provider": None, "line_items": items, "warnings": notes})


def retained_fields(result: ExtractionResult, receipt: ReceiptFacts) -> dict:
    return {
        "document_reading": minimise(result).model_dump(mode="json"),
        "receipt": {k: v for k, v in asdict(receipt).items() if k != "warnings"},
        "privacy": "Names, identifiers, provider details and original descriptions omitted. Original file and source text are not included.",
    }
