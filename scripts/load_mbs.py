"""Build the MBS SQLite table from the official export.

    python scripts/load_mbs.py --source data/mbs/MBS-XML-20260801.XML \
        --db data/mbs/mbs.sqlite --captured-on 2026-09-21
    python scripts/load_mbs.py --source data/mbs/mbs.csv --db data/mbs/mbs.sqlite \
        --map ITEM=ItemNum,DESCRIPTION=Description,SCHEDULE_FEE=ScheduleFee

Download the export yourself from mbsonline.gov.au and record the download date
with --captured-on. The date goes into every row, because a schedule fee
without a capture date is a number nobody can check later.

The export's column names have changed between releases, so this script fails
loudly on a missing column rather than quietly writing an empty table.

Owner: Bikram Bhattarai. Reviewer: Aayush Khade.
"""

from __future__ import annotations

import argparse
import hashlib
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from pathlib import Path

from oshc.billexplainer.mbs import MbsRow, load_mbs_csv, to_sqlite

XML_FIELDS = {
    "item_number": ("ItemNum", "Item", "ITEM"),
    "description": ("Description", "ItemDescription", "DESCRIPTION"),
    "schedule_fee": ("ScheduleFee", "Fee", "SCHEDULE_FEE"),
    "category": ("Category", "CATEGORY"),
}


def _first(node: ET.Element, names: tuple[str, ...]) -> str | None:
    for n in names:
        found = node.find(n)
        if found is not None and (found.text or "").strip():
            return found.text.strip()
    return None


def load_xml(path: Path, captured_on: str) -> list[MbsRow]:
    root = ET.parse(path).getroot()
    rows: list[MbsRow] = []
    skipped = 0
    for node in root.iter():
        item = _first(node, XML_FIELDS["item_number"])
        desc = _first(node, XML_FIELDS["description"])
        fee = _first(node, XML_FIELDS["schedule_fee"])
        if not (item and desc and fee):
            continue
        try:
            fee_dec = Decimal(fee.replace("$", "").replace(",", ""))
        except InvalidOperation:
            skipped += 1
            continue
        rows.append(
            MbsRow(
                item.strip().upper(),
                desc,
                fee_dec,
                _first(node, XML_FIELDS["category"]),
                captured_on,
            )
        )
    if not rows:
        raise ValueError(
            f"No usable items found in {path.name}. Element names differ from "
            f"{XML_FIELDS}. Open the file, find the real tag names, add them above."
        )
    if skipped:
        print(f"note: {skipped} node(s) had an unparseable fee and were skipped")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="official MBS export, .csv or .xml")
    ap.add_argument("--db", default="data/mbs/mbs.sqlite")
    ap.add_argument(
        "--captured-on", required=True, help="the date you downloaded it, YYYY-MM-DD"
    )
    ap.add_argument(
        "--map", default="", help="EXPORTCOL=OurCol pairs, comma separated (csv only)"
    )
    args = ap.parse_args()

    src = Path(args.source)
    if not src.exists():
        print(f"error: {src} not found. Download it from mbsonline.gov.au first.")
        return 1

    digest = hashlib.sha256(src.read_bytes()).hexdigest()

    if src.suffix.lower() == ".xml":
        rows = load_xml(src, args.captured_on)
    else:
        cmap = dict(p.split("=", 1) for p in args.map.split(",") if "=" in p) or None
        rows = [
            MbsRow(
                r.item_number,
                r.description,
                r.schedule_fee,
                r.category,
                r.captured_on or args.captured_on,
            )
            for r in load_mbs_csv(src, column_map=cmap)
        ]

    written = to_sqlite(rows, args.db)
    sample = rows[0]
    print(f"source      : {src.name}")
    print(f"sha256      : {digest}")
    print(f"captured_on : {args.captured_on}")
    print(f"rows written: {written}")
    print(
        f"first row   : {sample.item_number} | {sample.description[:60]}"
        f" | {sample.schedule_fee}"
    )
    print()
    print("Record the sha256 and captured_on in the minutes. The fee table is")
    print("evidence, and evidence without provenance is not evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
