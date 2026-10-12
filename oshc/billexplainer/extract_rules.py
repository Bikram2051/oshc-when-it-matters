'''Conservative labelled-table extraction. No LLM or benefit estimates.'''

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal

from oshc.billexplainer.read import BillText, read_text
from oshc.schemas import ExtractionResult, LineItem

COLUMNS = {
    "item": "item_number", "item number": "item_number", "mbs item": "item_number",
    "mbs item number": "item_number", "description": "raw_description",
    "service": "raw_description", "service description": "raw_description",
    "charge": "charged", "charged": "charged", "amount charged": "charged", "fee": "charged",
    "benefit paid": "benefit_paid", "insurer paid": "benefit_paid", "rebate paid": "benefit_paid",
    "gap": "gap", "out of pocket": "gap", "patient gap": "gap",
}
LABELS = {
    "provider": "provider", "service date": "service_date", "date of service": "service_date",
    "total charged": "total_charged", "total charge": "total_charged", "total fees": "total_charged",
    "total benefit paid": "total_benefit", "total insurer paid": "total_benefit",
    "total gap": "total_gap", "total out of pocket": "total_gap",
}
MISSING = {"", "-", "\u2014", "n/a", "unknown", "not shown"}
MONEY = re.compile(r"(?:(?:AUD|A\$|\$)\s*)?((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?)", re.I)
MONEY_LIKE = re.compile(r"(?:AUD|A\$|\$)\s*\d|\b\d+\.\d{2}\b", re.I)
FOREIGN = re.compile(r"\b(?:USD|NZD|CAD|EUR|GBP|INR|JPY|CNY)\b|[\u20ac\u00a3\u00a5]", re.I)


def _name(text):
    text = re.sub(r"\s*\((?:aud|a?\$)\)\s*$", "", text.lower())
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _cells(line, style=None):
    line = line.strip(" \r")
    if style is None:
        if "|" in line:
            style = "outer" if line.startswith("|") and line.endswith("|") else "pipe"
        elif "\t" in line:
            style = "tab"
        elif re.search(r" {2,}", line):
            style = "space"
    if style == "outer":
        if not (line.startswith("|") and line.endswith("|")):
            return [], style
        line = line[1:-1]
    if style in ("pipe", "outer"):
        cells = line.split("|")
    elif style == "tab":
        cells = line.split("\t")
    elif style == "space":
        cells = re.split(r" {2,}", line)
    else:
        cells = [line]
    return [cell.strip() for cell in cells], style


def _money(text, warnings, where):
    if text.lower() in MISSING:
        return None
    match = MONEY.fullmatch(text)
    if match:
        value = Decimal(match[1].replace(",", ""))
        if value <= 1_000_000:
            return float(value)
    warnings.append(f"{where}: unsupported money value; left unknown.")
    return None


def _item(text, warnings, where):
    if text.lower() in MISSING:
        return None
    match = re.fullmatch(r"(?:(?:MBS|Item(?: No\.?)?)\s*)?(\d{1,5})(?:\.0+)?", text, re.I)
    if match and int(match[1]) > 0:
        return str(int(match[1]))
    warnings.append(f"{where}: unclear item number; left unknown.")
    return None


def _date(text, warnings, where):
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, pattern).date().isoformat()
        except ValueError:
            pass
    warnings.append(f"{where}: unrecognised service date; left unknown.")
    return None


def _check_amounts(values, keys, warnings, where):
    charged, benefit, gap = (values.get(key) for key in keys)
    if charged is None:
        return
    if benefit is not None and benefit > charged:
        values[keys[1]] = values[keys[2]] = None
        warnings.append(f"{where}: benefit exceeds charge; benefit and gap left unknown.")
        return
    if gap is not None and (gap > charged or (
        benefit is not None and Decimal(str(charged)) - Decimal(str(benefit)) != Decimal(str(gap))
    )):
        values[keys[2]] = None
        warnings.append(f"{where}: inconsistent gap; left unknown.")


