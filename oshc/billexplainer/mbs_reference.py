"""Frozen MBS comparisons for learning examples, not OSHC claim estimates."""
from __future__ import annotations

import hashlib
import io
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import MappingProxyType
from typing import Literal, Mapping, Sequence

from oshc.schemas import ExtractionResult, LineItem

FROZEN_SHA256 = "c5c04792cbdc7017589b4453aa4506f26b6cfcbfeaee3b0d6c866a8050b06565"
SOURCE_PAGE = "https://www.mbsonline.gov.au/internet/mbsonline/publishing.nsf/Content/Downloads-20260801"
RELEASE_DATE = date(2026, 8, 1)
CAPTURE_DATE = date(2026, 9, 28)
CENT = Decimal("0.01")
SCOPE = (
    "Illustrative MBS reference comparison in AUD. The selected reference is capped "
    "at the line charge for this example. This is not an OSHC benefit or claim decision. "
    "Policy conditions, item eligibility, other adjustments and later source revisions "
    "have not been assessed. Printed benefits and gaps remain separate."
)
FIELDS = (
    "ItemNum", "Description", "Category", "Group", "FeeType", "ScheduleFee",
    "BenefitType", "Benefit85", "Benefit100", "ItemStartDate", "ItemEndDate",
    "FeeStartDate", "BenefitStartDate", "QFEStartDate", "QFEEndDate",
)


class SourceError(ValueError):
    pass


@dataclass(frozen=True)
class Snapshot:
    source_sha256: str
    items: Mapping[str, Mapping[str, str]]


@dataclass(frozen=True)
class LineComparison:
    line_number: int
    status: Literal["available", "unavailable"]
    reason: str
    item_number: str | None = None
    reference_field: str | None = None
    descriptor: str | None = None
    reference_amount: Decimal | None = None
    amount_used: Decimal | None = None
    difference: Decimal | None = None


@dataclass(frozen=True)
class BillComparison:
    source_sha256: str
    source_page: str
    release_date: str
    captured_on: str
    scope: str
    lines: tuple[LineComparison, ...]
    total_difference: Decimal | None
    total_note: str


def load_snapshot(path: str | Path = "corpus/MBS-XML-20260801.XML") -> Snapshot:
    """Read the approved bytes only. No download, database write or provider call."""
    path = Path(path)
    limit = 64 * 1024 * 1024
    with path.open("rb") as handle:
        raw = handle.read(limit + 1)
    if not raw or len(raw) > limit:
        raise SourceError("MBS XML is empty or exceeds 64 MiB.")
    checksum = hashlib.sha256(raw).hexdigest()
    if checksum != FROZEN_SHA256:
        raise SourceError("MBS XML hash differs from the frozen source.")
    items = {}
    try:
        for _, node in ET.iterparse(io.BytesIO(raw), events=("end",)):
            names = [child.tag.rsplit("}", 1)[-1] for child in node]
            if "ItemNum" not in names:
                continue
            if len(names) != len(set(names)):
                raise SourceError("Duplicate fields in an MBS record.")
            values = dict(zip(names, ((child.text or "").strip() for child in node)))
            item = values["ItemNum"]
            if not re.fullmatch(r"[1-9][0-9]{0,5}", item):
                raise SourceError("Invalid item number in the MBS source.")
            if item in items:
                raise SourceError("Duplicate item number in the MBS source.")
            items[item] = MappingProxyType({key: values.get(key, "") for key in FIELDS})
            node.clear()
    except ET.ParseError as error:
        raise SourceError("MBS XML could not be parsed.") from error
    if not items:
        raise SourceError("MBS XML has no recognised records.")
    return Snapshot(checksum, MappingProxyType(items))


def _money(value) -> Decimal | None:
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or not 0 <= amount <= 1_000_000:
            return None
        rounded = amount.quantize(CENT)
        return rounded if rounded == amount else None
    except (InvalidOperation, ValueError):
        return None


def _service_date(value: str | None) -> date | None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _line(number: int, line: LineItem, field: str | None,
          when: date | None, snapshot: Snapshot) -> LineComparison:
    def unavailable(reason):
        return LineComparison(number, "unavailable", reason)

    if field not in ("ScheduleFee", "Benefit85", "Benefit100"):
        return unavailable("Choose an explicit MBS reference basis for this example.")
    if when is None or not RELEASE_DATE <= when <= CAPTURE_DATE:
        return unavailable("Service date is missing or outside the frozen comparison window.")
    item = line.item_number or ""
    if not re.fullmatch(r"[1-9][0-9]{0,5}", item) or item not in snapshot.items:
        return unavailable("A recognised printed item number is required; description matching is not used.")
    row = snapshot.items[item]
    if row["FeeType"] != "N":
        return unavailable("Derived or unsupported fees need a separate calculation.")
    if field != "ScheduleFee" and row["BenefitType"] not in (
        ("B", "C") if field == "Benefit85" else ("D", "E")
    ):
        return unavailable("The selected published benefit does not apply to this MBS record.")
    required = ["ItemStartDate", "FeeStartDate"]
    if field != "ScheduleFee":
        required.append("BenefitStartDate")
    try:
        starts = [datetime.strptime(row[key], "%d.%m.%Y").date() for key in required]
        if row["QFEStartDate"]:
            starts.append(datetime.strptime(row["QFEStartDate"], "%d.%m.%Y").date())
        ends = [datetime.strptime(row[key], "%d.%m.%Y").date()
                for key in ("ItemEndDate", "QFEEndDate") if row[key]]
    except ValueError:
        return unavailable("Required source dates are missing or invalid.")
    if any(when < start for start in starts) or any(when > end for end in ends):
        return unavailable("The source dates do not cover this service date.")
    charge, fee, reference = _money(line.charged), _money(row["ScheduleFee"]), _money(row[field])
    if charge is None or fee is None or reference is None or reference > fee:
        return unavailable("The charge or selected source amount is missing or invalid.")
    amount_used = min(charge, reference)
    return LineComparison(number, "available", "Reference comparison only; cover is not assessed.",
                          item, field, row["Description"], reference, amount_used,
                          charge - amount_used)


def compare_bill(extracted: ExtractionResult, snapshot: Snapshot,
                 bases: Sequence[str | None] | None = None) -> BillComparison:
    """Each basis is explicitly selected, in bill-line order. Input is never modified."""
    selections = list(bases) if bases is not None else [None] * len(extracted.line_items)
    if len(selections) != len(extracted.line_items):
        raise ValueError("Supply one reference selection per bill line.")
    when = _service_date(extracted.service_date)
    lines = tuple(_line(i, line, field, when, snapshot)
                  for i, (line, field) in enumerate(zip(extracted.line_items, selections), 1))
    total = None
    note = "Total unavailable: every line must resolve and line charges must match a printed bill total."
    if lines and all(line.status == "available" for line in lines):
        charges = sum((_money(line.charged) for line in extracted.line_items), Decimal("0.00"))
        if _money(extracted.total_charged) == charges:
            total = sum((line.difference for line in lines), Decimal("0.00"))
            note = "Sum of illustrative differences only; not an actual bill gap or insurer benefit."
    return BillComparison(snapshot.source_sha256, SOURCE_PAGE, RELEASE_DATE.isoformat(),
                          CAPTURE_DATE.isoformat(), SCOPE, lines, total, note)
