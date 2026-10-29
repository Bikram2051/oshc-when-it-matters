"""Synthetic invoice generator. ReportLab to PDF, PyMuPDF to PNG.

Emits gold JSON alongside every document, so the ground truth comes from the
generator and never from a human reading the output.

ROLE SEPARATION, enforced by process not by code:
  - Minhaj owns this file. Bikram does not read it and does not review its diffs.
  - Two of four layout families are frozen as held-out. Their parameters live in
    data/heldout/ which is gitignored until evaluation day.
  - Aayush reviews this file, because Bikram writes the extractor it is scored
    against.

Owner: Md Minhaj Rahman. Reviewer: Aayush Khade.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import fitz
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

FAMILIES = ("gp_simple", "pathology_multiline", "specialist_gap", "hospital_mixed")
HELD_OUT = ("specialist_gap", "hospital_mixed")  # frozen before extraction code exists

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path.home() / "Desktop" / "oshc-week7-generated"
HELDOUT_DIR = ROOT / "data" / "heldout"


def _money(value: str | int | float | Decimal) -> str:
    """Return money exactly as required by the extraction gold protocol."""
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{amount:.2f}"


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest required by the evaluation file map."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    """Write deterministic UTF-8 JSON for generator-produced gold records."""
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )




def _render_gp_simple(record: dict, pdf_path: Path, png_path: Path) -> None:
    """Render one visible-family synthetic GP invoice as PDF and PNG."""
    pdf = canvas.Canvas(str(pdf_path), pagesize=A4)
    _, height = A4
    y = height - 70

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(60, y, "SYNTHETIC INVOICE")
    y -= 28

    pdf.setFont("Helvetica", 10)
    pdf.drawString(60, y, f"Provider: {record['provider']}")
    y -= 18
    pdf.drawString(60, y, f"Service date: {record['service_date']}")
    y -= 28

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(60, y, "Item | Description | Charge")
    y -= 18

    pdf.setFont("Helvetica", 10)
    for item in record["line_items"]:
        number = item["item_number"] or "-"
        pdf.drawString(
            60,
            y,
            f"{number} | {item['raw_description']} | ${item['charged']}",
        )
        y -= 18

    y -= 8
    pdf.drawString(60, y, f"Total charged: ${record['total_charged']}")
    pdf.save()

    document = fitz.open(pdf_path)
    page = document[0]
    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    pixmap.save(str(png_path))
    document.close()

def _gp_simple_record(index: int) -> dict:
    """Create one deterministic visible-family GP invoice record."""
    consultation = Decimal("90.00") + Decimal(index % 4) * Decimal("5.00")
    admin_fee = Decimal("15.00")
    total = consultation + admin_fee

    return {
        "document_id": f"GP-{index:03d}",
        "family": "gp_simple",
        "provider": "Demonstration General Practice",
        "service_date": f"2026-09-{index:02d}",
        "total_charged": _money(total),
        "total_benefit": None,
        "total_gap": None,
        "line_items": [
            {
                "raw_description": "Short consultation",
                "item_number": "23",
                "charged": _money(consultation),
                "benefit_paid": None,
                "gap": None,
            },
            {
                "raw_description": "Administration fee",
                "item_number": None,
                "charged": _money(admin_fee),
                "benefit_paid": None,
                "gap": None,
            },
        ],
    }




def _pathology_multiline_gold(record: dict) -> dict:
    """Return gold JSON with one entry per physically printed pathology line."""
    wrapped = {
        "65060": ("Haemoglobin, ESR and", "blood viscosity"),
        "65070": ("Blood count and blood", "film examination"),
        "65072": ("Reticulocyte examination", "and count"),
    }

    gold = dict(record)
    printed_lines = []

    for item in record["line_items"]:
        first, second = wrapped[item["item_number"]]

        printed_lines.append({
            "raw_description": first,
            "item_number": item["item_number"],
            "charged": item["charged"],
            "benefit_paid": None,
            "gap": None,
        })

        printed_lines.append({
            "raw_description": second,
            "item_number": None,
            "charged": None,
            "benefit_paid": None,
            "gap": None,
        })

    gold["line_items"] = printed_lines
    return gold

def _render_pathology_multiline(record: dict, pdf_path: Path, png_path: Path) -> None:
    """Render pathology rows with wrapped description continuation lines."""
    pdf = canvas.Canvas(str(pdf_path), pagesize=A4)
    _, height = A4
    y = height - 70

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(60, y, "SYNTHETIC PATHOLOGY INVOICE")
    y -= 28

    pdf.setFont("Helvetica", 10)
    pdf.drawString(60, y, f"Provider: {record['provider']}")
    y -= 18
    pdf.drawString(60, y, f"Service date: {record['service_date']}")
    y -= 28

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(60, y, "MBS item | Description | Charge")
    y -= 20

    wrapped = {
        "65060": ("Haemoglobin, ESR and", "blood viscosity"),
        "65070": ("Blood count and blood", "film examination"),
        "65072": ("Reticulocyte examination", "and count"),
    }

    pdf.setFont("Helvetica", 10)
    for item in record["line_items"]:
        first, second = wrapped[item["item_number"]]
        pdf.drawString(
            60,
            y,
            f"{item['item_number']} | {first} | ${item['charged']}",
        )
        y -= 15
        pdf.drawString(125, y, second)
        y -= 22

    pdf.drawString(60, y, f"Total charged: ${record['total_charged']}")
    pdf.save()

    document = fitz.open(pdf_path)
    page = document[0]
    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    pixmap.save(str(png_path))
    document.close()

def _pathology_multiline_record(index: int) -> dict:
    """Create one deterministic visible-family pathology invoice record."""
    items = [
        {
            "raw_description": "Haemoglobin, ESR and blood viscosity",
            "item_number": "65060",
            "charged": _money("8.25"),
            "benefit_paid": None,
            "gap": None,
        },
        {
            "raw_description": "Blood count and blood film examination",
            "item_number": "65070",
            "charged": _money("17.80"),
            "benefit_paid": None,
            "gap": None,
        },
        {
            "raw_description": "Reticulocyte examination and count",
            "item_number": "65072",
            "charged": _money("10.70"),
            "benefit_paid": None,
            "gap": None,
        },
    ]

    total = sum(Decimal(item["charged"]) for item in items)

    return {
        "document_id": f"PATH-{index:03d}",
        "family": "pathology_multiline",
        "provider": "Demonstration Pathology Laboratory",
        "service_date": f"2026-09-{10 + index:02d}",
        "total_charged": _money(total),
        "total_benefit": None,
        "total_gap": None,
        "line_items": items,
    }

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic OSHC invoice fixtures.")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output directory kept outside the repository.",
    )
    parser.add_argument(
        "--visible-count",
        type=int,
        default=10,
        help="Number of invoices to generate for each visible family.",
    )
    args = parser.parse_args()

    if args.visible_count < 1:
        raise SystemExit("--visible-count must be at least 1")

    out = args.out.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    map_rows = []

    for index in range(1, args.visible_count + 1):
        record = _gp_simple_record(index)

        pdf = out / f"{record['document_id']}.pdf"
        png = out / f"{record['document_id']}.png"
        gold = out / f"{record['document_id']}.json"

        _render_gp_simple(record, pdf, png)
        _write_json(gold, record)

        map_rows.append({
            "document_id": record["document_id"],
            "family": record["family"],
            "input_file": pdf.name,
            "input_sha256": _sha256(pdf),
            "gold_file": gold.name,
            "gold_sha256": _sha256(gold),
        })

    for index in range(1, args.visible_count + 1):
        record = _pathology_multiline_record(index)

        pdf = out / f"{record['document_id']}.pdf"
        png = out / f"{record['document_id']}.png"
        gold = out / f"{record['document_id']}.json"

        _render_pathology_multiline(record, pdf, png)
        _write_json(gold, _pathology_multiline_gold(record))

        map_rows.append({
            "document_id": record["document_id"],
            "family": record["family"],
            "input_file": pdf.name,
            "input_sha256": _sha256(pdf),
            "gold_file": gold.name,
            "gold_sha256": _sha256(gold),
        })

    map_path = out / "visible_file_map.csv"

    with map_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "document_id",
                "family",
                "input_file",
                "input_sha256",
                "gold_file",
                "gold_sha256",
            ),
        )
        writer.writeheader()
        writer.writerows(map_rows)

    print(
        f"Generated {len(map_rows)} visible-family invoices "
        f"plus PDF, PNG and gold JSON in {out}"
    )
    print(f"File map: {map_path}")


if __name__ == "__main__":
    main()