def extract(source: str | BillText) -> ExtractionResult:
    bill = read_text(source) if isinstance(source, str) else source
    warnings = list(bill.warnings)
    if not bill.text.strip() or bill.source_kind == "image":
        return ExtractionResult(extractor="rules", source_kind=bill.source_kind,
                                warnings=warnings or ["No supported text to extract."])
    if FOREIGN.search(bill.text):
        return ExtractionResult(extractor="rules", source_kind=bill.source_kind,
                                warnings=warnings + ["Non-AUD currency found; amounts were not extracted."])
    lines = bill.text.splitlines()
    if len(lines) > 2_000:
        return ExtractionResult(extractor="rules", source_kind=bill.source_kind,
                                warnings=warnings + ["Too many text lines; extraction stopped."])

    items, fields, conflicted = [], {}, set()
    header, style = None, None
    for number, raw in enumerate(lines, 1):
        line = raw.strip(" \r")
        if not line.strip() or re.fullmatch(r"[\s|:\-]+", line):
            continue
        where = f"Line {number}"
        label = re.fullmatch(r"([^:]{1,60}):\s*(.*)", line)
        field = LABELS.get(_name(label[1])) if label else None
        if field:
            header, style = None, None
            value = label[2].strip()
            if field.startswith("total_"):
                value = _money(value, warnings, where)
            elif field == "service_date":
                value = _date(value, warnings, where)
            else:
                value = value or None
            if field in conflicted:
                continue
            if field in fields and fields[field] != value:
                fields[field] = None
                conflicted.add(field)
                warnings.append(f"{where}: conflicting {field}; left unknown.")
            else:
                fields[field] = value
            continue

        candidate, candidate_style = _cells(line)
        names = [_name(cell) for cell in candidate]
        mapped = [COLUMNS.get(name) for name in names]
        if "raw_description" in mapped and "charged" in mapped:
            if set(names) & {"qty", "quantity", "units"} and "fee" in names and not (
                set(names) & {"charge", "charged", "amount charged"}
            ):
                header = None
                warnings.append(f"{where}: quantity with an ambiguous fee; explicit line charge required.")
                continue
            known = [key for key in mapped if key]
            if len(known) != len(set(known)):
                header = None
                warnings.append(f"{where}: duplicate table columns; table not interpreted.")
                continue
            header, style = mapped, candidate_style
            if None in mapped:
                warnings.append(f"{where}: unrecognised table columns omitted; payments are not insurer benefits.")
            continue

        cells, _ = _cells(line, style)
        if header is None or len(cells) != len(header):
            if header is not None and len(cells) > 1:
                warnings.append(f"{where}: table row does not match its header; row skipped.")
            elif MONEY_LIKE.search(line):
                warnings.append(f"{where}: monetary content could not be assigned to labelled columns.")
            continue
        values = {}
        for key, cell in zip(header, cells):
            if key == "item_number":
                values[key] = _item(cell, warnings, where)
            elif key in ("charged", "benefit_paid", "gap"):
                values[key] = _money(cell, warnings, where)
            elif key == "raw_description":
                values[key] = cell
        if values.get("raw_description", "").lower() in MISSING:
            warnings.append(f"{where}: missing service description; row skipped.")
            continue
        _check_amounts(values, ("charged", "benefit_paid", "gap"), warnings, where)
        items.append(LineItem(**values, note=f"Printed values from source line {number}."))

    _check_amounts(fields, ("total_charged", "total_benefit", "total_gap"), warnings, "Totals")
    for total, column in (("total_charged", "charged"), ("total_benefit", "benefit_paid"), ("total_gap", "gap")):
        printed = fields.get(total)
        amounts = [getattr(item, column) for item in items]
        if printed is not None and amounts and all(value is not None for value in amounts):
            summed = sum((Decimal(str(value)) for value in amounts), Decimal(0))
            if summed != Decimal(str(printed)):
                warnings.append(f"Printed {total} differs from extracted rows; review the source bill.")
    if not items:
        warnings.append("No supported table rows found. Use labelled columns or review manually.")
    return ExtractionResult(extractor="rules", source_kind=bill.source_kind,
                            line_items=items, warnings=list(dict.fromkeys(warnings)), **fields)
